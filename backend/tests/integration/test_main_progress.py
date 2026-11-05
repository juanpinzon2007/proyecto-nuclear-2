"""A: progreso puro de app.main con JWT/SQL reales, estado efectivo no persistido."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event

from app.core.config import get_settings
from app.db.session import get_engine
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel
from tests.integration.test_main_current_scenario import principal, integracion, autor, pg_autoria, payload_valido  # noqa: F401
from tests.integration.test_current_scenario_http import snapshot, publicar_segunda_edicion_y_archivar


def url(h): return f'/api/v1/attempts/{h.ik}/progress'


@pytest.mark.parametrize('estado', ['activo','vencido','finalizado'])
def test_progreso_efectivo_repetido_sin_dml_flush_commit(principal,estado,record_property):
    h=principal
    if estado=='vencido':
        ahora=h.reloj.ahora();h.reloj.ahora=lambda:ahora+timedelta(minutes=30)
    elif estado=='finalizado':
        assert h.client.post(f'/api/v1/attempts/{h.ik}/finish',headers=h.headers).status_code==200
    antes=snapshot(h,h.ik);engine=get_engine();operaciones=[]
    def sql(conn,cursor,statement,params,context,executemany):
        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','MERGE')):operaciones.append('DML')
    def commit(conn):operaciones.append('COMMIT')
    event.listen(engine,'before_cursor_execute',sql);event.listen(engine,'commit',commit)
    # Control de flush sobre las Session reales del engine principal.
    from sqlalchemy.orm import Session
    def flush(s,context,instances):
        if s.get_bind() is engine:operaciones.append('FLUSH')
    event.listen(Session,'before_flush',flush)
    try:
        a=h.principal.get(url(h),headers=h.main_headers);b=h.principal.get(url(h),headers=h.main_headers)
    finally:
        event.remove(engine,'before_cursor_execute',sql);event.remove(engine,'commit',commit);event.remove(Session,'before_flush',flush)
    assert a.status_code==b.status_code==200 and a.json()==b.json()
    assert operaciones==[] and snapshot(h,h.ik)==antes
    esperado={'activo':'EN_CURSO','vencido':'VENCIDO','finalizado':'FINALIZADO'}[estado]
    assert a.json()['intento']['estado']==esperado
    if estado=='vencido':
        assert antes[0][0].estado=='EN_CURSO' and antes[0][0].fin is None
        assert a.json()['intento']['fin']==a.json()['intento']['vence_en']
    assert a.headers['cache-control']=='no-store'
    for k in ('nota','justificacion','rubrica','puntaje',h.codigo,h.escenas[1]['preguntas'][0]['id'],h.escenas[2]['preguntas'][0]['id']):assert k not in a.text
    record_property('progreso_'+estado,a.text)


@pytest.mark.parametrize('problema,codigo',[('anonimo',401),('ajeno',403),('retirada',403),('matricula',403),('sin_zona',503)])
def test_progreso_privado_revalida_autoridad_y_configuracion(principal,monkeypatch,problema,codigo):
    h=principal;headers=h.main_headers
    if problema=='anonimo':headers={}
    elif problema=='ajeno':headers=h.headers_ajeno
    elif problema=='sin_zona':monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE');get_settings.cache_clear()
    else:
        with h.sesiones.begin() as s:
            if problema=='retirada':s.get(ConvocatoriaModel,h.convocatoria).estado='RETIRADA'
            else:s.get(GrupoEstudianteORM,h.matricula).activo=False
    antes=snapshot(h,h.ik);r=h.principal.get(url(h),headers=headers)
    assert r.status_code==codigo and snapshot(h,h.ik)==antes


def test_progreso_historico_tras_responder_y_lecturas_concurrentes(principal):
    h=principal
    q=h.principal.get(h.path,headers=h.main_headers).json()['pregunta']
    assert h.client.post(f"/api/v1/attempts/{h.ik}/decisions/{q['id']}",headers=h.headers,json={'id_opcion':q['opciones'][0]['id']}).status_code==201
    publicar_segunda_edicion_y_archivar(h)
    antes=snapshot(h,h.ik);barrera=Barrier(2)
    def consultar(_):
        barrera.wait(timeout=10);return h.principal.get(url(h),headers=h.main_headers)
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(consultar,range(2)))
    assert all(r.status_code==200 for r in rs) and rs[0].json()==rs[1].json()
    body=rs[0].json();assert body['respondidas']==1 and body['selecciones']==[{'id_decision':q['id'],'id_opcion':q['opciones'][0]['id']}]
    assert body['pendientes']==[h.escenas[1]['preguntas'][0]['id']]
    assert h.escenas[2]['preguntas'][0]['id'] not in rs[0].text
    assert snapshot(h,h.ik)==antes
