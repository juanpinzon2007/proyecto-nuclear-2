"""Pruebas de seguridad de los endpoints de scheduling."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_programar_sesion_sin_autenticacion():
    inicio = datetime.now(timezone.utc) + timedelta(days=1)

    datos = {
        "espacio_academico_id": str(uuid4()),
        "version_caso_id": str(uuid4()),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(hours=2)).isoformat(),
        "tiempo_maximo_minutos": 30,
    }

    respuesta = client.post(
        "/scheduling/sesiones",
        json=datos,
    )

    # La autenticación real aún no está integrada.
    # La API debe rechazar la operación con 503.
    assert respuesta.status_code == 503


def test_cambiar_estado_sin_autenticacion():
    sesion_id = uuid4()

    respuesta = client.post(
        f"/scheduling/sesiones/{sesion_id}/estado",
        json={"accion": "iniciar"},
    )

    assert respuesta.status_code == 503


def test_convocar_estudiante_sin_autenticacion():
    sesion_id = uuid4()

    respuesta = client.post(
        f"/scheduling/sesiones/{sesion_id}/convocatorias",
        json={"estudiante_id": str(uuid4())},
    )

    assert respuesta.status_code == 503


def test_crear_espacio_sin_autenticacion():
    respuesta = client.post(
        "/scheduling/espacios",
        json={"nombre": "Laboratorio de Psicología Social"},
    )

    assert respuesta.status_code == 503


def test_listar_convocatorias_sin_autenticacion():
    sesion_id = uuid4()

    respuesta = client.get(
        f"/scheduling/sesiones/{sesion_id}/convocatorias",
    )

    assert respuesta.status_code == 503


def test_notificar_calificacion_sin_autenticacion():
    respuesta = client.post(
        "/scheduling/calificaciones/notificar",
        json={
            "estudiante_id": str(uuid4()),
            "participacion_id": str(uuid4()),
        },
    )

    assert respuesta.status_code == 503
