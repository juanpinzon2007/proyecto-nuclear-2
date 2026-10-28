from dataclasses import replace
from decimal import Decimal
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import jwt
import pytest

from app.modules.identity.api.dependencies import (
    obtener_fabrica_autenticacion, obtener_proxy_administracion,
    obtener_proxy_excepciones, obtener_proxy_seguimiento,
)
from app.modules.identity.api.router import router
from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.application.ports import LecturaReportes, LecturaSeguimiento, ValidadorConvocatoria
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.proxy_excepciones import ProxyExcepciones
from app.modules.identity.application.proxy_seguimiento import ProxySeguimiento
from app.modules.identity.application.services import (
    ServicioAdministracionUsuarios, ServicioExcepciones, ServicioFeedbackDocente,
    ServicioReportes, ServicioSeguimiento,
)
from app.modules.identity.domain.entities import (
    AccesoConvocatoria, CondicionesRepeticion, DetalleParticipacion,
    EstadoReporte, FilaReporte, RespuestaSeguimiento, ResumenCaso,
)


BASE = "/api/v1/identity"
REPETICIONES = BASE + "/excepciones/repeticiones"


@pytest.fixture
def servicios(aplicacion, escenario):
    lecturas = Mock(spec=LecturaSeguimiento)
    lecturas.listar_casos_realizados.return_value = (ResumenCaso("c1", "Caso realizado"),)
    lecturas.consultar_participacion.return_value = DetalleParticipacion(
        "p1", "estudiante-1", "c1", (RespuestaSeguimiento("q1", "o1", "Explicación"),), "Valoración docente",
    )
    reportes = Mock(spec=LecturaReportes)
    reportes.obtener_filas.return_value = (
        FilaReporte("estudiante-1", "p1", EstadoReporte.PARCIAL, Decimal("2.50")),
        FilaReporte("estudiante-2", None, EstadoReporte.AUSENCIA, None),
    )
    seguimiento = ServicioSeguimiento(lecturas, ServicioReportes(reportes), ServicioFeedbackDocente(lambda: escenario.trabajo))
    excepciones = ServicioExcepciones(lambda: escenario.trabajo)
    administracion = ServicioAdministracionUsuarios(lambda: escenario.trabajo)
    aplicacion.dependency_overrides[obtener_proxy_seguimiento] = lambda: ProxySeguimiento(lambda: seguimiento, escenario.autorizacion)
    aplicacion.dependency_overrides[obtener_proxy_excepciones] = lambda: ProxyExcepciones(lambda: excepciones, escenario.autorizacion)
    aplicacion.dependency_overrides[obtener_proxy_administracion] = lambda: ProxyAdministracionUsuarios(lambda: administracion, escenario.autorizacion)
    return lecturas, reportes


def test_http_403_estudiante_intenta_autorizar_repeticion_excepcional(cliente, escenario, cabeceras):
    # JWT y resolución de usuario reales; ProxyExcepciones de producción.
    # No se sustituye obtener_usuario_actual ni se configura el servicio real.
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "estudiante-1"},
                             headers=cabeceras(escenario.estudiante))
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"]["codigo"] == "ACCESO_DENEGADO"
    assert respuesta.headers["cache-control"] == "no-store"
    escenario.trabajo.autorizaciones.guardar.assert_not_called()
    escenario.academia.condiciones_repeticion.assert_not_called()


@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("GET", "/seguimiento/casos", None),
    ("GET", "/seguimiento/participaciones/p1", None),
    ("GET", "/seguimiento/sesiones/s1/reporte", None),
    ("POST", "/seguimiento/participaciones/p1/feedback", {"texto": "Comentario"}),
    ("POST", "/docentes", {"correo": "nuevo@universidad.test"}),
    ("PUT", "/docentes/docente-1/autorizaciones", {"roles": ["DOCENTE"], "permisos": []}),
])
def test_estudiante_recibe_403_en_operaciones_docentes_y_administrativas(cliente, escenario, cabeceras, metodo, ruta, cuerpo):
    respuesta = cliente.request(metodo, BASE + ruta, json=cuerpo, headers=cabeceras(escenario.estudiante))
    assert respuesta.status_code == 403


