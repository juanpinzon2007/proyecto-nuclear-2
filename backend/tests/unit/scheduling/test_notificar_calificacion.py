
"""Pruebas de notificaciones de calificaciones RF-27."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.modules.scheduling.application.notificar_calificacion import (
    notificar_calificacion,
)
from app.modules.scheduling.infrastructure.models import (
    NotificacionModel,
)


def test_notificacion_calificacion_correcta():
    db = Mock()
    estudiante_id = uuid4()
    participacion_id = uuid4()

    resultado = notificar_calificacion(
        db,
        estudiante_id=estudiante_id,
        participacion_id=participacion_id,
    )

    assert isinstance(resultado, NotificacionModel)
    assert resultado.destinatario_id == estudiante_id
    assert resultado.tipo == "CALIFICACION"
    assert resultado.canal == "INTERNA"
    assert resultado.estado == "PENDIENTE"
    assert "calificación" in resultado.mensaje

    db.add.assert_called_once_with(resultado)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_rechazar_identificador_invalido():
    db = Mock()

    with pytest.raises(ValueError):
        notificar_calificacion(
            db,
            estudiante_id="incorrecto",
            participacion_id=uuid4(),
        )

    db.add.assert_not_called()
