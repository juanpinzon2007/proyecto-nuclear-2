"""Puente interno RF-26: reutiliza FeedbackDocente y su servicio transaccional.

Una valoración editable por participación y aviso interno atómico; sin notas.
"""
from datetime import timezone

from sqlalchemy import select, exists
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from app.modules.identity.application.services import ServicioFeedbackDocente
from app.modules.identity.domain.entities import Rol, FeedbackDocente
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM as F
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel
from app.modules.scheduling.application.crear_notificacion import crear_notificacion
from app.modules.cases.infrastructure.models import VersionCasoModel as V, CasoModel as C


class AmbitoFeedbackIndividual:
    def __init__(self,sesion,usuario): self.s,self.usuario=sesion,usuario

    def autorizar(self,id_docente,id_participacion):
        if id_docente!=self.usuario.id_usuario: raise AccesoDenegado()
        p=id_entero(id_participacion);u=id_entero(id_docente)
        self.s.execute(select(P.id_participacion).where(P.id_participacion==p).with_for_update()).one_or_none()
        cuenta=self.s.execute(select(UsuarioORM.id_rol).where(UsuarioORM.id_usuario==u).with_for_update()).one_or_none()
        if cuenta is None:raise AccesoDenegado()
        self.s.execute(select(RolORM.id_rol).where(RolORM.id_rol==cuenta.id_rol).with_for_update(read=True)).one()
        actual=RepositorioUsuariosSQLAlchemy(self.s).obtener(id_docente)
        if actual is None or not actual.activo or Rol.DOCENTE not in actual.roles: raise AccesoDenegado()
        self.s.execute(select(IdentidadAcademicaORM).where(IdentidadAcademicaORM.id_usuario==u).with_for_update(read=True)).all()
        resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(self.s))
        cases=resolver.resolver(id_usuario=id_docente,sistema=SistemaAcademico.CASES)
        scheduling=resolver.resolver(id_usuario=id_docente,sistema=SistemaAcademico.SCHEDULING)
        fila=self.s.execute(select(P.id_asignacion,GrupoEstudianteORM.id_estudiante,
            ConvocatoriaModel.estudiante_id.label('uuid_estudiante'))
            .select_from(P).join(GrupoEstudianteORM,GrupoEstudianteORM.id_grupo_estudiante==P.id_grupo_estudiante)
            .join(A,(A.id_asignacion==P.id_asignacion)&(A.id_grupo==GrupoEstudianteORM.id_grupo))
            .join(GrupoAcademicoORM,GrupoAcademicoORM.id_grupo==A.id_grupo)
            .join(S,(S.id==A.sesion_programada_id)&(S.version_caso_id==A.version_caso_id))
            .join(ConvocatoriaModel,(ConvocatoriaModel.id==P.convocatoria_id)&(ConvocatoriaModel.sesion_id==S.id))
            .join(V,V.id==A.version_caso_id).join(C,(C.id==V.caso_id)&(C.id_caso==A.id_caso))
            .where(P.id_participacion==p,GrupoAcademicoORM.id_profesor==u,S.docente_id==scheduling,C.docente_creador_id==cases)
            .with_for_update(of=[P,GrupoEstudianteORM,A,GrupoAcademicoORM,S,ConvocatoriaModel])).one_or_none()
        if fila is None: raise AccesoDenegado()
        self.s.execute(select(IdentidadAcademicaORM).where(
            IdentidadAcademicaORM.id_usuario==fila.id_estudiante).with_for_update(read=True)).all()
        estudiante=resolver.resolver(id_usuario=str(fila.id_estudiante),sistema=SistemaAcademico.SCHEDULING)
        if estudiante!=fila.uuid_estudiante: raise AccesoDenegado()
        return fila

    def puede_consultar_participacion(self,id_docente,id_participacion):
        self.autorizar(id_docente,id_participacion)
        return True


class RepositorioFeedbackIndividual:
    def __init__(self,sesion,usuario): self.s,self.usuario=sesion,usuario
    def agregar(self,feedback):
        if self.s.get_bind().dialect.name!="postgresql":raise IntegracionPendiente()
        fila=AmbitoFeedbackIndividual(self.s,self.usuario).autorizar(feedback.id_docente,feedback.id_participacion)
        # El lock de participación tomado por autorizar serializa también la
        # primera escritura y los reintentos concurrentes del mismo contenido.
        anterior=self.s.scalar(select(F.texto).where(F.id_participacion==id_entero(feedback.id_participacion)))
        stmt=insert(F).values(id_participacion=id_entero(feedback.id_participacion),id_asignacion=fila.id_asignacion,
            id_profesor=id_entero(feedback.id_docente),texto=feedback.texto,
            fecha_registro=feedback.fecha.astimezone(timezone.utc).replace(tzinfo=None))
        stmt=stmt.on_conflict_do_update(index_elements=[F.id_participacion],
            set_=dict(texto=stmt.excluded.texto,fecha_registro=stmt.excluded.fecha_registro),
            where=F.id_profesor==stmt.excluded.id_profesor).returning(F.id_retroalimentacion)
        if self.s.scalar(stmt) is None:raise AccesoDenegado()
        if anterior != feedback.texto:
            convocatoria=self.s.scalar(select(P.convocatoria_id).where(
                P.id_participacion==id_entero(feedback.id_participacion)))
            # Misma Session/UoW: fallo del aviso revierte también el comentario.
            # No usar notificar_calificacion: ni anuncia ni publica una nota.
            crear_notificacion(self.s,destinatario_id=fila.uuid_estudiante,
                convocatoria_id=convocatoria,tipo="RETROALIMENTACION",canal="INTERNA",
                mensaje=(f"El docente registró o actualizó la valoración general de tu participación {feedback.id_participacion}. "
                    "Consulta la plataforma para revisar su disponibilidad."))


