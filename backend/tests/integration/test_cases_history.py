"""Integridad histórica: PostgreSQL nuevo y desechable; nunca URL del equipo."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import threading
import time
from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.modules.cases.application.published_version import consultar_version_publicada
from app.modules.cases.domain.entities.caso import (
    VersionCaso, Escenario, Pregunta, OpcionRespuesta, Rubrica, CriterioRubrica, NivelRubrica,
)
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import CasoInvalidoError, ErrorPersistenciaCaso
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion
from app.modules.cases.infrastructure.models import VersionCasoModel, ValoracionOpcionModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.scheduling.application.programar_sesion import ErrorProgramacion, programar_sesion
from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic


@pytest.fixture(scope="module")
def sesiones_historia():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as c:
            command.upgrade(config_alembic(c), "head")
        yield sessionmaker(engine, expire_on_commit=False)


def nuevo():
    criterio = CriterioRubrica("Análisis", Decimal(100), niveles=[NivelRubrica("Alto", Decimal(5), "Descriptor")])
    opciones = [OpcionRespuesta(i, f"Opción {i}", i == 1, "Justificación",
                               valoraciones={criterio.id: Decimal(5 if i == 1 else 0)}) for i in (1,2)]
    return VersionCaso(
        "Caso de laboratorio", "Desarrollo", "Contexto", 45, uuid4(),
        escenarios=[Escenario(1,"Contexto de escena",preguntas=[Pregunta(1,"Enunciado",opciones=opciones)])],
        rubrica=Rubrica("Rúbrica", "regla-lab", criterios=[criterio]),
    )


@pytest.fixture
def borrador(sesiones_historia):
    version = nuevo()
    with sesiones_historia() as s:
        CasoRepository(s).guardar(version)
    return version


def leer(fabrica, v):
    with fabrica() as s:
        return CasoRepository(s).obtener_version(v.id, v.docente_creador_id)


def publicar(fabrica, v):
    v = leer(fabrica,v)
    v.publicar(construir_cadena_publicacion())
    with fabrica() as s:
        CasoRepository(s).actualizar_estado(v)
    return v


@pytest.mark.parametrize("estado", [EstadoCaso.PUBLICADO, EstadoCaso.ARCHIVADO])
def test_repositorio_rechaza_editar_estado_persistido_aunque_cliente_diga_borrador(sesiones_historia,borrador,estado):
    original = publicar(sesiones_historia,borrador)
    if estado == EstadoCaso.ARCHIVADO:
        original.archivar()
        with sesiones_historia() as s:
            CasoRepository(s).actualizar_estado(original)
    falso = replace(original,estado=EstadoCaso.BORRADOR,nombre="Intento de sobrescritura")
    with sesiones_historia() as s, pytest.raises(CasoInvalidoError):
        CasoRepository(s).reemplazar(falso)
    assert leer(sesiones_historia,borrador) == original


@pytest.mark.parametrize("campo", ["caso_id","docente_creador_id","numero"])
def test_repositorio_rechaza_identidad_familiar_o_propietario_alterados(sesiones_historia,borrador,campo):
    falso = replace(borrador,**{campo:99 if campo == "numero" else uuid4()})
    with sesiones_historia() as s, pytest.raises(ErrorPersistenciaCaso):
        CasoRepository(s).reemplazar(falso)
    assert leer(sesiones_historia,borrador) == borrador


def test_reemplazo_de_borrador_publicacion_y_archivo_conservan_grafo(sesiones_historia,borrador):
    borrador.nombre = "Edición permitida"
    with sesiones_historia() as s:
        CasoRepository(s).reemplazar(borrador)
    original = publicar(sesiones_historia,borrador)
    original.archivar()
    with sesiones_historia() as s:
        CasoRepository(s).actualizar_estado(original)
    assert leer(sesiones_historia,borrador) == original
    original.estado = EstadoCaso.BORRADOR
    with sesiones_historia() as s, pytest.raises(ErrorPersistenciaCaso):
        CasoRepository(s).actualizar_estado(original)
    assert leer(sesiones_historia,borrador).estado == EstadoCaso.ARCHIVADO


@pytest.mark.parametrize("cambio", ["enunciado","puntaje","descriptor","version_regla"])
def test_publicacion_rechaza_contenido_obsoleto_incluso_con_identity_map_cargado(sesiones_historia,borrador,cambio):
    with sesiones_historia() as s:
        cache = s.get(VersionCasoModel,borrador.id)
        _ = cache.escenarios[0].preguntas[0].opciones
        obsoleto = CasoRepository(s).obtener_version(borrador.id,borrador.docente_creador_id)
        actual = leer(sesiones_historia,borrador)
        if cambio == "enunciado":
            actual.escenarios[0].preguntas[0].enunciado = "Texto posterior"
        elif cambio == "puntaje":
            actual.escenarios[0].preguntas[0].opciones[0].valoraciones[actual.rubrica.criterios[0].id] = Decimal(4)
        elif cambio == "descriptor":
            actual.rubrica.criterios[0].niveles[0].descriptor = "Descriptor posterior"
        else:
            actual.rubrica.version_regla = "regla-posterior"
        with sesiones_historia() as otro:
            CasoRepository(otro).reemplazar(actual)
        obsoleto.publicar(construir_cadena_publicacion())
        with pytest.raises(ErrorPersistenciaCaso,match="contenido cambió"):
            CasoRepository(s).actualizar_estado(obsoleto)
    assert leer(sesiones_historia,borrador) == actual


def test_repositorio_no_publica_sin_cadena_valida(sesiones_historia,borrador):
    borrador.rubrica = None
    for opcion in borrador.escenarios[0].preguntas[0].opciones:
        opcion.valoraciones.clear()  # Borrador sin rúbrica, sin FK huérfanas.
    with sesiones_historia() as s:
        CasoRepository(s).reemplazar(borrador)
    solicitado = replace(borrador,estado=EstadoCaso.PUBLICADO)
    with sesiones_historia() as s, pytest.raises(CasoInvalidoError):
        CasoRepository(s).actualizar_estado(solicitado)
    assert leer(sesiones_historia,borrador).estado == EstadoCaso.BORRADOR


def test_persistencia_rechaza_valoraciones_de_rubrica_ajena_incluso_borrador(sesiones_historia,borrador):
    original=leer(sesiones_historia,borrador)
    ajeno = nuevo()
    with sesiones_historia() as s:
        CasoRepository(s).guardar(ajeno)
    opcion = borrador.escenarios[0].preguntas[0].opciones[0]
    opcion.valoraciones = {ajeno.rubrica.criterios[0].id:Decimal(5)}
    with sesiones_historia() as s, pytest.raises(ErrorPersistenciaCaso) as error:
        CasoRepository(s).reemplazar(borrador)
    assert error.value.__cause__.orig.sqlstate == "23514"
    assert leer(sesiones_historia,borrador)==original


def test_bloqueo_serializa_publicar_antes_de_editor_concurrente(sesiones_historia,borrador):
    listo = threading.Event()
    pid, errores = [], []

    def editar():
        try:
            with sesiones_historia() as s:
                pid.append(s.scalar(text("SELECT pg_backend_pid()")))
                listo.set()
                CasoRepository(s).reemplazar(replace(borrador,nombre="Edición tardía"))
        except Exception as e:
            errores.append(e)

    with sesiones_historia() as s:
        s.get(VersionCasoModel,borrador.id,with_for_update=True)
        hilo = threading.Thread(target=editar)
        hilo.start()
        try:
            assert listo.wait(2)
            limite = time.monotonic()+1
            bloqueado = False
            while time.monotonic()<limite:
                if s.scalar(text("SELECT cardinality(pg_blocking_pids(:pid))"),{"pid":pid[0]}):
                    bloqueado = True
                    break
                time.sleep(.01)
            assert bloqueado, "El editor debe esperar el bloqueo real de PostgreSQL"
            publicado = replace(borrador,estado=EstadoCaso.PUBLICADO)
            CasoRepository(s).actualizar_estado(publicado)
        finally:
            s.rollback()
            hilo.join(5)
        assert not hilo.is_alive()
    assert len(errores)==1 and isinstance(errores[0],CasoInvalidoError)
    assert leer(sesiones_historia,borrador).nombre == borrador.nombre


def test_programacion_relee_archivo_concurrente_y_conserva_UUID_exacto(sesiones_historia,borrador):
    original = publicar(sesiones_historia,borrador)
    with sesiones_historia.begin() as s:
        espacio = EspacioAcademicoModel(nombre="Laboratorio")
        s.add(espacio);s.flush()
        espacio_id = espacio.id
    with sesiones_historia() as s:
        cache = s.get(VersionCasoModel,borrador.id)
        original.archivar()
        with sesiones_historia() as otro:
            CasoRepository(otro).actualizar_estado(original)
        inicio = datetime(2030,1,1,tzinfo=timezone.utc)
        with pytest.raises(ErrorProgramacion,match="publicadas"):
            programar_sesion(s,espacio_academico_id=espacio_id,version_caso_id=cache.id,
                             docente_id=borrador.docente_creador_id,fecha_inicio=inicio,
                             fecha_fin=inicio+timedelta(hours=1),tiempo_maximo_minutos=20)


def test_SQL_directo_y_criterio_ajeno_son_rechazados_por_base(sesiones_historia,borrador):
    publicado = publicar(sesiones_historia,borrador)
    ajeno = nuevo()
    with sesiones_historia() as s:
        CasoRepository(s).guardar(ajeno)
    with sesiones_historia() as s, pytest.raises(IntegrityError) as error:
        s.execute(update(VersionCasoModel).where(VersionCasoModel.id==publicado.id).values(nombre="SQL directo"))
    assert error.value.orig.sqlstate=="23514"
    opcion = publicado.escenarios[0].preguntas[0].opciones[0]
    with sesiones_historia() as s, pytest.raises(IntegrityError) as error:
        s.execute(update(ValoracionOpcionModel).where(ValoracionOpcionModel.opcion_id==opcion.id)
                  .values(criterio_id=ajeno.rubrica.criterios[0].id))
    assert error.value.orig.sqlstate=="23514"
    assert leer(sesiones_historia,borrador) == publicado
