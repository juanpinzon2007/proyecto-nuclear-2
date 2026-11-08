"""RF-15 en app.main: JWT/relaciones/SQL reales, sin login docente provisional.

Se reutiliza preparación LAB de intentos; el token docente se emite únicamente
dentro de la fixture con TokensJWT. No sustituir autorización ni consultas.
"""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select, delete, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.modules.identity.api.dependencies import construir_tokens
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as Vinculo
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM as F
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from tests.integration.test_main_current_scenario import principal, integracion, autor, pg_autoria, payload_valido  # noqa: F401
from tests.integration.test_current_scenario_http import snapshot, publicar_segunda_edicion_y_archivar

BASE = '/api/v1/identity/seguimiento'


@pytest.fixture
def docente(principal):
    h = principal
    tokens = construir_tokens()  # Solo emisor de laboratorio, no login personal.
    h.docente_headers = {'Authorization': 'Bearer '+tokens.emitir(str(h.a.propio))}
    h.ajeno_headers = {'Authorization': 'Bearer '+tokens.emitir(str(h.a.propio+1))}
    with h.sesiones.begin() as s:
        s.add(Vinculo(id_usuario=h.a.propio+1, sistema='SCHEDULING', id_academico=uuid4()))
        h.pk = s.get(I, h.ik).id_participacion
    q = h.escenas[0]['preguntas'][0]
    assert h.principal.post(f'/api/v1/attempts/{h.ik}/decisions/{q["id"]}',
        headers=h.main_headers, json={'id_opcion':q['opciones'][0]['id']}).status_code == 201
    h.detalle_docente = f'{BASE}/participaciones/{h.pk}'
    return h


def datos(h):
    with h.sesiones() as s:
        return (snapshot(h,h.ik), s.execute(select(P.__table__).where(P.id_participacion==h.pk)).all(),
                s.execute(select(F.__table__).where(F.id_participacion==h.pk)).all())


@contextmanager
def observar_lectura():
    motor = get_engine()
    operaciones = []

    def sql(_, __, statement, ___, ____, _____):
        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','MERGE')):
            operaciones.append('DML')

    def commit(_):
        operaciones.append('COMMIT')

    def flush(s, _, __):
        if s.get_bind() is motor:
            operaciones.append('FLUSH')

    event.listen(motor,'before_cursor_execute',sql)
    event.listen(motor,'commit',commit)
    event.listen(Session,'before_flush',flush)
    try:
        yield operaciones
    finally:
        event.remove(motor,'before_cursor_execute',sql)
        event.remove(motor,'commit',commit)
        event.remove(Session,'before_flush',flush)


@pytest.mark.parametrize('estado',['activo','cerrado'])
def test_recorrido_principal_historico_sin_dml_flush_commit(docente, estado, record_property):
    h = docente
    nueva_escena = None
    if estado == 'cerrado':
        assert h.principal.post(f'/api/v1/attempts/{h.ik}/finish',headers=h.main_headers).status_code == 200
        assert h.principal.post(h.detalle_docente+'/feedback',headers=h.docente_headers,
            json={'texto':'Valoración individual histórica LAB'}).status_code == 201
        nueva_escena = publicar_segunda_edicion_y_archivar(h)
    antes = datos(h)
    with observar_lectura() as operaciones:
        casos = h.principal.get(BASE+'/casos',headers=h.docente_headers)
        assert casos.status_code == 200, casos.text
        caso = casos.json()[0]
        listado = h.principal.get(f'{BASE}/casos/{caso["id_caso"]}/participaciones',headers=h.docente_headers)
        detalle = h.principal.get(h.detalle_docente,headers=h.docente_headers)
        repetida = h.principal.get(h.detalle_docente,headers=h.docente_headers)
    assert listado.status_code == detalle.status_code == repetida.status_code == 200
    assert detalle.json() == repetida.json()
    assert operaciones == []
    assert datos(h) == antes
    d = detalle.json()
    assert caso['version_caso_id'] == d['version_caso_id'] == str(h.version)
    assert listado.json()[0]['id_participacion'] == str(h.pk)
    assert d['id_estudiante'] == str(h.estudiante) and d['id_sesion'] == str(h.sesion)
    assert d['respuestas'][0]['id_pregunta'] == h.escenas[0]['preguntas'][0]['id']
    assert d['respuestas'][0]['retroalimentacion'] == ('Justificación teórica.' if estado=='cerrado' else None)
    assert d['feedback_docente'] == ('Valoración individual histórica LAB' if estado=='cerrado' else None)
    for r in (casos,listado,detalle,repetida):
        assert r.headers['cache-control'] == 'no-store'
        for prohibido in ('clave_hash','codigo_hash','nota_final','puntaje','es_correcta','rubrica_id',h.codigo):
            assert prohibido not in r.text
    assert h.escenas[1]['preguntas'][0]['id'] not in detalle.text
    if nueva_escena:
        assert nueva_escena not in detalle.text
    record_property('detalle_'+estado,detalle.text)


