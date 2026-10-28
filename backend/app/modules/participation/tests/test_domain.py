from dataclasses import FrozenInstanceError, dataclass, replace
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.participation.domain.entities import (
    EstadoIntento,
    Intento,
    Participacion,
)
from app.modules.participation.domain.errors import (
    ErrorDominioParticipacion,
    IntentoNoEditable,
)

INICIO = datetime(2026, 10, 27, 15, tzinfo=timezone.utc)
DURACION = timedelta(minutes=10)


@dataclass
class RelojFijo:
    instante: datetime = INICIO

    def ahora(self) -> datetime:
        return self.instante


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def intento(reloj: RelojFijo) -> Intento:
    return Intento.iniciar(
        id_intento=10,
        id_participacion=20,
        id_consentimiento=30,
        numero_intento=1,
        tiempo_maximo=DURACION,
        reloj=reloj,
    )


def con_respuesta(intento: Intento, reloj: RelojFijo) -> Intento:
    return intento.registrar_decision(
        id_paso=40, id_decision=50, id_opcion=60, reloj=reloj
    )


def test_participacion_separa_asignacion_estudiante_e_intentos() -> None:
    participacion = Participacion(20, 100, 200, "REGISTRADA", INICIO)
    assert participacion.id_asignacion == 100
    assert participacion.id_grupo_estudiante == 200
    assert not hasattr(participacion, "nota_final")


def test_inicio_usa_reloj_inyectado_y_no_crea_respuestas(intento: Intento) -> None:
    assert intento.inicio == INICIO
    assert intento.vence_en == INICIO + DURACION
    assert intento.estado == EstadoIntento.EN_CURSO
    assert intento.fin is None
    assert intento.pasos == ()


def test_inicio_normaliza_zona_horaria() -> None:
    local = INICIO.astimezone(timezone(timedelta(hours=-5)))
    actual = Intento.iniciar(
        id_intento=10, id_participacion=20, id_consentimiento=30,
        numero_intento=1, tiempo_maximo=DURACION, reloj=RelojFijo(local),
    )
    assert actual.inicio == INICIO
    assert actual.inicio.tzinfo == timezone.utc


@pytest.mark.parametrize("valor", [0, -1, True, "10", 1.5])
def test_rechaza_identificador_invalido(intento: Intento, valor: object) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, id_intento=valor)


@pytest.mark.parametrize("campo", ["numero_intento", "id_participacion", "id_consentimiento", "id_permiso_extra"])
def test_valida_referencias_y_numero(intento: Intento, campo: str) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, **{campo: 0})


@pytest.mark.parametrize("duracion", [timedelta(0), timedelta(seconds=-1)])
def test_rechaza_duracion_no_positiva(intento: Intento, duracion: timedelta) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, tiempo_maximo=duracion)


def test_rechaza_fechas_sin_zona(intento: Intento) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, inicio=INICIO.replace(tzinfo=None))


def test_registrar_conserva_datos_er_y_usa_tiempo_servidor(intento: Intento, reloj: RelojFijo) -> None:
    reloj.instante += timedelta(seconds=12, microseconds=500000)
    actual = con_respuesta(intento, reloj)
    paso = actual.pasos[0]
    assert (paso.id_paso, paso.id_intento, paso.id_decision, paso.id_opcion) == (40, 10, 50, 60)
    assert paso.registrado_en == reloj.instante
    assert paso.tiempo_segundos == 12
    assert paso.numero_paso == 1
    assert intento.pasos == ()


def test_modificar_reemplaza_seleccion_sin_duplicar(intento: Intento, reloj: RelojFijo) -> None:
    anterior = con_respuesta(intento, reloj)
    reloj.instante += timedelta(seconds=30)
    actual = anterior.modificar_decision(
        id_decision=50, id_opcion=61, reflexion_estudiante="Nueva elección", reloj=reloj
    )
    assert len(actual.pasos) == 1
    paso = actual.pasos[0]
    assert (paso.id_paso, paso.numero_paso, paso.id_opcion) == (40, 1, 61)
    assert paso.reflexion_estudiante == "Nueva elección"
    assert paso.registrado_en == reloj.instante
    assert anterior.pasos[0].id_opcion == 60


