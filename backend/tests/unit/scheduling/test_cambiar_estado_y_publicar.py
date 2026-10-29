
"""Pruebas de integración del servicio State + Observer."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.modules.scheduling.application.cambiar_estado_y_publicar import (
    cambiar_estado_y_publicar,
)
from app.modules.scheduling.application.cambiar_estado_sesion import (
    SesionNoEncontradaError,
)
from app.modules.scheduling.domain.events import (
    EventoAcademico,
    GestorEventosAcademicos,
)
from app.modules.scheduling.domain.state import (
    TransicionInvalidaError,
)


def preparar_prueba(estado="SIN_INICIAR"):
    """Prepara los componentes necesarios para cada prueba."""

    db = Mock()

    sesion = SimpleNamespace(
        id=uuid4(),
        estado=estado,
        finalizado_en=None,
    )

    db.get.return_value = sesion

    gestor = GestorEventosAcademicos()
    observador = AsyncMock()

    gestor.suscribir("sesion.iniciada", observador)
    gestor.suscribir("sesion.finalizada", observador)

    return db, sesion, gestor, observador


def test_publicar_evento_al_iniciar():
    db, sesion, gestor, observador = preparar_prueba()

    resultado = asyncio.run(
        cambiar_estado_y_publicar(
            db,
            sesion_id=sesion.id,
            accion="iniciar",
            gestor=gestor,
        )
    )

    assert resultado.estado == "EN_CURSO"
    db.commit.assert_called_once()
    db.rollback.assert_not_called()

    observador.notificar.assert_awaited_once()

    evento = observador.notificar.await_args.args[0]

    assert isinstance(evento, EventoAcademico)
    assert evento.tipo == "sesion.iniciada"
    assert evento.entidad_id == sesion.id


def test_publicar_evento_al_finalizar():
    db, sesion, gestor, observador = preparar_prueba(
        "EN_CURSO"
    )

    resultado = asyncio.run(
        cambiar_estado_y_publicar(
            db,
            sesion_id=sesion.id,
            accion="finalizar",
            gestor=gestor,
            origen="WORKER",
        )
    )

    assert resultado.estado == "FINALIZADO"
    assert resultado.finalizado_en is not None

    db.commit.assert_called_once()
    observador.notificar.assert_awaited_once()

    evento = observador.notificar.await_args.args[0]

    assert evento.tipo == "sesion.finalizada"
    assert evento.entidad_id == sesion.id


def test_no_publicar_transicion_invalida():
    db, sesion, gestor, observador = preparar_prueba()

    with pytest.raises(TransicionInvalidaError):
        asyncio.run(
            cambiar_estado_y_publicar(
                db,
                sesion_id=sesion.id,
                accion="finalizar",
                gestor=gestor,
            )
        )

    assert sesion.estado == "SIN_INICIAR"

    db.commit.assert_not_called()
    db.rollback.assert_called_once()

    observador.notificar.assert_not_awaited()


def test_no_publicar_sesion_inexistente():
    db, sesion, gestor, observador = preparar_prueba()

    db.get.return_value = None

    with pytest.raises(SesionNoEncontradaError):
        asyncio.run(
            cambiar_estado_y_publicar(
                db,
                sesion_id=sesion.id,
                accion="iniciar",
                gestor=gestor,
            )
        )

    db.commit.assert_not_called()
    db.rollback.assert_called_once()

    observador.notificar.assert_not_awaited()


def test_no_publicar_si_falla_commit():
    db, sesion, gestor, observador = preparar_prueba()

    db.commit.side_effect = RuntimeError(
        "Error al confirmar la transaccion"
    )

    with pytest.raises(
        RuntimeError,
        match="Error al confirmar",
    ):
        asyncio.run(
            cambiar_estado_y_publicar(
                db,
                sesion_id=sesion.id,
                accion="iniciar",
                gestor=gestor,
            )
        )

    db.commit.assert_called_once()
    db.rollback.assert_called_once()

    observador.notificar.assert_not_awaited()


def test_error_observador_despues_del_commit():
    db, sesion, gestor, observador = preparar_prueba()

    observador.notificar.side_effect = RuntimeError(
        "Error al enviar notificacion"
    )

    with pytest.raises(
        RuntimeError,
        match="Error al enviar",
    ):
        asyncio.run(
            cambiar_estado_y_publicar(
                db,
                sesion_id=sesion.id,
                accion="iniciar",
                gestor=gestor,
            )
        )

    # El commit ya ocurrio antes del error del observador.
    db.commit.assert_called_once()
    db.rollback.assert_not_called()

    observador.notificar.assert_awaited_once()
