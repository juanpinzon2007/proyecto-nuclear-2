"""RF04: selección MAIN/JWT/PG17 limitada a grants explícitos, sin autoconcesión."""
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel as E, DocenteEspacioAcademicoModel as Grant
from tests.integration.test_session_programming_http import programacion, autor, pg_autoria, payload_valido, conceder, solicitar  # noqa: F401


@pytest.fixture
def espacios_main(programacion):
    from app.main import app
    h = programacion
    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides.update(h.client.app.dependency_overrides)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield h, client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anteriores)


def test_seleccion_solo_espacios_asignados_y_lectura_independiente(espacios_main):
    h, client = espacios_main
    conceder(h)
    ajeno = uuid4()
    with h.sesiones.begin() as s:
        s.add(E(id=ajeno, nombre='Privado de otro docente'))
        s.flush()
        s.add(Grant(id_docente=h.a.propio + 1, espacio_academico_id=ajeno))
    r = client.get('/scheduling/espacios', headers=h.a.headers)
    assert r.status_code == 200, r.text
    assert r.json() == [{'id': h.body['espacio_academico_id'], 'nombre': 'Espacio RF-18 LAB'}]
    r = client.get('/scheduling/espacios', headers=h.a.ajeno)
    assert r.status_code == 200 and r.json() == [{'id': str(ajeno), 'nombre': 'Privado de otro docente'}]
    with h.sesiones() as s:
        assert s.get(Grant, (h.a.propio, UUID(h.body['espacio_academico_id']))) is not None
    assert solicitar(h).status_code == 201  # Seleccionable y programable; UUID histórico intacto.


def test_crear_recurso_no_concede_permiso_y_revocacion_se_refleja(espacios_main):
    h, client = espacios_main
    assert client.get('/scheduling/espacios', headers=h.a.headers).json() == []
    conceder(h)
    assert len(client.get('/scheduling/espacios', headers=h.a.headers).json()) == 1
    with h.sesiones.begin() as s:
        s.execute(delete(Grant).where(Grant.id_docente == h.a.propio))
    assert client.get('/scheduling/espacios', headers=h.a.headers).json() == []
    assert solicitar(h).status_code == 403


@pytest.mark.parametrize('actor,estado', [('anonimo', 401), ('invalido', 401), ('estudiante', 403)])
def test_seleccion_exige_jwt_y_docente_vigente(espacios_main, actor, estado):
    h, client = espacios_main
    auth = {'anonimo': {}, 'invalido': {'Authorization': 'Bearer invalido'}, 'estudiante': h.a.estudiante}[actor]
    r = client.get('/scheduling/espacios', headers=auth)
    assert r.status_code == estado
    assert 'nombre' not in r.json()


def test_consultas_concurrentes_no_hacen_dml_flush_commit(espacios_main):
    h, client = espacios_main
    conceder(h)
    engine = h.sesiones.kw['bind']
    escrituras, flushes, commits = [], [], []

    def sql(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'MERGE'}:
            escrituras.append(statement)

    def flush(*args): flushes.append(True)
    def commit(*args): commits.append(True)

    event.listen(engine, 'before_cursor_execute', sql)
    event.listen(Session, 'before_flush', flush)
    event.listen(Session, 'before_commit', commit)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respuestas = list(pool.map(lambda _: client.get('/scheduling/espacios', headers=h.a.headers), range(4)))
        assert all(r.status_code == 200 and r.json() == respuestas[0].json() for r in respuestas)
        assert len(respuestas[0].json()) == 1
        assert escrituras == flushes == commits == []
    finally:
        event.remove(engine, 'before_cursor_execute', sql)
        event.remove(Session, 'before_flush', flush)
        event.remove(Session, 'before_commit', commit)


def test_fallo_sql_no_expone_detalles_y_siguiente_lectura_funciona(espacios_main):
    h, client = espacios_main
    conceder(h)
    engine = h.sesiones.kw['bind']

    def fallar(conn, cursor, statement, parameters, context, executemany):
        if 'JOIN docente_espacio_academico' in statement:
            raise OperationalError('SELECT', {}, Exception('detalle SQL privado de laboratorio'))

    event.listen(engine, 'before_cursor_execute', fallar)
    try:
        r = client.get('/scheduling/espacios', headers=h.a.headers)
        assert r.status_code == 503 and r.json() == {'detail': 'Consulta académica no disponible.'}
    finally:
        event.remove(engine, 'before_cursor_execute', fallar)
    assert len(client.get('/scheduling/espacios', headers=h.a.headers).json()) == 1
    with h.sesiones() as s:
        assert s.get(Grant, (h.a.propio, UUID(h.body['espacio_academico_id']))) is not None
