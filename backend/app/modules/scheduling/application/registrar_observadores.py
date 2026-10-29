
"""Configuración de observadores académicos."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.modules.scheduling.domain.events import (
    GestorEventosAcademicos,
)
from app.modules.scheduling.infrastructure.observador_notificaciones import (
    ObservadorNotificaciones,
)


def crear_gestor_eventos(
    session_factory: Callable[[], Session],
) -> GestorEventosAcademicos:
    """Configura los observadores de eventos de sesiones."""

    gestor = GestorEventosAcademicos()

    observador = ObservadorNotificaciones(
        session_factory=session_factory,
    )

    # Notificar cuando una sesión comienza.
    gestor.suscribir(
        "sesion.iniciada",
        observador,
    )

    # Notificar cuando una sesión finaliza.
    gestor.suscribir(
        "sesion.finalizada",
        observador,
    )

    return gestor
