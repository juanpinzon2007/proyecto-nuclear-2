"""Matrícula de ingreso por relaciones persistidas, sin provisión ni escrituras."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel


def exigir_matricula_ingreso(db: Session, *, id_usuario: str, sesion: SesionProgramadaModel) -> None:
    """No inferir grupos desde espacio, UUID ni filas de Participation.

    Sin asignación comprobable o con varias matrículas aplicables se falla
    cerrado: validar ingreso no elige una de ellas ni crea una asociación.
    """
    a, m, c, v = AsignacionCasoModel, GrupoEstudianteORM, CasoModel, VersionCasoModel
    with db.no_autoflush:
        if db.scalar(select(a.id_asignacion).where(a.sesion_programada_id == sesion.id).limit(1)) is None:
            raise IntegracionPendiente()
        filas = db.scalars(select(m.id_grupo_estudiante).select_from(a)
            .join(m, m.id_grupo == a.id_grupo)
            .join(v, v.id == a.version_caso_id)
            .join(c, (c.id == v.caso_id) & (c.id_caso == a.id_caso))
            .where(a.sesion_programada_id == sesion.id,
                   a.version_caso_id == sesion.version_caso_id,
                   m.id_estudiante == id_entero(id_usuario), m.activo.is_(True))).all()
    if not filas:
        raise AccesoDenegado()
    if len(filas) != 1:
        raise IntegracionPendiente()
