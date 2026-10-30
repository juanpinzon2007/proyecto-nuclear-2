
"""Pruebas unitarias del servicio de notificaciones RF-21."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.modules.scheduling.application.crear_notificacion import (
    ErrorNotificacion,
    crear_notificacion,
)
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    NotificacionModel,
)


def datos_validos():
    return {
        "destinatario_id": uuid4(),
        "tipo": "CONVOCATORIA",
        "canal": "CORREO",
        "mensaje": "Tienes una convocatoria académica.",
        "convocatoria_id": uuid4(),
    }


def preparar_db(estudiante_id):
    db = Mock()
    db.get.return_value = SimpleNamespace(
        estudiante_id=estudiante_id,
    )
    return db


def test_crear_notificacion_correctamente():
    datos = datos_validos()
    db = preparar_db(datos["destinatario_id"])

    resultado = crear_notificacion(db, **datos)

    assert isinstance(resultado, NotificacionModel)
    assert resultado.estado == "PENDIENTE"
    assert resultado.tipo == "CONVOCATORIA"
    assert resultado.canal == "CORREO"
    assert resultado.destinatario_id == datos["destinatario_id"]

    db.get.assert_called_once_with(
        ConvocatoriaModel,
        datos["convocatoria_id"],
    )
    db.add.assert_called_once_with(resultado)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_notificacion_interna_sin_convocatoria():
    db = Mock()

    resultado = crear_notificacion(
        db,
        destinatario_id=uuid4(),
        tipo="SESION_INICIADA",
        canal="INTERNA",
        mensaje="  Tu sesión ha comenzado.  ",
    )

    assert resultado.estado == "PENDIENTE"
    assert resultado.mensaje == "Tu sesión ha comenzado."

    db.get.assert_not_called()
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_rechazar_tipo_invalido():
    datos = datos_validos()
    datos["tipo"] = "DESCONOCIDO"
    db = Mock()

    with pytest.raises(ErrorNotificacion):
        crear_notificacion(db, **datos)

    db.add.assert_not_called()


def test_rechazar_canal_invalido():
    datos = datos_validos()
    datos["canal"] = "MENSAJERIA_DESCONOCIDA"
    db = Mock()

    with pytest.raises(ErrorNotificacion):
        crear_notificacion(db, **datos)

    db.add.assert_not_called()


@pytest.mark.parametrize("mensaje", ["", "   "])
def test_rechazar_mensaje_vacio(mensaje):
    datos = datos_validos()
    datos["mensaje"] = mensaje
    db = Mock()

    with pytest.raises(ErrorNotificacion):
        crear_notificacion(db, **datos)

    db.add.assert_not_called()


def test_convocatoria_es_obligatoria():
    datos = datos_validos()
    datos["convocatoria_id"] = None
    db = Mock()

    with pytest.raises(ErrorNotificacion):
        crear_notificacion(db, **datos)

    db.add.assert_not_called()


def test_rechazar_convocatoria_inexistente():
    datos = datos_validos()
    db = Mock()
    db.get.return_value = None

    with pytest.raises(ErrorNotificacion):
        crear_notificacion(db, **datos)

    db.add.assert_not_called()


def test_rechazar_destinatario_incorrecto():
    datos = datos_validos()
    db = preparar_db(uuid4())

    with pytest.raises(ErrorNotificacion):
        crear_notificacion(db, **datos)

    db.add.assert_not_called()
