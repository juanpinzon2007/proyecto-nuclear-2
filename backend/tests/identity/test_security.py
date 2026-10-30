from datetime import UTC, datetime

import jwt
import pytest

from app.modules.identity.domain.errors import NoAutenticado
from app.modules.identity.infrastructure.security import TokensJWT


CLAVE = "clave-de-pruebas-aisladas-" * 3


def claims_validos():
    ahora = int(datetime.now(UTC).timestamp())
    return {"sub": "estudiante-1", "iss": "sps-test", "aud": "sps-test-client",
            "iat": ahora, "nbf": ahora, "exp": ahora + 300, "jti": "prueba-1", "token_type": "access"}


def test_emite_y_verifica_identidad_y_convocatoria(tokens):
    token = tokens.emitir("estudiante-1", "convocatoria-1")
    identidad = tokens.verificar(token)
    assert identidad.id_usuario == "estudiante-1"
    assert identidad.id_convocatoria == "convocatoria-1"
    payload = jwt.decode(token, CLAVE, algorithms=["HS256"], audience="sps-test-client", issuer="sps-test")
    assert "roles" not in payload and "permisos" not in payload and "correo" not in payload
    assert "codigo_convocatoria" not in payload
    assert payload["exp"] - payload["iat"] == 900
    assert tokens.emitir("estudiante-1") != tokens.emitir("estudiante-1")


@pytest.mark.parametrize("campo", ["sub", "iss", "aud", "exp", "iat", "nbf", "jti", "token_type"])
def test_rechaza_claims_obligatorios_ausentes(tokens, campo):
    claims = claims_validos()
    del claims[campo]
    with pytest.raises(NoAutenticado):
        tokens.verificar(jwt.encode(claims, CLAVE, algorithm="HS256"))


@pytest.mark.parametrize("cambios", [
    {"iss": "sps-test-falso"}, {"aud": "otro-cliente"}, {"aud": ["sps-test-client"]},
    {"token_type": "refresh"}, {"sub": ""}, {"sub": 123}, {"jti": ""},
    {"convocatoria_id": None}, {"convocatoria_id": ""}, {"exp": 1},
    {"iat": 9999999999, "nbf": 9999999999, "exp": 10000000000},
    {"iat": True}, {"exp": "9999999999"}, {"exp": 9999999999},
])
def test_rechaza_claims_invalidos(tokens, cambios):
    claims = claims_validos() | cambios
    with pytest.raises(NoAutenticado):
        tokens.verificar(jwt.encode(claims, CLAVE, algorithm="HS256"))


@pytest.mark.parametrize("algoritmo,clave", [("none", ""), ("HS384", CLAVE), ("HS256", "otra-clave-de-pruebas-" * 3)])
def test_rechaza_algoritmo_o_firma_alterados(tokens, algoritmo, clave):
    with pytest.raises(NoAutenticado):
        tokens.verificar(jwt.encode(claims_validos(), clave, algorithm=algoritmo))


@pytest.mark.parametrize("token", ["", "no-es-un-jwt", "e30.e30.firma"])
def test_rechaza_token_malformado(tokens, token):
    with pytest.raises(NoAutenticado):
        tokens.verificar(token)


@pytest.mark.parametrize("clave,minutos", [("", 15), ("corta", 15), (CLAVE, 0), (CLAVE, 61), (CLAVE, True)])
def test_rechaza_configuracion_insegura(clave, minutos):
    with pytest.raises(ValueError):
        TokensJWT(clave, "sps", "cliente", minutos)
