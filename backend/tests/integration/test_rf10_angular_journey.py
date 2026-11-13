"""HTTP main real, JWT/PG17. Solo preparación del intento y reloj son LAB.

Se reutilizan fixtures y servicios. No acredita inicio productivo ni aprobación
integral de RF-10; múltiples preguntas/ciclos/revisitas siguen cerrados.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.integration.test_main_current_scenario import (
    principal, integracion, autor, pg_autoria, payload_valido,  # noqa: F401
)
from tests.integration.test_current_scenario_http import snapshot


@pytest.mark.parametrize('rama', [0, 1])
def test_recarga_y_ramas_main_hasta_fin_y_cierre_sin_notas(principal, rama):
    h = principal
    progress = f'/api/v1/attempts/{h.ik}/progress'
    before = snapshot(h, h.ik)
    current = h.principal.get(h.path, headers=h.main_headers)
    assert current.status_code == 200
    # Otro cliente HTTP, sin estado local compartido: recuperación tras recarga.
    with TestClient(app, raise_server_exceptions=False) as reload:
        assert reload.get(h.path, headers=h.main_headers).json() == current.json()
        assert reload.get(progress, headers=h.main_headers).json()['respondidas'] == 0
    assert snapshot(h, h.ik) == before
    q = current.json()['pregunta']; option = q['opciones'][rama]['id']
    path = f'/api/v1/attempts/{h.ik}/decisions/{q["id"]}'
    assert h.principal.post(path, headers=h.main_headers, json={'id_opcion': option}).status_code == 201
    replay = h.principal.post(path, headers=h.main_headers, json={'id_opcion': option})
    assert replay.status_code == 409 and replay.json()['detail']['codigo'] == 'RESPUESTA_INMUTABLE'
    p = h.principal.get(progress, headers=h.main_headers).json()
    assert p['selecciones'] == [{'id_decision': q['id'], 'id_opcion': option}]
    assert p['respondidas'] == 1
    next_scene = h.principal.get(h.path, headers=h.main_headers).json()
    assert next_scene['id_escenario'] == h.escenas[rama + 1]['id']
    nq = next_scene['pregunta']
    assert h.principal.post(f'/api/v1/attempts/{h.ik}/decisions/{nq["id"]}',
        headers=h.main_headers, json={'id_opcion': nq['opciones'][0]['id']}).status_code == 201
    terminal = h.principal.get(h.path, headers=h.main_headers)
    assert terminal.status_code == 200 and terminal.json() == dict(
        id_escenario=None, contexto=None, pregunta=None, recorrido_finalizado=True, respondidas=2)
    assert h.principal.get(progress, headers=h.main_headers).json()['intento']['estado'] == 'EN_CURSO'
    finish = f'/api/v1/attempts/{h.ik}/finish'
    closed = h.principal.post(finish, headers=h.main_headers)
    assert closed.status_code == 200 and closed.json()['estado'] == 'FINALIZADO'
    assert h.principal.post(finish, headers=h.main_headers).json() == closed.json()
    assert h.principal.get(h.path, headers=h.main_headers).status_code == 409
    final = h.principal.get(progress, headers=h.main_headers).json()
    assert final['respondidas'] == 2 and final['intento'] == closed.json()
    assert not {'nota_final', 'criterios', 'rubrica', 'esCorrecta', 'justificacion'} & final.keys()
    assert len(snapshot(h, h.ik)[1]) == 2


def test_vencimiento_leido_y_confirmado_por_comando_sin_perder_seleccion(principal):
    h = principal; q = h.principal.get(h.path, headers=h.main_headers).json()['pregunta']
    assert h.principal.post(f'/api/v1/attempts/{h.ik}/decisions/{q["id"]}',
        headers=h.main_headers, json={'id_opcion': q['opciones'][0]['id']}).status_code == 201
    nq = h.principal.get(h.path, headers=h.main_headers).json()['pregunta']
    before = snapshot(h, h.ik); now = h.reloj.ahora(); h.reloj.ahora = lambda: now + timedelta(minutes=30)
    p = h.principal.get(f'/api/v1/attempts/{h.ik}/progress', headers=h.main_headers)
    assert p.status_code == 200 and p.json()['intento']['estado'] == 'VENCIDO'
    assert snapshot(h, h.ik) == before  # GET solo proyecta el estado efectivo.
    denied = h.principal.post(f'/api/v1/attempts/{h.ik}/decisions/{nq["id"]}',
        headers=h.main_headers, json={'id_opcion': nq['opciones'][0]['id']})
    assert denied.status_code == 409 and denied.json()['detail']['codigo'] == 'INTENTO_NO_EDITABLE'
    after = snapshot(h, h.ik)
    assert after[0][0].estado == 'VENCIDO' and after[1] == before[1]
