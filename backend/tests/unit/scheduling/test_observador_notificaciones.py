
"""Pruebas del observador de notificaciones académicas."""

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

    db.get.return_value = SimpleNamespace(estado="EN_CURSO")
    db.scalar.side_effect = [1, None]
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

    db.get.return_value.estado = {"sesion.iniciada": "EN_CURSO", "sesion.finalizada": "FINALIZADO"}[tipo_evento]
    with patch(
        "app.modules.scheduling.infrastructure."
        "observador_notificaciones.crear_notificacion"
    ) as crear:
        gestor.preparar(evento, db)

    crear.assert_called_once()

    argumentos = crear.call_args.kwargs

    assert argumentos["tipo"] == tipo_notificacion
    assert argumentos["canal"] == "INTERNA"
    assert argumentos["convocatoria_id"] == convocatoria.id
    assert (
        argumentos["destinatario_id"]
        == convocatoria.estudiante_id
    )

    factory.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_ignorar_evento_no_registrado():
    db, factory, _ = preparar_db()

    gestor = crear_gestor_eventos(factory)

    evento = EventoAcademico(
        tipo="sesion.desconocida",
        entidad_id=uuid4(),
    )

    gestor.preparar(evento, db)

    factory.assert_not_called()
    db.commit.assert_not_called()


def test_fallo_se_propaga_sin_commit_ni_rollback_del_observador():
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
        gestor.preparar(evento, db)

    db.rollback.assert_not_called()
    db.commit.assert_not_called()
