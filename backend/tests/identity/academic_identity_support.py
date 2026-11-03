"""Laboratorios propios: SQLite y, opt-in, contenedor PostgreSQL NUEVO por módulo.

No usa .env, URLs externas, contenedores del equipo ni DROP SCHEMA. Los datos de
fixture se conservan hasta destruir el laboratorio completo.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from types import SimpleNamespace
from uuid import uuid4
import itertools
import re
from urllib.parse import quote, quote_plus

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import URL, create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import OperationalError

from app.modules.identity.infrastructure.models import RolORM, UsuarioORM


ANTERIOR = "6867083574f6"
REVISION = "20261031_academic_identity"
BACKEND = Path(__file__).resolve().parents[2]
IDS = itertools.count(100)


def config_alembic(conexion):
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("path_separator", "os")
    config.attributes["connection"] = conexion
    return config


def preparar_esquema_actual_aislado(conexion):
    """8C migra exclusivamente PG; SQLite verifica DDL ORM sobre el historial 8B.

    No estampa una revisión que no ejecutó ni simula triggers PostgreSQL.
    """
    if conexion.dialect.name == "postgresql":
        command.upgrade(config_alembic(conexion), "head")
        return
    command.upgrade(config_alembic(conexion), "20261102_steps_uuid")
    preparar_grafo_sqlite(conexion)
    from app.db.models import registrar_modelos_integrados
    metadata=registrar_modelos_integrados()
    metadata.create_all(conexion)
    for nombre in ("criterio_rubrica", "nivel_rubrica"):
        for indice in metadata.tables[nombre].indexes:
            if indice.name.startswith("uq_8c_"):
                indice.create(conexion, checkfirst=True)


def preparar_grafo_sqlite(conexion):
    """DDL físico real en SQLite vacío, sin atribuirle triggers PostgreSQL."""
    import importlib.util
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    if "es_inicial" in {c["name"] for c in inspect(conexion).get_columns("escenario")}:
        return
    archivo = BACKEND / "alembic/versions/20261102_cases_graph.py"
    spec = importlib.util.spec_from_file_location("ddl_grafo", archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    with Operations.context(MigrationContext.configure(conexion)):
        modulo.agregar_columnas()


def retirar_ddl_resultados_sqlite(conexion):
    """Solo DDL auxiliar vacío en SQLite en memoria, antes de ciclos históricos.

    No es downgrade de 8C: esa revisión nunca se ejecuta en SQLite.
    """
    if conexion.dialect.name!="sqlite" or conexion.engine.url.database not in (None,"",":memory:"):
        raise RuntimeError("Retirada DDL auxiliar reservada a SQLite en memoria.")
    from app.db.models import registrar_modelos_integrados
    metadata=registrar_modelos_integrados()
    for nombre in ("retroalimentacion_docente","resultado_criterio","resultado_intento"):
        if inspect(conexion).has_table(nombre):
            if conexion.scalar(text(f"SELECT 1 FROM {nombre} LIMIT 1")) is not None:
                raise RuntimeError("No eliminar resultados existentes.")
            metadata.tables[nombre].drop(conexion)
    for nombre in ("nivel_rubrica","criterio_rubrica"):
        for indice in metadata.tables[nombre].indexes:
            if indice.name.startswith("uq_8c_"):
                indice.drop(conexion,checkfirst=True)


def docker(*args, timeout=40, **kwargs):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True, timeout=timeout, **kwargs).stdout.strip()


def sin_credenciales(mensaje, secreto):
    mensaje = str(mensaje)
    for valor in {secreto, quote(secreto, safe=""), quote_plus(secreto)}:
        if valor:
            mensaje = mensaje.replace(valor, "<redactado>")
    mensaje = re.sub(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:\s/@]+:)[^@\s]+@", r"\1<redactado>@", mensaje)
    return re.sub(r'''(?i)((?:postgres_password|password|pwd)\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s;]+)''',
                  r"\1<redactado>", mensaje)


def esperar_postgresql_tcp(engine, *, secreto, timeout=30, intervalo=.2,
                           reloj=time.monotonic, pausa=time.sleep):
    """Solo está listo si TCP+autenticación+SELECT llegan a la BD esperada.

    El engine de laboratorio limita además cada conexión y sentencia. La espera
    monotónica puede exceder el plazo como máximo por un intento ya en curso.
    """
    limite = reloj() + timeout
    ultimo = "Sin conexión completada"
    intentos = 0
    while reloj() < limite:
        intentos += 1
        try:
            with engine.connect() as conexion:
                actual = conexion.scalar(text("SELECT current_database()"))
                if actual != "sps_identity_test_resolver":
                    raise RuntimeError("La identidad de la base no coincide con el laboratorio esperado.")
            return
        except OperationalError as error:
            ultimo = sin_credenciales(error, secreto)
            # No conservar conexiones inválidas de un arranque/reinicio parcial.
            engine.dispose()
        restante = limite - reloj()
        if restante > 0:
            pausa(min(intervalo, restante))
    raise TimeoutError(f"PostgreSQL TCP no disponible tras {intentos} intentos. Último error: {ultimo}") from None


def diagnostico_laboratorio(identificador, secreto):
    partes = []
    for nombre, argumentos in (
        ("estado", ["inspect", "--format", "{{json .State}}", identificador]),
        ("logs", ["logs", "--tail", "80", identificador]),
    ):
        try:
            resultado = subprocess.run(["docker", *argumentos], capture_output=True, text=True, timeout=3)
            partes.append(f"{nombre}: {resultado.stdout}\n{resultado.stderr}")
        except (OSError, subprocess.SubprocessError) as error:
            partes.append(f"{nombre}: diagnóstico no disponible ({type(error).__name__})")
    return sin_credenciales("\n".join(partes), secreto)


def eliminar_laboratorio(identificador):
    """Solo ID completo recibido de docker create; nunca selección por nombre."""
    if not re.fullmatch(r"[0-9a-f]{64}", identificador):
        raise RuntimeError("Se rechaza eliminar un contenedor sin ID completo propio.")
    resultado = subprocess.run(["docker", "rm", "--force", identificador],
                               capture_output=True, text=True, timeout=10)
    if resultado.returncode and "No such container" not in resultado.stderr:
        raise RuntimeError(f"No se pudo eliminar el laboratorio {identificador}.")


@contextmanager
def motor_postgresql_desechable():
    if os.getenv("SPS_TEST_IDENTITY_MAPPING_DOCKER") != "1":
        pytest.skip("PostgreSQL mapping no solicitado: SPS_TEST_IDENTITY_MAPPING_DOCKER=1 crea un laboratorio nuevo.")
    # Solo imagen ya instalada, sin pull ni conexión improvisada a servidores externos.
    docker("image", "inspect", "postgres:17")
    nombre = "sps-resolver-lab-" + uuid4().hex[:12]
    secreto = secrets.token_urlsafe(32)
    identificador = docker(
        "create", "--name", nombre,
        "--label", "sps.identity.mapping.lab=true", "--tmpfs", "/var/lib/postgresql/data",
        "--env", "POSTGRES_DB=sps_identity_test_resolver", "--env", "POSTGRES_USER=resolver_lab",
        "--env", "POSTGRES_PASSWORD", "--publish", "127.0.0.1::5432", "postgres:17",
        env=os.environ | {"POSTGRES_PASSWORD": secreto},
    )
    engine = None
    fallo = None
    try:
        # Conservar el ID antes de iniciar permite limpiar incluso si start falla.
        if not re.fullmatch(r"[0-9a-f]{64}", identificador):
            raise RuntimeError("Docker no devolvió un ID completo de laboratorio.")
        docker("start", identificador, timeout=10)
        datos = json.loads(docker("inspect", identificador))[0]
        assert datos["Id"] == identificador and datos["Name"] == "/" + nombre
        assert datos["Config"]["Labels"]["sps.identity.mapping.lab"] == "true"
        assert not any(m["Type"] in {"bind", "volume"} for m in datos["Mounts"])
        puerto = datos["NetworkSettings"]["Ports"]["5432/tcp"][0]
        assert puerto["HostIp"] == "127.0.0.1"
        engine = create_engine(URL.create("postgresql+psycopg", username="resolver_lab", password=secreto,
                                         host="127.0.0.1", port=int(puerto["HostPort"]),
                                         database="sps_identity_test_resolver"),
                               connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
                               pool_timeout=2)
        try:
            esperar_postgresql_tcp(engine, secreto=secreto)
        except Exception as error:
            raise RuntimeError(
                f"Arranque del laboratorio {identificador}: {sin_credenciales(error, secreto)}\n"
                f"{diagnostico_laboratorio(identificador, secreto)}"
            ) from None
        with engine.connect() as c:
            assert c.scalar(text("SELECT current_database()")) == "sps_identity_test_resolver"
            assert inspect(c).get_table_names() == []
        yield engine
    except BaseException as error:
        fallo = error
        raise
    finally:
        errores = []
        try:
            if engine is not None:
                engine.dispose()
        except Exception as error:
            errores.append(sin_credenciales(error, secreto))
        try:
            # También se ejecuta si dispose falla o el servidor nunca estuvo listo.
            eliminar_laboratorio(identificador)
        except Exception as error:
            errores.append(sin_credenciales(error, secreto))
        if errores:
            mensaje = f"Limpieza del laboratorio {identificador}: " + "; ".join(errores)
            if fallo is not None:
                fallo.add_note(mensaje)  # No ocultar el fallo original de arranque/prueba.
            else:
                raise RuntimeError(mensaje) from None


@pytest.fixture(scope="module", params=["sqlite", "postgresql"])
def motor_identidades(request):
    @contextmanager
    def sqlite():
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(engine, "connect")
        def fk(conexion, _):
            conexion.execute("PRAGMA foreign_keys=ON")
        try:
            yield engine
        finally:
            engine.dispose()
    with (sqlite() if request.param == "sqlite" else motor_postgresql_desechable()) as engine:
        with engine.begin() as c:
            preparar_esquema_actual_aislado(c)
        with sessionmaker(engine).begin() as s:
            s.add_all([RolORM(id_rol=1, nombre="DOCENTE"), RolORM(id_rol=2, nombre="ESTUDIANTE")])
        yield engine


@pytest.fixture
def cuentas_identidades(motor_identidades):
    fabrica = sessionmaker(motor_identidades, expire_on_commit=False)
    ids = (next(IDS), next(IDS))
    with fabrica.begin() as s:
        s.add_all([UsuarioORM(id_usuario=i, id_rol=1, nombre="Cuenta de laboratorio",
                             correo=f"cuenta{i}@universidad.test", clave_hash="no-login-por-clave-en-esta-fixture") for i in ids])
    return SimpleNamespace(engine=motor_identidades, sesiones=fabrica, propio=ids[0], ajeno=ids[1], uuid=uuid4())
