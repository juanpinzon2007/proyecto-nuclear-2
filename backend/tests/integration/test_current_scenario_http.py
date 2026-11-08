"""Consulta privada real: PostgreSQL17 propio, JWT y grafo existente, sin mocks de autoridad."""
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import event, select

from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.participation.api.dependencies import obtener_consulta_escenario
from app.modules.participation.infrastructure.models import IntentoModel, PasoSimulacionModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.integration.test_participation_http_composition import (
    integracion, autor, pg_autoria, payload_valido, iniciar,  # noqa: F401
)


def comenzar(h):
    r = iniciar(h)
    assert r.status_code == 201
    return r.json()['id_intento'], f"/api/v1/attempts/{r.json()['id_intento']}/current-scenario"


def snapshot(h, ik):
    with h.sesiones() as s:
        return (s.execute(select(IntentoModel.__table__).where(IntentoModel.id_intento == ik)).all(),
                s.execute(select(PasoSimulacionModel.__table__).where(PasoSimulacionModel.id_intento == ik)).all())


def test_contenido_lista_blanca_repeticion_sin_dml_y_pregunta_futura_no_elegible(integracion, record_property):
    h = integracion; ik, path = comenzar(h); antes = snapshot(h, ik)
    engine = h.sesiones.kw['bind']; escrituras = []
    def observar(conn, cursor, sql, params, context, executemany):
        if sql.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE', 'ALTER', 'DROP')):
            escrituras.append(sql.split()[0])
    event.listen(engine, 'before_cursor_execute', observar)
    try:
        r = h.client.get(path, headers=h.headers)
        repetida = h.client.get(path, headers=h.headers)
        arbitraria = h.client.get(path, headers=h.headers, params={'question_id': h.escenas[2]['preguntas'][0]['id']})
    finally:
        event.remove(engine, 'before_cursor_execute', observar)
    assert r.status_code == repetida.status_code == 200
    assert r.json() == repetida.json()
    assert arbitraria.status_code == 422
    assert not escrituras and snapshot(h, ik) == antes
    body = r.json(); q = h.escenas[0]['preguntas'][0]
    assert set(body) == {'id_escenario', 'contexto', 'pregunta', 'recorrido_finalizado', 'respondidas'}
    assert body['id_escenario'] == h.escenas[0]['id']
    assert body['contexto'] == h.escenas[0]['contexto_situacional']
    assert body['pregunta'] == {'id': q['id'], 'enunciado': q['enunciado'],
        'opciones': [{'id': o['id'], 'texto': o['texto']} for o in q['opciones']]}
    assert not body['recorrido_finalizado'] and body['respondidas'] == 0
    assert r.headers['cache-control'] == 'no-store'
    assert all(h.escenas[n]['preguntas'][0]['id'] not in r.text for n in (1, 2))
    for clave in ('es_correcta', 'justificacion', 'rubrica', 'puntaje', 'nota', 'destino_id', h.codigo):
        assert clave not in r.text
    record_property('respuesta_publica', r.text)  # Solo campos públicos de laboratorio.


@pytest.mark.parametrize('problema,estado', [
    ('anonimo', 401), ('jwt', 401), ('ajeno', 403), ('retirada', 403),
    ('matricula', 403), ('inactivo', 401), ('sesion_finalizada', 403),
    ('fuera_horario', 403), ('vencido', 409), ('cerrado', 409), ('sin_composicion', 503),
])
def test_autorizacion_y_tiempo_no_conceden_contenido_ni_escriben(integracion, problema, estado):
    h = integracion; ik, path = comenzar(h); headers = h.headers
    if problema == 'anonimo': headers = {}
    elif problema == 'jwt': headers = {'Authorization': 'Bearer invalido'}
    elif problema == 'ajeno': headers = h.headers_ajeno
    elif problema == 'fuera_horario':
        # Cambiar únicamente el horario de sesión, sin retroceder el reloj individual.
        with h.sesiones.begin() as s:
            s.get(SesionProgramadaModel, h.sesion).fecha_inicio += timedelta(minutes=2)
    elif problema == 'vencido':
        ahora = h.reloj.ahora(); h.reloj.ahora = lambda: ahora + timedelta(minutes=30)
    elif problema == 'cerrado':
        assert h.client.post(f'/api/v1/attempts/{ik}/finish', headers=h.headers).status_code == 200
    elif problema == 'sin_composicion':
        h.client.app.dependency_overrides.pop(obtener_consulta_escenario)
    else:
        with h.sesiones.begin() as s:
            if problema == 'retirada': s.get(ConvocatoriaModel, h.convocatoria).estado = 'RETIRADA'
            elif problema == 'matricula': s.get(GrupoEstudianteORM, h.matricula).activo = False
            elif problema == 'inactivo': s.get(UsuarioORM, h.estudiante).activo = False
            else: s.get(SesionProgramadaModel, h.sesion).estado = 'FINALIZADO'
    antes = snapshot(h, ik)
    r = h.client.get(path, headers=headers)
    assert r.status_code == estado
    assert snapshot(h, ik) == antes
    assert h.escenas[0]['preguntas'][0]['enunciado'] not in r.text


