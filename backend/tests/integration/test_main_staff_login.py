"""Correo/clave del personal en main, Argon2/JWT/SQL reales y PG17 propio.

El primer administrador y el catálogo son preparación explícita de laboratorio.
Los JWT usados en las operaciones se obtienen del nuevo endpoint, no de un fake.
No aprueba bootstrap institucional ni políticas de claves/sesiones adicionales.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import select,func,delete,event
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_engine,get_session_factory
from app.modules.identity.api.dependencies import construir_tokens
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM, RolPermisoORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as V
from tests.integration.test_cases_graph_authoring import pg_autoria,payload_valido  # noqa: F401
from tests.integration.test_main_teacher_followup import observar_lectura

BASE='/api/v1/identity'
CLAVE_LAB='Clave exclusivamente sintética del laboratorio personal'


@pytest.fixture(scope='module')
def hash_lab():
    return obtener_hasheador().hash(CLAVE_LAB)


@pytest.fixture
def personal(pg_autoria,monkeypatch,hash_lab):
    from app.main import app
    sesiones=pg_autoria
    with sesiones.begin() as s:
        if s.get(RolORM,3) is None:
            s.add(RolORM(id_rol=3,nombre='ADMINISTRADOR'))
        if s.get(RolPermisoORM,(1,1)) is None:
            s.add(RolPermisoORM(id_rol=1,id_permiso=1))
        cuentas=[]
        for rol in (3,1,1,2):
            u=U(id_rol=rol,nombre='Cuenta LAB personal',correo=f'personal-{uuid4().hex}@universidad.test',clave_hash=hash_lab)
            s.add(u);s.flush();cuentas.append((u.id_usuario,u.correo))
    url=sesiones.kw['bind'].url
    for k,v in dict(POSTGRES_HOST=url.host,POSTGRES_PORT=str(url.port),POSTGRES_DB=url.database,
        POSTGRES_USER=url.username,POSTGRES_PASSWORD=url.password,
        IDENTITY_JWT_SECRET='clave-firma-exclusiva-laboratorio-personal-'*2,
        IDENTITY_JWT_ISSUER='personal-lab',IDENTITY_JWT_AUDIENCE='personal-lab',IDENTITY_JWT_MINUTES='15').items():
        monkeypatch.setenv(k,v)
    # El login personal no exige un dominio estudiantil ni una convocatoria.
    monkeypatch.delenv('IDENTITY_INSTITUTIONAL_DOMAINS',raising=False)
    get_settings.cache_clear();get_engine.cache_clear();get_session_factory.cache_clear()
    anteriores=dict(app.dependency_overrides);app.dependency_overrides.clear()
    try:
        with TestClient(app,raise_server_exceptions=False) as cliente:
            assert app.dependency_overrides=={}
            yield SimpleNamespace(cliente=cliente,sesiones=sesiones,admin=cuentas[0],docente=cuentas[1],
                ajeno=cuentas[2],estudiante=cuentas[3],hash=hash_lab)
    finally:
        if get_engine.cache_info().currsize:
            motor=get_engine();assert motor.url==url;motor.dispose()
        get_session_factory.cache_clear();get_engine.cache_clear();get_settings.cache_clear()
        app.dependency_overrides.clear();app.dependency_overrides.update(anteriores)


def login(h,cuenta=None,**cambios):
    return h.cliente.post(BASE+'/auth/personal',json={'correo':(cuenta or h.docente)[1],'clave':CLAVE_LAB,**cambios})


def headers(h,cuenta=None):
    r=login(h,cuenta);assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}


def test_admin_ingresa_crea_docente_con_hash_y_docente_ingresa_sin_crear_vinculos(personal,payload_valido):
    h=personal;admin=headers(h,h.admin)
    correo=f'alta-{uuid4().hex}@universidad.test'
    clave='Asignada por administrador SOLO LAB'
    body={'nombre':'Docente creado por API LAB','correo':correo,'clave':clave,
          'roles':['DOCENTE'],'permisos':['CREAR_CASOS']}
    r=h.cliente.post(BASE+'/docentes',headers=admin,json=body)
    assert r.status_code==201,r.text
    nuevo=r.json()['id_usuario']
    assert clave not in r.text and 'clave_hash' not in r.text
    with h.sesiones() as s:
        fila=s.get(U,int(nuevo))
        assert fila.clave_hash!=clave and obtener_hasheador().verify(clave,fila.clave_hash)
    with observar_lectura() as operaciones:
        r=h.cliente.post(BASE+'/auth/personal',json={'correo':'  '+correo.upper()+'  ','clave':clave})
    assert r.status_code==200,r.text
    assert operaciones==[] and r.headers['cache-control']=='no-store'
    token=r.json()['access_token'];doc={'Authorization':'Bearer '+token}
    assert construir_tokens().verificar(token).id_convocatoria is None
    claims=jwt.decode(token,options={'verify_signature':False})  # Solo inspección de token ya verificado.
    assert not {'roles','permisos','correo','clave','codigo','convocatoria_id'}.intersection(claims)
    me=h.cliente.get(BASE+'/me',headers=doc)
    assert me.status_code==200 and me.json()['roles']==['DOCENTE']
    assert h.cliente.get(BASE+'/me',headers=admin).json()['roles']==['ADMINISTRADOR']
    asignacion=BASE+'/docentes/'+nuevo+'/autorizaciones'
    assert h.cliente.put(asignacion,headers=admin,
        json={'roles':['DOCENTE'],'permisos':['CREAR_CASOS']}).status_code==200
    # No simular permisos individuales modificando el catálogo compartido.
    assert h.cliente.put(asignacion,headers=admin,
        json={'roles':['DOCENTE'],'permisos':[]}).status_code==422
    assert h.cliente.post(BASE+'/docentes',headers=doc,json=body).status_code==403
    assert h.cliente.post('/api/v1/cases',headers=admin,json=payload_valido).status_code==403
    assert h.cliente.post('/api/v1/cases',headers=doc,json=payload_valido).status_code==403
    with h.sesiones() as s:
        assert s.scalar(select(func.count()).select_from(V).where(V.id_usuario==int(nuevo)))==0


def test_login_real_no_otorga_casos_ajenos_ni_permisos_eliminados(personal,payload_valido):
    h=personal
    with h.sesiones.begin() as s:
        for cuenta in (h.docente,h.ajeno):
            s.add(V(id_usuario=cuenta[0],sistema='CASES',id_academico=uuid4()))
    propio=headers(h);ajeno=headers(h,h.ajeno)
    creado=h.cliente.post('/api/v1/cases',headers=propio,json=payload_valido)
    assert creado.status_code==201,creado.text
    path='/api/v1/cases/'+creado.json()['version_id']
    assert h.cliente.get(path,headers=propio).status_code==200
    assert h.cliente.get(path,headers=ajeno).status_code==404
    with h.sesiones.begin() as s:
        s.execute(delete(RolPermisoORM).where(RolPermisoORM.id_rol==1,RolPermisoORM.id_permiso==1))
    assert h.cliente.post('/api/v1/cases',headers=propio,json=payload_valido).status_code==403


@pytest.mark.parametrize('problema,estado',[
    ('clave',401),('ausente',401),('inactivo',401),('estudiante',401),
    ('hash_corrupto',401),('correo_ambiguo',503),('correo_invalido',401),
])
def test_login_personal_rechaza_credenciales_y_cuentas_no_habilitadas(personal,problema,estado):
    h=personal;cambios={};cuenta=h.docente
    if problema=='clave':cambios['clave']='incorrecta-LAB'
    elif problema=='ausente':cambios['correo']='inexistente@universidad.test'
    elif problema=='correo_invalido':cambios['correo']='no-es-correo'
    elif problema=='estudiante':cuenta=h.estudiante
    else:
        with h.sesiones.begin() as s:
            if problema=='inactivo':s.get(U,h.docente[0]).activo=False
            elif problema=='hash_corrupto':s.get(U,h.docente[0]).clave_hash='MARCADOR_HASH_PRIVADO'
            else:s.add(U(id_rol=1,nombre='Duplicado LAB',correo=h.docente[1].upper(),clave_hash=h.hash))
    with observar_lectura() as operaciones:r=login(h,cuenta,**cambios)
    assert r.status_code==estado,r.text
    assert operaciones==[] and 'access_token' not in r.text
    for privado in (CLAVE_LAB,h.hash,'MARCADOR_HASH_PRIVADO',cuenta[1]):assert privado not in r.text
    if estado==401:assert r.json()['detail']=={'codigo':'NO_AUTENTICADO','mensaje':'Credenciales ausentes o inválidas.'}


@pytest.mark.parametrize('cambio',[{'clave':''},{'roles':['ADMINISTRADOR']},{'convocatoria_id':str(uuid4())}])
def test_login_personal_valida_solicitud_sin_aceptar_roles_del_cliente(personal,cambio):
    r=login(personal,**cambio)
    assert r.status_code==422 and 'access_token' not in r.text
    assert CLAVE_LAB not in r.text


@pytest.mark.parametrize('problema',['expirado','manipulado'])
def test_token_del_login_no_admite_expiracion_o_manipulacion(personal,problema):
    h=personal;token=login(h).json()['access_token']
    if problema=='manipulado':
        # Cambiar la firma, no confiar en claims alterados por el cliente.
        partes=token.split('.');partes[2]=('A' if partes[2][0]!='A' else 'B')+partes[2][1:];token='.'.join(partes)
    else:
        claims=jwt.decode(token,options={'verify_signature':False})
        claims['iat']-=1800;claims['nbf']=claims['iat'];claims['exp']-=1800
        emisor=construir_tokens();token=jwt.encode(claims,emisor._secreto,algorithm='HS256')
    assert h.cliente.get(BASE+'/me',headers={'Authorization':'Bearer '+token}).status_code==401


@pytest.mark.parametrize('cambio',['inactivo','rol'])
def test_estado_y_rol_persistidos_se_revalidan_despues_del_login(personal,cambio,payload_valido):
    h=personal;doc=headers(h)
    with h.sesiones.begin() as s:
        if cambio=='inactivo':s.get(U,h.docente[0]).activo=False
        else:s.get(U,h.docente[0]).id_rol=2
    assert h.cliente.post('/api/v1/cases',headers=doc,json=payload_valido).status_code==(401 if cambio=='inactivo' else 403)


def test_fallo_sql_del_login_no_emite_token_ni_expone_diagnostico(personal):
    h=personal;motor=get_engine()
    def fallo(_,__,statement,___,____,_____):
        if 'FROM usuario' in statement:raise OperationalError('SQL_PRIVADO',{},RuntimeError('MARCADOR_PRIVADO_LOGIN'))
    event.listen(motor,'before_cursor_execute',fallo)
    try:r=login(h)
    finally:event.remove(motor,'before_cursor_execute',fallo)
    assert r.status_code==503 and 'access_token' not in r.text
    assert 'SQL_PRIVADO' not in r.text and 'MARCADOR_PRIVADO_LOGIN' not in r.text


def test_login_personal_sin_clave_de_firma_configurada_falla_cerrado(personal,monkeypatch):
    monkeypatch.delenv('IDENTITY_JWT_SECRET');get_settings.cache_clear()
    r=login(personal)
    assert r.status_code==503 and 'access_token' not in r.text


def test_logins_concurrentes_no_escriben_ni_generan_identidades(personal):
    h=personal;barrera=Barrier(2,timeout=15)
    with h.sesiones() as s:antes=s.scalar(select(func.count()).select_from(V))
    def autenticar(_):barrera.wait();return login(h)
    with observar_lectura() as operaciones:
        with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(autenticar,range(2)))
    assert all(r.status_code==200 for r in rs) and operaciones==[]
    assert rs[0].json()['access_token']!=rs[1].json()['access_token']
    with h.sesiones() as s:assert s.scalar(select(func.count()).select_from(V))==antes
