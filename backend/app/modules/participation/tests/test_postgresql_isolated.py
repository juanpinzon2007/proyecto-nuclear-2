"""Laboratorio PostgreSQL opt-in: fixtures desechables, nunca el esquema SPS.

Exige una URL independiente y una base con nombre exacto de laboratorio.
Las tablas sin FK externas NO constituyen modelos académicos aprobados.
"""

import os
from datetime import timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, Table, UniqueConstraint, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.modules.participation.application.errors import ConflictoActualizacion
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente
from app.modules.participation.infrastructure.queries import LecturasParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy
from app.modules.participation.tests.test_sqlalchemy_queries import (
    INTENTO, PARTICIPACION, PASO, tablas_prueba,
)


@pytest.fixture
def laboratorio():
    valor = os.getenv("SPS_PERSISTENCE_LAB_URL")
    if not valor:
        pytest.skip("Falta SPS_PERSISTENCE_LAB_URL para laboratorio PostgreSQL independiente.")
    url = make_url(valor)
    if url.drivername != "postgresql+psycopg" or url.database != "sps_participation_test":
        pytest.fail("El laboratorio exige psycopg y la base sps_participation_test; nunca sps.")
    engine = create_engine(url)
    tablas = tablas_prueba()
    metadata = tablas.participacion.metadata
    # Restricción técnica diferida para provocar un fallo real EN COMMIT.
    prueba = Table("prueba_transaccion", metadata,
        Column("id", Integer, primary_key=True), Column("valor", Integer),
        UniqueConstraint("valor", deferrable=True, initially="DEFERRED"),
    )
    try:
        with engine.begin() as conexion:
            assert conexion.execute(text("SELECT current_database()")).scalar_one() == "sps_participation_test"
            # Sin checkfirst: una BD con tablas previas se rechaza, no se reutiliza.
            metadata.create_all(conexion, checkfirst=False)
        try:
            yield engine, sessionmaker(engine), tablas, prueba
        finally:
            metadata.drop_all(engine)
    finally:
        engine.dispose()


def uow(fabrica):
    return UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(sesion=s), crear_sesion=fabrica)


def test_commit_real_visible_desde_otra_sesion(laboratorio):
    engine, fabrica, _, tabla = laboratorio
    with uow(fabrica) as trabajo:
        trabajo.repositorio.sesion.execute(tabla.insert().values(id=1, valor=10))
        trabajo.commit()
    with engine.connect() as conexion:
        assert conexion.execute(select(tabla.c.valor)).scalar_one() == 10


def test_salida_sin_commit_revierte_escritura_real(laboratorio):
    engine, fabrica, _, tabla = laboratorio
    with uow(fabrica) as trabajo:
        trabajo.repositorio.sesion.execute(tabla.insert().values(id=1, valor=10))
    with engine.connect() as conexion:
        assert conexion.execute(select(tabla)).all() == []


def test_fallo_commit_traduce_conflicto_y_revierte_todo(laboratorio):
    engine, fabrica, _, tabla = laboratorio
    with pytest.raises(ConflictoActualizacion):
        with uow(fabrica) as trabajo:
            trabajo.repositorio.sesion.execute(tabla.insert(), [dict(id=1, valor=10), dict(id=2, valor=10)])
            trabajo.commit()
    with engine.connect() as conexion:
        assert conexion.execute(select(tabla)).all() == []


def sembrar(engine, tablas):
    # La fixture histórica define explícitamente UTC para timestamps sin zona.
    def naive(fila):
        return {k: v.replace(tzinfo=None) if hasattr(v, "tzinfo") else v for k, v in fila.items()}
    with engine.begin() as conexion:
        conexion.execute(tablas.participacion.insert().values(**naive(PARTICIPACION)))
        conexion.execute(tablas.intento.insert().values(**naive(INTENTO)))
        conexion.execute(tablas.paso_simulacion.insert().values(**naive(PASO)))


def lector(sesion, tablas, **opciones):
    return LecturasParticipacionSQLAlchemy(
        sesion, tablas, fechas=FechasPersistencia(timezone.utc),
        estados={"activo_fixture": EstadoIntento.EN_CURSO}, **opciones,
    )


def test_reconstruccion_real_preserva_pasos_y_duracion(laboratorio):
    engine, fabrica, tablas, _ = laboratorio
    sembrar(engine, tablas)
    with fabrica() as sesion:
        repo = lector(sesion, tablas, duracion_historica=lambda s, i: timedelta(minutes=10))
        intento = repo.obtener_intento(10)
        assert intento.pasos[0].id_opcion == PASO["id_opcion"]
        assert intento.pasos[0].reflexion_estudiante == "análisis"
        assert intento.tiempo_maximo == timedelta(minutes=10)
        assert repo.listar_intentos(20) == (intento,)


def test_bd_real_no_suple_duracion_historica_faltante(laboratorio):
    engine, fabrica, tablas, _ = laboratorio
    sembrar(engine, tablas)
    with fabrica() as sesion:
        with pytest.raises(MapeoPersistenciaPendiente):
            lector(sesion, tablas).obtener_intento(10)


def test_bloqueo_real_del_lector_impide_otro_escritor(laboratorio):
    engine, fabrica, tablas, _ = laboratorio
    sembrar(engine, tablas)
    with fabrica() as primera, fabrica() as segunda:
        repo = lector(primera, tablas, bloquear=True,
                      duracion_historica=lambda s, i: timedelta(minutes=10))
        repo.obtener_intento(10)
        segunda.execute(text("SET LOCAL lock_timeout = '150ms'"))
        with pytest.raises(DBAPIError) as fallo:
            segunda.execute(tablas.intento.update().where(tablas.intento.c.id_intento == 10).values(estado="otro"))
        assert fallo.value.orig.sqlstate == "55P03"
        segunda.rollback()
        primera.rollback()
        # Liberado el bloqueo, la segunda conexión puede escribir; se revierte.
        assert segunda.execute(tablas.intento.update().where(tablas.intento.c.id_intento == 10).values(estado="otro")).rowcount == 1
        segunda.rollback()
