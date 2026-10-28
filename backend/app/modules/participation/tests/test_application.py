from dataclasses import asdict, dataclass
from datetime import timedelta

import pytest

from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import (
    AccesoDenegado, ConflictoActualizacion, ErrorAplicacionParticipacion,
    RecursoNoDisponible, ReglaPendiente,
)
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.errors import ErrorDominioParticipacion, IntentoNoEditable
from app.modules.participation.tests.fakes import (
    AlmacenFalso, CasesFalso, IdentityFalso, INICIO, RelojFalso, SchedulingFalso,
)


@dataclass
class Entorno:
    almacen: AlmacenFalso
    reloj: RelojFalso
    identity: IdentityFalso
    scheduling: SchedulingFalso
    cases: CasesFalso
    facade: ParticipacionFacade

    def iniciar(self, **extras):
        return self.facade.iniciar_intento(
            id_estudiante=7, id_participacion=20, id_consentimiento=30, **extras,
        )

    def responder(self, id_intento: int = 10, id_decision: int = 50, id_opcion: int = 60):
        return self.facade.registrar_decision(
            id_estudiante=7, id_intento=id_intento, id_decision=id_decision, id_opcion=id_opcion,
        )


@pytest.fixture
def entorno() -> Entorno:
    almacen, reloj = AlmacenFalso(), RelojFalso()
    identity, scheduling, cases = IdentityFalso(), SchedulingFalso(), CasesFalso()
    facade = ParticipacionFacade(
        fabrica=almacen.unidad, identity=identity, scheduling=scheduling, cases=cases, reloj=reloj,
    )
    return Entorno(almacen, reloj, identity, scheduling, cases, facade)


def test_inicio_autorizado_guarda_el_intento_con_tiempo_programado(entorno: Entorno) -> None:
    entorno.scheduling.duracion = timedelta(minutes=3)
    resultado = entorno.iniciar()
    assert resultado.inicio == INICIO
    assert resultado.vence_en == INICIO + timedelta(minutes=3)
    assert resultado.estado == EstadoIntento.EN_CURSO
    assert entorno.almacen.intentos[resultado.id_intento].id_consentimiento == 30
    assert entorno.almacen.commits == 1
    assert entorno.identity.llamadas == ["acceso", "inicio"]
    assert entorno.scheduling.llamadas == ["condiciones", "nuevo"]


@pytest.mark.parametrize("causa", ["titular", "consentimiento", "permiso", "programacion"])
def test_inicio_rechazado_no_crea_intentos(entorno: Entorno, causa: str) -> None:
    datos = dict(id_estudiante=7, id_participacion=20, id_consentimiento=30)
    if causa == "titular":
        datos["id_estudiante"] = 8
    elif causa == "consentimiento":
        datos["id_consentimiento"] = 999
    elif causa == "permiso":
        datos["id_permiso_extra"] = 999
    else:
        entorno.scheduling.permitir_inicio = False
    with pytest.raises(AccesoDenegado):
        entorno.facade.iniciar_intento(**datos)
    assert entorno.almacen.intentos == {}
    assert entorno.almacen.commits == 0


def test_inicio_no_inventa_participacion_o_convocatoria(entorno: Entorno) -> None:
    with pytest.raises(RecursoNoDisponible):
        entorno.facade.iniciar_intento(id_estudiante=7, id_participacion=999, id_consentimiento=30)
    assert entorno.almacen.commits == 0


def test_inicio_no_duplica_un_intento_activo(entorno: Entorno) -> None:
    entorno.iniciar()
    with pytest.raises(ErrorAplicacionParticipacion):
        entorno.iniciar()
    assert len(entorno.almacen.intentos) == 1
    assert entorno.almacen.commits == 1


