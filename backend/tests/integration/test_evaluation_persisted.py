"""8C: SQL real; toda regla académica positiva de este archivo es SOLO fixture.

SQLite prueba lecturas, no locks. PostgreSQL es nuevo/destruible y usa migraciones.
No hay resultado oficial ni repositorio ficticio de resultados en esta composición.
"""
from dataclasses import replace
from datetime import timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.modules.cases.application.evaluation_snapshot import consultar_rubrica_historica
from app.modules.cases.infrastructure.models import CasoModel, ValoracionOpcionModel
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import AccesoDenegado, RecursoNoDisponible
from app.modules.participation.domain.calculador_rubrica import PlanCalculo, PoliticaCalculo, FormulaCalculo
from app.modules.participation.domain.evaluation import (
    ReferenciaAcademica, RubricaEvaluacion, CriterioEvaluable, NivelEvaluable, NivelObtenido,
    ModalidadEvaluacion, PoliticaEvaluacionPendiente, EvaluacionInconsistente,
)
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.evaluation import consultar_evidencias_8c, crear_evaluacion_8c
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente
from app.modules.participation.infrastructure.models import PasoSimulacionModel, IntentoModel
from tests.integration.test_participation_persistence import (
    datos, motor, laboratorio_pg, participacion, intento, FECHA,  # noqa: F401
)
from tests.integration.test_attempt_state import principal
from tests.integration.test_cases_history import nuevo, publicar


@pytest.fixture
def registro(datos):
    c = datos
    c.pk = participacion(c)
    c.ik = intento(c, c.pk)
    c.usuario = principal(c)
    c.q = c.version.escenarios[0].preguntas[0]
    with c.engine.begin() as s:
        s.execute(PasoSimulacionModel.__table__.insert().values(id_intento=c.ik, id_decision=c.q.id,
            id_opcion=c.q.opciones[0].id, numero_paso=1, registrado_en=FECHA+timedelta(seconds=60),
            tiempo_segundos=60, reflexion_estudiante="Evidencia sintética"))
        s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik)
            .values(estado="FINALIZADO", fin=FECHA+timedelta(minutes=2)))
    return c


def argumentos(c):
    return dict(usuario=c.usuario, id_intento=c.ik, fechas=FechasPersistencia(timezone.utc), crear_sesion=c.sesiones)


class RutaFixture:
    """Lista explícita del caso sintético; no ruta inferida del orden editorial."""
    def __init__(self, c): self.ids = (c.q.id,)
    def obtener(self, **_): return RecorridoAplicable(self.ids, True)
    def validar_cambio(self, **_): raise AssertionError("8C no debe editar respuestas")


class MapeoFixture:
    """Convención SOLO de laboratorio: máximo 5 y puntaje 0..5 -> porcentaje."""
    def preparar(self, f):
        return RubricaEvaluacion(ReferenciaAcademica(f.id_caso_academico, f.rubrica_id, f.referencia_versionada),
            Decimal(5), tuple(CriterioEvaluable(c.id, c.peso,
                tuple(NivelEvaluable(n.id, n.puntaje*Decimal(20)) for n in c.niveles)) for c in f.criterios))


class PoliticaFixture:
    """Un nivel por criterio según única valoración de la pregunta de fixture.

    No agrega respuestas, no define parciales/timeout ni equivale a una política SPS.
    """
    def __init__(self, c, modalidad=ModalidadEvaluacion.COMPLETA, calculo=True):
        self.c, self.modalidad, self.calculo = c, modalidad, calculo
    def clasificar(self, **_): return self.modalidad
    def preparar_calculo(self, *, datos, rubrica):
        if not self.calculo: raise PoliticaEvaluacionPendiente("Fórmula parcial de fixture no definida")
        puntajes = self.c.q.opciones[0].valoraciones
        niveles = tuple(NivelObtenido(cr.id_criterio, next(n.id_nivel for n in cr.niveles
            if n.logro_porcentaje == puntajes[cr.id_criterio]*Decimal(20))) for cr in rubrica.criterios)
        return PlanCalculo(niveles, PoliticaCalculo("fixture-solo-laboratorio-8c-v1",
            FormulaCalculo.SUMA_PONDERADA_PORCENTUAL, 2, ROUND_HALF_UP))


