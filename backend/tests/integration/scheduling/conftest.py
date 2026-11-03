from sqlalchemy import event
from tests.unit.scheduling.ingress_support import restaurar_utc_solo_fixture_sqlite
from tests.unit.scheduling.ingress_support import politica_fixture
from app.modules.scheduling.api.dependencies import exigir_contexto_convocatoria
from app.modules.scheduling.api.router import exigir_politica_ingreso_configurada
"""Fixtures de integración para el módulo de Scheduling.

Usa PostgreSQL si ``TEST_DATABASE_URL`` está definida; si no, SQLite en memoria.
Garantiza estrictamente el uso exclusivo de la base `sps_test`.
"""

import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

import app.modules.cases.infrastructure.models  # noqa: F401
import app.modules.scheduling.infrastructure.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db, get_session_factory
from app.main import app
from app.modules.scheduling.api.router import obtener_docente_autenticado
from unittest.mock import Mock
from app.modules.identity.api.dependencies import obtener_fabrica_tokens, obtener_fabrica_usuarios
from app.modules.identity.api.academic_dependencies import obtener_fabrica_resolver_academico
from app.modules.identity.application.academic_identity import (
    ConsultaVinculosAcademicos, ResolverIdentidadAcademica, SistemaAcademico, VinculoAcademico,
)
from app.modules.identity.application.ports import RepositorioUsuarios
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.infrastructure.security import TokensJWT

_CONNECT_TIMEOUT_S = 3
_LOCK_TIMEOUT_MS = 5_000
_IDLE_TX_TIMEOUT_MS = 15_000


def _crear_engine() -> Engine:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    parsed = make_url(url)
    if not (parsed.database or "").endswith("_test") or parsed.database == "sps":
        pytest.exit(
            f"ALERTA DE SEGURIDAD: TEST_DATABASE_URL apunta a '{parsed.database}'. "
            "Debe apuntar exclusivamente a 'sps_test'."
        )
    engine = create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            "connect_timeout": _CONNECT_TIMEOUT_S,
            "options": (
                f"-c lock_timeout={_LOCK_TIMEOUT_MS} "
                f"-c idle_in_transaction_session_timeout={_IDLE_TX_TIMEOUT_MS}"
            ),
        },
    )
    # Verificación en tiempo de ejecución de la base activa en PostgreSQL
    with engine.connect() as conn:
        db_actual = conn.execute(text("SELECT current_database()")).scalar_one()
        if db_actual != "sps_test":
            pytest.exit(
                f"ALERTA CRÍTICA: Conexión establecida con '{db_actual}'. "
                "Se aborta para proteger la base de datos."
            )
    return engine


def _terminar_sesiones_huerfanas(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid()"
            )
        )


@pytest.fixture(scope="session")
def _engine_con_esquema() -> Generator[Engine, None, None]:
    eng = _crear_engine()
    Base.metadata.create_all(eng)
    yield eng
    _terminar_sesiones_huerfanas(eng)
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def engine(_engine_con_esquema: Engine) -> Generator[Engine, None, None]:
    yield _engine_con_esquema
    if _engine_con_esquema.dialect.name == "postgresql":
        return  # Aislamiento por rollback externo, sin DELETE de versiones publicadas.
    _terminar_sesiones_huerfanas(_engine_con_esquema)
    with _engine_con_esquema.begin() as conn:
        for tabla in reversed(Base.metadata.sorted_tables):
            conn.execute(tabla.delete())


@pytest.fixture
def session_factory(engine: Engine):
    if engine.dialect.name != "postgresql":
        yield sessionmaker(bind=engine, expire_on_commit=False)
        return
    with engine.connect() as conexion:
        exterior=conexion.begin()
        try:
            yield sessionmaker(bind=conexion,expire_on_commit=False,join_transaction_mode="create_savepoint")
        finally:
            exterior.rollback()


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def docente_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def cabeceras_estudiante():
    """JWT/rol/resolver reales con cuenta y vínculo explícitos solo de prueba."""
    def configurar(estudiante_id):
        tokens = TokensJWT("clave-prueba-estudiante-scheduling-" * 2, "scheduling-test", "test-client")
        usuarios = Mock(spec=RepositorioUsuarios)
        usuarios.obtener.side_effect = lambda id_usuario: ContextoAcceso(
            "7", "estudiante@universidad.test", frozenset({Rol.ESTUDIANTE}),
        ) if id_usuario == "7" else None
        consulta = Mock(spec=ConsultaVinculosAcademicos)
        consulta.obtener.side_effect = lambda *, id_usuario, sistema: (
            (VinculoAcademico(id_usuario, sistema, estudiante_id),)
            if id_usuario == "7" and sistema == SistemaAcademico.SCHEDULING else ()
        )
        resolver = ResolverIdentidadAcademica(consulta)
        app.dependency_overrides[obtener_fabrica_tokens] = lambda: lambda: tokens
        app.dependency_overrides[obtener_fabrica_usuarios] = lambda: lambda: usuarios
        app.dependency_overrides[obtener_fabrica_resolver_academico] = lambda: lambda: resolver
        return {"Authorization": "Bearer " + tokens.emitir("7", "convocatoria-fixture")}
    return configurar


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
    docente_id: uuid.UUID,
) -> Generator[TestClient, None, None]:
    def _get_db() -> Generator[Session, None, None]:
        session = session_factory()
        event.listen(session, "loaded_as_persistent", restaurar_utc_solo_fixture_sqlite)
        try:
            yield session
        finally:
            session.rollback()
            session.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[exigir_politica_ingreso_configurada] = lambda: politica_fixture(15)
    app.dependency_overrides[exigir_contexto_convocatoria] = lambda: None
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[obtener_docente_autenticado] = lambda: docente_id
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