def test_repeticion_exige_decision_externa_no_solo_numero(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.facade.finalizar(id_estudiante=7, id_intento=10)
    with pytest.raises(AccesoDenegado):
        entorno.iniciar()
    nuevo = entorno.iniciar(id_permiso_extra=90)
    assert nuevo.numero_intento == 2
    assert len(entorno.almacen.intentos) == 2
    assert entorno.almacen.intentos[10].estado == EstadoIntento.FINALIZADO


def test_registrar_guarda_la_nueva_entidad_inmutable(entorno: Entorno) -> None:
    entorno.iniciar()
    original = entorno.almacen.intentos[10]
    entorno.reloj.instante += timedelta(seconds=20)
    entorno.responder()
    guardado = entorno.almacen.intentos[10]
    assert original.pasos == ()
    assert guardado.pasos[0].id_opcion == 60
    assert guardado.pasos[0].registrado_en == entorno.reloj.instante
    assert entorno.almacen.commits == 2


def test_modificar_conserva_id_y_no_duplica_seleccion(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.responder()
    anterior = entorno.almacen.intentos[10]
    entorno.facade.modificar_decision(
        id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
    )
    actual = entorno.almacen.intentos[10]
    assert len(actual.pasos) == 1
    assert actual.pasos[0].id_paso == anterior.pasos[0].id_paso
    assert actual.pasos[0].id_opcion == 61
    assert anterior.pasos[0].id_opcion == 60


@pytest.mark.parametrize("decision,opcion", [(50, 62), (999, 60), (99, 98)])
def test_rechaza_opcion_o_decision_fuera_del_caso_o_recorrido(
    entorno: Entorno, decision: int, opcion: int,
) -> None:
    entorno.iniciar()
    with pytest.raises(AccesoDenegado):
        entorno.responder(id_decision=decision, id_opcion=opcion)
    assert entorno.almacen.intentos[10].pasos == ()
    assert entorno.almacen.commits == 1


def test_politica_de_cambio_pendiente_no_sobrescribe_seleccion(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.responder()
    entorno.cases.regla_pendiente = True
    with pytest.raises(ReglaPendiente):
        entorno.facade.modificar_decision(
            id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
        )
    assert entorno.almacen.intentos[10].pasos[0].id_opcion == 60
    assert entorno.almacen.commits == 2


def test_cambiar_rama_no_borra_pasos_posteriores_por_iniciativa_de_la_fachada(entorno: Entorno) -> None:
    entorno.cases.ramificado = True
    entorno.iniciar()
    entorno.responder()
    entorno.responder(id_decision=51, id_opcion=62)
    anterior = entorno.almacen.intentos[10]
    with pytest.raises(ReglaPendiente):
        entorno.facade.modificar_decision(
            id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
        )
    assert entorno.almacen.intentos[10] == anterior


def test_progreso_usa_recorrido_de_cases_sin_revelar_evaluacion(entorno: Entorno) -> None:
    entorno.cases.ruta = RecorridoAplicable((50, 52), True)
    entorno.iniciar()
    entorno.responder()
    progreso = entorno.facade.consultar_progreso(id_estudiante=7, id_intento=10)
    assert progreso.decisiones_aplicables == (50, 52)
    assert progreso.respondidas == 1
    assert progreso.total_aplicable == 2
    assert progreso.pendientes == (52,)
    assert asdict(progreso.selecciones[0]) == {"id_decision": 50, "id_opcion": 60}
    datos = str(asdict(progreso))
    for prohibido in ("nota", "puntaje", "es_correcta", "justificacion", "INCOMPLETA"):
        assert prohibido not in datos
    assert entorno.almacen.commits == 2  # Consultar no escribe si nada cambió.


def test_total_desconocido_no_se_inventa_como_total_del_caso(entorno: Entorno) -> None:
    entorno.cases.ramificado = True
    entorno.iniciar()
    antes = entorno.facade.consultar_progreso(id_estudiante=7, id_intento=10)
    assert antes.total_aplicable is None
    assert antes.pendientes == (50,)
    entorno.responder(id_opcion=61)
    despues = entorno.facade.consultar_progreso(id_estudiante=7, id_intento=10)
    assert despues.total_aplicable == 2
    assert despues.pendientes == (52,)


@pytest.mark.parametrize("modificar", [False, True])
def test_rechazo_de_modificacion_tras_finalizar(entorno: Entorno, modificar: bool) -> None:
    entorno.iniciar()
    entorno.responder()
    entorno.facade.finalizar(id_estudiante=7, id_intento=10)
    with pytest.raises(IntentoNoEditable):
        if modificar:
            entorno.facade.modificar_decision(
                id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
            )
        else:
            entorno.responder(id_decision=51, id_opcion=62)
    assert entorno.almacen.commits == 3


@pytest.mark.parametrize("modificar", [False, True])
def test_al_limite_rechaza_edicion_y_conserva_vencimiento(entorno: Entorno, modificar: bool) -> None:
    entorno.iniciar()
    entorno.responder()
    entorno.reloj.instante += timedelta(minutes=10)
    with pytest.raises(IntentoNoEditable):
        if modificar:
            entorno.facade.modificar_decision(
                id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
            )
        else:
            entorno.responder(id_decision=51, id_opcion=62)
    actual = entorno.almacen.intentos[10]
    assert actual.estado == EstadoIntento.VENCIDO
    assert len(actual.pasos) == 1 and actual.pasos[0].id_opcion == 60
    assert actual.fin == INICIO + timedelta(minutes=10)


def test_tiempo_se_revalida_despues_de_las_dependencias(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.cases.despues_de_validar = lambda: setattr(
        entorno.reloj, "instante", INICIO + timedelta(minutes=10),
    )
    with pytest.raises(IntentoNoEditable):
        entorno.responder()
    assert entorno.almacen.intentos[10].pasos == ()


def test_vencimiento_individual_conserva_respuestas_y_no_clasifica_academicamente(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.responder()
    pasos = entorno.almacen.intentos[10].pasos
    entorno.reloj.instante += timedelta(hours=1)
    resultado = entorno.facade.procesar_vencimiento(id_estudiante=7, id_intento=10)
    assert resultado.estado == EstadoIntento.VENCIDO
    assert resultado.fin == INICIO + timedelta(minutes=10)
    assert entorno.almacen.intentos[10].pasos == pasos
    assert "nota" not in asdict(resultado)


def test_procesar_vencimiento_antes_del_limite_no_finaliza(entorno: Entorno) -> None:
    entorno.iniciar()
    resultado = entorno.facade.procesar_vencimiento(id_estudiante=7, id_intento=10)
    assert resultado.estado == EstadoIntento.EN_CURSO
    assert entorno.almacen.commits == 1


@pytest.mark.parametrize("vencido", [False, True])
def test_finalizacion_repetida_no_repite_escrituras(entorno: Entorno, vencido: bool) -> None:
    entorno.iniciar()
    entorno.responder()
    if vencido:
        entorno.reloj.instante += timedelta(minutes=10)
    primero = entorno.facade.finalizar(id_estudiante=7, id_intento=10)
    entorno.reloj.instante += timedelta(days=1)
    segundo = entorno.facade.finalizar(id_estudiante=7, id_intento=10)
    tercero = entorno.facade.procesar_vencimiento(id_estudiante=7, id_intento=10)
    assert primero == segundo == tercero
    assert entorno.almacen.commits == 3
    assert entorno.almacen.escrituras == 3


@pytest.mark.parametrize("operacion", ["registrar", "modificar", "progreso", "finalizar", "vencer"])
def test_todas_las_operaciones_aislan_otro_estudiante(entorno: Entorno, operacion: str) -> None:
    entorno.iniciar()
    entorno.responder()
    llamadas = {
        "registrar": lambda: entorno.facade.registrar_decision(
            id_estudiante=8, id_intento=10, id_decision=51, id_opcion=62),
        "modificar": lambda: entorno.facade.modificar_decision(
            id_estudiante=8, id_intento=10, id_decision=50, id_opcion=61),
        "progreso": lambda: entorno.facade.consultar_progreso(id_estudiante=8, id_intento=10),
        "finalizar": lambda: entorno.facade.finalizar(id_estudiante=8, id_intento=10),
        "vencer": lambda: entorno.facade.procesar_vencimiento(id_estudiante=8, id_intento=10),
    }
    anterior = entorno.almacen.intentos[10]
    with pytest.raises(AccesoDenegado):
        llamadas[operacion]()
    assert entorno.almacen.intentos[10] == anterior
    assert entorno.almacen.commits == 2


@pytest.mark.parametrize("dependencia,metodo", [
    ("identity", "acceso"), ("identity", "inicio"),
    ("scheduling", "condiciones"), ("scheduling", "nuevo"),
])
def test_errores_externos_al_iniciar_no_crean_intentos(entorno: Entorno, dependencia: str, metodo: str) -> None:
    getattr(entorno, dependencia).fallar_en.add(metodo)
    with pytest.raises(RuntimeError):
        entorno.iniciar()
    assert entorno.almacen.intentos == {}
    assert entorno.almacen.commits == 0


@pytest.mark.parametrize("dependencia,metodo", [
    ("identity", "acceso"), ("scheduling", "edicion"), ("scheduling", "caso"),
    ("cases", "opcion"), ("cases", "cambio"), ("cases", "recorrido"),
])
def test_error_al_guardar_no_pierde_seleccion_confirmada(entorno: Entorno, dependencia: str, metodo: str) -> None:
    entorno.iniciar()
    entorno.responder()
    anterior = entorno.almacen.intentos[10]
    getattr(entorno, dependencia).fallar_en.add(metodo)
    with pytest.raises(RuntimeError):
        entorno.facade.modificar_decision(
            id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
        )
    assert entorno.almacen.intentos[10] == anterior
    assert entorno.almacen.commits == 2


@pytest.mark.parametrize("operacion", ["inicio", "respuesta", "cierre", "vencimiento"])
def test_fallo_de_commit_no_confirma_cambios(entorno: Entorno, operacion: str) -> None:
    if operacion != "inicio":
        entorno.iniciar()
    if operacion == "vencimiento":
        entorno.reloj.instante += timedelta(minutes=10)
    anteriores = dict(entorno.almacen.intentos)
    commits = entorno.almacen.commits
    entorno.almacen.fallo_commit = True
    llamadas = {
        "inicio": entorno.iniciar,
        "respuesta": entorno.responder,
        "cierre": lambda: entorno.facade.finalizar(id_estudiante=7, id_intento=10),
        "vencimiento": lambda: entorno.facade.procesar_vencimiento(id_estudiante=7, id_intento=10),
    }
    with pytest.raises(RuntimeError):
        llamadas[operacion]()
    assert entorno.almacen.intentos == anteriores
    assert entorno.almacen.commits == commits


def test_conflicto_de_actualizacion_no_sobrescribe(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.almacen.conflicto = True
    with pytest.raises(ConflictoActualizacion):
        entorno.responder()
    assert entorno.almacen.intentos[10].pasos == ()


def test_asignacion_cerrada_impide_editar_pero_permite_cierre_individual(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.scheduling.permitir_edicion = False
    with pytest.raises(AccesoDenegado):
        entorno.responder()
    resultado = entorno.facade.finalizar(id_estudiante=7, id_intento=10)
    assert resultado.estado == EstadoIntento.FINALIZADO


def test_consultar_progreso_actualiza_vencimiento_sin_cambiar_duracion(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.responder()
    entorno.scheduling.duracion = timedelta(hours=2)
    entorno.scheduling.permitir_inicio = False
    entorno.reloj.instante += timedelta(minutes=10)
    resultado = entorno.facade.consultar_progreso(id_estudiante=7, id_intento=10)
    assert resultado.intento.estado == EstadoIntento.VENCIDO
    assert resultado.intento.fin == INICIO + timedelta(minutes=10)
    assert resultado.respondidas == 1
    assert entorno.almacen.intentos[10].estado == EstadoIntento.VENCIDO


def test_fallo_en_recorrido_no_confirma_una_consulta_parcial(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.reloj.instante += timedelta(minutes=10)
    entorno.cases.fallar_en.add("recorrido")
    with pytest.raises(RuntimeError):
        entorno.facade.consultar_progreso(id_estudiante=7, id_intento=10)
    assert entorno.almacen.commits == 1
    assert entorno.almacen.intentos[10].estado == EstadoIntento.EN_CURSO
    # El vencimiento puede procesarse sin Cases ni Scheduling disponibles.
    entorno.facade.procesar_vencimiento(id_estudiante=7, id_intento=10)
    assert entorno.almacen.intentos[10].estado == EstadoIntento.VENCIDO


def test_progreso_no_oculta_selecciones_fuera_de_un_recorrido_cambiado(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.responder()
    entorno.cases.ruta = RecorridoAplicable((51,), True)
    with pytest.raises(ReglaPendiente):
        entorno.facade.consultar_progreso(id_estudiante=7, id_intento=10)
    assert entorno.almacen.intentos[10].pasos[0].id_decision == 50
    assert entorno.almacen.commits == 2


def test_fallo_de_guardado_no_pierde_respuesta_previa(entorno: Entorno) -> None:
    entorno.iniciar()
    entorno.responder()
    anterior = entorno.almacen.intentos[10]
    entorno.almacen.fallo_guardado = True
    with pytest.raises(RuntimeError):
        entorno.facade.modificar_decision(
            id_estudiante=7, id_intento=10, id_decision=50, id_opcion=61,
        )
    assert entorno.almacen.intentos[10] == anterior
    assert entorno.almacen.commits == 2


def test_duracion_invalida_de_dependencia_no_inicia(entorno: Entorno) -> None:
    entorno.scheduling.duracion = timedelta(0)
    with pytest.raises(ErrorDominioParticipacion):
        entorno.iniciar()
    assert entorno.almacen.commits == 0


@pytest.mark.parametrize("decisiones", [(50, 50), (0,), (True,)])
def test_rechaza_recorrido_incoherente_de_dependencia(decisiones: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        RecorridoAplicable(decisiones, True)
