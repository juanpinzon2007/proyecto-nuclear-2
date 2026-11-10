"""app.main.app real, configuración PostgreSQL/JWT real; solo reloj de laboratorio."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.modules.identity.api import dependencies as identity
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.participation.api.dependencies import obtener_reloj_escenario
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.integration.test_participation_http_composition import (
    integracion, autor, pg_autoria, payload_valido, iniciar,  # noqa: F401
)
from tests.integration.test_current_scenario_http import snapshot


@pytest.fixture
def principal(integracion, monkeypatch):
    from app.main import app
    h = integracion
    r = iniciar(h)  # Preparación: inicio con políticas explícitas SOLO del laboratorio.
    assert r.status_code == 201
    h.ik = r.json()['id_intento']; h.path = f'/api/v1/attempts/{h.ik}/current-scenario'
    url = h.sesiones.kw['bind'].url
    tokens = h.client.app.dependency_overrides[identity.obtener_fabrica_tokens]()()
    # Configurar las fábricas REALES, sin sustituir autorización ni servicios.
    for k, v in dict(POSTGRES_HOST=url.host, POSTGRES_PORT=str(url.port),
        POSTGRES_DB=url.database, POSTGRES_USER=url.username, POSTGRES_PASSWORD=url.password,
        IDENTITY_JWT_SECRET=tokens._secreto, IDENTITY_JWT_ISSUER=tokens._emisor,
        IDENTITY_JWT_AUDIENCE=tokens._audiencia, IDENTITY_INSTITUTIONAL_DOMAINS='["universidad.test"]',
        PARTICIPATION_TIMESTAMP_ZONE='UTC').items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear(); get_session_factory.cache_clear(); get_engine.cache_clear()
    anteriores = dict(app.dependency_overrides); app.dependency_overrides.clear()
    app.dependency_overrides[obtener_reloj_escenario] = lambda: h.reloj
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            h.principal = client
            login = client.post('/api/v1/identity/auth/estudiantes', json={
                'correo': f'autor{h.estudiante}@universidad.test', 'codigo_convocatoria': h.codigo})
            assert login.status_code == 200
            h.main_headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
            assert set(app.dependency_overrides) == {obtener_reloj_escenario}
            yield h
    finally:
        # Únicamente el engine configurado contra este laboratorio propio.
        if get_engine.cache_info().currsize:
            engine = get_engine()
            assert engine.url == url
            engine.dispose()
        get_session_factory.cache_clear(); get_engine.cache_clear(); get_settings.cache_clear()
        app.dependency_overrides.clear(); app.dependency_overrides.update(anteriores)


def test_principal_login_consulta_privada_repetida_sin_dml_commit_y_avance(principal, record_property):
    h = principal; antes = snapshot(h, h.ik); operaciones = []
    engine = get_engine()
    def sql(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'MERGE')):
            operaciones.append('DML')
    def commit(conn): operaciones.append('COMMIT')
    event.listen(engine, 'before_cursor_execute', sql); event.listen(engine, 'commit', commit)
    try:
        a = h.principal.get(h.path, headers=h.main_headers)
        b = h.principal.get(h.path, headers=h.main_headers)
    finally:
        event.remove(engine, 'before_cursor_execute', sql); event.remove(engine, 'commit', commit)
    assert a.status_code == b.status_code == 200 and a.json() == b.json()
    assert snapshot(h, h.ik) == antes and operaciones == []
    body = a.json(); q = body['pregunta']
    assert body['id_escenario'] == h.escenas[0]['id']
    assert body['contexto'] == h.escenas[0]['contexto_situacional']
    assert set(body) == {'id_escenario', 'contexto', 'pregunta', 'recorrido_finalizado', 'respondidas'}
    assert set(q) == {'id', 'enunciado', 'opciones'}
    assert all(set(o) == {'id', 'texto'} for o in q['opciones'])
    assert a.headers['cache-control'] == 'no-store'
    assert all(h.escenas[n]['preguntas'][0]['id'] not in a.text for n in (1, 2))
    assert h.codigo not in a.text
    assert h.principal.get(h.path, headers=h.main_headers, params={'version_id': str(h.version)}).status_code == 422
    record_property('respuesta_principal', a.text)
    # El escritor sigue SOLO en la app aislada de preparación, nunca en main.
    assert h.client.post(f"/api/v1/attempts/{h.ik}/decisions/{q['id']}", headers=h.headers,
        json={'id_opcion': q['opciones'][0]['id']}).status_code == 201
    siguiente = h.principal.get(h.path, headers=h.main_headers)
    assert siguiente.status_code == 200 and siguiente.json()['respondidas'] == 1
    assert siguiente.json()['id_escenario'] == h.escenas[1]['id']


@pytest.mark.parametrize('problema,esperado', [('anonimo',401),('ajeno',403),('convocatoria',403),
    ('matricula',403),('horario',403),('vencido',409),('cerrado',409),('sin_zona',503),('zona_invalida',503)])
def test_principal_rechaza_sin_divulgar_y_sin_escribir(principal, monkeypatch, problema, esperado):
    h = principal; headers = h.main_headers
    if problema == 'anonimo': headers = {}
    elif problema == 'ajeno': headers = h.headers_ajeno
    elif problema in ('sin_zona','zona_invalida'):
        if problema == 'sin_zona': monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE')
        else: monkeypatch.setenv('PARTICIPATION_TIMESTAMP_ZONE', 'Zona/NoExiste')
        get_settings.cache_clear()
    elif problema == 'vencido':
        ahora = h.reloj.ahora(); h.reloj.ahora = lambda: ahora + timedelta(minutes=30)
    elif problema == 'cerrado':
        assert h.client.post(f'/api/v1/attempts/{h.ik}/finish', headers=h.headers).status_code == 200
    else:
        with h.sesiones.begin() as s:
            if problema == 'convocatoria': s.get(ConvocatoriaModel,h.convocatoria).estado = 'RETIRADA'
            elif problema == 'matricula': s.get(GrupoEstudianteORM,h.matricula).activo = False
            else: s.get(SesionProgramadaModel,h.sesion).fecha_inicio += timedelta(minutes=2)
    antes = snapshot(h,h.ik)
    r = h.principal.get(h.path,headers=headers)
    assert r.status_code == esperado
    assert snapshot(h,h.ik) == antes
    assert h.escenas[0]['preguntas'][0]['enunciado'] not in r.text
    assert r.headers['cache-control'] == 'no-store'


def test_principal_conserva_version_archivada_y_bloquea_inicio_sin_politicas(principal):
    h = principal
    from app.main import app
    from tests.integration.test_current_scenario_http import publicar_segunda_edicion_y_archivar
    # La aceptación histórica existente prepara otra edición del mismo caso y
    # archiva la asignada. Después comprobamos también la lectura de main.
    antes = h.principal.get(h.path,headers=h.main_headers)
    publicar_segunda_edicion_y_archivar(h)
    actual = h.principal.get(h.path,headers=h.main_headers)
    assert actual.status_code == 200 and actual.json() == antes.json()
    paths=app.openapi()['paths']
    rutas=[p for p in paths if p.startswith(('/api/v1/attempts/', '/api/v1/participations/', '/api/v1/convocatorias/'))]
    assert set(rutas) == {'/api/v1/attempts/{attempt_id}/current-scenario','/api/v1/attempts/{attempt_id}/progress',
        '/api/v1/attempts/{attempt_id}/decisions/{decision_id}','/api/v1/attempts/{attempt_id}/finish',
        '/api/v1/convocatorias/{convocatoria_id}/intentos'}
    assert set(paths['/api/v1/attempts/{attempt_id}/current-scenario']) == {'get'}
    # El contrato posterior registra el inicio condicionado: no lo habilita.
    # Se conserva el rechazo y el router general sigue sin estar montado.
    bloqueado = h.principal.post(f'/api/v1/convocatorias/{h.convocatoria}/intentos',headers=h.main_headers)
    assert bloqueado.status_code == 503 and bloqueado.headers['Cache-Control'] == 'no-store'
    assert h.principal.get(f'/api/v1/participations/1/attempts/{h.ik}/result',headers=h.main_headers).status_code == 404