def servicio(c, **cambios):
    return crear_evaluacion_8c(**argumentos(c), **(dict(recorrido=RutaFixture(c), mapeo=MapeoFixture(),
        politica=PoliticaFixture(c)) | cambios))


def vista(c, **cambios):
    return servicio(c, **cambios).previsualizar_intento(id_estudiante=c.alumno, id_intento=c.ik)


def test_evidencias_historicas_reales_sin_calificacion(registro):
    c = registro
    a = consultar_evidencias_8c(**argumentos(c))
    b = consultar_evidencias_8c(**argumentos(c))  # Session nueva
    assert a == b
    assert a.intento.pasos[0].id_decision == c.q.id
    assert a.intento.pasos[0].id_opcion == c.q.opciones[0].id
    assert a.rubrica.rubrica_id == c.version.rubrica.id
    assert a.rubrica.version_id == c.version.id
    assert a.rubrica.version_regla == c.version.rubrica.version_regla
    assert isinstance(a.rubrica.criterios[0].id, UUID)
    assert a.rubrica.criterios[0].niveles[0].puntaje == Decimal(5)
    assert not hasattr(a, "nota_final") and not hasattr(a.rubrica, "nota_maxima")
    assert all(v.criterio_id in {cr.id for cr in a.rubrica.criterios} for v in a.rubrica.valoraciones)


def test_motor_existente_calcula_UUID_reproducible_SOLO_con_politica_fixture(registro):
    c = registro
    a, b = vista(c), vista(c)
    assert a == b and a.nota_final == Decimal("5.00")
    assert a.modalidad == ModalidadEvaluacion.COMPLETA and a.lista_para_persistir
    assert a.referencia.id_rubrica == c.version.rubrica.id
    assert a.referencia.version == f"{c.version.id}:{c.version.rubrica.version_regla}"
    assert a.evidencias[0].id_decision == c.q.id and a.evidencias[0].id_opcion == c.q.opciones[0].id
    assert a.criterios[0].id_criterio == c.version.rubrica.criterios[0].id
    # Candidato listo matemáticamente NO es confirmación ni publicación.
    with pytest.raises(MapeoPersistenciaPendiente):
        servicio(c).evaluar_intento(id_estudiante=c.alumno, id_intento=c.ik)


@pytest.mark.parametrize("faltante", ["mapeo", "recorrido", "politica"])
def test_politicas_reales_ausentes_cierran_sin_nota(registro, faltante):
    if faltante == "politica":
        d=vista(registro, politica=None)
        assert d.nota_final is None and d.pendientes
    else:
        with pytest.raises(PoliticaEvaluacionPendiente): vista(registro, **{faltante: None})


def test_sin_formula_no_inventa_calculo_parcial(registro):
    c = registro
    d = vista(c, politica=PoliticaFixture(c, modalidad=ModalidadEvaluacion.PARCIAL, calculo=False))
    assert d.modalidad == ModalidadEvaluacion.PARCIAL
    assert d.nota_final is None and d.pendientes
    assert d.evidencias[0].id_opcion == c.q.opciones[0].id
    assert d.evidencias[0].cero_por_ausencia is None


def test_un_intento_no_se_convierte_en_ausencia(registro):
    c = registro
    with pytest.raises(EvaluacionInconsistente):
        vista(c, politica=PoliticaFixture(c, modalidad=ModalidadEvaluacion.AUSENCIA))
    with pytest.raises(EvaluacionInconsistente):
        servicio(c).evaluar_ausencia(id_estudiante=c.alumno, id_participacion=c.pk)


@pytest.mark.parametrize("cambio", ["rubrica", "version", "criterio", "nivel", "peso"])
def test_mapeo_no_sustituye_referencia_o_pertenencia(registro, cambio):
    class Ajeno(MapeoFixture):
        def preparar(self, f):
            r = super().preparar(f)
            if cambio=="rubrica": return replace(r, referencia=replace(r.referencia, id_rubrica=uuid4()))
            if cambio=="version": return replace(r, referencia=replace(r.referencia, version="otra-regla"))
            c = r.criterios[0]
            if cambio=="criterio": c = replace(c, id_criterio=uuid4())
            if cambio=="nivel": c = replace(c, niveles=(replace(c.niveles[0], id_nivel=uuid4()),))
            if cambio=="peso": c = replace(c, peso_porcentaje=Decimal(99))
            return replace(r, criterios=(c,))
    with pytest.raises(EvaluacionInconsistente): vista(registro, mapeo=Ajeno())


