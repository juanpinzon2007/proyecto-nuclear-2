from sqlalchemy.exc import SQLAlchemyError
from app.modules.identity.api.academic_dependencies import obtener_fabrica_sesiones_academicas
"""HTTP ASGI con JWT real; repositorios/configuración sustituidos solo en pruebas.

No verifica PostgreSQL ni una resolución INTEGER/UUID. Las rutas de sonda son
exclusivas de esta suite; no se añaden endpoints a la aplicación principal.
"""

from dataclasses import replace
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import jwt
import pytest

from app.modules.identity.api.dependencies import (
    obtener_docente_actual, obtener_fabrica_tokens, obtener_fabrica_usuarios,
)
from app.modules.identity.application.ports import RepositorioUsuarios
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.security import TokensJWT


SECRETO = "clave-exclusiva-integracion-docente-" * 2
UUID_AJENO = "d988b0f5-a0d1-4b4d-b909-9c8be80397ca"


@pytest.fixture
def entorno():
    usuario = ContextoAcceso("7", "docente@universidad.test", frozenset({Rol.DOCENTE}))
    repo = Mock(spec=RepositorioUsuarios)
    repo.obtener.return_value = usuario
    tokens = TokensJWT(SECRETO, "sps-prueba", "sps-cliente")
    fabrica_tokens = Mock(return_value=tokens)
    fabrica_usuarios = Mock(return_value=repo)
    ejecutado = Mock()
    app = FastAPI(debug=False)

    @app.get("/sonda-docente")
    def sonda(docente: Annotated[ContextoAcceso, Depends(obtener_docente_actual)]):
        ejecutado(docente)
        return {"id_usuario": docente.id_usuario}

    app.dependency_overrides[obtener_fabrica_tokens] = lambda: fabrica_tokens
    app.dependency_overrides[obtener_fabrica_usuarios] = lambda: fabrica_usuarios
    with TestClient(app) as cliente:
        yield SimpleNamespace(app=app, cliente=cliente, usuario=usuario, repo=repo,
                              tokens=tokens, fabrica_tokens=fabrica_tokens,
                              fabrica_usuarios=fabrica_usuarios, ejecutado=ejecutado)
    app.dependency_overrides.clear()


def headers(entorno, *, convocatoria=None):
    return {"Authorization": "Bearer " + entorno.tokens.emitir("7", convocatoria)}


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer invalido", "Bearer"])
def test_credenciales_ausentes_o_invalidas(entorno, authorization):
    respuesta = entorno.cliente.get("/sonda-docente", headers={} if authorization is None else {"Authorization": authorization})
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert respuesta.headers["cache-control"] == "no-store"
    entorno.fabrica_usuarios.assert_not_called()
    entorno.ejecutado.assert_not_called()


@pytest.mark.parametrize("alteracion", ["vencido", "firma", "roles_cliente"])
def test_claims_no_conceden_acceso(entorno, alteracion):
    claims = jwt.decode(entorno.tokens.emitir("7"), options={"verify_signature": False})
    secreto = SECRETO
    if alteracion == "vencido":
        claims.update(iat=1000, nbf=1000, exp=1060)
    elif alteracion == "firma":
        secreto = "otra-clave-exclusiva-de-prueba-" * 2
    else:
        claims["roles"] = ["DOCENTE"]
        entorno.repo.obtener.return_value = replace(entorno.usuario, roles=frozenset())
    token = jwt.encode(claims, secreto, algorithm="HS256")
    respuesta = entorno.cliente.get("/sonda-docente", headers={"Authorization": "Bearer " + token})
    assert respuesta.status_code == (403 if alteracion == "roles_cliente" else 401)
    entorno.ejecutado.assert_not_called()


@pytest.mark.parametrize("estado", ["inexistente", "inactivo", "otro_usuario"])
def test_identidad_vigente_obligatoria(entorno, estado):
    entorno.repo.obtener.return_value = {
        "inexistente": None,
        "inactivo": replace(entorno.usuario, activo=False),
        "otro_usuario": replace(entorno.usuario, id_usuario="8"),
    }[estado]
    assert entorno.cliente.get("/sonda-docente", headers=headers(entorno)).status_code == 401
    entorno.ejecutado.assert_not_called()


@pytest.mark.parametrize("rol", [Rol.ESTUDIANTE, Rol.ADMINISTRADOR])
def test_otro_rol_no_equivale_a_docente(entorno, rol):
    entorno.repo.obtener.return_value = replace(entorno.usuario, roles=frozenset({rol}))
    respuesta = entorno.cliente.get("/sonda-docente", headers=headers(entorno, convocatoria="conv-prueba"))
    assert respuesta.status_code == 403
    entorno.ejecutado.assert_not_called()


