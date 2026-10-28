"""Fixtures en memoria para las pruebas unitarias del dominio de casos."""

import uuid
from decimal import Decimal

import pytest

from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.entities.caso import VersionCaso
from app.modules.cases.domain.validators.base import ValidadorCaso
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion


@pytest.fixture
def constructor() -> ConstructorCaso:
    """Builder limpio, sin estado previo."""
    return ConstructorCaso()


@pytest.fixture
def cadena() -> ValidadorCaso:
    """Cadena de publicación completa."""
    return construir_cadena_publicacion()


@pytest.fixture
def caso_academico(constructor: ConstructorCaso) -> VersionCaso:
    """Versión completamente válida: 2 escenarios, 1 pregunta c/u, rúbrica 60/40 mapeada."""
    constructor.iniciar_datos(
        docente_creador_id=uuid.uuid4(),
        nombre="Conformidad grupal",
        desarrollo_situacional="Desarrollo situacional del caso.",
        contexto_historia="Contexto histórico.",
        tiempo_estimado_min=45,
    )
    # Las valoraciones se declaran por nombre de criterio y se resuelven en construir().
    for orden in (1, 2):
        constructor.agregar_escenario(orden, f"Contexto del escenario {orden}")
        constructor.agregar_pregunta(1, f"Enunciado del escenario {orden}")
        constructor.agregar_opcion_y_justificacion(1, "Opción correcta", True, "Es correcta por X.")
        constructor.asignar_valoracion("Análisis", Decimal(5)).asignar_valoracion(
            "Aplicación", Decimal(5)
        )
        constructor.agregar_opcion_y_justificacion(
            2, "Opción incorrecta", False, "Es incorrecta por Y."
        )
        constructor.asignar_valoracion("Análisis", Decimal(1)).asignar_valoracion(
            "Aplicación", Decimal(0)
        )
    constructor.definir_rubrica("Rúbrica base", "1.0")
    constructor.agregar_criterio("Análisis", Decimal(60)).agregar_nivel(
        "Alto", Decimal(5), "Analiza con profundidad."
    ).agregar_nivel("Bajo", Decimal(1), "Análisis superficial.")
    constructor.agregar_criterio("Aplicación", Decimal(40)).agregar_nivel(
        "Alto", Decimal(5), "Aplica la teoría."
    )
    return constructor.construir()


@pytest.fixture
def caso_sin_escenarios(caso_academico: VersionCaso) -> VersionCaso:
    caso_academico.escenarios.clear()
    return caso_academico


@pytest.fixture
def caso_tiempo_invalido(caso_academico: VersionCaso) -> VersionCaso:
    caso_academico.tiempo_estimado_min = 0
    return caso_academico


@pytest.fixture
def caso_escenario_sin_preguntas(caso_academico: VersionCaso) -> VersionCaso:
    caso_academico.escenarios[1].preguntas.clear()
    return caso_academico


@pytest.fixture
def caso_respuestas_sin_justificacion(caso_academico: VersionCaso) -> VersionCaso:
    caso_academico.escenarios[0].preguntas[0].opciones[1].justificacion = "   "
    return caso_academico


@pytest.fixture
def caso_una_sola_opcion(caso_academico: VersionCaso) -> VersionCaso:
    del caso_academico.escenarios[0].preguntas[0].opciones[1]
    return caso_academico


@pytest.fixture
def caso_rubrica_peso_90(caso_academico: VersionCaso) -> VersionCaso:
    assert caso_academico.rubrica is not None
    caso_academico.rubrica.criterios[0].peso = Decimal(50)  # 50 + 40 = 90
    return caso_academico


@pytest.fixture
def caso_sin_rubrica(caso_academico: VersionCaso) -> VersionCaso:
    caso_academico.rubrica = None
    return caso_academico


@pytest.fixture
def caso_opcion_sin_valoracion(caso_academico: VersionCaso) -> VersionCaso:
    caso_academico.escenarios[0].preguntas[0].opciones[0].valoraciones.clear()
    return caso_academico
