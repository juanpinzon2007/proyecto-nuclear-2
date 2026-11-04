"""RF-18: JWT/propiedad reales; no se fabrica autorización de espacio."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, func, delete, event
from sqlalchemy.exc import OperationalError

from app.modules.cases.api.router import router as cases_router
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, DocenteEspacioAcademicoModel as Grant
from app.modules.scheduling.api.dependencies import obtener_autorizacion_espacios_programacion
from tests.integration.test_cases_graph_authoring import (
    autor, pg_autoria, payload_valido, crear, configurar,
)  # noqa: F401


@pytest.fixture
def programacion(autor):
    a=autor
    app=FastAPI()
    app.dependency_overrides.update(a.client.app.dependency_overrides)
    app.include_router(cases_router);app.include_router(scheduling_router)
    with a.sesiones.begin() as s:
        propio=uuid4()
        cases=s.scalar(select(IA.id_academico).where(IA.id_usuario==a.propio,IA.sistema=='CASES'))
        assert cases!=propio
        s.add_all([IA(id_usuario=a.propio,sistema='SCHEDULING',id_academico=propio),
            IA(id_usuario=a.propio+1,sistema='SCHEDULING',id_academico=uuid4())])
    with TestClient(app,raise_server_exceptions=False) as client:
        actor=SimpleNamespace(**(vars(a)|dict(client=client)))
        vid,g,_=crear(actor);assert configurar(actor,vid,g).status_code==200
        assert client.post(f'/api/v1/cases/{vid}/publish',headers=a.headers).status_code==200
        espacio=client.post('/scheduling/espacios',headers=a.headers,json={'nombre':'Espacio RF-18 LAB'})
        assert espacio.status_code==201
        inicio=datetime(2030,1,1,12,tzinfo=timezone.utc)
        body=dict(espacio_academico_id=espacio.json()['id'],version_caso_id=vid,
            fecha_inicio=inicio.isoformat(),fecha_fin=(inicio+timedelta(hours=1)).isoformat(),
            tiempo_maximo_minutos=30,lugar='Laboratorio RF-18',mensaje_personalizado='Mensaje RF-18 LAB')
        yield SimpleNamespace(a=actor,client=client,sesiones=a.sesiones,body=body,version=UUID(vid),uuid_docente=propio)


def cantidad(h):
    with h.sesiones() as s:
        return s.scalar(select(func.count()).select_from(S).where(
            S.espacio_academico_id==UUID(h.body['espacio_academico_id'])))


def conceder(h,usuario=None):
    # Alta explícita de datos sintéticos; no se expone un servicio de concesión.
    with h.sesiones.begin() as s:
        s.add(Grant(id_docente=h.a.propio if usuario is None else usuario,
            espacio_academico_id=UUID(h.body['espacio_academico_id'])))


def solicitar(h,body=None,headers=None):
    return h.client.post('/scheduling/sesiones',headers=h.a.headers if headers is None else headers,
        json=h.body if body is None else body)


@pytest.mark.parametrize('lugar',[None,'Laboratorio RF-18'])
def test_programacion_autorizada_persiste_datos_y_uuid_de_scheduling(programacion,lugar):
    h=programacion;conceder(h);b=h.body|{'lugar':lugar}
    r=solicitar(h,b);assert r.status_code==201,r.text
    d=r.json();assert d['version_caso_id']==str(h.version)
    assert d['docente_id']==str(h.uuid_docente) and d['estado']=='SIN_INICIAR'
    with h.sesiones() as s:
        fila=s.get(S,UUID(d['id']))
        assert fila.version_caso_id==h.version and fila.docente_id==h.uuid_docente
        assert fila.lugar==lugar and fila.mensaje_personalizado==h.body['mensaje_personalizado']
        assert fila.tiempo_maximo_minutos==30


def test_sin_autorizacion_de_espacio_no_hay_programacion_implicita(programacion):
    h=programacion
    # Ni crear el espacio ni asignarlo a otro docente concede su uso al creador.
    conceder(h,h.a.propio+1)
    r=h.client.post('/scheduling/sesiones',headers=h.a.headers,json=h.body)
    assert r.status_code==403,r.text
    assert cantidad(h)==0


@pytest.mark.parametrize('actor',['anonimo','estudiante','docente_ajeno'])
def test_identidad_y_propiedad_de_caso_no_conceden_acceso_por_uuid_de_otro_modulo(programacion,actor):
    h=programacion
    if actor!='anonimo':conceder(h,h.a.propio+1 if actor=='docente_ajeno' else h.a.propio+2)
    headers={'anonimo':{},'estudiante':h.a.estudiante,'docente_ajeno':h.a.ajeno}[actor]
    r=h.client.post('/scheduling/sesiones',headers=headers,json=h.body)
    assert r.status_code==(401 if actor=='anonimo' else 403),r.text
    assert cantidad(h)==0


@pytest.mark.parametrize('campo',['fecha_fin','fecha_sin_zona','tiempo_cero','tiempo_supera_caso','mismo_instante_otra_zona','lugar_excesivo'])
def test_solicitud_temporal_invalida_no_llega_a_crear_sesion(programacion,campo):
    h=programacion;conceder(h);b=h.body.copy()
    if campo=='fecha_fin':b['fecha_fin']=b['fecha_inicio']
    elif campo=='fecha_sin_zona':b['fecha_inicio']='2030-01-01T12:00:00'
    elif campo=='tiempo_cero':b['tiempo_maximo_minutos']=0
    elif campo=='tiempo_supera_caso':b['tiempo_maximo_minutos']=h.a.payload['case']['tiempoEstimadoMin']+1
    elif campo=='lugar_excesivo':b['lugar']='a'*256
    else:
        b['fecha_inicio']='2030-01-01T12:00:00-05:00';b['fecha_fin']='2030-01-01T17:00:00+00:00'
    r=h.client.post('/scheduling/sesiones',headers=h.a.headers,json=b)
    assert r.status_code==422,r.text
    assert cantidad(h)==0


@pytest.mark.parametrize('estado',['BORRADOR','ARCHIVADO','INEXISTENTE'])
def test_solo_se_programa_version_publicada_disponible(programacion,estado):
    h=programacion;conceder(h);b=h.body.copy()
    if estado=='BORRADOR':
        vid,_,_=crear(h.a);b['version_caso_id']=vid
    elif estado=='ARCHIVADO':
        assert h.client.post(f'/api/v1/cases/{h.version}/archive',headers=h.a.headers).status_code==200
    else:b['version_caso_id']=str(uuid4())
    r=solicitar(h,b);assert r.status_code==422,r.text
    assert cantidad(h)==0


def test_autorizador_ausente_falla_cerrado_sin_proveedor_de_laboratorio(programacion):
    h=programacion;conceder(h)
    h.client.app.dependency_overrides[obtener_autorizacion_espacios_programacion]=lambda:None
    assert solicitar(h).status_code==503
    assert cantidad(h)==0


def test_fallo_despues_del_insert_revierte_sesion_y_conserva_permiso(programacion):
    h=programacion;conceder(h);engine=h.sesiones.kw['bind']
    def fallar(conn,cursor,sql,params,context,executemany):
        if sql.startswith('INSERT INTO sesion_programada'):
            raise OperationalError('INSERT',{},Exception('fallo de laboratorio'))
    event.listen(engine,'after_cursor_execute',fallar)
    try:assert solicitar(h).status_code==503
    finally:event.remove(engine,'after_cursor_execute',fallar)
    assert cantidad(h)==0
    with h.sesiones() as s:assert s.get(Grant,(h.a.propio,UUID(h.body['espacio_academico_id']))) is not None
    assert solicitar(h).status_code==201


def test_revocacion_concurrente_impide_programar_y_no_borra_sesion_historica(programacion):
    h=programacion;conceder(h)
    anterior=solicitar(h);assert anterior.status_code==201
    llego=Event();engine=h.sesiones.kw['bind']
    def observar(conn,cursor,sql,params,context,executemany):
        if 'docente_espacio_academico' in sql and 'FOR SHARE' in sql:llego.set()
    event.listen(engine,'before_cursor_execute',observar)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with h.sesiones() as s:
                s.execute(delete(Grant).where(Grant.id_docente==h.a.propio))
                futuro=pool.submit(solicitar,h)
                try:
                    assert llego.wait(timeout=10)
                    s.commit()
                    assert futuro.result(timeout=15).status_code==403
                finally:s.rollback()
    finally:event.remove(engine,'before_cursor_execute',observar)
    assert cantidad(h)==1
    assert h.client.get('/scheduling/sesiones/'+anterior.json()['id'],headers=h.a.headers).status_code==200


def test_publicacion_posterior_no_sustituye_uuid_de_version_programada(programacion):
    # Preparación de una edición 2 con los modelos/mapeador existentes. No hay
    # endpoint de nueva edición; no se presenta esta preparación como tal.
    from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
    from app.modules.cases.infrastructure.models import VersionCasoModel,CasoModel
    from tests.integration.test_cases_history import nuevo
    h=programacion;conceder(h)
    primera=solicitar(h);assert primera.status_code==201
    with h.sesiones() as s:
        vieja=s.get(VersionCasoModel,h.version)
        caso=s.get(CasoModel,vieja.caso_id)
        v=nuevo();v.caso_id=caso.id;v.numero=2;v.docente_creador_id=caso.docente_creador_id
        contenedor=CasoRepository(s)._mapear(v)
        nueva=contenedor.versiones.pop()
        caso.versiones.append(nueva)
        s.commit()
    detalle=h.client.get(f'/api/v1/cases/{v.id}',headers=h.a.headers).json()
    e=detalle['escenarios'][0]
    grafo={'escenario_inicial_id':e['id'],'transiciones':[
        {'opcion_id':o['id'],'tipo':'FIN','destino_id':None} for o in e['preguntas'][0]['opciones']]}
    assert configurar(h.a,str(v.id),grafo).status_code==200
    assert h.client.post(f'/api/v1/cases/{v.id}/publish',headers=h.a.headers).status_code==200
    segunda=solicitar(h);assert segunda.status_code==201
    assert segunda.json()['version_caso_id']==str(h.version)
    assert h.client.post(f'/api/v1/cases/{h.version}/archive',headers=h.a.headers).status_code==200
    with h.sesiones() as s:
        assert s.get(S,UUID(primera.json()['id'])).version_caso_id==h.version
        assert s.get(S,UUID(segunda.json()['id'])).version_caso_id==h.version
