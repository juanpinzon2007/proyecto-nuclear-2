"""Fixtures de integración: TestClient con base de datos temporal.

Usa PostgreSQL si ``TEST_DATABASE_URL`` está definida; si no, SQLite en memoria.

Diseño anti-bloqueos en PostgreSQL:

* El esquema se crea una sola vez por sesión de pytest y se destruye al final
  (el DDL toma ``ACCESS EXCLUSIVE``; así solo ocurre dos veces, no en cada prueba).
* Entre pruebas solo se vacían las tablas con ``DELETE`` (sin DDL).
* ``NullPool``: cada sesión abre y cierra su propia conexión; no hay conexiones
  inactivas en el pool compartidas entre la prueba y la app.
* ``lock_timeout`` e ``idle_in_transaction_session_timeout``: si algo quedara
  bloqueado, la prueba falla con error en segundos en vez de congelarse.
* Toda sesión (fixture o dependencia ``get_db``) termina con ``rollback`` + ``close``,
  de modo que una lectura nunca deja una transacción abierta.
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
from app.db.base import Base
from app.db.session import get_db
from app.main import app

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
    if not (parsed.database or "").endswith("_test"):
        # Las pruebas borran datos: nunca contra una base que no sea explícitamente de test.
        pytest.exit("TEST_DATABASE_URL debe apuntar a una base cuyo nombre termine en '_test'.")
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            # libpq: aborta si el servidor no responde en N segundos (en vez de colgarse).
            "connect_timeout": _CONNECT_TIMEOUT_S,
            "options": (
                f"-c lock_timeout={_LOCK_TIMEOUT_MS} "
                f"-c idle_in_transaction_session_timeout={_IDLE_TX_TIMEOUT_MS}"
            ),
        },
    )


def _terminar_sesiones_huerfanas(engine: Engine) -> None:
    """Cierra otras conexiones a la base de test (solo PostgreSQL)."""
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
    """Crea el esquema una vez por sesión y lo elimina al final."""
    eng = _crear_engine()
    Base.metadata.create_all(eng)
    yield eng
    _terminar_sesiones_huerfanas(eng)
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def engine(_engine_con_esquema: Engine) -> Generator[Engine, None, None]:
    """Engine compartido; al terminar cada prueba vacía las tablas sin DDL.

    Se desmonta después de ``client`` y ``db_session`` (ambos dependen de él), por lo
    que sus sesiones ya están cerradas cuando se ejecuta la limpieza.
    """
    yield _engine_con_esquema
    _terminar_sesiones_huerfanas(_engine_con_esquema)
    with _engine_con_esquema.begin() as conn:
        for tabla in reversed(Base.metadata.sorted_tables):
            conn.execute(tabla.delete())


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Sesión de verificación de la prueba; no deja transacciones abiertas."""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def _get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.rollback()  # libera la transacción de lectura implícita
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-Docente-Id": str(uuid.uuid4())}


@pytest.fixture
def payload_valido() -> dict[str, object]:
    def opcion(orden: int, correcta: bool) -> dict[str, object]:
        return {
            "orden": orden,
            "texto": f"Opción {orden}",
            "esCorrecta": correcta,
            "justificacion": "Justificación teórica.",
            "valoraciones": {"Análisis": 5 if correcta else 0},
        }

    return {
        "case": {
            "nombre": "Conformidad grupal",
            "desarrolloSituacional": "Desarrollo.",
            "contextoHistoria": "Contexto.",
            "tiempoEstimadoMin": 45,
        },
        "scenarios": [
            {
                "orden": 1,
                "contextoSituacional": "Escenario uno.",
                "questions": [
                    {
                        "orden": 1,
                        "enunciado": "¿Qué haría?",
                        "options": [opcion(1, True), opcion(2, False)],
                    }
                ],
            }
        ],
        "rubric": {
            "nombre": "Rúbrica",
            "versionRegla": "1.0",
            "criterios": [
                {
                    "nombre": "Análisis",
                    "peso": 100,
                    "niveles": [{"nombre": "Alto", "puntaje": 5, "descriptor": "Profundo."}],
                }
            ],
        },
    }
