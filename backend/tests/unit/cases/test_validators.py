"""Pruebas unitarias de la cadena de validación y de la publicación."""

import uuid

import pytest

from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.entities.caso import VersionCaso
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import CasoInvalidoError
from app.modules.cases.domain.validators.base import ValidadorCaso
from app.modules.cases.domain.validators.eslabones import (
    ValidadorEstructura,
    ValidadorMapeoOpciones,
    ValidadorPreguntas,
    ValidadorRespuestas,
    ValidadorRubrica,
)


def _errores(cadena: ValidadorCaso, version: VersionCaso) -> list[str]:
    return cadena.comprobar(version).errores


def test_caso_valido_publica(caso_academico: VersionCaso, cadena: ValidadorCaso) -> None:
    caso_academico.publicar(cadena)
    assert caso_academico.estado is EstadoCaso.PUBLICADO


def test_caso_valido_sin_errores(caso_academico: VersionCaso, cadena: ValidadorCaso) -> None:
    assert _errores(cadena, caso_academico) == []


def test_estructura_sin_escenarios(
    caso_sin_escenarios: VersionCaso, cadena: ValidadorCaso
) -> None:
    errores = _errores(cadena, caso_sin_escenarios)
    assert "El caso debe tener al menos un escenario." in errores


def test_estructura_tiempo_invalido(
    caso_tiempo_invalido: VersionCaso, cadena: ValidadorCaso
) -> None:
    assert _errores(cadena, caso_tiempo_invalido) == [
        "El tiempo estimado debe ser mayor que 0 minutos."
    ]


def test_preguntas_escenario_vacio(
    caso_escenario_sin_preguntas: VersionCaso, cadena: ValidadorCaso
) -> None:
    assert _errores(cadena, caso_escenario_sin_preguntas) == ["El escenario 2 no tiene preguntas."]


def test_respuestas_sin_justificacion(
    caso_respuestas_sin_justificacion: VersionCaso, cadena: ValidadorCaso
) -> None:
    assert _errores(cadena, caso_respuestas_sin_justificacion) == [
        "(escenario 1, pregunta 1) la opción 2 carece de justificación."
    ]


def test_respuestas_una_sola_opcion(
    caso_una_sola_opcion: VersionCaso, cadena: ValidadorCaso
) -> None:
    errores = _errores(cadena, caso_una_sola_opcion)
    assert "(escenario 1, pregunta 1) requiere al menos 2 opciones." in errores
    assert "(escenario 1, pregunta 1) no tiene opción incorrecta." in errores


def test_rubrica_pesos_90(caso_rubrica_peso_90: VersionCaso, cadena: ValidadorCaso) -> None:
    assert _errores(cadena, caso_rubrica_peso_90) == [
        "Los pesos de la rúbrica suman 90, deben sumar 100."
    ]


def test_rubrica_ausente(caso_sin_rubrica: VersionCaso, cadena: ValidadorCaso) -> None:
    # El mapeo de opciones no duplica el error cuando no hay rúbrica.
    assert _errores(cadena, caso_sin_rubrica) == ["El caso no tiene rúbrica asociada."]


def test_criterio_sin_niveles(caso_academico: VersionCaso, cadena: ValidadorCaso) -> None:
    assert caso_academico.rubrica is not None
    caso_academico.rubrica.criterios[1].niveles.clear()
    assert _errores(cadena, caso_academico) == ["El criterio 'Aplicación' no tiene niveles."]


def test_mapeo_opcion_sin_valoracion(
    caso_opcion_sin_valoracion: VersionCaso, cadena: ValidadorCaso
) -> None:
    assert _errores(cadena, caso_opcion_sin_valoracion) == [
        "(escenario 1, pregunta 1, opción 1) no tiene valoración para el criterio 'Análisis'.",
        "(escenario 1, pregunta 1, opción 1) no tiene valoración para el criterio 'Aplicación'.",
    ]


def test_mapeo_criterio_ajeno(caso_academico: VersionCaso, cadena: ValidadorCaso) -> None:
    caso_academico.escenarios[0].preguntas[0].opciones[0].valoraciones[uuid.uuid4()] = 1  # type: ignore[assignment]
    assert _errores(cadena, caso_academico) == [
        "(escenario 1, pregunta 1, opción 1) valora un criterio que no pertenece a la rúbrica."
    ]


def test_cadena_acumula_errores_de_todos_los_eslabones(
    constructor: ConstructorCaso, cadena: ValidadorCaso
) -> None:
    version = constructor.iniciar_datos(uuid.uuid4(), "n", "d", "c", 0).construir()
    version.escenarios.clear()
    errores = _errores(cadena, version)
    assert errores == [
        "El tiempo estimado debe ser mayor que 0 minutos.",
        "El caso debe tener al menos un escenario.",
        "El caso no tiene rúbrica asociada.",
    ]


def test_publicar_invalido_acumula_y_mantiene_borrador(
    caso_academico: VersionCaso, cadena: ValidadorCaso
) -> None:
    caso_academico.tiempo_estimado_min = -1
    caso_academico.escenarios[1].preguntas.clear()
    caso_academico.escenarios[0].preguntas[0].opciones[0].justificacion = ""
    assert caso_academico.rubrica is not None
    caso_academico.rubrica.criterios[0].peso = 10
    caso_academico.rubrica.criterios[1].niveles.clear()

    with pytest.raises(CasoInvalidoError) as info:
        caso_academico.publicar(cadena)

    assert info.value.errores == [
        "El tiempo estimado debe ser mayor que 0 minutos.",
        "El escenario 2 no tiene preguntas.",
        "(escenario 1, pregunta 1) la opción 1 carece de justificación.",
        "Los pesos de la rúbrica suman 50, deben sumar 100.",
        "El criterio 'Aplicación' no tiene niveles.",
    ]
    assert caso_academico.estado is EstadoCaso.BORRADOR


def test_no_se_republica_una_version_publicada(
    caso_academico: VersionCaso, cadena: ValidadorCaso
) -> None:
    caso_academico.publicar(cadena)
    with pytest.raises(CasoInvalidoError):
        caso_academico.publicar(cadena)


@pytest.mark.parametrize(
    "eslabon",
    [ValidadorEstructura, ValidadorPreguntas, ValidadorRespuestas, ValidadorRubrica,
     ValidadorMapeoOpciones],
)
def test_eslabon_individual_valida_caso_correcto(
    eslabon: type[ValidadorCaso], caso_academico: VersionCaso
) -> None:
    assert eslabon().comprobar(caso_academico).es_valido

