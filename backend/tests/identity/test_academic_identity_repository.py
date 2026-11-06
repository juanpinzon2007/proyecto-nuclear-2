from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

from alembic import command
from tests.identity.academic_identity_support import preparar_esquema_actual_aislado, retirar_ddl_resultados_sqlite
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import inspect, select, null
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import registrar_modelos_integrados
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico, VinculoAcademico
from app.modules.identity.domain.errors import AccesoDenegado, ConflictoIdentidad, IntegracionPendiente, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Repo
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel, SesionProgramadaModel
from .academic_identity_support import (  # noqa: F401
    motor_identidades, cuentas_identidades, config_alembic, ANTERIOR, REVISION,
)


def vinculo(c, sistema=SistemaAcademico.CASES):
    return VinculoAcademico(str(c.propio), sistema, c.uuid)


@pytest.mark.parametrize("sistema", list(SistemaAcademico))
def test_resuelve_uuid_persistido_exactamente(cuentas_identidades, sistema):
    c = cuentas_identidades
    with c.sesiones.begin() as s:
        Repo(s).agregar_verificado(vinculo(c, sistema))
    with c.sesiones() as s:
        assert ResolverIdentidadAcademica(Repo(s)).resolver(id_usuario=str(c.propio), sistema=sistema) == c.uuid


def test_sin_asociacion_rechaza(cuentas_identidades):
    c = cuentas_identidades
    with c.sesiones() as s, pytest.raises(AccesoDenegado):
        ResolverIdentidadAcademica(Repo(s)).resolver(id_usuario=str(c.propio), sistema=SistemaAcademico.CASES)


def test_varios_uuid_se_conservan_pero_resolver_no_elige(cuentas_identidades):
    c = cuentas_identidades
    with c.sesiones.begin() as s:
        Repo(s).agregar_verificado(vinculo(c))
        Repo(s).agregar_verificado(VinculoAcademico(str(c.propio), SistemaAcademico.CASES, uuid4()))
    with c.sesiones() as s:
        assert len(Repo(s).obtener(id_usuario=str(c.propio), sistema=SistemaAcademico.CASES)) == 2
        with pytest.raises(IntegracionPendiente):
            ResolverIdentidadAcademica(Repo(s)).resolver(id_usuario=str(c.propio), sistema=SistemaAcademico.CASES)


def test_no_reasigna_uuid_ni_hace_upsert_y_rollback_recupera(cuentas_identidades):
    c = cuentas_identidades
    with c.sesiones.begin() as s:
        Repo(s).agregar_verificado(vinculo(c))
    with c.sesiones() as s:
        with pytest.raises(ConflictoIdentidad):
            Repo(s).agregar_verificado(VinculoAcademico(str(c.ajeno), SistemaAcademico.CASES, c.uuid))
        s.rollback()
        assert Repo(s).obtener(id_usuario=str(c.ajeno), sistema=SistemaAcademico.CASES) == ()
        assert Repo(s).obtener(id_usuario=str(c.propio), sistema=SistemaAcademico.CASES) == (vinculo(c),)


def test_mismo_uuid_en_otro_sistema_no_implica_misma_cuenta(cuentas_identidades):
    c = cuentas_identidades
    with c.sesiones.begin() as s:
        Repo(s).agregar_verificado(vinculo(c))
        Repo(s).agregar_verificado(VinculoAcademico(str(c.ajeno), SistemaAcademico.SCHEDULING, c.uuid))
    with c.sesiones() as s:
        assert ResolverIdentidadAcademica(Repo(s)).resolver(id_usuario=str(c.ajeno), sistema=SistemaAcademico.SCHEDULING) == c.uuid


@pytest.mark.parametrize("error", ["usuario_inexistente", "usuario_null", "sistema", "uuid_nulo", "uuid_null"])
def test_restricciones_reales_no_dependen_del_repositorio(cuentas_identidades, error):
    c = cuentas_identidades
    fila = dict(id_usuario=c.propio, sistema="CASES", id_academico=c.uuid)
    fila.update({
        "usuario_inexistente": dict(id_usuario=2147483647), "usuario_null": dict(id_usuario=None),
        "sistema": dict(sistema="OTRO"), "uuid_nulo": dict(id_academico=UUID(int=0)),
        "uuid_null": dict(id_academico=None),
    }[error])
    with pytest.raises(IntegrityError):
        with c.sesiones.begin() as s:
            s.execute(IdentidadAcademicaORM.__table__.insert().values(**fila))


def test_salir_sin_commit_no_persiste(cuentas_identidades):
    c = cuentas_identidades
    with c.sesiones() as s:
        Repo(s).agregar_verificado(vinculo(c))
    with c.sesiones() as s:
        assert Repo(s).obtener(id_usuario=str(c.propio), sistema=SistemaAcademico.CASES) == ()


