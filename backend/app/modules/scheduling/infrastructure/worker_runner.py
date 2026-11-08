
"""Ejecutor periódico del Worker de cierre de sesiones (RF-19)."""

import asyncio
import argparse
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


def registrar_error(error: Exception) -> None:
    # Las excepciones SQL pueden incluir parámetros y datos académicos. Conservar
    # solo un código operativo y la clase; nunca texto, SQL ni traceback.
    logger.error("REVISION_FALLIDA tipo=%s", type(error).__name__)


async def ejecutar_revision() -> int:
    """Ejecuta una revisión de sesiones vencidas."""

    # Registro compartido antes de cualquier flush: el proceso separado no
    # importa app.main y debe resolver también las FK de publicación.
    from app.db.models import registrar_modelos_integrados
    registrar_modelos_integrados()
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

        except Exception as error:
            registrar_error(error)

        await asyncio.sleep(INTERVALO_SEGUNDOS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Revisar una vez y salir.")
    opciones = parser.parse_args(argv)
    try:
        asyncio.run(ejecutar_revision() if opciones.once else ejecutar_periodicamente())
    except KeyboardInterrupt:
        logger.info("Worker académico detenido")
    except Exception as error:
        registrar_error(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
