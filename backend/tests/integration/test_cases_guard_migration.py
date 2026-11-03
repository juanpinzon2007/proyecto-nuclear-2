"""Revisión real, DML y HTTP solo sobre PostgreSQL nuevo y desechable."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine,inspect,text

from tests.identity.academic_identity_support import motor_postgresql_desechable,config_alembic,sin_credenciales

BACKEND=Path(__file__).resolve().parents[2]
ROOT=BACKEND.parent
HEAD="20261102_cases_history_guard"
PARENT="20261101_er28_base_academica"
REVISION=BACKEND/"alembic/versions/20261102_cases_history_guard.py"
LAB=BACKEND/"docs/bd/laboratorio_bd2_04"


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_revision_copia_literal_SQL_autorizado_y_cabeza_unica():
    revision=load(REVISION,"revision_bd204")
    assert revision.UPGRADE_SQL==(LAB/"protecciones.sql").read_text(encoding="utf-8")
    assert revision.DOWNGRADE_SQL==(LAB/"revertir_protecciones.sql").read_text(encoding="utf-8")
    config=Config();config.set_main_option("script_location",str(BACKEND/"alembic"))
    script=ScriptDirectory.from_config(config)
    assert script.get_heads()==["20261102_immutable_answers"]
    assert script.get_revision("20261102_steps_uuid").down_revision=="20261102_participation_history"
    assert script.get_revision("20261102_participation_history").down_revision=="20261102_assignment_bridge"
    assert script.get_revision("20261102_assignment_bridge").down_revision==HEAD
    assert script.get_revision(HEAD).down_revision==PARENT


def test_upgrade_SQLite_no_finge_garantias_PostgreSQL():
    engine=create_engine("sqlite://")
    try:
        with engine.begin() as c:
            command.upgrade(config_alembic(c),PARENT)
            before=set(inspect(c).get_table_names())
            command.upgrade(config_alembic(c),HEAD)
            assert set(inspect(c).get_table_names())==before
            assert c.scalar(text("SELECT count(*) FROM sqlite_master WHERE type='trigger'"))==0
            assert c.scalar(text("SELECT version_num FROM alembic_version"))==HEAD
            command.downgrade(config_alembic(c),PARENT)
            assert set(inspect(c).get_table_names())==before
    finally:engine.dispose()


def test_revision_real_preflight_DML_locks_downgrade_y_reupgrade():
    if os.getenv("SPS_TEST_IDENTITY_MAPPING_DOCKER")!="1":
        pytest.skip("Requiere el laboratorio PostgreSQL nuevo opt-in")
    lab=load(LAB/"run_lab.py","lab_revision_bd204")
    evidence=lab.main(revision_guard=HEAD)
    assert evidence['status']=='passed'
    assert len(evidence['tests'])==113  # 109 originales + head y reupgrade reales.
    assert all(t['passed'] for t in evidence['tests'])
    assert all(c['removed_verified'] for c in evidence['cleanup'])


def test_HTTP_Cases_y_Scheduling_con_head_PostgreSQL_real():
    # Ni una URL con nombre parecido: la base sps_test se crea dentro del propio
    # contenedor recién verificado por el fixture, sin otra conexión heredada.
    with motor_postgresql_desechable() as owner:
        with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
            c.exec_driver_sql('CREATE DATABASE sps_test')
        url=owner.url.set(database="sps_test")
        engine=create_engine(url)
        try:
            with engine.begin() as c:
                assert c.scalar(text("SELECT current_database()"))=="sps_test"
                assert inspect(c).get_table_names()==[]
                command.upgrade(config_alembic(c),"head")
                assert c.scalar(text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"))==44
            safe=os.environ.copy()
            for n in ('SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL'):safe.pop(n,None)
            safe.update(TEST_DATABASE_URL=url.render_as_string(hide_password=False),SPS_TEST_POSTGRESQL="0",
                        PYTHONDONTWRITEBYTECODE="1")
            result=subprocess.run([sys.executable,"-B","-m","pytest","-c",str(BACKEND/"pyproject.toml"),
                str(BACKEND/"tests/integration/cases"),str(BACKEND/"tests/integration/scheduling"),
                "-q","-rs","--tb=short"],cwd=ROOT,env=safe,capture_output=True,text=True,timeout=150)
            output=sin_credenciales(result.stdout+result.stderr,url.password)
            print(output)
            assert result.returncode==0,output[-12000:]
        finally:engine.dispose()
