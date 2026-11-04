"""Aceptación RF-21 con JWT y PostgreSQL 17 desechable, sin proveedor de correo.

Reutiliza autoría/API/login reales de 8B. Matrículas/asignaciones y políticas de
inicio son datos explícitos de laboratorio, no overrides de autorización RF-21.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func

from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I, PasoSimulacionModel as Paso
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C, NotificacionModel as N
from tests.integration.test_participation_http_composition import (
    integracion, autor, pg_autoria, payload_valido, iniciar,
)  # noqa: F401 - fixtures reales compartidas


@pytest.fixture
def gestion(integracion):
    h=integracion
    with h.sesiones() as s:
        original=s.get(S,h.sesion)
        datos=dict(espacio_academico_id=str(original.espacio_academico_id),version_caso_id=str(h.version),
            fecha_inicio=original.fecha_inicio.isoformat(),fecha_fin=original.fecha_fin.isoformat(),
            tiempo_maximo_minutos=original.tiempo_maximo_minutos,mensaje_personalizado='Mensaje docente de laboratorio')
    r=h.client.post('/scheduling/sesiones',headers=h.a.headers,json=datos)
    assert r.status_code==201
    h.nueva_sesion=UUID(r.json()['id']);h.nuevo_base=f'/scheduling/sesiones/{h.nueva_sesion}/convocatorias'
    h.retiro=f'/scheduling/sesiones/{h.sesion}/convocatorias/{h.convocatoria}'
    with h.sesiones.begin() as s:
        origen=s.get(A,h.asignacion)
        asignacion=A(id_grupo=origen.id_grupo,id_caso=origen.id_caso,sesion_programada_id=h.nueva_sesion,
            version_caso_id=h.version,apertura=origen.apertura,cierre=origen.cierre,
            fecha_limite_ingreso=origen.fecha_limite_ingreso,tiempo_maximo_min=origen.tiempo_maximo_min)
        s.add(asignacion);s.flush();h.nueva_asignacion=asignacion.id_asignacion
        extra=UsuarioORM(id_rol=2,nombre='Otro matriculado LAB',correo=f'{uuid4()}@universidad.test',clave_hash='sin-login')
        s.add(extra);s.flush();h.extra=extra.id_usuario;h.uuid_extra=uuid4()
        s.add_all([IA(id_usuario=h.extra,sistema='SCHEDULING',id_academico=h.uuid_extra),
            IA(id_usuario=h.a.propio+1,sistema='SCHEDULING',id_academico=uuid4())])
        m=M(id_grupo=origen.id_grupo,id_estudiante=h.extra,fecha_ingreso=origen.apertura)
        s.add(m);s.flush();h.m_extra=m.id_grupo_estudiante
    return h


def alta(h,estudiante=None,headers=None):
    return h.client.post(h.nuevo_base,headers=h.a.headers if headers is None else headers,
        json={'estudiante_id':str(h.uuid_estudiante if estudiante is None else estudiante)})


def convocatorias(h):
    with h.sesiones() as s:return s.scalars(select(C.id).where(C.sesion_id==h.nueva_sesion)).all()


def avisos(h,cid,tipo):
    with h.sesiones() as s:return s.execute(select(N.__table__).where(N.convocatoria_id==cid,N.tipo==tipo)).all()


def test_altas_individuales_y_avisos_personalizados_sin_correo_ni_codigos_persistidos(gestion):
    h=gestion
    primero=alta(h);assert primero.status_code==201
    assert primero.headers['Cache-Control']=='no-store'
    cid=UUID(primero.json()['convocatoria_id']);codigo=primero.json()['codigo_acceso']
    n=avisos(h,cid,'CONVOCATORIA');assert len(n)==1
    assert n[0].destinatario_id==h.uuid_estudiante and n[0].canal=='INTERNA'
    assert 'Mensaje docente de laboratorio' in n[0].mensaje
    assert not any(codigo in x.mensaje for x in n)
    with h.sesiones() as s:
        assert s.get(C,cid).codigo_hash!=codigo
        assert s.scalar(select(func.count()).select_from(N).where(N.convocatoria_id==cid,N.canal=='CORREO'))==0
    segundo=alta(h,h.uuid_extra);assert segundo.status_code==201
    cid2=UUID(segundo.json()['convocatoria_id'])
    assert avisos(h,cid2,'CONVOCATORIA')[0].destinatario_id==h.uuid_extra
    assert alta(h).status_code==422  # No regenerar ni revelar el código perdido.
    assert len(convocatorias(h))==2 and len(avisos(h,cid,'CONVOCATORIA'))==1
    listado=h.client.get(h.nuevo_base,headers=h.a.headers)
    assert listado.status_code==200
    assert all(set(x)=={'id','sesion_id','estudiante_id','estado'} for x in listado.json())


@pytest.mark.parametrize('actor',['anonimo','estudiante','docente_ajeno'])
def test_alta_retiro_y_listado_rechazan_actores_ajenos(gestion,actor):
    h=gestion;headers={'anonimo':{},'estudiante':h.headers,'docente_ajeno':h.a.ajeno}[actor]
    esperado=401 if actor=='anonimo' else 403
    assert alta(h,headers=headers).status_code==esperado
    assert h.client.delete(h.retiro,headers=headers).status_code==esperado
    assert h.client.get(h.nuevo_base,headers=headers).status_code==esperado
    assert convocatorias(h)==[] and avisos(h,h.convocatoria,'CONVOCATORIA_RETIRADA')==[]


@pytest.mark.parametrize('problema',['sin_vinculo','sin_matricula','matricula_inactiva','cuenta_inactiva','sin_rol','vinculo_ambiguo','sin_asignacion'])
def test_alta_exige_ambito_academico_persistente(gestion,problema):
    h=gestion;destino=h.uuid_extra
    with h.sesiones.begin() as s:
        if problema=='sin_vinculo':destino=uuid4()
        elif problema=='sin_matricula':s.delete(s.get(M,h.m_extra))
        elif problema=='matricula_inactiva':s.get(M,h.m_extra).activo=False
        elif problema=='cuenta_inactiva':s.get(UsuarioORM,h.extra).activo=False
        elif problema=='sin_rol':s.get(UsuarioORM,h.extra).id_rol=1
        elif problema=='vinculo_ambiguo':s.add(IA(id_usuario=h.extra,sistema='SCHEDULING',id_academico=uuid4()))
        else:s.delete(s.get(A,h.nueva_asignacion))
    assert alta(h,destino).status_code==(503 if problema in ('vinculo_ambiguo','sin_asignacion') else 403)
    assert convocatorias(h)==[]


def test_retiro_revoca_login_ingreso_y_escritura_con_jwt_previo_sin_borrar_historia(gestion):
    h=gestion;r=iniciar(h);assert r.status_code==201
    ik,pk=r.json()['id_intento'],r.json()['id_participacion']
    q=h.escenas[0]['preguntas'][0];ruta=f"/api/v1/attempts/{ik}/decisions/{q['id']}"
    assert h.client.post(ruta,headers=h.headers,json={'id_opcion':q['opciones'][0]['id']}).status_code==201
    retirada=h.client.delete(h.retiro,headers=h.a.headers)
    assert retirada.status_code==200 and retirada.json()['estado']=='RETIRADA'
    assert h.client.delete(h.retiro,headers=h.a.headers).status_code==200
    n=avisos(h,h.convocatoria,'CONVOCATORIA_RETIRADA');assert len(n)==1
    assert n[0].destinatario_id==h.uuid_estudiante
    bandeja=h.client.get(f'/scheduling/notificaciones?destinatario_id={h.uuid_estudiante}',headers=h.headers)
    assert bandeja.status_code==200 and str(n[0].id) in {x['id'] for x in bandeja.json()}
    assert h.client.get('/api/v1/identity/me',headers=h.headers).status_code==200
    assert iniciar(h).status_code==403
    assert h.client.post('/api/v1/identity/auth/estudiantes',json={
        'correo':f'autor{h.estudiante}@universidad.test','codigo_convocatoria':h.codigo}).status_code==401
    assert h.client.post('/scheduling/validar-ingreso',headers=h.headers,json={
        'convocatoria_id':str(h.convocatoria),'estudiante_id':str(h.uuid_estudiante),'codigo_acceso':h.codigo}).status_code==403
    assert h.client.get(f'/api/v1/attempts/{ik}/progress',headers=h.headers).status_code==403
    assert h.client.post(ruta,headers=h.headers,json={'id_opcion':q['opciones'][1]['id']}).status_code==403
    with h.sesiones() as s:
        assert s.get(P,pk) is not None and s.get(I,ik).estado=='EN_CURSO'
        assert s.scalar(select(func.count()).select_from(Paso).where(Paso.id_intento==ik))==1
    # No se anula la cuenta ni se destruye/cierra el intento por una política inventada.


@pytest.mark.parametrize('operacion',['alta','retiro'])
def test_solicitudes_concurrentes_no_duplican_convocatorias_o_avisos(gestion,operacion):
    h=gestion;barrera=Barrier(2)
    def ejecutar(_):
        barrera.wait(timeout=10)
        return (alta(h) if operacion=='alta' else h.client.delete(h.retiro,headers=h.a.headers)).status_code
    with ThreadPoolExecutor(max_workers=2) as p:estados=sorted(p.map(ejecutar,range(2)))
    if operacion=='alta':
        assert estados==[201,422]
        filas=convocatorias(h);assert len(filas)==1 and len(avisos(h,filas[0],'CONVOCATORIA'))==1
    else:
        assert estados==[200,200] and len(avisos(h,h.convocatoria,'CONVOCATORIA_RETIRADA'))==1


@pytest.mark.parametrize('operacion',['alta','retiro'])
def test_fallo_tras_persistir_aviso_revierte_y_reintento_recupera(gestion,monkeypatch,operacion):
    from app.modules.scheduling.infrastructure import convocation_management as modulo
    h=gestion;original=modulo.crear_notificacion
    def fallar(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Fallo de laboratorio antes de commit')
    def ejecutar():return alta(h) if operacion=='alta' else h.client.delete(h.retiro,headers=h.a.headers)
    with monkeypatch.context() as m:
        m.setattr(modulo,'crear_notificacion',fallar)
        assert ejecutar().status_code==500
    if operacion=='alta':assert convocatorias(h)==[]
    else:
        with h.sesiones() as s:assert s.get(C,h.convocatoria).estado=='ACTIVA'
        assert avisos(h,h.convocatoria,'CONVOCATORIA_RETIRADA')==[]
    assert ejecutar().status_code==(201 if operacion=='alta' else 200)


def test_retiro_de_convocatoria_de_otra_sesion_no_modifica_destinatario(gestion):
    h=gestion
    r=h.client.delete(h.nuevo_base+'/'+str(h.convocatoria),headers=h.a.headers)
    assert r.status_code==403
    with h.sesiones() as s:assert s.get(C,h.convocatoria).estado=='ACTIVA'


def test_uuid_docente_no_sustituye_cuenta_autenticada_en_el_adaptador_sql(gestion):
    from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
    from app.modules.identity.domain.errors import AccesoDenegado
    from app.modules.scheduling.infrastructure.convocation_management import convocar_con_aviso
    h=gestion
    with h.sesiones.begin() as s:
        ajeno=RepositorioUsuariosSQLAlchemy(s).obtener(str(h.a.propio+1))
        propio=s.scalar(select(IA.id_academico).where(IA.id_usuario==h.a.propio,IA.sistema=='SCHEDULING'))
        with pytest.raises(AccesoDenegado):
            convocar_con_aviso(s,usuario=ajeno,docente_id=propio,estudiante_id=h.uuid_extra,sesion_id=h.nueva_sesion)
    assert convocatorias(h)==[]


@pytest.mark.parametrize('estado',['EN_CURSO','FINALIZADO'])
def test_alta_no_reabre_ingreso_en_sesion_iniciada_o_finalizada(gestion,estado):
    h=gestion;url=f'/scheduling/sesiones/{h.nueva_sesion}/estado'
    assert h.client.post(url,headers=h.a.headers,json={'accion':'iniciar'}).status_code==200
    if estado=='FINALIZADO':assert h.client.post(url,headers=h.a.headers,json={'accion':'finalizar'}).status_code==200
    assert alta(h).status_code==422 and convocatorias(h)==[]
