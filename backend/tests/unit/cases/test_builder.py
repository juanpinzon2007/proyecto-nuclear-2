"""Pruebas unitarias del Builder ``ConstructorCaso``."""

import uuid
from decimal import Decimal

import pytest

from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import ErrorConstruccionCaso
from app.modules.cases.domain.entities.caso import VersionCaso


def _iniciar(constructor: ConstructorCaso) -> ConstructorCaso:
    return constructor.iniciar_datos(uuid.uuid4(), "n", "d", "c", 30)


@pytest.mark.parametrize(
    "accion",
    [
        lambda b: b.agregar_escenario(1, "x"),
        lambda b: b.agregar_pregunta(1, "q"),
        lambda b: b.agregar_opcion_y_justificacion(1, "o", True, "j"),
        lambda b: b.asignar_valoracion("c", Decimal(1)),
        lambda b: b.definir_rubrica("r", "1"),
        lambda b: b.agregar_criterio("c", Decimal(100)),
        lambda b: b.agregar_nivel("n", Decimal(1), "d"),
        lambda b: b.construir(),
    ],
    ids=[
        "escenario",
        "pregunta",
        "opcion",
        "valoracion",
        "rubrica",
        "criterio",
        "nivel",
        "construir",
    ],
)
def test_metodos_sin_iniciar_datos_fallan(constructor: ConstructorCaso, accion) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ErrorConstruccionCaso):
        accion(constructor)


def test_pregunta_sin_escenario_falla(constructor: ConstructorCaso) -> None:
    with pytest.raises(ErrorConstruccionCaso, match="agregar_escenario"):
        _iniciar(constructor).agregar_pregunta(1, "q")


def test_opcion_sin_pregunta_falla(constructor: ConstructorCaso) -> None:
    _iniciar(constructor).agregar_escenario(1, "x")
    with pytest.raises(ErrorConstruccionCaso, match="agregar_pregunta"):
        constructor.agregar_opcion_y_justificacion(1, "o", True, "j")


def test_nueva_pregunta_reinicia_cursor_de_opcion(constructor: ConstructorCaso) -> None:
    _iniciar(constructor).agregar_escenario(1, "x").agregar_pregunta(1, "q")
    constructor.agregar_opcion_y_justificacion(1, "o", True, "j")
    constructor.agregar_pregunta(2, "q2")
    with pytest.raises(ErrorConstruccionCaso, match="agregar_opcion"):
        constructor.asignar_valoracion("c", Decimal(1))


def test_criterio_sin_rubrica_falla(constructor: ConstructorCaso) -> None:
    with pytest.raises(ErrorConstruccionCaso, match="definir_rubrica"):
        _iniciar(constructor).agregar_criterio("c", Decimal(100))


def test_nivel_sin_criterio_falla(constructor: ConstructorCaso) -> None:
    _iniciar(constructor).definir_rubrica("r", "1")
    with pytest.raises(ErrorConstruccionCaso, match="agregar_criterio"):
        constructor.agregar_nivel("n", Decimal(1), "d")


def test_ordenes_duplicados_fallan(constructor: ConstructorCaso) -> None:
    _iniciar(constructor).agregar_escenario(1, "x").agregar_pregunta(1, "q")
    constructor.agregar_opcion_y_justificacion(1, "o", True, "j")
    with pytest.raises(ErrorConstruccionCaso):
        constructor.agregar_opcion_y_justificacion(1, "o2", False, "j")
    with pytest.raises(ErrorConstruccionCaso):
        constructor.agregar_pregunta(1, "q2")
    with pytest.raises(ErrorConstruccionCaso):
        constructor.agregar_escenario(1, "x2")


def test_valoracion_a_criterio_inexistente_falla_al_construir(
    constructor: ConstructorCaso,
) -> None:
    _iniciar(constructor).agregar_escenario(1, "x").agregar_pregunta(1, "q")
    constructor.agregar_opcion_y_justificacion(1, "o", True, "j")
    constructor.asignar_valoracion("fantasma", Decimal(1))
    constructor.definir_rubrica("r", "1").agregar_criterio("real", Decimal(100))
    with pytest.raises(ErrorConstruccionCaso, match="fantasma"):
        constructor.construir()


def test_construccion_completa_ensambla_jerarquia(caso_academico: VersionCaso) -> None:
    assert caso_academico.estado is EstadoCaso.BORRADOR
    assert [e.orden for e in caso_academico.escenarios] == [1, 2]
    assert caso_academico.rubrica is not None
    assert caso_academico.rubrica.peso_total == Decimal(100)
    opcion = caso_academico.escenarios[0].preguntas[0].opciones[0]
    assert set(opcion.valoraciones) == {c.id for c in caso_academico.rubrica.criterios}


def test_construir_reinicia_el_builder(constructor: ConstructorCaso) -> None:
    _iniciar(constructor).construir()
    with pytest.raises(ErrorConstruccionCaso):
        constructor.agregar_escenario(1, "x")

