
"""Servicio de notificaciones por calificaciones académicas (RF-27)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scheduling.application.crear_notificacion import (
    crear_notificacion,
)
from app.modules.scheduling.infrastructure.models import (
    NotificacionModel,
)


def notificar_calificacion(
    db: Session,
    *,
    estudiante_id: UUID,
    participacion_id: UUID,
) -> NotificacionModel:
    """
    Registra una notificación cuando una participación
    ha sido calificada.

    Debe ejecutarse dentro de la misma transacción
    que guarda la calificación.
    """

    if not isinstance(estudiante_id, UUID):
        raise ValueError("Identificador de estudiante inválido.")

    if not isinstance(participacion_id, UUID):
        raise ValueError("Identificador de participación inválido.")

    mensaje = (
        "La evaluación de tu participación académica "
        "ya está disponible. Ingresa a la plataforma "
        "para consultar tu calificación y los comentarios "
        "del docente."
    )

    return crear_notificacion(
        db,
        destinatario_id=estudiante_id,
        tipo="CALIFICACION",
        canal="INTERNA",
        mensaje=mensaje,
    )
