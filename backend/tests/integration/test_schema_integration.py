
"""Regresiones de integración: registro ORM y migraciones de Identity, Cases y Scheduling."""

import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from alembic import command
from tests.identity.academic_identity_support import preparar_esquema_actual_aislado, retirar_ddl_resultados_sqlite
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
    PermisoIntentoExtraORM,
    RetroalimentacionDocenteORM,
    academic_metadata,
)
from app.modules.identity.infrastructure.models import RolORM
from tests.identity.test_persistence import base_aislada, configuracion_alembic


# Migracion final que unifica Identity, Cases y Scheduling.
HEAD_IDENTIDADES = "20261031_academic_identity"
HEAD_ER28 = "20261101_er28_base_academica"
HEAD_CASES = "20261102_cases_history_guard"
HEAD_BRIDGE = "20261102_steps_uuid"
MERGE = "6867083574f6"

# Merge anterior entre Identity y Cases.
MERGE_IDENTITY_CASES = "20261028_merge_access_cases"

# Migracion del modulo Scheduling.
SCHEDULING_REVISION = "36b9e0790539"

# Revisiones iniciales de Identity y Cases.
PARENTS = (
    "20261028_identity_access",
    "c27a750108db",
)


CASO_TABLES = {
    "caso",
    "version_caso",
    "escenario",
    "pregunta",
    "opcion_respuesta",
    "rubrica",
    "criterio_rubrica",
    "nivel_rubrica",
    "valoracion_opcion",
}

IDENTITY_TABLES = {
    "usuario",
    "rol",
    "permiso",
    "rol_permiso",
    "identidad_academica",
}

SCHEDULING_TABLES = {
    "espacio_academico",
    "sesion_programada",
    "convocatoria",
    "notificacion",
    "evento_auditoria",
}

ER28_BASE_TABLES = {"grupo_academico", "grupo_estudiante", "consentimiento"}

INTEGRATED_TABLES = (
    CASO_TABLES
    | IDENTITY_TABLES
    | SCHEDULING_TABLES
    | ER28_BASE_TABLES
    | {"asignacion_caso", "docente_espacio_academico", "documento_consentimiento_version", "seleccion_consentimiento"}
    | {"participacion", "intento", "permiso_intento_extra"}
    | {"paso_simulacion", "resultado_intento", "resultado_criterio", "retroalimentacion_docente"}
    | {"resultado_calculo_preguntas", "resultado_pregunta", "resultado_criterio_exacto"}
    | {"ausencia_academica", "publicacion_evaluacion", "resultado_participacion"}
)


def test_registro_compartido_es_cerrado_y_no_crea_tablas_academicas_ficticias():
    metadata = registrar_modelos_integrados()

    assert metadata is Base.metadata

    # El esquema integrado contiene los tres modulos migrados.
    assert set(metadata.tables) == INTEGRATED_TABLES
    assert len(metadata.tables) == 39

    # Todas las tablas deben poder ordenarse resolviendo sus FK.
    assert {tabla.name for tabla in metadata.sorted_tables} == set(metadata.tables)

    # Participation y algunas entidades academicas siguen pendientes.
    assert "participacion" in metadata.tables
    assert "asignacion_caso" in metadata.tables

    # No deben registrarse tablas ficticias para resolver dependencias.
    assert "permiso_intento_extra" in metadata.tables
    assert "retroalimentacion_docente" in metadata.tables


def test_modelos_pendientes_conservan_base_registry_y_todas_las_fk():
    assert set(academic_metadata.tables) == set()

    for modelo in (
        RetroalimentacionDocenteORM,
    ):
        assert issubclass(modelo, Base)
        assert modelo.__mapper__.registry is Base.registry
        assert modelo.__table__.metadata is Base.metadata
    assert PermisoIntentoExtraORM.__table__.metadata is Base.metadata

    assert {
        fk.target_fullname
        for fk in PermisoIntentoExtraORM.__table__.foreign_keys
    } == {
        "participacion.id_participacion",
        "usuario.id_usuario",
    }

    assert {
        fk.target_fullname
        for fk in RetroalimentacionDocenteORM.__table__.foreign_keys
    } == {
        "asignacion_caso.id_asignacion",
        "participacion.id_participacion",
        "usuario.id_usuario",
    }

    # El esquema pendiente tiene dependencias sin resolver.
    # No deben ocultarse mediante tablas ficticias.
    validar_referencias(academic_metadata)
    validar_referencias(Base.metadata)


def test_registro_no_descarta_fk_desconocidas_para_ignorar_errores():
    metadata = MetaData()

    Table(
        "origen",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("destino_id", ForeignKey("destino.id")),
    )

    with pytest.raises(NoReferencedTableError):
        validar_referencias(metadata)

    assert len(metadata.tables["origen"].foreign_keys) == 1