def test_segunda_decision_tiene_otro_numero(intento: Intento, reloj: RelojFijo) -> None:
    actual = con_respuesta(intento, reloj).registrar_decision(
        id_paso=41, id_decision=51, id_opcion=62, reloj=reloj
    )
    assert [paso.numero_paso for paso in actual.pasos] == [1, 2]


def test_rechaza_registrar_dos_veces_misma_decision(intento: Intento, reloj: RelojFijo) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        con_respuesta(intento, reloj).registrar_decision(
            id_paso=41, id_decision=50, id_opcion=61, reloj=reloj
        )


def test_rechaza_reutilizar_id_paso(intento: Intento, reloj: RelojFijo) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        con_respuesta(intento, reloj).registrar_decision(
            id_paso=40, id_decision=51, id_opcion=62, reloj=reloj
        )


def test_rechaza_modificar_decision_inexistente(intento: Intento, reloj: RelojFijo) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        intento.modificar_decision(id_decision=50, id_opcion=61, reloj=reloj)


@pytest.mark.parametrize("segundos", [600, 601, 3600])
@pytest.mark.parametrize("modificar", [False, True])
def test_no_edita_en_limite_o_despues_aunque_estado_siga_activo(
    intento: Intento, reloj: RelojFijo, segundos: int, modificar: bool
) -> None:
    actual = con_respuesta(intento, reloj)
    reloj.instante = INICIO + timedelta(seconds=segundos)
    with pytest.raises(IntentoNoEditable):
        if modificar:
            actual.modificar_decision(id_decision=50, id_opcion=61, reloj=reloj)
        else:
            actual.registrar_decision(id_paso=41, id_decision=51, id_opcion=62, reloj=reloj)
    assert actual.pasos[0].id_opcion == 60


def test_permite_editar_justo_antes_del_limite(intento: Intento, reloj: RelojFijo) -> None:
    reloj.instante = intento.vence_en - timedelta(microseconds=1)
    assert len(con_respuesta(intento, reloj).pasos) == 1


def test_cierre_voluntario_conserva_registros_y_no_califica(intento: Intento, reloj: RelojFijo) -> None:
    actual = con_respuesta(intento, reloj)
    reloj.instante += timedelta(minutes=1)
    cerrado = actual.finalizar(reloj)
    assert cerrado.estado == EstadoIntento.FINALIZADO
    assert cerrado.fin == reloj.instante
    assert cerrado.pasos == actual.pasos
    assert not hasattr(cerrado, "nota_final")


def test_finalizacion_sin_respuestas_no_inventa_calificacion(intento: Intento, reloj: RelojFijo) -> None:
    assert intento.finalizar(reloj).estado == EstadoIntento.FINALIZADO


@pytest.mark.parametrize("modificar", [False, True])
def test_no_edita_intento_finalizado(intento: Intento, reloj: RelojFijo, modificar: bool) -> None:
    cerrado = con_respuesta(intento, reloj).finalizar(reloj)
    with pytest.raises(IntentoNoEditable):
        if modificar:
            cerrado.modificar_decision(id_decision=50, id_opcion=61, reloj=reloj)
        else:
            cerrado.registrar_decision(id_paso=41, id_decision=51, id_opcion=62, reloj=reloj)


def test_vencimiento_cierra_en_deadline_y_conserva_respuestas(intento: Intento, reloj: RelojFijo) -> None:
    actual = con_respuesta(intento, reloj)
    reloj.instante += timedelta(hours=2)
    vencido = actual.actualizar_vencimiento(reloj)
    assert vencido.estado == EstadoIntento.VENCIDO
    assert vencido.fin == INICIO + DURACION
    assert vencido.pasos == actual.pasos
    with pytest.raises(IntentoNoEditable):
        vencido.modificar_decision(id_decision=50, id_opcion=61, reloj=reloj)


