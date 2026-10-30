
"""Pruebas unitarias del servicio de convocatorias RF-20."""

import hashlib
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.modules.scheduling.application.crear_convocatoria import (
    ErrorConvocatoria,
    ResultadoConvocatoria,
    crear_convocatoria,
)
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    SesionProgramadaModel,
)


def preparar_db(estado="SIN_INICIAR"):
    """Simula una sesión académica y su acceso a PostgreSQL."""

    db = Mock()

    db.get.return_value = SimpleNamespace(
        id=uuid4(),
        estado=estado,
    )

    # No existe una convocatoria previa.
    db.scalar.return_value = None

    # Simular la asignación del UUID al ejecutar flush.
    def simular_flush():
        convocatoria = db.add.call_args.args[0]
        convocatoria.id = uuid4()

    db.flush.side_effect = simular_flush

    return db


def datos_validos():
    return {
        "sesion_id": uuid4(),
        "estudiante_id": uuid4(),
    }


def test_crear_convocatoria_correctamente():
    db = preparar_db()
    datos = datos_validos()

    resultado = crear_convocatoria(db, **datos)

    assert isinstance(resultado, ResultadoConvocatoria)
    assert isinstance(resultado.convocatoria_id, UUID)
    assert resultado.codigo_acceso

    db.get.assert_called_once_with(
        SesionProgramadaModel,
        datos["sesion_id"],
    )

    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_guardar_hash_y_no_codigo_original():
    db = preparar_db()

    resultado = crear_convocatoria(
        db,
        **datos_validos(),
    )

    convocatoria = db.add.call_args.args[0]

    hash_esperado = hashlib.sha256(
        resultado.codigo_acceso.encode("utf-8")
    ).hexdigest()

    assert isinstance(convocatoria, ConvocatoriaModel)
    assert convocatoria.codigo_hash == hash_esperado
    assert convocatoria.codigo_hash != resultado.codigo_acceso
    assert convocatoria.estado == "ACTIVA"


def test_rechazar_sesion_inexistente():
    db = preparar_db()
    db.get.return_value = None

    with pytest.raises(
        ErrorConvocatoria,
        match="no existe",
    ):
        crear_convocatoria(db, **datos_validos())

    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize(
    "estado",
    ["EN_CURSO", "FINALIZADO"],
)
def test_rechazar_sesion_no_disponible(estado):
    db = preparar_db(estado)

    with pytest.raises(ErrorConvocatoria):
        crear_convocatoria(db, **datos_validos())

    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_rechazar_convocatoria_duplicada():
    db = preparar_db()

    db.scalar.return_value = SimpleNamespace(
        id=uuid4(),
        estado="ACTIVA",
    )

    with pytest.raises(
        ErrorConvocatoria,
        match="ya tiene una convocatoria",
    ):
        crear_convocatoria(db, **datos_validos())

    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_no_realizar_commit_automaticamente():
    db = preparar_db()

    crear_convocatoria(db, **datos_validos())

    db.add.assert_called_once()
    db.flush.assert_called_once()
    db.commit.assert_not_called()