@pytest.mark.parametrize("academicos_primero", [True, False])
def test_orden_de_importacion_no_contamina_metadata_integrada(
    academicos_primero,
):
    codigo = """
from app.db.models import registrar_modelos_integrados
from app.db.base import Base
{primero}

metadata = registrar_modelos_integrados()
tablas = dict(metadata.tables)

{despues}

assert dict(registrar_modelos_integrados().tables) == tablas
assert len(tablas) == 39

assert {{'grupo_academico', 'grupo_estudiante', 'consentimiento'}} <= set(tablas)

assert 'espacio_academico' in tablas
assert 'sesion_programada' in tablas
assert 'convocatoria' in tablas
assert 'notificacion' in tablas
assert 'evento_auditoria' in tablas

assert 'permiso_intento_extra' in tablas
assert 'retroalimentacion_docente' in tablas
assert 'participacion' in tablas
assert 'asignacion_caso' in tablas
""".format(
        primero=(
            "import app.modules.identity.infrastructure.academic_models"
            if academicos_primero
            else ""
        ),
        despues=(
            ""
            if academicos_primero
            else "import app.modules.identity.infrastructure.academic_models"
        ),
    )

    resultado = subprocess.run(
        [sys.executable, "-B", "-c", codigo],
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
    )

    assert resultado.returncode == 0, resultado.stderr


@pytest.mark.parametrize(
    "iniciales",
    [
        (),
        (PARENTS[0],),
        (PARENTS[1],),
        PARENTS,
    ],
)
def test_merge_desde_base_cada_rama_y_dos_ramas_preserva_datos(iniciales):
    with base_aislada("sqlite", "base") as engine:
        with engine.begin() as conexion:
            config = configuracion_alembic(conexion)
            script = ScriptDirectory.from_config(config)

            # Debe existir una sola cabeza final.
            assert script.get_heads() == ["20261108_voluntary_partial"]
            assert script.get_revision("20261102_academic_policy").down_revision == "20261102_evaluation_results"
            assert script.get_revision("20261102_evaluation_results").down_revision == HEAD_BRIDGE
            assert script.get_revision(HEAD_BRIDGE).down_revision == "20261102_participation_history"
            assert script.get_revision("20261102_participation_history").down_revision == "20261102_assignment_bridge"
            assert script.get_revision("20261102_assignment_bridge").down_revision == HEAD_CASES
            assert script.get_revision(HEAD_CASES).down_revision == HEAD_ER28
            assert script.get_revision(HEAD_ER28).down_revision == HEAD_IDENTIDADES
            assert script.get_revision(HEAD_IDENTIDADES).down_revision == MERGE

            # El merge final une Identity/Cases con Scheduling.
            assert set(
                script.get_revision(MERGE).down_revision
            ) == {
                MERGE_IDENTITY_CASES,
                SCHEDULING_REVISION,
            }

            # Se conserva el merge original Identity + Cases.
            assert set(
                script.get_revision(MERGE_IDENTITY_CASES).down_revision
            ) == set(PARENTS)

            # Scheduling depende de la migracion inicial de Cases.
            assert (
                script.get_revision(SCHEDULING_REVISION).down_revision
                == PARENTS[1]
            )

            # Las revisiones iniciales siguen siendo raices.
            for padre in PARENTS:
                assert script.get_revision(padre).down_revision is None

            # Probar distintos puntos de partida del historial.
            for revision in iniciales:
                command.upgrade(config, revision)

            assert set(
                conexion.scalars(
                    text("SELECT version_num FROM alembic_version")
                )
            ) == set(iniciales)

            caso_id = uuid4()

            # Insertar datos de prueba antes del merge.
            if PARENTS[0] in iniciales:
                conexion.execute(
                    RolORM.__table__.insert().values(
                        id_rol=91,
                        nombre="rol_de_regresion",
                    )
                )

            if PARENTS[1] in iniciales:
                conexion.execute(
                    CasoModel.__table__.insert().values(
                        id=caso_id,
                        docente_creador_id=uuid4(),
                    )
                )

            # Aplicar todas las migraciones hasta la cabeza final.
            preparar_esquema_actual_aislado(conexion)

            assert set(
                conexion.scalars(
                    text("SELECT version_num FROM alembic_version")
                )
            ) == {HEAD_BRIDGE}

            # Verificar las 19 anteriores y las tres tablas autorizadas del ER.
            assert set(
                inspect(conexion).get_table_names()
            ) == INTEGRATED_TABLES | {"alembic_version"}

            # Verificar que las migraciones preservan datos existentes.
            if PARENTS[0] in iniciales:
                assert conexion.scalar(
                    select(RolORM.nombre).where(RolORM.id_rol == 91)
                ) == "rol_de_regresion"

            if PARENTS[1] in iniciales:
                assert conexion.scalar(
                    select(CasoModel.id).where(CasoModel.id == caso_id)
                ) == caso_id

            # Comparar el esquema migrado contra los modelos ORM.
            assert compare_metadata(
                MigrationContext.configure(conexion),
                registrar_modelos_integrados(),
            ) == []

            # Verificar que todas las migraciones pueden revertirse.
            # Esta operacion se realiza sobre una BD SQLite aislada.
            retirar_ddl_resultados_sqlite(conexion)
            command.downgrade(config, "base")

            assert set(
                inspect(conexion).get_table_names()
            ) == {"alembic_version"}


def test_routers_identity_y_cases_siguen_registrados():
    from app.main import app

    rutas = app.openapi()["paths"]

    assert {"get", "post"} <= rutas["/api/v1/cases"].keys()
    assert "post" in rutas["/api/v1/identity/excepciones/repeticiones"]
    assert "get" in rutas["/api/v1/identity/me"]
