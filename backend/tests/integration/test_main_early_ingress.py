"""RF-22 corregido: no ingreso hasta habilitación efectiva, HTTP/JWT/PG17.

Se conserva el archivo para trazabilidad de los escenarios anticipados retirados.
Los positivos registran espera real y congelan admisión mediante habilitación docente.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.modules.identity.api import dependencies as identity
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M, GrupoAcademicoORM as G
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.scheduling.api.router import obtener_reloj_ingreso, exigir_politica_ingreso_configurada
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C, EventoAuditoriaModel as E
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from tests.integration.test_participation_http_composition import (
    integracion, autor, pg_autoria, payload_valido, cantidades, iniciar,  # noqa: F401
)
from tests.integration.test_main_teacher_followup import observar_lectura
from tests.integration.test_attempt_start import IngresoLaboratorio

PATH = '/scheduling/validar-ingreso'


@pytest.fixture
def ingreso_main(integracion, monkeypatch):
    from app.main import app
    h = integracion
    with h.sesiones() as s:
        anterior = s.get(S,h.sesion)
        inicio, fin, espacio = anterior.fecha_inicio, anterior.fecha_fin, anterior.espacio_academico_id
    h.instante = inicio + timedelta(minutes=1)
    reloj = SimpleNamespace(ahora=lambda: h.instante)
    url = h.sesiones.kw['bind'].url
    tokens = h.client.app.dependency_overrides[identity.obtener_fabrica_tokens]()()
    for k, v in dict(POSTGRES_HOST=url.host, POSTGRES_PORT=str(url.port), POSTGRES_DB=url.database,
        POSTGRES_USER=url.username, POSTGRES_PASSWORD=url.password,
        IDENTITY_JWT_SECRET=tokens._secreto, IDENTITY_JWT_ISSUER=tokens._emisor,
        IDENTITY_JWT_AUDIENCE=tokens._audiencia,
        IDENTITY_INSTITUTIONAL_DOMAINS='["universidad.test"]').items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear(); get_engine.cache_clear(); get_session_factory.cache_clear()
    anteriores = dict(app.dependency_overrides); app.dependency_overrides.clear()
    app.dependency_overrides[obtener_reloj_ingreso] = lambda: reloj
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            # Credencial asignada SOLO como preparación administrativa del LAB.
            clave = 'Clave de docente exclusivamente para habilitacion LAB'
            with h.sesiones.begin() as s:
                docente = s.get(UsuarioORM,h.a.propio)
                correo = docente.correo; docente.clave_hash = obtener_hasheador().hash(clave)
            login_docente = client.post('/api/v1/identity/auth/personal',json={'correo':correo,'clave':clave})
            assert login_docente.status_code == 200
            h.docente_headers = {'Authorization':'Bearer '+login_docente.json()['access_token']}
            # Sesión NUEVA SIN_INICIAR, sin falsear ni borrar la auditoría de la
            # sesión anterior usada por la preparación compartida de 8B.
            creada = client.post('/scheduling/sesiones',headers=h.docente_headers,json={
                'espacio_academico_id':str(espacio),'version_caso_id':str(h.version),
                'fecha_inicio':inicio.isoformat(),'fecha_fin':fin.isoformat(),'tiempo_maximo_minutos':30})
            assert creada.status_code == 201, creada.text
            h.sesion = UUID(creada.json()['id'])
            with h.sesiones.begin() as s:
                a = s.get(A,h.asignacion)
                nueva = A(id_grupo=a.id_grupo,id_caso=a.id_caso,sesion_programada_id=h.sesion,
                    version_caso_id=h.version,apertura=a.apertura,cierre=a.cierre,
                    fecha_limite_ingreso=a.fecha_limite_ingreso,tiempo_maximo_min=a.tiempo_maximo_min)
                s.add(nueva);s.flush();h.asignacion = nueva.id_asignacion
            convocada = client.post(f'/scheduling/sesiones/{h.sesion}/convocatorias',headers=h.docente_headers,
                json={'estudiante_id':str(h.uuid_estudiante)})
            assert convocada.status_code == 201, convocada.text
            h.convocatoria = UUID(convocada.json()['convocatoria_id']); h.codigo = convocada.json()['codigo_acceso']
            h.base = f'/api/v1/convocatorias/{h.convocatoria}'
            h.body = {'id_asignacion':h.asignacion,'codigo_acceso':h.codigo}
            login = client.post('/api/v1/identity/auth/estudiantes', json={
                'correo': f'autor{h.estudiante}@universidad.test', 'codigo_convocatoria': h.codigo})
            assert login.status_code == 200
            h.main = client; h.main_headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
            h.headers = h.main_headers
            h.inicio = inicio
            assert set(app.dependency_overrides) == {obtener_reloj_ingreso}
            yield h
    finally:
        if get_engine.cache_info().currsize:
            motor = get_engine(); assert motor.url == url; motor.dispose()
        get_session_factory.cache_clear(); get_engine.cache_clear(); get_settings.cache_clear()
        app.dependency_overrides.clear(); app.dependency_overrides.update(anteriores)


def pedir(h, *, headers=None, **cambios):
    return h.main.post(PATH, headers=h.main_headers if headers is None else headers,
        json={'convocatoria_id': str(h.convocatoria), 'estudiante_id': str(h.uuid_estudiante),
              'codigo_acceso': h.codigo, **cambios})


def habilitar(h):
    r = h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'iniciar'})
    assert r.status_code == 200 and r.json()['estado'] == 'EN_CURSO', r.text
    with h.sesiones() as s:
        assert s.get(S,h.sesion).estado == 'EN_CURSO'
        assert s.scalar(select(func.count()).select_from(E).where(
            E.sesion_id==h.sesion,E.estado_anterior=='SIN_INICIAR',E.estado_nuevo=='EN_CURSO')) == 1


@pytest.fixture
def habilitada_lab(ingreso_main):
    h = ingreso_main
    r=h.main.post(f'/scheduling/convocatorias/{h.convocatoria}/espera',headers=h.main_headers,
        json={'codigo_acceso':h.codigo})
    assert r.status_code==201,r.text
    habilitar(h)
    return h


@pytest.mark.parametrize('segundos', [-601,-600,-300,-1,0,1])
def test_sin_habilitar_rechaza_aunque_se_alcance_horario(ingreso_main, segundos, record_property):
    h = ingreso_main; h.instante = h.inicio + timedelta(seconds=segundos)
    antes = cantidades(h)
    with observar_lectura() as operaciones:
        r = pedir(h); repetida = pedir(h)
    assert r.status_code == repetida.status_code == 403, r.text
    assert operaciones == [] and cantidades(h) == antes == ([], [])
    assert r.headers['cache-control'] == 'no-store'
    assert all(x not in r.text for x in [h.codigo, 'clave_hash', 'nota_final', 'es_correcta'])
    record_property('sin_habilitacion', r.text)


@pytest.mark.parametrize('estado,segundos,esperado', [
    ('EN_CURSO',0,403),('EN_CURSO',-300,403),('EN_CURSO',600,403),
    ('FINALIZADO',-300,403),
])
def test_habilitacion_sin_solicitud_no_concede_admision_ni_reabre_finalizadas(ingreso_main, estado, segundos, esperado):
    h = ingreso_main; h.instante = h.inicio + timedelta(seconds=segundos)
    habilitar(h)
    if estado == 'FINALIZADO':
        assert h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,
            json={'accion':'finalizar'}).status_code == 200
    with observar_lectura() as operaciones: r = pedir(h)
    assert r.status_code == esperado, r.text
    assert operaciones == [] and cantidades(h) == ([], [])


@pytest.mark.parametrize('problema,esperado', [
    ('anonimo',401),('token',401),('ajeno',403),('retirada',403),('otro_estudiante',403),
    ('codigo',403),('matricula',403),('sin_asignacion',503),('ambigua',503),('identidad_ambigua',503),
])
def test_identidad_convocatoria_y_matricula_persistentes(habilitada_lab, problema, esperado):
    h = habilitada_lab; headers = None; cambios = {}
    if problema == 'anonimo': headers = {}
    elif problema == 'token': headers = {'Authorization': 'Bearer invalido'}
    elif problema == 'ajeno': headers = h.headers_ajeno
    elif problema == 'otro_estudiante': cambios['estudiante_id'] = str(uuid4())
    elif problema == 'codigo': cambios['codigo_acceso'] = 'codigo incorrecto LAB'
    else:
        with h.sesiones.begin() as s:
            if problema == 'retirada': s.get(C,h.convocatoria).estado = 'RETIRADA'
            elif problema == 'matricula': s.get(M,h.matricula).activo = False
            elif problema == 'sin_asignacion': s.delete(s.get(A,h.asignacion))
            elif problema == 'identidad_ambigua':
                s.add(IA(id_usuario=h.estudiante,sistema='SCHEDULING',id_academico=uuid4()))
            else:
                grupo = G(id_profesor=s.get(G,s.get(M,h.matricula).id_grupo).id_profesor,nombre='Segundo grupo LAB',periodo='LAB')
                s.add(grupo); s.flush()
                s.add(M(id_grupo=grupo.id_grupo,id_estudiante=h.estudiante,
                    fecha_ingreso=h.inicio.replace(tzinfo=None)-timedelta(days=1)))
                a = s.get(A,h.asignacion)
                s.add(A(id_grupo=grupo.id_grupo,id_caso=a.id_caso,sesion_programada_id=a.sesion_programada_id,
                    version_caso_id=a.version_caso_id,apertura=a.apertura,cierre=a.cierre,
                    fecha_limite_ingreso=a.fecha_limite_ingreso,tiempo_maximo_min=a.tiempo_maximo_min))
    with observar_lectura() as operaciones: r = pedir(h,headers=headers,**cambios)
    assert r.status_code == esperado, r.text
    assert operaciones == [] and cantidades(h) == ([], [])
    assert h.codigo not in r.text and str(h.version) not in r.text


@pytest.mark.parametrize('campo,valor', [('tolerancia_minutos',1000),('ahora','2099-01-01'),('zona','Zona/NoExiste')])
def test_http_no_permite_manipular_politica_ni_zona(ingreso_main,campo,valor):
    h = ingreso_main
    with observar_lectura() as operaciones: r = pedir(h,**{campo:valor})
    assert r.status_code == 422 and h.codigo not in r.text
    assert operaciones == [] and cantidades(h) == ([], [])


def test_reloj_sin_zona_falla_cerrado_y_offset_equivalente_no_amplia(habilitada_lab):
    h = habilitada_lab
    h.instante = (h.inicio+timedelta(minutes=1)).astimezone(timezone(timedelta(hours=-5)))
    assert pedir(h).status_code == 200
    h.instante = h.instante.replace(tzinfo=None)
    assert pedir(h).status_code == 503
    assert cantidades(h) == ([], [])


def test_ingresos_habilitados_lab_concurrentes_son_solo_lectura(habilitada_lab):
    h = habilitada_lab; barrera = Barrier(2)
    def consultar():
        barrera.wait(timeout=10)
        return pedir(h)
    with observar_lectura() as operaciones, ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(lambda _:consultar(), range(2)))
    assert [r.status_code for r in respuestas] == [200,200]
    assert respuestas[0].json() == respuestas[1].json()
    assert operaciones == [] and cantidades(h) == ([], [])


def test_habilitacion_http_real_con_admision_persistida(habilitada_lab, record_property):
    h = habilitada_lab
    with observar_lectura() as operaciones:
        r = pedir(h); repetida = pedir(h)
    assert r.status_code == repetida.status_code == 200, r.text
    assert r.json() == repetida.json()
    assert r.json()['estado'] == 'EN_CURSO'
    assert r.json()['version_caso_id'] == str(h.version)
    assert r.headers['cache-control'] == 'no-store'
    assert all(x not in r.text for x in (h.codigo,'nota_final','es_correcta','clave_hash'))
    assert operaciones == [] and cantidades(h) == ([], [])
    with h.sesiones() as s:
        assert s.get(S,h.sesion).version_caso_id == h.version
        assert s.scalar(select(func.count()).select_from(E).where(E.sesion_id==h.sesion)) == 1
    record_property('validacion_habilitada_con_admision_real',r.text)


def test_cliente_no_puede_sustituir_version_historica(habilitada_lab):
    h = habilitada_lab
    with observar_lectura() as operaciones:
        r = pedir(h,version_caso_id=str(uuid4()))
        valida = pedir(h)
    assert r.status_code == 422 and valida.status_code == 200
    assert valida.json()['version_caso_id'] == str(h.version)
    assert operaciones == [] and cantidades(h) == ([], [])


def test_habilitada_sin_admision_rechaza_concurrentemente_sin_escribir(ingreso_main):
    h = ingreso_main; habilitar(h); barrera = Barrier(2)
    def consultar(_):
        barrera.wait(timeout=10)
        return pedir(h)
    with observar_lectura() as operaciones, ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(consultar,range(2)))
    assert [r.status_code for r in respuestas] == [403,403]
    assert operaciones == [] and cantidades(h) == ([], [])


def test_rechazo_sin_habilitar_no_inicia_y_main_bloquea_inicio_sin_politicas(ingreso_main):
    h = ingreso_main
    assert pedir(h).status_code == 403
    # Incluso la composición con políticas explícitas LAB conserva EN_CURSO.
    assert iniciar(h).status_code == 403
    assert cantidades(h) == ([], [])
    r = h.main.post(h.base+'/intentos', headers=h.main_headers,json=h.body)
    # La composición main posterior existe, pero carece de políticas productivas.
    # 503/no-store sustituye exclusivamente la antigua ausencia de ruta (404).
    assert r.status_code == 503 and r.headers['Cache-Control'] == 'no-store'
    assert cantidades(h) == ([], [])


def test_fallo_sql_no_valida_ingreso_ni_filtra_diagnostico(habilitada_lab):
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError
    h = habilitada_lab; motor = get_engine()
    def fallar(conn,cursor,statement,params,context,executemany):
        if 'grupo_estudiante' in statement.lower():
            raise OperationalError('SELECT','privado',Exception('diagnostico privado'))
    event.listen(motor,'before_cursor_execute',fallar)
    try: r = pedir(h)
    finally: event.remove(motor,'before_cursor_execute',fallar)
    assert r.status_code == 503 and 'privado' not in r.text
    assert cantidades(h) == ([], [])
