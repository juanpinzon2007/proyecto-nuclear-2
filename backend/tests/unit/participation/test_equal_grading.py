"""Fórmula igualitaria: resultados conocidos y precisión sin servicios externos."""

from decimal import Decimal, Inexact, localcontext

import pytest

from app.modules.participation.domain.calculador_rubrica import (
    CalculadorRubrica, FormulaCalculo, PoliticaCalculo,
)
from app.modules.participation.domain.evaluation import (
    CriterioEvaluable, EvaluacionInconsistente, NivelEvaluable, NivelObtenido,
    PoliticaEvaluacionPendiente, ReferenciaAcademica, RubricaEvaluacion,
)


def calcular(logros, *, pesos=None, maxima="100"):
    pesos = pesos or ["1"] * len(logros)
    rubrica = RubricaEvaluacion(ReferenciaAcademica(1, 2, "v1"), Decimal(maxima), tuple(
        CriterioEvaluable(i + 10, Decimal(peso), (NivelEvaluable(i + 100, Decimal(logro)),))
        for i, (logro, peso) in enumerate(zip(logros, pesos))
    ))
    niveles = tuple(NivelObtenido(c.id_criterio, c.niveles[0].id_nivel) for c in rubrica.criterios)
    politica = PoliticaCalculo("igualitaria-unitaria", FormulaCalculo.PROMEDIO_IGUALITARIO_100, None, None)
    return CalculadorRubrica().calcular(rubrica, niveles, politica), rubrica


@pytest.mark.parametrize("logros,pesos,aportes,nota", [
    (["100", "0"], ["90", "10"], ["50", "0"], "50"),
    (["60", "90", "30"], ["10", "20", "70"], ["20", "30", "10"], "60"),
    (["0", "0"], ["0", "0"], ["0", "0"], "0"),
    (["87.654321"], ["17"], ["87.654321"], "87.654321"),
])
def test_promedio_igualitario_conserva_pesos_historicos(logros, pesos, aportes, nota):
    resultado, rubrica = calcular(logros, pesos=pesos)
    assert [r.puntaje_obtenido for r in resultado.criterios] == list(map(Decimal, aportes))
    assert resultado.nota_final == resultado.nota_sin_redondear == Decimal(nota)
    assert [c.peso_porcentaje for c in rubrica.criterios] == list(map(Decimal, pesos))
    assert resultado.politica == "igualitaria-unitaria"


def test_precision_decimal_global_no_redondea_el_promedio():
    with localcontext() as contexto:
        contexto.prec = 2
        contexto.traps[Inexact] = True
        resultado, _ = calcular(["87.654321", "12.345679"])
    assert resultado.nota_final == Decimal("50")
    assert resultado.criterios[0].puntaje_obtenido == Decimal("43.8271605")


@pytest.mark.parametrize("maxima", ["99", "101"])
def test_formula_igualitaria_exige_escala_100(maxima):
    with pytest.raises(EvaluacionInconsistente):
        calcular(["100"], maxima=maxima)


@pytest.mark.parametrize("decimales,redondeo", [(2, None), (None, "ROUND_HALF_UP")])
def test_no_inventa_regla_de_redondeo(decimales, redondeo):
    with pytest.raises(PoliticaEvaluacionPendiente):
        PoliticaCalculo("igualitaria", FormulaCalculo.PROMEDIO_IGUALITARIO_100, decimales, redondeo)


def test_nivel_de_otro_criterio_no_se_acepta():
    _, rubrica = calcular(["80", "60"])
    politica = PoliticaCalculo("igualitaria", FormulaCalculo.PROMEDIO_IGUALITARIO_100, None, None)
    niveles = (NivelObtenido(10, 101), NivelObtenido(11, 100))
    with pytest.raises(EvaluacionInconsistente):
        CalculadorRubrica().calcular(rubrica, niveles, politica)
