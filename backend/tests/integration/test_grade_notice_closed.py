"""RF-27: no anunciar calificaciones sin resultado oficial y ámbito verificables.

app.main, PostgreSQL17 desechable, JWT/roles/resolver reales. El token docente se
emite explícitamente en la fixture, sin afirmar un login de personal productivo.
"""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event

from app.main import app
from tests.integration.test_session_programming_http import programacion
from tests.integration.test_cases_graph_authoring import autor, pg_autoria, payload_valido  # noqa: F401


@pytest.fixture
def principal(programacion):
    h = programacion
    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides.update(h.client.app.dependency_overrides)
    motor = h.sesiones.kw['bind']
    escrituras = []
    commits = []

    def sql(_, __, statement, ___, ____, _____):
        if statement.lstrip().split(None, 1)[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'MERGE'}:
            escrituras.append(statement.split(None, 1)[0])

    def commit(_):
        commits.append(True)

    event.listen(motor, 'before_cursor_execute', sql)
    event.listen(motor, 'commit', commit)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield h, client, escrituras, commits
    finally:
        event.remove(motor, 'before_cursor_execute', sql)
        event.remove(motor, 'commit', commit)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


@pytest.mark.parametrize('actor,estado', [
    ('docente', 503), ('docente_ajeno', 503), ('estudiante', 403),
    ('anonimo', 401), ('token_invalido', 401),
])
def test_principal_no_anuncia_resultado_inexistente_ni_escribe(principal, actor, estado):
    h, client, escrituras, commits = principal
    headers = {'docente': h.a.headers, 'docente_ajeno': h.a.ajeno,
        'estudiante': h.a.estudiante, 'anonimo': {},
        'token_invalido': {'Authorization': 'Bearer invalido'}}[actor]
    r = client.post('/scheduling/calificaciones/notificar', headers=headers,
        json={'estudiante_id': str(uuid4()), 'participacion_id': str(uuid4())})
    assert r.status_code == estado, r.text
    assert r.headers.get('Cache-Control') == 'no-store'
    assert not escrituras and not commits
    assert 'ya está disponible' not in r.text
    if actor == 'docente':
        contrato = client.get('/openapi.json').json()['paths']['/scheduling/calificaciones/notificar']['post']
        assert '503' in contrato['responses'] and '201' not in contrato['responses']


def test_reintentos_y_solicitudes_concurrentes_no_generan_avisos(principal):
    h, client, escrituras, commits = principal
    body = {'estudiante_id': str(uuid4()), 'participacion_id': str(uuid4())}

    def solicitar(_):
        return client.post('/scheduling/calificaciones/notificar', headers=h.a.headers, json=body).status_code

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        assert list(ejecutor.map(solicitar, range(2))) == [503, 503]
    assert solicitar(None) == 503
    assert not escrituras and not commits
