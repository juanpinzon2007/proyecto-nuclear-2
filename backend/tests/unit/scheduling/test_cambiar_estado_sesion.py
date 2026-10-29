
"""Pruebas del cambio de estado y auditoría de sesiones."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.modules.scheduling.application.cambiar_estado_sesion import (
    SesionNoEncontradaError,
    cambiar_estado_sesion,
)
from app.modules.scheduling.domain.state import (
    TransicionInvalidaError,
)
from app.modules.scheduling.infrastructure.models import (
    EventoAuditoriaModel,
    SesionProgramadaModel,
)


def crear_db_simulada(estado="SIN_INICIAR"):
    """Prepara una sesión y una base de datos simulada."""

    db = Mock()

    sesion = SimpleNamespace(
        id=uuid4(),
        estado=estado,
        finalizado_en=None,
    )

    db.get.return_value = sesion

    return db, sesion


def test_iniciar_sesion_correctamente():
    db, sesion = crear_db_simulada()

    resultado = cambiar_estado_sesion(
        db,
        sesion_id=sesion.id,
        accion="iniciar",
        origen="DOCENTE",
    )

    assert resultado.estado == "EN_CURSO"
    assert sesion.finalizado_en is None

    db.get.assert_called_once_with(
        SesionProgramadaModel,
        sesion.id,
        with_for_update=True,
    )

    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_registrar_auditoria_al_iniciar():
    db, sesion = crear_db_simulada()

    cambiar_estado_sesion(
        db,
        sesion_id=sesion.id,
        accion="iniciar",
    )

    evento = db.add.call_args.args[0]

    assert isinstance(evento, EventoAuditoriaModel)
    assert evento.sesion_id == sesion.id
    assert evento.tipo == "CAMBIO_ESTADO"
    assert evento.estado_anterior == "SIN_INICIAR"
    assert evento.estado_nuevo == "EN_CURSO"
    assert evento.origen == "DOCENTE"


def test_finalizar_sesion_correctamente():
    db, sesion = crear_db_simulada("EN_CURSO")

    resultado = cambiar_estado_sesion(
        db,
        sesion_id=sesion.id,
        accion="finalizar",
        origen="WORKER",
    )

    assert resultado.estado == "FINALIZADO"
    assert isinstance(resultado.finalizado_en, datetime)
    assert resultado.finalizado_en.tzinfo == timezone.utc

    evento = db.add.call_args.args[0]

    assert evento.estado_anterior == "EN_CURSO"
    assert evento.estado_nuevo == "FINALIZADO"
    assert evento.origen == "WORKER"


def test_rechazar_finalizar_sesion_sin_iniciar():
    db, sesion = crear_db_simulada()

    with pytest.raises(TransicionInvalidaError):
        cambiar_estado_sesion(
            db,
            sesion_id=sesion.id,
            accion="finalizar",
        )

    assert sesion.estado == "SIN_INICIAR"
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_rechazar_cambios_en_sesion_finalizada():
    db, sesion = crear_db_simulada("FINALIZADO")

    with pytest.raises(TransicionInvalidaError):
        cambiar_estado_sesion(
            db,
            sesion_id=sesion.id,
            accion="iniciar",
        )

    assert sesion.estado == "FINALIZADO"
    db.add.assert_not_called()


def test_rechazar_sesion_inexistente():
    db = Mock()
    db.get.return_value = None

    with pytest.raises(SesionNoEncontradaError):
        cambiar_estado_sesion(
            db,
            sesion_id=uuid4(),
            accion="iniciar",
        )

    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_rechazar_origen_invalido():
    db, sesion = crear_db_simulada()

    with pytest.raises(ValueError):
        cambiar_estado_sesion(
            db,
            sesion_id=sesion.id,
            accion="iniciar",
            origen="DESCONOCIDO",
        )

    db.get.assert_not_called()
    db.add.assert_not_called()
