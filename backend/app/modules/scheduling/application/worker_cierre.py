"""Worker para cerrar sesiones académicas vencidas (RF-19)."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.scheduling.application.cambiar_estado_y_publicar import (
    cambiar_estado_y_publicar,
)
from app.modules.scheduling.domain.events import (
    GestorEventosAcademicos,
)
from app.modules.scheduling.infrastructure.models import (
    SesionProgramadaModel,
)


async def cerrar_sesiones_vencidas(
    session_factory: Callable[[], Session],
    gestor: GestorEventosAcademicos,
    *,
    ahora: datetime | None = None,
) -> int:
    """Finaliza sesiones EN_CURSO vencidas hace al menos 24 horas."""

    if ahora is None:
        ahora = datetime.now(timezone.utc)

    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("La fecha debe tener zona horaria.")

    limite = ahora - timedelta(hours=24)
    cerradas = 0

    with session_factory() as db:
        # Buscar las sesiones candidatas.
        consulta = (
            select(SesionProgramadaModel.id)
            .where(
                SesionProgramadaModel.estado == "EN_CURSO",
                SesionProgramadaModel.fecha_fin <= limite,
            )
            .order_by(SesionProgramadaModel.fecha_fin)
        )

        sesiones_ids = db.scalars(consulta).all()

        for sesion_id in sesiones_ids:
            # Bloquear y comprobar nuevamente.
            # Así evitamos cerrar una sesión reprogramada.
            sesion = db.get(
                SesionProgramadaModel,
                sesion_id,
                with_for_update=True,
            )

            if sesion is None or sesion.estado != "EN_CURSO":
                db.rollback()
                continue

            fecha_fin = sesion.fecha_fin
            if fecha_fin.tzinfo is None:
                fecha_fin = fecha_fin.replace(tzinfo=timezone.utc)

            if fecha_fin > limite:
                db.rollback()
                continue

            # Reutilizar State, auditoría y Observer.
            await cambiar_estado_y_publicar(
                db,
                sesion_id=sesion_id,
                accion="finalizar",
                origen="WORKER",
                gestor=gestor,
            )

            cerradas += 1

    return cerradas
