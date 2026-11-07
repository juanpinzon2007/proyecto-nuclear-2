"""Bootstrap controlado; catálogo LAB, primera cuenta creada por código real.

PostgreSQL17 propio por escenario. HTTP usa login/JWT y dependencias SQL reales.
Solo se simula la entrada de terminal para automatizar getpass; no la autorización.
"""
from concurrent.futures import ThreadPoolExecutor
import secrets
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from alembic import command
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import ConflictoIdentidad, IntegracionPendiente
from app.modules.identity.infrastructure import bootstrap_admin as bootstrap
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM, PermisoORM, RolPermisoORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic
from tests.integration.test_cases_graph_authoring import payload_valido  # noqa: F401


@pytest.fixture
def lab(monkeypatch):
    with motor_postgresql_desechable() as engine:
        with engine.begin() as conn:
            command.upgrade(config_alembic(conn), 'head')
            # Catálogo explícito de prueba; el comando NO crea ni modifica roles.
            conn.execute(sa.insert(RolORM), [dict(id_rol=1,nombre='DOCENTE'),
                dict(id_rol=2,nombre='ESTUDIANTE'),dict(id_rol=17,nombre='ADMINISTRADOR')])
            conn.execute(sa.insert(PermisoORM).values(id_permiso=1,codigo='CREAR_CASOS',descripcion='Catálogo LAB'))
            conn.execute(sa.insert(RolPermisoORM).values(id_rol=1,id_permiso=1))
        sesiones = sessionmaker(engine, expire_on_commit=False)
        url = engine.url
        for k,v in dict(POSTGRES_HOST=url.host,POSTGRES_PORT=str(url.port),POSTGRES_DB=url.database,
            POSTGRES_USER=url.username,POSTGRES_PASSWORD=url.password,IDENTITY_JWT_SECRET=secrets.token_urlsafe(48),
            IDENTITY_JWT_ISSUER='bootstrap-lab',IDENTITY_JWT_AUDIENCE='bootstrap-lab').items():
            monkeypatch.setenv(k,v)
        get_settings.cache_clear();get_session_factory.cache_clear();get_engine.cache_clear()
        h = SimpleNamespace(engine=engine,sesiones=sesiones,correo=f'admin-{uuid4().hex}@universidad.test',clave=secrets.token_urlsafe(32))
        assert contar(h) == 0
        try: yield h
        finally:
            if get_engine.cache_info().currsize:
                actual = get_engine(); assert actual.url == url; actual.dispose()
            get_settings.cache_clear();get_session_factory.cache_clear();get_engine.cache_clear()


def contar(h):
    with h.sesiones() as s: return s.scalar(sa.select(sa.func.count()).select_from(U))


def inicializar(h, **kw):
    return bootstrap.inicializar_primer_administrador(**(dict(correo=h.correo,
        nombre='Administrador inicial LAB',clave=h.clave,crear_sesion=h.sesiones) | kw))


def test_primera_cuenta_persiste_login_http_y_alta_docente_sin_escalamiento(lab,payload_valido):
    from app.main import app
    h = lab; inicial = inicializar(h)
    assert inicial.roles == frozenset({Rol.ADMINISTRADOR}) and inicial.permisos == frozenset()
    with h.sesiones() as s:
        u = s.get(U,int(inicial.id_usuario))
        assert u.id_rol == 17 and u.activo and u.clave_hash != h.clave
        assert obtener_hasheador().verify(h.clave,u.clave_hash)
    assert app.dependency_overrides == {}
    with TestClient(app) as client:
        login = client.post('/api/v1/identity/auth/personal',json={'correo':h.correo,'clave':h.clave})
        assert login.status_code == 200
        admin = {'Authorization':'Bearer '+login.json()['access_token']}
        assert client.get('/api/v1/identity/me',headers=admin).json()['roles'] == ['ADMINISTRADOR']
        clave = secrets.token_urlsafe(32)
        datos = dict(correo=f'docente-{uuid4().hex}@universidad.test',nombre='Docente LAB',clave=clave,
                     roles=['DOCENTE'],permisos=['CREAR_CASOS'])
        alta = client.post('/api/v1/identity/docentes',headers=admin,json=datos)
        assert alta.status_code == 201 and 'clave_hash' not in alta.text and clave not in alta.text
        ingreso = client.post('/api/v1/identity/auth/personal',json={'correo':datos['correo'],'clave':clave})
        assert ingreso.status_code == 200
        docente = {'Authorization':'Bearer '+ingreso.json()['access_token']}
        assert client.post('/api/v1/identity/docentes',headers=docente,json=datos).status_code == 403
        assert client.post('/api/v1/cases',headers=admin,json=payload_valido).status_code == 403
        assert client.post('/api/v1/identity/docentes',headers=admin,
            json=datos | {'roles':['DOCENTE','ADMINISTRADOR']}).status_code == 422
        assert client.post('/api/v1/identity/docentes',headers=admin,
            json=datos | {'roles':['DOCENTE ADMINISTRADOR']}).status_code == 422
    with h.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(IdentidadAcademicaORM)) == 0
        assert s.execute(sa.select(RolPermisoORM.id_rol,RolPermisoORM.id_permiso)).all() == [(1,1)]
    assert contar(h) == 2


