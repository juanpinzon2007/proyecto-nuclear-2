"""Ciclo oficial HTTP/JWT/PG17; preparación administrativa exclusivamente sintética."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S,NotificacionModel as N,EventoAuditoriaModel as E
from app.modules.participation.infrastructure.academic_results_models import AusenciaAcademicaModel as Aus,PublicacionEvaluacionModel as Pub,ResultadoParticipacionModel as RP
from app.modules.participation.infrastructure.models import ParticipacionModel as P,IntentoModel as I
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM as Extra
from tests.integration.test_main_technical_results import c,crear_registro,pg_resultados,docente_http,revision,lectura,guardar
from tests.integration.test_evaluation_readiness import otro_convocado,cerrar_sesion_fixture


def base(h):return f'/scheduling/sesiones/{h.c.sesion}/evaluacion'
def consultar(h):return h.client.get(base(h)+'/consolidacion',headers=h.auth['docente'])
def preparar(h):
    guardar(h.c);cerrar_sesion_fixture(h.c)
    r=consultar(h);assert r.status_code==200,r.text
    return r.json()
def publicar(h,revision):return h.client.post(base(h)+'/publicaciones',headers=h.auth['docente'],json={'revision_sha256':revision['revision_sha256']})
def ausencia(h,cid,**kwargs):return h.client.post(base(h)+f'/convocatorias/{cid}/ausencia',headers=h.auth['docente'],json={'motivo':'Confirmación expresa en laboratorio por el docente.'},**kwargs)
def propio(h):return f"/scheduling/convocatorias/{h.c.datos['convocatoria_id']}/resultado"
def cuenta(c,modelo):
    with c.sesiones() as s:return s.scalar(sa.select(sa.func.count()).select_from(modelo))


def test_publicacion_explicita_idempotente_y_lectura_privada(docente_http):
    h=docente_http;r=preparar(h);assert r['publicable'] is True
    n=cuenta(h.c,Pub)
    resp=publicar(h,r);assert resp.status_code==200,resp.text
    j=resp.json();assert j['oficial'] is True and j['version']==1
    assert j['resultados'][0]['nota']=='33.33'
    assert publicar(h,r).json()['id']==j['id'] and cuenta(h.c,Pub)==n+1
    with lectura(h):
        leido=h.client.get(propio(h),headers=h.auth['estudiante'])
        docente=h.client.get(base(h)+'/publicaciones',headers=h.auth['docente'])
    assert leido.status_code==docente.status_code==200
    assert leido.json()['oficial'] is True and leido.json()['nota']=='33.33'
    with h.c.sesiones() as s:
        ns=s.scalars(sa.select(N).where(N.publicacion_evaluacion_id==j['id'])).all()
        assert len(ns)==1 and str(ns[0].destinatario_id)==str(s.get(__import__('app.modules.scheduling.infrastructure.models',fromlist=['ConvocatoriaModel']).ConvocatoriaModel,h.c.datos['convocatoria_id']).estudiante_id)
        assert ns[0].canal=='INTERNA' and '33.33' not in ns[0].mensaje


def test_ausencia_explicita_sin_participacion_ni_intento_rectificacion_historica(docente_http):
    h=docente_http;cid=otro_convocado(h.c);r=preparar(h)
    assert not r['publicable'] and publicar(h,r).status_code==409
    p,i=cuenta(h.c,P),cuenta(h.c,I)
    a=ausencia(h,cid);assert a.status_code==200,a.text
    assert a.json()['nota']=='0.00' and a.json()['oficial'] is False
    assert ausencia(h,cid).json()['id']==a.json()['id']
    assert (cuenta(h.c,P),cuenta(h.c,I))==(p,i)
    r=consultar(h).json();assert r['publicable']
    pub=publicar(h,r);assert pub.status_code==200,pub.text
    datos={'id_confirmacion':a.json()['id'],'motivo':'Rectificación explícita documentada LAB.'}
    rr=h.client.post(base(h)+f'/convocatorias/{cid}/ausencia/rectificacion',headers=h.auth['docente'],json=datos)
    assert rr.status_code==200,rr.text
    assert rr.json()['confirmada'] is False and rr.json()['revision']==2
    assert consultar(h).json()['publicable'] is False
    anterior=h.client.get(base(h)+'/publicaciones',headers=h.auth['docente'])
    assert anterior.status_code==200 and anterior.json()['id']==pub.json()['id']
    assert publicar(h,consultar(h).json()).status_code==409


def test_retirada_excluida_y_antecedente_conservado(docente_http):
    h=docente_http;cid=otro_convocado(h.c,retirado=True);r=preparar(h)
    assert r['publicable'] and str(cid) in r['retiradas'] and len(r['filas'])==1
    p=publicar(h,r);assert p.status_code==200,p.text
    assert str(cid) in p.json()['retiradas'] and len(p.json()['resultados'])==1


@pytest.mark.parametrize('actor,estado',[('ajeno',403),('estudiante',403),('admin',403),('anonimo',401)])
def test_publicacion_y_ausencia_requieren_docente_titular(docente_http,actor,estado):
    h=docente_http;r=preparar(h);auth=h.auth.get(actor,{})
    for method,path,body in [('get','/consolidacion',None),('post','/publicaciones',{'revision_sha256':r['revision_sha256']}),('put','/visibilidad',{'mostrar_provisional':True})]:
        resp=getattr(h.client,method)(base(h)+path,headers=auth,**({'json':body} if body else {}))
        assert resp.status_code==estado,resp.text


def test_provisional_configurable_sin_correctas_durante_sesion_activa(docente_http):
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as s:s.get(S,h.c.sesion).estado='EN_CURSO'
    assert h.client.get(propio(h),headers=h.auth['estudiante']).status_code==404
    v=h.client.put(base(h)+'/visibilidad',headers=h.auth['docente'],json={'mostrar_provisional':True});assert v.status_code==200,v.text
    with lectura(h):r=h.client.get(propio(h),headers=h.auth['estudiante'])
    assert r.status_code==200,r.text
    assert r.json()['nota']=='33.33' and r.json()['oficial'] is False and r.json()['explicaciones']==[]
    assert not any(x in r.text for x in ('es_correcta','justificacion','clave_hash','@'))
    assert h.client.get(propio(h).replace(str(h.c.datos['convocatoria_id']),str(uuid4())),headers=h.auth['estudiante']).status_code==403
    cerrar_sesion_fixture(h.c)
    r=h.client.get(propio(h),headers=h.auth['estudiante']);assert r.status_code==200,r.text
    assert r.json()['explicaciones'] and 'es_correcta' in r.text


def test_publicaciones_concurrentes_no_duplican_efectos(docente_http):
    h=docente_http;r=preparar(h)
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:publicar(h,r),range(2)))
    assert [x.status_code for x in rs]==[200,200],[x.text for x in rs]
    assert rs[0].json()['id']==rs[1].json()['id']
    with h.c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(Pub).where(Pub.sesion_id==h.c.sesion))==1
        assert s.scalar(sa.select(sa.func.count()).select_from(N).where(N.publicacion_evaluacion_id==rs[0].json()['id']))==1


def test_fallo_aviso_revierte_publicacion_y_auditoria(docente_http,monkeypatch):
    h=docente_http;r=preparar(h)
    import app.modules.participation.infrastructure.academic_cycle as mod
    def fallar(s,**kw):s.execute(sa.text('SELECT 1/0'))
    monkeypatch.setattr(mod,'crear_notificacion',fallar)
    n=cuenta(h.c,Pub);e=cuenta(h.c,E)
    resp=publicar(h,r);assert resp.status_code==503,resp.text
    assert cuenta(h.c,Pub)==n and cuenta(h.c,E)==e


def test_publicacion_inmutable_y_revision_obsoleta(docente_http):
    h=docente_http;r=preparar(h)
    assert publicar(h,dict(r,revision_sha256='0'*64)).status_code==409
    pub=publicar(h,r);assert pub.status_code==200,pub.text
    for sql in ('UPDATE publicacion_evaluacion SET version=version+1 WHERE id=:id','DELETE FROM publicacion_evaluacion WHERE id=:id'):
        with pytest.raises(DBAPIError):
            with h.c.sesiones.begin() as s:s.execute(sa.text(sql),{'id':pub.json()['id']})


def test_repeticion_http_reutiliza_permiso_nativo_idempotente(docente_http):
    h=docente_http
    with h.c.sesiones.begin() as s:s.get(S,h.c.sesion).estado='EN_CURSO'
    body={'id_sesion':str(h.c.sesion),'id_estudiante':str(h.c.alumno)}
    path='/api/v1/identity/excepciones/repeticiones'
    r=h.client.post(path,headers=h.auth['docente'],json=body);assert r.status_code==201,r.text
    j=r.json();assert j['id_permiso_extra']>0
    r2=h.client.post(path,headers=h.auth['docente'],json=body);assert r2.status_code==201,r2.text
    assert r2.json()['id_permiso_extra']==j['id_permiso_extra']
    assert r2.json()['fecha_autorizacion']==j['fecha_autorizacion']
    with h.c.sesiones() as s:
        p=s.get(Extra,j['id_permiso_extra']);assert p.id_participacion==h.c.pk and p.cantidad_autorizada==1
    assert h.client.post(path,headers=h.auth['ajeno'],json=body).status_code==403


def test_mejor_nota_misma_participacion_no_mezcla_otro_caso(docente_http,crear_registro):
    from copy import copy
    from tests.integration.test_participation_persistence import intento
    from tests.integration.test_question_result_storage import cerrar
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as ses:ses.get(S,h.c.sesion).estado='EN_CURSO'
    permiso=h.client.post('/api/v1/identity/excepciones/repeticiones',headers=h.auth['docente'],json={'id_sesion':str(h.c.sesion),'id_estudiante':str(h.c.alumno)})
    assert permiso.status_code==201,permiso.text
    extra=copy(h.c);extra.ik=intento(extra,extra.pk,numero_intento=2,id_permiso_extra=permiso.json()['id_permiso_extra'])
    cerrar(extra,respondidas=3);guardar(extra)
    ajeno=crear_registro();cerrar(ajeno,cero=True,rama=1);guardar(ajeno)
    cerrar_sesion_fixture(h.c)
    revision=consultar(h).json();assert revision['publicable']
    assert len(revision['filas'])==1 and revision['filas'][0]['nota']=='100.00'
    assert len(revision['filas'][0]['intentos'])==2
    pub=publicar(h,revision);assert pub.status_code==200,pub.text
    assert pub.json()['resultados'][0]['nota']=='100.00'
    with pytest.raises(DBAPIError):
        intento(extra,extra.pk,numero_intento=3,id_permiso_extra=permiso.json()['id_permiso_extra'])


def test_ausencia_concurrente_y_negativa_con_intento(docente_http):
    h=docente_http;cid=otro_convocado(h.c);preparar(h)
    assert ausencia(h,h.c.datos['convocatoria_id']).status_code==409
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:ausencia(h,cid),range(2)))
    assert [r.status_code for r in rs]==[200,200],[r.text for r in rs]
    assert rs[0].json()['id']==rs[1].json()['id']
    with h.c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(Aus).where(Aus.convocatoria_id==cid))==1


def test_provisional_no_revela_resultados_con_intento_activo(docente_http):
    from copy import copy
    from tests.integration.test_participation_persistence import intento
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as s:
        s.get(S,h.c.sesion).estado='EN_CURSO'
        permiso=Extra(id_participacion=h.c.pk,id_profesor=h.c.docente,cantidad_autorizada=1,justificacion='Preparación administrativa LAB',fecha_autorizacion=__import__('tests.integration.test_participation_persistence',fromlist=['FECHA']).FECHA)
        s.add(permiso);s.flush();eid=permiso.id_permiso_extra
    intento(h.c,h.c.pk,numero_intento=2,id_permiso_extra=eid)
    v=h.client.put(base(h)+'/visibilidad',headers=h.auth['docente'],json={'mostrar_provisional':True});assert v.status_code==200,v.text
    r=h.client.get(propio(h),headers=h.auth['estudiante']);assert r.status_code==409 and 'nota' not in r.text


def test_migracion_real_subida_bajada_y_metadata_sin_filtro():
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from tests.identity.academic_identity_support import motor_postgresql_desechable,config_alembic
    from app.db.models import registrar_modelos_integrados
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),'20261107_question_results')
            anteriores=set(sa.inspect(s).get_table_names())
            command.upgrade(config_alembic(s),'head')
            assert set(sa.inspect(s).get_table_names())-anteriores=={'ausencia_academica','publicacion_evaluacion','resultado_participacion','despacho_correo'}
            assert compare_metadata(MigrationContext.configure(s),registrar_modelos_integrados())==[]
            command.downgrade(config_alembic(s),'20261107_question_results')
            assert set(sa.inspect(s).get_table_names())==anteriores
            command.upgrade(config_alembic(s),'head')
            assert compare_metadata(MigrationContext.configure(s),registrar_modelos_integrados())==[]


def test_downgrade_rechaza_perdida_de_publicacion(docente_http):
    from alembic import command
    from tests.identity.academic_identity_support import config_alembic
    h=docente_http;r=publicar(h,preparar(h));assert r.status_code==200,r.text
    with pytest.raises(RuntimeError,match='historia'):
        with h.c.engine.begin() as s:command.downgrade(config_alembic(s),'20261107_question_results')
    assert h.client.get(base(h)+'/publicaciones',headers=h.auth['docente']).json()['id']==r.json()['id']


def test_recorrido_tcp_reproducible_para_postman(monkeypatch,record_property):
    from contextlib import ExitStack
    from pathlib import Path
    import secrets,httpx
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/'docs'/'postman'))
    import laboratorio_publicacion as lab
    valores={k:secrets.token_urlsafe(32) for k in ('clave_docente','codigo_estudiante')}
    with ExitStack() as stack:
        h,rec=lab.preparar(valores,stack)
        from app.main import app
        port=lab.lab.serve(app,0,stack)
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=30) as client:
            d=client.post('/api/v1/identity/auth/personal',json={'correo':rec['correo_docente'],'clave':valores['clave_docente']});assert d.status_code==200
            a=client.post('/api/v1/identity/auth/personal',json={'correo':rec['correo_docente_ajeno'],'clave':valores['clave_docente']});assert a.status_code==200
            e=client.post('/api/v1/identity/auth/estudiantes',json={'correo':rec['correo_estudiante'],'codigo_convocatoria':valores['codigo_estudiante']});assert e.status_code==200
            dh={'Authorization':'Bearer '+d.json()['access_token']};eh={'Authorization':'Bearer '+e.json()['access_token']}
            r=client.get(base(h)+'/consolidacion',headers=dh);assert r.status_code==200 and r.json()['publicable']
            body={'revision_sha256':r.json()['revision_sha256']}
            p=client.post(base(h)+'/publicaciones',headers=dh,json=body);assert p.status_code==200,p.text
            assert client.post(base(h)+'/publicaciones',headers=dh,json=body).json()['id']==p.json()['id']
            j=client.get(propio(h),headers=eh);assert j.status_code==200 and j.json()['nota']=='33.33' and j.json()['oficial'] is True
            assert client.get(base(h)+'/publicaciones',headers={'Authorization':'Bearer '+a.json()['access_token']}).status_code==403
            assert client.get(base(h)+'/publicaciones').status_code==401
            record_property('evidencia_tcp','Login docente/estudiante 200; revisión 200; publicación 200; replay mismo ID; titular 33.33 oficial; ajeno 403; anónimo 401. Fixtures administrativas LAB explícitas.')


@pytest.mark.parametrize('cupo_base',[1,2])
def test_repeticion_historica_sin_permiso_no_se_publica(docente_http,cupo_base):
    from copy import copy
    from tests.integration.test_participation_persistence import intento
    from tests.integration.test_question_result_storage import cerrar
    h=docente_http;guardar(h.c)
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
    with h.c.sesiones.begin() as ses:ses.get(A,h.c.datos['id_asignacion']).intentos_base=cupo_base
    extra=copy(h.c);extra.ik=intento(extra,extra.pk,numero_intento=2)
    cerrar(extra);guardar(extra);cerrar_sesion_fixture(h.c)
    r=consultar(h);assert r.status_code==200,r.text
    assert r.json()['publicable'] is False and any(x['codigo']=='REPETICION_SIN_AUTORIZACION_VERIFICABLE' for x in r.json()['pendientes'])
    assert publicar(h,r.json()).status_code==409
