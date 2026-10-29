
"""Pruebas de creación de convocatorias y notificaciones."""

from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.scheduling.api.router import (
    obtener_docente_autenticado,
)
from app.modules.scheduling.application.crear_convocatoria import (
    ResultadoConvocatoria,
)


@pytest.fixture
def entorno_api():
    docente_id = uuid4()
    db = Mock()
    db.get.return_value = SimpleNamespace(
        docente_id=docente_id,
    )

    anteriores = app.dependency_overrides.copy()

    app.dependency_overrides[obtener_docente_autenticado] = (
        lambda: docente_id
    )
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


def test_convocatoria_crea_notificacion(entorno_api):
    client, db = entorno_api

    sesion_id = uuid4()
    estudiante_id = uuid4()
    convocatoria_id = uuid4()

    with (
        patch(
            "app.modules.scheduling.api.router.crear_convocatoria"
        ) as crear,
        patch(
            "app.modules.scheduling.api.router.crear_notificacion"
        ) as notificar,
    ):
        crear.return_value = ResultadoConvocatoria(
            convocatoria_id=convocatoria_id,
            codigo_acceso="CODIGO_DE_PRUEBA",
        )

        respuesta = client.post(
            f"/scheduling/sesiones/{sesion_id}/convocatorias",
            json={"estudiante_id": str(estudiante_id)},
        )

        assert respuesta.status_code == 201
        assert respuesta.json()["convocatoria_id"] == str(
            convocatoria_id
        )

        notificar.assert_called_once()
        assert notificar.call_args.kwargs["tipo"] == "CONVOCATORIA"
        assert notificar.call_args.kwargs["canal"] == "INTERNA"
        assert (
            notificar.call_args.kwargs["destinatario_id"]
            == estudiante_id
        )

        db.commit.assert_called_once()
        db.rollback.assert_not_called()


def test_fallo_notificacion_revierte_convocatoria(entorno_api):
    client, db = entorno_api

    with (
        patch(
            "app.modules.scheduling.api.router.crear_convocatoria"
        ) as crear,
        patch(
            "app.modules.scheduling.api.router.crear_notificacion"
        ) as notificar,
    ):
        crear.return_value = ResultadoConvocatoria(
            convocatoria_id=uuid4(),
            codigo_acceso="CODIGO_DE_PRUEBA",
        )

        notificar.side_effect = RuntimeError(
            "Error al registrar notificación"
        )

        respuesta = client.post(
            f"/scheduling/sesiones/{uuid4()}/convocatorias",
            json={"estudiante_id": str(uuid4())},
        )

        assert respuesta.status_code == 500
        db.rollback.assert_called_once()
        db.commit.assert_not_called()
