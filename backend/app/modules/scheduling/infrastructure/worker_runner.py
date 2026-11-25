
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

INTERVALO_SEGUNDOS = 3


def registrar_error(error: Exception) -> None:
    # Las excepciones SQL pueden incluir parámetros y datos académicos. Conservar
    # solo un código operativo y la clase; nunca texto, SQL ni traceback.
    logger.error("REVISION_FALLIDA tipo=%s", type(error).__name__)


async def _cerrar_intentos_vencidos(session_factory) -> int:
    """Cierra intentos activos cuyo tiempo concedido expiró, guarda borradores y calcula nota parcial (RF-23)."""
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    from sqlalchemy import literal_column, select
    from app.core.config import get_settings
    from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
    from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
    from app.modules.participation.api.interactive_router import cerrar_intento_y_evaluar
    from app.modules.participation.infrastructure.codecs import FechasPersistencia
    from app.modules.participation.infrastructure.models import IntentoModel, ParticipacionModel

    settings = get_settings()
    if not settings.participation_timestamp_zone or not settings.participation_timestamp_zone.strip():
        return 0
    try:
        fechas = FechasPersistencia(ZoneInfo(settings.participation_timestamp_zone))
    except (ValueError, ZoneInfoNotFoundError):
        return 0

    ahora_db = fechas.hacia_db(datetime.now(UTC), sin_offset=True)
    with session_factory() as probe:
        if probe.get_bind().dialect.name != "postgresql":
            return 0
        vencimiento = IntentoModel.inicio + (
            IntentoModel.duracion_concedida_segundos * literal_column("INTERVAL '1 second'")
        )
        vencidos_ids = probe.scalars(
            select(IntentoModel.id_intento)
            .where(IntentoModel.estado == literal_column("'EN_CURSO'"), vencimiento <= ahora_db)
            .order_by(vencimiento, IntentoModel.id_intento)
        ).all()

    cerrados = 0
    for id_int in vencidos_ids:
        with session_factory() as db:
            intento = db.get(IntentoModel, id_int)
            if intento is None or intento.estado != "EN_CURSO":
                continue
            part = db.get(ParticipacionModel, intento.id_participacion)
            mat = db.get(GrupoEstudianteORM, part.id_grupo_estudiante) if part else None
            if mat is None:
                continue
            usuario = RepositorioUsuariosSQLAlchemy(db).obtener(str(mat.id_estudiante))
            if usuario is None:
                continue
            cerrar_intento_y_evaluar(
                db,
                intento=intento,
                usuario=usuario,
                fechas=fechas,
                crear_sesion=session_factory,
                forzar_vencido=True,
                permitir_parcial=True,
            )
            cerrados += 1
    return cerrados


async def ejecutar_revision() -> int:
    """Ejecuta una revisión de sesiones vencidas, intentos expirados y correos pendientes."""

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
    intentos_cerrados = await _cerrar_intentos_vencidos(session_factory)
    if intentos_cerrados:
        logger.info("Intentos cerrados por vencimiento: %s", intentos_cerrados)

    try:
        from app.modules.scheduling.infrastructure.mail_delivery import configuracion_correo, despachar_pendientes

        if configuracion_correo() is not None:
            await asyncio.to_thread(despachar_pendientes, session_factory, limite=50, esperar_reintentos=True)
    except Exception as error:
        logger.warning("REVISION_CORREO_FALLIDA tipo=%s", type(error).__name__)

    logger.info("Sesiones cerradas: %s", cerradas)
    return cerradas


async def ejecutar_periodicamente() -> None:
    """Revisa vencimientos y correos pendientes en el intervalo operativo."""

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
