"""BD2-07: esquema y SQL reales; no simula autorización académica de inicio.

Datos sintéticos explícitos en SQLite aislado/PostgreSQL recién creado. Las
pruebas de guards y carreras solo se parametrizan en PostgreSQL, sin simularlos.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
import itertools
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from alembic import command
from tests.identity.academic_identity_support import preparar_esquema_actual_aislado, retirar_ddl_resultados_sqlite
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.pool import StaticPool

from app.db.models import registrar_modelos_integrados
from app.modules.cases.infrastructure.models import CasoModel
from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM, GrupoEstudianteORM, GrupoAcademicoORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Vinculos
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.identity.infrastructure.models import RolORM, UsuarioORM
from app.modules.participation.infrastructure.models import ParticipacionModel, IntentoModel
from app.modules.participation.infrastructure.queries import consultar_duracion_historica
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
from tests.identity.academic_identity_support import config_alembic, motor_postgresql_desechable
from tests.integration.test_assignment_bridge import preparar

HEAD = "20261102_participation_history"
PARENT = "20261102_assignment_bridge"
P, I = ParticipacionModel.__table__, IntentoModel.__table__
FECHA = datetime(2026, 11, 2, 12)
CLAVES = itertools.count(10001)


def migrar(engine):
    with engine.begin() as c:
        preparar_esquema_actual_aislado(c)
        c.execute(RolORM.__table__.insert(), [dict(id_rol=1,nombre="DOCENTE"), dict(id_rol=2,nombre="ESTUDIANTE")])


@pytest.fixture(scope="module")
def laboratorio_pg():
    with motor_postgresql_desechable() as engine:
        migrar(engine)
        yield engine


@pytest.fixture(scope="module", params=["sqlite", "postgresql"])
def motor(request):
    if request.param == "postgresql":
        yield request.getfixturevalue("laboratorio_pg")
        return
    engine = sa.create_engine("sqlite://", poolclass=StaticPool)
    @sa.event.listens_for(engine, "connect")
    def fk(dbapi, _):
        dbapi.execute("PRAGMA foreign_keys=ON")
    try:
        migrar(engine)
        yield engine
    finally:
        engine.dispose()


def contexto(engine):
    fabrica, v, valores = preparar(engine)
    uuid = uuid4()
    with fabrica.begin() as s:
        if engine.dialect.name == "sqlite":
            caso = s.get(CasoModel, v.caso_id)
            caso.id_caso = next(CLAVES)
            valores["id_caso"] = caso.id_caso
        alumno = UsuarioORM(id_rol=2,nombre="Alumno de laboratorio",correo=f"{uuid}@fixture.test",clave_hash="no-utilizable")
        s.add(alumno); s.flush()
        Vinculos(s).agregar_verificado(VinculoAcademico(str(alumno.id_usuario),SistemaAcademico.SCHEDULING,uuid))
        matricula = GrupoEstudianteORM(id_grupo=valores["id_grupo"],id_estudiante=alumno.id_usuario,fecha_ingreso=FECHA)
        asignacion = AsignacionCasoModel(**valores)
        consentimiento = ConsentimientoORM(id_estudiante=alumno.id_usuario,version_texto="sintetico",fecha_aceptacion=FECHA)
        s.add_all([matricula,asignacion,consentimiento]); s.flush()
        convocada = crear_convocatoria(s,sesion_id=valores["sesion_programada_id"],estudiante_id=uuid)
        datos = dict(id_asignacion=asignacion.id_asignacion,id_grupo_estudiante=matricula.id_grupo_estudiante,
                     convocatoria_id=convocada.convocatoria_id,fecha_registro=FECHA)
        alumno_id, consentimiento_id = alumno.id_usuario, consentimiento.id_consentimiento
        docente_id = s.get(GrupoAcademicoORM,valores["id_grupo"]).id_profesor
    return SimpleNamespace(engine=engine,sesiones=fabrica,version=v,datos=datos,alumno=alumno_id,uuid=uuid,
                           consentimiento=consentimiento_id,sesion=valores["sesion_programada_id"],docente=docente_id)


@pytest.fixture
def datos(motor):
    return contexto(motor)


@pytest.fixture
def datos_pg(laboratorio_pg):
    return contexto(laboratorio_pg)


def participacion(c, **cambios):
    with c.engine.begin() as s:
        return s.scalar(P.insert().values(**(c.datos|cambios)).returning(P.c.id_participacion))


def valores_intento(c, pk, **cambios):
    return dict(id_participacion=pk,id_consentimiento=c.consentimiento,numero_intento=1,
                estado="EN_CURSO",inicio=FECHA,fin=None,duracion_concedida_segundos=Decimal("1800.000001")) | cambios


def intento(c, pk, **cambios):
    with c.engine.begin() as s:
        return s.scalar(I.insert().values(**valores_intento(c,pk,**cambios)).returning(I.c.id_intento))


def test_metadata_reflejado_y_PK_FK_duracion_obligatoria(datos):
    with datos.engine.connect() as s:
        assert len(registrar_modelos_integrados().tables) == 39
        assert compare_metadata(MigrationContext.configure(s),registrar_modelos_integrados()) == []
        assert len(sa.inspect(s).get_foreign_keys("participacion")) == 4
        assert len(sa.inspect(s).get_foreign_keys("intento")) == 3
        assert not I.c.duracion_concedida_segundos.nullable
        assert I.c.duracion_concedida_segundos.type.scale == 6


def test_participacion_ORM_y_unicidad_por_convocatoria(datos):
    c = datos
    with c.sesiones.begin() as s:
        fila = ParticipacionModel(**c.datos)
        s.add(fila); s.flush()
        assert fila.estado == "pendiente" and type(fila.id_participacion) is int
    with pytest.raises(IntegrityError):
        participacion(c)


@pytest.mark.parametrize("campo", ["id_asignacion", "id_grupo_estudiante", "convocatoria_id"])
def test_FK_participacion_inexistente(datos,campo):
    with pytest.raises(IntegrityError):
        participacion(datos,**{campo:uuid4() if campo=="convocatoria_id" else 2147483647})


@pytest.mark.parametrize("campo", ["id_participacion", "id_consentimiento", "id_permiso_extra"])
def test_FK_intento_inexistente(datos,campo):
    pk = participacion(datos)
    with pytest.raises(IntegrityError):
        intento(datos,pk,**{campo:2147483647})


@pytest.mark.parametrize("cambio", [dict(estado="INCOMPLETA"),dict(duracion_concedida_segundos=0),
    dict(numero_intento=0),dict(fin=FECHA),dict(estado="FINALIZADO"),dict(duracion_concedida_segundos=None)])
def test_CHECK_no_inventa_estados_y_rechaza_datos_invalidos(datos,cambio):
    pk = participacion(datos)
    with pytest.raises(IntegrityError):
        intento(datos,pk,**cambio)


def test_un_activo_y_varios_historicos_sin_cambiar_participacion(datos):
    c = datos; pk = participacion(c)
    primero = intento(c,pk)
    with pytest.raises(IntegrityError):
        intento(c,pk,numero_intento=2)
    with c.engine.begin() as s:
        s.execute(I.update().where(I.c.id_intento==primero).values(estado="FINALIZADO",fin=FECHA+timedelta(minutes=10)))
        permiso = s.scalar(PermisoIntentoExtraORM.__table__.insert().values(id_participacion=pk,id_profesor=c.docente,
            cantidad_autorizada=1,justificacion="Solo fixture, no autorización real",fecha_autorizacion=FECHA).returning(PermisoIntentoExtraORM.id_permiso_extra))
    intento(c,pk,numero_intento=2,id_permiso_extra=permiso)
    with c.sesiones() as s:
        assert consultar_duracion_historica(s,primero)==timedelta(minutes=30,microseconds=1)
    with c.engine.connect() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(I).where(I.c.id_participacion==pk)) == 2
    with pytest.raises(IntegrityError):
        intento(c,pk,numero_intento=1,estado="FINALIZADO",fin=FECHA+timedelta(minutes=1))


def test_rollback_no_deja_intento_parcial(datos):
    pk = participacion(datos)
    with datos.engine.connect() as s:
        tx = s.begin()
        s.execute(I.insert().values(**valores_intento(datos,pk)))
        tx.rollback()
        assert s.scalar(sa.select(sa.func.count()).select_from(I).where(I.c.id_participacion==pk)) == 0


@pytest.mark.parametrize("parte", ["convocatoria", "matricula", "asignacion"])
def test_referencia_ajena_rechazada_PostgreSQL(datos_pg, parte):
    c = datos_pg; ajena = contexto(c.engine)
    campo = {"convocatoria":"convocatoria_id","matricula":"id_grupo_estudiante","asignacion":"id_asignacion"}[parte]
    with pytest.raises(IntegrityError):
        participacion(c,**{campo:ajena.datos[campo]})


def test_consentimiento_y_permiso_ajenos_rechazados(datos_pg):
    c = datos_pg; pk = participacion(c); otro = contexto(c.engine); otro_pk = participacion(otro)
    with pytest.raises(IntegrityError):
        intento(c,pk,id_consentimiento=otro.consentimiento)
    with c.engine.begin() as s:
        permiso = s.scalar(PermisoIntentoExtraORM.__table__.insert().values(id_participacion=otro_pk,id_profesor=otro.docente,
            cantidad_autorizada=1,justificacion="Fixture",fecha_autorizacion=FECHA).returning(PermisoIntentoExtraORM.id_permiso_extra))
    with pytest.raises(IntegrityError):
        intento(c,pk,id_permiso_extra=permiso)


@pytest.mark.parametrize("objetivo", ["participacion", "convocatoria", "matricula", "identidad", "consentimiento", "intento", "borrar", "truncar"])
def test_contexto_e_identidades_historicas_protegidos(datos_pg,objetivo):
    c = datos_pg; pk = participacion(c); ik = intento(c,pk)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            if objetivo=="participacion":
                s.execute(P.update().where(P.c.id_participacion==pk).values(convocatoria_id=uuid4()))
            elif objetivo=="convocatoria":
                s.execute(sa.update(ConvocatoriaModel).where(ConvocatoriaModel.id==c.datos["convocatoria_id"]).values(estudiante_id=uuid4()))
            elif objetivo=="matricula":
                s.execute(sa.update(GrupoEstudianteORM).where(GrupoEstudianteORM.id_grupo_estudiante==c.datos["id_grupo_estudiante"]).values(id_estudiante=2147483647))
            elif objetivo=="identidad":
                s.execute(IdentidadAcademicaORM.__table__.insert().values(id_usuario=c.alumno,sistema="SCHEDULING",id_academico=uuid4()))
            elif objetivo=="consentimiento":
                s.execute(sa.update(ConsentimientoORM).where(ConsentimientoORM.id_consentimiento==c.consentimiento).values(version_texto="sobrescrito"))
            elif objetivo=="intento":
                s.execute(I.update().where(I.c.id_intento==ik).values(duracion_concedida_segundos=9999))
            elif objetivo=="borrar":
                s.execute(I.delete().where(I.c.id_intento==ik))
            else:
                # Incluir la nueva dependencia permite llegar al guard histórico,
                # en vez de detenerse antes por la prohibición FK de TRUNCATE.
                s.exec_driver_sql("TRUNCATE intento, paso_simulacion, resultado_intento, resultado_criterio, resultado_calculo_preguntas, resultado_pregunta, resultado_criterio_exacto, resultado_participacion")


def test_duracion_microsegundos_y_vencimiento_no_cambian_al_reprogramar(datos_pg):
    c = datos_pg; pk = participacion(c); ik = intento(c,pk)
    with c.engine.begin() as s:
        antes = s.scalar(sa.text("SELECT inicio+duracion_concedida_segundos*interval '1 second' FROM intento WHERE id_intento=:i"),dict(i=ik))
        assert antes == FECHA+timedelta(minutes=30,microseconds=1)
        s.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(tiempo_maximo_minutos=99))
        assert s.scalar(sa.text("SELECT inicio+duracion_concedida_segundos*interval '1 second' FROM intento WHERE id_intento=:i"),dict(i=ik)) == antes
        s.execute(I.update().where(I.c.id_intento==ik).values(estado="VENCIDO",fin=antes))
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            s.execute(I.update().where(I.c.id_intento==ik).values(estado="EN_CURSO",fin=None))


def test_cierre_conserva_precision_sin_conversion_float(datos_pg):
    # Frontera técnica, NO duración académica propuesta: no se debe perder
    # el microsegundo de un timedelta representable por datetime y NUMERIC.
    c=datos_pg; pk=participacion(c)
    limite=FECHA+timedelta(days=100000,microseconds=1)
    intento(c,pk,estado="VENCIDO",fin=limite,duracion_concedida_segundos=Decimal("8640000000.000001"))


@pytest.mark.parametrize("estado,fin", [("FINALIZADO",FECHA+timedelta(hours=1)),("VENCIDO",FECHA+timedelta(minutes=1))])
def test_limites_historicos_de_cierre(datos_pg,estado,fin):
    pk = participacion(datos_pg)
    with pytest.raises(IntegrityError):
        intento(datos_pg,pk,estado=estado,fin=fin)


def carrera(c, llamadas, *, aislamiento="READ COMMITTED"):
    inicio = Barrier(2)
    def escritor(llamada):
        try:
            with c.engine.connect().execution_options(isolation_level=aislamiento) as s:
                with s.begin():
                    s.exec_driver_sql("SET LOCAL statement_timeout='5s'")
                    inicio.wait(timeout=5)
                    llamada(s)
            return "commit"
        except DBAPIError as error:
            return error.orig.sqlstate
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(escritor,llamadas))


def test_dos_altas_por_convocatoria_un_solo_ganador(datos_pg):
    c=datos_pg
    resultados=carrera(c,[lambda s:s.execute(P.insert().values(**c.datos))]*2)
    assert sorted(resultados)==["23505","commit"]


@pytest.mark.parametrize("aislamiento", ["READ COMMITTED", "SERIALIZABLE"])
def test_dos_intentos_activos_concurrentes(datos_pg,aislamiento):
    c=datos_pg; pk=participacion(c)
    resultados=carrera(c,[lambda s:s.execute(I.insert().values(**valores_intento(c,pk))),
        lambda s:s.execute(I.insert().values(**valores_intento(c,pk,numero_intento=2)))],aislamiento=aislamiento)
    assert resultados.count("commit")==1
    assert set(resultados)<= {"commit","23505","40001"}


@pytest.mark.parametrize("padre", ["convocatoria", "identidad"])
def test_carrera_contexto_con_padre_no_deja_asociacion_incorrecta(datos_pg,padre):
    c=datos_pg
    def mutar(s):
        if padre=="convocatoria":
            s.execute(sa.update(ConvocatoriaModel).where(ConvocatoriaModel.id==c.datos["convocatoria_id"]).values(estudiante_id=uuid4()))
        else:
            s.execute(IdentidadAcademicaORM.__table__.insert().values(id_usuario=c.alumno,sistema="SCHEDULING",id_academico=uuid4()))
    resultados=carrera(c,[lambda s:s.execute(P.insert().values(**c.datos)),mutar])
    assert resultados.count("commit")==1 and set(resultados)<= {"commit","23514"}


def test_repeatable_read_cierra_ante_snapshot_antiguo(datos_pg):
    c=datos_pg
    with pytest.raises(DBAPIError) as error:
        with c.engine.connect().execution_options(isolation_level="REPEATABLE READ") as s:
            with s.begin():
                s.execute(P.insert().values(**c.datos))
    assert error.value.orig.sqlstate=="40001"


def test_downgrade_rechaza_datos_historicos(datos_pg):
    pk=participacion(datos_pg); intento(datos_pg,pk)
    with datos_pg.engine.begin() as s:
        with pytest.raises(RuntimeError,match="datos historicos"):
            with s.begin_nested():
                command.downgrade(config_alembic(s),PARENT)
        assert s.scalar(sa.text("SELECT version_num FROM alembic_version"))=="20261108_academic_publication"


def test_upgrade_downgrade_vacio_preserva_protecciones_anteriores():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            antes=set(sa.inspect(s).get_table_names())
            command.upgrade(config_alembic(s),HEAD)
            assert set(sa.inspect(s).get_table_names())==antes|{"participacion","intento","permiso_intento_extra"}
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"))==28
            command.downgrade(config_alembic(s),PARENT)
            assert set(sa.inspect(s).get_table_names())==antes
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"))==19
            command.upgrade(config_alembic(s),HEAD)
