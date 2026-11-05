"""Pruebas HTTP aisladas: router provisional + fachada real + adaptadores falsos."""

from datetime import timedelta

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.modules.participation.api.dependencies import (
    EstudianteAutenticado, obtener_estudiante_actual, obtener_facade,
)
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.tests.fakes import SchedulingFalso
from app.modules.participation.tests.http_support import (
    AUSENCIA_URL, DECISION_URL, FIN_URL, INICIO_URL, PROGRESO_URL, RESULTADO_URL, crear_entorno_http,
)


@pytest.fixture
def entorno():
    with crear_entorno_http() as actual:
        yield actual


def sin_datos_academicos(datos):
    if isinstance(datos, dict):
        assert not {
            "nota_final", "puntaje_obtenido", "id_nivel", "es_correcta",
            "justificacion", "justificacion_teorica", "criterios", "modalidad", "evaluacion",
        }.intersection(datos)
        for valor in datos.values():
            sin_datos_academicos(valor)
    elif isinstance(datos, list):
        for valor in datos:
            sin_datos_academicos(valor)


def test_inicio_usa_identidad_inyectada_y_devuelve_recurso_creado(entorno):
    respuesta = entorno.iniciar()
    cuerpo = respuesta.json()
    assert cuerpo["id_intento"] == 10
    assert cuerpo["id_participacion"] == 20
    assert cuerpo["estado"] == "EN_CURSO"
    assert cuerpo["inicio"].endswith("Z")
    assert respuesta.headers["cache-control"] == "no-store"
    sin_datos_academicos(cuerpo)


@pytest.mark.parametrize("cuerpo", [
    {}, {"id_consentimiento": 0}, {"id_consentimiento": -1},
    {"id_consentimiento": True}, {"id_consentimiento": 30.5},
    {"id_consentimiento": "30"}, {"id_consentimiento": None},
    {"id_consentimiento": 30, "student_id": 8},
    {"id_consentimiento": 30, "id_estudiante": 8},
    {"id_consentimiento": 30, "estado": "FINALIZADO"},
    {"id_consentimiento": 30, "id_permiso_extra": False},
])
def test_validacion_de_inicio_no_crea_intento(entorno, cuerpo):
    respuesta = entorno.client.post(INICIO_URL, json=cuerpo)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "SOLICITUD_INVALIDA"
    assert entorno.almacen.intentos == {}


@pytest.mark.parametrize("cuerpo", [
    {}, {"id_opcion": 0}, {"id_opcion": True}, {"id_opcion": 60.1},
    {"id_opcion": "60"}, {"id_opcion": 60, "reflexion_estudiante": 123},
    {"id_opcion": 60, "nota_final": "5.0"},
    {"id_opcion": 60, "tiempo_segundos": 0},
])
def test_validacion_de_seleccion_no_modifica_dominio(entorno, cuerpo):
    entorno.iniciar()
    respuesta = entorno.client.post(DECISION_URL, json=cuerpo)
    assert respuesta.status_code == 422
    assert entorno.almacen.intentos[10].pasos == ()


def test_error_validacion_no_refleja_valores_privados_del_cliente(entorno):
    respuesta = entorno.client.post(INICIO_URL, json={"id_consentimiento": 30, "secreto": "NO_REPETIR_SECRETO"})
    assert respuesta.status_code == 422
    assert "NO_REPETIR_SECRETO" not in respuesta.text
    assert "body.secreto" in respuesta.json()["detail"]["campos"]


