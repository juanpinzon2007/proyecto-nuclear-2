"""B: primer registro real por main; selección inmutable y transacción existente."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.integration.test_main_current_scenario import principal,integracion,autor,pg_autoria,payload_valido  # noqa: F401
from tests.integration.test_current_scenario_http import snapshot


def pregunta(h):return h.principal.get(h.path,headers=h.main_headers).json()['pregunta']
def ruta(h,q):return f"/api/v1/attempts/{h.ik}/decisions/{q['id']}"
def responder(h,q,indice=0,**kw):return h.principal.post(ruta(h,q),headers=kw.get('headers',h.main_headers),json={'id_opcion':q['opciones'][indice]['id']})


def test_primer_registro_inmutable_progreso_y_siguiente_escenario_main(principal):
    h=principal;q=pregunta(h);assert responder(h,q).status_code==201
    antes=snapshot(h,h.ik)
    assert responder(h,q,1).status_code==409
    assert responder(h,q).status_code==409
    assert h.principal.put(ruta(h,q),headers=h.main_headers,json={'id_opcion':q['opciones'][1]['id']}).status_code==405
    assert snapshot(h,h.ik)==antes
    p=h.principal.get(f'/api/v1/attempts/{h.ik}/progress',headers=h.main_headers).json()
    assert p['respondidas']==1 and p['selecciones'][0]['id_opcion']==q['opciones'][0]['id']
    assert h.principal.get(h.path,headers=h.main_headers).json()['id_escenario']==h.escenas[1]['id']


@pytest.mark.parametrize('problema,codigo',[('anonimo',401),('ajeno',403),('matricula',403),
    ('retirada',403),('sesion_finalizada',403),('fuera_horario',403),('sin_zona',503),
    ('pregunta_futura',403),('opcion_ajena',403),('cerrado',409),('vencido',409)])
def test_registro_rechazado_sin_selecciones(principal,monkeypatch,problema,codigo):
    h=principal;q=pregunta(h);headers=h.main_headers
    if problema=='anonimo':headers={}
    elif problema=='ajeno':headers=h.headers_ajeno
    elif problema=='sin_zona':monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE');get_settings.cache_clear()
    elif problema=='pregunta_futura':q=h.escenas[1]['preguntas'][0]
    elif problema=='opcion_ajena':q=q|{'opciones':h.escenas[2]['preguntas'][0]['opciones']}
    elif problema=='vencido':
        ahora=h.reloj.ahora();h.reloj.ahora=lambda:ahora+timedelta(minutes=30)
    elif problema=='cerrado':assert h.client.post(f'/api/v1/attempts/{h.ik}/finish',headers=h.headers).status_code==200
    else:
        with h.sesiones.begin() as s:
            if problema=='matricula':s.get(GrupoEstudianteORM,h.matricula).activo=False
            elif problema=='retirada':s.get(ConvocatoriaModel,h.convocatoria).estado='RETIRADA'
            elif problema=='sesion_finalizada':s.get(SesionProgramadaModel,h.sesion).estado='FINALIZADO'
            else:s.get(SesionProgramadaModel,h.sesion).fecha_inicio+=timedelta(minutes=2)
    antes=snapshot(h,h.ik);r=responder(h,q,headers=headers);despues=snapshot(h,h.ik)
    assert r.status_code==codigo and despues[1]==[]
    if problema=='vencido':assert despues[0][0].estado=='VENCIDO'  # Semántica existente del comando, NO del GET.
    else:assert despues==antes


def test_registros_concurrentes_conservan_una_sola_seleccion(principal):
    h=principal;q=pregunta(h);b=Barrier(2)
    def enviar(i):b.wait(timeout=10);return responder(h,q,i)
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(enviar,(0,1)))
    assert sorted(r.status_code for r in rs)==[201,409]
    filas=snapshot(h,h.ik)[1];assert len(filas)==1
    assert str(filas[0].id_opcion) in {o['id'] for o in q['opciones']}


def test_fallo_tras_insert_revierte_y_permite_reintento(principal,monkeypatch):
    h=principal;q=pregunta(h);antes=snapshot(h,h.ik);original=RepositorioParticipacionSQLAlchemy.guardar_intento
    def fallo(self,*args,**kw):original(self,*args,**kw);raise RuntimeError('Fallo controlado posterior al INSERT')
    with monkeypatch.context() as m:
        m.setattr(RepositorioParticipacionSQLAlchemy,'guardar_intento',fallo)
        assert responder(h,q).status_code==500
    assert snapshot(h,h.ik)==antes
    assert responder(h,q).status_code==201
