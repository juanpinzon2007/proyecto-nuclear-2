"""Preparación docente main/JWT/PG17 reales; ningún override de seguridad.

Reutiliza el contexto SQL de las 13 pruebas internas. Los únicos puntajes de
ejemplo son LAB explícitos: HTTP no los devuelve ni publica.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import secrets
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.scheduling.domain.access_codes import hash_codigo
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from tests.integration.test_evaluation_readiness import (
    revision, c, pg_resultados, otro_convocado, cerrar_sesion_fixture, evaluar, intento, FECHA,  # noqa: F401
)

BASE='/scheduling/sesiones/'


@pytest.fixture
def docente_http(revision,monkeypatch):
    from app.main import app
    h=revision;clave=secrets.token_urlsafe(32);codigo=secrets.token_urlsafe(32)
    with h.sesiones.begin() as s:
        profesor=s.get(U,h.docente);profesor.clave_hash=obtener_hasheador().hash(clave)
        docente_correo=profesor.correo
        if s.get(RolORM,3) is None:s.add(RolORM(id_rol=3,nombre='ADMINISTRADOR'));s.flush()
        ajeno=U(id_rol=1,nombre='Docente ajeno LAB',correo=f'{uuid4().hex}@fixture.test',clave_hash=profesor.clave_hash)
        admin=U(id_rol=3,nombre='Admin LAB',correo=f'{uuid4().hex}@fixture.test',clave_hash=profesor.clave_hash)
        s.add_all([ajeno,admin]);s.flush()
        for sistema in ('CASES','SCHEDULING'):s.add(IA(id_usuario=ajeno.id_usuario,sistema=sistema,id_academico=uuid4()))
        cuentas={'docente':docente_correo,'ajeno':ajeno.correo,'admin':admin.correo}
        estudiante_correo=s.get(U,h.alumno).correo
        s.get(C,h.datos['convocatoria_id']).codigo_hash=hash_codigo(codigo)
    url=h.engine.url
    for k,v in dict(POSTGRES_HOST=url.host,POSTGRES_PORT=str(url.port),POSTGRES_DB=url.database,
        POSTGRES_USER=url.username,POSTGRES_PASSWORD=url.password,IDENTITY_JWT_SECRET=secrets.token_urlsafe(48),
        IDENTITY_JWT_ISSUER='readiness-http-lab',IDENTITY_JWT_AUDIENCE='readiness-http-lab',
        IDENTITY_INSTITUTIONAL_DOMAINS='["fixture.test"]',PARTICIPATION_TIMESTAMP_ZONE='UTC').items():monkeypatch.setenv(k,v)
    get_settings.cache_clear();get_engine.cache_clear();get_session_factory.cache_clear()
    assert app.dependency_overrides=={}
    try:
        with TestClient(app,raise_server_exceptions=False) as client:
            auth={}
            for key,correo in cuentas.items():
                r=client.post('/api/v1/identity/auth/personal',json={'correo':correo,'clave':clave})
                assert r.status_code==200
                auth[key]={'Authorization':'Bearer '+r.json()['access_token']}
            r=client.post('/api/v1/identity/auth/estudiantes',json={'correo':estudiante_correo,'codigo_convocatoria':codigo})
            assert r.status_code==200
            auth['estudiante']={'Authorization':'Bearer '+r.json()['access_token']}
            yield SimpleNamespace(c=h,client=client,auth=auth,path=BASE+str(h.sesion)+'/evaluacion/preparacion',codigo=codigo)
    finally:
        if get_engine.cache_info().currsize:
            actual=get_engine();assert actual.url==url;actual.dispose()
        get_session_factory.cache_clear();get_engine.cache_clear();get_settings.cache_clear()


@contextmanager
def lectura(h):
    engines={h.c.engine,get_engine()};ops=[];config=[]
    def sql(conn,cursor,statement,*args):
        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','MERGE','TRUNCATE','CREATE','ALTER','DROP')):ops.append('DML/DDL')
    def after(conn,cursor,statement,*args):
        if statement.lower().startswith('set transaction read only'):
            config.append((conn.get_isolation_level(),conn.exec_driver_sql('SHOW transaction_read_only').scalar()))
    def commit(conn):ops.append('COMMIT')
    def flush(s,*args):
        if s.get_bind() in engines:ops.append('FLUSH')
    for e in engines:
        sa.event.listen(e,'before_cursor_execute',sql);sa.event.listen(e,'after_cursor_execute',after);sa.event.listen(e,'commit',commit)
    sa.event.listen(Session,'before_flush',flush)
    try:
        yield config
        assert ops==[]
        assert all(x==('REPEATABLE READ','on') for x in config)
    finally:
        for e in engines:
            sa.event.remove(e,'before_cursor_execute',sql);sa.event.remove(e,'after_cursor_execute',after);sa.event.remove(e,'commit',commit)
        sa.event.remove(Session,'before_flush',flush)


def test_main_preparacion_privada_retiradas_sin_intentos_y_repeticiones(docente_http):
    h=docente_http;c=h.c
    sin_p=otro_convocado(c);retirada=otro_convocado(c,retirado=True)
    with c.sesiones.begin() as s:
        permiso=PermisoIntentoExtraORM(id_participacion=c.pk,id_profesor=c.docente,cantidad_autorizada=1,
            justificacion='Preparación de laboratorio, no política productiva',fecha_autorizacion=FECHA)
        s.add(permiso);s.flush();pk=permiso.id_permiso_extra
    segundo=intento(c,c.pk,numero_intento=2,id_permiso_extra=pk)
    with lectura(h) as config:
        r=h.client.get(h.path,headers=h.auth['docente'])
    assert r.status_code==200,r.text
    assert config and r.headers['cache-control']=='no-store'
    j=r.json();assert set(j)=={'id_sesion','version_caso_id','estado_sesion','convocatorias','pendientes','publicable'}
    assert j['version_caso_id']==str(c.version.id) and j['publicable'] is False
    filas={f['id_convocatoria']:f for f in j['convocatorias']}
    assert len(filas)==3 and filas[str(sin_p)]['id_participacion'] is None
    assert filas[str(sin_p)]['intentos']==[] and filas[str(retirada)]['estado']=='RETIRADA'
    assert 'TRATAMIENTO_RETIRO_PENDIENTE' in filas[str(retirada)]['pendientes']
    actual=filas[str(c.datos['convocatoria_id'])]
    assert [i['id_intento'] for i in actual['intentos']]==[c.ik,segundo]
    assert 'CONSOLIDACION_REPETICIONES_PENDIENTE' in actual['pendientes']
    assert not any(k in r.text for k in ('nota_final','puntaje','rubrica_id','version_regla','id_resultado_tecnico','procedencia','es_correcta','justificacion','@',h.codigo))
    with c.sesiones() as s:
        from app.modules.participation.infrastructure.models import IntentoModel
        assert s.get(IntentoModel,segundo).estado=='EN_CURSO'  # No se vence al leer.


def test_resultado_lab_se_verifica_sin_exponerlo_y_version_no_cambia(docente_http):
    h=docente_http;tecnico=evaluar(h.c);cerrar_sesion_fixture(h.c)
    with lectura(h):r=h.client.get(h.path,headers=h.auth['docente'])
    assert r.status_code==200
    j=r.json();i=j['convocatorias'][0]['intentos'][0]
    assert i['resultado_tecnico_disponible'] is True and 'id_resultado_tecnico' not in i
    assert j['version_caso_id']==str(h.c.version.id) and j['estado_sesion']=='FINALIZADO'
    assert j['publicable'] is False and 'RESULTADO_LABORATORIO_NO_OFICIAL' in j['convocatorias'][0]['pendientes']


@pytest.mark.parametrize('problema,estado',[
    ('anonimo',401),('invalido',401),('ajeno',403),('estudiante',403),('admin',403),
    ('inactivo',401),('sin_vinculo',403),('ambiguo',503),('docente_admin_no_definido',503)])
def test_autenticacion_y_permisos_persistentes_main(docente_http,problema,estado):
    h=docente_http;auth=h.auth.get(problema,h.auth['docente'])
    if problema=='anonimo':auth={}
    elif problema=='invalido':auth={'Authorization':'Bearer invalido-LAB'}
    elif problema in ('inactivo','sin_vinculo','ambiguo','docente_admin_no_definido'):
        with h.c.sesiones.begin() as s:
            if problema=='inactivo':s.get(U,h.c.docente).activo=False
            elif problema=='sin_vinculo':s.execute(sa.delete(IA).where(IA.id_usuario==h.c.docente))
            elif problema=='ambiguo':s.add(IA(id_usuario=h.c.docente,sistema='SCHEDULING',id_academico=uuid4()))
            else:
                rol=s.scalar(sa.select(RolORM).where(RolORM.nombre=='DOCENTE ADMINISTRADOR'))
                if rol is None:rol=RolORM(id_rol=77,nombre='DOCENTE ADMINISTRADOR');s.add(rol);s.flush()
                s.get(U,h.c.docente).id_rol=rol.id_rol
    with lectura(h):r=h.client.get(h.path,headers=auth|{'X-Docente-Id':str(h.c.docente)})
    assert r.status_code==estado and 'convocatorias' not in r.text


@pytest.mark.parametrize('inconsistencia',['grupo_ajeno','alumno_fuera_de_grupo','creador_ajeno'])
def test_no_filtra_datos_entre_grupos_o_casos(docente_http,inconsistencia):
    h=docente_http
    if inconsistencia=='alumno_fuera_de_grupo':otro_convocado(h.c,matricula=False)
    else:
        with h.c.sesiones.begin() as s:
            if inconsistencia=='grupo_ajeno':
                a=s.get(A,h.c.datos['id_asignacion']);s.get(G,a.id_grupo).id_profesor=h.c.alumno
            else:
                v=s.scalar(sa.select(IA).where(IA.id_usuario==h.c.docente,IA.sistema=='CASES'));v.id_academico=uuid4()
    with lectura(h):r=h.client.get(h.path,headers=h.auth['docente'])
    assert r.status_code==(403 if inconsistencia=='creador_ajeno' else 503)
    assert 'convocatorias' not in r.text and 'id_estudiante' not in r.text


@pytest.mark.parametrize('zona',[None,'Zona/NoExiste'])
def test_zona_obligatoria_sin_default(docente_http,monkeypatch,zona):
    h=docente_http
    if zona is None:monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE')
    else:monkeypatch.setenv('PARTICIPATION_TIMESTAMP_ZONE',zona)
    get_settings.cache_clear()
    with lectura(h):r=h.client.get(h.path,headers=h.auth['docente'])
    assert r.status_code==503


def test_lecturas_http_concurrentes_no_escriben(docente_http):
    h=docente_http
    with lectura(h) as config,ThreadPoolExecutor(max_workers=2) as pool:
        respuestas=list(pool.map(lambda _:h.client.get(h.path,headers=h.auth['docente']),range(2)))
    assert all(r.status_code==200 for r in respuestas) and respuestas[0].json()==respuestas[1].json()
    assert len(config)==2


def test_error_sql_no_filtra_informe_parcial_y_recupera(docente_http):
    h=docente_http;engine=get_engine()
    def fallar(conn,cursor,statement,*args):
        if statement.startswith('SELECT convocatoria.'):
            raise OperationalError('SQL_INTERNO_LAB',{},RuntimeError('MARCADOR_NO_PUBLICO'))
    sa.event.listen(engine,'before_cursor_execute',fallar)
    try:
        with lectura(h):r=h.client.get(h.path,headers=h.auth['docente'])
    finally:sa.event.remove(engine,'before_cursor_execute',fallar)
    assert r.status_code==503 and 'MARCADOR_NO_PUBLICO' not in r.text and 'SQL_INTERNO_LAB' not in r.text
    assert h.client.get(h.path,headers=h.auth['docente']).status_code==200


def test_uuid_parametros_y_sesion_inaccesible(docente_http):
    h=docente_http
    with lectura(h):
        assert h.client.get(BASE+'no-uuid/evaluacion/preparacion',headers=h.auth['docente']).status_code==422
        assert h.client.get(h.path+'?docente_id=otro',headers=h.auth['docente']).status_code==422
        assert h.client.get(BASE+str(uuid4())+'/evaluacion/preparacion',headers=h.auth['docente']).status_code==403
