
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
    """Configura efectos SQL atómicos; conserva la firma de API/worker.

    session_factory no se usa para avisos: estos comparten la transacción
    de la transición. No se abre una segunda Session.
    """

    gestor = GestorEventosAcademicos()

    observador = ObservadorNotificaciones()

    # Notificar cuando una sesión comienza.
    gestor.suscribir_transaccional(
        "sesion.iniciada",
        observador,
    )

    # Notificar cuando una sesión finaliza.
    gestor.suscribir_transaccional(
        "sesion.finalizada",
        observador,
    )

    return gestor