def test_actualizar_antes_del_limite_no_cierra(intento: Intento, reloj: RelojFijo) -> None:
    assert intento.actualizar_vencimiento(reloj) is intento


def test_finalizar_al_limite_produce_vencimiento(intento: Intento, reloj: RelojFijo) -> None:
    reloj.instante = intento.vence_en
    assert intento.finalizar(reloj).estado == EstadoIntento.VENCIDO


@pytest.mark.parametrize("por_tiempo", [False, True])
def test_cierre_es_idempotente_y_no_reabre(intento: Intento, reloj: RelojFijo, por_tiempo: bool) -> None:
    if por_tiempo:
        reloj.instante = intento.vence_en
    cerrado = intento.finalizar(reloj)
    reloj.instante += timedelta(days=1)
    assert cerrado.finalizar(reloj) is cerrado
    assert cerrado.actualizar_vencimiento(reloj) is cerrado


def test_rechaza_reloj_que_retrocede(intento: Intento, reloj: RelojFijo) -> None:
    reloj.instante += timedelta(seconds=30)
    actual = con_respuesta(intento, reloj)
    reloj.instante -= timedelta(seconds=1)
    with pytest.raises(ErrorDominioParticipacion):
        actual.finalizar(reloj)


def test_rechaza_reloj_sin_zona_al_editar(intento: Intento, reloj: RelojFijo) -> None:
    reloj.instante = INICIO.replace(tzinfo=None)
    with pytest.raises(ErrorDominioParticipacion):
        con_respuesta(intento, reloj)


@pytest.mark.parametrize("campo,valor", [
    ("id_intento", 11),
    ("registrado_en", INICIO - timedelta(seconds=1)),
    ("tiempo_segundos", 999),
])
def test_no_reconstituye_pasos_inconsistentes(
    intento: Intento, reloj: RelojFijo, campo: str, valor: object
) -> None:
    paso = con_respuesta(intento, reloj).pasos[0]
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, pasos=(replace(paso, **{campo: valor}),))


@pytest.mark.parametrize("cambios", [
    {"estado": EstadoIntento.FINALIZADO},
    {"fin": INICIO},
    {"estado": EstadoIntento.VENCIDO, "fin": INICIO},
    {"estado": EstadoIntento.FINALIZADO, "fin": INICIO + DURACION},
    {"estado": "DESCONOCIDO"},
])
def test_no_reconstituye_estado_inconsistente(intento: Intento, cambios: dict) -> None:
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, **cambios)


def test_objetos_inmutables(intento: Intento) -> None:
    with pytest.raises(FrozenInstanceError):
        intento.estado = EstadoIntento.FINALIZADO


def test_reconstitucion_normaliza_fechas_locales(intento: Intento, reloj: RelojFijo) -> None:
    local = timezone(timedelta(hours=-5))
    actual = con_respuesta(intento, reloj)
    paso = replace(actual.pasos[0], registrado_en=INICIO.astimezone(local))
    reconstruido = replace(actual, inicio=INICIO.astimezone(local), pasos=(paso,))
    assert reconstruido.inicio.tzinfo == timezone.utc
    assert reconstruido.pasos[0].registrado_en.tzinfo == timezone.utc
    assert reconstruido.vence_en == INICIO + DURACION


def test_rechaza_paso_posterior_al_cierre(intento: Intento, reloj: RelojFijo) -> None:
    reloj.instante += timedelta(seconds=30)
    actual = con_respuesta(intento, reloj)
    with pytest.raises(ErrorDominioParticipacion):
        replace(actual, estado=EstadoIntento.FINALIZADO, fin=INICIO)


def test_no_se_puede_ampliar_tiempo_al_reconstruir_una_respuesta(intento: Intento, reloj: RelojFijo) -> None:
    paso = con_respuesta(intento, reloj).pasos[0]
    fuera_de_tiempo = replace(paso, registrado_en=intento.vence_en, tiempo_segundos=600)
    with pytest.raises(ErrorDominioParticipacion):
        replace(intento, pasos=(fuera_de_tiempo,))
