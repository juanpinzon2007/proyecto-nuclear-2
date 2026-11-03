from sqlalchemy.exc import SQLAlchemyError
from app.modules.identity.api.academic_dependencies import obtener_fabrica_sesiones_academicas
"""JWT y resolución reales; consulta de vínculos/servicio Cases/Session con mocks.

HTTP ASGI, sin migraciones ni PostgreSQL. Los vínculos solo existen en fixtures.
"""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest

from tests.integration.test_docente_identity import entorno, headers, UUID_AJENO  # noqa: F401
from app.db.session import get_db
from app.modules.cases.api.dependencies import get_caso_service
from app.modules.cases.api.router import router as cases_router
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.identity.api.academic_dependencies import obtener_fabrica_resolver_academico
from app.modules.identity.application.academic_identity import (
    ConsultaVinculosAcademicos, ResolverIdentidadAcademica, SistemaAcademico, VinculoAcademico,
)
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import IntegracionPendiente


PROPIO = UUID("a199b9f7-051e-40df-b1f8-9a7fb321bac2")
AJENO = UUID(UUID_AJENO)


@pytest.fixture
def integrado(entorno):
    entorno.app.include_router(cases_router)
    entorno.app.include_router(scheduling_router)
    servicio = Mock()
    servicio.listar.return_value = []
    db = Mock()
    entorno.app.dependency_overrides[get_caso_service] = lambda: servicio
    entorno.app.dependency_overrides[get_db] = lambda: db
    consulta = Mock(spec=ConsultaVinculosAcademicos)
    consulta.obtener.side_effect = lambda *, id_usuario, sistema: (VinculoAcademico(id_usuario, sistema, PROPIO),)
    resolver = ResolverIdentidadAcademica(consulta)
    entorno.app.dependency_overrides[obtener_fabrica_resolver_academico] = lambda: lambda: resolver
    return SimpleNamespace(**vars(entorno), servicio=servicio, db=db, consulta=consulta)


@pytest.mark.parametrize("metodo,ruta", [
    ("GET", "/api/v1/cases"), ("POST", "/api/v1/cases"),
    ("GET", f"/api/v1/cases/{AJENO}"), ("PUT", f"/api/v1/cases/{AJENO}"),
    ("POST", f"/api/v1/cases/{AJENO}/publish"), ("POST", f"/api/v1/cases/{AJENO}/archive"),
    ("POST", "/scheduling/espacios"), ("POST", "/scheduling/sesiones"),
    ("GET", "/scheduling/espacios"), ("GET", "/scheduling/sesiones"),
    ("GET", f"/scheduling/sesiones/{AJENO}"),
    ("POST", f"/scheduling/sesiones/{AJENO}/estado"),
    ("POST", f"/scheduling/sesiones/{AJENO}/convocatorias"),
    ("GET", f"/scheduling/sesiones/{AJENO}/convocatorias"),
    ("POST", "/scheduling/calificaciones/notificar"),
])
def test_rutas_docentes_no_aceptan_solo_cabecera(integrado, metodo, ruta):
    respuesta = integrado.cliente.request(metodo, ruta, json={}, headers={"X-Docente-Id": UUID_AJENO})
    assert respuesta.status_code == 401
    integrado.consulta.obtener.assert_not_called()
    assert integrado.servicio.mock_calls == [] and integrado.db.mock_calls == []


@pytest.mark.parametrize("ruta", ["/api/v1/cases", f"/scheduling/sesiones/{AJENO}/convocatorias"])
@pytest.mark.parametrize("credencial", ["invalida", "estudiante", "docente_sin_persistencia"])
def test_identidad_y_resolucion_obligatorias(integrado, ruta, credencial):
    cabeceras = headers(integrado, convocatoria="conv-prueba")
    if credencial == "invalida":
        cabeceras["Authorization"] = "Bearer invalido"
    elif credencial == "estudiante":
        integrado.repo.obtener.return_value = ContextoAcceso("7", "alumno@universidad.test", frozenset({Rol.ESTUDIANTE}))
    else:
        del integrado.app.dependency_overrides[obtener_fabrica_resolver_academico]
        integrado.app.dependency_overrides[obtener_fabrica_sesiones_academicas] = lambda: Mock(side_effect=SQLAlchemyError("sin laboratorio"))
    respuesta = integrado.cliente.get(ruta, headers=cabeceras)
    assert respuesta.status_code == {"invalida": 401, "estudiante": 403, "docente_sin_persistencia": 503}[credencial]
    assert integrado.servicio.mock_calls == [] and integrado.db.mock_calls == []