def crear_servicio_feedback_individual(*,usuario,crear_sesion):
    return ServicioFeedbackDocente(lambda:UnidadTrabajoIdentitySQLAlchemy(
        usuarios=RepositorioUsuariosSQLAlchemy,academia=lambda s:AmbitoFeedbackIndividual(s,usuario),
        feedback=lambda s:RepositorioFeedbackIndividual(s,usuario),sesiones=crear_sesion))


def consultar_feedback_individual(*,usuario,id_participacion,crear_sesion):
    """Lectura privada reutilizable; un fallo SQL nunca concede acceso."""
    try:
        return _consultar_feedback_individual(usuario=usuario,
            id_participacion=id_participacion,crear_sesion=crear_sesion)
    except SQLAlchemyError:
        raise IntegracionPendiente() from None


def _consultar_feedback_individual(*,usuario,id_participacion,crear_sesion):
    with crear_sesion() as s:
        with s.begin():
            usuarios=RepositorioUsuariosSQLAlchemy(s)
            actual=usuarios.obtener(usuario.id_usuario)
            if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:raise AccesoDenegado()
            fila=s.execute(select(P.convocatoria_id).join(GrupoEstudianteORM,
                GrupoEstudianteORM.id_grupo_estudiante==P.id_grupo_estudiante).where(
                P.id_participacion==id_entero(id_participacion),GrupoEstudianteORM.id_estudiante==id_entero(actual.id_usuario))
                .with_for_update(of=P)).one_or_none()
            if fila is None:raise AccesoDenegado()
            cuenta=s.execute(select(UsuarioORM.id_rol).where(UsuarioORM.id_usuario==id_entero(usuario.id_usuario))
                .with_for_update()).one_or_none()
            if cuenta is None:raise AccesoDenegado()
            s.execute(select(RolORM.id_rol).where(RolORM.id_rol==cuenta.id_rol).with_for_update(read=True)).one()
            actual=usuarios.obtener(usuario.id_usuario)
            if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:raise AccesoDenegado()
            # La participación también serializa el inicio de nuevos intentos y
            # la escritura docente. Leer no crea ni actualiza la valoración.
            s.execute(select(IdentidadAcademicaORM).where(
                IdentidadAcademicaORM.id_usuario==id_entero(actual.id_usuario)).with_for_update(read=True)).all()
            resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s))
            ValidadorConvocatoriaScheduling(s,usuarios,resolver).validar_contexto(id_usuario=actual.id_usuario,
                contexto=usuario.id_convocatoria,solicitada=fila.convocatoria_id)
            estados=s.scalars(select(I.estado).where(I.id_participacion==id_entero(id_participacion))).all()
            if not estados or any(e not in {"FINALIZADO","VENCIDO"} for e in estados):raise AccesoDenegado()
            # No inferir vigencia de ingreso para una consulta histórica. Sí
            # exigir la misma matrícula, asignación, sesión y versión persistidas.
            asignacion=s.scalar(select(A.id_asignacion).select_from(P)
                .join(GrupoEstudianteORM,GrupoEstudianteORM.id_grupo_estudiante==P.id_grupo_estudiante)
                .join(A,(A.id_asignacion==P.id_asignacion)&(A.id_grupo==GrupoEstudianteORM.id_grupo))
                .join(S,(S.id==A.sesion_programada_id)&(S.version_caso_id==A.version_caso_id))
                .join(ConvocatoriaModel,(ConvocatoriaModel.id==P.convocatoria_id)&(ConvocatoriaModel.sesion_id==S.id))
                .join(V,V.id==A.version_caso_id).join(C,(C.id==V.caso_id)&(C.id_caso==A.id_caso))
                .where(P.id_participacion==id_entero(id_participacion)))
            if asignacion is None:raise AccesoDenegado()
            f=s.execute(select(F.__table__).where(F.id_participacion==id_entero(id_participacion),
                F.id_asignacion==asignacion)).mappings().one_or_none()
            if f is None:raise IntegracionPendiente()
            return FeedbackDocente(str(f["id_participacion"]),str(f["id_profesor"]),f["texto"],
                f["fecha_registro"].replace(tzinfo=timezone.utc))