@pytest.mark.parametrize('activo',[True,False])
def test_no_repite_ni_recupera_administrador_existente(lab,activo):
    h = lab; primero = inicializar(h)
    with h.sesiones.begin() as s:
        u=s.get(U,int(primero.id_usuario));u.activo=activo;original=u.clave_hash
    with pytest.raises(ConflictoIdentidad): inicializar(h,correo=f'otro-{uuid4().hex}@universidad.test')
    with h.sesiones() as s:
        u=s.get(U,int(primero.id_usuario));assert u.clave_hash==original and u.activo==activo
    assert contar(h)==1


@pytest.mark.parametrize('catalogo',['ausente','ambiguo','normalizado'])
def test_catalogo_no_se_inventa_ni_se_supone_id(lab,catalogo):
    h = lab
    with h.sesiones.begin() as s:
        if catalogo=='ausente': s.delete(s.get(RolORM,17))
        elif catalogo=='ambiguo': s.add(RolORM(id_rol=18,nombre='\tADMINISTRADOR\t'))
        else: s.get(RolORM,17).nombre=' administrador '
    if catalogo=='normalizado':
        assert inicializar(h).roles==frozenset({Rol.ADMINISTRADOR})
    else:
        with pytest.raises(IntegracionPendiente): inicializar(h)
        assert contar(h)==0


def test_correo_existente_normalizado_no_eleva_una_cuenta(lab):
    h=lab
    with h.sesiones.begin() as s:
        u=U(id_rol=1,nombre='Cuenta previa LAB',correo=' '+h.correo.upper()+' ',clave_hash='sin-login-LAB')
        s.add(u);s.flush();pk=u.id_usuario
    with pytest.raises(ConflictoIdentidad): inicializar(h)
    with h.sesiones() as s:
        assert s.get(U,pk).id_rol==1 and s.get(U,pk).clave_hash=='sin-login-LAB'
    assert contar(h)==1


def test_dos_inicializaciones_concurrentes_solo_confirman_una(lab):
    h=lab;barrera=Barrier(2)
    def ejecutar(n):
        barrera.wait(timeout=10)
        try: return ('creada',inicializar(h,correo=f'admin{n}-{uuid4().hex}@universidad.test').id_usuario)
        except ConflictoIdentidad: return ('rechazada',None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(ejecutar,1);b=pool.submit(ejecutar,2)
        assert sorted([a.result(timeout=15)[0],b.result(timeout=15)[0]])==['creada','rechazada']
    assert contar(h)==1


def test_error_pg_tras_insert_revierte_y_permite_reintento(lab):
    h=lab
    def fallo(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith('insert into usuario'):
            conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(h.engine,'after_cursor_execute',fallo)
    try:
        with pytest.raises(IntegracionPendiente): inicializar(h)
    finally: sa.event.remove(h.engine,'after_cursor_execute',fallo)
    assert contar(h)==0
    assert inicializar(h).roles==frozenset({Rol.ADMINISTRADOR}) and contar(h)==1


def test_snapshot_previo_no_se_admite_para_bootstrap(lab):
    h=lab
    fabrica=sessionmaker(h.engine.execution_options(isolation_level='REPEATABLE READ'))
    with pytest.raises(IntegracionPendiente): inicializar(h,crear_sesion=fabrica)
    assert contar(h)==0


def consola(monkeypatch, claves):
    entradas=iter(claves)
    monkeypatch.setattr(bootstrap.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(bootstrap.sys.stderr,'isatty',lambda:True)
    monkeypatch.setattr(bootstrap.getpass,'getpass',lambda prompt:next(entradas))


def argumentos(h):
    return ['--correo',h.correo,'--nombre','Administrador LAB','--confirmar-base',h.engine.url.database]


def test_comando_con_entrada_de_terminal_controlada_y_sql_real(lab,monkeypatch,capsys):
    h=lab;consola(monkeypatch,[h.clave,h.clave])
    assert bootstrap.main(argumentos(h))==0
    salida=capsys.readouterr()
    assert 'id_usuario=' in salida.out and h.clave not in salida.out+salida.err
    assert h.correo not in salida.out+salida.err
    assert contar(h)==1


def test_consola_y_argumentos_no_revelan_claves_ni_abren_operacion(monkeypatch,capsys):
    secreto=secrets.token_urlsafe(32)
    args=['--correo','operador@universidad.test','--nombre','Operador LAB','--confirmar-base','no-conectar']
    assert bootstrap.main(args+['--clave',secreto])==2
    monkeypatch.setattr(bootstrap.sys.stdin,'isatty',lambda:False)
    assert bootstrap.main(args)==2
    salida=capsys.readouterr()
    assert secreto not in salida.out+salida.err and 'id_usuario=' not in salida.out


def test_confirmacion_de_clave_y_destino_fallan_sin_alta(lab,monkeypatch,capsys):
    h=lab;consola(monkeypatch,[h.clave,'otra clave SOLO LAB'])
    assert bootstrap.main(argumentos(h))==2
    assert bootstrap.main(argumentos(h)[:-1]+['base-distinta'])==2
    assert contar(h)==0
    salida=capsys.readouterr();assert h.clave not in salida.out+salida.err
