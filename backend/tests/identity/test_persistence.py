from dataclasses import replace
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import os
import re
from uuid import uuid4

from alembic import command
from tests.identity.academic_identity_support import preparar_esquema_actual_aislado, retirar_ddl_resultados_sqlite
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.identity.api import dependencies
from app.modules.identity.api.router import router
from app.modules.identity.domain.entities import AutorizacionesDocente, DatosAltaDocente, Rol
from app.modules.identity.domain.errors import ConflictoIdentidad, IntegracionPendiente, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM, RetroalimentacionDocenteORM
from app.modules.identity.infrastructure.academic_repositories import NuevoPermisoIntentoExtra, RepositorioPermisosExtraSQLAlchemy
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM
from app.modules.identity.infrastructure.reporting_queries import ConsultaResultadosReporteSQLAlchemy, TablasLecturaReporte
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy
from .persistence_support import ACCESS_TABLES, BACKEND, bloque_dbml, columnas_dbml, tablas_academicas_prueba


def configuracion_alembic(conexion):
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("path_separator", "os")
    config.attributes["connection"] = conexion
    return config


@contextmanager
def base_aislada(motor, revision="head"):
    if motor == "sqlite":
        engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        @event.listens_for(engine, "connect")
        def activar_fk(conexion, _):
            conexion.execute("PRAGMA foreign_keys=ON")
        administrador = None
        esquema = None
    else:
        url = os.getenv("SPS_IDENTITY_TEST_URL")
        if not url:
            pytest.skip("SPS_IDENTITY_TEST_URL no configurada; no se usa la BD del proyecto.")
        administrador = create_engine(url)
        if not administrador.url.database.startswith("sps_identity_test") or administrador.url.host not in {"localhost", "127.0.0.1"}:
            administrador.dispose()
            pytest.fail("La prueba requiere una BD local aislada sps_identity_test*.")
        esquema = "sps_identity_" + uuid4().hex
        with administrador.begin() as conexion:
            conexion.execute(text(f'CREATE SCHEMA "{esquema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={esquema}"})
    try:
        with engine.begin() as conexion:
            if motor == "sqlite" and revision == "head":
                preparar_esquema_actual_aislado(conexion)
            else:
                command.upgrade(configuracion_alembic(conexion), revision)
        yield engine
    finally:
        engine.dispose()
        if administrador is not None:
            with administrador.begin() as conexion:
                conexion.execute(text(f'DROP SCHEMA "{esquema}" CASCADE'))
            administrador.dispose()


@pytest.fixture(params=["sqlite", "postgresql"])
def bd(request):
    # Integración real: siempre el head común, incluidos Identity y Cases.
    with base_aislada(request.param) as engine:
        yield engine


@pytest.fixture
def bd_dbml(bd):
    # Laboratorio del contrato académico aún no integrado. No reutilizar caso
    # UUID como si fuese caso.id_caso INTEGER ni crear un alias incompatible.
    with base_aislada(bd.dialect.name, "20261028_identity_access") as engine:
        yield engine


@pytest.fixture(scope="session")
def hash_prueba():
    return obtener_hasheador().hash("clave-exclusiva-del-laboratorio")


def sembrar_usuarios(bd, hash_prueba):
    sesiones = sessionmaker(bind=bd, expire_on_commit=False)
    with sesiones.begin() as s:
        s.add_all([RolORM(id_rol=1, nombre="ADMINISTRADOR"), RolORM(id_rol=2, nombre="DOCENTE"),
                   RolORM(id_rol=3, nombre="ESTUDIANTE")])
        s.add(PermisoORM(id_permiso=1, codigo="CREAR_CASOS", descripcion="Catálogo exclusivo de pruebas"))
        s.flush()
        s.add(RolPermisoORM(id_rol=2, id_permiso=1))
        s.add_all([UsuarioORM(id_usuario=1, id_rol=1, nombre="Administrador", correo="admin@universidad.test", clave_hash=hash_prueba),
                   UsuarioORM(id_usuario=2, id_rol=2, nombre="Docente", correo="docente@universidad.test", clave_hash=hash_prueba),
                   UsuarioORM(id_usuario=3, id_rol=3, nombre="Estudiante", correo="estudiante@universidad.test", clave_hash=hash_prueba)])
        s.flush()
        if bd.dialect.name == "postgresql":
            s.execute(text("SELECT setval(pg_get_serial_sequence('usuario', 'id_usuario'), 3, true)"))
    return sesiones


@pytest.fixture
def datos(bd, hash_prueba):
    return sembrar_usuarios(bd, hash_prueba)


@pytest.fixture
def datos_dbml(bd_dbml, hash_prueba):
    return sembrar_usuarios(bd_dbml, hash_prueba)


def autorizaciones(permisos=frozenset({"CREAR_CASOS"})):
    return AutorizacionesDocente(frozenset({Rol.DOCENTE}), permisos)


def test_migraciones_integradas_upgrade_downgrade_crean_ambos_modulos(bd):
    from app.db.models import registrar_modelos_integrados
    esperadas = set(registrar_modelos_integrados().tables)
    assert {"usuario", "rol", "permiso", "rol_permiso", "caso", "version_caso", "rubrica"} <= esperadas
    assert set(inspect(bd).get_table_names()) == esperadas | {"alembic_version"}
    with bd.begin() as conexion:
        if conexion.dialect.name=="sqlite":
            retirar_ddl_resultados_sqlite(conexion)
        command.downgrade(configuracion_alembic(conexion), "base")
    assert set(inspect(bd).get_table_names()) == {"alembic_version"}


@pytest.mark.parametrize("modelo", [RolORM, PermisoORM, RolPermisoORM, UsuarioORM, PermisoIntentoExtraORM, RetroalimentacionDocenteORM])
def test_mapeos_coinciden_con_columnas_tipos_nulabilidad_y_fk_del_dbml(modelo):
    tabla = modelo.__table__
    especificacion = columnas_dbml(tabla.name)
    if modelo is RetroalimentacionDocenteORM:
        # Adaptación individual autorizada: se preservan las columnas originales.
        especificacion.append(("id_participacion", "int", "", "not null, ref: > participacion.id_participacion"))
        assert tabla.c.id_participacion.unique is True
        assert tabla.c.id_asignacion.unique is not True
    assert set(tabla.c.keys()) == {campo for campo, _, _, _ in especificacion}
    for campo, tipo, tamanio, flags in especificacion:
        columna = tabla.c[campo]
        assert columna.nullable == ("not null" not in flags and not columna.primary_key)
        if tipo == "varchar":
            assert columna.type.length == int(tamanio)
        if tipo == "timestamp":
            assert columna.type.timezone is False
        fk = re.search(r"ref: > ([\w.]+)", flags)
        assert {r.target_fullname for r in columna.foreign_keys} == ({fk.group(1)} if fk else set())
    assert "usuario_permiso" not in tabla.metadata.tables
    assert "autorizacion_repeticion" not in tabla.metadata.tables


def test_usuario_un_solo_rol_y_permisos_derivados_del_rol(datos):
    with datos() as s:
        usuario = RepositorioUsuariosSQLAlchemy(s).obtener("2")
    assert usuario.roles == frozenset({Rol.DOCENTE})
    assert usuario.permisos == frozenset({"CREAR_CASOS"})
    assert usuario.activo is True


@pytest.mark.parametrize("identificador", ["0", "-1", "docente-1", "1 OR 1=1", "2147483648"])
def test_identificador_invalido_no_consulta_usuario(datos, identificador):
    with datos() as s:
        assert RepositorioUsuariosSQLAlchemy(s).obtener(identificador) is None


def test_crear_docente_persiste_nombre_hash_rol_y_default_activo(datos, hash_prueba):
    with UnidadTrabajoIdentitySQLAlchemy(usuarios=RepositorioUsuariosSQLAlchemy, sesiones=datos) as uow:
        usuario = uow.usuarios.crear_docente("Nuevo@Universidad.Test", autorizaciones(),
                                          datos=DatosAltaDocente("Nuevo docente", hash_prueba))
        uow.commit()
    with datos() as s:
        persistido = s.get(UsuarioORM, int(usuario.id_usuario))
        assert persistido.nombre == "Nuevo docente" and persistido.correo == "nuevo@universidad.test"
        assert persistido.clave_hash == hash_prueba and persistido.activo is True


def test_creacion_sin_datos_obligatorios_no_fabrica_nombre_o_clave(datos):
    with datos() as s:
        with pytest.raises(ReglaIdentidadInvalida):
            RepositorioUsuariosSQLAlchemy(s).crear_docente("nuevo@universidad.test", autorizaciones())


def test_no_modifica_permisos_del_rol_para_conceder_permiso_individual(datos):
    with datos() as s:
        with pytest.raises(ReglaIdentidadInvalida):
            RepositorioUsuariosSQLAlchemy(s).asignar_autorizaciones("2", autorizaciones(frozenset()))
        assert s.scalars(select(RolPermisoORM)).one().id_permiso == 1
        assert RepositorioUsuariosSQLAlchemy(s).obtener("2").permisos == frozenset({"CREAR_CASOS"})


def test_no_acepta_multirrol_que_el_er_no_representa(datos):
    with datos() as s:
        with pytest.raises(ReglaIdentidadInvalida):
            RepositorioUsuariosSQLAlchemy(s).asignar_autorizaciones("2", AutorizacionesDocente(
                frozenset({Rol.DOCENTE, Rol.ADMINISTRADOR}), frozenset({"CREAR_CASOS"})))


def test_unicidad_correo_y_rollback_atomico(datos, hash_prueba):
    with pytest.raises(ConflictoIdentidad):
        with UnidadTrabajoIdentitySQLAlchemy(usuarios=RepositorioUsuariosSQLAlchemy, sesiones=datos) as uow:
            uow.usuarios.crear_docente("nuevo@universidad.test", autorizaciones(), datos=DatosAltaDocente("Nuevo", hash_prueba))
            uow.usuarios.crear_docente("docente@universidad.test", autorizaciones(), datos=DatosAltaDocente("Duplicado", hash_prueba))
            uow.commit()
    with datos() as s:
        assert s.scalar(select(UsuarioORM).where(UsuarioORM.correo == "nuevo@universidad.test")) is None


def test_fk_usuario_y_pk_compuesta_rol_permiso_se_cumplen(datos, hash_prueba):
    with datos() as s:
        with pytest.raises(IntegrityError):
            s.add(UsuarioORM(id_rol=999, nombre="Inválido", correo="invalido@universidad.test", clave_hash=hash_prueba))
            s.flush()
        s.rollback()
        with pytest.raises(IntegrityError):
            s.add(RolPermisoORM(id_rol=2, id_permiso=1))
            s.flush()


def test_uow_parcial_no_simula_adaptadores_academicos(datos):
    with UnidadTrabajoIdentitySQLAlchemy(usuarios=RepositorioUsuariosSQLAlchemy, sesiones=datos) as uow:
        assert uow.usuarios.obtener("2") is not None
        with pytest.raises(IntegracionPendiente):
            _ = uow.feedback


@pytest.fixture
def cliente_bd(datos, tokens, monkeypatch):
    monkeypatch.setattr(dependencies, "get_session_factory", lambda: datos)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[dependencies.obtener_fabrica_tokens] = lambda: lambda: tokens
    with TestClient(app) as cliente:
        yield cliente


def test_http_me_resuelve_usuario_y_permisos_con_repositorio_real(cliente_bd, tokens):
    respuesta = cliente_bd.get("/api/v1/identity/me", headers={"Authorization": "Bearer " + tokens.emitir("2")})
    assert respuesta.status_code == 200
    assert respuesta.json()["roles"] == ["DOCENTE"] and respuesta.json()["permisos"] == ["CREAR_CASOS"]
    assert "clave_hash" not in respuesta.text


def test_http_403_estudiante_con_repositorio_real(cliente_bd, tokens):
    respuesta = cliente_bd.post("/api/v1/identity/excepciones/repeticiones",
        headers={"Authorization": "Bearer " + tokens.emitir("3", "1")},
        json={"id_sesion": "1", "id_estudiante": "3"})
    assert respuesta.status_code == 403


def test_http_crea_docente_con_uow_repositorio_proxy_y_hash_reales(cliente_bd, tokens, datos):
    respuesta = cliente_bd.post("/api/v1/identity/docentes",
        headers={"Authorization": "Bearer " + tokens.emitir("1")},
        json={"correo": "nuevo@universidad.test", "nombre": "Nombre docente",
              "clave": "clave-exclusiva-nuevo-docente", "permisos": ["CREAR_CASOS"]})
    assert respuesta.status_code == 201
    assert "clave" not in respuesta.text
    with datos() as s:
        usuario = s.scalar(select(UsuarioORM).where(UsuarioORM.correo == "nuevo@universidad.test"))
        assert usuario.nombre == "Nombre docente"
        assert obtener_hasheador().verify("clave-exclusiva-nuevo-docente", usuario.clave_hash)


def test_http_no_administra_catalogo_global_por_usuario(cliente_bd, tokens):
    respuesta = cliente_bd.put("/api/v1/identity/docentes/2/autorizaciones",
        headers={"Authorization": "Bearer " + tokens.emitir("1")}, json={"roles": ["DOCENTE"], "permisos": []})
    assert respuesta.status_code == 422


def test_http_asigna_el_rol_con_sus_permisos_reales(cliente_bd, tokens):
    respuesta = cliente_bd.put("/api/v1/identity/docentes/2/autorizaciones",
        headers={"Authorization": "Bearer " + tokens.emitir("1")},
        json={"roles": ["DOCENTE"], "permisos": ["CREAR_CASOS"]})
    assert respuesta.status_code == 200
    assert respuesta.json()["permisos"] == ["CREAR_CASOS"]


def test_http_alta_real_sin_nombre_y_clave_no_inventa_datos(cliente_bd, tokens):
    respuesta = cliente_bd.post("/api/v1/identity/docentes",
        headers={"Authorization": "Bearer " + tokens.emitir("1")},
        json={"correo": "nuevo@universidad.test", "permisos": ["CREAR_CASOS"]})
    assert respuesta.status_code == 422


def test_http_usuario_inactivo_en_bd_pierde_acceso_con_jwt_existente(cliente_bd, datos, tokens):
    headers = {"Authorization": "Bearer " + tokens.emitir("2")}
    assert cliente_bd.get("/api/v1/identity/me", headers=headers).status_code == 200
    with datos.begin() as s:
        s.get(UsuarioORM, 2).activo = False
    assert cliente_bd.get("/api/v1/identity/me", headers=headers).status_code == 401


def test_http_sin_asociaciones_no_abre_seguimiento_ni_excepciones(cliente_bd, tokens):
    headers = {"Authorization": "Bearer " + tokens.emitir("2")}
    # Seguimiento ya está conectado: cuenta sin asociación académica => 403.
    # Las excepciones siguen sin composición y conservan su 503.
    assert cliente_bd.get("/api/v1/identity/seguimiento/casos", headers=headers).status_code == 403
    assert cliente_bd.post("/api/v1/identity/excepciones/repeticiones", headers=headers,
                           json={"id_sesion": "1", "id_estudiante": "3"}).status_code == 503


@pytest.fixture
def academia(bd_dbml, datos_dbml):
    tablas = tablas_academicas_prueba(bd_dbml)
    fecha = datetime(2026, 10, 28, 12)
    with bd_dbml.begin() as c:
        c.execute(tablas["grupo_academico"].insert().values(id_grupo=1, id_profesor=2, nombre="Grupo", periodo="2026-2"))
        c.execute(tablas["grupo_estudiante"].insert().values(id_grupo_estudiante=1, id_grupo=1, id_estudiante=3, fecha_ingreso=fecha))
        c.execute(tablas["caso"].insert().values(id_caso=1, id_profesor=2, titulo="Caso", introduccion_teorica="Contexto", fecha_creacion=fecha))
        c.execute(tablas["asignacion_caso"].insert().values(id_asignacion=1, id_grupo=1, id_caso=1,
            apertura=fecha, cierre=fecha, fecha_limite_ingreso=fecha, tiempo_maximo_min=20, codigo_acceso_hash="hash-solo-fixture"))
        c.execute(tablas["participacion"].insert().values(id_participacion=1, id_asignacion=1, id_grupo_estudiante=1, fecha_registro=fecha))
    return tablas


def test_permiso_extra_persiste_columnas_reales_y_fk_sin_consumir_intentos(datos_dbml, academia):
    datos = datos_dbml
    nuevo = NuevoPermisoIntentoExtra(1, 2, 2, "Concesión documentada", datetime(2026, 10, 28, 12))
    with datos.begin() as s:
        identificador = RepositorioPermisosExtraSQLAlchemy(s).agregar(nuevo)
    with datos() as s:
        permiso = s.get(PermisoIntentoExtraORM, identificador)
        assert permiso.id_participacion == 1 and permiso.id_profesor == 2
        assert permiso.cantidad_autorizada == 2 and permiso.justificacion == "Concesión documentada"
        with pytest.raises(ConflictoIdentidad):
            RepositorioPermisosExtraSQLAlchemy(s).agregar(replace(nuevo, id_participacion=999))


def test_permiso_extra_sin_commit_no_se_persiste(datos_dbml, academia):
    datos = datos_dbml
    with datos() as s:
        RepositorioPermisosExtraSQLAlchemy(s).agregar(NuevoPermisoIntentoExtra(1, 2, 1, "Justificación", datetime(2026, 10, 28)))
    with datos() as s:
        assert s.scalars(select(PermisoIntentoExtraORM)).all() == []


def test_permiso_extra_no_adapta_fechas_utc_a_timestamp_sin_acuerdo(datos_dbml, academia):
    datos = datos_dbml
    with datos() as s:
        with pytest.raises(ReglaIdentidadInvalida):
            RepositorioPermisosExtraSQLAlchemy(s).agregar(NuevoPermisoIntentoExtra(
                1, 2, 1, "Justificación", datetime(2026, 10, 28, tzinfo=UTC)))


def test_feedback_dbml_original_y_adaptacion_individual_autorizada():
    tabla = RetroalimentacionDocenteORM.__table__
    original=columnas_dbml("retroalimentacion_docente")
    assert "unique" in next(flags for campo,_,_,flags in original if campo=="id_asignacion")
    assert "id_participacion" not in {campo for campo,_,_,_ in original}
    assert tabla.c.id_asignacion.unique is not True
    assert tabla.c.id_participacion.unique is True
    assert {f.target_fullname for f in tabla.c.id_participacion.foreign_keys}=={"participacion.id_participacion"}


def test_left_join_real_conserva_fila_sin_resultado_sin_inventar_ausencia(datos_dbml, academia):
    datos = datos_dbml
    tablas = TablasLecturaReporte(*(academia[n] for n in ("participacion", "grupo_estudiante", "resultado_participacion")))
    with datos() as s:
        consulta = ConsultaResultadosReporteSQLAlchemy(s, tablas)
        filas = consulta.consultar(1, (1,))
        assert len(filas) == 1 and filas[0].id_estudiante == 3
        assert filas[0].nota is None and filas[0].situacion is None
        assert consulta.consultar(1, ()) == ()
        sql = str(consulta.sentencia(1, (1,)).compile(dialect=postgresql.dialect()))
        assert "LEFT OUTER JOIN resultado_participacion" in sql


@pytest.mark.parametrize("situacion,nota", [("completa", "4.25"), ("parcial", "2.10"), ("ausencia", "0.00")])
def test_left_join_preserva_resultado_oficial_sin_reclasificar(datos_dbml, academia, situacion, nota):
    datos = datos_dbml
    with datos.begin() as s:
        s.execute(academia["resultado_participacion"].insert().values(
            id_participacion=1, situacion=situacion, nota_definitiva=Decimal(nota), fecha_calculo=datetime(2026, 10, 28)))
    with datos() as s:
        tablas = TablasLecturaReporte(*(academia[n] for n in ("participacion", "grupo_estudiante", "resultado_participacion")))
        fila = ConsultaResultadosReporteSQLAlchemy(s, tablas).consultar(1, (1,))[0]
        assert fila.situacion == situacion and fila.nota == Decimal(nota)