@pytest.mark.parametrize("cambio", ["cuenta", "convocatoria", "parametro"])
def test_titularidad_y_contexto_no_son_elegibles_por_cliente(registro, cambio):
    c = registro
    if cambio=="parametro":
        with pytest.raises(AccesoDenegado):
            servicio(c).previsualizar_intento(id_estudiante=c.alumno+10000, id_intento=c.ik)
    else:
        usuario = replace(c.usuario, **({"id_usuario":str(c.alumno+10000)} if cambio=="cuenta"
                                      else {"id_convocatoria":str(uuid4())}))
        with pytest.raises(AccesoDenegado): consultar_evidencias_8c(**(argumentos(c)|dict(usuario=usuario)))


def test_intento_inexistente_rechazado(registro):
    with pytest.raises(RecursoNoDisponible):
        consultar_evidencias_8c(**(argumentos(registro)|dict(id_intento=2147483647)))


def test_no_evalua_intento_activo_ni_lo_vence(datos):
    c = datos
    c.pk=participacion(c); c.ik=intento(c,c.pk); c.usuario=principal(c)
    with pytest.raises(EvaluacionInconsistente): consultar_evidencias_8c(**argumentos(c))
    with pytest.raises(EvaluacionInconsistente):
        crear_evaluacion_8c(**argumentos(c)).previsualizar_intento(id_estudiante=c.alumno, id_intento=c.ik)
    with c.engine.connect() as s:
        assert s.scalar(sa.select(IntentoModel.estado).where(IntentoModel.id_intento==c.ik)) == "EN_CURSO"


def test_historia_no_se_sustituye_por_publicacion_posterior(registro):
    c = registro
    antes = consultar_evidencias_8c(**argumentos(c))
    futura=nuevo(); futura.caso_id=c.version.caso_id; futura.numero=2
    futura.docente_creador_id=c.version.docente_creador_id
    with c.sesiones.begin() as s:
        modelo=CasoRepository(s)._mapear(futura)
        edicion=modelo.versiones.pop()
        familia=s.get(CasoModel,futura.caso_id)
        familia.versiones.append(edicion)
    publicar(c.sesiones,futura)
    assert consultar_evidencias_8c(**argumentos(c)) == antes
    with c.sesiones() as s:
        assert consultar_rubrica_historica(s, version_id=futura.id).rubrica_id != antes.rubrica.rubrica_id


def test_fallo_fuente_revierte_y_no_es_resultado_pendiente_inventado(registro, monkeypatch):
    import app.modules.participation.infrastructure.evaluation as modulo
    def fallo(db, **_):
        assert db.in_transaction()
        raise SQLAlchemyError("Fallo simulado de infraestructura")
    monkeypatch.setattr(modulo, "consultar_rubrica_historica", fallo)
    with pytest.raises(SQLAlchemyError): consultar_evidencias_8c(**argumentos(registro))
    with pytest.raises(SQLAlchemyError): vista(registro)


def test_previsualizacion_no_confirma_y_no_crea_tablas(registro):
    c = registro; commits=[]; rollbacks=[]
    class Sesion(c.sesiones.class_): pass
    sa.event.listen(Sesion, "after_commit", lambda _: commits.append(True))
    sa.event.listen(Sesion, "after_rollback", lambda _: rollbacks.append(True))
    fabrica=sa.orm.sessionmaker(c.engine, class_=Sesion)
    args=argumentos(c)|dict(crear_sesion=fabrica)
    consultar_evidencias_8c(**args)
    motor=crear_evaluacion_8c(**args, recorrido=RutaFixture(c), mapeo=MapeoFixture(), politica=PoliticaFixture(c))
    motor.previsualizar_intento(id_estudiante=c.alumno, id_intento=c.ik)
    assert not commits and len(rollbacks)==2
    tablas=sa.inspect(c.engine).get_table_names()
    assert {"resultado_intento", "resultado_criterio"} <= set(tablas)
    assert "resultado_participacion" not in tablas
    with c.engine.connect() as s:
        assert s.scalar(sa.text("SELECT count(*) FROM resultado_intento")) == 0


