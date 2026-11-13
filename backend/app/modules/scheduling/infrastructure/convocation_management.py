"""RF-21: ámbito SQL y avisos atómicos, reutilizando convocatoria/notificación.

Sin commit propio, envío de correo, creación de matrículas ni reactivaciones.
"""
from uuid import UUID

from sqlalchemy import select, text

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G, GrupoEstudianteORM as M
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.participation.infrastructure.models import ParticipacionModel
from app.modules.scheduling.application.cambiar_estado_sesion import SesionNoEncontradaError
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria, ErrorConvocatoria
from app.modules.scheduling.application.crear_notificacion import crear_notificacion
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C, SesionProgramadaModel as S


def _autorizar(db, *, usuario, docente_id, estudiante_id, sesion_id, alta):
    ids = [db.scalar(select(IA.id_usuario).where(IA.sistema=='SCHEDULING',IA.id_academico==v))
           for v in (docente_id,estudiante_id)]
    if any(i is None for i in ids):raise AccesoDenegado()
    # Orden estable de cuentas/roles; después convocatoria/sesión. No tomar
    # sesión primero para luego esperar la cuenta de un inicio en curso.
    cuentas=db.scalars(select(UsuarioORM).where(UsuarioORM.id_usuario.in_(ids))
        .order_by(UsuarioORM.id_usuario).with_for_update(read=True)).all()
    db.scalars(select(RolORM).where(RolORM.id_rol.in_([u.id_rol for u in cuentas]))
        .order_by(RolORM.id_rol).with_for_update(read=True)).all()
    db.scalars(select(IA).where(IA.id_usuario.in_(ids)).order_by(IA.id_usuario,IA.sistema,IA.id_academico)
        .with_for_update(read=True)).all()
    usuarios=RepositorioUsuariosSQLAlchemy(db)
    docente,estudiante=(usuarios.obtener(str(i)) for i in ids)
    if (usuario is None or docente is None or docente.id_usuario!=usuario.id_usuario
        or not docente.activo or Rol.DOCENTE not in docente.roles):raise AccesoDenegado()
    if estudiante is None or (alta and (not estudiante.activo or Rol.ESTUDIANTE not in estudiante.roles)):
        raise AccesoDenegado()
    resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(db))
    if (resolver.resolver(id_usuario=docente.id_usuario,sistema=SistemaAcademico.SCHEDULING)!=docente_id
        or resolver.resolver(id_usuario=estudiante.id_usuario,sistema=SistemaAcademico.SCHEDULING)!=estudiante_id):
        raise AccesoDenegado()
    creador=resolver.resolver(id_usuario=docente.id_usuario,sistema=SistemaAcademico.CASES)
    sesion=db.get(S,sesion_id,populate_existing=True,with_for_update=True)
    if sesion is None:raise SesionNoEncontradaError()
    if sesion.docente_id!=docente_id:raise AccesoDenegado()
    if sesion.estado not in {'SIN_INICIAR','EN_CURSO','FINALIZADO'}:raise IntegracionPendiente()
    if db.scalar(select(A.id_asignacion).where(A.sesion_programada_id==sesion_id).limit(1)) is None:
        raise IntegracionPendiente()  # No inferir el grupo desde espacio_academico.
    ambito=(select(M.id_grupo_estudiante).select_from(A)
        .join(G,G.id_grupo==A.id_grupo).join(M,M.id_grupo==G.id_grupo)
        .join(VersionCasoModel,VersionCasoModel.id==A.version_caso_id)
        .join(CasoModel,(CasoModel.id==VersionCasoModel.caso_id)&(CasoModel.id_caso==A.id_caso))
        .where(A.sesion_programada_id==sesion_id,A.version_caso_id==sesion.version_caso_id,
               G.id_profesor==ids[0],M.id_estudiante==ids[1],CasoModel.docente_creador_id==creador))
    if alta:ambito=ambito.where(M.activo.is_(True))
    if not db.scalars(ambito.with_for_update(read=True,of=[A,G,M])).all():raise AccesoDenegado()
    return sesion


def convocar_con_aviso(db, *, usuario, sesion_id: UUID, estudiante_id: UUID, docente_id: UUID):
    sesion=_autorizar(db,usuario=usuario,docente_id=docente_id,estudiante_id=estudiante_id,sesion_id=sesion_id,alta=True)
    resultado=crear_convocatoria(db,sesion_id=sesion_id,estudiante_id=estudiante_id)
    version=db.get(VersionCasoModel,sesion.version_caso_id)
    mensaje=(f"Has sido convocado al caso {version.nombre}. Inicio: {sesion.fecha_inicio.isoformat()}. "
             f"{sesion.mensaje_personalizado or ''}").strip()
    # Nunca persistir el código en mensaje ni sustituir un envío por un registro
    # CORREO sin proveedor. El despacho opcional conserva el secreto cifrado.
    aviso = crear_notificacion(db,destinatario_id=estudiante_id,convocatoria_id=resultado.convocatoria_id,
        tipo='CONVOCATORIA',canal='INTERNA',mensaje=mensaje)
    from app.modules.scheduling.infrastructure.mail_delivery import encolar_correo
    encolar_correo(db, notificacion=aviso, caso=version.nombre, sesion=sesion, codigo=resultado.codigo_acceso)
    return resultado


def retirar_con_aviso(db, *, usuario, sesion_id: UUID, convocatoria_id: UUID, docente_id: UUID):
    # La misma exclusión de provisión: también serializa la ausencia de P.
    if db.get_bind().dialect.name=='postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:clave,0))'),
            {'clave':'participation.convocatoria:'+str(convocatoria_id)})
    db.scalars(select(ParticipacionModel.id_participacion).where(
        ParticipacionModel.convocatoria_id==convocatoria_id).with_for_update()).all()
    convocatoria=db.get(C,convocatoria_id,populate_existing=True,with_for_update=True)
    if convocatoria is None or convocatoria.sesion_id!=sesion_id:raise AccesoDenegado()
    sesion = _autorizar(db,usuario=usuario,docente_id=docente_id,estudiante_id=convocatoria.estudiante_id,sesion_id=sesion_id,alta=False)
    if convocatoria.estado=='RETIRADA':return convocatoria
    if convocatoria.estado!='ACTIVA':raise ErrorConvocatoria('Estado de convocatoria no reconocido.')
    convocatoria.estado='RETIRADA'
    aviso = crear_notificacion(db,destinatario_id=convocatoria.estudiante_id,convocatoria_id=convocatoria.id,
        tipo='CONVOCATORIA_RETIRADA',canal='INTERNA',
        mensaje='El docente retiró tu autorización para esta sesión académica.')
    from app.modules.scheduling.infrastructure.mail_delivery import encolar_correo
    version = db.get(VersionCasoModel, sesion.version_caso_id)
    encolar_correo(db, notificacion=aviso, caso=version.nombre, sesion=sesion)
    db.flush()
    return convocatoria
