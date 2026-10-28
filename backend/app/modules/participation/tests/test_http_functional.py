"""QA funcional: componentes internos reales, solo dependencias externas falsas."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from functools import wraps
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.modules.participation.api.dependencies import EstudianteAutenticado, obtener_estudiante_actual
from app.modules.participation.api.schemas import ErrorHTTP, IntentoRespuesta, ProgresoRespuesta, ResultadoRespuesta
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.application.services import ServicioInicio, ServicioDecisiones, ServicioProgreso, ServicioCierre
from app.modules.participation.domain.calculador_rubrica import CalculadorRubrica
from app.modules.participation.domain.entities import EstadoIntento, Intento, Participacion
from app.modules.participation.domain.estrategias_evaluacion import EvaluacionAusenciaStrategy
from app.modules.participation.tests.evaluation_fakes import RepositorioResultadosFalso
from app.modules.participation.tests.fakes import INICIO, RepositorioFalso, UnidadTrabajoFalsa
from app.modules.participation.tests.http_support import (
    AUSENCIA_URL, DECISION_URL, FIN_URL, INICIO_URL, PROGRESO_URL, RESULTADO_URL, crear_entorno_http,
)


@pytest.fixture
def entorno():
    with crear_entorno_http() as actual:
        yield actual


def test_excepcion_inesperada_no_se_oculta_por_el_router(entorno, monkeypatch):
    def fallar(**datos):
        raise RuntimeError("fallo técnico reproducible")
    monkeypatch.setattr(entorno.facade, "consultar_progreso", fallar)
    with pytest.raises(RuntimeError, match="fallo técnico reproducible"):
        entorno.client.get(PROGRESO_URL)


@dataclass(frozen=True)
class CasoEndpoint:
    nombre: str
    metodo: str
    ruta: str
    cuerpo: dict | None
    exito: int


CASOS = (
    CasoEndpoint("inicio", "POST", INICIO_URL, {"id_consentimiento": 30}, 201),
    CasoEndpoint("registro", "POST", DECISION_URL, {"id_opcion": 60}, 201),
    CasoEndpoint("modificacion", "PUT", DECISION_URL, {"id_opcion": 61}, 200),
    CasoEndpoint("progreso", "GET", PROGRESO_URL, None, 200),
    CasoEndpoint("finalizacion", "POST", FIN_URL, None, 200),
    CasoEndpoint("resultado", "GET", RESULTADO_URL, None, 200),
    CasoEndpoint("ausencia", "GET", AUSENCIA_URL, None, 200),
)


def instantanea(almacen):
    # Agregados inmutables: copias del diccionario conservan el estado confirmado.
    # Se excluyen secuencias de IDs: consumir un ID no equivale a confirmar una fila.
    return (dict(almacen.participaciones), dict(almacen.intentos), dict(almacen.evaluaciones),
            almacen.commits, almacen.escrituras, almacen.inserciones_evaluacion)


def preparar(entorno, caso):
    if caso.nombre in ("resultado",):
        entorno.cerrar()
        assert entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    elif caso.nombre == "ausencia":
        assert not entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20).confirmada
    elif caso.nombre != "inicio":
        entorno.iniciar()
        if caso.nombre != "registro":
            entorno.responder()


def solicitar(client, caso, **cambios):
    ruta = cambios.pop("ruta", caso.ruta)
    datos = {"json": caso.cuerpo} if caso.cuerpo is not None else {}
    datos.update(cambios)
    return client.request(caso.metodo, ruta, **datos)


def sin_notas(datos):
    if isinstance(datos, dict):
        assert not {"nota_final", "puntaje_obtenido", "id_nivel", "es_correcta",
                    "justificacion", "justificacion_teorica", "criterios", "modalidad"}.intersection(datos)
        for valor in datos.values():
            sin_notas(valor)
    elif isinstance(datos, list):
        for valor in datos:
            sin_notas(valor)


def evidencia(record_property, caso, escenario, esperado, obtenido):
    record_property("qa", json.dumps({
        "endpoint": f"{caso.metodo} {caso.ruta}", "escenario": escenario,
        "esperado": esperado, "obtenido": obtenido,
    }, ensure_ascii=False))


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.nombre)
@pytest.mark.parametrize("escenario", ["valido", "invalido", "sin_autorizacion", "repeticion", "fallo_identidad", "cerrado_por_defecto"])
def test_matriz_funcional_siete_endpoints(entorno, caso, escenario, record_property):
    preparar(entorno, caso)
    antes = instantanea(entorno.almacen)
    if escenario == "invalido":
        if caso.nombre == "inicio":
            respuesta = solicitar(entorno.client, caso, json={})
        elif caso.nombre in ("registro", "modificacion"):
            respuesta = solicitar(entorno.client, caso, json={"id_opcion": True})
        else:
            ruta = caso.ruta.replace("/20/", "/0/").replace("/10/", "/0/")
            respuesta = solicitar(entorno.client, caso, ruta=ruta)
        assert respuesta.status_code == 422
        ErrorHTTP.model_validate(respuesta.json())
        assert instantanea(entorno.almacen) == antes
        evidencia(record_property, caso, escenario, "422 sin cambios confirmados", "422; estado y repositorio intactos")
        return
    if escenario in ("sin_autorizacion", "cerrado_por_defecto"):
        if escenario == "sin_autorizacion":
            entorno.app.dependency_overrides[obtener_estudiante_actual] = lambda: EstudianteAutenticado(id_estudiante=8)
            esperado = 403
        else:
            entorno.app.dependency_overrides.clear()
            esperado = 503
        respuesta = solicitar(entorno.client, caso)
        assert respuesta.status_code == esperado
        ErrorHTTP.model_validate(respuesta.json())
        sin_notas(respuesta.json())
        assert instantanea(entorno.almacen) == antes
        evidencia(record_property, caso, escenario, f"{esperado}; sin datos ni cambios", f"{esperado}; esquema y estado verificados")
        return
    if escenario == "fallo_identidad":
        entorno.identity.fallar_en.add("acceso")
        with pytest.raises(RuntimeError, match="Identity no disponible"):
            solicitar(entorno.client, caso)
        with TestClient(entorno.app, raise_server_exceptions=False) as client_http:
            respuesta = solicitar(client_http, caso)
        assert respuesta.status_code == 500 and respuesta.text == "Internal Server Error"
        assert "Identity" not in respuesta.text
        assert instantanea(entorno.almacen) == antes
        evidencia(record_property, caso, escenario, "Excepción observable; HTTP 500 sin detalles ni cambios", "RuntimeError propagado; 500 genérico; estado intacto")
        return

    respuesta = solicitar(entorno.client, caso)
    assert respuesta.status_code == caso.exito, respuesta.text
    datos = respuesta.json()
    if caso.nombre in ("resultado", "ausencia"):
        TypeAdapter(ResultadoRespuesta).validate_python(datos)
        assert instantanea(entorno.almacen) == antes
        if caso.nombre == "resultado":
            assert datos["nota_final"] == "4.00" and datos["modalidad"] == "COMPLETA"
            assert entorno.almacen.inserciones_evaluacion == 1
        else:
            assert datos["estado"] == "PENDIENTE" and datos["id_intento"] is None
            assert not entorno.almacen.intentos and not entorno.almacen.evaluaciones
            sin_notas(datos)
    elif caso.nombre == "progreso":
        ProgresoRespuesta.model_validate(datos)
        assert datos["selecciones"] == [{"id_decision": 50, "id_opcion": 60}]
        assert datos["respondidas"] == 1 and datos["total_aplicable"] == 2 and datos["pendientes"] == [51]
        assert instantanea(entorno.almacen) == antes
        sin_notas(datos)
    else:
        IntentoRespuesta.model_validate(datos)
        intento = entorno.almacen.intentos[datos["id_intento"]]
        assert intento.id_participacion == 20
        assert entorno.almacen.commits == antes[3] + 1
        if caso.nombre == "inicio":
            assert intento.inicio == entorno.reloj.instante and intento.pasos == ()
        elif caso.nombre in ("registro", "modificacion"):
            assert len(intento.pasos) == 1 and intento.pasos[0].id_paso == 40
            assert intento.pasos[0].id_opcion == caso.cuerpo["id_opcion"]
        else:
            assert intento.estado == EstadoIntento.FINALIZADO
            assert intento.fin == entorno.reloj.instante and len(intento.pasos) == 1
        sin_notas(datos)

    if escenario == "repeticion":
        confirmado = instantanea(entorno.almacen)
        politica_llamadas = entorno.politica.llamadas
        repetida = solicitar(entorno.client, caso)
        esperado = {"inicio": 409, "registro": 422}.get(caso.nombre, 200)
        assert repetida.status_code == esperado
        if caso.nombre == "modificacion":
            assert len(entorno.almacen.intentos[10].pasos) == 1
            assert entorno.almacen.intentos[10].pasos[0].id_paso == 40
            assert entorno.almacen.intentos[10].pasos[0].id_opcion == 61
        else:
            assert instantanea(entorno.almacen) == confirmado
        if caso.nombre in ("resultado", "ausencia", "progreso", "finalizacion"):
            assert repetida.json() == datos
        if caso.nombre == "resultado":
            assert entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
            assert entorno.almacen.inserciones_evaluacion == 1
            assert entorno.politica.llamadas == politica_llamadas
        evidencia(record_property, caso, escenario, f"Primera {caso.exito}; repetida {esperado}; sin duplicados", f"{respuesta.status_code}/{repetida.status_code}; dominio y contadores verificados")
    else:
        evidencia(record_property, caso, escenario, f"{caso.exito}; JSON y persistencia coherentes", f"{respuesta.status_code}; esquema, agregado y repositorio verificados")


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c.nombre)
def test_fallo_dependencia_especifica_no_corrompe_estado(entorno, caso, monkeypatch, record_property):
    preparar(entorno, caso)
    antes = instantanea(entorno.almacen)
    if caso.nombre == "inicio":
        entorno.scheduling.fallar_en.add("condiciones")
    elif caso.nombre in ("registro", "modificacion", "progreso"):
        entorno.cases.fallar_en.add({"registro": "opcion", "modificacion": "cambio", "progreso": "recorrido"}[caso.nombre])
    elif caso.nombre == "finalizacion":
        entorno.almacen.fallo_commit = True
    else:
        def fallar(*args, **kwargs):
            raise RuntimeError("Repositorio de prueba no disponible")
        if caso.nombre == "resultado":
            monkeypatch.setattr(RepositorioResultadosFalso, "obtener_definitiva", fallar)
        else:
            monkeypatch.setattr(RepositorioFalso, "listar_intentos", fallar)
    with pytest.raises(RuntimeError):
        solicitar(entorno.client, caso)
    with TestClient(entorno.app, raise_server_exceptions=False) as client_http:
        respuesta = solicitar(client_http, caso)
    assert respuesta.status_code == 500 and respuesta.text == "Internal Server Error"
    assert instantanea(entorno.almacen) == antes
    if caso.nombre == "finalizacion":
        entorno.almacen.fallo_commit = False
        assert solicitar(entorno.client, caso).status_code == 200
        assert entorno.almacen.intentos[10].estado == EstadoIntento.FINALIZADO
    evidencia(record_property, caso, "fallo_dependencia_especifica", "Error observable, rollback; recuperación del cierre", "Excepción y 500 sin detalles; estado anterior preservado")


def registrar_traza(monkeypatch, objeto, metodo, etiqueta, trazas):
    original = getattr(objeto, metodo)
    @wraps(original)
    def ejecutar(*args, **kwargs):
        trazas.append(etiqueta)
        return original(*args, **kwargs)
    monkeypatch.setattr(objeto, metodo, ejecutar)


def test_flujo_funcional_completo_http_con_trazabilidad(entorno, monkeypatch, record_property):
    trazas = []
    iniciar_original = Intento.iniciar.__func__
    def iniciar_dominio(clase, *args, **kwargs):
        trazas.append("Dominio.iniciar")
        return iniciar_original(clase, *args, **kwargs)
    monkeypatch.setattr(Intento, "iniciar", classmethod(iniciar_dominio))
    for clase, metodo, etiqueta in (
        (ParticipacionFacade, "iniciar_intento", "Facade.iniciar"),
        (ServicioInicio, "iniciar", "Servicio.iniciar"),
        (ServicioDecisiones, "guardar", "Servicio.guardar"),
        (ServicioProgreso, "consultar", "Servicio.progreso"),
        (ServicioCierre, "cerrar", "Servicio.cierre"),
        (Intento, "registrar_decision", "Dominio.registrar"),
        (Intento, "modificar_decision", "Dominio.modificar"),
        (Intento, "finalizar", "Dominio.finalizar"),
        (RepositorioFalso, "agregar_intento", "Repositorio.agregar"),
        (RepositorioFalso, "guardar_intento", "Repositorio.guardar"),
        (UnidadTrabajoFalsa, "commit", "UoW.commit"),
        (CalculadorRubrica, "calcular", "Calculador.real"),
        (RepositorioResultadosFalso, "agregar_definitiva", "Resultados.insertar"),
    ):
        registrar_traza(monkeypatch, clase, metodo, etiqueta, trazas)

    # La participación se materializa por el fake, no mediante un endpoint inventado.
    entorno.almacen.participaciones.clear()
    entorno.almacen.participaciones[20] = Participacion(20, 100, 200, "REGISTRADA", INICIO)
    assert not entorno.almacen.intentos
    inicio = entorno.iniciar()
    assert trazas[:5] == ["Facade.iniciar", "Servicio.iniciar", "Dominio.iniciar", "Repositorio.agregar", "UoW.commit"]
    assert inicio.json()["estado"] == "EN_CURSO"
    entorno.reloj.instante += timedelta(seconds=10)
    entorno.responder()
    segunda = entorno.client.post("/api/v1/attempts/10/decisions/51", json={"id_opcion": 63})
    assert segunda.status_code == 201
    progreso = entorno.client.get(PROGRESO_URL)
    assert progreso.status_code == 200 and progreso.json()["respondidas"] == 2
    sin_notas(progreso.json())
    anterior = entorno.almacen.intentos[10]
    entorno.reloj.instante += timedelta(seconds=10)
    cambio = entorno.client.put(DECISION_URL, json={"id_opcion": 61})
    assert cambio.status_code == 200
    actual = entorno.almacen.intentos[10]
    assert len(actual.pasos) == 2
    assert actual.pasos[0].id_paso == anterior.pasos[0].id_paso
    assert anterior.pasos[0].id_opcion == 60 and actual.pasos[0].id_opcion == 61
    assert actual.pasos[1] == anterior.pasos[1]
    fin = entorno.client.post(FIN_URL)
    assert fin.status_code == 200
    assert entorno.almacen.intentos[10].fin == entorno.reloj.instante
    assert entorno.almacen.intentos[10].estado == EstadoIntento.FINALIZADO
    guardado = instantanea(entorno.almacen)
    rechazo = entorno.client.put(DECISION_URL, json={"id_opcion": 60})
    assert rechazo.status_code == 409 and instantanea(entorno.almacen) == guardado
    repetido = entorno.client.post(FIN_URL)
    assert repetido.json() == fin.json() and instantanea(entorno.almacen) == guardado
    pendiente = entorno.client.get(RESULTADO_URL)
    assert pendiente.json()["estado"] == "PENDIENTE"
    sin_notas(pendiente.json())
    assert entorno.politica.llamadas == 0
    # No existe un endpoint de generación de notas: el disparo backend es explícito.
    assert entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    resultado = entorno.client.get(RESULTADO_URL)
    TypeAdapter(ResultadoRespuesta).validate_python(resultado.json())
    assert resultado.json()["estado"] == "DEFINITIVA"
    # Fixture explícita: 5*.60*.50 + 5*.40*.50 = 2.50, calculado por código real.
    assert resultado.json()["nota_final"] == "2.50"
    assert [c.puntaje_obtenido for c in entorno.almacen.evaluaciones[(20, 10)].criterios] == [Decimal("1.5"), Decimal("1")]
    commits = entorno.almacen.commits
    assert entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    assert entorno.client.get(RESULTADO_URL).json() == resultado.json()
    assert entorno.almacen.inserciones_evaluacion == 1 and entorno.almacen.commits == commits
    for requerido in ("Servicio.guardar", "Dominio.registrar", "Dominio.modificar", "Servicio.progreso",
                      "Dominio.finalizar", "Repositorio.guardar", "Calculador.real", "Resultados.insertar"):
        assert requerido in trazas
    assert trazas.index("Servicio.guardar") < trazas.index("Dominio.registrar") < trazas.index("Repositorio.guardar")
    record_property("traza_capas", json.dumps(trazas))
    evidencia(record_property, CASOS[5], "flujo_completo", "Flujo HTTP con 2 selecciones, cierre único y nota ficticia 2.50 confirmada", "Todas las etapas verificadas; dominio real; un resultado definitivo; 2.50")


def test_parcial_pendiente_y_politica_explicita_por_http(entorno, record_property):
    entorno.cerrar(completo=False)
    assert not entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    pendiente = entorno.client.get(RESULTADO_URL)
    assert pendiente.status_code == 200 and pendiente.json()["estado"] == "PENDIENTE"
    sin_notas(pendiente.json())
    assert not entorno.almacen.evaluaciones
    entorno.politica.parcial_definida = True  # Aprobación exclusiva de esta fixture.
    assert entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    resultado = entorno.client.get(RESULTADO_URL)
    assert resultado.status_code == 200 and resultado.json()["modalidad"] == "PARCIAL"
    assert resultado.json()["nota_final"] == "3.00"
    assert len(entorno.almacen.intentos[10].pasos) == 1
    assert entorno.almacen.inserciones_evaluacion == 1
    evidencia(record_property, CASOS[5], "parcial_y_politica_explicita", "Pendiente sin nota; con política de prueba: PARCIAL 3.00", "200 PENDIENTE → 200 DEFINITIVA PARCIAL 3.00; una inserción")


def test_ausencia_usa_strategy_real_sin_intento_y_no_publica_cero_ficticio(entorno, monkeypatch, record_property):
    capturados = []
    original = EvaluacionAusenciaStrategy.preparar
    def preparar_ausencia(self, contexto):
        datos = original(self, contexto)
        capturados.append(datos)
        return datos
    monkeypatch.setattr(EvaluacionAusenciaStrategy, "preparar", preparar_ausencia)
    estado = entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20)
    assert not estado.confirmada and estado.id_intento is None
    assert capturados[0].id_intento is None
    assert [e.cero_por_ausencia for e in capturados[0].evidencias] == [Decimal(0), Decimal(0)]
    antes = instantanea(entorno.almacen)
    uno, dos = entorno.client.get(AUSENCIA_URL), entorno.client.get(AUSENCIA_URL)
    assert uno.status_code == dos.status_code == 200 and uno.json() == dos.json()
    assert uno.json()["estado"] == "PENDIENTE"
    assert instantanea(entorno.almacen) == antes
    assert entorno.almacen.siguiente_intento == 10 and not entorno.almacen.intentos
    assert not entorno.almacen.evaluaciones
    sin_notas(uno.json())
    evidencia(record_property, CASOS[6], "strategy_ausencia_real", "Ceros internos sin intento; publicación pendiente por ER", "Dos ceros de Strategy real; HTTP PENDIENTE; cero intentos y evaluaciones definitivas")


def test_vencimiento_y_fallo_recorrido_no_pierden_respuestas(entorno):
    entorno.iniciar()
    entorno.responder()
    antes = instantanea(entorno.almacen)
    entorno.reloj.instante += timedelta(minutes=10)
    entorno.cases.fallar_en.add("recorrido")
    with pytest.raises(RuntimeError):
        entorno.client.get(PROGRESO_URL)
    assert instantanea(entorno.almacen) == antes
    # El tiempo se valida aun cuando la consulta fallida no confirmó VENCIDO.
    assert entorno.client.put(DECISION_URL, json={"id_opcion": 61}).status_code == 409
    assert entorno.almacen.intentos[10].estado == EstadoIntento.VENCIDO
    assert entorno.almacen.intentos[10].pasos[0].id_opcion == 60