def test_json_invalido_se_traduce_sin_reflejar_cuerpo(entorno):
    respuesta = entorno.client.post(
        INICIO_URL, content='{"id_consentimiento":SECRETO}',
        headers={"Content-Type": "application/json"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "SOLICITUD_INVALIDA"
    assert "SECRETO" not in respuesta.text
    assert entorno.almacen.intentos == {}


def test_inicio_de_participacion_ajena_es_rechazado(entorno):
    respuesta = entorno.client.post("/api/v1/participations/21/attempts", json={"id_consentimiento": 30})
    assert respuesta.status_code == 403
    assert entorno.almacen.intentos == {}


@pytest.mark.parametrize("ruta", [
    "/api/v1/attempts/0/progress", "/api/v1/attempts/-1/progress",
    "/api/v1/attempts/abc/progress",
])
def test_validacion_de_identificadores_de_ruta(entorno, ruta):
    assert entorno.client.get(ruta).status_code == 422


def test_registro_modificacion_y_progreso_usan_fachada_real(entorno):
    entorno.iniciar()
    entorno.responder()
    respuesta = entorno.client.put(DECISION_URL, json={"id_opcion": 61, "reflexion_estudiante": "Revisé mi elección"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "RESPUESTA_INMUTABLE"
    assert entorno.almacen.intentos[10].pasos[0].reflexion_estudiante is None
    progreso = entorno.client.get(PROGRESO_URL)
    assert progreso.status_code == 200
    assert progreso.json()["selecciones"] == [{"id_decision": 50, "id_opcion": 60}]
    assert progreso.json()["respondidas"] == 1
    assert progreso.json()["pendientes"] == [51]
    assert progreso.json()["total_aplicable"] == 2
    sin_datos_academicos(progreso.json())


def test_progreso_no_inventa_total_en_ruta_ramificada(entorno):
    entorno.cases.ramificado = True
    entorno.iniciar()
    respuesta = entorno.client.get(PROGRESO_URL)
    assert respuesta.status_code == 200
    assert respuesta.json()["total_aplicable"] is None
    assert respuesta.json()["decisiones_aplicables"] == [50]
    sin_datos_academicos(respuesta.json())


def test_post_duplicado_no_crea_otra_seleccion_y_put_no_es_upsert(entorno):
    entorno.iniciar()
    respuesta = entorno.client.put(DECISION_URL, json={"id_opcion": 60})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "RESPUESTA_INMUTABLE"
    entorno.responder()
    assert entorno.client.post(DECISION_URL, json={"id_opcion": 61}).status_code == 409
    assert len(entorno.almacen.intentos[10].pasos) == 1


def test_no_acepta_decision_fuera_del_recorrido(entorno):
    entorno.iniciar()
    respuesta = entorno.client.post("/api/v1/attempts/10/decisions/99", json={"id_opcion": 98})
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "ACCESO_DENEGADO"


def test_cambio_de_ruta_pendiente_no_borra_respuestas(entorno):
    entorno.cases.ramificado = True
    entorno.iniciar()
    entorno.responder()
    entorno.client.post("/api/v1/attempts/10/decisions/51", json={"id_opcion": 62})
    anteriores = entorno.almacen.intentos[10].pasos
    respuesta = entorno.client.put(DECISION_URL, json={"id_opcion": 61})
    assert respuesta.status_code == 409
    assert entorno.almacen.intentos[10].pasos == anteriores
    sin_datos_academicos(respuesta.json())


@pytest.mark.parametrize("modificar", [False, True])
def test_intento_finalizado_rechaza_cambios(entorno, modificar):
    entorno.cerrar()
    respuesta = (
        entorno.client.put(DECISION_URL, json={"id_opcion": 61}) if modificar else
        entorno.client.post("/api/v1/attempts/10/decisions/52", json={"id_opcion": 64})
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "INTENTO_NO_EDITABLE"


def test_vencimiento_rechaza_cambio_y_conserva_respuesta(entorno):
    entorno.iniciar()
    entorno.responder()
    entorno.reloj.instante += timedelta(minutes=10)
    respuesta = entorno.client.put(DECISION_URL, json={"id_opcion": 61})
    assert respuesta.status_code == 409
    assert entorno.almacen.intentos[10].estado == EstadoIntento.VENCIDO
    assert entorno.almacen.intentos[10].pasos[0].id_opcion == 60
    progreso = entorno.client.get(PROGRESO_URL)
    assert progreso.json()["intento"]["estado"] == "VENCIDO"
    sin_datos_academicos(progreso.json())


def test_finalizacion_http_es_idempotente(entorno):
    entorno.iniciar()
    entorno.responder()
    uno = entorno.client.post(FIN_URL)
    commits = entorno.almacen.commits
    entorno.reloj.instante += timedelta(hours=1)
    dos = entorno.client.post(FIN_URL)
    assert uno.status_code == dos.status_code == 200
    assert uno.json() == dos.json()
    assert entorno.almacen.commits == commits
    assert entorno.almacen.evaluaciones == {}
    sin_datos_academicos(uno.json())


def test_inicio_repetido_en_curso_es_conflicto(entorno):
    entorno.iniciar()
    assert entorno.client.post(INICIO_URL, json={"id_consentimiento": 30}).status_code == 409
    assert len(entorno.almacen.intentos) == 1


def test_resultado_prematuro_no_devuelve_informacion_academica(entorno):
    entorno.iniciar()
    entorno.responder()
    respuesta = entorno.client.get(RESULTADO_URL)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "EVALUACION_NO_DISPONIBLE"
    sin_datos_academicos(respuesta.json())


def test_cerrado_sin_evaluacion_confirmada_devuelve_pendiente_sin_calcular(entorno):
    entorno.cerrar()
    commits = entorno.almacen.commits
    respuesta = entorno.client.get(RESULTADO_URL)
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "estado": "PENDIENTE", "id_participacion": 20, "id_intento": 10,
        "codigo": "EVALUACION_NO_CONFIRMADA",
        "mensaje": "Todavía no hay una evaluación persistida y confirmada.",
    }
    assert entorno.politica.llamadas == 0
    assert entorno.almacen.commits == commits
    sin_datos_academicos(respuesta.json())


def test_motor_no_configurado_no_se_disfraza_de_evaluacion_pendiente(entorno):
    entorno.cerrar()
    facade = ParticipacionFacade(
        fabrica=entorno.almacen.unidad, identity=entorno.identity, cases=entorno.cases,
        scheduling=SchedulingFalso(), reloj=entorno.reloj,
    )
    entorno.app.dependency_overrides[obtener_facade] = lambda: facade
    respuesta = entorno.client.get(RESULTADO_URL)
    assert respuesta.status_code == 503
    assert respuesta.json()["detail"]["codigo"] == "INTEGRACION_O_POLITICA_PENDIENTE"
    sin_datos_academicos(respuesta.json())


def test_resultado_definitivo_solo_despues_de_commit_autorizado(entorno):
    entorno.cerrar()
    assert entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    respuesta = entorno.client.get(RESULTADO_URL)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "DEFINITIVA"
    assert datos["modalidad"] == "COMPLETA"
    assert datos["nota_final"] == "4.00"  # Política ficticia, cálculo real.
    assert datos["criterios"][0]["puntaje_obtenido"] == "3"
    assert datos["referencia"]["version"] == "referencia-ficticia-v1"
    assert "evidencias" not in datos and "pendientes" not in datos
    assert respuesta.headers["cache-control"] == "no-store"


def test_resultado_parcial_distingue_modalidad_de_estado_de_ejecucion(entorno):
    entorno.cerrar(completo=False)
    entorno.politica.parcial_definida = True  # Solo política explícita de prueba.
    entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10)
    datos = entorno.client.get(RESULTADO_URL).json()
    assert datos["estado"] == "DEFINITIVA"
    assert datos["modalidad"] == "PARCIAL"
    assert datos["nota_final"] == "3.00"


def test_politica_parcial_pendiente_no_expone_nota(entorno):
    entorno.cerrar(completo=False)
    assert not entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10).confirmada
    respuesta = entorno.client.get(RESULTADO_URL)
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "PENDIENTE"
    sin_datos_academicos(respuesta.json())


def test_ausencia_pendiente_no_fabrica_intento_ni_nota(entorno):
    estado = entorno.facade.evaluar_ausencia(id_estudiante=7, id_participacion=20)
    assert not estado.confirmada
    respuesta = entorno.client.get(AUSENCIA_URL)
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "PENDIENTE"
    assert respuesta.json()["id_intento"] is None
    assert entorno.almacen.intentos == {}
    sin_datos_academicos(respuesta.json())


def test_resultado_inexistente_no_se_confunde_con_evaluacion_pendiente(entorno):
    respuesta = entorno.client.get("/api/v1/participations/20/attempts/999/result")
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["codigo"] == "RECURSO_NO_DISPONIBLE"


@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("post", INICIO_URL, {"id_consentimiento": 30}),
    ("post", DECISION_URL, {"id_opcion": 60}),
    ("put", DECISION_URL, {"id_opcion": 61}),
    ("get", PROGRESO_URL, None), ("post", FIN_URL, None),
    ("get", RESULTADO_URL, None), ("get", AUSENCIA_URL, None),
])
def test_cerrados_por_defecto_aun_si_router_se_registrara_accidentalmente(entorno, metodo, ruta, cuerpo):
    entorno.app.dependency_overrides.clear()
    datos = {"json": cuerpo} if cuerpo is not None else {}
    respuesta = entorno.client.request(metodo, ruta, **datos)
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["codigo"] == "NO_AUTENTICADO"
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert entorno.almacen.intentos == {}


