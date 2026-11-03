from tests.unit.scheduling.ingress_support import politica_fixture
from app.modules.scheduling.api.dependencies import exigir_contexto_convocatoria
from app.modules.scheduling.api.router import exigir_politica_ingreso_configurada
"""Pruebas unitarias de los endpoints de la API de Scheduling."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.modules.identity.api.academic_dependencies import obtener_estudiante_scheduling
from app.db.session import get_db
from app.main import app
from app.modules.scheduling.api.router import (
    obtener_docente_autenticado,
)
from app.modules.scheduling.application.validar_ingreso import ErrorIngreso
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
    ConvocatoriaModel,
    NotificacionModel,
)


@pytest.fixture
def entorno_docente():
    docente_id = uuid4()
    db = Mock()

    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[obtener_docente_autenticado] = lambda: docente_id
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, db, docente_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


@pytest.fixture
def entorno_publico():
    db = Mock()

    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


@pytest.fixture
def entorno_estudiante(entorno_publico):
    # Fixture de router: autorización sustituida; la suite de seguridad prueba JWT.
    client, db = entorno_publico
    estudiante_id = uuid4()
    app.dependency_overrides[obtener_estudiante_scheduling] = lambda: estudiante_id
    app.dependency_overrides[exigir_politica_ingreso_configurada] = lambda: politica_fixture(15)
    app.dependency_overrides[exigir_contexto_convocatoria] = lambda: None
    yield client, db, estudiante_id


# -------------------------------------------------------------------------
# Espacios Académicos (RF-04 / RF-18)
# -------------------------------------------------------------------------

def test_listar_espacios_vacio(entorno_docente):
    client, db, docente_id = entorno_docente
    db.scalars.return_value.all.return_value = []

    respuesta = client.get("/scheduling/espacios")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listar_espacios_con_datos(entorno_docente):
    client, db, docente_id = entorno_docente
    espacio_id = uuid4()
    espacio = SimpleNamespace(id=espacio_id, nombre="Laboratorio 101")
    db.scalars.return_value.all.return_value = [espacio]

    respuesta = client.get("/scheduling/espacios")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["id"] == str(espacio_id)
    assert datos[0]["nombre"] == "Laboratorio 101"


def test_crear_espacio_autorizado(entorno_docente):
    client, db, _ = entorno_docente

    def simular_refresh(instancia):
        instancia.id = uuid4()

    db.refresh.side_effect = simular_refresh

    respuesta = client.post(
        "/scheduling/espacios",
        json={"nombre": "Cámara de Gesell"},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Cámara de Gesell"
    db.add.assert_called_once()
    db.commit.assert_called_once()


# -------------------------------------------------------------------------
# Sesiones Académicas (RF-18, RF-19)
# -------------------------------------------------------------------------

def test_obtener_sesion_existente(entorno_docente):
    client, db, docente_id = entorno_docente
    sesion_id = uuid4()
    ahora = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
    sesion = SimpleNamespace(
        id=sesion_id,
        espacio_academico_id=uuid4(),
        version_caso_id=uuid4(),
        docente_id=docente_id,
        fecha_inicio=ahora,
        fecha_fin=ahora,
        tiempo_maximo_minutos=40,
        lugar="Aula 3",
        mensaje_personalizado="Bienvenida",
        estado="EN_CURSO",
        finalizado_en=None,
    )
    db.get.return_value = sesion

    respuesta = client.get(f"/scheduling/sesiones/{sesion_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == str(sesion_id)
    assert respuesta.json()["estado"] == "EN_CURSO"


def test_obtener_sesion_inexistente(entorno_docente):
    client, db, docente_id = entorno_docente
    db.get.return_value = None

    respuesta = client.get(f"/scheduling/sesiones/{uuid4()}")
    assert respuesta.status_code == 404
    assert "no encontrada" in respuesta.json()["detail"].lower()


# -------------------------------------------------------------------------
# Convocatorias (RF-20)
# -------------------------------------------------------------------------

def test_listar_convocatorias_autorizado(entorno_docente):
    client, db, docente_id = entorno_docente
    sesion_id = uuid4()
    sesion = SimpleNamespace(id=sesion_id, docente_id=docente_id)
    db.get.return_value = sesion

    convocatoria_id = uuid4()
    estudiante_id = uuid4()
    convocatoria = SimpleNamespace(
        id=convocatoria_id,
        sesion_id=sesion_id,
        estudiante_id=estudiante_id,
        estado="ACTIVA",
    )
    db.scalars.return_value.all.return_value = [convocatoria]

    respuesta = client.get(f"/scheduling/sesiones/{sesion_id}/convocatorias")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["id"] == str(convocatoria_id)
    assert datos[0]["estudiante_id"] == str(estudiante_id)


def test_listar_convocatorias_docente_no_propietario(entorno_docente):
    client, db, _ = entorno_docente
    sesion_id = uuid4()
    sesion = SimpleNamespace(id=sesion_id, docente_id=uuid4())  # Otro docente
    db.get.return_value = sesion

    respuesta = client.get(f"/scheduling/sesiones/{sesion_id}/convocatorias")
    assert respuesta.status_code == 403


# -------------------------------------------------------------------------
# Validación de Ingreso de Estudiantes (RF-22)
# -------------------------------------------------------------------------

def test_validar_ingreso_estudiante_exitoso(entorno_estudiante):
    client, db, estudiante_id = entorno_estudiante

    sesion_id = uuid4()
    ahora = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
    sesion = SimpleNamespace(
        id=sesion_id,
        espacio_academico_id=uuid4(),
        version_caso_id=uuid4(),
        docente_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora,
        tiempo_maximo_minutos=30,
        lugar="Aula 1",
        mensaje_personalizado=None,
        estado="EN_CURSO",
        finalizado_en=None,
    )

    with patch(
        "app.modules.scheduling.api.router.validar_ingreso",
        return_value=sesion,
    ):
        respuesta = client.post(
            "/scheduling/validar-ingreso",
            json={
                "convocatoria_id": str(uuid4()),
                "estudiante_id": str(estudiante_id),
                "codigo_acceso": "codigo_correcto_123",
            },
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == str(sesion_id)
        assert respuesta.json()["estado"] == "EN_CURSO"


def test_validar_ingreso_estudiante_denegado(entorno_estudiante):
    client, db, estudiante_id = entorno_estudiante

    with patch(
        "app.modules.scheduling.api.router.validar_ingreso",
        side_effect=ErrorIngreso("Acceso no autorizado."),
    ):
        respuesta = client.post(
            "/scheduling/validar-ingreso",
            json={
                "convocatoria_id": str(uuid4()),
                "estudiante_id": str(estudiante_id),
                "codigo_acceso": "codigo_incorrecto",
            },
        )
        assert respuesta.status_code == 403
        assert "Acceso no autorizado" in respuesta.json()["detail"]


# -------------------------------------------------------------------------
# Notificaciones (RF-21, RF-27)
# -------------------------------------------------------------------------

def test_listar_notificaciones_estudiante(entorno_estudiante):
    client, db, estudiante_id = entorno_estudiante
    destinatario_id = estudiante_id
    notif = SimpleNamespace(
        id=uuid4(),
        convocatoria_id=uuid4(),
        destinatario_id=destinatario_id,
        tipo="CONVOCATORIA",
        canal="INTERNA",
        mensaje="Tienes una convocatoria académica.",
        estado="PENDIENTE",
        creada_en=datetime.now(timezone.utc),
    )
    db.scalars.return_value.all.return_value = [notif]

    respuesta = client.get(f"/scheduling/notificaciones?destinatario_id={destinatario_id}")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["destinatario_id"] == str(destinatario_id)
    assert datos[0]["tipo"] == "CONVOCATORIA"


def test_notificar_calificacion_autorizado(entorno_docente):
    client, db, _ = entorno_docente
    estudiante_id = uuid4()
    participacion_id = uuid4()

    notif = SimpleNamespace(
        id=uuid4(),
        convocatoria_id=None,
        destinatario_id=estudiante_id,
        tipo="CALIFICACION",
        canal="INTERNA",
        mensaje="La evaluación de tu participación académica ya está disponible.",
        estado="PENDIENTE",
        creada_en=datetime.now(timezone.utc),
    )

    with patch(
        "app.modules.scheduling.api.router.notificar_calificacion",
        return_value=notif,
    ):
        respuesta = client.post(
            "/scheduling/calificaciones/notificar",
            json={
                "estudiante_id": str(estudiante_id),
                "participacion_id": str(participacion_id),
            },
        )
        assert respuesta.status_code == 201
        assert respuesta.json()["tipo"] == "CALIFICACION"
        assert respuesta.json()["destinatario_id"] == str(estudiante_id)
        db.commit.assert_called_once()
