"""Composición RF-18/RF-04 con versión exacta y UoW del llamador."""
from sqlalchemy import select

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.cases.infrastructure.models import VersionCasoModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.scheduling.application.programar_sesion import programar_sesion, ErrorProgramacion
from app.modules.scheduling.application.programming_access import AutorizacionEspacioProgramacion
from app.modules.scheduling.infrastructure.models import DocenteEspacioAcademicoModel


class AutorizacionEspacioSQLAlchemy:
    def __init__(self, db):self.db=db

    def autorizar(self, *, id_usuario, id_espacio):
        permiso=self.db.scalar(select(DocenteEspacioAcademicoModel.id_docente).where(
            DocenteEspacioAcademicoModel.id_docente==id_entero(id_usuario),
            DocenteEspacioAcademicoModel.espacio_academico_id==id_espacio).with_for_update(read=True))
        if permiso is None:raise AccesoDenegado()


def programar_sesion_autorizada(db, *, usuario, docente_id,
                              autorizacion_espacio: AutorizacionEspacioProgramacion | None,
                              grupo_id=None, estudiantes_ids=None, fecha_limite_ingreso=None,
                              fechas_asignacion=None, **datos):
    # Reutiliza la relectura escritora que estabiliza y refresca cuenta y rol,
    # incluso si la Session conserva entidades ORM de una consulta anterior.
    actual=RepositorioUsuariosSQLAlchemy(db).obtener_para_escritura(usuario.id_usuario)
    if actual is None or not actual.activo or Rol.DOCENTE not in actual.roles:raise AccesoDenegado()
    db.scalars(select(IdentidadAcademicaORM).where(
        IdentidadAcademicaORM.id_usuario==id_entero(actual.id_usuario))
        .order_by(IdentidadAcademicaORM.sistema,IdentidadAcademicaORM.id_academico)
        .with_for_update(read=True)).all()
    resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(db))
    scheduling=resolver.resolver(id_usuario=actual.id_usuario,sistema=SistemaAcademico.SCHEDULING)
    cases=resolver.resolver(id_usuario=actual.id_usuario,sistema=SistemaAcademico.CASES)
    if scheduling!=docente_id:raise AccesoDenegado()
    if any(valor is not None for valor in (grupo_id, estudiantes_ids, fecha_limite_ingreso)):
        if grupo_id is None or not estudiantes_ids or fecha_limite_ingreso is None:
            raise ErrorProgramacion('La selección académica está incompleta.')
        if len(set(estudiantes_ids)) != len(estudiantes_ids):
            raise ErrorProgramacion('La selección contiene estudiantes duplicados.')
        from app.modules.scheduling.infrastructure.academic_assignment import validar_seleccion
        validar_seleccion(db, usuario=actual, grupo_id=grupo_id, estudiantes_ids=estudiantes_ids)
    # Mismo lock raíz que publicación/archivo y programar_sesion. La consulta de
    # autoría reutiliza el repositorio de Cases, nunca compara los dos UUID personales.
    version=db.get(VersionCasoModel,datos['version_caso_id'],populate_existing=True,with_for_update=True)
    if version is None:raise ErrorProgramacion('La version del caso no existe.')
    if CasoRepository(db).obtener_version(version.id,cases) is None:raise AccesoDenegado()
    if autorizacion_espacio is None:raise IntegracionPendiente()
    if autorizacion_espacio.autorizar(id_usuario=actual.id_usuario,id_espacio=datos['espacio_academico_id']) is not None:
        raise IntegracionPendiente()
    sesion = programar_sesion(db,docente_id=scheduling,**datos)
    if grupo_id is not None:
        from app.modules.scheduling.infrastructure.academic_assignment import asignar_y_convocar
        return asignar_y_convocar(db, sesion=sesion, usuario=actual, grupo_id=grupo_id,
            estudiantes_ids=estudiantes_ids, fecha_limite_ingreso=fecha_limite_ingreso, fechas=fechas_asignacion)
    return sesion
