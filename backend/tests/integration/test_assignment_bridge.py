"""P1-P3: DML real y carreras solo en un PostgreSQL nuevo del fixture propietario.

SQLite verifica DDL/metadata; no simula los triggers ni la secuencia PostgreSQL.
Todos los usuarios, grupos y contenidos son sintéticos, sin autorizar RF-22.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from alembic import command
from tests.identity.academic_identity_support import preparar_esquema_actual_aislado, retirar_ddl_resultados_sqlite
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.models import registrar_modelos_integrados
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM
from app.modules.identity.infrastructure.models import RolORM, UsuarioORM
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico, VinculoAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
from app.modules.scheduling.domain.access_codes import hash_codigo
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel, SesionProgramadaModel
from tests.identity.academic_identity_support import config_alembic, motor_postgresql_desechable
from tests.integration.test_cases_history import nuevo, publicar, leer

HEAD = "20261102_assignment_bridge"
PARENT = "20261102_cases_history_guard"
T = AsignacionCasoModel.__table__
FECHA = datetime(2026, 11, 2, 12)


@pytest.fixture(scope="module")
def laboratorio():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as c:
            command.upgrade(config_alembic(c), HEAD)
            c.execute(RolORM.__table__.insert(), [dict(id_rol=1, nombre="DOCENTE"), dict(id_rol=2, nombre="ESTUDIANTE")])
        yield engine


def preparar(engine):
    fabrica = sessionmaker(engine, expire_on_commit=False)
    v = nuevo()
    with fabrica() as s:
        CasoRepository(s).guardar(v)
    v = publicar(fabrica, v)
    with fabrica.begin() as s:
        usuario = UsuarioORM(id_rol=1, nombre="Fixture explícita", correo=f"{uuid4()}@fixture.test", clave_hash="no-utilizable")
        espacio = EspacioAcademicoModel(nombre="Laboratorio propio")
        s.add_all([usuario, espacio]); s.flush()
        grupo = GrupoAcademicoORM(id_profesor=usuario.id_usuario, nombre="Grupo sintético", periodo="2026-2")
        s.add(grupo); s.flush()
        sesion = SesionProgramadaModel(espacio_academico_id=espacio.id, version_caso_id=v.id,
            docente_id=uuid4(), fecha_inicio=FECHA.replace(tzinfo=timezone.utc),
            fecha_fin=(FECHA+timedelta(hours=1)).replace(tzinfo=timezone.utc), tiempo_maximo_minutos=30)
        s.add(sesion); s.flush()
        clave = s.get(CasoModel, v.caso_id).id_caso
        valores = dict(id_grupo=grupo.id_grupo, id_caso=clave, sesion_programada_id=sesion.id,
            version_caso_id=v.id, apertura=FECHA, cierre=FECHA+timedelta(hours=1),
            fecha_limite_ingreso=FECHA, tiempo_maximo_min=30, codigo_acceso_hash=None)
    return fabrica, v, valores


@pytest.fixture
def contexto(laboratorio):
    return preparar(laboratorio)


def insertar(c, valores):
    return c.scalar(T.insert().values(**valores).returning(T.c.id_asignacion))


def test_metadata_SQLite_y_downgrade_sin_generacion_ficticia():
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as c:
            c.exec_driver_sql("PRAGMA foreign_keys=ON")
            command.upgrade(config_alembic(c), HEAD)
            assert len(registrar_modelos_integrados().tables) == 30
            preparar_esquema_actual_aislado(c)
            assert compare_metadata(MigrationContext.configure(c), registrar_modelos_integrados()) == []
            identificador = uuid4()
            c.execute(CasoModel.__table__.insert().values(id=identificador, docente_creador_id=uuid4()))
            assert c.scalar(sa.select(CasoModel.id_caso).where(CasoModel.id == identificador)) is None
            assert c.scalar(sa.text("SELECT count(*) FROM sqlite_master WHERE type='trigger'")) == 0
            retirar_ddl_resultados_sqlite(c)
            command.downgrade(config_alembic(c), PARENT)
            assert "asignacion_caso" not in sa.inspect(c).get_table_names()
            command.upgrade(config_alembic(c), HEAD)
            assert c.scalar(sa.select(CasoModel.id).where(CasoModel.id == identificador)) == identificador
    finally:
        engine.dispose()


def test_upgrade_legado_sin_backfill_y_downgrade_controlado():
    with motor_postgresql_desechable() as engine:
        identificador, docente = uuid4(), uuid4()
        with engine.begin() as c:
            command.upgrade(config_alembic(c), PARENT)
            c.execute(CasoModel.__table__.insert().values(id=identificador, docente_creador_id=docente))
            command.upgrade(config_alembic(c), HEAD)
            assert c.scalar(sa.select(CasoModel.id_caso).where(CasoModel.id == identificador)) is None
            assert c.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal")) == 19
            preparar_esquema_actual_aislado(c)
            assert compare_metadata(MigrationContext.configure(c), registrar_modelos_integrados()) == []
            command.downgrade(config_alembic(c), PARENT)
            assert c.scalar(sa.select(CasoModel.docente_creador_id).where(CasoModel.id == identificador)) == docente
            assert c.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal")) == 18
            command.upgrade(config_alembic(c), HEAD)
            nuevo_uuid = uuid4()
            clave = c.scalar(CasoModel.__table__.insert().values(id=nuevo_uuid, docente_creador_id=docente).returning(CasoModel.id_caso))
            assert type(clave) is int and clave > 0
            with pytest.raises(RuntimeError, match="identidades academicas"):
                with c.begin_nested():
                    command.downgrade(config_alembic(c), PARENT)
            assert c.scalar(sa.select(CasoModel.id_caso).where(CasoModel.id == nuevo_uuid)) == clave
            assert c.scalar(sa.text("SELECT version_num FROM alembic_version")) == HEAD


def test_clave_ORM_generada_unica_y_UUID_real_estable(laboratorio, contexto):
    fabrica, v, valores = contexto
    otra = preparar(laboratorio)[2]
    assert type(valores["id_caso"]) is int and valores["id_caso"] != otra["id_caso"]
    with fabrica() as s:
        assert s.scalar(sa.select(CasoModel.id).where(CasoModel.id_caso == valores["id_caso"])) == v.caso_id
    with laboratorio.begin() as c:
        with pytest.raises(IntegrityError) as error:
            with c.begin_nested():
                c.execute(CasoModel.__table__.insert().values(id=uuid4(), docente_creador_id=uuid4(), id_caso=valores["id_caso"]))
        assert error.value.orig.sqlstate == "23505"
        with pytest.raises(IntegrityError):
            with c.begin_nested():
                c.execute(sa.update(CasoModel).where(CasoModel.id == v.caso_id).values(id_caso=2147483647))


def test_asignacion_ORM_conserva_identidades_y_codigo_grupal_nulo(laboratorio, contexto):
    fabrica, v, valores = contexto
    with fabrica.begin() as s:
        fila = AsignacionCasoModel(**valores)
        s.add(fila); s.flush()
        assert type(fila.id_asignacion) is int
        assert fila.codigo_acceso_hash is None and fila.intentos_base == 1
        assert fila.version_caso_id == v.id and fila.id_caso == valores["id_caso"]
    with laboratorio.begin() as c:
        with pytest.raises(RuntimeError, match="asignaciones"):
            with c.begin_nested():
                command.downgrade(config_alembic(c), PARENT)


@pytest.mark.parametrize("campo,valor", [
    ("id_grupo", 2147483647), ("id_caso", 2147483647),
    ("sesion_programada_id", "uuid"), ("version_caso_id", "uuid"),
    ("id_grupo", None), ("id_caso", None), ("version_caso_id", None), ("sesion_programada_id", None),
])
def test_referencias_inexistentes_y_null_rechazados_con_rollback(laboratorio, contexto, campo, valor):
    valores = contexto[2] | {campo: uuid4() if valor == "uuid" else valor}
    with laboratorio.begin() as c:
        with pytest.raises(IntegrityError):
            with c.begin_nested():
                insertar(c, valores)
        assert c.scalar(sa.select(sa.func.count()).select_from(T).where(T.c.sesion_programada_id == contexto[2]["sesion_programada_id"])) == 0
        assert c.scalar(sa.select(sa.literal(1))) == 1


def test_version_de_otra_familia_rechazada(laboratorio, contexto):
    ajena = preparar(laboratorio)[2]
    with laboratorio.begin() as c, pytest.raises(IntegrityError) as error:
        insertar(c, contexto[2] | {"version_caso_id": ajena["version_caso_id"], "sesion_programada_id": ajena["sesion_programada_id"]})
    assert error.value.orig.sqlstate == "23514"


def test_sesion_de_otra_version_rechazada_por_FK_compuesta(laboratorio, contexto):
    ajena = preparar(laboratorio)[2]
    with laboratorio.begin() as c, pytest.raises(IntegrityError) as error:
        insertar(c, contexto[2] | {"sesion_programada_id": ajena["sesion_programada_id"]})
    assert error.value.orig.sqlstate == "23503"


@pytest.mark.parametrize("condicion", ["borrador", "sin_rubrica", "archivado"])
def test_asignar_requiere_publicacion_y_rubrica_propia(laboratorio, contexto, condicion):
    fabrica, v, valores = contexto
    if condicion == "archivado":
        v.archivar()
        with fabrica() as s:
            CasoRepository(s).actualizar_estado(v)
    else:
        nueva = nuevo()
        if condicion == "sin_rubrica":
            nueva.rubrica = None
            for escena in nueva.escenarios:
                for pregunta in escena.preguntas:
                    for opcion in pregunta.opciones:
                        opcion.valoraciones = {}
        with fabrica() as s:
            CasoRepository(s).guardar(nueva)
        with laboratorio.begin() as c:
            if condicion == "sin_rubrica":
                c.execute(sa.update(VersionCasoModel).where(VersionCasoModel.id == nueva.id).values(estado="PUBLICADO"))
            valores = valores | {"id_caso": c.scalar(sa.select(CasoModel.id_caso).where(CasoModel.id == nueva.caso_id)), "version_caso_id": nueva.id}
    with laboratorio.begin() as c, pytest.raises(IntegrityError) as error:
        insertar(c, valores)
    assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize("campo", ["id_asignacion", "id_caso", "id_grupo", "version_caso_id", "sesion_programada_id"])
def test_contexto_historico_no_se_reasigna(laboratorio, contexto, campo):
    with laboratorio.begin() as c:
        pk = insertar(c, contexto[2])
        valor = uuid4() if campo.endswith("_id") else 2147483647
        with pytest.raises(IntegrityError) as error:
            with c.begin_nested():
                c.execute(T.update().where(T.c.id_asignacion == pk).values(**{campo: valor}))
        assert error.value.orig.sqlstate == "23514"
        assert c.scalar(sa.select(T.c.version_caso_id).where(T.c.id_asignacion == pk)) == contexto[1].id


def test_nueva_edicion_no_sustituye_version_rubrica_ni_regla(laboratorio, contexto):
    fabrica, anterior, valores = contexto
    with laboratorio.begin() as c:
        pk = insertar(c, valores)
    segunda = nuevo()
    segunda.caso_id, segunda.numero, segunda.docente_creador_id = anterior.caso_id, 2, anterior.docente_creador_id
    # Fixture histórica explícita: guardar() crea familias nuevas; este
    # experimento agrega una edición a la familia existente sin cambiar la API.
    with fabrica.begin() as s:
        modelo = CasoRepository(s)._mapear(segunda)
        edicion = modelo.versiones.pop()
        familia = s.get(CasoModel, anterior.caso_id)
        familia.versiones.append(edicion)
    publicar(fabrica, segunda)
    anterior.archivar()
    with fabrica() as s:
        CasoRepository(s).actualizar_estado(anterior)
    with laboratorio.begin() as c:
        assert c.scalar(sa.select(T.c.version_caso_id).where(T.c.id_asignacion == pk)) == anterior.id
        assert c.scalar(sa.select(SesionProgramadaModel.version_caso_id).where(SesionProgramadaModel.id == valores["sesion_programada_id"])) == anterior.id
        with pytest.raises(IntegrityError) as error:
            with c.begin_nested():
                c.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id == valores["sesion_programada_id"]).values(version_caso_id=segunda.id))
        assert error.value.orig.sqlstate == "23503"
    historica = leer(fabrica, anterior)
    assert historica.rubrica == anterior.rubrica
    assert historica.rubrica.id != segunda.rubrica.id


def test_unique_sesion_grupo_y_otros_grupos_explicitos(laboratorio, contexto):
    valores = contexto[2]
    with laboratorio.begin() as c:
        pk = insertar(c, valores)
        with pytest.raises(IntegrityError) as error:
            with c.begin_nested():
                insertar(c, valores)
        assert error.value.orig.sqlstate == "23505"
        otro_grupo = preparar(laboratorio)[2]["id_grupo"]
        assert insertar(c, valores | {"id_grupo": otro_grupo}) != pk


def test_dos_asignaciones_concurrentes_mismo_contexto_un_solo_ganador(laboratorio, contexto):
    inicio = Barrier(2)
    def escritor(_):
        try:
            with laboratorio.begin() as c:
                c.exec_driver_sql("SET LOCAL lock_timeout='5s'")
                inicio.wait(timeout=5)
                insertar(c, contexto[2])
            return "commit"
        except IntegrityError as error:
            return error.orig.sqlstate
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(escritor, range(2))) == ["23505", "commit"]
    with laboratorio.connect() as c:
        assert c.scalar(sa.select(sa.func.count()).select_from(T).where(T.c.sesion_programada_id == contexto[2]["sesion_programada_id"])) == 1


def test_retarget_concurrente_con_insercion_no_deja_asociacion_incorrecta(laboratorio, contexto):
    otra = preparar(laboratorio)[1]
    inicio = Barrier(2)
    def escritor(asignar):
        try:
            with laboratorio.begin() as c:
                c.exec_driver_sql("SET LOCAL lock_timeout='5s'")
                inicio.wait(timeout=5)
                if asignar:
                    insertar(c, contexto[2])
                else:
                    c.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id == contexto[2]["sesion_programada_id"]).values(version_caso_id=otra.id))
            return "commit"
        except IntegrityError as error:
            return error.orig.sqlstate
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(escritor, (True, False))) == ["23503", "commit"]
    with laboratorio.connect() as c:
        assert c.scalar(sa.text("SELECT count(*) FROM asignacion_caso a JOIN sesion_programada s ON s.id=a.sesion_programada_id WHERE a.version_caso_id<>s.version_caso_id")) == 0


def test_rollback_asignacion_no_deja_registro_parcial(laboratorio, contexto):
    with laboratorio.connect() as c:
        tx = c.begin()
        insertar(c, contexto[2])
        tx.rollback()
        assert c.scalar(sa.select(sa.func.count()).select_from(T).where(T.c.sesion_programada_id == contexto[2]["sesion_programada_id"])) == 0


def test_codigo_grupal_no_sustituye_individual_ni_titularidad(contexto):
    fabrica, _, valores = contexto
    codigo_grupal = "grupal-exclusivo-" + uuid4().hex
    correo = uuid4().hex + "@fixture.test"
    with fabrica.begin() as s:
        alumnos = [UsuarioORM(id_rol=2, nombre="Alumno sintético", correo=correo if i == 0 else uuid4().hex+"@fixture.test", clave_hash="no-utilizable") for i in range(2)]
        s.add_all(alumnos); s.flush()
        convocatorias = []
        for alumno in alumnos:
            estudiante_uuid = uuid4()
            RepositorioIdentidadAcademicaSQLAlchemy(s).agregar_verificado(VinculoAcademico(str(alumno.id_usuario), SistemaAcademico.SCHEDULING, estudiante_uuid))
            convocatorias.append(crear_convocatoria(s, sesion_id=valores["sesion_programada_id"], estudiante_id=estudiante_uuid))
        s.add(AsignacionCasoModel(**(valores | {"codigo_acceso_hash": hash_codigo(codigo_grupal)})))
    with fabrica() as s:
        validador = ValidadorConvocatoriaScheduling(s, RepositorioUsuariosSQLAlchemy(s), ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s)))
        assert validador.validar(correo, codigo_grupal) is None
        assert validador.validar(correo, convocatorias[1].codigo_acceso) is None
        acceso = validador.validar(correo, convocatorias[0].codigo_acceso)
        assert acceso.id_convocatoria == str(convocatorias[0].convocatoria_id)
    # Autenticar convocatoria NO acredita matrícula ni habilita iniciar intento.


def test_PK_y_FK_impiden_duplicar_asignacion_o_borrar_sesion_referida(laboratorio, contexto):
    with laboratorio.begin() as c:
        pk = insertar(c, contexto[2])
        with pytest.raises(IntegrityError) as duplicada:
            with c.begin_nested():
                insertar(c, contexto[2] | {"id_asignacion": pk})
        assert duplicada.value.orig.sqlstate == "23505"
        with pytest.raises(IntegrityError) as huerfana:
            with c.begin_nested():
                c.execute(sa.delete(SesionProgramadaModel).where(SesionProgramadaModel.id == contexto[2]["sesion_programada_id"]))
        assert huerfana.value.orig.sqlstate == "23503"
