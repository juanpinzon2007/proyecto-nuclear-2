"""RF13/24: reglas del incremento, datos sintéticos y PG17 propietario.

La preparación adapta exclusivamente helpers de datos, nunca autorizadores,
repositorios ni el motor bajo prueba. No hay endpoint de notas nuevo.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timezone, timedelta
from decimal import Decimal, localcontext
import json
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.modules.cases.application.graph import GrafoVersion, EscenaGrafo, PreguntaGrafo, Transicion
from app.modules.cases.application.scoring import ConfiguracionPreguntas, PuntajeAlternativa, ConfiguracionCalificacionInvalida, REGLA_PREGUNTAS
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.cases.infrastructure.models import ValoracionOpcionModel, VersionCasoModel
from app.modules.cases.domain.entities.caso import Escenario, Pregunta, OpcionRespuesta
from app.modules.participation.domain.calculador_rubrica import CalculadorRubrica
from app.modules.participation.domain.evaluation import EvaluacionInconsistente
from app.modules.participation.application.errors import AccesoDenegado
from app.modules.participation.infrastructure.question_evaluation import calcular_intento_por_preguntas
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import IntentoModel, PasoSimulacionModel
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from tests.integration.test_evaluation_result_storage import pg_resultados, c  # noqa: F401
from tests.integration import test_assignment_bridge as bridge
from tests.integration.test_participation_persistence import contexto, participacion, intento, FECHA
from tests.integration.test_attempt_state import principal
from tests.integration.test_cases_history import nuevo
from tests.integration.test_cases_graph_authoring import autor, pg_autoria, payload_valido  # noqa: F401


@pytest.mark.parametrize('valores,total,esperada',[
    (('100','100','100'),3,'100.00'),(('0','0'),2,'0.00'),
    (('100','50','0'),3,'50.00'),(('100',),3,'33.33'),
    (('100','100'),3,'66.67'),(('1.005',),1,'1.01'),
    (('99.99','100'),2,'100.00'),((),3,'0.00')])
def test_decimal_peso_unico_sin_redondeo_intermedio(valores,total,esperada):
    with localcontext() as c:
        c.prec=3
        assert CalculadorRubrica().calcular_preguntas(puntajes=tuple(map(Decimal,valores)),total_exigidas=total)==Decimal(esperada)


@pytest.mark.parametrize('puntos,total',[(('101',),1),(('-1',),1),(('NaN',),1),(('Infinity',),1),(('1','2'),1),(('1',),0)])
def test_puntajes_y_denominador_invalidos_no_producen_nota(puntos,total):
    with pytest.raises(EvaluacionInconsistente):
        CalculadorRubrica().calcular_preguntas(puntajes=tuple(map(Decimal,puntos)),total_exigidas=total)


def configuracion():
    escenas=[uuid4() for _ in range(3)];qs=[uuid4() for _ in range(3)];os=[uuid4() for _ in range(6)];cr=uuid4()
    g=GrafoVersion(uuid4(),tuple(EscenaGrafo(e,i==0,'LAB',(PreguntaGrafo(q,'LAB',tuple(
        Transicion(os[i*2+j],'ESCENA' if i==0 else 'FIN',escenas[j+1] if i==0 else None,'LAB') for j in range(2))),))
        for i,(e,q) in enumerate(zip(escenas,qs))))
    return ConfiguracionPreguntas(g,(cr,),tuple(PuntajeAlternativa(qs[i],os[2*i+j],cr,Decimal(100)) for i in range(3) for j in range(2)))


def test_ramas_excluidas_no_penalizan_y_no_se_eligen_al_vencer():
    c=configuracion();assert c.validar()==2
    for rama in range(2):
        root=c.grafo.escenas[0].preguntas[0];final=c.grafo.escenas[rama+1].preguntas[0]
        ruta,n,puntos=c.seleccionar(((root.id,root.opciones[rama].opcion_id),(final.id,final.opciones[0].opcion_id)))
        assert ruta.finalizado and CalculadorRubrica().calcular_preguntas(puntajes=puntos,total_exigidas=n)==Decimal('100.00')
    ruta,n,puntos=c.seleccionar(())
    assert len(ruta.decisiones)==1 and n==2 and puntos==()


def test_correspondencia_multicriterio_no_multiplica_preguntas():
    c=configuracion();otro=uuid4()
    c=replace(c,criterios=(*c.criterios,otro),puntajes=(*c.puntajes,*(replace(p,criterio_id=otro) for p in c.puntajes)))
    assert c.validar()==2
    assert CalculadorRubrica().calcular_preguntas(puntajes=(Decimal(100),),total_exigidas=c.validar())==Decimal('50.00')


def test_motor_previo_sigue_verificable_sin_ejecutar_fuentes_recibidas():
    from app.modules.participation.application.result_provenance import motor_compatible
    motor=json.loads((Path(__file__).parents[1]/'fixtures/evaluation_motor_v2.json').read_text('utf-8'))
    for formula in ('SUMA_PONDERADA_PORCENTUAL','PROMEDIO_IGUALITARIO_100'):
        assert motor_compatible(motor,formula)
    motor['app.modules.participation.domain.calculador_rubrica']+='\n# alterado'
    assert not motor_compatible(motor,'PROMEDIO_IGUALITARIO_100')


def test_resultado_motor_anterior_recuperable_desde_postgresql(c,monkeypatch):
    import app.modules.participation.infrastructure.persisted_evaluation as modulo
    from tests.integration.test_evaluation_result_storage import evaluar, consultar
    motor=json.loads((Path(__file__).parents[1]/'fixtures/evaluation_motor_v2.json').read_text('utf-8'))
    # Es el documento de procedencia del motor anterior, no un algoritmo nuevo.
    with monkeypatch.context() as m:
        m.setattr(modulo,'fuentes_motor',lambda:motor)
        antes=evaluar(c)
    assert consultar(c)==antes and antes.datos.nota_final==Decimal('5.00')


@pytest.mark.parametrize('error',['desigual','duplicada','sin_puntaje','puntaje_ajeno','criterio_ajeno','contradictorio','criterios_desiguales'])
def test_configuraciones_ambiguas_o_incompletas_se_rechazan(error):
    c=configuracion();g=c.grafo
    if error=='desigual':
        e=g.escenas[0];q=e.preguntas[0];q=replace(q,opciones=(replace(q.opciones[0],tipo='FIN',destino_id=None),q.opciones[1]))
        c=replace(c,grafo=replace(g,escenas=(replace(e,preguntas=(q,)),*g.escenas[1:])))
    elif error=='duplicada':c=replace(c,puntajes=(*c.puntajes,c.puntajes[0]))
    elif error=='sin_puntaje':c=replace(c,puntajes=c.puntajes[1:])
    elif error=='puntaje_ajeno':c=replace(c,puntajes=(replace(c.puntajes[0],pregunta_id=uuid4()),*c.puntajes[1:]))
    elif error=='criterio_ajeno':c=replace(c,puntajes=(replace(c.puntajes[0],criterio_id=uuid4()),*c.puntajes[1:]))
    elif error=='contradictorio':
        otro=uuid4();c=replace(c,criterios=(*c.criterios,otro),puntajes=(*c.puntajes,replace(c.puntajes[0],criterio_id=otro,puntaje=Decimal(20))))
    else:c=replace(c,criterios=(*c.criterios,uuid4()))
    with pytest.raises(ConfiguracionCalificacionInvalida):c.validar()


def version_calificable():
    v=nuevo();v.rubrica.version_regla=REGLA_PREGUNTAS;criterio=v.rubrica.criterios[0]
    # Valores docentes explícitos 0..100, sin multiplicar los niveles históricos.
    v.escenarios=[Escenario(i,'LAB',preguntas=[Pregunta(1,'Pregunta LAB',opciones=[
        OpcionRespuesta(j,'Alternativa LAB',j==1,'Explicación LAB',valoraciones={criterio.id:Decimal(100 if j==1 else 0)})
        for j in (1,2)])]) for i in (1,2,3)]
    raiz=v.escenarios[0].preguntas[0]
    raiz.opciones[1].es_correcta=True
    raiz.opciones[1].valoraciones={criterio.id:Decimal(100)}
    raiz.opciones.append(OpcionRespuesta(3,'Alternativa cero LAB',False,'Explicación LAB',valoraciones={criterio.id:Decimal(0)}))
    return v


def configurar(s,v):
    es=v.escenarios
    RepositorioGrafoSQLAlchemy(s).configurar(version_id=v.id,docente_id=v.docente_creador_id,inicial_id=es[0].id,
        transiciones=tuple((o.id,'ESCENA' if i==0 else 'FIN',es[1 if j==0 else 2].id if i==0 else None)
            for i,e in enumerate(es) for j,o in enumerate(e.preguntas[0].opciones)))


@pytest.fixture
def registro_puntajes(pg_resultados,monkeypatch):
    v=version_calificable();original=bridge.publicar
    def publicar_con_grafo(fabrica,version):
        with fabrica.begin() as s:configurar(s,version)
        return original(fabrica,version)
    # Solo preparación de datos sintéticos sobre las relaciones reales.
    with monkeypatch.context() as m:
        m.setattr(bridge,'nuevo',lambda:v);m.setattr(bridge,'publicar',publicar_con_grafo)
        c=contexto(pg_resultados)
    c.pk=participacion(c);c.ik=intento(c,c.pk);c.usuario=principal(c)
    return c


def cerrar(c,*,rama=0,vencido=False,respondidas=2,cero=False):
    es=c.version.escenarios;qs=[es[0].preguntas[0],es[rama+1].preguntas[0]]
    with c.sesiones.begin() as s:
        for i,q in enumerate(qs[:respondidas]):
            j=(2 if i==0 else 1) if cero else (rama if i==0 else 0)
            s.add(PasoSimulacionModel(id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[j].id,
                numero_paso=i+1,registrado_en=FECHA+timedelta(seconds=60*(i+1)),tiempo_segundos=60*(i+1)))
        s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik).values(
            estado='VENCIDO' if vencido else 'FINALIZADO',
            fin=FECHA+(timedelta(seconds=1800,microseconds=1) if vencido else timedelta(minutes=3))))


def calcular(c,**kw):
    return calcular_intento_por_preguntas(**(dict(usuario=c.usuario,id_intento=c.ik,fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones)|kw))


@pytest.mark.parametrize('rama,esperada',[(0,'100.00'),(1,'100.00')])
def test_postgresql_recorrido_historico_sin_ramas_inaccesibles(registro_puntajes,rama,esperada):
    c=registro_puntajes;cerrar(c,rama=rama)
    a=calcular(c);b=calcular(c)
    assert a==b and a.nota_final==Decimal(esperada) and a.preguntas_exigidas==2
    assert a.modalidad.value=='COMPLETA' and not a.persistido and not a.oficial
    with c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento==c.ik))==0


def test_postgresql_todas_cero(registro_puntajes):
    c=registro_puntajes;cerrar(c,rama=1,cero=True)
    assert calcular(c).nota_final==Decimal('0.00')


@pytest.mark.parametrize('respondidas,esperada',[(0,'0.00'),(1,'50.00')])
def test_postgresql_vencido_denominador_completo_sin_respuestas_ficticias(registro_puntajes,respondidas,esperada):
    c=registro_puntajes;cerrar(c,vencido=True,respondidas=respondidas)
    r=calcular(c)
    assert r.nota_final==Decimal(esperada) and r.modalidad.value=='PARCIAL' and r.pendientes_con_cero==2-respondidas
    with c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(PasoSimulacionModel).where(PasoSimulacionModel.id_intento==c.ik))==respondidas


def test_postgresql_concurrencia_no_escribe_y_rollback_error(registro_puntajes):
    c=registro_puntajes;cerrar(c)
    ops=[]
    def sql(conn,cursor,statement,*args):
        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')):ops.append(statement)
    def commit(conn):ops.append('COMMIT')
    sa.event.listen(c.engine,'before_cursor_execute',sql);sa.event.listen(c.engine,'commit',commit)
    try:
        with ThreadPoolExecutor(max_workers=2) as p:rs=list(p.map(lambda _:calcular(c),range(2)))
        assert rs[0]==rs[1]
        with pytest.raises(AccesoDenegado):calcular(c,usuario=replace(c.usuario,id_usuario=str(c.docente)))
        assert calcular(c)==rs[0] and not ops
    finally:
        sa.event.remove(c.engine,'before_cursor_execute',sql);sa.event.remove(c.engine,'commit',commit)


def test_postgresql_puntajes_publicados_inmutables_y_otro_caso_no_recalifica(registro_puntajes):
    c=registro_puntajes;cerrar(c);antes=calcular(c)
    with pytest.raises(IntegrityError):
        with c.sesiones.begin() as s:s.execute(sa.update(ValoracionOpcionModel).where(
            ValoracionOpcionModel.opcion_id==c.version.escenarios[0].preguntas[0].opciones[0].id).values(puntaje=Decimal(1)))
    futura=version_calificable();futura.caso_id=c.version.caso_id;futura.numero=2;futura.docente_creador_id=c.version.docente_creador_id
    from app.modules.cases.infrastructure.models import CasoModel
    from tests.integration.test_cases_history import publicar
    with c.sesiones.begin() as s:
        modelo=CasoRepository(s)._mapear(futura)
        edicion=modelo.versiones.pop()
        familia=s.get(CasoModel,futura.caso_id)
        familia.versiones.append(edicion)
    with c.sesiones.begin() as s:configurar(s,futura)
    publicar(c.sesiones,futura)
    assert calcular(c)==antes


@pytest.mark.parametrize('estado',['EN_CURSO','FINALIZADO_INCOMPLETO'])
def test_no_inventa_cierre_ni_completitud(registro_puntajes,estado):
    c=registro_puntajes
    if estado!='EN_CURSO':cerrar(c,respondidas=1)
    if estado=='EN_CURSO':
        with pytest.raises(EvaluacionInconsistente):calcular(c)
    else:
        # Sustituye el contrato anterior: cierre real sin FIN ahora es PARCIAL v2.
        r=calcular(c);assert r.modalidad.value=='PARCIAL' and r.nota_final==Decimal('50.00')
        assert r.pendientes_con_cero==1 and not r.persistido and not r.oficial


def test_postgresql_publicacion_desigual_revierte_y_legado_no_se_reinterpreta(pg_resultados):
    from sqlalchemy.orm import sessionmaker
    from tests.integration.test_cases_history import publicar
    f=sessionmaker(pg_resultados,expire_on_commit=False);v=version_calificable()
    with f() as s:CasoRepository(s).guardar(v)
    with f.begin() as s:
        configurar(s,v)
        RepositorioGrafoSQLAlchemy(s).configurar(version_id=v.id,docente_id=v.docente_creador_id,
            inicial_id=v.escenarios[0].id,transiciones=((v.escenarios[0].preguntas[0].opciones[0].id,'FIN',None),))
    with pytest.raises(ConfiguracionCalificacionInvalida):publicar(f,v)
    with f() as s:assert s.get(VersionCasoModel,v.id).estado.value=='BORRADOR'
    legado=nuevo()
    with f() as s:CasoRepository(s).guardar(legado)
    publicado=publicar(f,legado)
    from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas
    with f() as s,pytest.raises(ConfiguracionCalificacionInvalida):consultar_configuracion_preguntas(s,version_id=publicado.id)


@pytest.mark.parametrize('configuracion,esperado',[('valida',200),('desigual',422),('fuera_de_escala',400),('precision_perdida',400)])
def test_http_publicar_solo_nuevas_versiones_evaluables_validas(autor,configuracion,esperado):
    from tests.integration.test_cases_graph_authoring import crear, configurar as configurar_http
    a=autor;a.payload['rubric']['versionRegla']=REGLA_PREGUNTAS
    for e in a.payload['scenarios']:
        for o in e['questions'][0]['options']:
            o['valoraciones']={'Análisis':'1.005' if configuracion=='precision_perdida' else 101 if configuracion=='fuera_de_escala' else 100 if o['esCorrecta'] else 0}
    if configuracion in ('fuera_de_escala','precision_perdida'):
        r=a.client.post('/api/v1/cases',headers=a.headers,json=a.payload)
        assert r.status_code==400 and 'no se redondea' in r.text
        return
    vid,body,_=crear(a)
    if configuracion=='desigual':body['transiciones'][0]={'opcion_id':body['transiciones'][0]['opcion_id'],'tipo':'FIN'}
    assert configurar_http(a,vid,body).status_code==200
    r=a.client.post(f'/api/v1/cases/{vid}/publish',headers=a.headers)
    assert r.status_code==esperado,r.text
    if esperado!=200:
        assert a.client.get(f'/api/v1/cases/{vid}',headers=a.headers).json()['estado']=='BORRADOR'
