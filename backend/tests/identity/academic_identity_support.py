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
    preparar_admision_sqlite(conexion)
    from app.db.models import registrar_modelos_integrados
    metadata=registrar_modelos_integrados()
    metadata.create_all(conexion)
    preparar_consentimiento_sqlite(conexion)
    preparar_publicacion_sqlite(conexion)
    for nombre in ("criterio_rubrica", "nivel_rubrica", "opcion_respuesta"):
        for indice in metadata.tables[nombre].indexes:
            if indice.name.startswith("uq_8c_"):
                indice.create(conexion, checkfirst=True)



def preparar_publicacion_sqlite(conexion):
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    from app.db.models import registrar_modelos_integrados
    ops=Operations(MigrationContext.configure(conexion));metadata=registrar_modelos_integrados()
    for tabla in ('sesion_programada','notificacion'):
        checks={c['name'] for c in inspect(conexion).get_check_constraints(tabla)}
        objetivo='ck_sesion_visibilidad' if tabla=='sesion_programada' else 'ck_aviso_publicacion'
        if objetivo in checks:continue
        with ops.batch_alter_table(tabla,recreate='always') as b:
            for c in metadata.tables[tabla].constraints:
                if c.name in ('ck_sesion_visibilidad','ck_aviso_publicacion'):b.create_check_constraint(c.name,str(c.sqltext))
            if tabla=='sesion_programada':b.create_foreign_key('fk_sesion_visibilidad_fixture','usuario',['visibilidad_docente_id'],['id_usuario'])
            else:
                b.create_foreign_key('fk_notificacion_publicacion_fixture','publicacion_evaluacion',['publicacion_evaluacion_id'],['id'])
                b.create_unique_constraint('uq_notificacion_publicacion',['publicacion_evaluacion_id','convocatoria_id'])


def columnas_publicacion_para_fixture_historica(conexion):
    """Columnas nullable de compatibilidad de ORM, SOLO en fixtures históricos.

    No instala publicación ni estampa la nueva revisión. Su migración se prueba
    por separado en PG real; las comparaciones de head nunca usan este filtro.
    """
    import sqlalchemy as sa
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    ops=Operations(MigrationContext.configure(conexion))
    for tabla,columnas in {'sesion_programada': [('mostrar_resultados_provisionales',sa.Boolean()),('visibilidad_docente_id',sa.Integer()),('visibilidad_actualizada_en',sa.DateTime(timezone=True))],
            'notificacion':[('publicacion_evaluacion_id',sa.Uuid())]}.items():
        if not inspect(conexion).has_table(tabla):continue
        existentes={c['name'] for c in inspect(conexion).get_columns(tabla)}
        for nombre,tipo in columnas:
            if nombre not in existentes:ops.add_column(tabla,sa.Column(nombre,tipo,nullable=True))


def omitir_publicacion_futura(objeto,nombre,tipo,reflejado,comparado):
    if tipo=='table' and nombre in {'ausencia_academica','publicacion_evaluacion','resultado_participacion'}:return False
    nuevas={'mostrar_resultados_provisionales','visibilidad_docente_id','visibilidad_actualizada_en','publicacion_evaluacion_id'}
    if tipo=='column' and nombre in nuevas:return False
    if nombre in {'ck_sesion_visibilidad','uq_notificacion_publicacion','ck_aviso_publicacion'}:return False
    if tipo in {'foreign_key_constraint','unique_constraint'} and any(c.name in nuevas for c in objeto.columns):return False
    return True


def columnas_consentimiento_para_fixture_historica(conexion):
    """Solo columnas auxiliares para usar ORM actual en revisiones antiguas.

    No estampa la revisión nueva ni instala evidencia, documentos o guards.
    """
    import sqlalchemy as sa
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    columnas_publicacion_para_fixture_historica(conexion)
    ops=Operations(MigrationContext.configure(conexion))
    if inspect(conexion).has_table('consentimiento'):
        existentes={c['name'] for c in inspect(conexion).get_columns('consentimiento')}
        for n,t in [('id_version_documento',sa.Integer()),('aceptacion_explicita',sa.Boolean()),('huella_aceptada',sa.String(64))]:
            if n not in existentes:ops.add_column('consentimiento',sa.Column(n,t,nullable=True))
    if inspect(conexion).has_table('participacion') and 'id_consentimiento' not in {c['name'] for c in inspect(conexion).get_columns('participacion')}:
        ops.add_column('participacion',sa.Column('id_consentimiento',sa.Integer(),nullable=True))