@pytest.mark.parametrize("cabecera", [None, "Basic credenciales", "Bearer invalido"])
def test_sin_credenciales_verificables_devuelve_401(cliente, cabecera):
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"},
                             headers={} if cabecera is None else {"Authorization": cabecera})
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_no_acepta_identidad_en_headers_o_query(cliente):
    respuesta = cliente.post(REPETICIONES + "?id_usuario=admin-1", json={"id_sesion": "s1", "id_estudiante": "e1"},
                             headers={"X-User-ID": "admin-1", "X-Role": "ADMINISTRADOR"})
    assert respuesta.status_code == 401


def test_jwt_no_es_fuente_de_roles(cliente, tokens, escenario):
    token = tokens.emitir("estudiante-1", "convocatoria-1")
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["roles"] = ["ADMINISTRADOR", "DOCENTE"]
    token = jwt.encode(claims, "clave-de-pruebas-aisladas-" * 3, algorithm="HS256")
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"},
                             headers={"Authorization": "Bearer " + token})
    assert respuesta.status_code == 403


def test_roles_y_permisos_se_recargan_del_servidor(cliente, tokens, escenario):
    token = tokens.emitir("docente-1")
    escenario.identidades["docente-1"] = replace(escenario.docente, roles=frozenset())
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"},
                             headers={"Authorization": "Bearer " + token})
    assert respuesta.status_code == 403


@pytest.mark.parametrize("cambio", ["eliminado", "inactivo"])
def test_usuario_eliminado_o_inactivo_pierde_acceso(cliente, escenario, cabeceras, cambio):
    headers = cabeceras(escenario.docente)
    escenario.identidades["docente-1"] = None if cambio == "eliminado" else replace(escenario.docente, activo=False)
    assert cliente.get(BASE + "/me", headers=headers).status_code == 401


def test_estudiante_necesita_contexto_convocatoria_en_su_jwt(cliente, tokens):
    respuesta = cliente.get(BASE + "/me", headers={"Authorization": "Bearer " + tokens.emitir("estudiante-1")})
    assert respuesta.status_code == 401


def test_login_http_emite_jwt_tras_validar_correo_y_codigo(aplicacion, cliente, escenario, tokens):
    convocatorias = Mock(spec=ValidadorConvocatoria)
    convocatorias.validar.return_value = AccesoConvocatoria("estudiante-1", "convocatoria-1")
    servicio = ServicioAutenticacion(escenario.usuarios, convocatorias, tokens, ("universidad.test",))
    aplicacion.dependency_overrides[obtener_fabrica_autenticacion] = lambda: lambda: servicio
    respuesta = cliente.post(BASE + "/auth/estudiantes", json={
        "correo": "alumno@universidad.test", "codigo_convocatoria": "codigo-de-prueba",
    })
    assert respuesta.status_code == 200
    assert tokens.verificar(respuesta.json()["access_token"]).id_usuario == "estudiante-1"
    assert "codigo-de-prueba" not in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"


def test_validacion_no_revela_codigo_ni_valores_rechazados(cliente):
    secreto = "codigo-que-no-debe-aparecer"
    respuesta = cliente.post(BASE + "/auth/estudiantes", json={
        "correo": "alumno@universidad.test", "codigo_convocatoria": secreto, "rol": "ADMINISTRADOR",
    })
    assert respuesta.status_code == 422
    assert secreto not in respuesta.text and "ADMINISTRADOR" not in respuesta.text


def test_produccion_sin_adaptadores_no_simula_login():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as cliente:
        respuesta = cliente.post(BASE + "/auth/estudiantes", json={
            "correo": "alumno@universidad.test", "codigo_convocatoria": "inventado",
        })
        assert respuesta.status_code == 503
        assert "access_token" not in respuesta.json()
        assert cliente.get(BASE + "/me").status_code == 401


def test_docente_con_identidad_valida_sin_adaptador_recibe_503(cliente, escenario, cabeceras):
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 503


def test_docente_creador_puede_conceder_repeticion_con_servicio_real(cliente, servicios, escenario, cabeceras):
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 201
    assert respuesta.json()["id_docente_autorizador"] == "docente-1"
    escenario.trabajo.autorizaciones.guardar.assert_called_once()
    escenario.trabajo.commit.assert_called_once()


@pytest.mark.parametrize("condiciones,estado", [
    (CondicionesRepeticion(False, True, False), 403),
    (CondicionesRepeticion(True, True, True), 409),
    (CondicionesRepeticion(True, False, False), 409),
])
def test_repeticion_respeta_reglas_academicas(cliente, servicios, escenario, cabeceras, condiciones, estado):
    escenario.academia.condiciones_repeticion.return_value = condiciones
    respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == estado
    escenario.trabajo.autorizaciones.guardar.assert_not_called()


