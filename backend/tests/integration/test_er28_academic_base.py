"""BD2-01: contrato del ER y persistencia solo en laboratorios descartables.

SQLite es en memoria; PostgreSQL es un contenedor NUEVO de la fixture existente.
No se consultan URLs del proyecto ni se crean filas fuera de las pruebas.
"""

import ast
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import re
from uuid import uuid4

from alembic import command, op
from tests.identity.academic_identity_support import preparar_esquema_actual_aislado, retirar_ddl_resultados_sqlite
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.pool import StaticPool

from app.db.models import registrar_modelos_integrados
from app.modules.identity.infrastructure.academic_base_models import (
    ConsentimientoORM, GrupoAcademicoORM, GrupoEstudianteORM,
)
from app.modules.identity.infrastructure.academic_models import academic_metadata
from tests.identity.academic_identity_support import config_alembic, motor_postgresql_desechable
from tests.identity.persistence_support import DBML, bloque_dbml, columnas_dbml


HEAD = "20261101_er28_base_academica"
PARENT = "20261031_academic_identity"
MODELOS = (GrupoAcademicoORM, GrupoEstudianteORM, ConsentimientoORM)
NUEVAS = {m.__tablename__ for m in MODELOS}
ANTERIORES = {
    "rol", "permiso", "rol_permiso", "usuario", "identidad_academica",
    "caso", "version_caso", "escenario", "pregunta", "opcion_respuesta",
    "rubrica", "criterio_rubrica", "nivel_rubrica", "valoracion_opcion",
    "espacio_academico", "sesion_programada", "convocatoria", "notificacion",
    "evento_auditoria",
}
FECHA = datetime(2026, 11, 1, 12)


@pytest.fixture(scope="module")
def laboratorio_pg():
    with motor_postgresql_desechable() as engine:
        yield engine


@pytest.fixture(scope="module", params=["sqlite", "postgresql"])
def motor(request):
    if request.param == "postgresql":
        yield request.getfixturevalue("laboratorio_pg")
        return
    engine = sa.create_engine("sqlite://", poolclass=StaticPool)
    @sa.event.listens_for(engine, "connect")
    def configurar(dbapi, _):
        # BEGIN explícito permite aislar también el DDL entre pruebas.
        dbapi.isolation_level = None
        dbapi.execute("PRAGMA foreign_keys=ON")
    @sa.event.listens_for(engine, "begin")
    def comenzar(conexion):
        conexion.exec_driver_sql("BEGIN")
    try:
        yield engine
    finally:
        engine.dispose()


@contextmanager
def transaccion(engine):
    with engine.connect() as c:
        tx = c.begin()
        try:
            yield c
        finally:
            if tx.is_active:
                tx.rollback()


@pytest.fixture
def conexion(motor):
    with transaccion(motor) as c:
        yield c


@pytest.fixture
def conexion_pg(laboratorio_pg):
    with transaccion(laboratorio_pg) as c:
        yield c


def cuentas(c):
    tablas = registrar_modelos_integrados().tables
    c.execute(tablas["rol"].insert(), [
        {"id_rol": 1, "nombre": "DOCENTE"},
        {"id_rol": 2, "nombre": "ESTUDIANTE"},
    ])
    c.execute(tablas["usuario"].insert(), [
        {"id_usuario": i, "id_rol": 1 if i == 101 else 2, "nombre": "Fixture BD2-01",
         "correo": f"bd2-{i}@universidad.test", "clave_hash": "sin-credenciales-reales"}
        for i in (101, 102, 103)
    ])


@pytest.fixture
def bd(conexion):
    command.upgrade(config_alembic(conexion), HEAD)
    from tests.identity.academic_identity_support import columnas_consentimiento_para_fixture_historica
    columnas_consentimiento_para_fixture_historica(conexion)
    cuentas(conexion)
    return conexion


def grupo(c, nombre="Grupo exclusivo de laboratorio"):
    resultado = c.execute(GrupoAcademicoORM.__table__.insert().values(
        id_profesor=101, nombre=nombre, periodo="2026-2",
    ))
    return resultado.inserted_primary_key[0]


def datos_membresia(c):
    return dict(id_grupo=grupo(c), id_estudiante=102, fecha_ingreso=FECHA)


def datos_consentimiento():
    return dict(id_estudiante=102, version_texto="texto-laboratorio", fecha_aceptacion=FECHA)