def test_override_facade_solo_no_elimina_exigencia_de_identidad(entorno):
    del entorno.app.dependency_overrides[obtener_estudiante_actual]
    respuesta = entorno.client.post(INICIO_URL, json={"id_consentimiento": 30})
    assert respuesta.status_code == 401
    assert entorno.almacen.commits == 0


def test_identidad_sola_no_habilita_adaptadores_inexistentes(entorno):
    del entorno.app.dependency_overrides[obtener_facade]
    respuesta = entorno.client.post(INICIO_URL, json={"id_consentimiento": 30})
    assert respuesta.status_code == 503
    assert respuesta.json()["detail"]["codigo"] == "INTEGRACION_NO_CONFIGURADA"


def test_headers_y_query_de_identidad_no_autentican(entorno):
    from app.modules.identity.api.dependencies import obtener_fabrica_tokens
    from app.modules.identity.infrastructure.security import TokensJWT

    entorno.app.dependency_overrides.clear()
    tokens = TokensJWT("clave-solo-tests-participation-8a-" * 2, "tests", "tests")
    entorno.app.dependency_overrides[obtener_fabrica_tokens] = lambda: lambda: tokens
    respuesta = entorno.client.post(
        INICIO_URL + "?student_id=7", json={"id_consentimiento": 30},
        headers={"X-Student-ID": "7", "Authorization": "Bearer token-inventado"},
    )
    assert respuesta.status_code == 401
    assert entorno.almacen.intentos == {}


