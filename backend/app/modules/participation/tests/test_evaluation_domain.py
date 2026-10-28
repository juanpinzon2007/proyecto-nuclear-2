from dataclasses import replace
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from datetime import timedelta

import pytest

from app.modules.participation.application.evaluation_service import seleccionar_estrategia
from app.modules.participation.domain.calculador_rubrica import (
    CalculadorRubrica, FormulaCalculo, PoliticaCalculo,
)
from app.modules.participation.domain.entities import EstadoIntento, Intento
from app.modules.participation.domain.estrategias_evaluacion import (
    EvaluacionAusenciaStrategy, EvaluacionCompletaStrategy, EvaluacionParcialStrategy,
)
from app.modules.participation.domain.evaluation import (
    CALCULO_PENDIENTE, MAPEO_AUSENCIA_PENDIENTE, ContextoEvaluacion,
    CriterioEvaluable, DatosEvaluacion, EvaluacionInconsistente, EvidenciaDecision,
    ModalidadEvaluacion, NivelEvaluable, NivelObtenido, PoliticaEvaluacionPendiente,
    ResultadoCriterio,
)
from app.modules.participation.tests.evaluation_fakes import politica_de_prueba, rubrica_de_prueba
from app.modules.participation.tests.fakes import INICIO, RelojFalso


def contexto(modalidad=ModalidadEvaluacion.COMPLETA, *, completo=True, vencido=False):
    reloj = RelojFalso()
    intento = Intento.iniciar(
        id_intento=10, id_participacion=20, id_consentimiento=30, numero_intento=1,
        tiempo_maximo=timedelta(minutes=10), reloj=reloj,
    )
    intento = intento.registrar_decision(id_paso=40, id_decision=50, id_opcion=60, reloj=reloj)
    if completo:
        intento = intento.registrar_decision(id_paso=41, id_decision=51, id_opcion=63, reloj=reloj)
    if vencido:
        reloj.instante += timedelta(minutes=10)
    intento = intento.finalizar(reloj)
    return ContextoEvaluacion(rubrica_de_prueba().referencia, 20, modalidad, (50, 51), intento)


@pytest.mark.parametrize("modalidad,clase", [
    (ModalidadEvaluacion.COMPLETA, EvaluacionCompletaStrategy),
    (ModalidadEvaluacion.PARCIAL, EvaluacionParcialStrategy),
    (ModalidadEvaluacion.AUSENCIA, EvaluacionAusenciaStrategy),
])
def test_seleccion_de_estrategia(modalidad, clase):
    assert isinstance(seleccionar_estrategia(modalidad), clase)


def test_no_selecciona_por_un_estado_de_ejecucion():
    with pytest.raises(EvaluacionInconsistente):
        seleccionar_estrategia(EstadoIntento.VENCIDO)


def test_completa_prepara_evidencias_sin_calificar_automaticamente():
    datos = EvaluacionCompletaStrategy().preparar(contexto())
    assert [e.id_opcion for e in datos.evidencias] == [60, 63]
    assert datos.nota_final is None
    assert datos.criterios == ()
    assert datos.pendientes == (CALCULO_PENDIENTE,)
    assert not datos.lista_para_persistir


def test_completa_rechaza_respuestas_faltantes():
    with pytest.raises(EvaluacionInconsistente):
        EvaluacionCompletaStrategy().preparar(contexto(completo=False))


def test_completa_no_confunde_vencido_con_finalizado_voluntario():
    with pytest.raises(EvaluacionInconsistente):
        EvaluacionCompletaStrategy().preparar(contexto(vencido=True))


@pytest.mark.parametrize("vencido", [False, True])
def test_parcial_preserva_respuestas_y_no_inventa_ceros(vencido):
    ctx = contexto(ModalidadEvaluacion.PARCIAL, completo=False, vencido=vencido)
    datos = EvaluacionParcialStrategy().preparar(ctx)
    assert datos.modalidad == ModalidadEvaluacion.PARCIAL
    assert datos.evidencias[0].id_opcion == 60
    assert datos.evidencias[1].id_opcion is None
    assert all(e.cero_por_ausencia is None for e in datos.evidencias)
    assert datos.nota_final is None