def valores_validos(c, tabla):
    if tabla == "grupo_academico":
        return dict(id_profesor=101, nombre="Fixture", periodo="2026-2")
    if tabla == "grupo_estudiante":
        return datos_membresia(c)
    return datos_consentimiento()


@pytest.mark.parametrize("modelo", MODELOS)
def test_columnas_y_claves_coinciden_con_el_dbml_original(modelo):
    t = modelo.__table__
    especificacion = columnas_dbml(t.name)
    extras={'id_version_documento','aceptacion_explicita','huella_aceptada'} if t.name=='consentimiento' else set()
    assert set(t.c.keys()) == {n for n, _, _, _ in especificacion}|extras
    tipos = {"int": sa.Integer, "varchar": sa.String, "timestamp": sa.DateTime, "boolean": sa.Boolean}
    for nombre, tipo, longitud, flags in especificacion:
        col = t.c[nombre]
        assert isinstance(col.type, tipos[tipo])
        assert col.primary_key == ("pk" in flags)
        assert col.nullable == ("not null" not in flags and not col.primary_key)
        if tipo == "varchar":
            assert col.type.length == int(longitud)
        if tipo == "timestamp":
            assert col.type.timezone is False
        if col.primary_key:
            assert col.autoincrement is True
        target = re.search(r"ref: > ([\w.]+)", flags)
        assert {f.target_fullname for f in col.foreign_keys} == ({target.group(1)} if target else set())
        if "default: true" in flags:
            assert str(col.server_default.arg).lower() == "true"
        else:
            assert col.server_default is None
        assert col.default is None
    esperadas = {
        tuple(x.strip() for x in columnas.split(","))
        for columnas in re.findall(r"\(([^)]+)\) \[unique\]", bloque_dbml(t.name))
    }
    assert {tuple(c.name for c in u.columns) for u in t.constraints if isinstance(u, sa.UniqueConstraint)} == esperadas
    assert {q.name for q in t.constraints if isinstance(q,sa.CheckConstraint)}==({'ck_consentimiento_evidencia'} if extras else set())
    assert {q.name for q in t.indexes}==({'uq_consentimiento_explicito_vigente'} if extras else set())
    assert all(f.ondelete is None and f.onupdate is None for f in t.foreign_key_constraints)


def test_inventario_aprobado_metadata_y_limites_de_la_revision():
    m = registrar_modelos_integrados()
    assert set(m.tables) == ANTERIORES | NUEVAS | {"asignacion_caso", "participacion", "intento", "permiso_intento_extra", "paso_simulacion", "resultado_intento", "resultado_criterio", "retroalimentacion_docente", "docente_espacio_academico", "documento_consentimiento_version", "seleccion_consentimiento", "resultado_calculo_preguntas", "resultado_pregunta", "resultado_criterio_exacto"}
    assert len(m.tables) == 36
    assert {t.name for t in m.sorted_tables} == set(m.tables)
    assert set(academic_metadata.tables) == set()
    assert not NUEVAS & set(academic_metadata.tables)
    assert sum(len(x.__table__.columns) for x in MODELOS) == 17
    assert sum(len(x.__table__.foreign_key_constraints) for x in MODELOS) == 5
    assert len(re.findall(r"^Table ", DBML.read_text(encoding="utf-8"), re.M)) == 28

    script = ScriptDirectory.from_config(config_alembic(None))
    assert script.get_heads() == ["20261107_question_results"]
    assert script.get_revision("20261102_steps_uuid").down_revision == "20261102_participation_history"
    assert script.get_revision("20261102_participation_history").down_revision == "20261102_assignment_bridge"
    assert script.get_revision("20261102_assignment_bridge").down_revision == "20261102_cases_history_guard"
    assert script.get_revision("20261102_cases_history_guard").down_revision == HEAD
    revision = script.get_revision(HEAD)
    assert revision.down_revision == PARENT
    tree = ast.parse(Path(revision.path).read_text(encoding="utf-8"))
    upgrade = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
    operaciones = [n for n in ast.walk(upgrade)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and isinstance(n.func.value, ast.Name) and n.func.value.id == "op"]
    assert {n.func.attr for n in operaciones} == {"create_table"}
    assert {ast.literal_eval(n.args[0]) for n in operaciones} == NUEVAS


