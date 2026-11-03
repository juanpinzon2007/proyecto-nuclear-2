"""Consulta interna mínima; no es un endpoint ni autoriza acceso estudiantil.

El consumidor debe verificar la convocatoria y tomar version_id de Scheduling.
Solo devuelve referencias de versión y de su rúbrica; no contenido docente,
opciones, corrección, criterios, niveles ni valoraciones.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import CasoModel, RubricaModel, VersionCasoModel


@dataclass(frozen=True)
class ReferenciaVersionPublicada:
    caso_id: UUID
    version_id: UUID
    numero: int
    rubrica_id: UUID
    version_regla: str


class ConsultaVersionPublicada(Protocol):
    def __call__(self, db: Session, *, version_id: UUID) -> ReferenciaVersionPublicada:
        """Lee exclusivamente la versión publicada solicitada y su rúbrica propia.

        Usa la Session del llamador sin autoflush, escrituras, commit ni cierre.
        Rechaza referencias ausentes/no publicadas/sin rúbrica mediante
        CasoNoEncontradoError; no sustituye por otra versión ni autoriza ingreso.
        """
        ...


def consultar_version_publicada(db: Session, *, version_id: UUID) -> ReferenciaVersionPublicada:
    """Lee la versión exacta y su rúbrica, sin elegir las últimas ni hacer commit.

    PUBLICADO sin rúbrica asociada no proporciona una referencia utilizable.
    No ejecuta el cálculo ni interpreta version_regla como política aprobada.
    """
    with db.no_autoflush:
        fila = db.execute(select(
            VersionCasoModel.caso_id, VersionCasoModel.id, VersionCasoModel.numero,
            RubricaModel.id, RubricaModel.version_regla,
        ).select_from(VersionCasoModel).join(CasoModel, CasoModel.id == VersionCasoModel.caso_id).join(
            RubricaModel, RubricaModel.version_caso_id == VersionCasoModel.id,
        ).where(
            VersionCasoModel.id == version_id, VersionCasoModel.estado == EstadoCaso.PUBLICADO,
        )).one_or_none()
    if fila is None:
        raise CasoNoEncontradoError("La versión asignada no está disponible para el ingreso.")
    return ReferenciaVersionPublicada(
        caso_id=fila[0], version_id=fila[1], numero=fila[2],
        rubrica_id=fila[3], version_regla=fila[4],
    )
