"""8B: servicios/Facade SQL reales; RF-22 y recorrido explícito SOLO fixtures.

Sin rutas públicas, URLs del proyecto ni correspondencias de identificadores.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta, timezone
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
from sqlalchemy.orm import sessionmaker

from app.db.models import registrar_modelos_integrados
from app.modules.cases.domain.entities.caso import Pregunta, OpcionRespuesta
from app.modules.cases.infrastructure.models import CasoModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.identity.infrastructure.models import RolORM
from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import AccesoDenegado, ConflictoActualizacion, ReglaPendiente
from app.modules.participation.domain.errors import ErrorDominioParticipacion, IntentoNoEditable
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.composition import crear_facade_8b
from app.modules.participation.infrastructure.models import PasoSimulacionModel, IntentoModel
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.identity.academic_identity_support import config_alembic, motor_postgresql_desechable
from tests.integration.test_participation_persistence import contexto, participacion, intento, FECHA
from tests.integration.test_cases_history import nuevo, publicar
from tests.integration.test_attempt_state import principal

HEAD="20261102_steps_uuid"
PARENT="20261102_participation_history"
T=PasoSimulacionModel.__table__


@pytest.fixture(scope="module")
def pg():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as s:
            command.upgrade(config_alembic(s),"head")
            s.execute(RolORM.__table__.insert(),[dict(id_rol=1,nombre="DOCENTE"),dict(id_rol=2,nombre="ESTUDIANTE")])
        yield engine


@pytest.fixture
def c(pg):
    c=contexto(pg)
    c.anterior=c.version
    v=nuevo(); v.caso_id=c.version.caso_id; v.numero=2; v.docente_creador_id=c.version.docente_creador_id
    criterio=v.rubrica.criterios[0].id
    v.escenarios[0].preguntas.append(Pregunta(2,"Otra pregunta",opciones=[
        OpcionRespuesta(1,"Una",True,"Explicación",valoraciones={criterio:5}),
        OpcionRespuesta(2,"Otra",False,"Explicación",valoraciones={criterio:0})]))
    with c.sesiones.begin() as s:
        modelo=CasoRepository(s)._mapear(v)
        edicion=modelo.versiones.pop()
        familia=s.get(CasoModel,v.caso_id)
        familia.versiones.append(edicion)
    c.version=publicar(c.sesiones,v)
    with c.sesiones.begin() as s:
        vieja=s.get(SesionProgramadaModel,c.sesion)
        nueva=SesionProgramadaModel(espacio_academico_id=vieja.espacio_academico_id,version_caso_id=v.id,
            docente_id=vieja.docente_id,fecha_inicio=vieja.fecha_inicio,fecha_fin=vieja.fecha_fin,
            tiempo_maximo_minutos=vieja.tiempo_maximo_minutos,estado="SIN_INICIAR")
        s.add(nueva); s.flush()
        vieja_a=s.get(AsignacionCasoModel,c.datos["id_asignacion"])
        asignacion=AsignacionCasoModel(id_grupo=vieja_a.id_grupo,id_caso=vieja_a.id_caso,
            sesion_programada_id=nueva.id,version_caso_id=v.id,apertura=vieja_a.apertura,cierre=vieja_a.cierre,
            fecha_limite_ingreso=vieja_a.fecha_limite_ingreso,tiempo_maximo_min=vieja_a.tiempo_maximo_min)
        s.add(asignacion);s.flush()
        conv=crear_convocatoria(s,sesion_id=nueva.id,estudiante_id=c.uuid)
        nueva.estado="EN_CURSO"
        c.datos=c.datos|dict(id_asignacion=asignacion.id_asignacion,convocatoria_id=conv.convocatoria_id)
        c.sesion=nueva.id
    c.pk=participacion(c);c.ik=intento(c,c.pk)
    c.usuario=principal(c)
    c.ahora=FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=1)
    return c


class EdicionFixture:
    """Autorización explícita solo del laboratorio, NO implementación productiva."""
    def __init__(self,c):self.c=c
    def autorizar(self,condiciones):
        if condiciones.sesion_id!=self.c.sesion or condiciones.estado_sesion!="EN_CURSO":
            raise AccesoDenegado("Edición no autorizada por la fixture.")
        assert condiciones.id_asignacion==self.c.datos["id_asignacion"]
        assert condiciones.id_grupo_estudiante==self.c.datos["id_grupo_estudiante"]


AUTORIZACION_FIXTURE=object()


def fachada(c,*,autorizacion=AUTORIZACION_FIXTURE,recorrido=None,usuario=None):
    return crear_facade_8b(usuario=c.usuario if usuario is None else usuario,id_intento=c.ik,
        autorizacion_edicion=EdicionFixture(c) if autorizacion is AUTORIZACION_FIXTURE else autorizacion,
        reloj=SimpleNamespace(ahora=lambda:c.ahora),fechas=FechasPersistencia(timezone.utc),
        crear_sesion=c.sesiones,recorrido=recorrido)


def guardar(c,*,modificar=False,q=0,o=0,**deps):
    # Autorización de recorrido explícita SOLO en pruebas. La pertenencia a una
    # versión nunca basta como permiso para la primera pregunta o una modificación.
    if "recorrido" not in deps:
        deps["recorrido"]=RutaFixture(c)
    preguntas=c.version.escenarios[0].preguntas
    metodo=fachada(c,**deps).modificar_decision if modificar else fachada(c,**deps).registrar_decision
    return metodo(id_estudiante=c.alumno,id_intento=c.ik,id_decision=preguntas[q].id,id_opcion=preguntas[q].opciones[o].id)


def progreso(c,**deps):
    return fachada(c,**deps).consultar_progreso(id_estudiante=c.alumno,id_intento=c.ik)


def filas(c):
    with c.engine.connect() as s:
        return s.execute(sa.select(T).where(T.c.id_intento==c.ik).order_by(T.c.numero_paso)).all()


def test_flujo_real_registro_modificacion_recuperacion_y_cierre(c):
    guardar(c)
    inicial=filas(c)
    p=progreso(c)
    assert p.respondidas==1 and p.selecciones[0].id_opcion==inicial[0].id_opcion
    assert p.decisiones_aplicables is None and p.pendientes is None and p.total_aplicable is None
    from app.modules.participation.api.mappers import mapear_progreso
    publico=mapear_progreso(p).model_dump(mode="json")
    assert publico["selecciones"][0]["id_opcion"]==str(inicial[0].id_opcion)
    assert publico["pendientes"] is None and "puntaje" not in str(publico)
    c.ahora+=timedelta(seconds=30)
    with pytest.raises(IntentoNoEditable):guardar(c,modificar=True,o=1)
    assert filas(c)[0].id_paso==inicial[0].id_paso
    assert filas(c)==inicial
    assert progreso(c).selecciones[0].id_opcion==c.version.escenarios[0].preguntas[0].opciones[0].id
    c.ahora+=timedelta(seconds=30)
    final=fachada(c).finalizar(id_estudiante=c.alumno,id_intento=c.ik)
    assert final.estado.value=="FINALIZADO"
    assert fachada(c).finalizar(id_estudiante=c.alumno,id_intento=c.ik)==final
    assert progreso(c).respondidas==1
    with pytest.raises(IntentoNoEditable):
        guardar(c,modificar=True,o=0)
    assert len(filas(c))==1


class RutaFixture:
    """Únicamente fixture: recorrido explícito de estas dos preguntas sintéticas."""
    def __init__(self,c):self.version=c.version.id;self.ids=tuple(q.id for q in c.version.escenarios[0].preguntas)
    def obtener(self,*,version_id,selecciones):
        assert version_id==self.version
        return RecorridoAplicable(self.ids,True)
    def validar_cambio(self,*,version_id,selecciones,propuesta):
        assert version_id==self.version


def test_progreso_de_dos_respuestas_con_contrato_de_recorrido_explicito(c):
    ruta=RutaFixture(c)
    guardar(c,recorrido=ruta)
    guardar(c,q=1,recorrido=ruta)
    p=progreso(c,recorrido=ruta)
    assert p.respondidas==2 and p.total_aplicable==2 and p.pendientes==()
    final=fachada(c,recorrido=ruta).finalizar(id_estudiante=c.alumno,id_intento=c.ik)
    assert progreso(c,recorrido=ruta).intento==final and len(filas(c))==2


def test_sin_politica_de_ruta_no_inventa_conservacion_de_otras_respuestas(c):
    guardar(c)
    with pytest.raises(ReglaPendiente,match="conservación"):
        guardar(c,q=1,recorrido=None)
    assert len(filas(c))==1


def test_sin_autorizacion_edicion_no_guarda_y_no_abre_inicio(c):
    with pytest.raises(ReglaPendiente):
        guardar(c,autorizacion=None)
    assert filas(c)==[]
    with pytest.raises(ReglaPendiente):
        fachada(c).iniciar_intento(id_estudiante=c.alumno,id_participacion=c.pk,id_consentimiento=c.consentimiento)


def test_edicion_no_reutiliza_ventana_de_ingreso_RF22(c):
    # La fixture autoriza editar el intento existente; el dominio aplica sus
    # treinta minutos históricos, sin inventar otra ventana de ingreso.
    c.ahora=FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=15)
    guardar(c)
    assert len(filas(c))==1 and progreso(c).respondidas==1


@pytest.mark.parametrize("dependencia",["edicion","cambio"])
def test_dependencia_no_puede_conceder_acceso_devolviendo_false(c,dependencia):
    if dependencia=="edicion":
        class Denegada:
            def autorizar(self,_):return False
        with pytest.raises(ReglaPendiente):guardar(c,autorizacion=Denegada())
        assert filas(c)==[]
    else:
        guardar(c)
        class Denegada(RutaFixture):
            def validar_cambio(self,**_):return False
        with pytest.raises(ReglaPendiente):guardar(c,q=1,recorrido=Denegada(c))
        assert len(filas(c))==1


@pytest.mark.parametrize("control",["matricula","convocatoria","cuenta","contexto"])
def test_validacion_de_escritura_relee_controles_reales(c,control):
    from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
    from app.modules.identity.infrastructure.models import UsuarioORM
    with c.engine.begin() as s:
        if control=="matricula":
            s.execute(sa.update(GrupoEstudianteORM).where(GrupoEstudianteORM.id_grupo_estudiante==c.datos["id_grupo_estudiante"]).values(activo=False))
        elif control=="convocatoria":
            s.execute(sa.update(ConvocatoriaModel).where(ConvocatoriaModel.id==c.datos["convocatoria_id"]).values(estado="RETIRADA"))
        elif control=="cuenta":
            s.execute(sa.update(UsuarioORM).where(UsuarioORM.id_usuario==c.alumno).values(activo=False))
        else:c.usuario=replace(c.usuario,id_convocatoria=str(uuid4()))
    with pytest.raises(AccesoDenegado):guardar(c)
    assert filas(c)==[]


def test_contrato_de_ruta_no_puede_devolver_otra_version(c):
    class RutaAjena(RutaFixture):
        def obtener(self,**_):return RecorridoAplicable((c.anterior.escenarios[0].preguntas[0].id,),True)
    with pytest.raises(ReglaPendiente):progreso(c,recorrido=RutaAjena(c))


def test_modificacion_que_necesita_invalidacion_no_borra_respuestas(c):
    ruta=RutaFixture(c)
    guardar(c,recorrido=ruta);guardar(c,q=1,recorrido=ruta)
    anteriores=filas(c)
    class NoAprobada(RutaFixture):
        def validar_cambio(self,**_):raise ReglaPendiente("Cambio de ruta no aprobado")
    with pytest.raises(IntentoNoEditable):guardar(c,modificar=True,o=1,recorrido=NoAprobada(c))
    assert filas(c)==anteriores


def test_HTTP_UUID_en_app_de_prueba_con_persistencia_real(c):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.modules.participation.api.router import router
    from app.modules.participation.api.dependencies import obtener_facade,obtener_estudiante_actual,EstudianteAutenticado
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[obtener_estudiante_actual]=lambda:EstudianteAutenticado(id_estudiante=c.alumno)
    app.dependency_overrides[obtener_facade]=lambda:fachada(c,recorrido=RutaFixture(c))
    q=c.version.escenarios[0].preguntas[0]
    with TestClient(app) as client:
        ruta=f"/api/v1/attempts/{c.ik}/decisions/{q.id}"
        r=client.post(ruta,json={"id_opcion":str(q.opciones[0].id)})
        assert r.status_code==201,r.text
        r=client.get(f"/api/v1/attempts/{c.ik}/progress")
        assert r.status_code==200 and r.json()["respondidas"]==1 and r.json()["total_aplicable"]==2
        assert client.post(f"/api/v1/attempts/{c.ik}/finish").status_code==200
        assert client.put(ruta,json={"id_opcion":str(q.opciones[1].id)}).status_code==409


def test_titularidad_y_parametro_student_no_son_suplantables(c):
    otro=contexto(c.engine)
    with pytest.raises(AccesoDenegado):
        progreso(c,usuario=principal(otro))
    with pytest.raises(AccesoDenegado):
        fachada(c).registrar_decision(id_estudiante=otro.alumno,id_intento=c.ik,
            id_decision=c.version.escenarios[0].preguntas[0].id,id_opcion=c.version.escenarios[0].preguntas[0].opciones[0].id)
    assert filas(c)==[]


@pytest.mark.parametrize("problema",["opcion_ajena","version_anterior","otra_familia","inexistente"])
def test_FK_y_version_exacta_rechazan_selecciones_cruzadas(c,problema):
    q=c.version.escenarios[0].preguntas[0]
    decision,opcion=q.id,q.opciones[0].id
    if problema=="opcion_ajena":opcion=c.version.escenarios[0].preguntas[1].opciones[0].id
    elif problema=="version_anterior":
        q=c.anterior.escenarios[0].preguntas[0];decision,opcion=q.id,q.opciones[0].id
    elif problema=="otra_familia":
        otro=contexto(c.engine);q=otro.version.escenarios[0].preguntas[0];decision,opcion=q.id,q.opciones[0].id
    else:opcion=uuid4()
    with pytest.raises(AccesoDenegado):
        fachada(c).registrar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=decision,id_opcion=opcion)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            s.execute(T.insert().values(id_intento=c.ik,id_decision=decision,id_opcion=opcion,numero_paso=1,
                registrado_en=c.ahora.replace(tzinfo=None),tiempo_segundos=60))
    assert filas(c)==[]


def test_respuestas_sql_no_modificables_tras_cierre(c):
    guardar(c)
    fachada(c).finalizar(id_estudiante=c.alumno,id_intento=c.ik)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            s.execute(T.update().where(T.c.id_intento==c.ik).values(reflexion_estudiante="alterado"))
    assert filas(c)[0].reflexion_estudiante is None


def test_vencimiento_persistido_conserva_respuestas_y_duracion(c):
    guardar(c)
    c.ahora+=timedelta(hours=1)
    with pytest.raises(IntentoNoEditable):
        guardar(c,modificar=True,o=1)
    p=progreso(c)
    assert p.intento.estado.value=="VENCIDO" and p.respondidas==1
    assert p.intento.fin==p.intento.vence_en
    assert p.intento.vence_en==FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=30,microseconds=1)


def test_rollback_despues_de_escribir_paso_no_deja_cambios(c,monkeypatch):
    original=RepositorioParticipacionSQLAlchemy.guardar_intento
    def fallar(self,*args,**kwargs):
        original(self,*args,**kwargs)
        raise RuntimeError("fallo controlado antes de commit")
    monkeypatch.setattr(RepositorioParticipacionSQLAlchemy,"guardar_intento",fallar)
    with pytest.raises(RuntimeError):guardar(c)
    assert filas(c)==[]


def test_actualizacion_esperada_rechaza_objeto_inmutable_obsoleto(c):
    with c.sesiones.begin() as s:
        viejo=RepositorioParticipacionSQLAlchemy(s,fechas=FechasPersistencia(timezone.utc)).obtener_intento(c.ik)
    guardar(c)
    with c.sesiones.begin() as s:
        with pytest.raises(ConflictoActualizacion):
            RepositorioParticipacionSQLAlchemy(s,fechas=FechasPersistencia(timezone.utc)).guardar_intento(viejo,esperado=viejo)
    assert len(filas(c))==1


def test_registros_concurrentes_no_pierden_actualizaciones(c):
    inicio=Barrier(2)
    def escritor(o):
        inicio.wait(timeout=5)
        try:guardar(c,o=o);return "commit"
        except ErrorDominioParticipacion:return "duplicada"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(escritor,[0,1]))==["commit","duplicada"]
    assert len(filas(c))==1


def test_cierre_y_modificacion_concurrentes_conservan_historia(c):
    guardar(c);inicio=Barrier(2)
    def cerrar():
        inicio.wait(timeout=5)
        fachada(c).finalizar(id_estudiante=c.alumno,id_intento=c.ik)
        return "cerrado"
    def modificar():
        inicio.wait(timeout=5)
        try:guardar(c,modificar=True,o=1);return "modificado"
        except IntentoNoEditable:return "rechazado"
    with ThreadPoolExecutor(max_workers=2) as pool:
        r=[pool.submit(cerrar),pool.submit(modificar)]
        assert r[0].result(timeout=10)=="cerrado"
        assert r[1].result(timeout=10)=="rechazado"
    assert progreso(c).intento.estado.value=="FINALIZADO" and len(filas(c))==1


def test_cierre_sql_antes_de_la_ultima_respuesta_es_rechazado(c):
    guardar(c)
    with pytest.raises(IntegrityError):
        with c.engine.begin() as s:
            s.execute(sa.update(IntentoModel).where(IntentoModel.id_intento==c.ik).values(estado="FINALIZADO",fin=FECHA))


def test_downgrade_con_respuestas_no_borra_historia(c):
    guardar(c)
    with c.engine.begin() as s:
        with pytest.raises(RuntimeError,match="respuestas historicas"):
            with s.begin_nested():command.downgrade(config_alembic(s),PARENT)
    assert len(filas(c))==1


def test_SQLite_DDL_FK_y_contrato_HTTP_UUID_sin_simular_locks():
    from app.modules.participation.api.schemas import SeleccionSolicitud, ProgresoRespuesta
    engine=sa.create_engine("sqlite://")
    try:
        with engine.begin() as s:
            s.exec_driver_sql("PRAGMA foreign_keys=ON")
            preparar_esquema_actual_aislado(s)
            assert len(registrar_modelos_integrados().tables)==40
            assert compare_metadata(MigrationContext.configure(s),registrar_modelos_integrados())==[]
            assert len(sa.inspect(s).get_foreign_keys("paso_simulacion"))==3
            opcion=uuid4()
            assert SeleccionSolicitud(id_opcion=str(opcion)).id_opcion==opcion
            retirar_ddl_resultados_sqlite(s)
            command.downgrade(config_alembic(s),PARENT)
            assert "paso_simulacion" not in sa.inspect(s).get_table_names()
    finally:engine.dispose()


def test_ciclo_PG_preserva_los_guards_previos():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as s:
            command.upgrade(config_alembic(s),PARENT)
            command.upgrade(config_alembic(s),HEAD)
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"))==31
            command.downgrade(config_alembic(s),PARENT)
            assert s.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"))==28
            command.upgrade(config_alembic(s),HEAD)
