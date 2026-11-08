from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.modules.identity.api.dependencies import obtener_fabrica_tokens, obtener_fabrica_usuarios
from app.modules.identity.api.router import router
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import (
    ConsultaEscrituraAcademica, RepositorioAutorizaciones, RepositorioFeedback, RepositorioUsuarios,
)
from app.modules.identity.domain.entities import CondicionesRepeticion, ContextoAcceso, Rol
from app.modules.identity.infrastructure.security import TokensJWT


@pytest.fixture
def escenario():
    estudiante = ContextoAcceso("estudiante-1", "alumno@universidad.test", frozenset({Rol.ESTUDIANTE}))
    docente = ContextoAcceso("docente-1", "docente@universidad.test", frozenset({Rol.DOCENTE}))
    administrador = ContextoAcceso("admin-1", "admin@universidad.test", frozenset({Rol.ADMINISTRADOR}))
    identidades = {c.id_usuario: c for c in (estudiante, docente, administrador)}
    usuarios = Mock(spec=RepositorioUsuarios)
    usuarios.obtener.side_effect = identidades.get
    usuarios.permisos_existentes.return_value = True
    academia = Mock(spec=ConsultaEscrituraAcademica)
    academia.puede_consultar_participacion.return_value = True
    academia.puede_consultar_sesion.return_value = True
    academia.condiciones_repeticion.return_value = CondicionesRepeticion(True, True, False)
    trabajo = MagicMock()
    trabajo.__enter__.return_value = trabajo
    trabajo.__exit__.return_value = False
    trabajo.usuarios = usuarios
    trabajo.academia = academia
    trabajo.autorizaciones = Mock(spec=RepositorioAutorizaciones)
    trabajo.autorizaciones.guardar.return_value = None  # Contrato histórico void; sin Mock implícito como ID.
    trabajo.feedback = Mock(spec=RepositorioFeedback)
    return SimpleNamespace(
        estudiante=estudiante, docente=docente, administrador=administrador,
        identidades=identidades, usuarios=usuarios, academia=academia, trabajo=trabajo,
        autorizacion=ServicioAutorizacion(lambda: academia),
    )


@pytest.fixture
def tokens():
    # Clave exclusiva de pruebas; no configura ni se importa desde producción.
    return TokensJWT("clave-de-pruebas-aisladas-" * 3, "sps-test", "sps-test-client")


@pytest.fixture
def aplicacion(escenario, tokens):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[obtener_fabrica_tokens] = lambda: lambda: tokens
    app.dependency_overrides[obtener_fabrica_usuarios] = lambda: lambda: escenario.usuarios
    return app


@pytest.fixture
def cliente(aplicacion):
    with TestClient(aplicacion) as client:
        yield client


@pytest.fixture
def cabeceras(tokens):
    def construir(usuario):
        convocatoria = "convocatoria-1" if Rol.ESTUDIANTE in usuario.roles else None
        return {"Authorization": "Bearer " + tokens.emitir(usuario.id_usuario, convocatoria)}
    return construir
