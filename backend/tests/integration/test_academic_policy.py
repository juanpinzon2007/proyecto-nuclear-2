"""Reglas aprobadas; los mapeos/agregaciones numéricos de ejemplo son SOLO LAB."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.modules.participation.application.academic_policy import PoliticaAcademicaConfirmada, MapeoEscala100
from app.modules.participation.application.result_provenance import canonico, huella, MOTOR_V1_COMPATIBLE
from app.modules.participation.domain.calculador_rubrica import CalculadorRubrica, PoliticaCalculo, FormulaCalculo
from app.modules.participation.domain.evaluation import (
    RubricaEvaluacion,CriterioEvaluable,NivelEvaluable,NivelObtenido,ReferenciaAcademica,
    ModalidadEvaluacion,ContextoEvaluacion,PoliticaEvaluacionPendiente,EvaluacionInconsistente,
)
from app.modules.participation.domain.estrategias_evaluacion import EvaluacionParcialStrategy, EvaluacionAusenciaStrategy
from app.modules.participation.infrastructure.evaluation import crear_evaluacion_8c
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R, ResultadoCriterioModel as RC
from app.modules.participation.infrastructure.individual_feedback import crear_servicio_feedback_individual, consultar_feedback_individual
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM as F
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.application.academic_identity import VinculoAcademico,SistemaAcademico
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado,IntegracionPendiente
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel
from tests.integration.test_evaluation_result_storage import c,pg_resultados,servicio,definicion,capturar_filas  # noqa: F401
from tests.integration.test_evaluation_persisted import MapeoFixture,RutaFixture,argumentos
from app.modules.participation.tests.test_evaluation_domain import contexto
from tests.integration.test_evaluation_feedback import cerrar_fixture
from tests.integration.test_participation_persistence import contexto as contexto_sql
from tests.integration.test_participation_persistence import participacion,intento,FECHA
from tests.integration.test_attempt_state import principal
from tests.integration.test_cases_history import nuevo
from app.modules.cases.domain.entities.caso import NivelRubrica,OpcionRespuesta
from app.modules.participation.infrastructure.models import IntentoModel,PasoSimulacionModel
from types import SimpleNamespace
from datetime import timezone,timedelta
from tests.identity.academic_identity_support import config_alembic,motor_postgresql_desechable

HEAD="20261102_academic_policy"
PARENT="20261102_evaluation_results"


def rubrica(logros,pesos=None):
    pesos=pesos or [Decimal(100)/len(logros)]*len(logros)
    return RubricaEvaluacion(ReferenciaAcademica(1,2,"fixture"),Decimal(100),
        tuple(CriterioEvaluable(i+1,pesos[i],(NivelEvaluable(i+11,Decimal(x)),)) for i,x in enumerate(logros)))


def calculo(r):
    return CalculadorRubrica().calcular(r,tuple(NivelObtenido(c.id_criterio,c.niveles[0].id_nivel) for c in r.criterios),
        PoliticaCalculo("diana-v1",FormulaCalculo.PROMEDIO_IGUALITARIO_100,None,None))


@pytest.mark.parametrize("logro",[0,50,100])
def test_escala_inclusiva_sin_redondeo(logro):
    assert calculo(rubrica([logro])).nota_final==Decimal(logro)


def test_igual_peso_no_reescribe_pesos_historicos():
    r=rubrica([20,100],[Decimal(60),Decimal(40)])
    assert calculo(r).nota_final==Decimal(60)
    assert tuple(c.peso_porcentaje for c in r.criterios)==(Decimal(60),Decimal(40))
    assert {p for _,p in PoliticaAcademicaConfirmada.pesos_efectivos(r)}=={Fraction(1,2)}


def test_tres_criterios_no_se_aproximan_a_33_33():
    r=rubrica([30,60,90],[Decimal(60),Decimal(30),Decimal(10)])
    assert calculo(r).nota_final==Decimal(60)
    assert {p for _,p in PoliticaAcademicaConfirmada.pesos_efectivos(r)}=={Fraction(1,3)}
    with pytest.raises(PoliticaEvaluacionPendiente,match="redondeo"):
        calculo(rubrica([100,100,100],[Decimal(60),Decimal(30),Decimal(10)]))


def test_no_se_inventa_redondeo_ni_escala_alternativa():
    with pytest.raises(PoliticaEvaluacionPendiente):
        PoliticaCalculo("diana",FormulaCalculo.PROMEDIO_IGUALITARIO_100,2,"ROUND_HALF_UP")
    with pytest.raises(EvaluacionInconsistente,match="escala"):
        calculo(replace(rubrica([100]),nota_maxima=Decimal(5)))


def test_logro_finito_de_alta_precision_no_se_redondea():
    logro=Decimal((0,Decimal(5**100).as_tuple().digits,-100))  # 1 / 2**100, exacto
    assert calculo(rubrica([logro])).nota_final==logro


def test_vencido_recibe_ceros_sin_opciones_ficticias():
    ctx=contexto(ModalidadEvaluacion.PARCIAL,completo=False,vencido=True)
    datos=EvaluacionParcialStrategy().preparar(ctx)
    p=PoliticaAcademicaConfirmada()
    preguntas=p.preguntas_para_evaluar(datos=datos,intento=ctx.intento)
    assert preguntas[0].id_opcion==60 and preguntas[0].valor_no_respondida is None
    assert preguntas[1].id_opcion is None and preguntas[1].valor_no_respondida==0
    assert len(ctx.intento.pasos)==1 and datos.evidencias[1].cero_por_ausencia is None
    with pytest.raises(PoliticaEvaluacionPendiente,match="agregación"):
        p.preparar_calculo_para_intento(datos=datos,rubrica=rubrica([100]),intento=ctx.intento)


def test_ausencia_misma_regla_sin_intento_y_sin_nivel_cero_inventado():
    ctx=ContextoEvaluacion(ReferenciaAcademica(1,2,"fixture"),20,ModalidadEvaluacion.AUSENCIA,(50,51),None,True)
    datos=EvaluacionAusenciaStrategy().preparar(ctx)
    p=PoliticaAcademicaConfirmada()
    assert datos.id_intento is None and all(x.valor_no_respondida==0 for x in p.preguntas_para_evaluar(datos=datos,intento=None))
    with pytest.raises(PoliticaEvaluacionPendiente):p.preparar_calculo(datos=datos,rubrica=rubrica([0]))


class ResolucionUnaPreguntaFixture:
    """SOLO laboratorio: una valoración de una pregunta coincide con un nivel."""
    def __init__(self,c):self.c=c
    def resolver(self,*,preguntas,rubrica):
        assert len(preguntas)==1
        q=preguntas[0]
        if q.id_opcion is None:
            assert q.valor_no_respondida==0
            puntos=Decimal(0)
        else:puntos=next(o for o in self.c.q.opciones if o.id==q.id_opcion).valoraciones[rubrica.criterios[0].id_criterio]*20
        nivel=next((n for n in rubrica.criterios[0].niveles if n.logro_porcentaje==puntos),None)
        if nivel is None:raise PoliticaEvaluacionPendiente("No hay nivel real equivalente; no inventarlo")
        return (NivelObtenido(rubrica.criterios[0].id_criterio,nivel.id_nivel),)


def academico(c,**kw):
    return servicio(c,politica=PoliticaAcademicaConfirmada(ResolucionUnaPreguntaFixture(c)),
        mapeo=MapeoEscala100(MapeoFixture()),definicion=definicion(c,version="2",
        mapeo={"escala":"100 aprobada; niveles de ejemplo SOLO LAB"},
        agregacion={"regla":"una pregunta coincide con un nivel SOLO LAB"}),**kw)


def test_100_se_persiste_y_recupera_sin_nota_oficial(c):
    a=academico(c).evaluar(id_estudiante=c.alumno)
    b=academico(c).consultar(id_estudiante=c.alumno)
    assert a==b and a.datos.nota_final==Decimal(100) and not a.oficial
    p=json.loads(a.procedencia)
    assert p["plan"]["politica"]["redondeo"] is None
    assert p["plan"]["politica"]["formula"]=="PROMEDIO_IGUALITARIO_100"
    with c.engine.connect() as s:assert sa.inspect(s).get_columns("resultado_intento")[2]["type"].precision==5


def test_sin_mapeo_agregacion_no_hay_nota_academica_completa(c):
    s=crear_evaluacion_8c(**argumentos(c),mapeo=MapeoFixture(),recorrido=RutaFixture(c))
    d=s.previsualizar_intento(id_estudiante=c.alumno,id_intento=c.ik)
    assert d.nota_final is None and any("agregación" in p for p in d.pendientes)


def docente(c):
    with c.sesiones.begin() as s:
        repo=RepositorioIdentidadAcademicaSQLAlchemy(s)
        repo.agregar_verificado(VinculoAcademico(str(c.docente),SistemaAcademico.CASES,c.version.docente_creador_id))
        sid=s.scalar(sa.select(SesionProgramadaModel.docente_id).where(SesionProgramadaModel.id==c.sesion))
        repo.agregar_verificado(VinculoAcademico(str(c.docente),SistemaAcademico.SCHEDULING,sid))
        return RepositorioUsuariosSQLAlchemy(s).obtener(str(c.docente))


def escribir(c,u,texto):
    return crear_servicio_feedback_individual(usuario=u,crear_sesion=c.sesiones).registrar(u,str(c.pk),texto)


def leer(c,**kw):
    return consultar_feedback_individual(**(dict(usuario=c.usuario,id_participacion=str(c.pk),crear_sesion=c.sesiones)|kw))


def test_feedback_individual_editable_y_privado(c):
    u=docente(c)
    escribir(c,u,"Valoración inicial")
    with c.sesiones() as s:pk=s.scalar(sa.select(F.id_retroalimentacion).where(F.id_participacion==c.pk))
    escribir(c,u,"Valoración corregida")
    assert leer(c).texto=="Valoración corregida"
    with c.sesiones() as s:
        filas=s.execute(sa.select(F.id_retroalimentacion).where(F.id_participacion==c.pk)).all()
        assert filas==[(pk,)]
    otra=cerrar_fixture(contexto_sql(c.engine),opcion=0)
    with pytest.raises(AccesoDenegado):leer(c,usuario=otra.usuario)
    fake=replace(c.usuario,roles=frozenset({Rol.DOCENTE}))
    with pytest.raises(AccesoDenegado):escribir(c,fake,"Suplantación")


def test_docente_ajeno_no_puede_editar_feedback(c):
    u=docente(c);escribir(c,u,"Privado")
    otra=cerrar_fixture(contexto_sql(c.engine),opcion=0);ajeno=docente(otra)
    with pytest.raises(AccesoDenegado):escribir(c,ajeno,"Ataque")
    assert leer(c).texto=="Privado"


def test_feedback_concurrente_una_sola_valoracion(c):
    u=docente(c)
    with ThreadPoolExecutor(max_workers=2) as p:
        a=p.submit(escribir,c,u,"Uno");b=p.submit(escribir,c,u,"Dos")
        a.result(timeout=15);b.result(timeout=15)
    with c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(F).where(F.id_participacion==c.pk))==1
    assert leer(c).texto in {"Uno","Dos"}


def test_feedback_rollback_no_pierde_valoracion_previa(c):
    u=docente(c);escribir(c,u,"Anterior")
    def fallo(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith("INSERT INTO retroalimentacion_docente"):raise RuntimeError("Fallo después del upsert")
    sa.event.listen(c.engine,"after_cursor_execute",fallo)
    try:
        with pytest.raises(RuntimeError):escribir(c,u,"No confirmado")
    finally:sa.event.remove(c.engine,"after_cursor_execute",fallo)
    assert leer(c).texto=="Anterior"


def test_no_reasigna_feedback_por_SQL(c):
    u=docente(c);escribir(c,u,"Privado")
    otra=cerrar_fixture(contexto_sql(c.engine),opcion=0)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:s.execute(sa.update(F).where(F.id_participacion==c.pk).values(id_participacion=otra.pk))


def test_downgrade_no_trunca_nota_100():
    with motor_postgresql_desechable() as e:
        inicializar(e,HEAD)
        c=cerrar_fixture(contexto_sql(e),opcion=0);c.politica_id="fixture-100"
        academico(c).evaluar(id_estudiante=c.alumno)
        with c.engine.begin() as s:
            with pytest.raises(RuntimeError,match="100"):
                with s.begin_nested():command.downgrade(config_alembic(s),PARENT)
        assert academico(c).consultar(id_estudiante=c.alumno).datos.nota_final==100


def test_historia_v1_se_recupera_sin_recalificar(c,monkeypatch):
    r,detalle=capturar_filas(c,monkeypatch)
    p=json.loads(r["procedencia"])
    motor=json.loads((Path(__file__).parents[1]/"fixtures/evaluation_motor_v1.json").read_text(encoding="utf-8"))
    assert huella(canonico(motor))==MOTOR_V1_COMPATIBLE
    p["motor"]=motor;p["motor_documento"]=canonico(motor)
    d=json.loads(p["definicion_documento"]);d["motor_sha256"]=MOTOR_V1_COMPATIBLE
    p["definicion_documento"]=canonico(d)
    r["procedencia"]=canonico(p);r["procedencia_sha256"]=huella(r["procedencia"]);r["politica_hash"]=huella(p["definicion_documento"])
    with c.engine.begin() as s:
        s.execute(R.__table__.insert().values(**r));s.execute(RC.__table__.insert(),detalle)
    antes=servicio(c).consultar(id_estudiante=c.alumno)
    assert antes.datos.nota_final==5
    assert antes.procedencia==r["procedencia"] and antes.sha256==r["procedencia_sha256"]


def test_upgrade_downgrade_vacio_exclusivamente_PG():
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            command.upgrade(config_alembic(s),HEAD)
            assert sa.inspect(s).get_columns("resultado_intento")[2]["type"].precision==5
            command.downgrade(config_alembic(s),PARENT)
            assert "retroalimentacion_docente" not in sa.inspect(s).get_table_names()
            assert sa.inspect(s).get_columns("resultado_intento")[2]["type"].precision==4


def inicializar(e,revision):
    from app.modules.identity.infrastructure.models import RolORM
    with e.begin() as s:
        command.upgrade(config_alembic(s),revision)
        s.execute(sa.insert(RolORM),[dict(id_rol=1,nombre="DOCENTE"),dict(id_rol=2,nombre="ESTUDIANTE")])


def contexto_modificado(e,monkeypatch,*,cero=False,tercera=False):
    import tests.integration.test_assignment_bridge as soporte
    def crear():
        v=nuevo();q=v.escenarios[0].preguntas[0];cr=v.rubrica.criterios[0]
        if cero:cr.niveles.append(NivelRubrica("Sin logro",Decimal(0),"Descriptor de laboratorio"))
        if tercera:q.opciones.append(OpcionRespuesta(3,"Tercera alternativa",False,"Justificación 3",valoraciones={cr.id:Decimal(0)}))
        return v
    with monkeypatch.context() as m:
        m.setattr(soporte,"nuevo",crear)
        return contexto_sql(e)


def test_una_seleccion_sin_limitar_tres_alternativas(pg_resultados,monkeypatch):
    from app.modules.participation.infrastructure.composition import crear_facade_8b
    from app.modules.participation.infrastructure.codecs import FechasPersistencia
    from app.modules.participation.domain.errors import ErrorDominioParticipacion
    from tests.integration.test_steps_uuid import EdicionFixture,RutaFixture as RutaEdicion
    c=contexto_modificado(pg_resultados,monkeypatch,tercera=True)
    c.pk=participacion(c);c.ik=intento(c,c.pk);c.usuario=principal(c)
    with c.engine.begin() as s:s.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(estado="EN_CURSO"))
    def facade():
        return crear_facade_8b(usuario=c.usuario,id_intento=c.ik,fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones,
            reloj=SimpleNamespace(ahora=lambda:FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=1)),
            autorizacion_edicion=EdicionFixture(c),recorrido=RutaEdicion(c))
    q=c.version.escenarios[0].preguntas[0]
    facade().registrar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[2].id)
    with pytest.raises(ErrorDominioParticipacion):
        facade().registrar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[0].id)
    with pytest.raises(ErrorDominioParticipacion):
        facade().modificar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[0].id)
    with c.sesiones() as s:
        filas=s.execute(sa.select(PasoSimulacionModel).where(PasoSimulacionModel.id_intento==c.ik)).scalars().all()
        assert len(filas)==1 and filas[0].id_opcion==q.opciones[2].id
    assert len(q.opciones)==3


def test_parcial_vencido_aplica_cero_con_nivel_real_solo_en_fixture(pg_resultados,monkeypatch):
    c=contexto_modificado(pg_resultados,monkeypatch,cero=True)
    c.pk=participacion(c);c.ik=intento(c,c.pk);c.usuario=principal(c)
    c.q=c.version.escenarios[0].preguntas[0];c.politica_id="fixture-parcial-"+str(c.ik)
    with c.engine.begin() as s:s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik)
        .values(estado="VENCIDO",fin=FECHA+timedelta(minutes=30,microseconds=1)))
    r=academico(c,reloj=SimpleNamespace(ahora=lambda:FECHA.replace(tzinfo=timezone.utc)+timedelta(hours=1))).evaluar(id_estudiante=c.alumno)
    assert r.datos.modalidad==ModalidadEvaluacion.PARCIAL and r.datos.nota_final==0
    p=json.loads(r.procedencia)
    assert p["preguntas_aplicadas"][0]["valor_no_respondida"]=="0"
    assert p["preguntas_aplicadas"][0]["id_opcion"] is None
    with c.sesiones() as s:assert s.scalar(sa.select(sa.func.count()).select_from(PasoSimulacionModel).where(PasoSimulacionModel.id_intento==c.ik))==0


def test_migracion_preserva_nota_y_huellas_legacy(monkeypatch):
    with motor_postgresql_desechable() as e:
        inicializar(e,PARENT)
        c=cerrar_fixture(contexto_sql(e),opcion=0);c.politica_id="fixture-legacy"
        r,det=capturar_filas(c,monkeypatch)
        with e.begin() as s:
            s.execute(R.__table__.insert().values(**r));s.execute(RC.__table__.insert(),det)
        antes=servicio(c).consultar(id_estudiante=c.alumno)
        with e.begin() as s:command.upgrade(config_alembic(s),HEAD)
        despues=servicio(c).consultar(id_estudiante=c.alumno)
        assert antes==despues and despues.datos.nota_final==5


def test_dos_alumnos_misma_asignacion_feedback_individual(c):
    from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
    from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
    u=docente(c)
    otra=contexto_sql(c.engine)
    with c.sesiones.begin() as s:
        grupo=s.get(AsignacionCasoModel,c.datos["id_asignacion"]).id_grupo
        m=GrupoEstudianteORM(id_grupo=grupo,id_estudiante=otra.alumno,fecha_ingreso=FECHA)
        s.add(m);s.flush()
        conv=crear_convocatoria(s,sesion_id=c.sesion,estudiante_id=otra.uuid)
        otra.datos=otra.datos|dict(id_grupo_estudiante=m.id_grupo_estudiante,id_asignacion=c.datos["id_asignacion"],convocatoria_id=conv.convocatoria_id)
    otra.version=c.version;otra.sesion=c.sesion
    cerrar_fixture(otra,opcion=0)
    escribir(c,u,"Comentario primero");escribir(otra,u,"Comentario segundo")
    assert leer(c).texto=="Comentario primero" and leer(otra).texto=="Comentario segundo"
    with pytest.raises(AccesoDenegado):leer(c,id_participacion=str(otra.pk))


def test_feedback_para_convocado_sin_intento_no_crea_intento(pg_resultados):
    c=contexto_sql(pg_resultados)
    c.pk=participacion(c);c.usuario=principal(c)
    with c.engine.begin() as s:
        s.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(estado="FINALIZADO"))
    u=docente(c)
    escribir(c,u,"Valoración individual para el estudiante convocado")
    with c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(IntentoModel).where(IntentoModel.id_participacion==c.pk))==0
        f=s.execute(sa.select(F.__table__).where(F.id_participacion==c.pk)).mappings().one()
        assert f["id_asignacion"]==c.datos["id_asignacion"] and f["id_profesor"]==c.docente
    # La escritura individual no certifica ausencia ni habilita la entrega sin
    # resolver las condiciones académicas; no crea nota ni un intento ficticio.
    with pytest.raises(AccesoDenegado):leer(c)
