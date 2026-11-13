"""Comando docente PG17/JWT real. Finish se confirma antes y no depende del motor."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone,timedelta
from threading import Barrier
from uuid import uuid4
import pytest
import sqlalchemy as sa
from app.db.session import get_engine
from app.modules.participation.domain.clock import RelojSistema
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.identity.infrastructure.models import UsuarioORM as U
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S,NotificacionModel as N
from tests.integration.test_main_technical_results import c,crear_registro,pg_resultados,docente_http,revision,ruta  # noqa: F401
from tests.integration.test_question_result_storage import guardar,contar,cerrar
from tests.integration.test_evaluation_result_storage import evaluar
from tests.integration.test_participation_persistence import FECHA


def enviar(h):return h.client.post(ruta(h),headers=h.auth['docente'])
def estado(c):
    with c.sesiones() as s:
        i=s.get(I,c.ik);return i.estado,i.fin


@pytest.mark.parametrize('c',['activo'],indirect=True)
@pytest.mark.parametrize('rama,vencido',[(0,False),(1,False),(0,True)])
def test_finish_http_independiente_seguido_calculo_docente(docente_http,monkeypatch,rama,vencido):
    h=docente_http
    # Preparación académica explícita LAB. No acredita habilitación docente HTTP.
    with h.c.sesiones.begin() as s:s.get(S,h.c.sesion).estado='EN_CURSO'
    reloj=[FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=1)]
    monkeypatch.setattr(RelojSistema,'ahora',lambda self:reloj[0])
    base=f'/api/v1/attempts/{h.c.ik}'
    for i in range(1 if vencido else 3):
        q=h.client.get(base+'/current-scenario',headers=h.auth['estudiante'])
        assert q.status_code==200,q.text
        q=q.json()['pregunta'];o=q['opciones'][rama if i==0 else 0]
        r=h.client.post(base+'/decisions/'+q['id'],headers=h.auth['estudiante'],json={'id_opcion':o['id']})
        assert r.status_code==201,r.text
        reloj[0]+=timedelta(minutes=1)
    if vencido:reloj[0]=FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=31)
    fin=h.client.post(base+'/finish',headers=h.auth['estudiante'])
    assert fin.status_code==200,fin.text
    assert fin.json()['estado']==('VENCIDO' if vencido else 'FINALIZADO') and contar(h.c)==0
    antes=estado(h.c)
    r=enviar(h);assert r.status_code==200,r.text
    j=r.json();assert j['nota_final']==('33.33' if vencido else '100.00') and j['oficial'] is False
    assert j['modalidad']==('PARCIAL' if vencido else 'COMPLETA')
    assert j['version_caso_id']==str(h.c.version.id)
    assert enviar(h).json()==j and h.client.get(ruta(h),headers=h.auth['docente']).json()==j
    assert estado(h.c)==antes and contar(h.c)==1


def test_reintento_no_invoca_un_calculo_nuevo(docente_http,monkeypatch):
    h=docente_http;r=enviar(h);assert r.status_code==200,r.text
    from app.modules.participation.infrastructure.question_result_repository import DetallesPreguntasSQLAlchemy
    def no_recalcular(*args,**kw):raise AssertionError('No se vuelve a generar un resultado')
    monkeypatch.setattr(DetallesPreguntasSQLAlchemy,'preparar',no_recalcular)
    assert enviar(h).json()==r.json() and contar(h.c)==1


@pytest.mark.parametrize('etapa',['configuracion','detalle'])
def test_error_sql_rollback_y_recuperacion_conservan_cierre(docente_http,etapa):
    h=docente_http;antes=estado(h.c);e=get_engine();fallo=[False]
    def romper(conn,cursor,sql,*args):
        objetivo=('valoracion_opcion' in sql and sql.startswith('SELECT')) if etapa=='configuracion' else sql.startswith('INSERT INTO resultado_calculo_preguntas')
        if objetivo and not fallo[0]:
            fallo[0]=True;conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(e,'before_cursor_execute',romper)
    try:r=enviar(h)
    finally:sa.event.remove(e,'before_cursor_execute',romper)
    assert fallo[0] and r.status_code==503,r.text
    assert estado(h.c)==antes and contar(h.c)==0 and 'division' not in r.text
    r=enviar(h);assert r.status_code==200,r.text
    assert estado(h.c)==antes and contar(h.c)==1 and r.json()['oficial'] is False


def test_commit_exitoso_lectura_fallida_y_reintento_recupera(docente_http):
    h=docente_http;e=get_engine();insertado=[False];confirmado=[False];fallo=[False]
    def sql(conn,cursor,statement,*args):
        if statement.startswith('INSERT INTO resultado_intento '):insertado[0]=True
        if confirmado[0] and statement.startswith('SELECT resultado_intento.') and not fallo[0]:
            fallo[0]=True;conn.exec_driver_sql('SELECT 1/0')
    def commit(conn):
        if insertado[0]:confirmado[0]=True
    sa.event.listen(e,'before_cursor_execute',sql);sa.event.listen(e,'commit',commit)
    try:r=enviar(h)
    finally:sa.event.remove(e,'before_cursor_execute',sql);sa.event.remove(e,'commit',commit)
    assert r.status_code==503 and fallo[0] and contar(h.c)==1
    with h.c.sesiones() as s:anterior=s.execute(sa.select(R.id_resultado,R.fecha_calculo).where(R.id_intento==h.c.ik)).one()
    r=enviar(h);assert r.status_code==200,r.text
    assert r.json()['id_resultado']==anterior.id_resultado and contar(h.c)==1


def test_dos_post_simultaneos_una_cabecera_sin_avisos(docente_http):
    h=docente_http;e=get_engine();b=Barrier(2);inserts=[]
    with h.c.sesiones() as s:avisos=s.scalar(sa.select(sa.func.count()).select_from(N))
    def sql(conn,cursor,statement,*args):
        if statement.startswith('INSERT INTO resultado_intento '):inserts.append(1)
    def post(_):b.wait(timeout=10);return enviar(h)
    sa.event.listen(e,'before_cursor_execute',sql)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(post,range(2)))
    finally:sa.event.remove(e,'before_cursor_execute',sql)
    assert [r.status_code for r in rs]==[200,200],[r.text for r in rs]
    assert rs[0].json()==rs[1].json() and len(inserts)==1 and contar(h.c)==1
    with h.c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(N))==avisos


@pytest.mark.parametrize('actor,status',[('anonimo',401),('invalido',401),('ajeno',403),('estudiante',403),('admin',403),('inactivo',401),('rol_revocado',403)])
def test_autorizacion_docente_no_confia_en_cabeceras(docente_http,actor,status):
    h=docente_http;auth=h.auth.get(actor,h.auth['docente'])
    if actor=='anonimo':auth={}
    elif actor=='invalido':auth={'Authorization':'Bearer invalido-LAB'}
    elif actor in ('inactivo','rol_revocado'):
        with h.c.sesiones.begin() as s:
            if actor=='inactivo':s.get(U,h.c.docente).activo=False
            else:s.get(U,h.c.docente).id_rol=3
    r=h.client.post(ruta(h),headers=auth|{'X-Docente-Id':str(h.c.docente)})
    assert r.status_code==status and contar(h.c)==0 and 'nota_final' not in r.text


@pytest.mark.parametrize('problema',['grupo_ajeno','sesion_ajena','intento_ajeno'])
def test_referencias_fuera_de_ambito(docente_http,problema,crear_registro):
    from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
    h=docente_http;url=ruta(h)
    if problema=='grupo_ajeno':
        with h.c.sesiones.begin() as s:s.get(G,s.get(A,h.c.datos['id_asignacion']).id_grupo).id_profesor=h.c.alumno
    elif problema=='sesion_ajena':url=url.replace(str(h.c.sesion),str(uuid4()))
    else:
        otro=crear_registro();cerrar(otro);url=ruta(h,otro.ik)
    r=h.client.post(url,headers=h.auth['docente'])
    assert r.status_code==403 and contar(h.c)==0


@pytest.mark.parametrize('c',['activo'],indirect=True)
def test_intento_activo_409_no_se_cierra(docente_http):
    h=docente_http;antes=estado(h.c)
    assert enviar(h).status_code==409 and estado(h.c)==antes and contar(h.c)==0


@pytest.mark.parametrize('c',['legacy'],indirect=True)
@pytest.mark.parametrize('persistido',[False,True])
def test_configuracion_historica_no_se_reinterpreta(docente_http,persistido):
    h=docente_http;antes=estado(h.c)
    if persistido:evaluar(h.c)
    r=enviar(h)
    assert r.status_code==(409 if persistido else 503),r.text
    assert estado(h.c)==antes and contar(h.c)==int(persistido)


def test_post_no_admite_puntajes_versiones_ni_body(docente_http):
    h=docente_http
    assert h.client.post(ruta(h),headers=h.auth['docente'],json={'nota_final':'100','version_caso_id':str(uuid4())}).status_code==422
    assert h.client.post(ruta(h)+'?rubrica_id='+str(uuid4()),headers=h.auth['docente']).status_code==422
    assert contar(h.c)==0


@pytest.mark.parametrize('c',['activo'],indirect=True)
def test_cierre_temprano_sin_fin_evalua_parcial_sin_selecciones_ficticias(docente_http,monkeypatch):
    h=docente_http;monkeypatch.setattr(RelojSistema,'ahora',lambda self:FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=1))
    r=h.client.post(f'/api/v1/attempts/{h.c.ik}/finish',headers=h.auth['estudiante'])
    assert r.status_code==200 and r.json()['estado']=='FINALIZADO'
    antes=estado(h.c)
    # Sustituye el bloqueo anterior por la política técnica explícita v2.
    calculo=enviar(h);assert calculo.status_code==200,calculo.text
    assert calculo.json()['modalidad']=='PARCIAL' and calculo.json()['nota_final']=='0.00'
    assert calculo.json()['oficial'] is False and contar(h.c)==1 and estado(h.c)==antes



def test_evaluacion_concurrente_con_worker_conserva_cierre_y_auditoria(docente_http):
    import asyncio
    from app.modules.scheduling.application.worker_cierre import cerrar_sesiones_vencidas
    from app.modules.scheduling.application.registrar_observadores import crear_gestor_eventos
    from app.modules.scheduling.infrastructure.models import EventoAuditoriaModel as Auditoria
    h=docente_http
    with h.c.sesiones.begin() as s:s.get(S,h.c.sesion).estado='EN_CURSO'
    b=Barrier(2);gestor=crear_gestor_eventos(h.c.sesiones)
    def worker():
        b.wait(timeout=10)
        return asyncio.run(cerrar_sesiones_vencidas(h.c.sesiones,gestor,ahora=FECHA.replace(tzinfo=timezone.utc)+timedelta(hours=48)))
    def comando():b.wait(timeout=10);return enviar(h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(worker);r=pool.submit(comando);a.result(timeout=40);respuesta=r.result(timeout=40)
    assert respuesta.status_code in (200,409),respuesta.text
    assert enviar(h).status_code==200 and contar(h.c)==1
    with h.c.sesiones() as s:
        assert s.get(S,h.c.sesion).estado=='FINALIZADO'
        assert s.scalar(sa.select(sa.func.count()).select_from(Auditoria).where(Auditoria.sesion_id==h.c.sesion,Auditoria.estado_nuevo=='FINALIZADO'))==1
    assert estado(h.c)[0]=='VENCIDO'



def test_comando_conserva_version_asignada_ante_edicion_posterior(docente_http):
    from app.modules.cases.infrastructure.models import VersionCasoModel as V
    from app.modules.cases.domain.enums import EstadoCaso
    h=docente_http
    with h.c.sesiones.begin() as s:
        v=s.get(V,h.c.version.id)
        s.add(V(id=uuid4(),caso_id=v.caso_id,numero=v.numero+1,nombre='Posterior LAB',
            desarrollo_situacional='Borrador nuevo',contexto_historia='LAB',tiempo_estimado_min=20,estado=EstadoCaso.BORRADOR))
    r=enviar(h);assert r.status_code==200,r.text
    j=r.json();assert j['version_caso_id']==str(h.c.version.id) and j['rubrica_id']==str(h.c.version.rubrica.id)
    assert j['nota_final']=='33.33' and enviar(h).json()==j
