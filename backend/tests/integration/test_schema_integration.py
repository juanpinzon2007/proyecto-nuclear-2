"""Regresiones de integración: registro ORM y migraciones de Identity + Cases."""

import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, inspect, select, text
from sqlalchemy.exc import NoReferencedTableError

from app.db.base import Base
from app.db.models import registrar_modelos_integrados, validar_referencias
from app.modules.cases.infrastructure.models import CasoModel
from app.modules.identity.infrastructure.academic_models import (
    PermisoIntentoExtraORM, RetroalimentacionDocenteORM, academic_metadata,
)
from app.modules.identity.infrastructure.models import RolORM
from tests.identity.test_persistence import base_aislada, configuracion_alembic


MERGE = "20261028_merge_access_cases"
PARENTS = ("20261028_identity_access", "c27a750108db")
CASO_TABLES = {"caso", "version_caso", "escenario", "pregunta", "opcion_respuesta",
               "rubrica", "criterio_rubrica", "nivel_rubrica", "valoracion_opcion"}
IDENTITY_TABLES = {"usuario", "rol", "permiso", "rol_permiso"}


def test_registro_compartido_es_cerrado_y_no_crea_tablas_academicas_ficticias():
    metadata = registrar_modelos_integrados()
    assert metadata is Base.metadata
    assert set(metadata.tables) == CASO_TABLES | IDENTITY_TABLES
    assert {tabla.name for tabla in metadata.sorted_tables} == set(metadata.tables)
    assert "participacion" not in metadata.tables
    assert "asignacion_caso" not in metadata.tables


def test_modelos_pendientes_conservan_base_registry_y_todas_las_fk():
    assert set(academic_metadata.tables) == {"permiso_intento_extra", "retroalimentacion_docente"}
    for modelo in (PermisoIntentoExtraORM, RetroalimentacionDocenteORM):
        assert issubclass(modelo, Base)
        assert modelo.__mapper__.registry is Base.registry
        assert modelo.__table__.metadata is academic_metadata
    assert {fk.target_fullname for fk in PermisoIntentoExtraORM.__table__.foreign_keys} == {
        "participacion.id_participacion", "usuario.id_usuario",
    }
    assert {fk.target_fullname for fk in RetroalimentacionDocenteORM.__table__.foreign_keys} == {
        "asignacion_caso.id_asignacion", "usuario.id_usuario",
    }
    # No se permite desplegar este esquema incompleto: el error sigue explícito.
    with pytest.raises(NoReferencedTableError):
        validar_referencias(academic_metadata)


def test_registro_no_descarta_fk_desconocidas_para_ignorar_errores():
    metadata = MetaData()
    Table("origen", metadata, Column("id", Integer, primary_key=True),
          Column("destino_id", ForeignKey("destino.id")))
    with pytest.raises(NoReferencedTableError):
        validar_referencias(metadata)
    assert len(metadata.tables["origen"].foreign_keys) == 1


@pytest.mark.parametrize("academicos_primero", [True, False])
def test_orden_de_importacion_no_contamina_metadata_integrada(academicos_primero):
    codigo = """
from app.db.models import registrar_modelos_integrados
from app.db.base import Base
{primero}
metadata = registrar_modelos_integrados()
tablas = dict(metadata.tables)
{despues}
assert dict(registrar_modelos_integrados().tables) == tablas
assert len(tablas) == 13
assert 'permiso_intento_extra' not in tablas
assert 'participacion' not in tablas
""".format(
        primero="import app.modules.identity.infrastructure.academic_models" if academicos_primero else "",
        despues="" if academicos_primero else "import app.modules.identity.infrastructure.academic_models",
    )
    resultado = subprocess.run([sys.executable, "-B", "-c", codigo], capture_output=True,
                               text=True, env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"})
    assert resultado.returncode == 0, resultado.stderr


@pytest.mark.parametrize("iniciales", [(), (PARENTS[0],), (PARENTS[1],), PARENTS])
def test_merge_desde_base_cada_rama_y_dos_ramas_preserva_datos(iniciales):
    with base_aislada("sqlite", "base") as engine:
        with engine.begin() as conexion:
            config = configuracion_alembic(conexion)
            script = ScriptDirectory.from_config(config)
            assert script.get_heads() == [MERGE]
            assert set(script.get_revision(MERGE).down_revision) == set(PARENTS)
            for padre in PARENTS:
                assert script.get_revision(padre).down_revision is None
            for revision in iniciales:
                command.upgrade(config, revision)
            assert set(conexion.scalars(text("SELECT version_num FROM alembic_version"))) == set(iniciales)

            caso_id = uuid4()
            if PARENTS[0] in iniciales:
                conexion.execute(RolORM.__table__.insert().values(id_rol=91, nombre="rol_de_regresion"))
            if PARENTS[1] in iniciales:
                # Defaults y tipos del modelo publicado de Juan, sin reescribirlo.
                conexion.execute(CasoModel.__table__.insert().values(id=caso_id, docente_creador_id=uuid4()))

            command.upgrade(config, "head")
            assert set(conexion.scalars(text("SELECT version_num FROM alembic_version"))) == {MERGE}
            assert set(inspect(conexion).get_table_names()) == CASO_TABLES | IDENTITY_TABLES | {"alembic_version"}
            if PARENTS[0] in iniciales:
                assert conexion.scalar(select(RolORM.nombre).where(RolORM.id_rol == 91)) == "rol_de_regresion"
            if PARENTS[1] in iniciales:
                assert conexion.scalar(select(CasoModel.id).where(CasoModel.id == caso_id)) == caso_id
            assert compare_metadata(MigrationContext.configure(conexion), registrar_modelos_integrados()) == []

            command.downgrade(config, "base")
            assert set(inspect(conexion).get_table_names()) == {"alembic_version"}


def test_routers_identity_y_cases_siguen_registrados():
    from app.main import app
    rutas = app.openapi()["paths"]
    assert {"get", "post"} <= rutas["/api/v1/cases"].keys()
    assert "post" in rutas["/api/v1/identity/excepciones/repeticiones"]
    assert "get" in rutas["/api/v1/identity/me"]