def test_docente_no_puede_consultar_participacion_ajena(cliente, servicios, escenario, cabeceras):
    escenario.academia.puede_consultar_participacion.return_value = False
    respuesta = cliente.get(BASE + "/seguimiento/participaciones/ajena", headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 403
    servicios[0].consultar_participacion.assert_not_called()


def test_consulta_detalle_y_casos_mediante_proxy(cliente, servicios, escenario, cabeceras):
    headers = cabeceras(escenario.docente)
    assert cliente.get(BASE + "/seguimiento/casos", headers=headers).json() == [{"id_caso": "c1", "nombre": "Caso realizado"}]
    respuesta = cliente.get(BASE + "/seguimiento/participaciones/p1", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.json()["respuestas"][0]["retroalimentacion"] == "Explicación"
    servicios[0].consultar_participacion.assert_called_once_with("docente-1", "p1")


def test_descarga_csv_incluye_parciales_y_ausentes(cliente, servicios, escenario, cabeceras):
    respuesta = cliente.get(BASE + "/seguimiento/sesiones/s1/reporte", headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert "attachment" in respuesta.headers["content-disposition"]
    assert "PARCIAL,2.50" in respuesta.text and "AUSENCIA," in respuesta.text


def test_reporte_fuera_del_ambito_no_consulta_datos(cliente, servicios, escenario, cabeceras):
    escenario.academia.puede_consultar_sesion.return_value = False
    respuesta = cliente.get(BASE + "/seguimiento/sesiones/ajena/reporte", headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 403
    servicios[1].obtener_filas.assert_not_called()


def test_feedback_http_usa_autor_autenticado(cliente, servicios, escenario, cabeceras):
    respuesta = cliente.post(BASE + "/seguimiento/participaciones/p1/feedback", json={"texto": "Buen análisis"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 201
    assert respuesta.json()["id_docente"] == "docente-1"
    escenario.trabajo.feedback.agregar.assert_called_once()


def test_feedback_no_acepta_suplantacion_de_autor(cliente, servicios, escenario, cabeceras):
    respuesta = cliente.post(BASE + "/seguimiento/participaciones/p1/feedback", json={"texto": "Comentario", "id_docente": "otro"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 422
    escenario.trabajo.feedback.agregar.assert_not_called()


def test_administrador_crea_docente_y_asigna_permisos(cliente, servicios, escenario, cabeceras):
    escenario.usuarios.crear_docente.return_value = escenario.docente
    respuesta = cliente.post(BASE + "/docentes", json={"correo": "Docente@Universidad.Test", "permisos": ["CREAR_CASOS"]}, headers=cabeceras(escenario.administrador))
    assert respuesta.status_code == 201
    assert escenario.usuarios.crear_docente.call_args.args[0] == "docente@universidad.test"
    assert escenario.usuarios.crear_docente.call_args.args[1].permisos == frozenset({"CREAR_CASOS"})
    escenario.trabajo.commit.assert_called_once()


def test_administrador_modifica_roles_y_permisos_del_docente(cliente, servicios, escenario, cabeceras):
    escenario.usuarios.asignar_autorizaciones.return_value = escenario.docente
    respuesta = cliente.put(BASE + "/docentes/docente-1/autorizaciones", json={"roles": ["DOCENTE"], "permisos": []}, headers=cabeceras(escenario.administrador))
    assert respuesta.status_code == 200
    escenario.usuarios.asignar_autorizaciones.assert_called_once()


def test_docente_no_administra_usuarios(cliente, servicios, escenario, cabeceras):
    respuesta = cliente.post(BASE + "/docentes", json={"correo": "nuevo@universidad.test"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 403
    escenario.usuarios.crear_docente.assert_not_called()


def test_no_devuelve_exito_si_falla_commit(aplicacion, servicios, escenario, cabeceras):
    escenario.trabajo.commit.side_effect = RuntimeError("detalle privado de persistencia")
    with TestClient(aplicacion, raise_server_exceptions=False) as cliente:
        respuesta = cliente.post(REPETICIONES, json={"id_sesion": "s1", "id_estudiante": "e1"}, headers=cabeceras(escenario.docente))
    assert respuesta.status_code == 500
    assert "privado" not in respuesta.text
