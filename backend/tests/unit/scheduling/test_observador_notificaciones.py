
"""Pruebas del observador de notificaciones académicas."""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.scheduling.application.registrar_observadores import (
    crear_gestor_eventos,
)
from app.modules.scheduling.domain.events import EventoAcademico


def preparar_db():
    db = MagicMock()
    db.__enter__.return_value = db

    convocatoria = SimpleNamespace(
        id=uuid4(),
        estudiante_id=uuid4(),
    )

    db.scalars.return_value.all.return_value = [
        convocatoria
    ]

    factory = MagicMock(return_value=db)

    return db, factory, convocatoria


@pytest.mark.parametrize(
    "tipo_evento,tipo_notificacion",
    [
        ("sesion.iniciada", "SESION_INICIADA"),
        ("sesion.finalizada", "SESION_FINALIZADA"),
    ],
)
def test_crear_notificacion_por_evento(
    tipo_evento,
    tipo_notificacion,
):
    db, factory, convocatoria = preparar_db()

    gestor = crear_gestor_eventos(factory)

    evento = EventoAcademico(
        tipo=tipo_evento,
        entidad_id=uuid4(),
    )

    with patch(
        "app.modules.scheduling.infrastructure."
        "observador_notificaciones.crear_notificacion"
    ) as crear:
        asyncio.run(gestor.publicar(evento))

    crear.assert_called_once()

    argumentos = crear.call_args.kwargs

    assert argumentos["tipo"] == tipo_notificacion
    assert argumentos["canal"] == "INTERNA"
    assert argumentos["convocatoria_id"] == convocatoria.id
    assert (
        argumentos["destinatario_id"]
        == convocatoria.estudiante_id
    )

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_ignorar_evento_no_registrado():
    db, factory, _ = preparar_db()

    gestor = crear_gestor_eventos(factory)

    evento = EventoAcademico(
        tipo="sesion.desconocida",
        entidad_id=uuid4(),
    )

    asyncio.run(gestor.publicar(evento))

    factory.assert_not_called()
    db.commit.assert_not_called()


def test_rollback_si_falla_base_datos():
    db, factory, _ = preparar_db()

    db.scalars.side_effect = RuntimeError(
        "Error de base de datos"
    )

    gestor = crear_gestor_eventos(factory)

    evento = EventoAcademico(
        tipo="sesion.iniciada",
        entidad_id=uuid4(),
    )

    with pytest.raises(RuntimeError):
        asyncio.run(gestor.publicar(evento))

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
