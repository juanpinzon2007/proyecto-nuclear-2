from dataclasses import asdict, dataclass, replace
from datetime import timedelta
from decimal import Decimal

import pytest

from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import (
    AccesoDenegado, ConflictoActualizacion, RecursoNoDisponible, ReglaPendiente,
)
from app.modules.participation.application.evaluation_service import ServicioEvaluacion
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.evaluation import (
    MAPEO_AUSENCIA_PENDIENTE, EvaluacionInconsistente, ModalidadEvaluacion,
    PoliticaEvaluacionPendiente,
)
from app.modules.participation.tests.evaluation_fakes import (
    AlmacenEvaluacionFalso, AusenciasFalsas, CasesEvaluacionFalso, PoliticaEvaluacionFalsa,
)
from app.modules.participation.tests.fakes import IdentityFalso, RelojFalso, SchedulingFalso


@dataclass
class EntornoEvaluacion:
    almacen: AlmacenEvaluacionFalso
    reloj: RelojFalso
    identity: IdentityFalso
    scheduling: SchedulingFalso
    cases: CasesEvaluacionFalso
    politica: PoliticaEvaluacionFalsa
    ausencias: AusenciasFalsas
    facade: ParticipacionFacade

    def cerrar(self, *, completo=True, vencido=False):
        intento = self.facade.iniciar_intento(
            id_estudiante=7, id_participacion=20, id_consentimiento=30,
        )
        self.facade.registrar_decision(
            id_estudiante=7, id_intento=intento.id_intento, id_decision=50, id_opcion=60,
        )
        if completo:
            self.facade.registrar_decision(
                id_estudiante=7, id_intento=intento.id_intento, id_decision=51, id_opcion=63,
            )
        if vencido:
            self.reloj.instante += timedelta(minutes=10)
        return self.facade.finalizar(id_estudiante=7, id_intento=intento.id_intento)

    def evaluar(self):
        return self.facade.evaluar_intento(id_estudiante=7, id_intento=10)

    def consultar(self):
        return self.facade.consultar_evaluacion(id_estudiante=7, id_participacion=20, id_intento=10)


@pytest.fixture
def entorno():
    almacen, reloj = AlmacenEvaluacionFalso(), RelojFalso()
    identity, scheduling = IdentityFalso(), SchedulingFalso()
    cases, politica, ausencias = CasesEvaluacionFalso(), PoliticaEvaluacionFalsa(), AusenciasFalsas()
    servicio = ServicioEvaluacion(almacen.unidad_evaluacion, identity, scheduling, cases, politica, ausencias)
    facade = ParticipacionFacade(
        fabrica=almacen.unidad, identity=identity, cases=cases,
        scheduling=scheduling, reloj=reloj, evaluacion=servicio,
    )
    return EntornoEvaluacion(almacen, reloj, identity, scheduling, cases, politica, ausencias, facade)


def test_cierre_no_evalua_ni_altera_su_semantica(entorno):
    cerrado = entorno.cerrar()
    commits = entorno.almacen.commits
    repetido = entorno.facade.finalizar(id_estudiante=7, id_intento=10)
    assert cerrado == repetido
    assert entorno.almacen.commits == commits
    assert entorno.almacen.evaluaciones == {}
    assert entorno.politica.llamadas == 0


def test_evaluacion_completa_confirmada_con_calculo_real(entorno):
    entorno.cerrar()
    estado = entorno.evaluar()
    assert estado.confirmada and estado.modalidad == ModalidadEvaluacion.COMPLETA
    assert "nota_final" not in asdict(estado)
    resultado = entorno.consultar()
    assert resultado.nota_final == Decimal("4.00")
    assert [r.puntaje_obtenido for r in resultado.criterios] == [Decimal(3), Decimal(1)]
    assert resultado.referencia.version == "referencia-ficticia-v1"
    assert resultado.politica_calculo == "politica-ficticia-porcentual-v1"
    assert entorno.almacen.inserciones_evaluacion == 1


def test_no_hay_lectura_academica_antes_de_confirmar_evaluacion(entorno):
    entorno.cerrar()
    with pytest.raises(RecursoNoDisponible):
        entorno.consultar()


def test_no_evaluar_intento_aun_en_curso(entorno):
    entorno.facade.iniciar_intento(id_estudiante=7, id_participacion=20, id_consentimiento=30)
    with pytest.raises(EvaluacionInconsistente):
        entorno.evaluar()
    assert entorno.almacen.evaluaciones == {}


