
"""Servicio para convocar estudiantes a sesiones académicas."""

import secrets
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.scheduling.application.codigos_convocatoria import (
    hash_codigo_numerico,
    huellas_de_consulta,
)
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
    codigo_acceso: str = field(repr=False)


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

    # Serializar la emisión por estudiante, incluso en sesiones distintas.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:clave, 0))"),
            {"clave": f"scheduling.codigo-convocatoria:{estudiante_id}"},
        )

    # Comprobar que el estudiante no esté convocado.
    consulta = select(ConvocatoriaModel).where(
        ConvocatoriaModel.sesion_id == sesion_id,
        ConvocatoriaModel.estudiante_id == estudiante_id,
    )

    existente = db.scalar(consulta)

    if existente is not None:
        raise ErrorConvocatoria(
            "El estudiante ya tiene una convocatoria para esta sesión."
        )

    for _ in range(16):
        codigo_acceso = f"{secrets.randbelow(1_000_000):06d}"
        codigo_hash = hash_codigo_numerico(codigo_acceso, estudiante_id)
        repetido = db.scalar(select(ConvocatoriaModel.id).where(
            ConvocatoriaModel.estudiante_id == estudiante_id,
            ConvocatoriaModel.codigo_hash.in_(huellas_de_consulta(codigo_acceso, estudiante_id)),
        ).limit(1))
        if repetido is None:
            break
    else:
        raise ErrorConvocatoria("No fue posible asignar un código. Inténtalo de nuevo.")

    convocatoria = ConvocatoriaModel(
        sesion_id=sesion_id,
        estudiante_id=estudiante_id,
        codigo_hash=codigo_hash,
        estado="ACTIVA",
    )

    db.add(convocatoria)
    db.flush()

    # El código original se entrega al servicio interno que lo encola para correo.
    return ResultadoConvocatoria(
        convocatoria_id=convocatoria.id,
        codigo_acceso=codigo_acceso,
    )