@pytest.mark.parametrize("identificador", [True, 0, -1, "uuid-no-convertible", UUID(int=0)])
def test_UUID_no_relaja_validacion_de_identificadores(identificador):
    with pytest.raises(EvaluacionInconsistente): NivelObtenido(identificador, uuid4())
    with pytest.raises(EvaluacionInconsistente): NivelEvaluable(identificador, Decimal(100))


def test_valoracion_entre_ediciones_rechazada_en_SQL_o_en_lectura(registro):
    c = registro; otra = nuevo()
    with c.sesiones() as s: CasoRepository(s).guardar(otra)
    publicar(c.sesiones, otra)
    valores=dict(opcion_id=c.q.opciones[0].id, criterio_id=otra.rubrica.criterios[0].id, puntaje=Decimal(5))
    if c.engine.dialect.name == "postgresql":
        with pytest.raises(IntegrityError):
            with c.engine.begin() as s: s.execute(sa.insert(ValoracionOpcionModel).values(**valores))
        assert consultar_evidencias_8c(**argumentos(c)).rubrica.rubrica_id == c.version.rubrica.id
    else:
        # SQLite no reproduce los triggers PostgreSQL. Se demuestra por separado
        # el rechazo de la fuente ante una relación que las FK simples permiten.
        with c.engine.begin() as s: s.execute(sa.insert(ValoracionOpcionModel).values(**valores))
        with pytest.raises(EvaluacionInconsistente): consultar_evidencias_8c(**argumentos(c))


def test_opcion_de_otra_version_no_se_convierte_en_evidencia(registro):
    c = registro; otra = nuevo()
    with c.sesiones() as s: CasoRepository(s).guardar(otra)
    publicar(c.sesiones, otra)
    cambio=dict(id_decision=otra.escenarios[0].preguntas[0].id,
                id_opcion=otra.escenarios[0].preguntas[0].opciones[0].id)
    stmt=sa.update(PasoSimulacionModel).where(PasoSimulacionModel.id_intento==c.ik).values(**cambio)
    if c.engine.dialect.name == "postgresql":
        with pytest.raises(IntegrityError):
            with c.engine.begin() as s: s.execute(stmt)
    else:
        with c.engine.begin() as s: s.execute(stmt)
        with pytest.raises(AccesoDenegado): consultar_evidencias_8c(**argumentos(c))


def test_vencido_es_parcial_por_RN14_sin_formula_ni_ausencia_inventada(datos):
    c=datos; c.pk=participacion(c); c.ik=intento(c,c.pk); c.usuario=principal(c)
    c.q=c.version.escenarios[0].preguntas[0]
    with c.engine.begin() as s:
        s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik).values(
            estado="VENCIDO",fin=FECHA+timedelta(minutes=30,microseconds=1)))
    assert consultar_evidencias_8c(**argumentos(c)).intento.estado.value == "VENCIDO"
    # RN-14 centralizada, p. 7: vencimiento -> parcial. No define fórmula ni
    # penalización; cambia la expectativa previa a partir de esta evidencia.
    parcial=vista(c,politica=None)
    assert parcial.modalidad == ModalidadEvaluacion.PARCIAL
    assert parcial.nota_final is None and parcial.pendientes
    assert parcial.evidencias[0].id_opcion is None
    assert parcial.evidencias[0].cero_por_ausencia is None
    with pytest.raises(EvaluacionInconsistente):
        vista(c,politica=PoliticaFixture(c,modalidad=ModalidadEvaluacion.COMPLETA))


def test_fuente_y_repositorio_comparten_la_sesion_transaccional(registro,monkeypatch):
    import app.modules.participation.infrastructure.evaluation as modulo
    original=modulo.consultar_rubrica_historica
    sesiones=[]
    def consultar(db,**kw):
        assert db.in_transaction()
        sesiones.append(db)
        return original(db,**kw)
    monkeypatch.setattr(modulo,"consultar_rubrica_historica",consultar)
    def fabrica():
        s=registro.sesiones()
        sesiones.append(s)
        return s
    motor=crear_evaluacion_8c(**(argumentos(registro)|dict(crear_sesion=fabrica)),
        recorrido=RutaFixture(registro),mapeo=MapeoFixture(),politica=PoliticaFixture(registro))
    motor.previsualizar_intento(id_estudiante=registro.alumno,id_intento=registro.ik)
    assert len(sesiones)==2 and sesiones[0] is sesiones[1]
