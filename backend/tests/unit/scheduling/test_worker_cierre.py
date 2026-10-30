
"""Pruebas unitarias del Worker de cierre automático."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.scheduling.application.worker_cierre import (
    cerrar_sesiones_vencidas,
)


AHORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def preparar_db(fecha_fin=None, estado="EN_CURSO"):
    db = MagicMock()
    db.__enter__.return_value = db

    sesion_id = uuid4()

    sesion = SimpleNamespace(
        id=sesion_id,
        estado=estado,
        fecha_fin=fecha_fin or AHORA - timedelta(hours=25),
    )

    db.scalars.return_value.all.return_value = [sesion_id]
    db.get.return_value = sesion

    factory = MagicMock(return_value=db)
    gestor = MagicMock()

    return db, factory, gestor, sesion_id


def test_cerrar_sesion_vencida():
    db, factory, gestor, sesion_id = preparar_db()

    with patch(
        "app.modules.scheduling.application.worker_cierre."
        "cambiar_estado_y_publicar",
        new_callable=AsyncMock,
    ) as cambiar:
        cantidad = asyncio.run(
            cerrar_sesiones_vencidas(
                factory,
                gestor,
                ahora=AHORA,
            )
        )

    assert cantidad == 1

    cambiar.assert_awaited_once_with(
        db,
        sesion_id=sesion_id,
        accion="finalizar",
        origen="WORKER",
        gestor=gestor,
    )

    db.get.assert_called_once()
    db.rollback.assert_not_called()


def test_no_cerrar_sesion_reciente():
    db, factory, gestor, _ = preparar_db(
        fecha_fin=AHORA - timedelta(hours=2)
    )

    with patch(
        "app.modules.scheduling.application.worker_cierre."
        "cambiar_estado_y_publicar",
        new_callable=AsyncMock,
    ) as cambiar:
        cantidad = asyncio.run(
            cerrar_sesiones_vencidas(
                factory, gestor, ahora=AHORA
            )
        )

    assert cantidad == 0
    cambiar.assert_not_awaited()
    db.rollback.assert_called_once()


def test_no_cerrar_sesion_finalizada():
    db, factory, gestor, _ = preparar_db(
        estado="FINALIZADO"
    )

    with patch(
        "app.modules.scheduling.application.worker_cierre."
        "cambiar_estado_y_publicar",
        new_callable=AsyncMock,
    ) as cambiar:
        cantidad = asyncio.run(
            cerrar_sesiones_vencidas(
                factory, gestor, ahora=AHORA
            )
        )

    assert cantidad == 0
    cambiar.assert_not_awaited()


def test_no_cerrar_sesion_reprogramada():
    db, factory, gestor, _ = preparar_db()

    # La consulta inicial encontró la sesión,
    # pero la fecha cambió antes de bloquearla.
    db.get.return_value.fecha_fin = (
        AHORA + timedelta(days=1)
    )

    with patch(
        "app.modules.scheduling.application.worker_cierre."
        "cambiar_estado_y_publicar",
        new_callable=AsyncMock,
    ) as cambiar:
        cantidad = asyncio.run(
            cerrar_sesiones_vencidas(
                factory, gestor, ahora=AHORA
            )
        )

    assert cantidad == 0
    db.rollback.assert_called_once()
    cambiar.assert_not_awaited()


def test_sin_sesiones_pendientes():
    db, factory, gestor, _ = preparar_db()

    db.scalars.return_value.all.return_value = []

    with patch(
        "app.modules.scheduling.application.worker_cierre."
        "cambiar_estado_y_publicar",
        new_callable=AsyncMock,
    ) as cambiar:
        cantidad = asyncio.run(
            cerrar_sesiones_vencidas(
                factory, gestor, ahora=AHORA
            )
        )

    assert cantidad == 0
    cambiar.assert_not_awaited()


def test_rechazar_fecha_sin_zona_horaria():
    db, factory, gestor, _ = preparar_db()

    with pytest.raises(ValueError):
        asyncio.run(
            cerrar_sesiones_vencidas(
                factory,
                gestor,
                ahora=datetime(2026, 11, 10, 12, 0),
            )
        )

    factory.assert_not_called()