@pytest.mark.parametrize("identificador", ["0", "01", "no-entero", "2147483648"])
def test_identificador_invalido_cierra_sin_consultar(identificador):
    s = Mock(spec=Session)
    with pytest.raises(IntegracionPendiente):
        Repo(s).obtener(id_usuario=identificador, sistema=SistemaAcademico.CASES)
    s.scalars.assert_not_called()


def test_corrupcion_devuelta_por_driver_cierra_acceso():
    s = Mock(spec=Session)
    s.no_autoflush = Session().no_autoflush
    s.scalars.return_value.all.return_value = [SimpleNamespace(id_usuario=7, sistema="CASES", id_academico=None)]
    with pytest.raises(IntegracionPendiente):
        Repo(s).obtener(id_usuario="7", sistema=SistemaAcademico.CASES)


def test_error_sql_no_filtra_diagnostico():
    s = Mock(spec=Session)
    s.no_autoflush = Session().no_autoflush
    s.scalars.side_effect = SQLAlchemyError("detalle privado")
    with pytest.raises(IntegracionPendiente) as fallo:
        Repo(s).obtener(id_usuario="7", sistema=SistemaAcademico.CASES)
    assert "privado" not in str(fallo.value)


def test_error_inesperado_no_se_oculta():
    s = Mock(spec=Session)
    s.no_autoflush = Session().no_autoflush
    s.scalars.side_effect = RuntimeError("fallo inesperado")
    with pytest.raises(RuntimeError):
        Repo(s).obtener(id_usuario="7", sistema=SistemaAcademico.CASES)


def test_migracion_aditiva_ciclo_y_datos_previos(cuentas_identidades):
    c = cuentas_identidades
    with c.sesiones.begin() as s:
        # Representa un caso legado todavía sin clave académica reconciliada.
        # Las identidades nuevas no pueden eliminarse mediante downgrade.
        caso = CasoModel(docente_creador_id=c.uuid, id_caso=null())
        espacio = EspacioAcademicoModel(nombre="Fixture previa de migración")
        s.add_all([caso, espacio])
        s.flush()
        version = VersionCasoModel(caso_id=caso.id, numero=1, nombre="Caso previo",
                                   desarrollo_situacional="d", contexto_historia="c",
                                   tiempo_estimado_min=30, estado=EstadoCaso.BORRADOR)
        s.add(version)
        s.flush()
        version.estado=EstadoCaso.PUBLICADO
        s.flush()
        ahora = datetime.now(timezone.utc)
        s.add(SesionProgramadaModel(espacio_academico_id=espacio.id, version_caso_id=version.id,
                                    docente_id=c.uuid, fecha_inicio=ahora,
                                    fecha_fin=ahora + timedelta(hours=1), tiempo_maximo_minutos=15))
    with c.engine.begin() as conexion:
        config = config_alembic(conexion)
        script = ScriptDirectory.from_config(config)
        assert script.get_heads() == ["20261106_consent_versions"]
        assert script.get_revision("20261102_steps_uuid").down_revision == "20261102_participation_history"
        assert script.get_revision("20261102_participation_history").down_revision == "20261102_assignment_bridge"
        assert script.get_revision("20261102_assignment_bridge").down_revision == "20261102_cases_history_guard"
        assert script.get_revision("20261102_cases_history_guard").down_revision == "20261101_er28_base_academica"
        assert script.get_revision("20261101_er28_base_academica").down_revision == REVISION
        assert compare_metadata(MigrationContext.configure(conexion), registrar_modelos_integrados()) == []
        tablas = [t for t in registrar_modelos_integrados().sorted_tables if t.name != "identidad_academica"]
        antes = {t.name: conexion.execute(select(t).order_by(*t.primary_key.columns)).all() for t in tablas}
        if conexion.dialect.name == "sqlite": retirar_ddl_resultados_sqlite(conexion)
        command.downgrade(config, ANTERIOR)
        assert "identidad_academica" not in inspect(conexion).get_table_names()
        # Volver a la cabeza actual: también restaura las tres tablas vacías
        # que el downgrade retiró; conservar la revisión histórica como padre.
        preparar_esquema_actual_aislado(conexion)
        despues = {t.name: conexion.execute(select(t).order_by(*t.primary_key.columns)).all() for t in tablas}
        assert despues == antes
        assert inspect(conexion).get_pk_constraint("identidad_academica")["constrained_columns"] == ["sistema", "id_academico"]
        assert not any(set(u["column_names"]) == {"id_usuario", "sistema"}
                       for u in inspect(conexion).get_unique_constraints("identidad_academica"))
