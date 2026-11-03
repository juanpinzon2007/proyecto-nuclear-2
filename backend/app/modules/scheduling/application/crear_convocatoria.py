
"""Servicio para convocar estudiantes a sesiones académicas."""

import secrets
from app.modules.scheduling.domain.access_codes import hash_codigo

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    SesionProgramadaModel,
)


class ErrorConvocatoria(ValueError):
    """Error al crear una convocatoria."""
    pass


@dataclass(frozen=True)
class ResultadoConvocatoria:
    convocatoria_id: UUID
    codigo_acceso: str


def crear_convocatoria(
    db: Session,
    *,
    sesion_id: UUID,
    estudiante_id: UUID,
) -> ResultadoConvocatoria:
    """Crea una convocatoria y genera su código de acceso."""

    # 1. Comprobar que la sesión existe.
    sesion = db.get(SesionProgramadaModel, sesion_id)

    if sesion is None:
        raise ErrorConvocatoria(
            "La sesión académica no existe."
        )

    # 2. Solo convocar a sesiones que no han iniciado.
    if sesion.estado != "SIN_INICIAR":
        raise ErrorConvocatoria(
            "No se puede convocar a una sesión iniciada o finalizada."
        )

    # 3. Comprobar que el estudiante no esté convocado.
    consulta = select(ConvocatoriaModel).where(
        ConvocatoriaModel.sesion_id == sesion_id,
        ConvocatoriaModel.estudiante_id == estudiante_id,
    )

    existente = db.scalar(consulta)

    if existente is not None:
        raise ErrorConvocatoria(
            "El estudiante ya tiene una convocatoria para esta sesión."
        )

    # 4. Generar un código de acceso aleatorio.
    codigo_acceso = secrets.token_urlsafe(32)

    # 5. Guardar únicamente el hash del código.
    codigo_hash = hash_codigo(codigo_acceso)

    # 6. Crear la convocatoria.
    convocatoria = ConvocatoriaModel(
        sesion_id=sesion_id,
        estudiante_id=estudiante_id,
        codigo_hash=codigo_hash,
        estado="ACTIVA",
    )

    db.add(convocatoria)
    db.flush()

    # El código original se devuelve una sola vez.
    return ResultadoConvocatoria(
        convocatoria_id=convocatoria.id,
        codigo_acceso=codigo_acceso,
    )
