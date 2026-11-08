"""Cierre voluntario parcial: main/JWT/PG17; política técnica de equipo, no institucional."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timezone, timedelta
from decimal import Decimal
from fractions import Fraction
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from alembic import command
from app.db.session import get_engine
from app.modules.participation.domain.clock import RelojSistema
from app.modules.participation.infrastructure.models import IntentoModel as I, PasoSimulacionModel as Paso
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.participation.infrastructure.question_result_models import ResultadoPreguntaModel as Q
from app.modules.participation.infrastructure.question_evaluation import preparar_calculo_historico
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, NotificacionModel as N
from app.modules.participation.infrastructure.academic_results_models import PublicacionEvaluacionModel as Pub
from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas
from app.modules.cases.application.scoring import ConfiguracionCalificacionInvalida
from app.modules.participation.infrastructure.evaluation import _unidad,_evidencias_autorizadas
from app.modules.participation.infrastructure.composition import _Alcance
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from tests.integration.test_main_technical_results import c,crear_registro,pg_resultados,docente_http,revision,ruta,lectura
from tests.integration.test_question_result_storage import guardar,leer,cerrar,contar
from tests.integration.test_participation_persistence import FECHA
from tests.integration.test_evaluation_readiness import cerrar_sesion_fixture
from tests.identity.academic_identity_support import motor_postgresql_desechable,config_alembic

HEAD='20261108_voluntary_partial'
PARENT='20261108_academic_publication'


def preparar(h,monkeypatch,n=1,rama=0):
    with h.c.sesiones.begin() as s:s.get(S,h.c.sesion).estado='EN_CURSO'
    reloj=[FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=1)]
    monkeypatch.setattr(RelojSistema,'ahora',lambda self:reloj[0])
    base=f'/api/v1/attempts/{h.c.ik}'
    decisiones=[]
    for i in range(n):
        actual=h.client.get(base+'/current-scenario',headers=h.auth['estudiante']);assert actual.status_code==200,actual.text
        q=actual.json()['pregunta'];op=q['opciones'][rama if i==0 else 0]
        r=h.client.post(base+'/decisions/'+q['id'],headers=h.auth['estudiante'],json={'id_opcion':op['id']})
        assert r.status_code==201,r.text
        decisiones.append((q['id'],op['id']));reloj[0]+=timedelta(minutes=1)
    actual=h.client.get(base+'/current-scenario',headers=h.auth['estudiante']);assert actual.status_code==200
    assert actual.json()['recorrido_finalizado'] is False
    r=h.client.post(base+'/finish',headers=h.auth['estudiante']);assert r.status_code==200,r.text
    assert r.json()['estado']=='FINALIZADO' and contar(h.c)==0
    return base,decisiones,r.json()


def evaluar(h):return h.client.post(ruta(h),headers=h.auth['docente'])

def estado(c):
    with c.sesiones() as s:
        i=s.get(I,c.ik);return i.estado,i.inicio,i.fin


@pytest.mark.parametrize('c',['activo'],indirect=True)
@pytest.mark.parametrize('n,rama,nota',[(0,0,'0.00'),(1,0,'33.33'),(1,1,'33.33'),(2,0,'66.67'),(2,1,'66.67')])
def test_prefijo_real_denominador_uniforme_sin_elegir_rama_futura(docente_http,monkeypatch,n,rama,nota):
    h=docente_http;base,decisiones,fin=preparar(h,monkeypatch,n,rama);antes=estado(h.c)
    r=evaluar(h);assert r.status_code==200,r.text;j=r.json()
    assert j['modalidad']=='PARCIAL' and j['nota_final']==nota and j['oficial'] is False
    assert j['preguntas_exigidas']==3 and j['preguntas_respondidas']==n and j['pendientes_con_cero']==3-n
    assert j['version_caso_id']==str(h.c.version.id) and len(j['preguntas'])==n
    assert sum((Fraction(int(x['numerador']),int(x['denominador'])) for x in j['criterios']),Fraction(0))==Fraction(100*n,3)
    assert evaluar(h).json()==j
    with lectura(h):assert h.client.get(ruta(h),headers=h.auth['docente']).json()==j
    assert h.client.post(base+'/finish',headers=h.auth['estudiante']).json()==fin
    assert estado(h.c)==antes
    with h.c.sesiones() as s:
        cab=s.scalar(sa.select(R).where(R.id_intento==h.c.ik));doc=json.loads(cab.procedencia)
        assert cab.politica_version=='2' and json.loads(doc['politica_documento'])['cierre_voluntario']['origen']=='PROPUESTA_TECNICA_EQUIPO'
        reales={(str(x.id_decision),str(x.id_opcion)) for x in s.scalars(sa.select(Paso).where(Paso.id_intento==h.c.ik))}
        persistidos={(str(x.pregunta_id),str(x.opcion_id)) for x in s.scalars(sa.select(Q).where(Q.id_resultado==cab.id_resultado))}
        assert reales==persistidos==set(decisiones)
        assert s.scalar(sa.select(sa.func.count()).select_from(Pub).where(Pub.sesion_id==h.c.sesion))==0
    if decisiones:
        q,op=decisiones[0]
        assert h.client.post(base+'/decisions/'+q,headers=h.auth['estudiante'],json={'id_opcion':op}).status_code==409


@pytest.mark.parametrize('c',['activo'],indirect=True)
def test_dos_calculos_concurrentes_un_resultado_sin_notificaciones(docente_http,monkeypatch):
    h=docente_http;preparar(h,monkeypatch);antes=estado(h.c)
    with h.c.sesiones() as s:avisos=s.scalar(sa.select(sa.func.count()).select_from(N))
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:evaluar(h),range(2)))
    assert [r.status_code for r in rs]==[200,200],[r.text for r in rs]
    assert rs[0].json()==rs[1].json() and contar(h.c)==1 and estado(h.c)==antes
    with h.c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(N))==avisos


@pytest.mark.parametrize('c',['activo'],indirect=True)
def test_error_sql_revierte_resultado_y_reintento_conserva_cierre(docente_http,monkeypatch):
    h=docente_http;preparar(h,monkeypatch);antes=estado(h.c);e=get_engine();fallo=[]
    def romper(conn,cursor,sql,*args):
        if sql.startswith('INSERT INTO resultado_calculo_preguntas') and not fallo:
            fallo.append(True);conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(e,'before_cursor_execute',romper)
    try:r=evaluar(h)
    finally:sa.event.remove(e,'before_cursor_execute',romper)
    assert fallo and r.status_code==503 and contar(h.c)==0 and estado(h.c)==antes
    assert evaluar(h).status_code==200 and contar(h.c)==1


@pytest.mark.parametrize('c',['activo'],indirect=True)
@pytest.mark.parametrize('campo,valor',[('modalidad','COMPLETA'),('politica_version','1')])
def test_postgresql_rechaza_cabecera_falseada_sin_debilitar_guards(docente_http,monkeypatch,campo,valor):
    h=docente_http;preparar(h,monkeypatch);e=get_engine();cambios=[];codigos=[]
    def alterar(conn,cursor,sql,params,*args):
        if sql.startswith('INSERT INTO resultado_intento '):params[campo]=valor;cambios.append(True)
    def error(ctx):codigos.append(getattr(ctx.original_exception,'sqlstate',None))
    sa.event.listen(e,'before_cursor_execute',alterar);sa.event.listen(e,'handle_error',error)
    try:r=evaluar(h)
    finally:sa.event.remove(e,'before_cursor_execute',alterar);sa.event.remove(e,'handle_error',error)
    assert cambios and '23514' in codigos and r.status_code==503 and contar(h.c)==0
    assert evaluar(h).status_code==200


@pytest.mark.parametrize('c',['activo'],indirect=True)
@pytest.mark.parametrize('actor,status',[('anonimo',401),('ajeno',403),('estudiante',403)])
def test_cierre_incompleto_no_abre_autorizacion(docente_http,monkeypatch,actor,status):
    h=docente_http;preparar(h,monkeypatch)
    r=h.client.post(ruta(h),headers=h.auth.get(actor,{}))
    assert r.status_code==status and contar(h.c)==0 and 'nota_final' not in r.text


def test_version_ambigua_rechazada_sin_fabricar_pendientes(crear_registro):
    # Snapshot derivada de PG con una continuación deliberadamente desigual.
    # No se altera la versión publicada en DB: sus guards impiden esa corrupción.
    c=crear_registro();cerrar(c,respondidas=0)
    fechas=FechasPersistencia(timezone.utc);t=_unidad(c.sesiones,fechas);a=_Alcance(lambda:t.sesion,c.usuario,c.ik,fechas)
    with t:
        h=_evidencias_autorizadas(t,a,c.usuario,c.ik);config=consultar_configuracion_preguntas(t.sesion,version_id=c.version.id)
        g=config.grafo;e=g.escenas[0];q=e.preguntas[0]
        op=replace(q.opciones[0],tipo='FIN',destino_id=None)
        q=replace(q,opciones=(op,*q.opciones[1:]))
        desigual=replace(config,grafo=replace(g,escenas=(replace(e,preguntas=(q,)),*g.escenas[1:])))
        with pytest.raises(ConfiguracionCalificacionInvalida):preparar_calculo_historico(h,desigual)
    assert contar(c)==0


def test_upgrade_downgrade_preserva_v1_y_bloquea_perdida_v2(crear_registro):
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            from app.modules.identity.infrastructure.models import RolORM
            s.execute(sa.insert(RolORM),[dict(id_rol=1,nombre='DOCENTE'),dict(id_rol=2,nombre='ESTUDIANTE')])
            original=s.scalar(sa.text("SELECT pg_get_functiondef('public.fp8_cabecera(jsonb)'::regprocedure)"))
        c=crear_registro(motor=e);cerrar(c,respondidas=3);anterior=guardar(c)
        with e.begin() as s:command.upgrade(config_alembic(s),HEAD)
        assert leer(c)==anterior
        with e.begin() as s:
            command.downgrade(config_alembic(s),PARENT)
            assert s.scalar(sa.text("SELECT pg_get_functiondef('public.fp8_cabecera(jsonb)'::regprocedure)"))==original
        assert leer(c)==anterior
        with e.begin() as s:command.upgrade(config_alembic(s),HEAD)
        parcial=crear_registro(motor=e);cerrar(parcial,respondidas=1);nuevo=guardar(parcial)
        assert nuevo.datos.modalidad.value=='PARCIAL' and nuevo.datos.nota_final==Decimal('33.33')
        with pytest.raises(RuntimeError,match='Downgrade rechazado'):
            with e.begin() as s:command.downgrade(config_alembic(s),PARENT)
        with e.connect() as s:assert s.scalar(sa.text('SELECT version_num FROM alembic_version'))==HEAD
        assert leer(parcial)==nuevo and leer(c)==anterior


@pytest.mark.parametrize('c',['activo'],indirect=True)
def test_consolidacion_reutiliza_parcial_sin_publicar_y_historia_inmutable(docente_http,monkeypatch):
    h=docente_http;preparar(h,monkeypatch);r=evaluar(h);assert r.status_code==200
    base=f'/scheduling/sesiones/{h.c.sesion}/evaluacion'
    propio=f"/scheduling/convocatorias/{h.c.datos['convocatoria_id']}/resultado"
    assert h.client.get(propio,headers=h.auth['estudiante']).status_code==404
    visible=h.client.put(base+'/visibilidad',headers=h.auth['docente'],json={'mostrar_provisional':True})
    assert visible.status_code==200
    with lectura(h):vista=h.client.get(propio,headers=h.auth['estudiante'])
    assert vista.status_code==200 and vista.json()['oficial'] is False
    assert vista.json()['situacion']=='PARCIAL' and vista.json()['nota']=='33.33' and vista.json()['explicaciones']==[]
    cerrar_sesion_fixture(h.c)
    with lectura(h):revision=h.client.get(base+'/consolidacion',headers=h.auth['docente'])
    assert revision.status_code==200 and revision.json()['publicable']
    fila=revision.json()['filas'][0];assert fila['situacion']=='PARCIAL' and fila['nota']=='33.33'
    with h.c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(Pub).where(Pub.sesion_id==h.c.sesion))==0
    # La publicación exige un POST docente independiente y explícito, nunca finish ni evaluar.
    pub=h.client.post(base+'/publicaciones',headers=h.auth['docente'],json={'revision_sha256':revision.json()['revision_sha256']})
    assert pub.status_code==200,pub.text
    assert pub.json()['resultados'][0]['situacion']=='PARCIAL' and pub.json()['resultados'][0]['nota']=='33.33'
    with lectura(h):oficial=h.client.get(propio,headers=h.auth['estudiante'])
    assert oficial.status_code==200 and oficial.json()['oficial'] is True and oficial.json()['nota']=='33.33'
    with pytest.raises(DBAPIError):
        with h.c.sesiones.begin() as s:s.execute(sa.update(I).where(I.id_intento==h.c.ik).values(estado='EN_CURSO',fin=None))
