"""Únicamente PostgreSQL 17 nuevo: esquema técnico autorizado, sin backfill."""
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import select,func,inspect,delete,text
from sqlalchemy.exc import IntegrityError

from app.db.models import registrar_modelos_integrados
from app.modules.identity.infrastructure.models import RolORM
from app.modules.scheduling.infrastructure.models import DocenteEspacioAcademicoModel as G, SesionProgramadaModel as S
from tests.identity.academic_identity_support import motor_postgresql_desechable,config_alembic
from tests.integration.test_participation_persistence import contexto

HEAD='20261104_teacher_spaces'
PARENT='20261102_immutable_answers'


def test_upgrade_integridad_sin_autoconcesion_y_downgrade_controlado():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as c:
            command.upgrade(config_alembic(c),PARENT)
            c.execute(RolORM.__table__.insert(),[dict(id_rol=1,nombre='DOCENTE'),dict(id_rol=2,nombre='ESTUDIANTE')])
        # Datos históricos sintéticos anteriores a RF-18: ni programar ni crear
        # espacios previamente puede convertirse en una asignación implícita.
        h=contexto(engine)
        with engine.begin() as c:
            antes=set(inspect(c).get_table_names())
            sesion=c.execute(select(S.__table__).where(S.id==h.sesion)).one()
            command.upgrade(config_alembic(c),HEAD)
            assert set(inspect(c).get_table_names())==antes|{'docente_espacio_academico'}
            assert c.scalar(select(func.count()).select_from(G))==0
            assert len(inspect(c).get_foreign_keys(G.__tablename__))==2
            assert inspect(c).get_pk_constraint(G.__tablename__)['constrained_columns']==['id_docente','espacio_academico_id']
            assert compare_metadata(MigrationContext.configure(c),registrar_modelos_integrados())==[]
            assert c.execute(select(S.__table__).where(S.id==h.sesion)).one()==sesion
        valores=dict(id_docente=h.docente,espacio_academico_id=sesion.espacio_academico_id)
        with engine.begin() as c:c.execute(G.__table__.insert().values(**valores))
        for invalido,estado in [(valores,'23505'),(valores|{'id_docente':2147483647},'23503'),
                                (valores|{'espacio_academico_id':uuid4()},'23503')]:
            with pytest.raises(IntegrityError) as error:
                with engine.begin() as c:c.execute(G.__table__.insert().values(**invalido))
            assert error.value.orig.sqlstate==estado
        with engine.begin() as c:
            with pytest.raises(RuntimeError,match='asignaciones explícitas'):
                with c.begin_nested():command.downgrade(config_alembic(c),PARENT)
            assert c.scalar(text('SELECT version_num FROM alembic_version'))==HEAD
            assert c.scalar(select(func.count()).select_from(G))==1
            # Solo la fila sintética propia; no se ejecuta sobre datos del equipo.
            c.execute(delete(G).where(G.id_docente==h.docente))
            command.downgrade(config_alembic(c),PARENT)
            assert set(inspect(c).get_table_names())==antes
            assert c.execute(select(S.__table__).where(S.id==h.sesion)).one()==sesion
            command.upgrade(config_alembic(c),HEAD)
            assert c.scalar(select(func.count()).select_from(G))==0
