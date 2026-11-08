"""Persistencia técnica 8C real. Solo PostgreSQL nuevo; reglas SOLO de laboratorio."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timezone, timedelta
from decimal import Decimal
import json
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, DBAPIError

from app.db.models import registrar_modelos_integrados
from app.modules.identity.infrastructure.models import RolORM
from app.modules.participation.application.errors import AccesoDenegado, ConflictoActualizacion
from app.modules.participation.application.result_provenance import DefinicionPoliticaLaboratorio, canonico, huella
from app.modules.participation.domain.evaluation import EvaluacionInconsistente, PoliticaEvaluacionPendiente
from app.modules.participation.domain.calculador_rubrica import PlanCalculo, PoliticaCalculo, FormulaCalculo, NivelObtenido
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.persisted_evaluation import EvaluacionPersistenteLaboratorio
from app.modules.participation.infrastructure.result_repository import RepositorioResultadosTecnicosSQLAlchemy
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R, ResultadoCriterioModel as C
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic
from tests.integration.test_participation_persistence import contexto, FECHA
from tests.integration.test_participation_persistence import participacion, intento
from tests.integration.test_attempt_state import principal
from tests.integration.test_evaluation_feedback import cerrar_fixture
from tests.integration.test_evaluation_persisted import RutaFixture, MapeoFixture, PoliticaFixture

HEAD="20261102_academic_policy"
PARENT="20261102_steps_uuid"


@pytest.fixture(scope="module")
def pg_resultados():
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),"head")
            s.execute(sa.insert(RolORM),[dict(id_rol=1,nombre="DOCENTE"),dict(id_rol=2,nombre="ESTUDIANTE")])
        yield e


@pytest.fixture
def c(pg_resultados):
    c=cerrar_fixture(contexto(pg_resultados),opcion=0)
    c.politica_id="fixture-8c-"+uuid4().hex
    return c


def definicion(c, **cambios):
    return DefinicionPoliticaLaboratorio.crear(**(dict(identificador=c.politica_id,version="1",
        clasificacion={"regla":"completa forzada SOLO para el caso sintético cerrado"},
        mapeo={"maximo":"5","logro":"puntaje por 20, SOLO laboratorio"},
        agregacion={"regla":"única pregunta de fixture determina nivel por criterio"})|cambios))


def servicio(c, **kw):
    return EvaluacionPersistenteLaboratorio(**(dict(usuario=c.usuario,id_intento=c.ik,
        fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones,
        reloj=SimpleNamespace(ahora=lambda:FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=3)),
        definicion=definicion(c),politica=PoliticaFixture(c),mapeo=MapeoFixture(),recorrido=RutaFixture(c))|kw))


def evaluar(c, **kw): return servicio(c,**kw).evaluar(id_estudiante=c.alumno)
def consultar(c, **kw): return servicio(c,**kw).consultar(id_estudiante=c.alumno)


def contar(c):
    with c.engine.connect() as s:
        return s.scalar(sa.select(sa.func.count()).select_from(R).where(R.id_intento==c.ik))


def test_evaluar_guardar_y_recuperar_otra_session(c):
    resultado=evaluar(c)
    recuperado=consultar(c)
    assert resultado==recuperado and resultado.datos.nota_final==Decimal("5.00")
    assert not recuperado.oficial
    p=json.loads(recuperado.procedencia)
    assert huella(recuperado.procedencia)==recuperado.sha256
    assert p["fuente_rubrica"]["rubrica_id"]==str(c.version.rubrica.id)
    assert p["fuente_rubrica"]["version_id"]==str(c.version.id)
    assert p["plan"]["politica"]["formula"]=="SUMA_PONDERADA_PORCENTUAL"
    d=json.loads(p["definicion_documento"])
    assert d["version"]=="1" and d["implementaciones"]["mapeo"] and d["motor_sha256"]
    with c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(C).where(C.id_resultado==resultado.id_resultado))==1
        assert RepositorioResultadosTecnicosSQLAlchemy(s,alcance=None,fechas=None).obtener_definitiva()==None


def test_duplicado_no_sobrescribe(c):
    a=evaluar(c)
    with pytest.raises(ConflictoActualizacion): evaluar(c)
    assert contar(c)==1 and consultar(c)==a


@pytest.mark.parametrize("actor",["cuenta","docente","contexto"])
def test_titularidad_real_en_evaluacion_y_lectura(c,actor):
    evaluar(c)
    cambios={"cuenta":dict(id_usuario="2147483647"),"docente":dict(id_usuario=str(c.docente)),
        "contexto":dict(id_convocatoria=str(uuid4()))}[actor]
    with pytest.raises(AccesoDenegado): evaluar(c,usuario=replace(c.usuario,**cambios))
    with pytest.raises(AccesoDenegado): consultar(c,usuario=replace(c.usuario,**cambios))
    assert contar(c)==1


def test_no_guarda_pendiente(c):
    with pytest.raises(PoliticaEvaluacionPendiente):
        evaluar(c,politica=PoliticaFixture(c,calculo=False))
    assert contar(c)==0


def test_definicion_versionada_no_es_mutable_ni_solo_nombre(c):
    parametros={"maximo":"5"}
    d=definicion(c,mapeo=parametros)
    parametros["maximo"]="100"
    assert json.loads(d.documento)["mapeo"]["maximo"]=="5"
    with pytest.raises(EvaluacionInconsistente): DefinicionPoliticaLaboratorio(canonico(dict(id="nombre",version="1")))


def test_misma_identidad_version_no_admite_otra_definicion(c):
    evaluar(c)
    otra=cerrar_fixture(contexto(c.engine),opcion=0);otra.politica_id=c.politica_id
    with pytest.raises(IntegrityError): evaluar(otra,definicion=definicion(otra,mapeo={"otra":"definicion"}))
    assert contar(otra)==0


def capturar_filas(c,monkeypatch):
    class Capturada(Exception): pass
    original=RepositorioResultadosTecnicosSQLAlchemy.guardar_tecnico
    captura={}
    def guardar(self,**kw):
        r=original(self,**kw)
        captura["r"]=dict(self.sesion.execute(sa.select(R.__table__).where(R.id_resultado==r.id_resultado)).mappings().one())
        captura["c"]=[dict(x) for x in self.sesion.execute(sa.select(C.__table__).where(C.id_resultado==r.id_resultado)).mappings()]
        raise Capturada()
    with monkeypatch.context() as m:
        m.setattr(RepositorioResultadosTecnicosSQLAlchemy,"guardar_tecnico",guardar)
        with pytest.raises(Capturada): evaluar(c)
    assert contar(c)==0
    return captura["r"],captura["c"]


@pytest.mark.parametrize("campo",["caso_id","id_caso","version_caso_id","rubrica_id","version_regla","ambito","procedencia_sha256"])
def test_SQL_cabeceras_invalidas_rechazadas(c,monkeypatch,campo):
    r,det=capturar_filas(c,monkeypatch)
    r[campo] = ("OFICIAL" if campo=="ambito" else "x" if campo=="version_regla" else "0"*64
        if campo=="procedencia_sha256" else 2147483647 if campo=="id_caso" else uuid4())
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            s.execute(R.__table__.insert().values(**r))
            s.execute(C.__table__.insert(),det)
    assert contar(c)==0


@pytest.mark.parametrize("campo",["id_criterio","id_nivel","rubrica_id"])
def test_FK_compuestas_impiden_relaciones_ajenas_existentes(c,monkeypatch,campo):
    r,det=capturar_filas(c,monkeypatch)
    otra=contexto(c.engine).version.rubrica
    det[0][campo] = otra.id if campo=="rubrica_id" else otra.criterios[0].id if campo=="id_criterio" else otra.criterios[0].niveles[0].id
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            s.execute(R.__table__.insert().values(**r));s.execute(C.__table__.insert(),det)
    assert contar(c)==0


def test_constraint_diferida_rechaza_cabecera_sin_detalle(c,monkeypatch):
    r,_=capturar_filas(c,monkeypatch)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:s.execute(R.__table__.insert().values(**r))
    assert contar(c)==0


@pytest.mark.parametrize("tabla",[R,C])
@pytest.mark.parametrize("operacion",["update","delete","truncate"])
def test_historia_inmutable_por_SQL(c,tabla,operacion):
    evaluar(c)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            if operacion=="truncate":s.execute(sa.text("TRUNCATE "+tabla.__tablename__+" CASCADE"))
            elif operacion=="delete":s.execute(sa.delete(tabla))
            else:s.execute(sa.update(tabla).values(**({"ambito":"OFICIAL"} if tabla is R else {"puntaje_obtenido":0})))
    assert contar(c)==1


def test_rollback_tras_cabecera_no_deja_parciales(c):
    def fallo(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith("INSERT INTO resultado_criterio"):raise RuntimeError("Fallo simulado tras cabecera")
    sa.event.listen(c.engine,"before_cursor_execute",fallo)
    try:
        with pytest.raises(RuntimeError,match="simulado"):evaluar(c)
    finally:sa.event.remove(c.engine,"before_cursor_execute",fallo)
    assert contar(c)==0


def test_concurrencia_mismo_intento_confirma_solo_uno(c):
    barrera=Barrier(2)
    def ejecutar():
        barrera.wait(timeout=5)
        try:evaluar(c);return "guardado"
        except ConflictoActualizacion:return "duplicado"
    with ThreadPoolExecutor(max_workers=2) as p:
        a=p.submit(ejecutar);b=p.submit(ejecutar)
        assert sorted([a.result(timeout=15),b.result(timeout=15)])==["duplicado","guardado"]
    assert contar(c)==1


def test_upgrade_downgrade_en_laboratorio_vacio():
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            command.upgrade(config_alembic(s),"head")
            assert compare_metadata(MigrationContext.configure(s),registrar_modelos_integrados())==[]
            assert len(registrar_modelos_integrados().tables)==36
            assert len(sa.inspect(s).get_foreign_keys("resultado_criterio"))==3
            command.downgrade(config_alembic(s),PARENT)
            assert "resultado_intento" not in sa.inspect(s).get_table_names()
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"))==31
            command.upgrade(config_alembic(s),HEAD)


def test_downgrade_con_resultados_conserva_historia(c):
    evaluar(c)
    with c.engine.begin() as s:
        with pytest.raises(RuntimeError,match="resultados historicos"):
            with s.begin_nested():command.downgrade(config_alembic(s),PARENT)
    assert contar(c)==1


def test_SQL_duplicado_de_criterio_es_rechazado(c,monkeypatch):
    r,det=capturar_filas(c,monkeypatch)
    copia=det[0].copy();copia.pop("id_resultado_criterio")
    with pytest.raises(IntegrityError) as e:
        with c.engine.begin() as s:
            s.execute(R.__table__.insert().values(**r))
            s.execute(C.__table__.insert(),det)
            s.execute(C.__table__.insert().values(**copia))
    assert e.value.orig.diag.constraint_name=="uq_8c_resultado_criterio"
    assert contar(c)==0


def test_concurrencia_definicion_mismo_id_version_serializa(c):
    otra=cerrar_fixture(contexto(c.engine),opcion=0);otra.politica_id=c.politica_id
    barrera=Barrier(2)
    def ejecutar(caso,defn):
        barrera.wait(timeout=5)
        try:evaluar(caso,definicion=defn);return "guardado"
        except IntegrityError:return "rechazado"
    with ThreadPoolExecutor(max_workers=2) as p:
        a=p.submit(ejecutar,c,definicion(c));b=p.submit(ejecutar,otra,definicion(otra,mapeo={"cambio":"no compatible"}))
        assert sorted([a.result(timeout=15),b.result(timeout=15)])==["guardado","rechazado"]
    assert contar(c)+contar(otra)==1


def test_no_evalua_intento_activo(pg_resultados):
    c=contexto(pg_resultados);c.pk=participacion(c);c.ik=intento(c,c.pk)
    c.usuario=principal(c);c.q=c.version.escenarios[0].preguntas[0];c.politica_id=uuid4().hex
    with pytest.raises(EvaluacionInconsistente): evaluar(c)
    assert contar(c)==0


def test_no_redondea_detalle_para_hacerlo_caber(c):
    class MapeoFraccional(MapeoFixture):
        def preparar(self,f):
            r=super().preparar(f);cr=r.criterios[0]
            return replace(r,nota_maxima=Decimal("5.01"),criterios=(replace(cr,niveles=(replace(cr.niveles[0],logro_porcentaje=Decimal("33.33")),)),))
    class PoliticaFraccional(PoliticaFixture):
        def preparar_calculo(self,*,datos,rubrica):
            return PlanCalculo((NivelObtenido(rubrica.criterios[0].id_criterio,rubrica.criterios[0].niveles[0].id_nivel),),
                PoliticaCalculo("fixture-fraccional",FormulaCalculo.SUMA_PONDERADA_PORCENTUAL,2,"ROUND_HALF_UP"))
    with pytest.raises(EvaluacionInconsistente,match="precisión"):
        evaluar(c,mapeo=MapeoFraccional(),politica=PoliticaFraccional(c),
            definicion=definicion(c,mapeo={"maximo":"5.01","logro":"33.33 SOLO laboratorio"}))
    assert contar(c)==0


@pytest.mark.parametrize("campo",["motor","nota","plan","fuente","evidencia"])
def test_verificacion_rechaza_procedencia_alterada(c,campo):
    r=evaluar(c);p=json.loads(r.procedencia)
    if campo=="motor":p["motor"]={}
    if campo=="nota":p["datos"]["nota_final"]="4.00"
    if campo=="plan":p["plan"]["niveles"][0]["id_nivel"]=str(uuid4())
    if campo=="fuente":p["fuente_rubrica"]["version_regla"]="otra"
    if campo=="evidencia":p["datos"]["evidencias"][0]["id_decision"]=str(uuid4())
    s=servicio(c)
    with s.trabajo as t:
        with pytest.raises((EvaluacionInconsistente,PoliticaEvaluacionPendiente)):
            t.resultados._verificar(canonico(p))
    assert consultar(c)==r


def test_repositorio_no_abre_base_no_identificada():
    sesion=SimpleNamespace(in_transaction=lambda:True,
        get_bind=lambda:SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),scalar=lambda _:"base_compartida")
    repo=RepositorioResultadosTecnicosSQLAlchemy(sesion,alcance=None,fechas=None)
    with pytest.raises(PoliticaEvaluacionPendiente,match="identificada"):repo._laboratorio()


def test_resultado_laboratorio_nunca_se_obtiene_por_contrato_oficial(c):
    evaluar(c)
    s=servicio(c)
    with s.trabajo as t:
        assert t.resultados.obtener_definitiva(id_participacion=c.pk,id_intento=c.ik) is None
        with pytest.raises(PoliticaEvaluacionPendiente,match="oficiales"):
            t.resultados.agregar_definitiva(consultar(c).datos)


def test_snapshot_repeatable_read_no_permite_escritura(c,monkeypatch):
    r,det=capturar_filas(c,monkeypatch)
    with pytest.raises(DBAPIError) as e:
        with c.engine.connect().execution_options(isolation_level="REPEATABLE READ") as s:
            with s.begin():
                s.execute(R.__table__.insert().values(**r))
                s.execute(C.__table__.insert(),det)
    assert e.value.orig.sqlstate=="40001" and contar(c)==0


def test_SQL_no_habilita_resultados_en_otra_base_del_mismo_laboratorio(c,monkeypatch):
    r,_=capturar_filas(c,monkeypatch)
    # Recurso NUEVO del contenedor propio; no se usa ninguna base preexistente.
    nombre="sps_eval_denegada_"+uuid4().hex
    with c.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as s:
        s.exec_driver_sql("CREATE DATABASE "+nombre)
    motor=sa.create_engine(c.engine.url.set(database=nombre))
    try:
        with motor.begin() as s:
            assert sa.inspect(s).get_table_names()==[]
            command.upgrade(config_alembic(s),HEAD)
        with pytest.raises(IntegrityError,match="laboratorio identificado"):
            with motor.begin() as s:s.execute(R.__table__.insert().values(**r))
    finally: motor.dispose()
    # El fixture elimina el contenedor completo y por tanto ambas bases propias.
