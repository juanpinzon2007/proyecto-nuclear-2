"""Selección RF-04 sobre relaciones existentes, dentro de la UoW de programación.

No concede matrícula, permisos de espacio ni admisión. El llamador conserva
commit/rollback y aporta una política explícita para los timestamps históricos.
"""
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G, GrupoEstudianteORM as M
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.scheduling.application.programar_sesion import ErrorProgramacion
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.convocation_management import convocar_con_aviso
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel


@dataclass(frozen=True)
class ConvocatoriaAsignada:
    convocatoria_id: UUID
    estudiante_id: UUID
    codigo_acceso: str = field(repr=False)


@dataclass(frozen=True)
class ProgramacionAcademicaPersistida:
    sesion: SesionProgramadaModel
    id_asignacion: int
    convocatorias: tuple[ConvocatoriaAsignada, ...]


def validar_seleccion(db, *, usuario, grupo_id, estudiantes_ids):
    """Congela cuentas, vínculos y matrículas antes de escribir la sesión."""
    vinculos = db.execute(select(IA.id_usuario, IA.id_academico).where(
        IA.sistema == 'SCHEDULING', IA.id_academico.in_(estudiantes_ids))
        .order_by(IA.id_usuario, IA.id_academico)).all()
    ids = [v.id_usuario for v in vinculos]
    if len(ids) != len(estudiantes_ids) or len(set(ids)) != len(ids):
        raise AccesoDenegado()
    cuentas = db.scalars(select(U).where(U.id_usuario.in_([id_entero(usuario.id_usuario), *ids]))
        .order_by(U.id_usuario).with_for_update(read=True)
        .execution_options(populate_existing=True)).all()
    db.scalars(select(RolORM).where(RolORM.id_rol.in_([u.id_rol for u in cuentas]))
        .order_by(RolORM.id_rol).with_for_update(read=True)
        .execution_options(populate_existing=True)).all()
    db.scalars(select(IA).where(IA.id_usuario.in_(ids))
        .order_by(IA.id_usuario, IA.sistema, IA.id_academico).with_for_update(read=True)).all()
    usuarios = RepositorioUsuariosSQLAlchemy(db)
    resolver = ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(db))
    for id_usuario, esperado in vinculos:
        actual = usuarios.obtener(str(id_usuario))
        if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
            raise AccesoDenegado()
        if resolver.resolver(id_usuario=actual.id_usuario, sistema=SistemaAcademico.SCHEDULING) != esperado:
            raise AccesoDenegado()
    grupo = db.scalar(select(G).where(G.id_grupo == grupo_id).with_for_update(read=True))
    if grupo is None or grupo.id_profesor != id_entero(usuario.id_usuario):
        raise AccesoDenegado()
    matriculados = db.scalars(select(M.id_estudiante).where(
        M.id_grupo == grupo_id, M.id_estudiante.in_(ids), M.activo.is_(True))
        .order_by(M.id_estudiante).with_for_update(read=True)).all()
    if set(matriculados) != set(ids):
        raise AccesoDenegado()


def asignar_y_convocar(db, *, sesion, usuario, grupo_id, estudiantes_ids, fecha_limite_ingreso, fechas):
    if fechas is None:
        raise IntegracionPendiente()
    if (fecha_limite_ingreso.utcoffset() is None
        or not sesion.fecha_inicio <= fecha_limite_ingreso <= sesion.fecha_fin):
        raise ErrorProgramacion('Fecha límite de ingreso inválida.')
    version = db.get(VersionCasoModel, sesion.version_caso_id)
    caso = db.get(CasoModel, version.caso_id)
    if caso.id_caso is None:
        raise IntegracionPendiente()
    asignacion = AsignacionCasoModel(id_grupo=grupo_id, id_caso=caso.id_caso,
        sesion_programada_id=sesion.id, version_caso_id=sesion.version_caso_id,
        apertura=fechas.hacia_db(sesion.fecha_inicio, sin_offset=True),
        cierre=fechas.hacia_db(sesion.fecha_fin, sin_offset=True),
        fecha_limite_ingreso=fechas.hacia_db(fecha_limite_ingreso, sin_offset=True),
        intentos_base=1, estado='programada', tiempo_maximo_min=sesion.tiempo_maximo_minutos)
    db.add(asignacion)
    db.flush()
    convocatorias = []
    for estudiante_id in sorted(estudiantes_ids):
        resultado = convocar_con_aviso(db, usuario=usuario, sesion_id=sesion.id,
            estudiante_id=estudiante_id, docente_id=sesion.docente_id)
        convocatorias.append(ConvocatoriaAsignada(
            resultado.convocatoria_id, estudiante_id, resultado.codigo_acceso,
        ))
    return ProgramacionAcademicaPersistida(sesion, asignacion.id_asignacion, tuple(convocatorias))
