"""C: cierre principal y recorrido vertical; nunca calcula/publica una nota."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
import json

import pytest
from sqlalchemy import select,func,event
from app.core.config import get_settings
from app.db.session import get_engine
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from tests.integration.test_main_current_scenario import principal,integracion,autor,pg_autoria,payload_valido  # noqa: F401
from tests.integration.test_main_decisions import pregunta,responder
from tests.integration.test_current_scenario_http import snapshot


def ruta(h):return f'/api/v1/attempts/{h.ik}/finish'
def cerrar(h,headers=None):return h.principal.post(ruta(h),headers=h.main_headers if headers is None else headers)


def test_vertical_principal_escenario_progreso_respuestas_fin_sin_notas(principal,record_property):
    h=principal;pasos=[]
    def observar(nombre,r,codigo):
        assert r.status_code==codigo,nombre
        pasos.append({'paso':nombre,'http':r.status_code});return r
    for i in range(2):
        r=observar('escenario actual',h.principal.get(h.path,headers=h.main_headers),200)
        q=r.json()['pregunta']
        p=observar('progreso puro',h.principal.get(f'/api/v1/attempts/{h.ik}/progress',headers=h.main_headers),200)
        assert p.json()['respondidas']==i
        observar('primera selección',responder(h,q),201)
    terminal=observar('FIN del recorrido',h.principal.get(h.path,headers=h.main_headers),200)
    assert terminal.json()['recorrido_finalizado'] and terminal.json()['pregunta'] is None
    antes=snapshot(h,h.ik)
    fin=observar('cierre',cerrar(h),200);assert fin.json()['estado']=='FINALIZADO'
    assert observar('cierre idempotente',cerrar(h),200).json()==fin.json()
    assert snapshot(h,h.ik)[1]==antes[1] and len(antes[1])==2
    p=observar('progreso cerrado',h.principal.get(f'/api/v1/attempts/{h.ik}/progress',headers=h.main_headers),200)
    assert p.json()['intento']['estado']=='FINALIZADO' and p.json()['pendientes']==[]
    observar('escenario cerrado',h.principal.get(h.path,headers=h.main_headers),409)
    observar('resultados no expuestos',h.principal.get(f'/api/v1/participations/1/attempts/{h.ik}/result',headers=h.main_headers),404)
    with h.sesiones() as s:assert s.scalar(select(func.count()).select_from(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento==h.ik))==0
    record_property('vertical_main',json.dumps(pasos))


def test_cierre_confirma_vencimiento_que_get_no_persistio(principal):
    h=principal;ahora=h.reloj.ahora();h.reloj.ahora=lambda:ahora+timedelta(minutes=30)
    p=h.principal.get(f'/api/v1/attempts/{h.ik}/progress',headers=h.main_headers)
    assert p.json()['intento']['estado']=='VENCIDO' and snapshot(h,h.ik)[0][0].estado=='EN_CURSO'
    r=cerrar(h);assert r.status_code==200 and r.json()['estado']=='VENCIDO'
    assert r.json()['fin']==r.json()['vence_en']
    despues=snapshot(h,h.ik);assert despues[0][0].estado=='VENCIDO' and despues[1]==[]
    assert cerrar(h).json()==r.json() and snapshot(h,h.ik)==despues


@pytest.mark.parametrize('problema,codigo',[('anonimo',401),('ajeno',403),('retirada',403),('matricula',403),('sin_zona',503)])
def test_cierre_no_concede_autorizacion_implicita(principal,monkeypatch,problema,codigo):
    h=principal;headers=h.main_headers
    if problema=='anonimo':headers={}
    elif problema=='ajeno':headers=h.headers_ajeno
    elif problema=='sin_zona':monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE');get_settings.cache_clear()
    else:
        with h.sesiones.begin() as s:
            if problema=='retirada':s.get(ConvocatoriaModel,h.convocatoria).estado='RETIRADA'
            else:s.get(GrupoEstudianteORM,h.matricula).activo=False
    antes=snapshot(h,h.ik);assert cerrar(h,headers).status_code==codigo and snapshot(h,h.ik)==antes


def test_cierres_concurrentes_un_update_idempotente(principal):
    h=principal;b=Barrier(2);updates=[];engine=get_engine()
    def sql(conn,cursor,statement,params,context,executemany):
        if statement.lstrip().upper().startswith('UPDATE INTENTO '):updates.append(1)
    event.listen(engine,'after_cursor_execute',sql)
    def enviar(_):b.wait(timeout=10);return cerrar(h)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(enviar,range(2)))
    finally:event.remove(engine,'after_cursor_execute',sql)
    assert all(r.status_code==200 for r in rs) and rs[0].json()==rs[1].json()
    assert len(updates)==1


def test_respuesta_y_cierre_concurrentes_no_pierden_selecciones(principal):
    h=principal;q=pregunta(h);b=Barrier(2)
    def respuesta():b.wait(timeout=10);return responder(h,q)
    def fin():b.wait(timeout=10);return cerrar(h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(respuesta);f=pool.submit(fin);r,c=a.result(timeout=20),f.result(timeout=20)
    assert c.status_code==200 and r.status_code in (201,409)
    estado,pasos=snapshot(h,h.ik)
    assert estado[0].estado=='FINALIZADO' and len(pasos)==(1 if r.status_code==201 else 0)


def test_cierre_rollback_tras_update_preserva_intento(principal,monkeypatch):
    h=principal;antes=snapshot(h,h.ik);original=RepositorioParticipacionSQLAlchemy.guardar_intento
    def fallo(self,*a,**kw):original(self,*a,**kw);raise RuntimeError('Fallo controlado después de UPDATE')
    with monkeypatch.context() as m:
        m.setattr(RepositorioParticipacionSQLAlchemy,'guardar_intento',fallo)
        assert cerrar(h).status_code==500
    assert snapshot(h,h.ik)==antes
    assert cerrar(h).status_code==200
