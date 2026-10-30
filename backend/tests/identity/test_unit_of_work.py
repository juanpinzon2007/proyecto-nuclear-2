from unittest.mock import Mock

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy


@pytest.fixture
def laboratorio():
    # Laboratorio SQLite técnico, no es el ER ni una prueba de PostgreSQL.
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    tabla = Table("prueba_uow", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(engine)
    yield engine, tabla, sessionmaker(bind=engine)
    engine.dispose()


def construir_uow(sesiones, vistos):
    def adaptador(sesion):
        vistos.append(sesion)
        return Mock()
    return UnidadTrabajoIdentitySQLAlchemy(
        usuarios=adaptador, autorizaciones=adaptador, feedback=adaptador,
        academia=adaptador, sesiones=sesiones,
    )


def test_adaptadores_comparten_session_y_commit_es_explicito(laboratorio):
    engine, tabla, sesiones = laboratorio
    vistos = []
    with construir_uow(sesiones, vistos) as uow:
        assert len(vistos) == 4 and all(s is vistos[0] for s in vistos)
        vistos[0].execute(tabla.insert().values(id=1))
        uow.commit()
    with engine.connect() as conexion:
        assert conexion.execute(select(tabla.c.id)).scalars().all() == [1]


def test_sin_commit_descarta_escritura(laboratorio):
    engine, tabla, sesiones = laboratorio
    vistos = []
    with construir_uow(sesiones, vistos):
        vistos[0].execute(tabla.insert().values(id=1))
    with engine.connect() as conexion:
        assert conexion.execute(select(tabla.c.id)).scalars().all() == []


def test_error_de_persistencia_revierte_toda_la_transaccion(laboratorio):
    engine, tabla, sesiones = laboratorio
    vistos = []
    with pytest.raises(IntegrityError):
        with construir_uow(sesiones, vistos):
            vistos[0].execute(tabla.insert().values(id=1))
            vistos[0].execute(tabla.insert().values(id=1))
    with engine.connect() as conexion:
        assert conexion.execute(select(tabla.c.id)).scalars().all() == []


def test_commit_fallido_ejecuta_rollback_y_cierra():
    sesion = Mock()
    sesion.commit.side_effect = RuntimeError("fallo de confirmación")
    vistos = []
    with pytest.raises(RuntimeError, match="fallo de confirmación"):
        with construir_uow(lambda: sesion, vistos) as uow:
            uow.commit()
    assert sesion.rollback.call_count >= 1
    sesion.close.assert_called_once()


def test_reutiliza_fabrica_compartida_sin_motor_nuevo(monkeypatch):
    sesion = Mock()
    fabrica = Mock(return_value=sesion)
    monkeypatch.setattr("app.modules.identity.infrastructure.unit_of_work.get_session_factory", lambda: fabrica)
    adaptador = Mock()
    with UnidadTrabajoIdentitySQLAlchemy(usuarios=adaptador, autorizaciones=adaptador,
                                       feedback=adaptador, academia=adaptador):
        pass
    fabrica.assert_called_once_with()
    assert all(llamada.args == (sesion,) for llamada in adaptador.call_args_list)
    sesion.close.assert_called_once()


def test_no_confirma_fuera_de_una_uow_abierta(laboratorio):
    _, _, sesiones = laboratorio
    uow = construir_uow(sesiones, [])
    with pytest.raises(RuntimeError):
        uow.commit()


def test_fallo_de_constructor_revierte_y_cierra():
    sesion = Mock()
    fallo = Mock(side_effect=RuntimeError("adaptador incompleto"))
    uow = UnidadTrabajoIdentitySQLAlchemy(usuarios=fallo, autorizaciones=Mock(),
                                       feedback=Mock(), academia=Mock(), sesiones=lambda: sesion)
    with pytest.raises(RuntimeError, match="adaptador incompleto"):
        with uow:
            pass
    sesion.rollback.assert_called_once()
    sesion.close.assert_called_once()
