"""Opt-in real, solo SELECT y transacciones; no crea ni modifica tablas académicas."""

import os
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy


@pytest.fixture
def fabrica_postgresql():
    if os.getenv("SPS_TEST_POSTGRESQL") != "1":
        pytest.skip("PostgreSQL real no habilitado: falta SPS_TEST_POSTGRESQL=1 y configuración de conexión.")
    if not get_settings().postgres_password or not get_settings().postgres_password.get_secret_value():
        pytest.fail("Configure PostgreSQL mediante la configuración compartida antes de solicitar estas pruebas.")
    return get_session_factory()


def test_postgresql_conexion_y_commit_sin_ddl(fabrica_postgresql):
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(sesion=s), crear_sesion=fabrica_postgresql) as trabajo:
        sesion = trabajo.repositorio.sesion
        assert sesion.get_bind().dialect.name == "postgresql"
        assert sesion.execute(text("SELECT 1")).scalar_one() == 1
        trabajo.commit()


def test_postgresql_recuperacion_despues_de_error(fabrica_postgresql):
    with pytest.raises(DBAPIError):
        with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(sesion=s), crear_sesion=fabrica_postgresql) as trabajo:
            trabajo.repositorio.sesion.execute(text("SELECT 1 / 0"))
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(sesion=s), crear_sesion=fabrica_postgresql) as trabajo:
        assert trabajo.repositorio.sesion.execute(text("SELECT 1")).scalar_one() == 1


def test_postgresql_decimal_y_timestamp_del_driver(fabrica_postgresql):
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(sesion=s), crear_sesion=fabrica_postgresql) as trabajo:
        fila = trabajo.repositorio.sesion.execute(text(
            "SELECT CAST(1.23 AS NUMERIC(5,2)), TIMESTAMPTZ '2026-10-27 15:00:00+00'"
        )).one()
        assert isinstance(fila[0], Decimal) and fila[0] == Decimal("1.23")
        assert fila[1].astimezone(timezone.utc).hour == 15
