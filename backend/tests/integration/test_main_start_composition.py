"""Aceptación MAIN/PG17: políticas y documento SINTÉTICOS solo por inyección LAB.

No se consideran aprobados RF-12/23/25. Las pruebas sin inyección acreditan cierre.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta, datetime, timezone
from threading import Barrier
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
import sqlalchemy as sa

from app.main import app
from app.modules.identity.api.consent_dependencies import (
    obtener_aprobacion_consentimiento, obtener_reloj_consentimiento,
)
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C
from app.modules.participation.api.start_dependencies import obtener_politica_inicio, obtener_politica_vinculacion
from app.modules.participation.application.errors import AccesoDenegado
from app.modules.participation.infrastructure.models import ParticipacionModel as P,IntentoModel as I
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from tests.integration.test_lab_student_journey import recorrido_lab,pg_autoria,payload_valido,cantidades
from tests.integration.test_attempt_start import InicioLaboratorio
from tests.integration.test_participation_provision import VinculacionLaboratorio


class AprobacionSoloLaboratorio:
    def __init__(self,documento):self.documento=documento
    def autorizar(self,documento,*,id_asignacion,ahora):
        if (documento.id_version_documento!=self.documento.id_version_documento
            or documento.huella!=self.documento.huella or documento.referencia!=self.documento.referencia):
            raise IntegracionPendiente()


class InicioConExtraSoloLaboratorio(InicioLaboratorio):
    def autorizar(self,c):
        if c.id_permiso_extra is not None:
            if c.numero_intento!=2 or c.intentos_base!=1 or c.cantidad_extra!=1 or c.usos_permiso!=0:
                raise AccesoDenegado('Repetición fuera del contrato sintético.')
            c=replace(c,numero_intento=1,id_permiso_extra=None)
        super().autorizar(c)


def componer_laboratorio(h):
    # Solo políticas/reloj: no se sustituye auth, SQL, admisión ni el coordinador.
    app.dependency_overrides[obtener_aprobacion_consentimiento]=lambda:AprobacionSoloLaboratorio(h.documento)
    app.dependency_overrides[obtener_reloj_consentimiento]=lambda:SimpleNamespace(ahora=lambda:h.ahora)
    app.dependency_overrides[obtener_politica_inicio]=lambda:InicioConExtraSoloLaboratorio(h.documento.referencia)
    app.dependency_overrides[obtener_politica_vinculacion]=lambda:VinculacionLaboratorio()


def urls(h):
    return (f'/api/v1/identity/convocatorias/{h.titular.convocatoria}/asignaciones/{h.aid}/consentimiento',
        f'/api/v1/convocatorias/{h.titular.convocatoria}/intentos')


def aceptar_main(h):
    url,_=urls(h);d=h.main.get(url,headers=h.titular.headers)
    assert d.status_code==200
    b={k:d.json()[k] for k in ('id_version_documento','referencia','huella')}|{'acepta':True}
    a=h.main.post(url+'/aceptacion',headers=h.titular.headers,json=b)
    assert a.status_code==200
    return a,b


def iniciar_main(h,cid,**cambios):
    return h.main.post(urls(h)[1],headers=h.titular.headers,json={
        'id_asignacion':h.aid,'codigo_acceso':h.titular.codigo,'id_consentimiento':cid}|cambios)


@pytest.fixture
def main_preparada(recorrido_lab):
    h=recorrido_lab;componer_laboratorio(h);yield h


def test_default_proveedores_cerrados_sin_politicas_ni_doc_aprobado(recorrido_lab):
    h=recorrido_lab;u,start=urls(h)
    for method,url,body in [('GET',u,None),('GET',u+'/aceptacion',None),('POST',u+'/aceptacion',
        {'id_version_documento':h.docid,'referencia':h.documento.referencia,'huella':h.documento.huella,'acepta':True}),
        ('POST',start,{'id_asignacion':h.aid,'codigo_acceso':h.titular.codigo,'id_consentimiento':1})]:
        r=h.main.request(method,url,headers=h.titular.headers,json=body)
        assert r.status_code==503 and r.headers['Cache-Control']=='no-store'
    assert cantidades(h)==([],[])
    with h.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(C).where(C.id_estudiante==h.titular.id))==0


@pytest.mark.parametrize('actor,expected',[('anonimo',401),('invalido',401),('docente',403)])
def test_auth_precede_politicas(recorrido_lab,actor,expected):
    h=recorrido_lab;headers={} if actor=='anonimo' else {'Authorization':'Bearer invalido'}
    if actor=='docente':
        # Cuenta real del creador; JWT emitido por login ya probado en fixture.
        from app.modules.identity.infrastructure.models import UsuarioORM
        from app.modules.identity.infrastructure.credentials import obtener_hasheador
        with h.sesiones.begin() as s:
            u=s.scalar(sa.select(UsuarioORM).where(UsuarioORM.id_rol==1));correo=u.correo
            clave='Clave exclusivamente sintetica auth fase1';u.clave_hash=obtener_hasheador().hash(clave)
        login=h.main.post('/api/v1/identity/auth/personal',json={'correo':correo,'clave':clave});assert login.status_code==200
        headers={'Authorization':'Bearer '+login.json()['access_token']}
    for url in (urls(h)[0],urls(h)[1]):
        r=h.main.request('GET' if url.endswith('consentimiento') else 'POST',url,headers=headers,
            json=None if url.endswith('consentimiento') else {'id_asignacion':h.aid,'codigo_acceso':h.titular.codigo,'id_consentimiento':1})
        assert r.status_code==expected
    assert cantidades(h)==([],[])


def test_recorrido_main_aceptacion_inicio_decisiones_cierre(main_preparada):
    h=main_preparada;a,b=aceptar_main(h);u,_=urls(h)
    assert h.main.post(u+'/aceptacion',headers=h.titular.headers,json=b).json()==a.json()
    cid=a.json()['id_consentimiento'];r=iniciar_main(h,cid);assert r.status_code==201
    ik=r.json()['id_intento'];pk=r.json()['id_participacion']
    with h.sesiones() as s:
        i=s.get(I,ik);assert i.id_consentimiento==s.get(P,pk).id_consentimiento==cid
        assert i.duracion_concedida_segundos==1800 and s.get(C,cid).id_version_documento==h.docid
    assert iniciar_main(h,cid).status_code==409
    for e in h.escenas[:2]:
        q=e['preguntas'][0];url=f'/api/v1/attempts/{ik}/decisions/{q["id"]}'
        assert h.main.post(url,headers=h.titular.headers,json={'id_opcion':q['opciones'][0]['id']}).status_code==201
        assert h.main.post(url,headers=h.titular.headers,json={'id_opcion':q['opciones'][1]['id']}).status_code==409
    p=h.main.get(f'/api/v1/attempts/{ik}/progress',headers=h.titular.headers)
    assert p.status_code==200 and p.json()['respondidas']==2
    r=h.main.post(f'/api/v1/attempts/{ik}/finish',headers=h.titular.headers);assert r.status_code==200
    assert h.main.post(f'/api/v1/attempts/{ik}/finish',headers=h.titular.headers).json()==r.json()
    with h.sesiones() as s:assert s.get(I,ik).estado=='FINALIZADO' and s.scalar(sa.select(sa.func.count()).select_from(R))==0
    assert '/api/v1/convocatorias/{convocatoria_id}/participacion' not in app.openapi()['paths']


@pytest.mark.parametrize('faltante',[obtener_politica_inicio,obtener_politica_vinculacion,obtener_aprobacion_consentimiento])
def test_un_puerto_ausente_impide_insertar(main_preparada,faltante):
    h=main_preparada;a,_=aceptar_main(h);app.dependency_overrides.pop(faltante)
    assert iniciar_main(h,a.json()['id_consentimiento']).status_code==503
    assert cantidades(h)==([],[])


def test_aprobacion_invalida_no_confirma_evidencia(main_preparada):
    h=main_preparada
    class NoEsAprobacion:
        def autorizar(self,*a,**k):return True
    app.dependency_overrides[obtener_aprobacion_consentimiento]=lambda:NoEsAprobacion()
    assert h.main.get(urls(h)[0],headers=h.titular.headers).status_code==503
    with h.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(C).where(C.id_estudiante==h.titular.id))==0


@pytest.mark.parametrize('problema',['matricula','retirada','aceptacion_ajena'])
def test_autorizacion_revalidada_en_main_antes_de_insertar(main_preparada,problema):
    h=main_preparada;a,_=aceptar_main(h);cid=a.json()['id_consentimiento']
    if problema=='matricula':
        from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
        with h.sesiones.begin() as s:
            s.get(M,h.titular.matricula).activo=False
    elif problema=='retirada':
        from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as Conv
        from uuid import UUID
        with h.sesiones.begin() as s:s.get(Conv,UUID(h.titular.convocatoria)).estado='RETIRADA'
    else:
        # PK auténtica de otra aceptación explícita; nunca un ID ficticio.
        from tests.integration.test_lab_student_journey import aceptar
        cid=aceptar(h,h.ajeno)['id_consentimiento']
    assert iniciar_main(h,cid).status_code==403
    assert cantidades(h)==([],[])


def test_inicio_concurrente_y_rollback_real(main_preparada):
    h=main_preparada;a,_=aceptar_main(h);cid=a.json()['id_consentimiento']
    def fallo(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith('insert into intento'):conn.exec_driver_sql('SELECT 1/0')
    from app.db.session import get_engine
    engines={h.engine,get_engine()}
    for engine in engines:sa.event.listen(engine,'before_cursor_execute',fallo)
    try:
        # 22012 es inesperado: RutaParticipacion lo propaga como 500 (contrato
        # de test_lab_student_journey), no como dependencia/política ausente 503.
        r=iniciar_main(h,cid)
        assert r.status_code==500 and 'SELECT' not in r.text and 'postgresql' not in r.text
    finally:
        for engine in engines:sa.event.remove(engine,'before_cursor_execute',fallo)
    assert cantidades(h)==([],[])
    gate=Barrier(2)
    def enviar():gate.wait(timeout=10);return iniciar_main(h,cid).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(lambda _:enviar(),range(2)))
    assert sorted(codes)==[201,409] and tuple(map(len,cantidades(h)))==(1,1)


def test_repeticion_permiso_real_consumido_una_vez(main_preparada):
    h=main_preparada;a,_=aceptar_main(h);cid=a.json()['id_consentimiento'];primero=iniciar_main(h,cid)
    assert primero.status_code==201;ik=primero.json()['id_intento']
    assert h.main.post(f'/api/v1/attempts/{ik}/finish',headers=h.titular.headers).status_code==200
    assert iniciar_main(h,cid).status_code==403
    # El permiso se autoriza mediante el endpoint real, no se inventa una FK.
    from app.modules.identity.infrastructure.models import UsuarioORM
    from app.modules.identity.infrastructure.credentials import obtener_hasheador
    from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
    from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S
    with h.sesiones.begin() as s:
        docente_uuid=s.get(S,h.sesion).docente_id
        u=s.scalar(sa.select(UsuarioORM).join(IA,IA.id_usuario==UsuarioORM.id_usuario)
            .where(IA.sistema=='SCHEDULING',IA.id_academico==docente_uuid));correo=u.correo
        clave='Clave exclusivamente sintetica repeticion fase1';u.clave_hash=obtener_hasheador().hash(clave)
    login=h.main.post('/api/v1/identity/auth/personal',json={'correo':correo,'clave':clave});assert login.status_code==200
    permiso=h.main.post('/api/v1/identity/excepciones/repeticiones',headers={'Authorization':'Bearer '+login.json()['access_token']},
        json={'id_sesion':str(h.sesion),'id_estudiante':str(h.titular.id)})
    assert permiso.status_code==201
    pid=permiso.json()['id_permiso_extra']
    # Permiso emitido por reloj real: no simular que precede al instante congelado.
    from app.modules.participation.api.dependencies import obtener_reloj_escenario
    h.ahora=datetime.now(timezone.utc)
    app.dependency_overrides[obtener_reloj_escenario]=lambda:SimpleNamespace(ahora=lambda:h.ahora)
    gate=Barrier(2)
    def enviar():gate.wait(timeout=10);return iniciar_main(h,cid,id_permiso_extra=pid)
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:enviar(),range(2)))
    assert sorted(r.status_code for r in rs)==[201,409]
    r=next(r for r in rs if r.status_code==201)
    assert iniciar_main(h,cid,id_permiso_extra=pid).status_code==409
    assert h.main.post(f'/api/v1/attempts/{r.json()["id_intento"]}/finish',headers=h.titular.headers).status_code==200
    assert iniciar_main(h,cid,id_permiso_extra=pid).status_code==403
    with h.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(I).where(I.id_permiso_extra==pid))==1


def test_vencimiento_y_respuestas_conservadas_main(main_preparada):
    h=main_preparada;a,_=aceptar_main(h);r=iniciar_main(h,a.json()['id_consentimiento']);assert r.status_code==201
    ik=r.json()['id_intento'];q=h.escenas[0]['preguntas'][0]
    assert h.main.post(f'/api/v1/attempts/{ik}/decisions/{q["id"]}',headers=h.titular.headers,json={'id_opcion':q['opciones'][0]['id']}).status_code==201
    from app.modules.participation.api.dependencies import obtener_reloj_escenario
    app.dependency_overrides[obtener_reloj_escenario]=lambda:SimpleNamespace(ahora=lambda:h.ahora+timedelta(minutes=30))
    p=h.main.get(f'/api/v1/attempts/{ik}/progress',headers=h.titular.headers);assert p.status_code==200 and p.json()['intento']['estado']=='VENCIDO'
    assert h.main.post(f'/api/v1/attempts/{ik}/finish',headers=h.titular.headers).status_code==200
    with h.sesiones() as s:assert s.get(I,ik).estado=='VENCIDO'