@pytest.mark.parametrize('actor,codigo',[
    ('anonimo',401),('token_invalido',401),('estudiante',403),('administrador',403),
    ('docente_ajeno',403),('sin_vinculo',403),('vinculo_ambiguo',503),
])
def test_detalle_principal_rechaza_actor_o_identidad_no_autorizados(docente,actor,codigo):
    h = docente
    headers = dict(h.docente_headers)
    if actor == 'anonimo': headers = {}
    elif actor == 'token_invalido': headers = {'Authorization':'Bearer invalido'}
    elif actor == 'estudiante': headers = dict(h.main_headers)
    elif actor == 'docente_ajeno': headers = dict(h.ajeno_headers)
    elif actor == 'administrador':
        with h.sesiones.begin() as s:
            s.add(RolORM(id_rol=900,nombre='ADMINISTRADOR'))
            s.get(UsuarioORM,h.a.propio).id_rol = 900
    else:
        with h.sesiones.begin() as s:
            if actor == 'sin_vinculo':
                s.execute(delete(Vinculo).where(Vinculo.id_usuario==h.a.propio,Vinculo.sistema=='SCHEDULING'))
            else:
                s.add(Vinculo(id_usuario=h.a.propio,sistema='SCHEDULING',id_academico=uuid4()))
    # Cabecera/query nunca pueden acreditar la identidad del dueño.
    headers['X-Docente-Id'] = str(h.a.propio)
    antes = datos(h)
    with observar_lectura() as operaciones:
        r = h.principal.get(h.detalle_docente+'?id_docente='+str(h.a.propio),headers=headers)
    assert r.status_code == codigo, r.text
    assert datos(h) == antes and operaciones == []
    assert 'respuestas' not in r.text and 'clave_hash' not in r.text and h.codigo not in r.text


def test_lecturas_principales_concurrentes_no_escriben(docente):
    h = docente
    barrera = Barrier(2,timeout=15)
    antes = datos(h)

    def consultar(_):
        barrera.wait()
        return h.principal.get(h.detalle_docente,headers=h.docente_headers)

    with observar_lectura() as operaciones:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respuestas = list(pool.map(consultar,range(2)))
    assert all(r.status_code==200 for r in respuestas)
    assert respuestas[0].json() == respuestas[1].json()
    assert operaciones == [] and datos(h) == antes


def test_fallo_de_lectura_sql_principal_es_saneado_y_no_escribe(docente):
    h = docente
    motor = get_engine()
    antes = datos(h)

    def fallar(_, __, statement, ___, ____, _____):
        if 'FROM paso_simulacion' in statement:
            raise OperationalError('SQL no público',{},RuntimeError('MARCADOR_PRIVADO_RF15'))

    event.listen(motor,'before_cursor_execute',fallar)
    try:
        with observar_lectura() as operaciones:
            r = h.principal.get(h.detalle_docente,headers=h.docente_headers)
    finally:
        event.remove(motor,'before_cursor_execute',fallar)
    assert r.status_code == 503, r.text
    assert operaciones == [] and datos(h) == antes
    assert 'MARCADOR_PRIVADO_RF15' not in r.text and 'SQL no público' not in r.text
