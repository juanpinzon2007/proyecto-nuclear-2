"""Pruebas exclusivas PostgreSQL: servidor efímero propio, nunca la BD del equipo."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.domain.errors import ConflictoIdentidad, IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Repo
from app.modules.identity.infrastructure.models import RolORM, UsuarioORM
from .academic_identity_support import motor_postgresql_desechable, config_alembic


@pytest.fixture(scope="module")
def laboratorio_pg():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as c:
            command.upgrade(config_alembic(c), "head")
        sesiones = sessionmaker(engine)
        with sesiones.begin() as s:
            s.add(RolORM(id_rol=1, nombre="DOCENTE"))
            s.flush()
            s.add_all([UsuarioORM(id_usuario=i, id_rol=1, nombre="Fixture",
                                 correo=f"cuenta{i}@universidad.test", clave_hash="fixture-sin-login") for i in (1, 2)])
        yield engine, sesiones


def test_perdida_real_de_conexion_falla_cerrada_y_pool_recupera(laboratorio_pg):
    engine, sesiones = laboratorio_pg
    with sesiones() as s:
        pid = s.scalar(text("SELECT pg_backend_pid()"))
        # Solo el backend de esta Session, en el contenedor creado por la fixture.
        with engine.begin() as control:
            assert control.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
        with pytest.raises(IntegracionPendiente):
            Repo(s).obtener(id_usuario="1", sistema=SistemaAcademico.CASES)
        s.rollback()
    with sesiones() as s:
        assert s.scalar(text("SELECT 1")) == 1


def test_dos_propietarios_concurrentes_no_pueden_adquirir_mismo_uuid(laboratorio_pg):
    engine, sesiones = laboratorio_pg
    identificador = uuid4()
    listo = Event()
    def contender():
        with sesiones() as s:
            s.execute(text("SET LOCAL lock_timeout = '5s'"))
            listo.set()
            try:
                Repo(s).agregar_verificado(VinculoAcademico("2", SistemaAcademico.CASES, identificador))
                s.commit()
                return "apropiado"
            except ConflictoIdentidad:
                s.rollback()
                return "rechazado"
    with sesiones() as primera:
        Repo(primera).agregar_verificado(VinculoAcademico("1", SistemaAcademico.CASES, identificador))
        with ThreadPoolExecutor(max_workers=1) as pool:
            futuro = pool.submit(contender)
            assert listo.wait(5)
            primera.commit()
            assert futuro.result(timeout=10) == "rechazado"
    with sesiones() as s:
        assert Repo(s).obtener(id_usuario="1", sistema=SistemaAcademico.CASES) == (
            VinculoAcademico("1", SistemaAcademico.CASES, identificador),
        )
        assert Repo(s).obtener(id_usuario="2", sistema=SistemaAcademico.CASES) == ()
