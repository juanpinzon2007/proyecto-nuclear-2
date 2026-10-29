from uuid import uuid4
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.modules.scheduling.domain.events import (
    EventoAcademico,
    GestorEventosAcademicos,
)


def test_observer_recibe_evento():
    gestor = GestorEventosAcademicos()
    observador = AsyncMock()

    gestor.suscribir("sesion.programada", observador)

    evento = EventoAcademico(
        tipo="sesion.programada",
        entidad_id=1,
    )

    asyncio.run(gestor.publicar(evento))

    observador.notificar.assert_awaited_once_with(evento)


def test_evento_sin_observadores():
    gestor = GestorEventosAcademicos()

    evento = EventoAcademico(
        tipo="sesion.finalizada",
        entidad_id=uuid4(),
    )

    asyncio.run(gestor.publicar(evento))


def test_varios_observadores_reciben_evento():
    gestor = GestorEventosAcademicos()

    observador_correo = AsyncMock()
    observador_auditoria = AsyncMock()

    gestor.suscribir(
        "sesion.programada", observador_correo
    )
    gestor.suscribir(
        "sesion.programada", observador_auditoria
    )

    evento = EventoAcademico(
        tipo="sesion.programada",
        entidad_id=uuid4(),
    )

    asyncio.run(gestor.publicar(evento))

    observador_correo.notificar.assert_awaited_once()
    observador_auditoria.notificar.assert_awaited_once()


def test_observer_no_recibe_evento_diferente():
    gestor = GestorEventosAcademicos()
    observador = AsyncMock()

    gestor.suscribir("sesion.programada", observador)

    evento = EventoAcademico(
        tipo="sesion.finalizada",
        entidad_id=uuid4(),
    )

    asyncio.run(gestor.publicar(evento))

    observador.notificar.assert_not_awaited()


def test_error_del_observador_se_propaga():
    gestor = GestorEventosAcademicos()
    observador = AsyncMock()

    observador.notificar.side_effect = RuntimeError(
        "Error en el observador"
    )

    gestor.suscribir("sesion.programada", observador)

    evento = EventoAcademico(
        tipo="sesion.programada",
        entidad_id=uuid4(),
    )

    with pytest.raises(RuntimeError):
        asyncio.run(gestor.publicar(evento))