@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("post", DECISION_URL, {"id_opcion": 61}),
    ("put", DECISION_URL, {"id_opcion": 61}),
    ("get", PROGRESO_URL, None), ("post", FIN_URL, None),
    ("get", RESULTADO_URL, None), ("get", AUSENCIA_URL, None),
])
def test_id_url_no_permite_acceso_a_otro_estudiante(entorno, metodo, ruta, cuerpo):
    entorno.cerrar()
    entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10)
    entorno.app.dependency_overrides[obtener_estudiante_actual] = lambda: EstudianteAutenticado(id_estudiante=8)
    datos = {"json": cuerpo} if cuerpo is not None else {}
    respuesta = entorno.client.request(metodo, ruta, **datos)
    assert respuesta.status_code == 403
    sin_datos_academicos(respuesta.json())


def test_participacion_propietaria_en_url_no_autoriza_otro_intento(entorno):
    entorno.iniciar()
    otro = entorno.facade.iniciar_intento(id_estudiante=8, id_participacion=21, id_consentimiento=30)
    entorno.facade.finalizar(id_estudiante=8, id_intento=otro.id_intento)
    respuesta = entorno.client.get(f"/api/v1/participations/20/attempts/{otro.id_intento}/result")
    assert respuesta.status_code == 409
    sin_datos_academicos(respuesta.json())


