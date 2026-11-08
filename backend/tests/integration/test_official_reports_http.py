"""RF-16 en app.main, JWT real y PG17 desechable; sin notas sintéticas."""
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from decimal import Decimal
from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4
import pytest
import sqlalchemy as sa
from openpyxl import load_workbook
from pypdf import PdfReader
from app.modules.identity.infrastructure.models import UsuarioORM as U
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S
from tests.integration.test_main_technical_results import c, crear_registro, pg_resultados, docente_http, revision, lectura, guardar
from tests.integration.test_academic_cycle_http import preparar, publicar, consultar, ausencia, otro_convocado, base, cuenta
from tests.integration.test_evaluation_readiness import cerrar_sesion_fixture
from app.modules.participation.infrastructure.academic_results_models import PublicacionEvaluacionModel as Pub, ResultadoParticipacionModel as RP


def ruta(h):
    return f'/api/v1/identity/seguimiento/sesiones/{h.c.sesion}/reporte'


def descargar(h,formato='xlsx',actor='docente',**params):
    return h.client.get(ruta(h),params={'formato':formato,**params},headers=h.auth.get(actor,{}))


def oficial(h):
    p=publicar(h,preparar(h));assert p.status_code==200,p.text
    return p.json()


def filas(resp,hoja='Resultados'):
    assert resp.status_code==200,resp.text[:400] if resp.status_code!=200 else ''
    return list(load_workbook(BytesIO(resp.content),data_only=False)[hoja].values)


def texto(resp):
    assert resp.status_code==200,resp.text[:400] if resp.status_code!=200 else ''
    return '\n'.join(p.extract_text() for p in PdfReader(BytesIO(resp.content)).pages)


@pytest.mark.parametrize('formato',['xlsx','pdf'])
def test_exportacion_publicacion_real_solo_lectura_y_sesion_independiente(docente_http,formato):
    h=docente_http;p=oficial(h)
    with lectura(h) as config:
        r=descargar(h,formato)
    assert r.status_code==200,r.text[:200] if r.status_code!=200 else ''
    assert config and all(x==('REPEATABLE READ','on') for x in config)
    assert r.headers['x-publicacion-id']==p['id'] and r.headers['x-publicacion-version']=='1'
    assert r.headers['x-publicacion-sha256']==p['revision_sha256']
    assert r.headers['cache-control']=='no-store' and r.headers['x-content-type-options']=='nosniff'
    assert r.headers['content-disposition'].endswith(f'.{formato}"')
    if formato=='xlsx':
        assert r.content[:2]==b'PK'
        rows=filas(r);assert len(rows)==2 and Decimal(str(rows[1][7]))==Decimal('33.33')
        assert rows[1][6]=='PARCIAL' and rows[1][8]==1
        wb=load_workbook(BytesIO(r.content));assert wb['Intentos']['G2'].number_format=='yyyy-mm-dd hh:mm:ss'
        its=filas(r,'Intentos');assert len(its)==2 and its[1][3]==h.c.ik
        assert its[1][6] is not None and its[1][7]>its[1][6]
        assert Decimal(str(its[1][8]))==Decimal('1800.000001')
    else:
        assert r.content.startswith(b'%PDF-')
        t=texto(r);assert '33.33' in t and 'PARCIAL' in t and p['id'] in t
    with h.c.sesiones() as s:
        assert s.get(Pub,p['id']).fuente_sha256==p['revision_sha256']
        assert s.scalar(sa.select(sa.func.count()).select_from(RP).where(RP.publicacion_id==p['id']))==1
    out=os.getenv('SPS_EVIDENCIA_RESULTADOS_DIR')
    if out:Path(out,f'reporte_oficial.{formato}').write_bytes(r.content)


def test_ausencia_cero_y_retirada_sin_notas_ni_intentos(docente_http):
    h=docente_http;cid=otro_convocado(h.c);ret=otro_convocado(h.c,retirado=True)
    preparar(h);assert ausencia(h,cid).status_code==200
    p=publicar(h,consultar(h).json());assert p.status_code==200,p.text
    r=descargar(h);rows=filas(r);assert len(rows)==3
    aus=next(x for x in rows[1:] if x[6]=='AUSENTE')
    assert aus[4]==str(cid) and aus[5] is None and aus[7]==0 and aus[8]==0 and aus[10]
    assert filas(r,'Antecedentes')[1]==(str(ret),'RETIRADA',None)
    assert len(filas(r,'Intentos'))==2
    t=texto(descargar(h,'pdf'));assert str(ret) in t and 'AUSENTE' in t and '0.00' in t