def test_repetir_evaluacion_no_recalcula_ni_duplica_efectos(entorno):
    entorno.cerrar()
    uno = entorno.evaluar()
    commits = entorno.almacen.commits
    entorno.politica.fallo_externo = True
    entorno.cases.fallar_en.add("rubrica")
    dos = entorno.evaluar()
    assert uno == dos
    assert entorno.politica.llamadas == 1
    assert entorno.almacen.inserciones_evaluacion == 1
    assert entorno.almacen.commits == commits
    assert entorno.consultar().nota_final == Decimal("4.00")


@pytest.mark.parametrize("causa", ["mapeo", "redondeo", "parcial"])
def test_politicas_pendientes_no_producen_nota_publicable(entorno, causa):
    entorno.cerrar(completo=causa != "parcial")
    if causa == "mapeo":
        entorno.politica.mapeo_definido = False
    elif causa == "redondeo":
        entorno.politica.redondeo_definido = False
    commits = entorno.almacen.commits
    estado = entorno.evaluar()
    assert not estado.confirmada and estado.pendientes
    assert entorno.almacen.commits == commits
    assert entorno.almacen.evaluaciones == {}
    assert "nota_final" not in asdict(estado)
    with pytest.raises(RecursoNoDisponible):
        entorno.consultar()


def test_parcial_con_politica_expresa_usa_matematica_real(entorno):
    entorno.cerrar(completo=False, vencido=True)
    entorno.politica.parcial_definida = True
    estado = entorno.evaluar()
    assert estado.modalidad == ModalidadEvaluacion.PARCIAL and estado.confirmada
    resultado = entorno.consultar()
    # SOLO fixture: el criterio sin respuesta se mapea explícitamente a nivel cero.
    assert resultado.nota_final == Decimal("3.00")
    assert resultado.evidencias[1].id_opcion is None
    assert resultado.evidencias[1].cero_por_ausencia is None
    assert entorno.almacen.intentos[10].estado == EstadoIntento.VENCIDO


def test_finalizado_voluntario_no_equivale_automaticamente_a_completa(entorno):
    entorno.cerrar(completo=False)
    entorno.politica.parcial_definida = True
    assert entorno.almacen.intentos[10].estado == EstadoIntento.FINALIZADO
    assert entorno.evaluar().modalidad == ModalidadEvaluacion.PARCIAL


def test_pendiente_se_puede_reintentar_cuando_llega_politica(entorno):
    entorno.cerrar(completo=False)
    assert not entorno.evaluar().confirmada
    entorno.politica.parcial_definida = True
    assert entorno.evaluar().confirmada
    assert entorno.almacen.inserciones_evaluacion == 1


def test_ausencia_sin_intento_aplica_ceros_pero_bloquea_mapeo_er_no_resuelto(entorno):
    estado = entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20)
    assert estado.modalidad == ModalidadEvaluacion.AUSENCIA
    assert estado.id_intento is None
    assert MAPEO_AUSENCIA_PENDIENTE in estado.pendientes
    assert not estado.confirmada
    assert entorno.almacen.intentos == {}
    assert entorno.almacen.evaluaciones == {}
    assert entorno.almacen.commits == 0


def test_ausencia_necesita_confirmacion_academica_ademas_de_no_tener_intentos(entorno):
    entorno.ausencias.permitida = False
    with pytest.raises(AccesoDenegado):
        entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20)
    assert entorno.almacen.evaluaciones == {}


def test_politica_no_puede_convertir_ausencia_en_puntajes_positivos(entorno):
    entorno.politica.ausencia_incorrecta = True
    with pytest.raises(EvaluacionInconsistente):
        entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20)
    assert entorno.almacen.intentos == {}
    assert entorno.almacen.evaluaciones == {}


def test_clasificacion_externa_incompatible_con_evidencias_se_rechaza(entorno):
    entorno.cerrar(completo=False)
    entorno.politica.modalidad_forzada = ModalidadEvaluacion.COMPLETA
    with pytest.raises(EvaluacionInconsistente):
        entorno.evaluar()
    assert entorno.almacen.evaluaciones == {}


def test_ausencia_no_acepta_participacion_con_intento_real(entorno):
    entorno.cerrar(completo=False, vencido=True)
    with pytest.raises(EvaluacionInconsistente):
        entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20)
    assert entorno.ausencias.llamadas == 0


def test_no_evaluar_sin_recorrido_definido(entorno):
    entorno.cerrar()
    entorno.cases.ruta = RecorridoAplicable((50,), False)
    with pytest.raises(PoliticaEvaluacionPendiente):
        entorno.evaluar()
    assert entorno.almacen.evaluaciones == {}


def test_rechaza_rubrica_de_otro_caso(entorno):
    entorno.cerrar()
    referencia = replace(entorno.cases.rubrica.referencia, id_caso=999)
    entorno.cases.rubrica = replace(entorno.cases.rubrica, referencia=referencia)
    with pytest.raises(EvaluacionInconsistente):
        entorno.evaluar()