def test_ausencia_genera_ceros_por_decision_sin_intento_ficticio():
    ctx = ContextoEvaluacion(
        rubrica_de_prueba().referencia, 20, ModalidadEvaluacion.AUSENCIA,
        (50, 51), None, ausencia_confirmada=True,
    )
    datos = EvaluacionAusenciaStrategy().preparar(ctx)
    assert datos.id_intento is None
    assert all(e.id_opcion is None and e.cero_por_ausencia == Decimal(0) for e in datos.evidencias)
    assert MAPEO_AUSENCIA_PENDIENTE in datos.pendientes
    assert not datos.lista_para_persistir


def test_ausencia_rechaza_falta_de_confirmacion():
    ctx = ContextoEvaluacion(rubrica_de_prueba().referencia, 20, ModalidadEvaluacion.AUSENCIA, (50,), None)
    with pytest.raises(EvaluacionInconsistente):
        EvaluacionAusenciaStrategy().preparar(ctx)


def test_ausencia_rechaza_intento_real():
    with pytest.raises(EvaluacionInconsistente):
        EvaluacionAusenciaStrategy().preparar(contexto(ModalidadEvaluacion.AUSENCIA))


@pytest.mark.parametrize("estrategia,modalidad", [
    (EvaluacionCompletaStrategy(), ModalidadEvaluacion.COMPLETA),
    (EvaluacionParcialStrategy(), ModalidadEvaluacion.PARCIAL),
])
def test_rechaza_intentos_en_curso(estrategia, modalidad):
    ctx = contexto(modalidad)
    ctx = replace(ctx, intento=replace(ctx.intento, estado=EstadoIntento.EN_CURSO, fin=None))
    with pytest.raises(EvaluacionInconsistente):
        estrategia.preparar(ctx)


def test_no_acepta_evidencias_fuera_de_la_ruta():
    with pytest.raises(EvaluacionInconsistente):
        EvaluacionCompletaStrategy().preparar(replace(contexto(), decisiones_aplicables=(50,)))


def test_calculo_ponderado_explicito_con_resultado_conocido():
    # Fixture matemática: 5 * .60 * 1 + 5 * .40 * .50 = 4.00.
    calculo = CalculadorRubrica().calcular(
        rubrica_de_prueba(), (NivelObtenido(1, 13), NivelObtenido(2, 24)), politica_de_prueba(),
    )
    assert [c.puntaje_obtenido for c in calculo.criterios] == [Decimal("3"), Decimal("1")]
    assert calculo.nota_sin_redondear == Decimal("4")
    assert calculo.nota_final == Decimal("4.00")


def test_contexto_decimal_global_no_cambia_el_resultado():
    rubrica = replace(rubrica_de_prueba(), nota_maxima=Decimal("7.123456789"))
    with localcontext() as contexto_decimal:
        contexto_decimal.prec = 2
        calculo = CalculadorRubrica().calcular(
            rubrica, (NivelObtenido(1, 13), NivelObtenido(2, 24)), politica_de_prueba(),
        )
    assert calculo.nota_sin_redondear == Decimal("5.6987654312")
    assert calculo.nota_final == Decimal("5.70")


def test_trampas_globales_no_impiden_redondeo_explicito():
    rubrica = replace(rubrica_de_prueba(), nota_maxima=Decimal("2.010"))
    with localcontext() as contexto_decimal:
        contexto_decimal.traps[Inexact] = True
        calculo = CalculadorRubrica().calcular(
            rubrica, (NivelObtenido(1, 14), NivelObtenido(2, 24)), politica_de_prueba(),
        )
    assert calculo.nota_final == Decimal("1.01")


@pytest.mark.parametrize("redondeo,esperado", [
    (ROUND_HALF_UP, "1.01"), (ROUND_HALF_EVEN, "1.00"), (ROUND_DOWN, "1.00"),
])
def test_redondeo_solo_si_se_proporciona_expresamente(redondeo, esperado):
    rubrica = replace(rubrica_de_prueba(), nota_maxima=Decimal("2.010"))
    politica = replace(politica_de_prueba(), redondeo=redondeo)
    calculo = CalculadorRubrica().calcular(
        rubrica, (NivelObtenido(1, 14), NivelObtenido(2, 24)), politica,
    )
    assert calculo.nota_final == Decimal(esperado)


