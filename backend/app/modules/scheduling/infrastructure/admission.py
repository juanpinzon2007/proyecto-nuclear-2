"""Solicitud de espera y concesión causal. Sin P/I ni políticas temporales nuevas."""
from sqlalchemy import select
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.scheduling.domain.ingress_policy import fecha_utc
from app.modules.scheduling.infrastructure.ingress_access import exigir_matricula_ingreso
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C, SesionProgramadaModel as S, EventoAuditoriaModel as E
from app.modules.scheduling.domain.access_codes import coincide_codigo


def contexto_admision(db, usuario, convocatoria_id):
    repo=RepositorioUsuariosSQLAlchemy(db)
    actual=repo.obtener(usuario.id_usuario)
    if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:raise AccesoDenegado()
    resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(db))
    ValidadorConvocatoriaScheduling(db,repo,resolver).validar_contexto(
        id_usuario=actual.id_usuario,contexto=usuario.id_convocatoria,solicitada=convocatoria_id)
    estudiante=resolver.resolver(id_usuario=actual.id_usuario,sistema=SistemaAcademico.SCHEDULING)
    c=db.get(C,convocatoria_id,populate_existing=True)
    if c is None or c.estado!='ACTIVA' or c.estudiante_id!=estudiante:raise AccesoDenegado()
    s=db.get(S,c.sesion_id,populate_existing=True)
    if s is None:raise IntegracionPendiente()
    exigir_matricula_ingreso(db,id_usuario=actual.id_usuario,sesion=s)
    return c,s


def registrar_espera(db, *, usuario, convocatoria_id, codigo, reloj):
    c,s=contexto_admision(db,usuario,convocatoria_id)
    # No esperar S mientras se posee C de otro escritor: S->C y NOWAIT.
    s=db.get(S,s.id,with_for_update={'nowait':True},populate_existing=True)
    c=db.get(C,c.id,with_for_update={'nowait':True},populate_existing=True)
    c,s=contexto_admision(db,usuario,c.id)
    if not coincide_codigo(codigo,c.codigo_hash):raise AccesoDenegado()
    if s.estado=='FINALIZADO':raise AccesoDenegado()
    if c.admision_evento_id is not None:
        verificar_concesion(db,c,s)
        return c,s,False
    if s.estado!='SIN_INICIAR':raise AccesoDenegado()
    if c.espera_registrada_en is not None:
        if c.espera_version_caso_id!=s.version_caso_id:raise IntegracionPendiente()
        return c,s,False
    c.espera_registrada_en=fecha_utc(reloj.ahora())
    c.espera_version_caso_id=s.version_caso_id
    db.flush()
    return c,s,True


def verificar_concesion(db,c,s):
    if s.estado!='EN_CURSO' or c.estado!='ACTIVA' or c.admision_evento_id is None:raise AccesoDenegado()
    if c.espera_registrada_en is None or c.espera_version_caso_id!=s.version_caso_id:raise IntegracionPendiente()
    e=db.get(E,c.admision_evento_id,populate_existing=True)
    if (e is None or e.sesion_id!=s.id or e.tipo!='CAMBIO_ESTADO' or e.origen!='DOCENTE'
            or e.estado_anterior!='SIN_INICIAR' or e.estado_nuevo!='EN_CURSO'):raise IntegracionPendiente()


class AdmisionSQLAlchemy:
    def __init__(self,db,usuario,*,bloquear=False):
        self.db,self.usuario,self.bloquear=db,usuario,bloquear
    def autorizar(self, *, convocatoria_id, estudiante_id, sesion_id, version_id):
        c,s=contexto_admision(self.db,self.usuario,convocatoria_id)
        if (c.estudiante_id,s.id,s.version_caso_id)!=(estudiante_id,sesion_id,version_id):raise AccesoDenegado()
        if self.bloquear and c.admision_evento_id is not None:
            # El escritor de Participation ya posee cuenta/matrícula/C/S/A.
            # Proteger también la evidencia causal hasta su único commit.
            self.db.get(E,c.admision_evento_id,with_for_update={'read':True},populate_existing=True)
        verificar_concesion(self.db,c,s)


def congelar_admisiones(db, *, sesion_id):
    # El coordinador ya tiene S exclusivo. Fallar rápido ante C poseída por un
    # escritor legado que espera S, nunca formar una espera circular.
    candidatas=db.scalars(select(C).where(C.sesion_id==sesion_id,C.espera_registrada_en.is_not(None),
        C.admision_evento_id.is_(None)).order_by(C.id).with_for_update(nowait=True)
        .execution_options(populate_existing=True)).all()
    if not candidatas:return
    s=db.get(S,sesion_id,populate_existing=True)
    eventos=db.scalars(select(E).where(E.sesion_id==sesion_id,E.tipo=='CAMBIO_ESTADO',
        E.estado_anterior=='SIN_INICIAR',E.estado_nuevo=='EN_CURSO',E.origen=='DOCENTE')
        .with_for_update(read=True)).all()
    if len(eventos)!=1 or s.estado!='EN_CURSO':raise IntegracionPendiente()
    for c in candidatas:
        if c.estado!='ACTIVA' or c.espera_version_caso_id!=s.version_caso_id:continue
        ids=db.scalars(select(IA.id_usuario).where(IA.sistema=='SCHEDULING',IA.id_academico==c.estudiante_id)).all()
        if len(ids)!=1:continue
        repo=RepositorioUsuariosSQLAlchemy(db);u=repo.obtener(str(ids[0]))
        if u is None or not u.activo or Rol.ESTUDIANTE not in u.roles:continue
        try:
            if ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(db)).resolver(
                id_usuario=u.id_usuario,sistema=SistemaAcademico.SCHEDULING)!=c.estudiante_id:continue
            exigir_matricula_ingreso(db,id_usuario=u.id_usuario,sesion=s)
        except (AccesoDenegado,IntegracionPendiente):continue
        c.admision_evento_id=eventos[0].id
    db.flush()
