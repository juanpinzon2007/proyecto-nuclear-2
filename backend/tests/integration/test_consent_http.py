"""HTTP aislado, login/JWT real y PG17 desechable. Documentos SOLO LAB.

Las fixtures son preparación administrativa sintética, no publicación oficial.
No se sustituye titularidad, matrícula, convocatoria, selector ni transacciones.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timezone
from hashlib import sha256
import secrets
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.modules.identity.api import dependencies as identity
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.api.consent import crear_router_consentimiento
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C, GrupoEstudianteORM as M
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy as Fuente
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel
from tests.integration.test_consent_version_persistence import publicar, elegir
from tests.integration.test_participation_provision import convocada, pg_grafo, filas, servicio, argumentos  # noqa: F401


def app_para(c, factory=None):
    app = FastAPI()
    tokens = TokensJWT(secrets.token_urlsafe(48), 'consentimiento-lab', 'consentimiento-lab')
    app.dependency_overrides[identity.obtener_fabrica_tokens] = lambda: lambda: tokens
    def usuarios():
        with c.sesiones() as s:
            yield lambda: RepositorioUsuariosSQLAlchemy(s)
    app.dependency_overrides[identity.obtener_fabrica_usuarios] = usuarios
    app.dependency_overrides[identity.obtener_fabrica_sesiones_login] = lambda: c.sesiones
    app.dependency_overrides[identity.obtener_dominios_login] = lambda: ('fixture.test',)
    app.include_router(identity_router)
    app.include_router(crear_router_consentimiento(crear_sesion=factory or c.sesiones,
        fechas=FechasPersistencia(timezone.utc), reloj=SimpleNamespace(ahora=lambda: c.ahora)))
    return app, tokens


@pytest.fixture
def http(convocada):
    c = convocada
    with c.sesiones.begin() as s:
        c.documento = publicar(c, s)
        elegir(c, s, c.documento)
        correo = s.get(UsuarioORM, c.alumno).correo
    app, c.tokens = app_para(c)
    with TestClient(app, raise_server_exceptions=False) as client:
        login = client.post('/api/v1/identity/auth/estudiantes', json={
            'correo': correo, 'codigo_convocatoria': c.codigo})
        assert login.status_code == 200  # No imprimir tokens ni códigos.
        c.headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
        c.url = (f'/api/v1/identity/convocatorias/{c.datos["convocatoria_id"]}'
            f'/asignaciones/{c.datos["id_asignacion"]}/consentimiento')
        c.client, c.app = client, app
        yield c


def body(c):
    with c.sesiones() as s:
        d = Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'], ahora=c.ahora)
    return dict(id_version_documento=d.id_version_documento, referencia=d.referencia,
                huella=d.huella, acepta=True)


def aceptaciones(c):
    with c.sesiones() as s:
        return s.scalars(select(C.id_consentimiento).where(C.id_estudiante==c.alumno,
            C.id_version_documento.is_not(None))).all()


def enviar(c, datos=None, **kw):
    return c.client.post(c.url+'/aceptacion', headers=c.headers, json=datos or body(c), **kw)


def test_login_documento_aceptacion_y_estado_privados_durables(http, record_property):
    c = http
    d = c.client.get(c.url, headers=c.headers)
    assert d.status_code==200
    assert d.json()['id_version_documento']==c.documento
    assert d.json()['huella']==sha256(d.json()['texto'].encode()).hexdigest()
    assert 'SINTETICO SOLO LAB' in d.json()['texto']
    estado = c.client.get(c.url+'/aceptacion', headers=c.headers)
    assert estado.status_code==200 and estado.json()['aceptado'] is False
    a = enviar(c)
    assert a.status_code==200 and a.json()['aceptado'] is True
    assert enviar(c).json()==a.json()  # Timestamp/PK originales, no otra aceptación.
    assert c.client.get(c.url+'/aceptacion', headers=c.headers).json()==a.json()
    with c.sesiones() as s:
        prueba=s.get(C,a.json()['id_consentimiento'])
        assert prueba.id_estudiante==c.alumno and prueba.id_version_documento==c.documento
        assert prueba.aceptacion_explicita and prueba.huella_aceptada==d.json()['huella']
    assert len(aceptaciones(c))==1 and filas(c)==([],[])
    for respuesta in (d,estado,a):
        assert respuesta.headers['Cache-Control']=='no-store'
        assert not any(k in respuesta.json() for k in ('id_estudiante','correo','autoridad_aprobadora','nota_final'))
    record_property('recorrido', 'login real 200; documento 200; no aceptado; aceptación 200; repetición mismo PK; nueva Session confirma; 0 P/I')


@pytest.mark.parametrize('operacion', ['documento','estado','aceptar'])
def test_sin_documento_seleccionado_cierra_sin_usar_borrador(http, operacion):
    c=http
    # Otra asignación del mismo laboratorio tiene matrícula/convocatoria reales,
    # pero ningún selector: no retirar ni degradar el documento inmutable anterior.
    from tests.integration.test_attempt_start import preparar_convocada
    otro=preparar_convocada(c.engine)
    app,_=app_para(otro)
    with otro.sesiones() as s:correo=s.get(UsuarioORM,otro.alumno).correo
    with TestClient(app,raise_server_exceptions=False) as client:
        login=client.post('/api/v1/identity/auth/estudiantes',json={'correo':correo,'codigo_convocatoria':otro.codigo})
        assert login.status_code==200
        headers={'Authorization':'Bearer '+login.json()['access_token']}
        url=f'/api/v1/identity/convocatorias/{otro.datos["convocatoria_id"]}/asignaciones/{otro.datos["id_asignacion"]}/consentimiento'
        r=(client.post(url+'/aceptacion',headers=headers,json=body(c)) if operacion=='aceptar'
           else client.get(url+('/aceptacion' if operacion=='estado' else ''),headers=headers))
        assert r.status_code==503 and r.headers['Cache-Control']=='no-store'
    assert aceptaciones(otro)==[] and filas(otro)==([],[])


def test_documento_reemplazado_requiere_nueva_aceptacion_preserva_anterior(http):
    c=http;datos=body(c);a=enviar(c,datos)
    assert a.status_code==200
    with c.sesiones.begin() as s:
        nuevo=publicar(c,s,'2');elegir(c,s,nuevo)
    assert enviar(c,datos).status_code==409
    estado=c.client.get(c.url+'/aceptacion',headers=c.headers)
    assert estado.status_code==200 and not estado.json()['aceptado']
    assert estado.json()['id_version_documento']==nuevo
    assert enviar(c).status_code==200 and len(aceptaciones(c))==2
    with c.sesiones() as s:assert s.get(C,a.json()['id_consentimiento']).id_version_documento==c.documento


@pytest.mark.parametrize('cambio,esperado', [({'acepta':False},403),({'acepta':'true'},422),
    ({'id_version_documento':2147483647},409),({'huella':'0'*64},409),
    ({'referencia':'otra'},409),({'id_estudiante':999},422)])
def test_aceptacion_no_implicita_ni_version_o_actor_arbitrarios(http,cambio,esperado):
    c=http;r=enviar(c,body(c)|cambio)
    assert r.status_code==esperado and aceptaciones(c)==[] and filas(c)==([],[])


@pytest.mark.parametrize('problema,esperado', [('ausente',401),('invalido',401),('docente',403),
    ('ajeno',403),('contexto',403),('retirada',403),('matricula',403),('sin_vinculo',403),('ambiguo',503),('inactivo',401)])
def test_autorizacion_http_real_revalida_fuentes(http,problema,esperado):
    c=http;headers=c.headers
    if problema=='ausente':headers={}
    elif problema=='invalido':headers={'Authorization':'Bearer invalido'}
    elif problema=='docente':headers={'Authorization':'Bearer '+c.tokens.emitir(str(c.docente))}
    elif problema=='contexto':headers={'Authorization':'Bearer '+c.tokens.emitir(str(c.alumno),str(uuid4()))}
    elif problema=='ajeno':
        from tests.integration.test_participation_persistence import contexto
        otro=contexto(c.engine)
        headers={'Authorization':'Bearer '+c.tokens.emitir(str(otro.alumno),str(c.datos['convocatoria_id']))}
    else:
        with c.sesiones.begin() as s:
            if problema=='retirada':s.get(ConvocatoriaModel,c.datos['convocatoria_id']).estado='RETIRADA'
            elif problema=='matricula':s.get(M,c.datos['id_grupo_estudiante']).activo=False
            elif problema=='inactivo':s.get(UsuarioORM,c.alumno).activo=False
            elif problema=='sin_vinculo':s.delete(s.get(IdentidadAcademicaORM,('SCHEDULING',c.uuid)))
            elif problema=='ambiguo':s.add(IdentidadAcademicaORM(sistema='SCHEDULING',id_academico=uuid4(),id_usuario=c.alumno))
    r=c.client.post(c.url+'/aceptacion',headers=headers,json=body(c))
    assert r.status_code==esperado and aceptaciones(c)==[] and filas(c)==([],[])
    assert c.client.get(c.url,headers=headers).status_code==esperado


def test_get_sin_dml_flush_ni_commit(http):
    c=http;assert enviar(c).status_code==200
    vistos=[]
    def sql(conn,cursor,statement,*args):
        if statement.lstrip().split()[0].lower() in {'insert','update','delete','merge','truncate','create','alter','drop'}:vistos.append(statement)
    def flush(*args):vistos.append('flush')
    def commit(*args):vistos.append('commit')
    event.listen(c.engine,'before_cursor_execute',sql)
    event.listen(Session,'before_flush',flush);event.listen(Session,'after_commit',commit)
    try:
        for _ in range(2):
            assert c.client.get(c.url,headers=c.headers).status_code==200
            assert c.client.get(c.url+'/aceptacion',headers=c.headers).status_code==200
    finally:
        event.remove(c.engine,'before_cursor_execute',sql)
        event.remove(Session,'before_flush',flush);event.remove(Session,'after_commit',commit)
    assert vistos==[] and len(aceptaciones(c))==1 and filas(c)==([],[])


def test_aceptacion_http_concurrente_mismo_id(http):
    c=http;datos=body(c);b=Barrier(2)
    def operar(_):
        b.wait(timeout=10)
        with TestClient(c.app,raise_server_exceptions=False) as client:
            return client.post(c.url+'/aceptacion',headers=c.headers,json=datos)
    with ThreadPoolExecutor(2) as pool:res=list(pool.map(operar,range(2)))
    assert [r.status_code for r in res]==[200,200]
    assert res[0].json()==res[1].json() and len(aceptaciones(c))==1 and filas(c)==([],[])


def test_fallo_al_commit_revierte_aceptacion_y_permita_reintento(http):
    c=http
    class SesionFallo(Session):pass
    def fallar(s):raise SQLAlchemyError('Fallo LAB antes de confirmar')
    event.listen(SesionFallo,'before_commit',fallar)
    factory=sessionmaker(bind=c.engine,class_=SesionFallo)
    app,tokens=app_para(c,factory)
    headers={'Authorization':'Bearer '+tokens.emitir(str(c.alumno),str(c.datos['convocatoria_id']))}
    try:
        with TestClient(app,raise_server_exceptions=False) as client:
            assert client.post(c.url+'/aceptacion',headers=headers,json=body(c)).status_code==503
    finally:event.remove(SesionFallo,'before_commit',fallar)
    assert aceptaciones(c)==[] and filas(c)==([],[])
    assert enviar(c).status_code==200 and len(aceptaciones(c))==1


def test_sin_revocacion_http_y_guard_activo_conservado(http):
    c=http;a=enviar(c);assert a.status_code==200
    from tests.integration.test_attempt_start import InicioLaboratorio
    pk=a.json()['id_consentimiento']
    servicio(c,crear_fuente_consentimiento=Fuente,politica_inicio=InicioLaboratorio(body(c)['referencia']))\
        .iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=pk)
    assert c.client.delete(c.url+'/aceptacion',headers=c.headers).status_code==405
    with pytest.raises(IntegrityError),c.sesiones.begin() as s:s.get(C,pk).fecha_revocacion=c.ahora.replace(tzinfo=None)
    assert enviar(c).json()['id_consentimiento']==pk


def test_main_registra_composicion_condicionada_sin_provision_independiente():
    from app.main import app
    rutas=set(app.openapi()['paths'])
    assert any('/consentimiento' in p for p in rutas)
    assert '/api/v1/convocatorias/{convocatoria_id}/intentos' in rutas
    assert '/api/v1/convocatorias/{convocatoria_id}/participacion' not in rutas