def test_maximo_de_repeticion_publicado_y_no_resultado_ajeno(docente_http,crear_registro):
    from tests.integration.test_participation_persistence import intento
    from tests.integration.test_question_result_storage import cerrar
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as s:s.get(S,h.c.sesion).estado='EN_CURSO'
    permiso=h.client.post('/api/v1/identity/excepciones/repeticiones',headers=h.auth['docente'],json={
        'id_sesion':str(h.c.sesion),'id_estudiante':str(h.c.alumno)})
    assert permiso.status_code==201
    extra=copy(h.c);extra.ik=intento(extra,extra.pk,numero_intento=2,id_permiso_extra=permiso.json()['id_permiso_extra'])
    cerrar(extra,respondidas=3);guardar(extra)
    ajeno=crear_registro();cerrar(ajeno,cero=True,rama=1);guardar(ajeno)
    cerrar_sesion_fixture(h.c);p=publicar(h,consultar(h).json());assert p.status_code==200,p.text
    r=descargar(h);rows=filas(r)
    assert len(rows)==2 and rows[1][7]==100 and rows[1][8]==2
    assert {x[3] for x in filas(r,'Intentos')[1:]}=={h.c.ik,extra.ik}
    assert '100.00' in texto(descargar(h,'pdf'))


@pytest.mark.parametrize('actor,status',[('ajeno',403),('estudiante',403),('admin',403),('anonimo',401)])
def test_rechazo_fuera_ambito_no_exporta(docente_http,actor,status):
    h=docente_http;oficial(h)
    for formato in ('xlsx','pdf'):
        with lectura(h):r=descargar(h,formato,actor)
        assert r.status_code==status,r.text
        assert 'attachment' not in r.headers.get('content-disposition','')


def test_jwt_invalido_y_cuenta_inactiva(docente_http):
    h=docente_http;oficial(h)
    r=h.client.get(ruta(h)+'?formato=xlsx',headers={'Authorization':'Bearer invalido'})
    assert r.status_code==401
    with h.c.sesiones.begin() as s:s.get(U,h.c.docente).activo=False
    assert descargar(h).status_code==401


def test_sin_publicacion_tecnico_no_se_exporta(docente_http):
    h=docente_http;preparar(h)
    with lectura(h):r=descargar(h)
    assert r.status_code==404 and 'application/json' in r.headers['content-type']
    with h.c.sesiones() as db:assert db.scalar(sa.select(sa.func.count()).select_from(Pub).where(Pub.sesion_id==h.c.sesion))==0


def test_filtros_orden_vacio_y_referencias_ajenas(docente_http):
    h=docente_http;p=oficial(h);f=p['resultados'][0]['detalle']
    assert len(filas(descargar(h,id_grupo=f['grupo_id'],id_estudiante=[h.c.alumno],agrupar_por='estudiante')))==2
    assert len(filas(descargar(h,estado='AUSENTE')))==1
    assert 'No hay resultados' in texto(descargar(h,'pdf',estado='AUSENTE'))
    for q in ({'id_grupo':999999},{'id_estudiante':999999}):assert descargar(h,**q).status_code==403
    for q in ({'id_estudiante':0},{'estado':'APROBADO'},{'version_publicacion':0},{'docente_id':h.c.docente}):
        assert descargar(h,**q).status_code==422
    assert descargar(h,version_publicacion=99).status_code==404


def test_historico_no_cambia_tras_rectificacion_sin_republicar(docente_http):
    h=docente_http;cid=otro_convocado(h.c);preparar(h)
    a=ausencia(h,cid);assert a.status_code==200
    p=publicar(h,consultar(h).json());assert p.status_code==200
    original=filas(descargar(h))
    r=h.client.post(base(h)+f'/convocatorias/{cid}/ausencia/rectificacion',headers=h.auth['docente'],json={
        'id_confirmacion':a.json()['id'],'motivo':'Rectificación explícita de laboratorio.'})
    assert r.status_code==200 and not consultar(h).json()['publicable']
    assert filas(descargar(h))==original
    assert filas(descargar(h,version_publicacion=1))==original


def test_nombre_historico_formula_y_caracteres_no_se_interpretan(docente_http):
    h=docente_http
    nombre='=HYPERLINK("https://fixture.test","José Núñez & <LAB>")'
    with h.c.sesiones.begin() as s:s.get(U,h.c.alumno).nombre=nombre
    p=oficial(h);g=p['resultados'][0]['detalle']['grupo_id']
    with h.c.sesiones.begin() as s:
        s.get(U,h.c.alumno).nombre='Otro nombre actual LAB'
        s.get(G,g).nombre='Grupo cambiado LAB'
    r=descargar(h);wb=load_workbook(BytesIO(r.content));cell=wb['Resultados']['D2']
    assert cell.value==nombre and cell.data_type=='s' and cell.quotePrefix
    assert not any(c.data_type=='f' or c.hyperlink for ws in wb for row in ws for c in row)
    assert wb['Resultados']['B2'].value==p['resultados'][0]['detalle']['grupo_nombre']
    assert ''.join(nombre.split()) in ''.join(texto(descargar(h,'pdf')).split())


