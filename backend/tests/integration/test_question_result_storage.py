"""Persistencia exacta real: PG17 nuevo, sin rutas de notas ni nivel ficticio."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timezone,timedelta
from decimal import Decimal
from fractions import Fraction
from copy import deepcopy
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4
import json
import os
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError,DBAPIError

from app.db.models import registrar_modelos_integrados
from app.modules.cases.domain.entities.caso import Escenario,Pregunta,OpcionRespuesta,CriterioRubrica,NivelRubrica
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
from app.modules.participation.infrastructure.persisted_questions import persistir_resultado_preguntas,consultar_resultado_tecnico
from app.modules.participation.infrastructure.question_result_repository import DetallesPreguntasSQLAlchemy
from app.modules.participation.infrastructure.question_result_models import ResultadoCalculoPreguntasModel as G,ResultadoPreguntaModel as Q,ResultadoCriterioExactoModel as C
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R,ResultadoCriterioModel as L
from app.modules.participation.infrastructure.models import IntentoModel,PasoSimulacionModel
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.application.errors import AccesoDenegado,ConflictoActualizacion
from tests.identity.academic_identity_support import motor_postgresql_desechable,config_alembic
from tests.integration.test_evaluation_result_storage import pg_resultados  # noqa: F401
from tests.integration.test_question_scoring import version_calificable,configurar
from tests.integration import test_assignment_bridge as bridge
from tests.integration.test_participation_persistence import contexto,participacion,intento,FECHA
from tests.integration.test_attempt_state import principal
from tests.integration.test_main_evaluation_readiness import docente_http, revision, lectura  # noqa: F401

HEAD='20261107_question_results'
PARENT='20261106_consent_versions'


@pytest.fixture
def crear_registro(pg_resultados,monkeypatch):
    def crear(*,criterios=1,puntos=None,cola_extra=0,motor=None):
        v=version_calificable();cr=v.rubrica.criterios[0]
        v.escenarios.append(Escenario(4,'Cola común LAB',preguntas=[Pregunta(1,'Última pregunta LAB',opciones=[
            OpcionRespuesta(i,'Opción LAB',i==1,'Explicación LAB',valoraciones={cr.id:Decimal(100 if i==1 else 0)}) for i in (1,2)])]))
        for numero in range(cola_extra):
            v.escenarios.append(Escenario(5+numero,'Continuación común LAB',preguntas=[Pregunta(1,'Pregunta LAB',opciones=[
                OpcionRespuesta(i,'Opción LAB',i==1,'Explicación LAB',valoraciones={cr.id:Decimal(100 if i==1 else 0)}) for i in (1,2)])]))
        if criterios==2:
            cr.peso=Decimal(50)
            v.rubrica.criterios.append(CriterioRubrica('Segundo criterio',Decimal(50),niveles=[NivelRubrica('Alto',Decimal(5),'Descriptor LAB')]))
        for i,e in enumerate(v.escenarios):
            for o in e.preguntas[0].opciones:
                p=o.valoraciones[cr.id] if puntos is None else (Decimal(puntos[0 if i==0 else 2 if i==3 else 1]) if o.es_correcta else Decimal(0))
                o.valoraciones={c.id:p for c in v.rubrica.criterios}
        original=bridge.publicar
        def publicar(fabrica,version):
            with fabrica.begin() as s:
                configurar(s,version)
                RepositorioGrafoSQLAlchemy(s).configurar(version_id=version.id,docente_id=version.docente_creador_id,inicial_id=version.escenarios[0].id,
                    transiciones=tuple((o.id,'ESCENA',version.escenarios[3].id) for e in version.escenarios[1:3] for o in e.preguntas[0].opciones)+
                    tuple((o.id,'ESCENA',version.escenarios[i+1].id) for i in range(3,len(version.escenarios)-1) for o in version.escenarios[i].preguntas[0].opciones))
            return original(fabrica,version)
        with monkeypatch.context() as m:
            m.setattr(bridge,'nuevo',lambda:v);m.setattr(bridge,'publicar',publicar)
            c=contexto(motor if motor is not None else pg_resultados)
        c.pk=participacion(c);c.ik=intento(c,c.pk);c.usuario=principal(c)
        return c
    return crear


@pytest.fixture
def c(crear_registro):
    contexto=crear_registro()
    cerrar(contexto,vencido=True,respondidas=1)
    return contexto


def cerrar(c,*,vencido=False,respondidas=3,rama=0,cero=False):
    qs=[c.version.escenarios[i].preguntas[0] for i in (0,rama+1,*range(3,len(c.version.escenarios)))]
    with c.sesiones.begin() as s:
        for i,q in enumerate(qs[:respondidas]):
            op=(2 if i==0 else 1) if cero else (rama if i==0 else 0)
            s.add(PasoSimulacionModel(id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[op].id,numero_paso=i+1,
                registrado_en=FECHA+timedelta(seconds=(i+1)*60),tiempo_segundos=(i+1)*60))
        s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik).values(estado='VENCIDO' if vencido else 'FINALIZADO',
            fin=FECHA+(timedelta(seconds=1800,microseconds=1) if vencido else timedelta(minutes=max(5,len(qs)+1)))))


def args(c,**kw):return dict(usuario=c.usuario,id_intento=c.ik,fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones)|kw
def guardar(c,**kw):return persistir_resultado_preguntas(**args(c,**kw),reloj=SimpleNamespace(ahora=lambda:FECHA.replace(tzinfo=timezone.utc)+timedelta(hours=1)))
def leer(c,**kw):return consultar_resultado_tecnico(**args(c,**kw))
def contar(c):
    with c.sesiones() as s:return s.scalar(sa.select(sa.func.count()).select_from(R).where(R.id_intento==c.ik))


def evidencia_numerica(c,r,recuperado,nombre):
    """Salida opcional de filas REALES ya confirmadas; no modifica el veredicto."""
    salida=os.getenv('SPS_EVIDENCIA_RESULTADOS_DIR')
    if salida is None:return
    with c.sesiones() as s:
        cabecera=s.get(R,r.id_resultado);resumen=s.get(G,r.id_resultado)
        preguntas=s.scalars(sa.select(Q).where(Q.id_resultado==r.id_resultado).order_by(Q.numero_paso)).all()
        criterios=s.scalars(sa.select(C).where(C.id_resultado==r.id_resultado).order_by(C.criterio_id)).all()
        documento=dict(datos='SINTETICOS_LABORATORIO',id_resultado=r.id_resultado,id_intento=c.ik,
            version_caso_id=str(cabecera.version_caso_id),rubrica_id=str(cabecera.rubrica_id),ambito=cabecera.ambito,
            nota_final_db=str(cabecera.nota_final),nota_leida_otra_sesion=str(recuperado.datos.nota_final),oficial=recuperado.oficial,
            suma_exacta=str(resumen.suma_puntajes),preguntas_exigidas=resumen.preguntas_exigidas,
            pendientes=resumen.preguntas_pendientes,procedencia_sha256=cabecera.procedencia_sha256,
            puntajes=[str(p.puntaje) for p in preguntas],
            criterios=[dict(suma=str(v.suma_puntajes),numerador=str(v.numerador),denominador=str(v.denominador)) for v in criterios])
    with (Path(salida)/(nombre+'.json')).open('x',encoding='utf-8') as f:json.dump(documento,f,indent=2)


@pytest.mark.parametrize('rama,cero,nota',[(0,False,'100.00'),(1,False,'100.00'),(1,True,'0.00')])
def test_escribir_leer_otra_session_ramas_y_cero(crear_registro,rama,cero,nota):
    c=crear_registro();cerrar(c,rama=rama,cero=cero)
    r=guardar(c);recuperado=leer(c)
    assert r==recuperado and r.datos.nota_final==Decimal(nota) and r.datos.persistido and not r.oficial
    assert contar(c)==1 and r.datos.preguntas_exigidas==3
    evidencia_numerica(c,r,recuperado,f'calculo_rama_{rama}_cero_{cero}')
    with c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(L).where(L.id_resultado==r.id_resultado))==0
        assert s.scalar(sa.select(sa.func.count()).select_from(Q).where(Q.id_resultado==r.id_resultado))==3


def test_peso_igual_sin_ponderar_criterios(crear_registro):
    c=crear_registro(criterios=2,puntos=('30','60','90'));cerrar(c)
    r=guardar(c);assert r.datos.nota_final==Decimal('60.00')
    evidencia_numerica(c,r,leer(c),'peso_igual')
    with c.sesiones() as s:
        cs=s.scalars(sa.select(C).where(C.id_resultado==r.id_resultado)).all()
        assert len(cs)==2 and all(x.suma_puntajes==Decimal(180) for x in cs)
        assert sum((Fraction(x.numerador)/Fraction(x.denominador) for x in cs),Fraction(0))==60


def test_sumas_intermedias_superiores_a_precision_historica(crear_registro):
    c=crear_registro(cola_extra=9);cerrar(c,respondidas=12)
    r=guardar(c);assert r.datos.nota_final==Decimal('100.00') and r.datos.preguntas_exigidas==12
    evidencia_numerica(c,r,leer(c),'suma_1200')
    with c.sesiones() as s:
        assert s.get(G,r.id_resultado).suma_puntajes==Decimal(1200)
        assert s.scalar(sa.select(C.suma_puntajes).where(C.id_resultado==r.id_resultado))==Decimal(1200)


@pytest.mark.parametrize('criterios',[1,2])
def test_tercio_exacto_vencido_sin_redondear_contribucion(crear_registro,criterios):
    c=crear_registro(criterios=criterios);cerrar(c,vencido=True,respondidas=1)
    r=guardar(c);recuperado=leer(c);assert recuperado==r
    evidencia_numerica(c,r,recuperado,f'tercio_{criterios}_criterios')
    assert r.datos.nota_final==Decimal('33.33') and r.datos.modalidad.value=='PARCIAL' and r.datos.pendientes_con_cero==2
    with c.sesiones() as s:
        cs=s.scalars(sa.select(C).where(C.id_resultado==r.id_resultado)).all()
        assert sum((Fraction(x.numerador)/Fraction(x.denominador) for x in cs),Fraction(0))==Fraction(100,3)
        assert all(x.numerador==100 if criterios==1 else x.numerador==50 for x in cs)
        assert all(x.denominador==3 for x in cs)
        assert s.scalar(sa.select(sa.func.count()).select_from(PasoSimulacionModel).where(PasoSimulacionModel.id_intento==c.ik))==1


def test_vencido_sin_respuestas_no_crea_selecciones(crear_registro):
    c=crear_registro();cerrar(c,vencido=True,respondidas=0)
    r=guardar(c);assert r.datos.nota_final==Decimal('0.00')
    with c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(Q).where(Q.id_resultado==r.id_resultado))==0


def test_ambito_tecnico_no_depende_de_nombre_de_base_lab(crear_registro,pg_resultados):
    from app.modules.identity.infrastructure.models import RolORM
    nombre='sps_preguntas_lab_'+uuid4().hex
    # Base nueva dentro del CONTENEDOR TEMPORAL PROPIO del fixture. No se usa
    # ninguna conexión de .env ni se toca una base externa o preexistente.
    with pg_resultados.connect().execution_options(isolation_level='AUTOCOMMIT') as s:
        s.exec_driver_sql('CREATE DATABASE '+nombre)
    motor=sa.create_engine(pg_resultados.url.set(database=nombre))
    try:
        with motor.begin() as s:
            command.upgrade(config_alembic(s),HEAD)
            s.execute(sa.insert(RolORM),[dict(id_rol=1,nombre='DOCENTE'),dict(id_rol=2,nombre='ESTUDIANTE')])
        c=crear_registro(motor=motor);cerrar(c);r=guardar(c)
        assert leer(c)==r and not r.oficial
        with motor.connect() as s:assert s.scalar(sa.select(R.ambito).where(R.id_resultado==r.id_resultado))=='TECNICO'
    finally:motor.dispose()  # El dueño del fixture destruye SU contenedor completo.


def test_idempotencia_y_concurrencia_misma_cabecera(crear_registro):
    c=crear_registro();cerrar(c);b=Barrier(2)
    def ejecutar(_):b.wait(timeout=5);return guardar(c)
    with ThreadPoolExecutor(max_workers=2) as p:rs=list(p.map(ejecutar,range(2)))
    assert rs[0]==rs[1]==guardar(c)==leer(c) and contar(c)==1


def test_actor_ajeno_no_calcula_escribe_ni_lee(crear_registro):
    c=crear_registro();cerrar(c)
    ajeno=replace(c.usuario,id_usuario=str(c.docente))
    with pytest.raises(AccesoDenegado):guardar(c,usuario=ajeno)
    assert contar(c)==0
    guardar(c)
    with pytest.raises(AccesoDenegado):leer(c,usuario=ajeno)


def test_error_sql_rollback_cabecera_y_detalles(crear_registro):
    c=crear_registro();cerrar(c)
    def error(conn,cursor,sql,*_):
        if sql.startswith('INSERT INTO resultado_calculo_preguntas'):conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(c.engine,'before_cursor_execute',error)
    try:
        with pytest.raises(DBAPIError):guardar(c)
    finally:sa.event.remove(c.engine,'before_cursor_execute',error)
    assert contar(c)==0
    assert guardar(c)==leer(c)


def capturar(c,monkeypatch):
    original=DetallesPreguntasSQLAlchemy.guardar;captura={}
    class Cortar(Exception):pass
    def guardar_rollback(self,*a,**kw):
        r=original(self,*a,**kw)
        for t in (R,G,Q,C):captura[t]=[dict(x) for x in self.s.execute(sa.select(t.__table__).where(t.id_resultado==r.id_resultado)).mappings()]
        raise Cortar()
    with monkeypatch.context() as m:
        m.setattr(DetallesPreguntasSQLAlchemy,'guardar',guardar_rollback)
        with pytest.raises(Cortar):guardar(c)
    assert contar(c)==0
    return captura


@pytest.mark.parametrize('alteracion',['puntaje','pregunta_ajena','opcion_ajena','denominador_cero','numerador','suma','denominador_total','config_hash','detalle_incompleto','infinito','nan'])
def test_sql_integridad_y_fracciones_no_falsificables(crear_registro,monkeypatch,alteracion):
    c=crear_registro();cerrar(c,vencido=True,respondidas=1);d=capturar(c,monkeypatch)
    if alteracion=='puntaje':d[Q][0]['puntaje']=Decimal(50)
    elif alteracion=='pregunta_ajena':d[Q][0]['pregunta_id']=uuid4()
    elif alteracion=='opcion_ajena':d[Q][0]['opcion_id']=uuid4()
    elif alteracion=='denominador_cero':d[C][0]['denominador']=Decimal(0)
    elif alteracion=='numerador':d[C][0]['numerador']+=1
    elif alteracion=='suma':d[G][0]['suma_puntajes']=Decimal(1)
    elif alteracion=='denominador_total':d[G][0]['preguntas_exigidas']=4;d[G][0]['preguntas_pendientes']=3
    elif alteracion=='config_hash':d[G][0]['configuracion_sha256']='0'*64
    elif alteracion=='infinito':d[C][0]['denominador']=Decimal('Infinity')
    elif alteracion=='nan':d[C][0]['numerador']=Decimal('NaN')
    else:d[Q]=[]
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            for t in (R,G,Q,C):
                if d[t]:s.execute(t.__table__.insert(),d[t])
    assert contar(c)==0


def test_referencia_cruzada_existente_se_rechaza(crear_registro,monkeypatch):
    c=crear_registro();cerrar(c,vencido=True,respondidas=1);d=capturar(c,monkeypatch)
    otra=crear_registro();q=otra.version.escenarios[0].preguntas[0]
    d[Q][0].update(pregunta_id=q.id,opcion_id=q.opciones[0].id)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            for t in (R,G,Q,C):s.execute(t.__table__.insert(),d[t])
    assert contar(c)==0


@pytest.mark.parametrize('campo',['version_caso_id','rubrica_id','modalidad','ambito','politica_hash'])
def test_cabecera_no_admite_cambio_de_contexto(crear_registro,monkeypatch,campo):
    c=crear_registro();cerrar(c);d=capturar(c,monkeypatch)
    d[R][0][campo]=uuid4() if campo in ('version_caso_id','rubrica_id') else 'PARCIAL' if campo=='modalidad' else 'OFICIAL' if campo=='ambito' else '0'*64
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            for t in (R,G,Q,C):s.execute(t.__table__.insert(),d[t])
    assert contar(c)==0


@pytest.mark.parametrize('tabla',[G,Q,C])
@pytest.mark.parametrize('op',['update','delete','truncate'])
def test_detalles_historicos_inmutables(crear_registro,tabla,op):
    c=crear_registro();cerrar(c);r=guardar(c)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            if op=='truncate':s.execute(sa.text('TRUNCATE '+tabla.__tablename__+' CASCADE'))
            elif op=='delete':s.execute(sa.delete(tabla).where(tabla.id_resultado==r.id_resultado))
            else:s.execute(sa.update(tabla).where(tabla.id_resultado==r.id_resultado).values(**({'preguntas_exigidas':1} if tabla is G else {'puntaje':0} if tabla is Q else {'numerador':0})))
    assert leer(c)==r


def test_upgrade_downgrade_vacio_y_metadata_real():
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            anteriores=set(sa.inspect(s).get_table_names())
            command.upgrade(config_alembic(s),HEAD)
            assert set(sa.inspect(s).get_table_names())-anteriores=={G.__tablename__,Q.__tablename__,C.__tablename__}
            assert compare_metadata(MigrationContext.configure(s),registrar_modelos_integrados())==[]
            command.downgrade(config_alembic(s),PARENT)
            assert set(sa.inspect(s).get_table_names())==anteriores
            command.upgrade(config_alembic(s),HEAD)


def test_downgrade_con_resultados_rechazado_sin_perdida(crear_registro):
    c=crear_registro();cerrar(c);r=guardar(c)
    with c.engine.begin() as s:
        with pytest.raises(RuntimeError,match='historicos'):
            with s.begin_nested():command.downgrade(config_alembic(s),PARENT)
    assert leer(c)==r


def test_upgrade_y_downgrade_preservan_resultado_del_motor_anterior():
    from app.modules.identity.infrastructure.models import RolORM
    from tests.integration.test_evaluation_feedback import cerrar_fixture
    from tests.integration.test_evaluation_result_storage import evaluar,consultar
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            s.execute(sa.insert(RolORM),[dict(id_rol=1,nombre='DOCENTE'),dict(id_rol=2,nombre='ESTUDIANTE')])
        c=cerrar_fixture(contexto(e),opcion=0);c.politica_id='compatibilidad-'+uuid4().hex
        anterior=evaluar(c)
        with e.begin() as s:command.upgrade(config_alembic(s),HEAD)
        assert consultar(c)==anterior

        with e.begin() as s:command.downgrade(config_alembic(s),PARENT)
        assert consultar(c)==anterior
        with e.begin() as s:command.upgrade(config_alembic(s),HEAD)
        assert consultar(c)==anterior


def test_motor_anterior_no_se_reinterpreta_por_el_nombre_de_regla(pg_resultados,monkeypatch):
    from tests.integration.test_cases_history import nuevo
    from tests.integration.test_evaluation_feedback import cerrar_fixture
    from tests.integration.test_evaluation_result_storage import evaluar,consultar
    from app.modules.cases.application.scoring import REGLA_PREGUNTAS
    v=nuevo();v.rubrica.version_regla=REGLA_PREGUNTAS;original=bridge.publicar
    def publicar(fabrica,version):
        with fabrica.begin() as s:
            RepositorioGrafoSQLAlchemy(s).configurar(version_id=v.id,docente_id=v.docente_creador_id,
                inicial_id=v.escenarios[0].id,transiciones=tuple((o.id,'FIN',None) for o in v.escenarios[0].preguntas[0].opciones))
        return original(fabrica,version)
    with monkeypatch.context() as m:
        m.setattr(bridge,'nuevo',lambda:v);m.setattr(bridge,'publicar',publicar)
        c=cerrar_fixture(contexto(pg_resultados),opcion=0)
    c.politica_id='legacy-coincidencia-'+uuid4().hex
    r=evaluar(c)
    assert consultar(c)==leer(c)==r and r.ambito=='LABORATORIO'
    with pytest.raises(ConflictoActualizacion):guardar(c)
    assert consultar(c)==r and contar(c)==1


def test_lector_docente_read_only_reutiliza_resultado_nuevo(crear_registro):
    c=crear_registro();cerrar(c);r=guardar(c)
    from tests.integration.test_evaluation_readiness import Vinculos,VinculoAcademico,SistemaAcademico,CasoModel,S,RepositorioUsuariosSQLAlchemy,consulta,solo_lectura
    with c.sesiones.begin() as s:
        for sis,uid in ((SistemaAcademico.CASES,s.get(CasoModel,c.version.caso_id).docente_creador_id),(SistemaAcademico.SCHEDULING,s.get(S,c.sesion).docente_id)):
            Vinculos(s).agregar_verificado(VinculoAcademico(str(c.docente),sis,uid))
    with c.sesiones() as s:c.actor=RepositorioUsuariosSQLAlchemy(s).obtener(str(c.docente))
    with solo_lectura(c):revision=consulta(c).consultar(id_sesion=c.sesion)
    assert not revision.publicable and revision.convocatorias[0].intentos[0].id_resultado_tecnico==r.id_resultado


def test_main_jwt_real_reconoce_resultado_sin_filtrar_nota(docente_http):
    h=docente_http;r=guardar(h.c)
    with lectura(h) as config:
        respuesta=h.client.get(h.path,headers=h.auth['docente'])
    assert respuesta.status_code==200 and config
    j=respuesta.json();fila=j['convocatorias'][0]
    assert fila['intentos'][0]['resultado_tecnico_disponible'] is True
    assert 'RESULTADO_TECNICO_NO_OFICIAL' in fila['pendientes'] and j['publicable'] is False
    assert not any(x in respuesta.text for x in ('nota_final','puntaje','rubrica_id','procedencia','numerador'))
    for actor in ('ajeno','estudiante'):
        assert h.client.get(h.path,headers=h.auth[actor]).status_code==403
    assert leer(h.c)==r