@pytest.mark.parametrize("operacion", ["evaluar", "consultar", "ausencia"])
def test_aislamiento_de_otro_estudiante(entorno, operacion):
    entorno.cerrar()
    entorno.evaluar()
    llamadas = {
        "evaluar": lambda: entorno.facade.evaluar_intento(id_estudiante=8, id_intento=10),
        "consultar": lambda: entorno.facade.consultar_evaluacion(
            id_estudiante=8, id_participacion=20, id_intento=10),
        "ausencia": lambda: entorno.facade.evaluar_ausencia(id_estudiante=8, id_participacion=20),
    }
    with pytest.raises(AccesoDenegado):
        llamadas[operacion]()
    assert entorno.almacen.inserciones_evaluacion == 1


def test_error_de_dependencia_no_se_disfraza_de_politica_pendiente(entorno):
    entorno.cerrar()
    entorno.politica.fallo_externo = True
    with pytest.raises(RuntimeError):
        entorno.evaluar()
    assert entorno.almacen.evaluaciones == {}


def test_fallo_commit_no_publica_candidato_y_permite_reintento(entorno):
    entorno.cerrar()
    entorno.almacen.fallo_commit = True
    with pytest.raises(RuntimeError):
        entorno.evaluar()
    assert entorno.almacen.evaluaciones == {}
    assert entorno.almacen.intentos[10].estado == EstadoIntento.FINALIZADO
    with pytest.raises(RecursoNoDisponible):
        entorno.consultar()
    entorno.almacen.fallo_commit = False
    assert entorno.evaluar().confirmada
    assert entorno.almacen.inserciones_evaluacion == 1


def test_repositorio_rechaza_duplicado_en_lugar_de_sobrescribir(entorno):
    entorno.cerrar()
    entorno.evaluar()
    datos = entorno.consultar()
    with entorno.almacen.unidad_evaluacion() as trabajo:
        with pytest.raises(ConflictoActualizacion):
            trabajo.resultados.agregar_definitiva(datos)
    assert entorno.almacen.inserciones_evaluacion == 1


def test_repositorio_nunca_devuelve_candidato_sin_commit(entorno):
    entorno.cerrar()
    entorno.evaluar()
    datos = entorno.consultar()
    entorno.almacen.evaluaciones.clear()
    with entorno.almacen.unidad_evaluacion() as trabajo:
        trabajo.resultados.agregar_definitiva(datos)
        assert trabajo.resultados.obtener_definitiva(id_participacion=20, id_intento=10) is None
    assert entorno.almacen.evaluaciones == {}


def test_dos_transacciones_simuladas_no_confirman_dos_definitivas(entorno):
    entorno.cerrar()
    entorno.evaluar()
    datos = entorno.consultar()
    entorno.almacen.evaluaciones.clear()
    entorno.almacen.inserciones_evaluacion = 0
    uno, dos = entorno.almacen.unidad_evaluacion(), entorno.almacen.unidad_evaluacion()
    uno.resultados.agregar_definitiva(datos)
    dos.resultados.agregar_definitiva(datos)
    uno.commit()
    with pytest.raises(ConflictoActualizacion):
        dos.commit()
    assert entorno.almacen.inserciones_evaluacion == 1


def test_lectura_rechaza_resultado_pendiente_devuelto_por_adaptador(entorno):
    entorno.cerrar()
    entorno.evaluar()
    datos = entorno.consultar()
    entorno.almacen.evaluaciones[(20, 10)] = replace(datos, pendientes=("inconsistencia",))
    with pytest.raises(EvaluacionInconsistente):
        entorno.consultar()


def test_no_consolida_distintos_intentos_automaticamente(entorno):
    entorno.cerrar()
    entorno.evaluar()
    segundo = entorno.facade.iniciar_intento(
        id_estudiante=7, id_participacion=20, id_consentimiento=30, id_permiso_extra=90,
    )
    entorno.facade.finalizar(id_estudiante=7, id_intento=segundo.id_intento)
    entorno.politica.parcial_definida = True
    entorno.facade.evaluar_intento(id_estudiante=7, id_intento=segundo.id_intento)
    assert set(entorno.almacen.evaluaciones) == {(20, 10), (20, segundo.id_intento)}
    assert entorno.consultar().nota_final == Decimal("4.00")
    assert (20, None) not in entorno.almacen.evaluaciones


def test_fachada_sin_motor_configurado_rechaza_evaluacion(entorno):
    facade = ParticipacionFacade(
        fabrica=entorno.almacen.unidad, identity=entorno.identity, cases=entorno.cases,
        scheduling=entorno.scheduling, reloj=entorno.reloj,
    )
    with pytest.raises(ReglaPendiente):
        facade.evaluar_intento(id_estudiante=7, id_intento=10)