def test_docente_autorizado_conserva_id_identity_sin_convertir(entorno):
    respuesta = entorno.cliente.get("/sonda-docente", headers=headers(entorno))
    assert respuesta.status_code == 200 and respuesta.json() == {"id_usuario": "7"}
    entorno.repo.obtener.assert_called_once_with("7")
    entorno.ejecutado.assert_called_once_with(entorno.usuario)
    assert not isinstance(entorno.ejecutado.call_args.args[0].id_usuario, UUID)


@pytest.mark.parametrize("con_token", [False, True])
def test_x_docente_id_no_autentica_ni_suplanta(entorno, con_token):
    cabeceras = headers(entorno) if con_token else {}
    cabeceras.update({"X-Docente-Id": UUID_AJENO, "X-Role": "DOCENTE"})
    respuesta = entorno.cliente.get("/sonda-docente?id_usuario=999", headers=cabeceras)
    assert respuesta.status_code == (200 if con_token else 401)
    if con_token:
        assert respuesta.json() == {"id_usuario": "7"}
    else:
        entorno.ejecutado.assert_not_called()


def test_rol_revocado_se_consulta_de_nuevo_por_solicitud(entorno):
    cabeceras = headers(entorno)
    assert entorno.cliente.get("/sonda-docente", headers=cabeceras).status_code == 200
    entorno.repo.obtener.return_value = replace(entorno.usuario, roles=frozenset())
    assert entorno.cliente.get("/sonda-docente", headers=cabeceras).status_code == 403
    assert entorno.repo.obtener.call_count == 2
    assert entorno.ejecutado.call_count == 1


@pytest.mark.parametrize("dependencia", ["tokens", "usuarios", "consulta"])
def test_dependencia_no_disponible_cierra_acceso(entorno, dependencia):
    objetivo = {"tokens": entorno.fabrica_tokens, "usuarios": entorno.fabrica_usuarios,
                "consulta": entorno.repo.obtener}[dependencia]
    objetivo.side_effect = IntegracionPendiente("detalle privado")
    respuesta = entorno.cliente.get("/sonda-docente", headers=headers(entorno))
    assert respuesta.status_code == 503
    assert "privado" not in respuesta.text
    entorno.ejecutado.assert_not_called()


def test_fallo_inesperado_no_se_oculta_ni_abre_acceso(entorno):
    entorno.repo.obtener.side_effect = RuntimeError("detalle privado")
    with pytest.raises(RuntimeError, match="detalle privado"):
        entorno.cliente.get("/sonda-docente", headers=headers(entorno))
    with TestClient(entorno.app, raise_server_exceptions=False) as cliente:
        respuesta = cliente.get("/sonda-docente", headers=headers(entorno))
        assert respuesta.status_code == 500
        assert "privado" not in respuesta.text
    entorno.ejecutado.assert_not_called()


def test_sin_overrides_anonimo_rechazado_antes_de_configurar_bd(entorno):
    entorno.app.dependency_overrides.clear()
    assert entorno.cliente.get("/sonda-docente").status_code == 401


def test_cases_rechaza_cabecera_temporal_sin_token():
    from app.modules.cases.api.dependencies import get_caso_service
    from app.modules.cases.api.router import router

    app = FastAPI()
    servicio = Mock()
    servicio.listar.return_value = []
    app.include_router(router)
    app.dependency_overrides[get_caso_service] = lambda: servicio
    with TestClient(app) as cliente:
        assert cliente.get("/api/v1/cases").status_code == 401
        # Regresión de seguridad: la cabecera ya no autentica.
        assert cliente.get("/api/v1/cases", headers={"X-Docente-Id": UUID_AJENO}).status_code == 401
    servicio.listar.assert_not_called()


def test_scheduling_cierra_503_si_falla_persistencia_academica(entorno):
    from app.db.session import get_db
    from app.modules.scheduling.api.router import router

    entorno.app.include_router(router)
    entorno.app.dependency_overrides[obtener_fabrica_sesiones_academicas] = lambda: Mock(side_effect=SQLAlchemyError("sin laboratorio"))
    db = Mock()
    entorno.app.dependency_overrides[get_db] = lambda: db
    cabeceras = {**headers(entorno), "X-Docente-Id": UUID_AJENO}
    respuesta = entorno.cliente.post("/scheduling/espacios", json={"nombre": "Espacio prueba"}, headers=cabeceras)
    assert respuesta.status_code == 503
    db.add.assert_not_called()
    db.commit.assert_not_called()