def preparar_consentimiento_sqlite(conexion):
    """FK/CHECK/índice reales SQLite; ninguna emulación de guards/locks PG."""
    import sqlalchemy as sa
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    if conexion.dialect.name!='sqlite':raise RuntimeError('Solo SQLite aislado.')
    columnas_publicacion_para_fixture_historica(conexion)
    if 'id_version_documento' in {c['name'] for c in inspect(conexion).get_columns('consentimiento')}:return
    ops=Operations(MigrationContext.configure(conexion))
    with ops.batch_alter_table('consentimiento',recreate='always') as b:
        b.add_column(sa.Column('id_version_documento',sa.Integer(),nullable=True))
        b.add_column(sa.Column('aceptacion_explicita',sa.Boolean(),nullable=True))
        b.add_column(sa.Column('huella_aceptada',sa.String(64),nullable=True))
        b.create_foreign_key('fk_consentimiento_documento','documento_consentimiento_version',['id_version_documento'],['id_version_documento'])
        b.create_check_constraint('ck_consentimiento_evidencia','(id_version_documento IS NULL AND aceptacion_explicita IS NULL AND huella_aceptada IS NULL) OR (id_version_documento IS NOT NULL AND aceptacion_explicita IS TRUE AND huella_aceptada IS NOT NULL AND length(huella_aceptada)=64)')
        b.create_index('uq_consentimiento_explicito_vigente',['id_estudiante','id_version_documento'],unique=True,sqlite_where=sa.text('aceptacion_explicita IS TRUE AND fecha_revocacion IS NULL'))
    with ops.batch_alter_table('participacion',recreate='always') as b:
        b.add_column(sa.Column('id_consentimiento',sa.Integer(),nullable=True))
        b.create_foreign_key('fk_participacion_consentimiento','consentimiento',['id_consentimiento'],['id_consentimiento'])


def preparar_admision_sqlite(conexion):
    """DDL SQLite real para metadata; no emula locks ni triggers PostgreSQL."""
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    import sqlalchemy as sa
    if conexion.dialect.name!='sqlite':raise RuntimeError('Solo fixture SQLite.')
    ops=Operations(MigrationContext.configure(conexion))
    columnas={c['name'] for c in inspect(conexion).get_columns('convocatoria')}
    if 'espera_registrada_en' in columnas:return
    if conexion.scalar(sa.text('SELECT 1 FROM convocatoria LIMIT 1')) is not None:
        raise RuntimeError('Preparación de admisión solo antes de datos de fixture.')
    with ops.batch_alter_table('evento_auditoria',recreate='always') as batch:
        batch.create_unique_constraint('uq_evento_id_sesion_admision',['id','sesion_id'])
    with ops.batch_alter_table('convocatoria',recreate='always') as batch:
        batch.add_column(sa.Column('espera_registrada_en',sa.DateTime(timezone=True),nullable=True))
        batch.add_column(sa.Column('espera_version_caso_id',sa.Uuid(),nullable=True))
        batch.add_column(sa.Column('admision_evento_id',sa.Uuid(),nullable=True))
        batch.create_foreign_key('fk_espera_sesion_version','sesion_programada',
            ['sesion_id','espera_version_caso_id'],['id','version_caso_id'])
        batch.create_foreign_key('fk_admision_evento_sesion','evento_auditoria',
            ['admision_evento_id','sesion_id'],['id','sesion_id'])
        batch.create_check_constraint('ck_espera_pareja','(espera_registrada_en IS NULL) = (espera_version_caso_id IS NULL)')
        batch.create_check_constraint('ck_admision_espera','admision_evento_id IS NULL OR espera_registrada_en IS NOT NULL')


def columnas_convocatoria_para_fixture_historica(conexion):
    """Adaptación explícita SOLO para probar migraciones anteriores con ORM actual.

    Tres columnas nullable auxiliares; no estampa la revisión nueva, ni instala
    constraints/guards ni acredita admisión. Las pruebas de la revisión nueva
    ejecutan su upgrade real. Reservado a PG propio de los fixtures históricos.
    """
    import sqlalchemy as sa
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    if conexion.dialect.name!='postgresql':raise RuntimeError('Solo laboratorio histórico PG.')
    columnas={c['name'] for c in inspect(conexion).get_columns('convocatoria')}
    ops=Operations(MigrationContext.configure(conexion))
    for nombre,tipo in [('espera_registrada_en',sa.DateTime(timezone=True)),
                        ('espera_version_caso_id',sa.Uuid()),('admision_evento_id',sa.Uuid())]:
        if nombre not in columnas:ops.add_column('convocatoria',sa.Column(nombre,tipo,nullable=True))
    columnas_consentimiento_para_fixture_historica(conexion)


