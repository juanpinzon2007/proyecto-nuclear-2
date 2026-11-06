"""Recorrido integral LAB: main real + composición privada, sin overrides de auth.

Solo PG17 desechable. Bootstrap administrativo, asociaciones académicas y
documento sintético son preparación de laboratorio, no publicación institucional.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import secrets
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select, func, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM, RolPermisoORM
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.application.academic_identity import VinculoAcademico, SistemaAcademico
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM, ConsentimientoORM
from app.modules.identity.api.consent import crear_router_consentimiento
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy as Fuente
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.participation.api.dependencies import obtener_reloj_escenario
from app.modules.participation.api.provision_router import crear_router_inicio_8b
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.scheduling.api.router import obtener_reloj_ingreso
from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada
from app.modules.scheduling.infrastructure.models import DocenteEspacioAcademicoModel, ConvocatoriaModel, EventoAuditoriaModel
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from tests.integration.test_cases_graph_authoring import pg_autoria, payload_valido  # noqa: F401
from tests.integration.test_consent_version_persistence import publicar, elegir
from tests.integration.test_participation_provision import VinculacionLaboratorio
from tests.integration.test_attempt_start import InicioLaboratorio
from tests.integration.test_admitted_start import escrituras


@pytest.fixture
def recorrido_lab(pg_autoria, payload_valido, monkeypatch, record_property):
    from app.main import app
    sesiones=pg_autoria;engine=sesiones.kw['bind'];url=engine.url
    ahora=datetime.now(timezone.utc);reloj=SimpleNamespace(ahora=lambda:ahora)
    prefijo=uuid4().hex;clave_admin=secrets.token_urlsafe(24);clave_docente=secrets.token_urlsafe(24)
    correo_admin=f'admin-{prefijo}@universidad.test';correo_docente=f'docente-{prefijo}@universidad.test'
    with sesiones.begin() as s:
        if s.get(RolORM,3) is None:s.add(RolORM(id_rol=3,nombre='ADMINISTRADOR'));s.flush()
        if s.get(RolPermisoORM,(1,1)) is None:s.add(RolPermisoORM(id_rol=1,id_permiso=1))
        admin=U(id_rol=3,nombre='Administrador LAB',correo=correo_admin,clave_hash=obtener_hasheador().hash(clave_admin))
        s.add(admin);s.flush();admin_id=admin.id_usuario
        assert admin.clave_hash!=clave_admin and obtener_hasheador().verify(clave_admin,admin.clave_hash)
    # Única configuración de BD: URL entregada por el fixture Docker propio.
    for k,v in dict(POSTGRES_HOST=url.host,POSTGRES_PORT=str(url.port),POSTGRES_DB=url.database,
        POSTGRES_USER=url.username,POSTGRES_PASSWORD=url.password,IDENTITY_JWT_SECRET=secrets.token_urlsafe(48),
        IDENTITY_JWT_ISSUER='recorrido-integral-lab',IDENTITY_JWT_AUDIENCE='recorrido-integral-lab',
        IDENTITY_INSTITUTIONAL_DOMAINS='["universidad.test"]',PARTICIPATION_TIMESTAMP_ZONE='UTC').items():monkeypatch.setenv(k,v)
    get_settings.cache_clear();get_session_factory.cache_clear();get_engine.cache_clear()
    anteriores=dict(app.dependency_overrides);app.dependency_overrides.clear()
    app.dependency_overrides[obtener_reloj_ingreso]=lambda:reloj
    app.dependency_overrides[obtener_reloj_escenario]=lambda:reloj
    pasos=[]
    def paso(client,superficie,nombre,metodo,ruta,esperado,**kwargs):
        respuesta=client.request(metodo,ruta,**kwargs)
        pasos.append(dict(paso=nombre,superficie=superficie,metodo=metodo,ruta=ruta,
            esperado=esperado,observado=respuesta.status_code))
        record_property('pasos_http',json.dumps(pasos,ensure_ascii=False))
        assert respuesta.status_code==esperado,f'{nombre}: HTTP {respuesta.status_code}, esperado {esperado}'
        return respuesta
    try:
        with TestClient(app,raise_server_exceptions=False) as main:
            def principal(nombre,metodo,ruta,esperado,**kw):return paso(main,'app.main',nombre,metodo,ruta,esperado,**kw)
            a=principal('login administrador','POST','/api/v1/identity/auth/personal',200,
                json={'correo':correo_admin,'clave':clave_admin})
            admin_headers={'Authorization':'Bearer '+a.json()['access_token']}
            creado=principal('alta docente autorizada','POST','/api/v1/identity/docentes',201,headers=admin_headers,
                json={'correo':correo_docente,'nombre':'Docente LAB','clave':clave_docente,
                      'roles':['DOCENTE'],'permisos':['CREAR_CASOS']})
            docente_id=int(creado.json()['id_usuario'])
            d=principal('login docente','POST','/api/v1/identity/auth/personal',200,
                json={'correo':correo_docente,'clave':clave_docente})
            docente_headers={'Authorization':'Bearer '+d.json()['access_token']}
            # Sin APIs de autovinculación: asociaciones nuevas y verificadas SOLO
            # como preparación administrativa, nunca conversión INTEGER→UUID.
            alumnos=[]
            with sesiones.begin() as s:
                vinculos=RepositorioIdentidadAcademicaSQLAlchemy(s)
                for sistema in (SistemaAcademico.CASES,SistemaAcademico.SCHEDULING):
                    vinculos.agregar_verificado(VinculoAcademico(str(docente_id),sistema,uuid4()))
                grupo=GrupoAcademicoORM(id_profesor=docente_id,nombre='Grupo integral LAB',periodo='LAB')
                s.add(grupo);s.flush();gid=grupo.id_grupo
                for n in (1,2):
                    u=U(id_rol=2,nombre=f'Estudiante LAB {n}',correo=f'estudiante{n}-{prefijo}@universidad.test',
                        clave_hash=obtener_hasheador().hash(secrets.token_urlsafe(24)))
                    s.add(u);s.flush();acad=uuid4()
                    vinculos.agregar_verificado(VinculoAcademico(str(u.id_usuario),SistemaAcademico.SCHEDULING,acad))
                    m=GrupoEstudianteORM(id_grupo=gid,id_estudiante=u.id_usuario,fecha_ingreso=ahora.replace(tzinfo=None))
                    s.add(m);s.flush();alumnos.append(SimpleNamespace(id=u.id_usuario,correo=u.correo,uuid=acad,matricula=m.id_grupo_estudiante))
            payload=deepcopy(payload_valido)
            for n in (2,3):
                escena=deepcopy(payload['scenarios'][0]);escena['orden']=n;payload['scenarios'].append(escena)
            caso=principal('crear caso por API','POST','/api/v1/cases',201,headers=docente_headers,json=payload)
            vid=caso.json()['version_id']
            detalle=principal('leer edición propia','GET',f'/api/v1/cases/{vid}',200,headers=docente_headers).json()
            escenas=sorted(detalle['escenarios'],key=lambda e:e['orden'])
            opciones=[sorted(e['preguntas'][0]['opciones'],key=lambda o:o['orden']) for e in escenas]
            grafo={'escenario_inicial_id':escenas[0]['id'],'transiciones':[
                {'opcion_id':o['id'],'tipo':'ESCENA','destino_id':escenas[i+1]['id']} for i,o in enumerate(opciones[0])]+[
                {'opcion_id':o['id'],'tipo':'FIN'} for alternativas in opciones[1:] for o in alternativas]}
            principal('configurar grafo','PUT',f'/api/v1/cases/{vid}/graph',200,headers=docente_headers,json=grafo)
            principal('publicar edición','POST',f'/api/v1/cases/{vid}/publish',200,headers=docente_headers)
            espacio=principal('crear espacio','POST','/scheduling/espacios',201,headers=docente_headers,json={'nombre':'Espacio LAB'}).json()['id']
            with sesiones.begin() as s:s.add(DocenteEspacioAcademicoModel(id_docente=docente_id,espacio_academico_id=UUID(espacio)))
            inicio=ahora-timedelta(minutes=5);fin=ahora+timedelta(hours=1)
            sesion=principal('programar sesión','POST','/scheduling/sesiones',201,headers=docente_headers,
                json={'espacio_academico_id':espacio,'version_caso_id':vid,'fecha_inicio':inicio.isoformat(),
                      'fecha_fin':fin.isoformat(),'tiempo_maximo_minutos':30}).json()['id']
            with sesiones.begin() as s:
                familia=s.scalar(select(CasoModel).join(VersionCasoModel,VersionCasoModel.caso_id==CasoModel.id).where(VersionCasoModel.id==UUID(vid)))
                asignacion=AsignacionCasoModel(id_grupo=gid,id_caso=familia.id_caso,sesion_programada_id=UUID(sesion),
                    version_caso_id=UUID(vid),apertura=inicio.replace(tzinfo=None),cierre=fin.replace(tzinfo=None),
                    fecha_limite_ingreso=fin.replace(tzinfo=None),tiempo_maximo_min=30)
                s.add(asignacion);s.flush();aid=asignacion.id_asignacion
            for alumno in alumnos:
                convocatoria=principal('convocatoria individual','POST',f'/scheduling/sesiones/{sesion}/convocatorias',201,
                    headers=docente_headers,json={'estudiante_id':str(alumno.uuid)}).json()
                alumno.convocatoria=convocatoria['convocatoria_id'];alumno.codigo=convocatoria['codigo_acceso']
                login=principal('login estudiante','POST','/api/v1/identity/auth/estudiantes',200,
                    json={'correo':alumno.correo,'codigo_convocatoria':alumno.codigo})
                alumno.headers={'Authorization':'Bearer '+login.json()['access_token']}
            titular,ajeno=alumnos
            espera=f'/scheduling/convocatorias/{titular.convocatoria}/espera'
            uno=principal('entrar en espera','POST',espera,201,headers=titular.headers,json={'codigo_acceso':titular.codigo})
            assert principal('recuperar espera','POST',espera,200,headers=titular.headers,json={'codigo_acceso':titular.codigo}).json()==uno.json()
            principal('habilitar por docente','POST',f'/scheduling/sesiones/{sesion}/estado',200,headers=docente_headers,json={'accion':'iniciar'})
            admision=principal('consulta concesión','GET',f'/scheduling/convocatorias/{titular.convocatoria}/admision',200,headers=titular.headers)
            assert admision.json()['admitida']
            with sesiones() as s:
                c=s.get(ConvocatoriaModel,UUID(titular.convocatoria));e=s.get(EventoAuditoriaModel,c.admision_evento_id)
                assert e.sesion_id==UUID(sesion) and e.origen=='DOCENTE' and e.estado_nuevo=='EN_CURSO'
                assert c.espera_version_caso_id==UUID(vid)
            # Publicación técnica sintética, por contrato interno: NO institucional.
            contexto=SimpleNamespace(datos={'id_asignacion':aid},docente=admin_id,ahora=ahora)
            with sesiones.begin() as s:
                docid=publicar(contexto,s);elegir(contexto,s,docid)
                documento=Fuente(s).vigente(id_asignacion=aid,ahora=ahora)
            aislada=FastAPI()
            aislada.include_router(crear_router_consentimiento(crear_sesion=sesiones,fechas=FechasPersistencia(timezone.utc),reloj=reloj))
            aislada.include_router(crear_router_inicio_8b(crear_sesion=sesiones,fechas=FechasPersistencia(timezone.utc),reloj=reloj,
                politica_ingreso=PoliticaIngresoNoConfigurada(),politica_vinculacion=VinculacionLaboratorio(),
                politica_inicio=InicioLaboratorio(documento.referencia),crear_fuente_consentimiento=Fuente))
            with TestClient(aislada,raise_server_exceptions=False) as laboratorio:
                assert aislada.dependency_overrides=={}
                assert set(app.dependency_overrides)=={obtener_reloj_ingreso,obtener_reloj_escenario}
                record_property('preparacion_laboratorio',json.dumps({'admin_hash_real':True,'roles_catalogo_SQL':True,
                    'asociaciones_grupos_matriculas_grant_espacio_y_asignacion':'contratos internos/preparación administrativa LAB',
                    'documento':'SINTETICO NO INSTITUCIONAL','sin_overrides_autenticacion':True}))
                yield SimpleNamespace(main=main,lab=laboratorio,paso=paso,sesiones=sesiones,engine=engine,ahora=ahora,
                    titular=titular,ajeno=ajeno,aid=aid,version=UUID(vid),sesion=UUID(sesion),docid=docid,
                    documento=documento,escenas=escenas,pasos=pasos)
    finally:
        if get_engine.cache_info().currsize:
            actual=get_engine();assert actual.url==url;actual.dispose()
        get_settings.cache_clear();get_session_factory.cache_clear();get_engine.cache_clear()
        app.dependency_overrides.clear();app.dependency_overrides.update(anteriores)


def aceptar(h,alumno=None):
    alumno=alumno or h.titular
    base=f'/api/v1/identity/convocatorias/{alumno.convocatoria}/asignaciones/{h.aid}/consentimiento'
    d=h.paso(h.lab,'aislada','consultar documento','GET',base,200,headers=alumno.headers).json()
    assert d['id_version_documento']==h.docid and d['huella']==h.documento.huella
    return h.paso(h.lab,'aislada','aceptación explícita','POST',base+'/aceptacion',200,headers=alumno.headers,
        json={'id_version_documento':h.docid,'referencia':d['referencia'],'huella':d['huella'],'acepta':True}).json()


def iniciar(h,pk,esperado=201,alumno=None):
    alumno=alumno or h.titular
    return h.paso(h.lab,'aislada','inicio transaccional','POST',f'/api/v1/convocatorias/{alumno.convocatoria}/intentos',esperado,
        headers=alumno.headers,json={'id_asignacion':h.aid,'id_consentimiento':pk,'codigo_acceso':alumno.codigo})


def cantidades(h):
    with h.sesiones() as s:
        p=s.scalars(select(P.id_participacion).where(P.convocatoria_id==UUID(h.titular.convocatoria))).all()
        i=s.scalars(select(I.id_intento).where(I.id_participacion.in_(p))).all() if p else []
        return p,i


def test_recorrido_integral_administrador_docente_estudiante_main_y_aislada(recorrido_lab,record_property):
    h=recorrido_lab;aceptacion=aceptar(h);pk=aceptacion['id_consentimiento']
    assert aceptar(h)==aceptacion and cantidades(h)==([],[])
    ajena=aceptar(h,h.ajeno)
    with escrituras(h) as sql:iniciar(h,ajena['id_consentimiento'],403,alumno=h.ajeno)
    assert sql==[]  # Tiene consentimiento real LAB y matrícula, pero NO concesión.
    txids=[];conexiones=[];commits=[]
    def registrar(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith(('insert into participacion','insert into intento')):
            txids.append(str(conn.scalar(text('SELECT txid_current()'))));conexiones.append(id(conn))
    def commit(conn):commits.append(True)
    event.listen(h.engine,'after_cursor_execute',registrar);event.listen(h.engine,'commit',commit)
    try:r=iniciar(h,pk)
    finally:event.remove(h.engine,'after_cursor_execute',registrar);event.remove(h.engine,'commit',commit)
    assert len(txids)==2 and len(set(txids))==len(set(conexiones))==len(commits)==1
    pid,iid=r.json()['id_participacion'],r.json()['id_intento']
    with h.sesiones() as s:
        assert s.get(P,pid).id_consentimiento==s.get(I,iid).id_consentimiento==pk
        assert s.get(ConsentimientoORM,pk).id_version_documento==h.docid
        assert s.get(AsignacionCasoModel,s.get(P,pid).id_asignacion).version_caso_id==h.version
    iniciar(h,pk,409);assert tuple(map(len,cantidades(h)))==(1,1)
    p=h.paso(h.lab,'aislada','recuperar participación','POST',f'/api/v1/convocatorias/{h.titular.convocatoria}/participacion',200,
        headers=h.titular.headers,json={'id_asignacion':h.aid,'codigo_acceso':h.titular.codigo})
    assert p.json()['id_participacion']==pid
    base=f'/api/v1/attempts/{iid}'
    h.paso(h.main,'app.main','progreso ajeno rechazado','GET',base+'/progress',403,headers=h.ajeno.headers)
    h.paso(h.main,'app.main','escenario ajeno rechazado','GET',base+'/current-scenario',403,headers=h.ajeno.headers)
    for n in (0,1):
        actual=h.paso(h.main,'app.main','escenario actual','GET',base+'/current-scenario',200,headers=h.titular.headers).json()
        assert set(actual)=={'id_escenario','contexto','pregunta','recorrido_finalizado','respondidas'}
        assert actual['id_escenario']==h.escenas[n]['id']
        q=actual['pregunta'];url=base+f'/decisions/{q["id"]}'
        assert set(q)=={'id','enunciado','opciones'} and q['id']==h.escenas[n]['preguntas'][0]['id']
        h.paso(h.main,'app.main','primera respuesta','POST',url,201,headers=h.titular.headers,json={'id_opcion':q['opciones'][0]['id']})
        h.paso(h.main,'app.main','segunda selección rechazada','POST',url,409,headers=h.titular.headers,json={'id_opcion':q['opciones'][1]['id']})
    progreso=h.paso(h.main,'app.main','progreso privado','GET',base+'/progress',200,headers=h.titular.headers)
    assert progreso.json()['respondidas']==2 and progreso.json()['pendientes']==[]
    assert not any(x in progreso.text for x in ('es_correcta','justificacion','nota_final','puntaje','rubrica'))
    final=h.paso(h.main,'app.main','finalizar intento','POST',base+'/finish',200,headers=h.titular.headers)
    assert final.json()['estado']=='FINALIZADO'
    assert h.paso(h.main,'app.main','recuperar cierre','POST',base+'/finish',200,headers=h.titular.headers).json()==final.json()
    with h.sesiones() as s:
        assert s.get(I,iid).estado=='FINALIZADO'
        assert s.scalar(select(func.count()).select_from(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento==iid))==0
    record_property('uow_verificada',json.dumps({'dos_inserts_misma_transaccion_pg':True,'una_conexion':True,'un_commit':True,'persistencia_sesion_independiente':True,'resultados_oficiales':0}))


def test_error_sql_real_revierte_pi_y_reintento_recorrido(recorrido_lab,record_property):
    h=recorrido_lab;pk=aceptar(h)['id_consentimiento'];estados=[]
    def fallo(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith('insert into intento'):
            try:conn.exec_driver_sql('SELECT 1/0')  # Error PostgreSQL real, solo LAB propio.
            except DBAPIError as e:estados.append(e.orig.sqlstate);raise
    event.listen(h.engine,'after_cursor_execute',fallo)
    try:iniciar(h,pk,500)
    finally:event.remove(h.engine,'after_cursor_execute',fallo)
    assert estados==['22012'] and cantidades(h)==([],[])
    with h.sesiones() as s:assert s.get(ConsentimientoORM,pk).id_version_documento==h.docid
    assert iniciar(h,pk).status_code==201 and tuple(map(len,cantidades(h)))==(1,1)
    record_property('rollback_sql_verificado',json.dumps({'sqlstate':'22012','participaciones_tras_error':0,'intentos_tras_error':0,'aceptacion_previa_conservada':True,'reintento':201}))