def test_redondeo_que_excede_maximo_se_rechaza_sin_recortar():
    rubrica = replace(rubrica_de_prueba(), nota_maxima=Decimal("1.005"))
    with pytest.raises(EvaluacionInconsistente):
        CalculadorRubrica().calcular(
            rubrica, (NivelObtenido(1, 13), NivelObtenido(2, 23)), politica_de_prueba(),
        )


def test_no_calcula_sin_politica():
    with pytest.raises(PoliticaEvaluacionPendiente):
        CalculadorRubrica().calcular(rubrica_de_prueba(), (), None)


@pytest.mark.parametrize("niveles", [
    (NivelObtenido(1, 13),),
    (NivelObtenido(1, 13), NivelObtenido(1, 14)),
    (NivelObtenido(1, 23), NivelObtenido(2, 24)),
    (NivelObtenido(1, 13), NivelObtenido(9, 24)),
])
def test_rechaza_niveles_incompletos_duplicados_o_ajenos(niveles):
    with pytest.raises(EvaluacionInconsistente):
        CalculadorRubrica().calcular(rubrica_de_prueba(), niveles, politica_de_prueba())


def test_no_normaliza_pesos_erroneos_automaticamente():
    rubrica = rubrica_de_prueba()
    rubrica = replace(rubrica, criterios=(replace(rubrica.criterios[0], peso_porcentaje=Decimal(50)), rubrica.criterios[1]))
    with pytest.raises(EvaluacionInconsistente):
        CalculadorRubrica().calcular(rubrica, (NivelObtenido(1, 13), NivelObtenido(2, 24)), politica_de_prueba())


@pytest.mark.parametrize("valor", [0.1, Decimal("NaN"), Decimal("Infinity"), Decimal("-1"), Decimal("101")])
def test_porcentajes_rechazan_floats_y_valores_invalidos(valor):
    with pytest.raises(EvaluacionInconsistente):
        NivelEvaluable(1, valor)


@pytest.mark.parametrize("cambios", [
    {"redondeo": "NO_DEFINIDO"}, {"decimales": -1}, {"formula": "INVENTADA"}, {"identificador": ""},
])
def test_rechaza_politica_inconsistente(cambios):
    with pytest.raises(EvaluacionInconsistente):
        replace(politica_de_prueba(), **cambios)


def test_no_duplica_criterios_o_niveles_de_rubrica():
    rubrica = rubrica_de_prueba()
    with pytest.raises(EvaluacionInconsistente):
        replace(rubrica, criterios=(rubrica.criterios[0], rubrica.criterios[0]))
    with pytest.raises(EvaluacionInconsistente):
        replace(rubrica.criterios[0], niveles=(NivelEvaluable(13, Decimal(0)), NivelEvaluable(13, Decimal(100))))


def test_datos_no_permiten_notas_sin_criterios_y_politica():
    datos = EvaluacionCompletaStrategy().preparar(contexto())
    with pytest.raises(EvaluacionInconsistente):
        replace(datos, nota_final=Decimal(5), pendientes=())


def test_ceros_por_ausencia_no_se_aplican_a_parciales():
    datos = EvaluacionParcialStrategy().preparar(contexto(ModalidadEvaluacion.PARCIAL, completo=False))
    with pytest.raises(EvaluacionInconsistente):
        replace(datos, evidencias=(EvidenciaDecision(50, None, Decimal(0)),))


def test_contexto_no_mezcla_participaciones():
    with pytest.raises(EvaluacionInconsistente):
        replace(contexto(), id_participacion=999)


def test_datos_no_permiten_resultados_de_criterio_duplicados():
    datos = EvaluacionCompletaStrategy().preparar(contexto())
    criterio = ResultadoCriterio(1, 13, Decimal(3))
    with pytest.raises(EvaluacionInconsistente):
        replace(datos, criterios=(criterio, criterio))