def omitir_solo_constraints_admision_futura(objeto,nombre,tipo,reflejado,comparado):
    """Vista histórica anterior a admisión, consentimiento y detalle exacto.

    Solo excluye objetos de revisiones posteriores. Los tests de la cabeza
    actual comparan todo el metadata sin este filtro.
    """
    if not omitir_publicacion_futura(objeto,nombre,tipo,reflejado,comparado):return False
    if tipo=='table' and nombre in {'documento_consentimiento_version','seleccion_consentimiento',
            'resultado_calculo_preguntas','resultado_pregunta','resultado_criterio_exacto'}:return False
    return nombre not in {'uq_8c_opcion_pregunta','fk_consentimiento_documento','fk_participacion_consentimiento','ck_consentimiento_evidencia','uq_consentimiento_explicito_vigente','fk_espera_sesion_version','fk_admision_evento_sesion',
        'ck_espera_pareja','ck_admision_espera','uq_evento_id_sesion_admision'}


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
    for nombre in ("resultado_participacion","publicacion_evaluacion","ausencia_academica","resultado_criterio_exacto","resultado_pregunta","resultado_calculo_preguntas","seleccion_consentimiento","documento_consentimiento_version","docente_espacio_academico","retroalimentacion_docente","resultado_criterio","resultado_intento"):
        if inspect(conexion).has_table(nombre):
            if conexion.scalar(text(f"SELECT 1 FROM {nombre} LIMIT 1")) is not None:
                raise RuntimeError("No eliminar resultados existentes.")
            metadata.tables[nombre].drop(conexion)
    for nombre in ("nivel_rubrica","criterio_rubrica","opcion_respuesta"):
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
    docker("image", "inspect", "docker.io/library/postgres:17")
    nombre = "sps-resolver-lab-" + uuid4().hex[:12]
    secreto = secrets.token_urlsafe(32)
    identificador = docker(
        "create", "--name", nombre,
        "--label", "sps.identity.mapping.lab=true", "--tmpfs", "/var/lib/postgresql/data",
        "--env", "POSTGRES_DB=sps_identity_test_resolver", "--env", "POSTGRES_USER=resolver_lab",
        "--env", "POSTGRES_PASSWORD", "--publish", "127.0.0.1::5432", "docker.io/library/postgres:17",
        env=os.environ | {"POSTGRES_PASSWORD": secreto},
    )
    engine = None
    fallo = None
    try:
        # Conservar el ID antes de iniciar permite limpiar incluso si start falla.
        if not re.fullmatch(r"[0-9a-f]{64}", identificador):
            raise RuntimeError("Docker no devolvió un ID completo de laboratorio.")
        docker("start", identificador, timeout=10)
        try:
            datos = esperar_puerto_publicado(identificador,nombre=nombre)
        except TimeoutError as error:
            raise RuntimeError(f"{error}\n{diagnostico_laboratorio(identificador,secreto)}") from None
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


def esperar_puerto_publicado(identificador, *, nombre, timeout=10, intervalo=.2,
                            reloj=time.monotonic, pausa=time.sleep):
    """Docker start puede retornar antes de publicar el puerto efímero.

    No equivale a PostgreSQL listo: después se exige la conexión TCP y SELECT
    ya existentes. Solo inspecciona el ID propio y mantiene los checks de origen.
    """
    limite=reloj()+timeout
    while reloj()<limite:
        datos=json.loads(docker("inspect",identificador,timeout=3))[0]
        assert datos["Id"]==identificador and datos["Name"]=="/"+nombre
        assert datos["Config"]["Labels"]["sps.identity.mapping.lab"]=="true"
        assert not any(m["Type"] in {"bind","volume"} for m in datos["Mounts"])
        puertos=datos["NetworkSettings"]["Ports"].get("5432/tcp") or []
        if puertos:
            assert puertos[0]["HostIp"]=="127.0.0.1"
            assert 0<int(puertos[0]["HostPort"])<=65535
            return datos
        restante=limite-reloj()
        if restante>0:pausa(min(intervalo,restante))
    raise TimeoutError("Docker no publicó el puerto TCP local del laboratorio dentro del plazo.")


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
