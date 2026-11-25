
"""Pruebas unitarias del servicio de convocatorias RF-20."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.modules.scheduling.application.codigos_convocatoria import (
    coincide_codigo_convocatoria,
)
from app.modules.scheduling.domain.access_codes import hash_codigo
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


def test_codigo_numerico_con_ceros_iniciales_y_huella_protegida(monkeypatch):
    db = preparar_db()
    datos = datos_validos()
    monkeypatch.setattr("app.modules.scheduling.application.crear_convocatoria.secrets.randbelow", lambda _: 7)

    resultado = crear_convocatoria(
        db,
        **datos,
    )

    convocatoria = db.add.call_args.args[0]

    assert isinstance(convocatoria, ConvocatoriaModel)
    assert resultado.codigo_acceso == "000007"
    assert convocatoria.codigo_hash.startswith("v2$")
    assert coincide_codigo_convocatoria("000007", convocatoria.codigo_hash, datos["estudiante_id"])
    assert not coincide_codigo_convocatoria("000008", convocatoria.codigo_hash, datos["estudiante_id"])
    assert not coincide_codigo_convocatoria("000007", convocatoria.codigo_hash, uuid4())
    anterior = "codigo-anterior-de-prueba"
    assert coincide_codigo_convocatoria(anterior, hash_codigo(anterior), datos["estudiante_id"])
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
