"""Política confirmada de respuestas inmutables; SQL/Facade reales en laboratorio.

El recorrido es el grafo SQL de Cases, no un proveedor simulado. Solo la
autorización temporal de Scheduling continúa siendo una fixture explícita.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta, timezone
from threading import Barrier

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.modules.identity.infrastructure.models import RolORM
from app.modules.participation.domain.errors import RespuestaInmutable, IntentoNoEditable
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import PasoSimulacionModel as P
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic
from tests.integration.test_cases_graph import simulacion, pg_grafo, responder, facade  # noqa: F401
from tests.integration.test_participation_persistence import FECHA

HEAD = "20261102_immutable_answers"
PARENT = "20261102_cases_graph"


def filas(c):
    with c.engine.connect() as s:
        return s.execute(sa.select(P.__table__).where(P.id_intento == c.ik).order_by(P.numero_paso)).all()


@pytest.mark.parametrize("opcion", [0, 1])
def test_segunda_respuesta_incluso_identica_no_reemplaza(simulacion, opcion):
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    q = c.version.escenarios[0].preguntas[0]
    with pytest.raises(RespuestaInmutable):
        facade(c).registrar_decision(id_estudiante=c.alumno, id_intento=c.ik,
            id_decision=q.id, id_opcion=q.opciones[opcion].id)
    assert filas(c) == antes
    # Otra pregunta autorizada por el grafo continúa siendo respondible.
    responder(c, 1)
    assert len(filas(c)) == 2 and filas(c)[0] == antes[0]


@pytest.mark.parametrize("estado", ["activo", "finalizado", "vencido"])
def test_put_logico_rechazado_conserva_original(simulacion, estado):
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    if estado == "finalizado":
        facade(c).finalizar(id_estudiante=c.alumno, id_intento=c.ik)
    elif estado == "vencido":
        c.ahora += timedelta(hours=1)
    q = c.version.escenarios[0].preguntas[0]
    with pytest.raises(RespuestaInmutable if estado == "activo" else IntentoNoEditable):
        facade(c).modificar_decision(id_estudiante=c.alumno, id_intento=c.ik,
            id_decision=q.id, id_opcion=q.opciones[1].id, reflexion_estudiante="Intento de reescritura")
    assert filas(c) == antes


@pytest.mark.parametrize("cambio", ["opcion", "reflexion", "borrar"])
def test_repositorio_rechaza_agregado_manipulado(simulacion, cambio):
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    with pytest.raises(RespuestaInmutable), c.sesiones.begin() as s:
        repo = RepositorioParticipacionSQLAlchemy(s, fechas=FechasPersistencia(timezone.utc))
        original = repo.obtener_intento(c.ik)
        paso = original.pasos[0]
        nuevo = replace(original, pasos=() if cambio == "borrar" else (replace(paso,
            **({"id_opcion": c.version.escenarios[0].preguntas[0].opciones[1].id} if cambio == "opcion"
               else {"reflexion_estudiante": "Alterada"})),))
        repo.guardar_intento(nuevo, esperado=original)
    assert filas(c) == antes


@pytest.mark.parametrize("cambio", ["opcion", "reflexion", "tiempo", "noop", "delete", "truncate", "upsert", "orm"])
def test_sql_directo_no_elude_politica(simulacion, cambio):
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    with pytest.raises(IntegrityError), c.sesiones.begin() as s:
        if cambio == "delete":
            s.execute(sa.delete(P).where(P.id_intento == c.ik))
        elif cambio == "truncate":
            s.execute(sa.text("TRUNCATE public.paso_simulacion"))
        elif cambio == "upsert":
            valores = dict(antes[0]._mapping)
            valores.pop("id_paso")
            valores["id_opcion"] = c.version.escenarios[0].preguntas[0].opciones[1].id
            s.execute(insert(P.__table__).values(**valores).on_conflict_do_update(
                index_elements=["id_intento", "id_decision"], set_={"id_opcion": valores["id_opcion"]}))
        elif cambio == "orm":
            paso = s.get(P, antes[0].id_paso)
            paso.reflexion_estudiante = "Mutación ORM"
            s.flush()
        else:
            valores = {"id_opcion": c.version.escenarios[0].preguntas[0].opciones[1].id} if cambio == "opcion" else \
                {"reflexion_estudiante": "Mutación SQL"} if cambio == "reflexion" else \
                {"registrado_en": FECHA + timedelta(minutes=2), "tiempo_segundos": 120} if cambio == "tiempo" else \
                {"id_opcion": antes[0].id_opcion}
            s.execute(sa.update(P).where(P.id_intento == c.ik).values(**valores))
    assert filas(c) == antes


def test_rollback_revierte_otro_registro_si_se_intenta_mutar(simulacion):
    c = simulacion
    responder(c, 0)
    antes = filas(c)
    q = c.version.escenarios[1].preguntas[0]
    with pytest.raises(IntegrityError), c.engine.begin() as s:
        s.execute(sa.insert(P).values(id_intento=c.ik, id_decision=q.id, id_opcion=q.opciones[0].id,
            numero_paso=2, registrado_en=FECHA+timedelta(minutes=2), tiempo_segundos=120))
        s.execute(sa.update(P).where(P.id_paso == antes[0].id_paso).values(reflexion_estudiante="No autorizado"))
    assert filas(c) == antes
    responder(c, 1)
    assert len(filas(c)) == 2


@pytest.mark.parametrize("segunda", [0, 1])
def test_solicitudes_concurrentes_un_ganador_sin_sustitucion(simulacion, segunda):
    c, barrera = simulacion, Barrier(2)
    q = c.version.escenarios[0].preguntas[0]
    def enviar(opcion):
        barrera.wait(timeout=5)
        try:
            facade(c).registrar_decision(id_estudiante=c.alumno, id_intento=c.ik,
                id_decision=q.id, id_opcion=q.opciones[opcion].id)
            return ("guardada", q.opciones[opcion].id)
        except RespuestaInmutable:
            return ("rechazada", None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(enviar, 0), pool.submit(enviar, segunda)
        resultados = (a.result(timeout=10), b.result(timeout=10))
    assert sorted(r[0] for r in resultados) == ["guardada", "rechazada"]
    assert len(filas(c)) == 1
    assert filas(c)[0].id_opcion == next(opcion for estado, opcion in resultados if estado == "guardada")


def test_sql_insert_concurrente_no_duplica(simulacion):
    c, barrera = simulacion, Barrier(2)
    q = c.version.escenarios[0].preguntas[0]
    def insertar(opcion):
        barrera.wait(timeout=5)
        try:
            with c.engine.begin() as s:
                s.execute(sa.insert(P).values(id_intento=c.ik, id_decision=q.id, id_opcion=q.opciones[opcion].id,
                    numero_paso=1, registrado_en=FECHA+timedelta(minutes=1), tiempo_segundos=60))
            return "guardada"
        except IntegrityError:
            return "rechazada"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(insertar, (0, 1))) == ["guardada", "rechazada"]
    assert len(filas(c)) == 1


def test_migracion_preserva_respuestas_y_downgrade_solo_retira_su_guard():
    from tests.integration.test_cases_graph import simulacion as preparar_simulacion
    with motor_postgresql_desechable() as e:
        with e.begin() as s:
            command.upgrade(config_alembic(s), PARENT)
            from tests.identity.academic_identity_support import columnas_convocatoria_para_fixture_historica
            columnas_convocatoria_para_fixture_historica(s)
            s.execute(sa.insert(RolORM), [dict(id_rol=1,nombre="DOCENTE"), dict(id_rol=2,nombre="ESTUDIANTE")])
        c = preparar_simulacion.__wrapped__(e)
        responder(c, 0)
        antes = filas(c)
        with e.begin() as s:
            tablas = set(sa.inspect(s).get_table_names())
            command.upgrade(config_alembic(s), HEAD)
            assert set(sa.inspect(s).get_table_names()) == tablas
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal")) == 44
        assert filas(c) == antes
        with e.begin() as s:
            command.downgrade(config_alembic(s), PARENT)
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal")) == 43
        assert filas(c) == antes
        with e.begin() as s:
            command.upgrade(config_alembic(s), HEAD)
        with pytest.raises(IntegrityError), e.begin() as s:
            s.execute(sa.update(P).where(P.id_intento == c.ik).values(id_opcion=antes[0].id_opcion))
        assert filas(c) == antes
