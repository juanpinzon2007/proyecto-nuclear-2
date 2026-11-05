
"""Servicio para cambiar el estado de una sesión académica."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scheduling.domain.state import transicionar
from app.modules.scheduling.infrastructure.models import (
    SesionProgramadaModel,
    EventoAuditoriaModel,
)


class SesionNoEncontradaError(Exception):
    """Se intenta modificar una sesión inexistente."""
    pass


def cambiar_estado_sesion(
    db: Session,
    *,
    sesion_id: UUID,
    accion: str,
    origen: str = "DOCENTE",
) -> SesionProgramadaModel:
    """Cambia el estado y registra la auditoría."""

    if origen not in {"DOCENTE", "WORKER", "SISTEMA"}:
        raise ValueError("Origen de cambio de estado no válido.")

    # El lock serializa escritores; populate_existing evita que State use
    # atributos antiguos de una instancia ya presente en el identity map.
    sesion = db.get(
        SesionProgramadaModel,
        sesion_id,
        with_for_update=True,
        populate_existing=True,
    )

    if sesion is None:
        raise SesionNoEncontradaError(
            f"No existe la sesión {sesion_id}"
        )

    estado_anterior = sesion.estado

    # Validar el cambio utilizando el patrón State
    estado_nuevo = transicionar(
        estado_actual=estado_anterior,
        accion=accion,
    )

    # Actualizar el estado
    sesion.estado = estado_nuevo

    # Registrar la fecha de finalización
    if estado_nuevo == "FINALIZADO":
        sesion.finalizado_en = datetime.now(timezone.utc)

    # Crear un registro de auditoría
    evento = EventoAuditoriaModel(
        sesion_id=sesion.id,
        tipo="CAMBIO_ESTADO",
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        origen=origen,
        descripcion=f"Acción ejecutada: {accion}",
    )

    db.add(evento)
    db.flush()

    return sesion