def test_consultas_concurrentes_y_fallo_exportador_no_alteran_publicacion(docente_http,monkeypatch):
    from app.modules.identity.infrastructure.report_exporters import ExportadorReportesOficiales
    h=docente_http;p=oficial(h)
    with lectura(h):
        with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:descargar(h),range(2)))
    assert all(x.status_code==200 for x in rs) and filas(rs[0])==filas(rs[1])
    def fallar(*args):raise RuntimeError('Información privada que nunca sale del exportador')
    monkeypatch.setattr(ExportadorReportesOficiales,'_xlsx',fallar)
    with lectura(h):r=descargar(h)
    assert r.status_code==503 and 'Información privada' not in r.text
    with h.c.sesiones() as db:assert db.scalar(sa.select(sa.func.count()).select_from(Pub).where(Pub.sesion_id==h.c.sesion))==1
    assert h.client.get(base(h)+'/publicaciones',headers=h.auth['docente']).json()['id']==p['id']


def test_pdf_multipagina_y_encabezados_repetidos(docente_http):
    h=docente_http;cids=[otro_convocado(h.c) for _ in range(55)]
    preparar(h)
    for cid in cids:assert ausencia(h,cid).status_code==200
    p=publicar(h,consultar(h).json());assert p.status_code==200,p.text
    r=descargar(h,'pdf');t=texto(r);pdf=PdfReader(BytesIO(r.content))
    assert len(pdf.pages)>=3
    for i,page in enumerate(pdf.pages,1):assert f'Página {i}' in page.extract_text()
    assert t.count('Estado')>=3 and all(str(cid) in t for cid in cids)
    assert len(filas(descargar(h)))==57
    out=os.getenv('SPS_EVIDENCIA_RESULTADOS_DIR')
    if out:Path(out,'reporte_multipagina.pdf').write_bytes(r.content)


@pytest.mark.parametrize('c',['completo','activo'],indirect=True)
def test_extremos_oficiales_sin_recalcular_al_exportar(docente_http,c):
    from tests.integration.test_question_result_storage import cerrar
    h=docente_http
    from app.modules.participation.infrastructure.models import IntentoModel as I
    with h.c.sesiones() as s:activo=s.get(I,h.c.ik).estado=='EN_CURSO'
    if activo:cerrar(h.c,cero=True,rama=1)
    p=oficial(h)
    esperado=Decimal('0.00') if activo else Decimal('100.00')
    assert Decimal(p['resultados'][0]['nota'])==esperado
    assert Decimal(str(filas(descargar(h))[1][7]))==esperado
    assert format(esperado,'.2f') in texto(descargar(h,'pdf'))


def test_republicacion_y_descarga_explicita_de_version_anterior(docente_http):
    h=docente_http;cid=otro_convocado(h.c);preparar(h)
    a=ausencia(h,cid);assert a.status_code==200
    p1=publicar(h,consultar(h).json());assert p1.status_code==200
    antigua=filas(descargar(h))
    rr=h.client.post(base(h)+f'/convocatorias/{cid}/ausencia/rectificacion',headers=h.auth['docente'],json={
        'id_confirmacion':a.json()['id'],'motivo':'Rectificación de antecedente LAB con trazabilidad.'})
    assert rr.status_code==200
    assert ausencia(h,cid).status_code==200
    p2=publicar(h,consultar(h).json());assert p2.status_code==200,p2.text
    assert p2.json()['version']==2 and p2.json()['id']!=p1.json()['id']
    assert descargar(h).headers['x-publicacion-id']==p2.json()['id']
    r=descargar(h,version_publicacion=1)
    assert r.headers['x-publicacion-id']==p1.json()['id'] and filas(r)==antigua


@pytest.mark.parametrize('zona',[None,'Zona/inexistente'])
def test_zona_obligatoria_cierre_seguro_sin_escrituras(docente_http,monkeypatch,zona):
    from app.core.config import get_settings
    h=docente_http;oficial(h)
    if zona is None:monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE',raising=False)
    else:monkeypatch.setenv('PARTICIPATION_TIMESTAMP_ZONE',zona)
    get_settings.cache_clear()
    with lectura(h):r=descargar(h)
    assert r.status_code==503 and 'attachment' not in r.headers.get('content-disposition','')


def test_fallo_sql_lectura_revierte_y_permita_recuperacion(docente_http,monkeypatch):
    from app.modules.participation.infrastructure.academic_cycle import CicloAcademicoSQL
    h=docente_http;p=oficial(h);anterior=CicloAcademicoSQL._publicada
    def fallar(self,s,pub):s.execute(sa.text('SELECT 1/0'))
    with monkeypatch.context() as patch:
        patch.setattr(CicloAcademicoSQL,'_publicada',fallar)
        with lectura(h):r=descargar(h)
        assert r.status_code==503
    with lectura(h):r=descargar(h)
    assert r.status_code==200 and r.headers['x-publicacion-id']==p['id']
