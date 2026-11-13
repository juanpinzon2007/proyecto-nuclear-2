"""Puertos productivos obligatorios: jamás fallback de LAB ni UTC implícito."""
from datetime import datetime,timedelta
from types import SimpleNamespace
from fastapi import HTTPException
import pytest
from app.modules.identity.api import consent_dependencies as c
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.participation.api import start_dependencies as s
from app.modules.participation.application.errors import ReglaPendiente

def test_puertos_no_tienen_politica_productiva_implicita():
    for proveedor in (s.obtener_politica_inicio,s.obtener_politica_vinculacion):
        with pytest.raises(ReglaPendiente):proveedor()
    with pytest.raises(HTTPException) as e:c.obtener_aprobacion_consentimiento()
    assert e.value.status_code==503

@pytest.mark.parametrize('zona',[None,'','No-es-una-zona'])
def test_zona_obligatoria_sin_inferir_utc(monkeypatch,zona):
    monkeypatch.setattr(c,'get_settings',lambda:SimpleNamespace(participation_timestamp_zone=zona))
    with pytest.raises(IntegracionPendiente):c.obtener_fechas_consentimiento()

def test_zona_explicita_valida(monkeypatch):
    monkeypatch.setattr(c,'get_settings',lambda:SimpleNamespace(participation_timestamp_zone='UTC'))
    assert c.obtener_fechas_consentimiento().desde_db(datetime(2026,11,9)).utcoffset()==timedelta(0)

@pytest.mark.parametrize('invalido',[None,True])
def test_configuracion_no_puede_omitir_aprobacion(invalido):
    def no_abrir():pytest.fail('No abrir una Session por configuración inválida')
    with pytest.raises(IntegracionPendiente):
        c.obtener_servicio_consentimiento(usuario=None,aprobacion=invalido,fechas=None,reloj=None,sesiones=no_abrir)
    ok=SimpleNamespace(autorizar=lambda *a,**k:None)
    for puerto in ('inicio','vinculacion','aprobacion'):
        args=dict(usuario=None,inicio=ok,vinculacion=ok,aprobacion=ok,fechas=None,reloj=None,sesiones=no_abrir)
        args[puerto]=invalido
        with pytest.raises(ReglaPendiente):s.obtener_servicio_inicio(**args)
