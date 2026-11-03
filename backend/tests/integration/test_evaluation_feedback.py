"""Feedback histórico interno: datos SQL reales, sin notas/publicación ni reglas ficticias."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

from app.modules.cases.application.answer_feedback import consultar_explicaciones_seleccionadas
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.participation.application.errors import AccesoDenegado, RecursoNoDisponible
from app.modules.participation.domain.evaluation import EvaluacionInconsistente
from app.modules.participation.infrastructure.evaluation import preparar_retroalimentacion_8c, crear_evaluacion_8c
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente
from app.modules.participation.infrastructure.models import IntentoModel, PasoSimulacionModel
from tests.integration.test_evaluation_persisted import registro, argumentos, datos, motor, laboratorio_pg  # noqa: F401
from tests.integration.test_participation_persistence import datos_pg, participacion, intento, FECHA  # noqa: F401
from tests.integration.test_attempt_state import principal
from tests.integration.test_cases_history import nuevo, publicar


def feedback(c, **cambios):
    return preparar_retroalimentacion_8c(**(argumentos(c)|cambios))


def cerrar_fixture(c, *, opcion=None):
    """Preparación sintética; no constituye autorización productiva de inicio."""
    c.pk=participacion(c); c.ik=intento(c,c.pk); c.usuario=principal(c)
    c.q=c.version.escenarios[0].preguntas[0]
    with c.engine.begin() as s:
        if opcion is not None:
            s.execute(sa.insert(PasoSimulacionModel).values(id_intento=c.ik,id_decision=c.q.id,
                id_opcion=c.q.opciones[opcion].id,numero_paso=1,registrado_en=FECHA+timedelta(seconds=60),
                tiempo_segundos=60))
        s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik)
            .values(estado="FINALIZADO",fin=FECHA+timedelta(minutes=2)))
    return c


def test_feedback_preparado_de_opcion_real_sin_nota_ni_publicacion(registro):
    c=registro
    f=feedback(c)
    assert f==feedback(c)  # otra Session
    assert f.id_intento==c.ik and f.id_participacion==c.pk
    assert f.version_id==c.version.id and f.rubrica_id==c.version.rubrica.id
    assert f.version_regla==c.version.rubrica.version_regla
    assert len(f.respuestas)==1
    r=f.respuestas[0];o=c.q.opciones[0]
    assert (r.pregunta_id,r.opcion_id,r.enunciado)==(c.q.id,o.id,c.q.enunciado)
    assert (r.es_correcta,r.justificacion,r.texto_seleccionado)==(o.es_correcta,o.justificacion,o.texto)
    assert not hasattr(f,"nota_final") and not hasattr(f,"publicada")
    with pytest.raises(FrozenInstanceError): r.justificacion="reemplazo"
    # Preparar feedback no acredita un resultado académico consultable.
    with pytest.raises(MapeoPersistenciaPendiente):
        crear_evaluacion_8c(**argumentos(c)).consultar_evaluacion(
            id_estudiante=c.alumno,id_participacion=c.pk,id_intento=c.ik)


def test_respuesta_incorrecta_usa_su_justificacion_no_la_de_otra_opcion(datos):
    c=cerrar_fixture(datos,opcion=1)
    r=feedback(c).respuestas[0]
    assert r.es_correcta is False
    assert r.opcion_id==c.q.opciones[1].id and r.justificacion==c.q.opciones[1].justificacion
    assert r.opcion_id!=c.q.opciones[0].id


def test_cerrado_sin_selecciones_no_inventa_respuestas_ni_ausencia(datos):
    c=cerrar_fixture(datos)
    assert feedback(c).respuestas==()
    assert not hasattr(feedback(c),"modalidad")


@pytest.mark.parametrize("cambio",["docente","cuenta_ajena","convocatoria_ajena","sin_contexto"])
def test_feedback_no_expuesto_a_otro_actor_o_contexto(registro,cambio):
    c=registro
    cambios={"docente":dict(id_usuario=str(c.docente)),"cuenta_ajena":dict(id_usuario="2147483647"),
             "convocatoria_ajena":dict(id_convocatoria=str(uuid4())),"sin_contexto":dict(id_convocatoria=None)}
    with pytest.raises(AccesoDenegado): feedback(c,usuario=replace(c.usuario,**cambios[cambio]))


def test_feedback_intento_inexistente_rechazado(registro):
    with pytest.raises(RecursoNoDisponible): feedback(registro,id_intento=2147483647)


def test_intento_activo_no_llega_a_leer_correccion(datos,monkeypatch):
    import app.modules.participation.infrastructure.evaluation as modulo
    c=datos;c.pk=participacion(c);c.ik=intento(c,c.pk);c.usuario=principal(c)
    def prohibida(*_,**__): raise AssertionError("No debe leer corrección durante el intento")
    monkeypatch.setattr(modulo,"consultar_explicaciones_seleccionadas",prohibida)
    with pytest.raises(EvaluacionInconsistente): feedback(c)


@pytest.mark.parametrize("cambio",["version","pregunta","opcion","duplicada"])
def test_fuente_rechaza_selecciones_cruzadas(registro,cambio):
    c=registro;version=c.version.id
    pares=((c.q.id,c.q.opciones[0].id),)
    if cambio=="version":version=uuid4()
    if cambio=="pregunta":pares=((uuid4(),c.q.opciones[0].id),)
    if cambio=="opcion":pares=((c.q.id,uuid4()),)
    if cambio=="duplicada":pares=pares*2
    with c.sesiones() as s,pytest.raises(CasoNoEncontradoError):
        consultar_explicaciones_seleccionadas(s,version_id=version,selecciones=pares)


def test_feedback_historico_archivado_no_cambia_por_publicacion_posterior(registro):
    c=registro;anterior=feedback(c)
    futura=nuevo();futura.caso_id=c.version.caso_id;futura.numero=2
    futura.docente_creador_id=c.version.docente_creador_id
    with c.sesiones.begin() as s:
        modelo=CasoRepository(s)._mapear(futura);edicion=modelo.versiones.pop()
        familia=s.get(CasoModel,futura.caso_id);familia.versiones.append(edicion)
    publicar(c.sesiones,futura)
    with c.engine.begin() as s:
        s.execute(sa.update(VersionCasoModel).where(VersionCasoModel.id==c.version.id).values(estado="ARCHIVADO"))
    assert feedback(c)==anterior


def test_fuente_feedback_comparte_transaccion_y_no_hace_commit(registro,monkeypatch):
    import app.modules.participation.infrastructure.evaluation as modulo
    original=modulo.consultar_explicaciones_seleccionadas;sesiones=[];commits=[];rollbacks=[]
    def fabrica():
        s=registro.sesiones();sesiones.append(s)
        sa.event.listen(s,"after_commit",lambda _:commits.append(True))
        sa.event.listen(s,"after_rollback",lambda _:rollbacks.append(True))
        return s
    def consultar(s,**kw):
        assert s is sesiones[-1] and s.in_transaction()
        return original(s,**kw)
    monkeypatch.setattr(modulo,"consultar_explicaciones_seleccionadas",consultar)
    feedback(registro,crear_sesion=fabrica)
    assert len(sesiones)==1 and not commits and rollbacks==[True]


def test_fallo_feedback_revierte_sin_publicar(registro,monkeypatch):
    import app.modules.participation.infrastructure.evaluation as modulo
    rollbacks=[]
    def fabrica():
        s=registro.sesiones()
        sa.event.listen(s,"after_rollback",lambda _:rollbacks.append(True))
        return s
    def fallo(*_,**__): raise SQLAlchemyError("Fallo simulado de la fuente")
    monkeypatch.setattr(modulo,"consultar_explicaciones_seleccionadas",fallo)
    with pytest.raises(SQLAlchemyError): feedback(registro,crear_sesion=fabrica)
    assert rollbacks==[True]


def test_lecturas_concurrentes_feedback_PG_conservan_historia(datos_pg):
    c=cerrar_fixture(datos_pg,opcion=0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(feedback,c);b=pool.submit(feedback,c)
        assert a.result(timeout=10)==b.result(timeout=10)
