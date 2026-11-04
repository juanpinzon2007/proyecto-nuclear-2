
"""Router aislado: delegación y UoW. Avisos reales: aceptación RF-21 PostgreSQL."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.scheduling.api.router import (
    obtener_docente_autenticado,
)
from app.modules.identity.api.dependencies import obtener_docente_actual
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.scheduling.application.crear_convocatoria import (
    ResultadoConvocatoria,
)


@pytest.fixture
def entorno_api():
    docente_id = uuid4()
    db = Mock()
    usuario = ContextoAcceso('7','docente@universidad.test',frozenset({Rol.DOCENTE}))

    anteriores = app.dependency_overrides.copy()

    app.dependency_overrides[obtener_docente_autenticado] = (
        lambda: docente_id
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[obtener_docente_actual] = lambda: usuario

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, db, usuario, docente_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


def test_router_delega_convocatoria_y_aviso_en_una_transaccion(entorno_api):
    client, db, usuario, docente_id = entorno_api

    sesion_id = uuid4()
    estudiante_id = uuid4()
    convocatoria_id = uuid4()

    with patch("app.modules.scheduling.api.router.convocar_con_aviso") as crear:
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

        crear.assert_called_once_with(db,usuario=usuario,sesion_id=sesion_id,
            estudiante_id=estudiante_id,docente_id=docente_id)
        assert respuesta.headers['Cache-Control']=='no-store'

        db.commit.assert_called_once()
        db.rollback.assert_not_called()


def test_fallo_notificacion_revierte_convocatoria(entorno_api):
    client, db, _, _ = entorno_api

    with patch("app.modules.scheduling.api.router.convocar_con_aviso") as crear:
        crear.side_effect = RuntimeError(
            "Error al registrar notificación"
        )

        respuesta = client.post(
            f"/scheduling/sesiones/{uuid4()}/convocatorias",
            json={"estudiante_id": str(uuid4())},
        )

        assert respuesta.status_code == 500
        db.rollback.assert_called_once()
        db.commit.assert_not_called()
