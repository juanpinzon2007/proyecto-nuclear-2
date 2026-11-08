"""Admisión main + consentimiento SQL/HTTP + inicio en app aislada, PG17 propio.

Documentos y políticas de inicio/provisión son SOLO LAB. Autenticación, ámbitos,
concesión causal, fuente/aceptación, UoW, grafo y repositorios son los reales.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timezone
from threading import Barrier, Event
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select, func, text

from app.modules.identity.api.consent import crear_router_consentimiento
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy as Fuente
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C, GrupoEstudianteORM as M
from app.modules.participation.api.provision_router import crear_router_inicio_8b
from app.modules.participation.api.router import router as attempts_router
from app.modules.participation.api.dependencies import obtener_facade, crear_dependencia_facade_8b
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.integration.test_consent_version_persistence import publicar, elegir
from tests.integration.test_participation_provision import VinculacionLaboratorio
from tests.integration.test_attempt_start import InicioLaboratorio
from tests.integration.test_main_early_ingress import ingreso_main, habilitar
from tests.integration.test_participation_http_composition import integracion, autor, pg_autoria, payload_valido, cantidades  # noqa: F401


@pytest.fixture
def preparada(ingreso_main):
    h=ingreso_main;h.engine=h.sesiones.kw['bind']
    h.reloj_inicio=SimpleNamespace(ahora=lambda:h.instante)
    h.doc_contexto=SimpleNamespace(datos={'id_asignacion':h.asignacion},docente=h.a.propio,ahora=h.instante)
    with h.sesiones.begin() as s:
        h.documento=publicar(h.doc_contexto,s);elegir(h.doc_contexto,s,h.documento)
        d=Fuente(s).vigente(id_asignacion=h.asignacion,ahora=h.instante)
    h.referencia=d.referencia
    app=FastAPI();app.dependency_overrides.update(h.client.app.dependency_overrides)
    app.dependency_overrides[obtener_facade]=crear_dependencia_facade_8b(crear_sesion=h.sesiones,
        fechas=FechasPersistencia(timezone.utc),reloj=h.reloj_inicio,matricula_activa=True)
    app.include_router(identity_router)
    app.include_router(attempts_router)
    app.include_router(crear_router_consentimiento(crear_sesion=h.sesiones,
        fechas=FechasPersistencia(timezone.utc),reloj=h.reloj_inicio))
    app.include_router(crear_router_inicio_8b(crear_sesion=h.sesiones,
        fechas=FechasPersistencia(timezone.utc),reloj=h.reloj_inicio,
        politica_ingreso=PoliticaIngresoNoConfigurada(),politica_inicio=InicioLaboratorio(d.referencia),
        politica_vinculacion=VinculacionLaboratorio(),crear_fuente_consentimiento=Fuente))
    h.url_consentimiento=(f'/api/v1/identity/convocatorias/{h.convocatoria}'
        f'/asignaciones/{h.asignacion}/consentimiento')
    h.aceptar_body=dict(id_version_documento=d.id_version_documento,referencia=d.referencia,huella=d.huella,acepta=True)
    h.aplicacion=app
    with TestClient(app,raise_server_exceptions=False) as cliente:
        h.flujo=cliente
        # Otro login real, no override de identidad ni token fabricado por el test.
        login=cliente.post('/api/v1/identity/auth/estudiantes',json={
            'correo':f'autor{h.estudiante}@universidad.test','codigo_convocatoria':h.codigo})
        assert login.status_code==200
        h.headers={'Authorization':'Bearer '+login.json()['access_token']}
        yield h


def aceptar(h):
    r=h.flujo.post(h.url_consentimiento+'/aceptacion',headers=h.headers,json=h.aceptar_body)
    assert r.status_code==200
    h.explicito=r.json()['id_consentimiento']
    return h.explicito


def admitir(h):
    r=h.main.post(f'/scheduling/convocatorias/{h.convocatoria}/espera',headers=h.main_headers,
        json={'codigo_acceso':h.codigo})
    assert r.status_code==201
    habilitar(h)
    with h.sesiones() as s:
        c=s.get(ConvocatoriaModel,h.convocatoria)
        assert c.admision_evento_id is not None and c.espera_version_caso_id==h.version


def iniciar(h,**cambios):
    return h.flujo.post(h.base+'/intentos',headers=h.headers,
        json=h.body|{'id_consentimiento':getattr(h,'explicito',h.consentimiento)}|cambios)


@contextmanager
def escrituras(h):
    sql=[]
    def observar(conn,cursor,statement,*args):
        inicio=statement.lstrip().lower()
        if inicio.startswith(('insert into participacion','insert into intento')):sql.append(inicio.split('(')[0])
    event.listen(h.engine,'before_cursor_execute',observar)
    try:yield sql
    finally:event.remove(h.engine,'before_cursor_execute',observar)


def test_recorrido_admitido_consentimiento_inicio_y_cierre_atomico(preparada,record_property):
    h=preparada;aceptar(h);assert cantidades(h)==([],[])
    admitir(h)
    with escrituras(h) as sql:r=iniciar(h)
    assert r.status_code==201
    assert len(sql)==2
    pk,ik=r.json()['id_participacion'],r.json()['id_intento']
    with h.sesiones() as s:
        assert s.get(P,pk).id_consentimiento==s.get(I,ik).id_consentimiento==h.explicito
        assert s.get(C,h.explicito).id_version_documento==h.documento
        assert s.get(SesionProgramadaModel,h.sesion).version_caso_id==h.version
    # Reutilizar P es idempotente; repetir inicio continúa devolviendo 409.
    p=h.flujo.post(h.base+'/participacion',headers=h.headers,json=h.body)
    assert p.status_code==200 and p.json()['id_participacion']==pk
    assert iniciar(h).status_code==409 and tuple(map(len,cantidades(h)))==(1,1)
    base=f'/api/v1/attempts/{ik}'
    for escena in h.escenas[:2]:
        q=escena['preguntas'][0];url=base+f'/decisions/{q["id"]}'
        assert h.flujo.post(url,headers=h.headers,json={'id_opcion':q['opciones'][0]['id']}).status_code==201
        assert h.flujo.put(url,headers=h.headers,json={'id_opcion':q['opciones'][1]['id']}).status_code==409
    progreso=h.flujo.get(base+'/progress',headers=h.headers)
    assert progreso.status_code==200 and progreso.json()['respondidas']==2
    assert not any(x in progreso.text for x in ('nota_final','es_correcta','justificacion','puntaje'))
    assert h.flujo.post(base+'/finish',headers=h.headers).json()['estado']=='FINALIZADO'
    assert h.flujo.post(base+'/finish',headers=h.headers).status_code==200
    with h.sesiones() as s:
        assert s.get(I,ik).estado=='FINALIZADO'
        assert s.scalar(select(func.count()).select_from(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento==ik))==0
    record_property('recorrido','login SQL/JWT; aceptación HTTP; espera; habilitación/concesión; inicio 201; repetición 409; respuesta 201/PUT409; progreso privado; cierre idempotente; 0 resultados')


@pytest.mark.parametrize('problema',['no_admitido','retirada','matricula','consentimiento_ausente','version_anterior','consentimiento_ajeno'])
def test_rechazo_antes_del_insert_incluso_tras_consulta_anterior(preparada,problema):
    h=preparada
    if problema!='consentimiento_ausente':aceptar(h)
    if problema=='no_admitido':habilitar(h)
    else:admitir(h)
    if problema=='retirada':
        assert h.main.get(f'/scheduling/convocatorias/{h.convocatoria}/admision',headers=h.main_headers).json()['admitida']
        with h.sesiones.begin() as s:s.get(ConvocatoriaModel,h.convocatoria).estado='RETIRADA'
    elif problema=='matricula':
        with h.sesiones.begin() as s:s.get(M,h.matricula).activo=False
    elif problema=='version_anterior':
        with h.sesiones.begin() as s:elegir(h.doc_contexto,s,publicar(h.doc_contexto,s,'2'))
    elif problema=='consentimiento_ajeno':
        from tests.integration.test_participation_persistence import contexto
        h.explicito=contexto(h.engine).consentimiento
    with escrituras(h) as sql:r=iniciar(h)
    assert r.status_code==403 and sql==[] and cantidades(h)==([],[])


def test_inicios_http_simultaneos_un_solo_intento(preparada):
    h=preparada;aceptar(h);admitir(h);barrera=Barrier(2)
    def comenzar(_):
        barrera.wait(timeout=10)
        with TestClient(h.aplicacion,raise_server_exceptions=False) as client:
            return client.post(h.base+'/intentos',headers=h.headers,
                json=h.body|{'id_consentimiento':h.explicito}).status_code
    with ThreadPoolExecutor(2) as pool:estados=list(pool.map(comenzar,range(2)))
    assert sorted(estados)==[201,409] and tuple(map(len,cantidades(h)))==(1,1)


def test_participacion_preexistente_no_elude_admision_al_iniciar_directamente(preparada):
    from dataclasses import replace
    from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
    from app.modules.participation.infrastructure.start import crear_facade_inicio_8b
    from app.modules.participation.application.errors import AccesoDenegado
    h=preparada;aceptar(h);habilitar(h)  # No hubo espera ni concesión.
    # Preparación administrativa negativa: representa una P histórica existente,
    # no una creación autorizada por la API actual. Nunca sembrar un intento.
    with h.sesiones.begin() as s:
        p=P(id_asignacion=h.asignacion,id_grupo_estudiante=h.matricula,
            convocatoria_id=h.convocatoria,id_consentimiento=h.explicito,
            estado='pendiente',fecha_registro=h.instante.replace(tzinfo=None))
        s.add(p);s.flush();pk=p.id_participacion
        usuario=replace(RepositorioUsuariosSQLAlchemy(s).obtener(str(h.estudiante)),id_convocatoria=str(h.convocatoria))
    facade=crear_facade_inicio_8b(usuario=usuario,id_participacion=pk,reloj=h.reloj_inicio,
        fechas=FechasPersistencia(timezone.utc),crear_sesion=h.sesiones,codigo_acceso=h.codigo,
        politica_ingreso=PoliticaIngresoNoConfigurada(),politica_inicio=InicioLaboratorio(h.referencia))
    with escrituras(h) as sql,pytest.raises(AccesoDenegado):
        facade.iniciar_intento(id_estudiante=h.estudiante,id_participacion=pk,id_consentimiento=h.explicito)
    assert sql==[] and tuple(map(len,cantidades(h)))==(1,0)


def test_rollback_tras_insert_intento_no_deja_participacion(preparada):
    h=preparada;aceptar(h);admitir(h)
    def fallar(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith('insert into intento'):raise RuntimeError('Fallo intermedio SOLO LAB')
    event.listen(h.engine,'after_cursor_execute',fallar)
    try:assert iniciar(h).status_code==500
    finally:event.remove(h.engine,'after_cursor_execute',fallar)
    assert cantidades(h)==([],[])
    with h.sesiones() as s:assert s.get(C,h.explicito).id_version_documento==h.documento
    assert iniciar(h).status_code==201


def test_cambio_documental_concurrente_no_reescribe_vinculo(preparada):
    h=preparada;aceptar(h);admitir(h)
    with h.sesiones.begin() as s:nuevo=publicar(h.doc_contexto,s,'2')
    detenido,liberar,publicando=Event(),Event(),Event();pid=[]
    def parar(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith('insert into participacion'):
            detenido.set();assert liberar.wait(15)
    def seleccionar():
        with h.sesiones.begin() as s:
            pid.append(s.scalar(text('SELECT pg_backend_pid()')));publicando.set()
            elegir(h.doc_contexto,s,nuevo)
    event.listen(h.engine,'before_cursor_execute',parar)
    try:
        with ThreadPoolExecutor(2) as pool:
            inicio=pool.submit(iniciar,h)
            assert detenido.wait(15)
            cambio=pool.submit(seleccionar);assert publicando.wait(5)
            try:
                limite=time.monotonic()+5;bloqueado=False
                while time.monotonic()<limite:
                    with h.engine.connect() as s:
                        bloqueado=s.scalar(text('SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid'),{'pid':pid[0]})=='Lock'
                    if bloqueado:break
                    time.sleep(.02)
                assert bloqueado and not cambio.done()
            finally:liberar.set()
            r=inicio.result(timeout=15);cambio.result(timeout=15)
    finally:
        liberar.set();event.remove(h.engine,'before_cursor_execute',parar)
    assert r.status_code==201
    with h.sesiones() as s:
        assert s.get(P,r.json()['id_participacion']).id_consentimiento==h.explicito
        assert s.get(C,h.explicito).id_version_documento==h.documento
        assert Fuente(s).vigente(id_asignacion=h.asignacion,ahora=h.instante).id_version_documento==nuevo
