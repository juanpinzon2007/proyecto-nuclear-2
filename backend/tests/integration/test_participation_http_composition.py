"""Composición 8B real en aplicación aislada; políticas SOLO de laboratorio.

Cases y su grafo se crean por API. Identity autentica correo/código contra SQL.
Scheduling programa/convoca/inicia por API. Grupo, matrícula, consentimiento y
puente de asignación se siembran como datos explícitos de laboratorio: no existen
servicios públicos autorizados que permitan darlos por creados automáticamente.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, func

from app.db.session import get_session_factory
from app.modules.cases.api.router import router as cases_router
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.identity.api import dependencies as identity
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM, ConsentimientoORM
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.participation.api.router import router as attempts_router
from app.modules.participation.api.provision_router import crear_router_inicio_8b
from app.modules.participation.api.dependencies import obtener_facade, crear_dependencia_facade_8b
from app.modules.participation.application.errors import AccesoDenegado
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.scheduling.api.router import router as scheduling_router, exigir_politica_ingreso_configurada, obtener_reloj_ingreso
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C
from app.modules.scheduling.infrastructure.models import DocenteEspacioAcademicoModel
from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada
from tests.integration.test_cases_graph_authoring import pg_autoria, autor, crear, configurar  # noqa: F401
from tests.integration.cases.conftest import payload_valido  # noqa: F401
from tests.integration.test_attempt_start import IngresoLaboratorio, InicioLaboratorio
from tests.integration.test_participation_provision import VinculacionLaboratorio


class InicioExtraLaboratorio(InicioLaboratorio):
    """Un extra SOLO en este laboratorio, no aprobación de P01–P16."""
    def autorizar(self, c):
        if c.id_permiso_extra is None:
            return super().autorizar(c)
        if c.numero_intento!=2 or c.cantidad_extra!=1 or c.usos_permiso!=0:
            raise AccesoDenegado("Cupo extra LAB agotado.")
        return super().autorizar(replace(c,id_permiso_extra=None,numero_intento=1))


@pytest.fixture
def integracion(autor, request):
    a=autor
    opciones=dict(politica_ingreso=IngresoLaboratorio(),politica_inicio=InicioLaboratorio(),
                  politica_vinculacion=VinculacionLaboratorio())
    opciones.update(getattr(request,"param",{}))
    reloj=SimpleNamespace(ahora=lambda:datetime(2026,11,2,12,1,tzinfo=timezone.utc))
    app=FastAPI()
    app.dependency_overrides.update(a.client.app.dependency_overrides)
    app.dependency_overrides[get_session_factory]=lambda:a.sesiones
    app.dependency_overrides[identity.obtener_fabrica_sesiones_login]=lambda:a.sesiones
    app.dependency_overrides[identity.obtener_dominios_login]=lambda:("universidad.test",)
    app.dependency_overrides[exigir_politica_ingreso_configurada]=lambda:opciones["politica_ingreso"] or PoliticaIngresoNoConfigurada()
    app.dependency_overrides[obtener_reloj_ingreso]=lambda:reloj
    app.dependency_overrides[obtener_facade]=crear_dependencia_facade_8b(crear_sesion=a.sesiones,
        fechas=FechasPersistencia(timezone.utc),reloj=reloj)
    for router in (cases_router,identity_router,scheduling_router,attempts_router):app.include_router(router)
    app.include_router(crear_router_inicio_8b(crear_sesion=a.sesiones,reloj=reloj,
        fechas=FechasPersistencia(timezone.utc),**opciones))
    estudiante=a.propio+2;uuid_estudiante=uuid4();uuid_docente=uuid4()
    fecha=datetime(2026,11,2,12)
    with a.sesiones.begin() as s:
        s.add_all([IdentidadAcademicaORM(id_usuario=estudiante,sistema="SCHEDULING",id_academico=uuid_estudiante),
                   IdentidadAcademicaORM(id_usuario=a.propio,sistema="SCHEDULING",id_academico=uuid_docente)])
        grupo=GrupoAcademicoORM(id_profesor=a.propio,nombre="Grupo LAB",periodo="2026-2")
        s.add(grupo);s.flush()
        matricula=GrupoEstudianteORM(id_grupo=grupo.id_grupo,id_estudiante=estudiante,fecha_ingreso=fecha)
        consentimiento=ConsentimientoORM(id_estudiante=estudiante,version_texto="sintetico",fecha_aceptacion=fecha)
        s.add_all([matricula,consentimiento]);s.flush()
        grupo_id,matricula_id,consentimiento_id=grupo.id_grupo,matricula.id_grupo_estudiante,consentimiento.id_consentimiento
        otro=UsuarioORM(id_rol=2,nombre='Otro alumno LAB',correo=f'{uuid4()}@universidad.test',clave_hash='no-login')
        s.add(otro);s.flush();otro_id=otro.id_usuario
        s.add(IdentidadAcademicaORM(id_usuario=otro_id,sistema='SCHEDULING',id_academico=uuid4()))
    with TestClient(app,raise_server_exceptions=False) as client:
        actor=SimpleNamespace(**(vars(a)|dict(client=client)))
        version,grafo,escenas=crear(actor)
        assert configurar(actor,version,grafo).status_code==200
        assert client.post(f"/api/v1/cases/{version}/publish",headers=a.headers).status_code==200
        espacio=client.post('/scheduling/espacios',headers=a.headers,json={'nombre':'Espacio LAB'})
        assert espacio.status_code==201,espacio.text
        # Asignación explícita de laboratorio; crear el catálogo no concede uso.
        with a.sesiones.begin() as s:
            s.add(DocenteEspacioAcademicoModel(id_docente=a.propio,espacio_academico_id=UUID(espacio.json()['id'])))
        sesion=client.post('/scheduling/sesiones',headers=a.headers,json={
            'espacio_academico_id':espacio.json()['id'],'version_caso_id':version,
            'fecha_inicio':fecha.replace(tzinfo=timezone.utc).isoformat(),
            'fecha_fin':(fecha+timedelta(hours=1)).replace(tzinfo=timezone.utc).isoformat(),
            'tiempo_maximo_minutos':30})
        assert sesion.status_code==201,sesion.text
        sid=sesion.json()['id']
        with a.sesiones.begin() as s:
            caso=s.scalar(select(CasoModel).join(VersionCasoModel,VersionCasoModel.caso_id==CasoModel.id)
                          .where(VersionCasoModel.id==UUID(version)))
            asignacion=A(id_grupo=grupo_id,id_caso=caso.id_caso,sesion_programada_id=UUID(sid),
                version_caso_id=UUID(version),apertura=fecha,cierre=fecha+timedelta(hours=1),
                fecha_limite_ingreso=fecha+timedelta(hours=1),tiempo_maximo_min=30)
            s.add(asignacion);s.flush();aid=asignacion.id_asignacion
        conv=client.post(f'/scheduling/sesiones/{sid}/convocatorias',headers=a.headers,
            json={'estudiante_id':str(uuid_estudiante)})
        assert conv.status_code==201,conv.text
        cid=conv.json()['convocatoria_id'];codigo=conv.json()['codigo_acceso']
        estado=client.post(f'/scheduling/sesiones/{sid}/estado',headers=a.headers,json={'accion':'iniciar'})
        assert estado.status_code==200,estado.text
        login=client.post('/api/v1/identity/auth/estudiantes',json={
            'correo':f'autor{estudiante}@universidad.test','codigo_convocatoria':codigo})
        assert login.status_code==200,login.text
        headers={'Authorization':'Bearer '+login.json()['access_token']}
        tokens=app.dependency_overrides[identity.obtener_fabrica_tokens]()()
        yield SimpleNamespace(a=actor,client=client,sesiones=a.sesiones,estudiante=estudiante,
            convocatoria=UUID(cid),sesion=UUID(sid),asignacion=aid,version=UUID(version),
            matricula=matricula_id,consentimiento=consentimiento_id,uuid_estudiante=uuid_estudiante,
            reloj=reloj,headers=headers,codigo=codigo,escenas=escenas,
            headers_ajeno={'Authorization':'Bearer '+tokens.emitir(str(otro_id),cid)},
            base=f'/api/v1/convocatorias/{cid}',
            body={'id_asignacion':aid,'codigo_acceso':codigo})


def cantidades(h):
    with h.sesiones() as s:
        p=s.scalars(select(P.id_participacion).where(P.convocatoria_id==h.convocatoria)).all()
        i=s.execute(select(I.id_intento,I.id_permiso_extra).where(I.id_participacion.in_(p))).all() if p else []
        return p,i


def iniciar(h,**extra):
    return h.client.post(h.base+'/intentos',headers=h.headers,
        json=h.body|dict(id_consentimiento=h.consentimiento)|extra)


def test_ingreso_provision_inicio_respuestas_y_cierre_son_operaciones_distintas(integracion):
    h=integracion
    ingreso=h.client.post('/scheduling/validar-ingreso',headers=h.headers,json={
        'convocatoria_id':str(h.convocatoria),'estudiante_id':str(h.uuid_estudiante),'codigo_acceso':h.codigo})
    assert ingreso.status_code==200,ingreso.text
    assert cantidades(h)==([],[])
    p=h.client.post(h.base+'/participacion',headers=h.headers,json=h.body)
    otra=h.client.post(h.base+'/participacion',headers=h.headers,json=h.body)
    assert p.status_code==201 and otra.status_code==200
    assert p.json()['id_participacion']==otra.json()['id_participacion']
    assert len(cantidades(h)[0])==1 and cantidades(h)[1]==[]
    inicio=iniciar(h);assert inicio.status_code==201,inicio.text
    ik=inicio.json()['id_intento']
    for escena in (0,1):
        q=h.escenas[escena]['preguntas'][0]
        url=f"/api/v1/attempts/{ik}/decisions/{q['id']}"
        body={'id_opcion':q['opciones'][0]['id']}
        assert h.client.post(url,headers=h.headers,json=body).status_code==201
        assert h.client.put(url,headers=h.headers,json=body).status_code==409
    progreso=h.client.get(f'/api/v1/attempts/{ik}/progress',headers=h.headers)
    assert progreso.status_code==200 and progreso.json()['respondidas']==2
    assert progreso.json()['pendientes']==[]
    assert all(x not in progreso.text for x in ['es_correcta','justificacion','nota_final',h.codigo])
    fin=f'/api/v1/attempts/{ik}/finish'
    assert h.client.post(fin,headers=h.headers).json()['estado']=='FINALIZADO'
    assert h.client.post(fin,headers=h.headers).status_code==200
    assert iniciar(h).status_code==403  # No hay repetición implícita.


def test_inicio_combinado_conserva_version_asignada_y_no_ultima_publicacion(integracion):
    h=integracion
    posterior,g,_=crear(h.a);assert configurar(h.a,posterior,g).status_code==200
    assert h.client.post(f'/api/v1/cases/{posterior}/publish',headers=h.a.headers).status_code==200
    r=iniciar(h);assert r.status_code==201,r.text
    assert all(len(x)==1 for x in cantidades(h))
    with h.sesiones() as s:
        a=s.get(A,h.asignacion)
        assert a.version_caso_id==h.version and a.version_caso_id!=UUID(posterior)
        assert s.get(I,r.json()['id_intento']).id_participacion==r.json()['id_participacion']
    assert iniciar(h).status_code==409
    assert h.client.post(f"/api/v1/participations/{r.json()['id_participacion']}/attempts",
        headers=h.headers,json={'id_consentimiento':h.consentimiento}).status_code==503
    assert h.client.get(f"/api/v1/participations/{r.json()['id_participacion']}/attempts/{r.json()['id_intento']}/result",
        headers=h.headers).status_code==503


@pytest.mark.parametrize('integracion',[{'politica_ingreso':None},{'politica_vinculacion':None},{'politica_inicio':None}],indirect=True)
def test_sin_politica_no_se_confirma_participacion_ni_intento(integracion):
    h=integracion;r=iniciar(h)
    assert r.status_code==503 and r.json()['detail']['codigo']=='INTEGRACION_O_POLITICA_PENDIENTE'
    assert cantidades(h)==([],[])
    assert h.codigo not in r.text and r.headers['cache-control']=='no-store'


@pytest.mark.parametrize('problema',['anonimo','invalido','ajeno','convocatoria_inexistente','retirada','matricula','sesion_finalizada','antes','fin'])
def test_http_no_concede_inicio_fuera_de_su_alcance(integracion,problema):
    h=integracion;headers=h.headers;url=h.base+'/intentos'
    if problema=='anonimo':headers={}
    elif problema=='invalido':headers={'Authorization':'Bearer invalido'}
    elif problema=='ajeno':headers=h.headers_ajeno
    elif problema=='convocatoria_inexistente':url=f'/api/v1/convocatorias/{uuid4()}/intentos'
    elif problema in ('antes','fin'):
        h.reloj.ahora=lambda:datetime(2026,11,2,11,59,tzinfo=timezone.utc) if problema=='antes' else datetime(2026,11,2,13,tzinfo=timezone.utc)
    else:
        with h.sesiones.begin() as s:
            if problema=='retirada':s.get(C,h.convocatoria).estado='RETIRADA'
            elif problema=='matricula':s.get(GrupoEstudianteORM,h.matricula).activo=False
            else:s.get(S,h.sesion).estado='FINALIZADO'
    r=h.client.post(url,headers=headers,json=h.body|dict(id_consentimiento=h.consentimiento))
    assert r.status_code==(401 if problema in ('anonimo','invalido') else 403),r.text
    assert cantidades(h)==([],[])


@pytest.mark.parametrize('campo',['id_estudiante','estado','tolerancia_minutos'])
def test_cliente_no_aporta_identidad_estado_o_politica(integracion,campo):
    h=integracion;r=h.client.post(h.base+'/participacion',headers=h.headers,json=h.body|{campo:999})
    assert r.status_code==422 and h.codigo not in r.text
    assert cantidades(h)==([],[])


@pytest.mark.parametrize('operacion',['participacion','intentos'])
def test_solicitudes_http_concurrentes_no_duplican(integracion,operacion):
    h=integracion;barrera=Barrier(2)
    def solicitar(_):
        barrera.wait(timeout=10)
        return iniciar(h) if operacion=='intentos' else h.client.post(h.base+'/participacion',headers=h.headers,json=h.body)
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(solicitar,range(2)))
    assert sorted(r.status_code for r in rs)==([201,409] if operacion=='intentos' else [200,201])
    p,i=cantidades(h);assert len(p)==1 and len(i)==(1 if operacion=='intentos' else 0)


def test_fallo_despues_del_insert_de_intento_revierte_tambien_participacion(integracion,monkeypatch):
    h=integracion;original=RepositorioParticipacionSQLAlchemy.agregar_intento
    def fallo(self,intento):
        original(self,intento)
        raise RuntimeError('Fallo controlado posterior al INSERT')
    with monkeypatch.context() as m:
        m.setattr(RepositorioParticipacionSQLAlchemy,'agregar_intento',fallo)
        assert iniciar(h).status_code==500
    assert cantidades(h)==([],[])
    assert iniciar(h).status_code==201


@pytest.mark.parametrize('integracion',[{'politica_inicio':InicioExtraLaboratorio()}],indirect=True)
def test_permiso_extra_se_consume_en_la_misma_transaccion_solo_en_lab(integracion):
    h=integracion;r=iniciar(h);assert r.status_code==201
    h.client.post(f"/api/v1/attempts/{r.json()['id_intento']}/finish",headers=h.headers)
    with h.sesiones.begin() as s:
        permiso=PermisoIntentoExtraORM(id_participacion=r.json()['id_participacion'],id_profesor=h.a.propio,
            cantidad_autorizada=1,justificacion='Concesión SOLO LAB',fecha_autorizacion=datetime(2026,11,2,12))
        s.add(permiso);s.flush();pk=permiso.id_permiso_extra
    extra=iniciar(h,id_permiso_extra=pk);assert extra.status_code==201,extra.text
    h.client.post(f"/api/v1/attempts/{extra.json()['id_intento']}/finish",headers=h.headers)
    assert iniciar(h,id_permiso_extra=pk).status_code==403
    with h.sesiones() as s:
        assert s.scalar(select(func.count()).select_from(I).where(I.id_permiso_extra==pk))==1
