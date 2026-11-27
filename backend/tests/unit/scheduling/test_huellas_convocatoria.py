import hashlib
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import SecretStr

from app.modules.scheduling.application import codigos_convocatoria as codigos


ESTUDIANTE = UUID(int=1)


@pytest.fixture(params=[True, False], ids=["con_clave", "sin_clave"])
def clave_configurada(request, monkeypatch):
    clave = SecretStr("clave-de-prueba") if request.param else None
    monkeypatch.setattr(codigos, "get_settings", lambda: SimpleNamespace(scheduling_mail_encryption_key=clave))
    return request.param


def test_codigo_actual_y_compatibilidad(clave_configurada):
    codigo = "012345"
    anterior = hashlib.sha256(codigo.encode()).hexdigest()
    assert codigos.coincide_codigo_convocatoria(codigo, anterior, ESTUDIANTE)
    if clave_configurada:
        actual = codigos.hash_codigo_numerico(codigo, ESTUDIANTE)
        assert actual.startswith("v2$")
        assert codigos.huellas_de_consulta(codigo, ESTUDIANTE) == (actual, anterior)
        assert codigos.coincide_codigo_convocatoria(codigo, actual, ESTUDIANTE)
        assert not codigos.coincide_codigo_convocatoria(codigo, actual, UUID(int=2))
        assert not codigos.coincide_codigo_convocatoria("012346", actual, ESTUDIANTE)
    else:
        with pytest.raises(codigos.CorreoConvocatoriaNoDisponible):
            codigos.hash_codigo_numerico(codigo, ESTUDIANTE)
        assert codigos.huellas_de_consulta(codigo, ESTUDIANTE) == (anterior,)


@pytest.mark.parametrize("codigo", ["12345", "1234567", "ABC123", "１２３４５６"])
def test_codigo_anterior_solo_consulta_sha256(codigo, clave_configurada):
    esperado = hashlib.sha256(codigo.encode()).hexdigest()
    assert codigos.huellas_de_consulta(codigo, ESTUDIANTE) == (esperado,)