def test_rama_alternativa_y_fin_solo_reflejan_respuestas_confirmadas(integracion):
    h = integracion; ik, path = comenzar(h)
    q = h.client.get(path, headers=h.headers).json()['pregunta']
    respuesta = h.client.post(f"/api/v1/attempts/{ik}/decisions/{q['id']}", headers=h.headers,
        json={'id_opcion': q['opciones'][1]['id']})
    assert respuesta.status_code == 201
    siguiente = h.client.get(path, headers=h.headers)
    assert siguiente.status_code == 200
    assert siguiente.json()['id_escenario'] == h.escenas[2]['id']
    assert siguiente.json()['respondidas'] == 1
    q2 = siguiente.json()['pregunta']
    assert h.client.post(f"/api/v1/attempts/{ik}/decisions/{q2['id']}", headers=h.headers,
        json={'id_opcion': q2['opciones'][0]['id']}).status_code == 201
    antes = snapshot(h, ik)
    assert h.client.get(path, headers=h.headers).json() == dict(id_escenario=None,
        contexto=None, pregunta=None, recorrido_finalizado=True, respondidas=2)
    assert snapshot(h, ik) == antes and antes[0][0].estado == 'EN_CURSO'


def publicar_segunda_edicion_y_archivar(h):
    from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
    from app.modules.cases.infrastructure.models import VersionCasoModel, CasoModel
    from tests.integration.test_cases_history import nuevo
    from tests.integration.test_cases_graph_authoring import configurar
    # Falta API de nueva edición: preparación administrativa explícita, reutilizada de RF18.
    with h.sesiones.begin() as s:
        anterior = s.get(VersionCasoModel, h.version); caso = s.get(CasoModel, anterior.caso_id)
        v = nuevo(); v.caso_id = caso.id; v.numero = 2; v.docente_creador_id = caso.docente_creador_id
        contenedor = CasoRepository(s)._mapear(v)
        caso.versiones.append(contenedor.versiones.pop())
    detalle = h.client.get(f'/api/v1/cases/{v.id}', headers=h.a.headers).json()
    e = detalle['escenarios'][0]
    g = dict(escenario_inicial_id=e['id'], transiciones=[dict(opcion_id=o['id'], tipo='FIN', destino_id=None)
        for o in e['preguntas'][0]['opciones']])
    assert configurar(h.a, str(v.id), g).status_code == 200
    assert h.client.post(f'/api/v1/cases/{v.id}/publish', headers=h.a.headers).status_code == 200
    assert h.client.post(f'/api/v1/cases/{h.version}/archive', headers=h.a.headers).status_code == 200
    return e['id']


def test_otra_edicion_publicada_y_archivo_no_sustituyen_escenario_historico(integracion):
    h = integracion; ik, path = comenzar(h)
    original = h.client.get(path, headers=h.headers)
    nueva_escena = publicar_segunda_edicion_y_archivar(h)
    actual = h.client.get(path, headers=h.headers)
    assert actual.status_code == 200 and actual.json() == original.json()
    assert nueva_escena not in actual.text


@pytest.mark.parametrize('fallo', ['grafo', 'sql'])
def test_dependencia_indisponible_no_devuelve_contenido_y_libera_transaccion(integracion, monkeypatch, fallo):
    from app.modules.cases.application.graph import GrafoNoDisponible
    from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
    from sqlalchemy.exc import OperationalError
    h = integracion; ik, path = comenzar(h); antes = snapshot(h, ik)
    def indisponible(*args, **kw):
        if fallo == 'grafo': raise GrafoNoDisponible('Recorrido temporalmente no disponible')
        raise OperationalError('SELECT', {}, Exception('Fallo controlado de laboratorio'))
    with monkeypatch.context() as m:
        m.setattr(RepositorioGrafoSQLAlchemy, 'leer', indisponible)
        r = h.client.get(path, headers=h.headers)
        assert r.status_code == 503
        assert h.escenas[0]['preguntas'][0]['enunciado'] not in r.text
    assert snapshot(h, ik) == antes
    assert h.client.get(path, headers=h.headers).status_code == 200
