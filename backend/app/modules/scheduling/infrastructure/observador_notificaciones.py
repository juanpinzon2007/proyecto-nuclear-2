
"""Observador de notificaciones de sesiones académicas."""

import asyncio
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.scheduling.application.crear_notificacion import (
    crear_notificacion,
)
from app.modules.scheduling.domain.events import EventoAcademico
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
)


class ObservadorNotificaciones:
    """Registra notificaciones cuando cambia el estado de una sesión."""

    MENSAJES = {
        "sesion.iniciada": (
            "SESION_INICIADA",
            "La sesión académica a la que fuiste convocado "
            "ha comenzado.",
        ),
        "sesion.finalizada": (
            "SESION_FINALIZADA",
            "La sesión académica a la que fuiste convocado "
            "ha finalizado.",
        ),
    }

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    async def notificar(self, evento: EventoAcademico) -> None:
        """Recibe un evento sin bloquear el bucle asíncrono."""

        if evento.tipo not in self.MENSAJES:
            return

        await asyncio.to_thread(self._registrar, evento)

    def _registrar(self, evento: EventoAcademico) -> None:
        """Guarda notificaciones usando una transacción propia."""

        tipo, mensaje = self.MENSAJES[evento.tipo]

        # La sesión de BD se crea dentro del hilo de trabajo.
        with self.session_factory() as db:
            try:
                convocatorias = db.scalars(
                    select(ConvocatoriaModel).where(
                        ConvocatoriaModel.sesion_id
                        == evento.entidad_id,
                        ConvocatoriaModel.estado == "ACTIVA",
                    )
                ).all()

                for convocatoria in convocatorias:
                    crear_notificacion(
                        db,
                        destinatario_id=convocatoria.estudiante_id,
                        convocatoria_id=convocatoria.id,
                        tipo=tipo,
                        canal="INTERNA",
                        mensaje=mensaje,
                    )

                db.commit()

            except Exception:
                db.rollback()
                raise