@pytest.mark.parametrize("sistema,ruta", [
    (SistemaAcademico.CASES, "/api/v1/cases"),
    (SistemaAcademico.SCHEDULING, f"/scheduling/sesiones/{AJENO}/convocatorias"),
])
@pytest.mark.parametrize("problema", ["ausente", "duplicado", "usuario_ajeno", "otro_sistema", "uuid_invalido", "nulo", "caida"])
def test_asociaciones_no_verificadas_cierran_acceso(integrado, sistema, ruta, problema):
    correcto = VinculoAcademico("7", sistema, PROPIO)
    valores = {
        "ausente": (), "duplicado": (correcto, correcto),
        "usuario_ajeno": (VinculoAcademico("8", sistema, PROPIO),),
        "otro_sistema": (VinculoAcademico("7", SistemaAcademico.SCHEDULING if sistema == SistemaAcademico.CASES else SistemaAcademico.CASES, PROPIO),),
        "uuid_invalido": (VinculoAcademico("7", sistema, "7"),),
        "nulo": (VinculoAcademico("7", sistema, UUID(int=0)),),
    }
    integrado.consulta.obtener.side_effect = None
    if problema == "caida":
        integrado.consulta.obtener.side_effect = IntegracionPendiente("detalle privado")
    else:
        integrado.consulta.obtener.return_value = valores[problema]
    respuesta = integrado.cliente.get(ruta, headers={**headers(integrado), "X-Docente-Id": UUID_AJENO})
    assert respuesta.status_code == (403 if problema == "ausente" else 503)
    assert "privado" not in respuesta.text
    assert integrado.servicio.mock_calls == [] and integrado.db.mock_calls == []


def test_cases_ignora_cabecera_ajena_con_vinculo_verificado(integrado):
    respuesta = integrado.cliente.get("/api/v1/cases", headers={**headers(integrado), "X-Docente-Id": UUID_AJENO})
    assert respuesta.status_code == 200
    integrado.servicio.listar.assert_called_once_with(PROPIO)
    integrado.consulta.obtener.assert_called_once_with(id_usuario="7", sistema=SistemaAcademico.CASES)


@pytest.mark.parametrize("propia", [False, True])
def test_scheduling_comprueba_propiedad_despues_de_resolver(integrado, propia):
    integrado.db.get.return_value = SimpleNamespace(docente_id=PROPIO if propia else AJENO)
    integrado.db.scalars.return_value.all.return_value = []
    respuesta = integrado.cliente.get(f"/scheduling/sesiones/{AJENO}/convocatorias",
                                      headers={**headers(integrado), "X-Docente-Id": UUID_AJENO})
    assert respuesta.status_code == (200 if propia else 403)
    integrado.consulta.obtener.assert_called_once_with(id_usuario="7", sistema=SistemaAcademico.SCHEDULING)
    if not propia:
        integrado.db.scalars.assert_not_called()


def test_no_se_deduce_mismo_uuid_entre_sistemas(integrado):
    integrado.consulta.obtener.side_effect = lambda *, id_usuario, sistema: (
        VinculoAcademico(id_usuario, sistema, PROPIO if sistema == SistemaAcademico.CASES else AJENO),
    )
    integrado.db.get.return_value = SimpleNamespace(docente_id=AJENO)
    integrado.db.scalars.return_value.all.return_value = []
    assert integrado.cliente.get("/api/v1/cases", headers=headers(integrado)).status_code == 200
    assert integrado.cliente.get(f"/scheduling/sesiones/{AJENO}/convocatorias", headers=headers(integrado)).status_code == 200
    integrado.servicio.listar.assert_called_once_with(PROPIO)


def test_detalle_sesion_ajena_no_se_expone(integrado):
    integrado.db.get.return_value = SimpleNamespace(docente_id=AJENO)
    respuesta = integrado.cliente.get(f"/scheduling/sesiones/{AJENO}", headers=headers(integrado))
    assert respuesta.status_code == 403


def test_filtro_de_docente_no_suplanta(integrado):
    respuesta = integrado.cliente.get(f"/scheduling/sesiones?docente_id={AJENO}", headers=headers(integrado))
    assert respuesta.status_code == 403
    integrado.db.scalars.assert_not_called()


def test_listado_sesiones_siempre_filtra_docente_resuelto(integrado):
    integrado.db.scalars.return_value.all.return_value = []
    respuesta = integrado.cliente.get("/scheduling/sesiones", headers=headers(integrado))
    assert respuesta.status_code == 200
    consulta = integrado.db.scalars.call_args.args[0]
    assert PROPIO in consulta.compile().params.values()


def test_error_inesperado_resolver_no_se_oculta(integrado):
    integrado.consulta.obtener.side_effect = RuntimeError("fallo inesperado")
    with pytest.raises(RuntimeError, match="fallo inesperado"):
        integrado.cliente.get("/api/v1/cases", headers=headers(integrado))
    integrado.servicio.listar.assert_not_called()


def test_openapi_no_solicita_x_docente_id(integrado):
    schema = integrado.app.openapi()
    operacion = schema["paths"]["/api/v1/cases"]["get"]
    assert not any(p["name"] == "X-Docente-Id" for p in operacion.get("parameters", []))
    assert operacion["security"] == [{"HTTPBearer": []}]