def test_upgrade_vacio_y_modelos_reflejados(conexion):
    command.upgrade(config_alembic(conexion), HEAD)
    i = sa.inspect(conexion)
    assert set(i.get_table_names()) == ANTERIORES | NUEVAS | {"alembic_version"}
    for modelo in MODELOS:
        t = modelo.__table__
        assert set(i.get_pk_constraint(t.name)["constrained_columns"]) == set(t.primary_key.columns.keys())
        assert {c["name"] for c in i.get_columns(t.name)} == set(t.c.keys())-({"id_version_documento","aceptacion_explicita","huella_aceptada"} if t.name=="consentimiento" else set())
        assert conexion.scalar(sa.select(sa.func.count()).select_from(t)) == 0
        fk = {(tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
              for f in i.get_foreign_keys(t.name)}
        esperado = {(tuple(f.column_keys), f.elements[0].column.table.name,
                     tuple(e.column.name for e in f.elements)) for f in t.foreign_key_constraints if "id_version_documento" not in f.column_keys}
        assert fk == esperado
    # La revisión histórica conserva sus 22 tablas. El metadata actual agrega
    # P1-P3: comprobar coincidencia completa al alcanzar la cabeza actual.
    preparar_esquema_actual_aislado(conexion)
    assert compare_metadata(MigrationContext.configure(conexion), registrar_modelos_integrados()) == []


def test_insertar_matricula_consentimiento_y_default_sin_politicas(bd):
    g = grupo(bd)
    t = GrupoEstudianteORM.__table__
    r = bd.execute(t.insert().values(id_grupo=g, id_estudiante=102, fecha_ingreso=FECHA))
    fila = bd.execute(sa.select(t).where(t.c.id_grupo_estudiante == r.inserted_primary_key[0])).one()
    assert fila.id_grupo == g and fila.activo is True and fila.fecha_ingreso == FECHA
    c = ConsentimientoORM.__table__
    r = bd.execute(c.insert().values(**datos_consentimiento()))
    fila = bd.execute(sa.select(c).where(c.c.id_consentimiento == r.inserted_primary_key[0])).one()
    assert fila.id_estudiante == 102 and fila.fecha_revocacion is None
    assert fila.fecha_aceptacion == FECHA


@pytest.mark.parametrize("tabla,campo", [
    ("grupo_academico", "id_profesor"), ("grupo_estudiante", "id_grupo"),
    ("grupo_estudiante", "id_estudiante"), ("consentimiento", "id_estudiante"),
])
def test_fk_rechaza_huerfanos_y_rollback_conserva_conexion(bd, tabla, campo):
    m = registrar_modelos_integrados()
    valores = valores_validos(bd, tabla)
    valores[campo] = 2147483647
    antes = bd.scalar(sa.select(sa.func.count()).select_from(m.tables[tabla]))
    with pytest.raises(IntegrityError):
        with bd.begin_nested():
            bd.execute(m.tables[tabla].insert().values(**valores))
    assert bd.scalar(sa.select(sa.func.count()).select_from(m.tables[tabla])) == antes
    assert bd.scalar(sa.select(sa.literal(1))) == 1


def test_unique_matricula_y_estudiante_en_otro_grupo(bd):
    valores = datos_membresia(bd)
    t = GrupoEstudianteORM.__table__
    bd.execute(t.insert().values(**valores))
    with pytest.raises(IntegrityError):
        with bd.begin_nested():
            bd.execute(t.insert().values(**valores))
    bd.execute(t.insert().values(**(valores | {"id_grupo": grupo(bd, "Otro grupo")})))
    assert bd.scalar(sa.select(sa.func.count()).select_from(t)) == 2


@pytest.mark.parametrize("tabla,campo", [
    ("grupo_academico", "id_profesor"), ("grupo_academico", "nombre"),
    ("grupo_academico", "periodo"), ("grupo_estudiante", "id_grupo"),
    ("grupo_estudiante", "id_estudiante"), ("grupo_estudiante", "fecha_ingreso"),
    ("grupo_estudiante", "activo"), ("consentimiento", "id_estudiante"),
    ("consentimiento", "version_texto"), ("consentimiento", "fecha_aceptacion"),
])
def test_not_null_original(bd, tabla, campo):
    valores = valores_validos(bd, tabla)
    valores[campo] = None
    with pytest.raises(IntegrityError):
        with bd.begin_nested():
            bd.execute(registrar_modelos_integrados().tables[tabla].insert().values(**valores))


@pytest.mark.parametrize("modelo", MODELOS)
def test_pk_autogenerada_y_duplicado_rechazado(bd, modelo):
    t = modelo.__table__
    resultado = bd.execute(t.insert().values(**valores_validos(bd, t.name)))
    identificador = resultado.inserted_primary_key[0]
    assert type(identificador) is int and identificador > 0
    pk = next(iter(t.primary_key.columns))
    fila = bd.execute(sa.select(t).where(pk == identificador)).one()._mapping
    with pytest.raises(IntegrityError):
        with bd.begin_nested():
            bd.execute(t.insert().values(**dict(fila)))
    assert bd.scalar(sa.select(sa.func.count()).select_from(t).where(pk == identificador)) == 1


def filas_y_estructura(c, nombres):
    i = sa.inspect(c)
    reflejadas = sa.MetaData()
    reflejadas.reflect(bind=c, only=sorted(nombres))
    datos = {n: c.execute(sa.select(reflejadas.tables[n]).order_by(
        *reflejadas.tables[n].primary_key.columns)).all() for n in sorted(nombres)}
    estructura = {
        n: (
            [(x["name"], str(x["type"]), x["nullable"], x.get("default")) for x in i.get_columns(n)],
            i.get_pk_constraint(n), i.get_foreign_keys(n),
            i.get_unique_constraints(n), i.get_check_constraints(n), i.get_indexes(n),
        ) for n in sorted(nombres)
    }
    return datos, estructura


def sembrar_historia_sintetica(c):
    """Una muestra en cada tabla anterior; nunca datos reales o política oficial."""
    m = registrar_modelos_integrados().tables
    cuentas(c)
    ids = {n: uuid4() for n in (
        "doc_cases", "doc_scheduling", "est_scheduling", "caso", "version", "escena",
        "pregunta", "opcion", "rubrica", "criterio", "nivel", "espacio", "sesion", "conv",
    )}
    def poner(tabla, **valores):
        c.execute(m[tabla].insert().values(**valores))
    poner("permiso", id_permiso=1, codigo="CREAR_CASOS", descripcion="Fixture")
    poner("rol_permiso", id_rol=1, id_permiso=1)
    for alias, sistema, user in (("doc_cases", "CASES", 101), ("doc_scheduling", "SCHEDULING", 101),
                                 ("est_scheduling", "SCHEDULING", 102)):
        poner("identidad_academica", sistema=sistema, id_academico=ids[alias], id_usuario=user)
    poner("caso", id=ids["caso"], docente_creador_id=ids["doc_cases"], creado_en=FECHA.replace(tzinfo=timezone.utc))
    poner("version_caso", id=ids["version"], caso_id=ids["caso"], numero=1, nombre="Caso de laboratorio",
          desarrollo_situacional="Fixture", contexto_historia="Fixture", tiempo_estimado_min=10, estado="PUBLICADO")
    poner("escenario", id=ids["escena"], version_caso_id=ids["version"], orden=1, contexto_situacional="Fixture")
    poner("pregunta", id=ids["pregunta"], escenario_id=ids["escena"], orden=1, enunciado="Fixture")
    poner("opcion_respuesta", id=ids["opcion"], pregunta_id=ids["pregunta"], orden=1, texto="Fixture",
          es_correcta=True, justificacion="Fixture")
    poner("rubrica", id=ids["rubrica"], version_caso_id=ids["version"], nombre="Fixture", version_regla="sin-formula-oficial")
    poner("criterio_rubrica", id=ids["criterio"], rubrica_id=ids["rubrica"], nombre="Fixture", peso=Decimal("100"))
    poner("nivel_rubrica", id=ids["nivel"], criterio_id=ids["criterio"], nombre="Fixture", puntaje=Decimal("1"), descriptor="Fixture")
    poner("valoracion_opcion", opcion_id=ids["opcion"], criterio_id=ids["criterio"], puntaje=Decimal("1"))
    poner("espacio_academico", id=ids["espacio"], nombre="Fixture")
    poner("sesion_programada", id=ids["sesion"], espacio_academico_id=ids["espacio"],
          version_caso_id=ids["version"], docente_id=ids["doc_scheduling"],
          fecha_inicio=FECHA.replace(tzinfo=timezone.utc), fecha_fin=(FECHA+timedelta(hours=1)).replace(tzinfo=timezone.utc),
          tiempo_maximo_minutos=5, estado="EN_CURSO")
    poner("convocatoria", id=ids["conv"], sesion_id=ids["sesion"], estudiante_id=ids["est_scheduling"],
          codigo_hash="hash-sintetico-no-utilizable", estado="ACTIVA")
    poner("notificacion", id=uuid4(), convocatoria_id=ids["conv"], destinatario_id=ids["est_scheduling"],
          tipo="PROGRAMACION", canal="INTERNA", mensaje="Fixture", creada_en=FECHA.replace(tzinfo=timezone.utc))
    poner("evento_auditoria", id=uuid4(), sesion_id=ids["sesion"], tipo="INICIO", estado_anterior="SIN_INICIAR",
          estado_nuevo="EN_CURSO", origen="SISTEMA", creado_en=FECHA.replace(tzinfo=timezone.utc))


def test_upgrade_y_downgrade_solo_nuevas_preservan_las_19(conexion):
    config = config_alembic(conexion)
    command.upgrade(config, PARENT)
    sembrar_historia_sintetica(conexion)
    antes = filas_y_estructura(conexion, ANTERIORES)
    assert all(antes[0].values())
    command.upgrade(config, HEAD)
    assert filas_y_estructura(conexion, ANTERIORES) == antes
    for n in NUEVAS:
        assert conexion.scalar(sa.select(sa.func.count()).select_from(sa.table(n))) == 0
    command.downgrade(config, PARENT)
    assert set(sa.inspect(conexion).get_table_names()) == ANTERIORES | {"alembic_version"}
    assert filas_y_estructura(conexion, ANTERIORES) == antes
    assert conexion.scalar(sa.text("SELECT version_num FROM alembic_version")) == PARENT


def test_fallo_tercera_creacion_revierte_ddl_en_postgresql(conexion_pg, monkeypatch):
    c = conexion_pg
    command.upgrade(config_alembic(c), PARENT)
    crear = op.create_table
    def fallar(nombre, *args, **kwargs):
        if nombre == "consentimiento":
            raise RuntimeError("fallo DDL inyectado en laboratorio")
        return crear(nombre, *args, **kwargs)
    monkeypatch.setattr(op, "create_table", fallar)
    with pytest.raises(RuntimeError, match="fallo DDL"):
        with c.begin_nested():
            command.upgrade(config_alembic(c), HEAD)
    assert set(sa.inspect(c).get_table_names()) == ANTERIORES | {"alembic_version"}
    assert c.scalar(sa.text("SELECT version_num FROM alembic_version")) == PARENT


@pytest.mark.parametrize("poblar", ["grupo_academico", "grupo_estudiante", "consentimiento"])
def test_downgrade_rechaza_datos_antes_de_borrar(conexion_pg, poblar, monkeypatch):
    c = conexion_pg
    command.upgrade(config_alembic(c), HEAD)
    cuentas(c)
    if poblar == "grupo_academico":
        grupo(c)
    elif poblar == "grupo_estudiante":
        c.execute(GrupoEstudianteORM.__table__.insert().values(**datos_membresia(c)))
    else:
        c.execute(ConsentimientoORM.__table__.insert().values(**datos_consentimiento()))
    antes = filas_y_estructura(c, ANTERIORES | NUEVAS)
    borrados = []
    borrar = op.drop_table
    def observar(nombre, *args, **kwargs):
        borrados.append(nombre)
        return borrar(nombre, *args, **kwargs)
    monkeypatch.setattr(op, "drop_table", observar)
    with pytest.raises(RuntimeError, match="contiene datos"):
        with c.begin_nested():
            command.downgrade(config_alembic(c), PARENT)
    assert borrados == []
    assert filas_y_estructura(c, ANTERIORES | NUEVAS) == antes
    assert c.scalar(sa.text("SELECT version_num FROM alembic_version")) == HEAD


@pytest.mark.parametrize("campo,valor", [("nombre", "x"*121), ("periodo", "x"*31)])
def test_longitud_real_postgresql_grupo(conexion_pg, campo, valor):
    c = conexion_pg
    command.upgrade(config_alembic(c), HEAD)
    cuentas(c)
    valores = dict(id_profesor=101, nombre="Fixture", periodo="2026-2") | {campo: valor}
    with pytest.raises(DataError):
        with c.begin_nested():
            c.execute(GrupoAcademicoORM.__table__.insert().values(**valores))


def test_longitud_real_postgresql_consentimiento(conexion_pg):
    c = conexion_pg
    command.upgrade(config_alembic(c), HEAD)
    cuentas(c)
    with pytest.raises(DataError):
        with c.begin_nested():
            c.execute(ConsentimientoORM.__table__.insert().values(**(datos_consentimiento() | {"version_texto": "x"*31})))
