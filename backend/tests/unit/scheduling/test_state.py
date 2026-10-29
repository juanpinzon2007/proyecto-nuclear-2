
import pytest

from app.modules.scheduling.domain.state import (
    transicionar,
    TransicionInvalidaError,
)


def test_iniciar_sesion():
    resultado = transicionar("SIN_INICIAR", "iniciar")
    assert resultado == "EN_CURSO"


def test_finalizar_sesion():
    resultado = transicionar("EN_CURSO", "finalizar")
    assert resultado == "FINALIZADO"


@pytest.mark.parametrize(
    "estado, accion",
    [
        ("SIN_INICIAR", "finalizar"),
        ("EN_CURSO", "iniciar"),
        ("FINALIZADO", "iniciar"),
        ("FINALIZADO", "finalizar"),
    ],
)
def test_transiciones_invalidas(estado, accion):
    with pytest.raises(TransicionInvalidaError):
        transicionar(estado, accion)


def test_estado_desconocido():
    with pytest.raises(TransicionInvalidaError):
        transicionar("DESCONOCIDO", "iniciar")
