"""Autorización aislada: el ámbito académico se sustituye por un doble."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import ConsultaAmbitoAcademico
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import (
    AccesoDenegado, NoAutenticado, ReglaIdentidadInvalida,
)


@pytest.fixture
def contexto():
    return ContextoAcceso("docente-1", "docente@universidad.test", frozenset({Rol.DOCENTE}))


@pytest.fixture
def entorno():
    academia = Mock(spec=ConsultaAmbitoAcademico)
    fabrica = Mock(return_value=academia)
    return ServicioAutorizacion(fabrica), fabrica, academia


@pytest.mark.parametrize("recurso", ["sesion", "participacion"])
@pytest.mark.parametrize("respuesta", [False, None, 1, "true", [], object()])
def test_ambito_exige_true_literal(entorno, contexto, recurso, respuesta):
    servicio, fabrica, academia = entorno
    consulta = getattr(academia, f"puede_consultar_{recurso}")
    consulta.return_value = respuesta
    with pytest.raises(AccesoDenegado):
        getattr(servicio, f"exigir_{recurso}")(contexto, "recurso-1")
    fabrica.assert_called_once_with()
    consulta.assert_called_once_with("docente-1", "recurso-1")


@pytest.mark.parametrize("recurso", ["sesion", "participacion"])
def test_ambito_autorizado_consulta_actor_y_recurso_exactos(entorno, contexto, recurso):
    servicio, _, academia = entorno
    consulta = getattr(academia, f"puede_consultar_{recurso}")
    consulta.return_value = True
    getattr(servicio, f"exigir_{recurso}")(contexto, "recurso-1")
    consulta.assert_called_once_with("docente-1", "recurso-1")


@pytest.mark.parametrize("recurso", ["sesion", "participacion"])
@pytest.mark.parametrize("id_recurso", ["", "con espacio", "x\n", "x" * 201])
def test_id_invalido_no_consulta_academia(entorno, contexto, recurso, id_recurso):
    servicio, fabrica, _ = entorno
    with pytest.raises(ReglaIdentidadInvalida):
        getattr(servicio, f"exigir_{recurso}")(contexto, id_recurso)
    fabrica.assert_not_called()


@pytest.mark.parametrize("recurso", ["sesion", "participacion"])
@pytest.mark.parametrize("activo,roles,error", [
    (False, frozenset({Rol.DOCENTE}), NoAutenticado),
    (True, frozenset({Rol.ESTUDIANTE}), AccesoDenegado),
    (True, frozenset({Rol.ADMINISTRADOR}), AccesoDenegado),
])
def test_actor_no_habilitado_no_consulta_academia(entorno, contexto, recurso, activo, roles, error):
    servicio, fabrica, _ = entorno
    with pytest.raises(error):
        getattr(servicio, f"exigir_{recurso}")(replace(contexto, activo=activo, roles=roles), "recurso-1")
    fabrica.assert_not_called()


def test_fallo_academico_se_propaga_sin_conceder_acceso(entorno, contexto):
    servicio, _, academia = entorno
    academia.puede_consultar_sesion.side_effect = RuntimeError("fuente no disponible")
    with pytest.raises(RuntimeError, match="fuente no disponible"):
        servicio.exigir_sesion(contexto, "sesion-1")
