
"""Ejecutor periódico del Worker de cierre de sesiones (RF-19)."""

import asyncio
import logging
import sys

from app.db.session import get_session_factory
from app.modules.scheduling.application.registrar_observadores import (
    crear_gestor_eventos,
)
from app.modules.scheduling.application.worker_cierre import (
    cerrar_sesiones_vencidas,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 60


async def ejecutar_revision() -> int:
    """Ejecuta una revisión de sesiones vencidas."""

    session_factory = get_session_factory()
    gestor = crear_gestor_eventos(session_factory)

    cerradas = await cerrar_sesiones_vencidas(
        session_factory=session_factory,
        gestor=gestor,
    )

    logger.info("Sesiones cerradas: %s", cerradas)
    return cerradas


async def ejecutar_periodicamente() -> None:
    """Ejecuta el Worker cada 60 segundos."""

    logger.info("Worker académico iniciado")

    while True:
        try:
            await ejecutar_revision()

        except Exception:
            logger.exception("Error en el Worker académico")

        await asyncio.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    if "--once" in sys.argv:
        asyncio.run(ejecutar_revision())
    else:
        asyncio.run(ejecutar_periodicamente())