def test_error_tecnico_no_expone_mensajes_de_adaptadores(entorno, monkeypatch):
    def fallar(**datos):
        raise RuntimeError("password=SECRETO SQL es_correcta=True puntaje=5")
    monkeypatch.setattr(entorno.facade, "consultar_progreso", fallar)
    # Solo este cliente deliberadamente observa el límite HTTP de un fallo.
    # El cliente normal continúa propagando excepciones para detectar defectos.
    with TestClient(entorno.app, raise_server_exceptions=False) as client:
        respuesta = client.get(PROGRESO_URL)
    assert respuesta.status_code == 500
    assert respuesta.text == "Internal Server Error"
    assert "SECRETO" not in respuesta.text and "SQL" not in respuesta.text


def test_conflicto_de_persistencia_no_devuelve_exito(entorno):
    entorno.iniciar()
    entorno.almacen.conflicto = True
    respuesta = entorno.client.post(DECISION_URL, json={"id_opcion": 60})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "CONFLICTO_ACTUALIZACION"
    assert entorno.almacen.intentos[10].pasos == ()


def test_commit_fallido_no_hace_visible_candidato(entorno):
    entorno.cerrar()
    entorno.almacen.fallo_commit = True
    with pytest.raises(RuntimeError):
        entorno.facade.evaluar_intento(id_estudiante=7, id_intento=10)
    respuesta = entorno.client.get(RESULTADO_URL)
    assert respuesta.json()["estado"] == "PENDIENTE"
    sin_datos_academicos(respuesta.json())


def test_errores_de_autenticacion_real_se_pueden_inyectar_sin_jwt_alternativo(entorno):
    def no_autenticado():
        raise HTTPException(status_code=401, detail={"codigo": "NO_AUTENTICADO", "mensaje": "Se requiere autenticación."})
    entorno.app.dependency_overrides[obtener_estudiante_actual] = no_autenticado
    respuesta = entorno.client.get(PROGRESO_URL)
    assert respuesta.status_code == 401
    assert entorno.almacen.commits == 0


def test_openapi_aislado_marca_contrato_provisional_y_separa_resultados(entorno):
    contrato = entorno.app.openapi()
    rutas = contrato["paths"]
    assert len(rutas) == 7  # Nueva consulta privada; POST/PUT comparten ruta de decisión.
    for metodos in rutas.values():
        for operacion in metodos.values():
            assert "Provisional" in operacion["summary"]
    esquema = rutas[RESULTADO_URL.replace("20", "{participation_id}").replace("10", "{attempt_id}")]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert esquema["discriminator"]["propertyName"] == "estado"
    assert "student_id" not in str(contrato["components"]["schemas"]["InicioIntentoSolicitud"])
    actual = rutas['/api/v1/attempts/{attempt_id}/current-scenario']['get']
    assert actual['security'] == [{'HTTPBearer': []}]
    assert set(contrato['components']['schemas']['EscenarioActualRespuesta']['properties']) == {
        'id_escenario', 'contexto', 'pregunta', 'recorrido_finalizado', 'respondidas'}
    assert set(contrato['components']['schemas']['OpcionActualRespuesta']['properties']) == {'id', 'texto'}


def test_router_completo_no_registrado_y_solo_get_escenario_habilitado(entorno):
    from app.main import app
    # Verificar el contrato expandido, sin depender de contenedores internos
    # de FastAPI al incluir el router de lectura reutilizado.
    rutas_participacion = set(entorno.app.openapi()['paths'])
    consulta = '/api/v1/attempts/{attempt_id}/current-scenario'
    assert rutas_participacion.intersection(app.openapi()["paths"]) == {consulta}
    assert set(app.openapi()['paths'][consulta]) == {'get'}
    with TestClient(app) as client:
        assert client.get(PROGRESO_URL).status_code == 404
        assert client.get("/health").status_code == 200
