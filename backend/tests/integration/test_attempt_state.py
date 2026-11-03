"""8B parcial: cabecera persistida propia, sin simular pasos ni progreso.

JWT real de la biblioteca existente y SQL de laboratorio; no endpoint nuevo.
Las fixtures crean intentos, no se habilita ningún servicio productivo de inicio.
"""
from dataclasses import asdict, replace
from datetime import timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import event, update
from sqlalchemy.exc import SQLAlchemyError

from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models import VersionCasoModel
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.infrastructure.attempt_state import ConsultaEstadoIntentoSQLAlchemy
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import IntentoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.integration.test_participation_persistence import (
    datos, motor, laboratorio_pg, participacion, intento, contexto, FECHA,  # noqa: F401
)

TOKENS = TokensJWT("clave-solo-test-estado-persistido-"*2, "estado-lab", "estado-cliente")


def principal(c):
    token = TOKENS.emitir(str(c.alumno), str(c.datos["convocatoria_id"]))
    identidad = TOKENS.verificar(token)
    with c.sesiones() as s:
        cuenta = RepositorioUsuariosSQLAlchemy(s).obtener(identidad.id_usuario)
    return replace(cuenta, id_convocatoria=identidad.id_convocatoria)


@pytest.fixture
def registro(datos):
    pk = participacion(datos)
    return SimpleNamespace(**vars(datos), pk=pk, ik=intento(datos,pk), usuario=principal(datos))


def consultar(c, *, usuario=None, identificador=None, fechas=None, sesion=None):
    def lectura(s):
        return ConsultaEstadoIntentoSQLAlchemy(s, fechas=fechas if fechas is not None else FechasPersistencia(timezone.utc)).consultar(
            usuario=c.usuario if usuario is None else usuario, id_intento=c.ik if identificador is None else identificador)
    if sesion is not None:
        return lectura(sesion)
    with c.sesiones() as s:
        return lectura(s)


def test_recupera_estado_real_sin_inventar_selecciones_o_progreso(registro):
    c = registro; estado = consultar(c)
    assert estado.id_intento == c.ik and estado.id_participacion == c.pk
    assert estado.estado == EstadoIntento.EN_CURSO
    assert estado.vence_en == FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=30,microseconds=1)
    assert set(asdict(estado)) == {"id_intento","id_participacion","numero_intento","estado","inicio","fin","vence_en"}
    assert not hasattr(estado,"selecciones") and not hasattr(estado,"respondidas")


@pytest.mark.parametrize("estado", ["FINALIZADO", "VENCIDO"])
def test_lee_cierre_persistido_y_no_reabre(registro,estado):
    c = registro
    fin = FECHA+timedelta(minutes=10) if estado=="FINALIZADO" else FECHA+timedelta(minutes=30,microseconds=1)
    with c.engine.begin() as s:
        s.execute(update(IntentoModel).where(IntentoModel.id_intento==c.ik).values(estado=estado,fin=fin))
        s.execute(update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(estado="FINALIZADO"))
    resultado = consultar(c)
    assert resultado.estado == EstadoIntento(estado)
    assert resultado.fin == fin.replace(tzinfo=timezone.utc)
    assert consultar(c) == resultado
    # El cierre de arriba es fixture SQL: no se presenta como caso de uso de 8B.


def test_reprogramacion_y_archivo_no_cambian_duracion_ni_exigen_ultima_version(registro):
    c = registro; anterior = consultar(c)
    with c.engine.begin() as s:
        s.execute(update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(tiempo_maximo_minutos=99))
        s.execute(update(VersionCasoModel).where(VersionCasoModel.id==c.version.id).values(estado=EstadoCaso.ARCHIVADO))
    assert consultar(c) == anterior


@pytest.mark.parametrize("identificador", [2147483647, 0, -1, True, "1"])
def test_intento_inexistente_o_id_invalido_no_enumera(registro,identificador):
    with pytest.raises(AccesoDenegado,match="Intento no disponible"):
        consultar(registro,identificador=identificador)


def test_intento_de_otro_alumno_no_es_visible(registro):
    otro = contexto(registro.engine)
    with pytest.raises(AccesoDenegado,match="Intento no disponible"):
        consultar(registro,usuario=principal(otro))


@pytest.mark.parametrize("contexto_jwt", [None, "invalido", "otro"])
def test_contexto_de_convocatoria_obligatorio(registro,contexto_jwt):
    with pytest.raises(AccesoDenegado,match="Intento no disponible"):
        consultar(registro,usuario=replace(registro.usuario,id_convocatoria=str(uuid4()) if contexto_jwt=="otro" else contexto_jwt))


@pytest.mark.parametrize("problema", ["inactivo", "docente", "retirada"])
def test_relee_permisos_y_convocatoria_actuales(registro,problema):
    c = registro
    with c.engine.begin() as s:
        if problema=="retirada":
            s.execute(update(ConvocatoriaModel).where(ConvocatoriaModel.id==c.datos["convocatoria_id"]).values(estado="RETIRADA"))
        else:
            s.execute(update(UsuarioORM).where(UsuarioORM.id_usuario==c.alumno).values(**(dict(activo=False) if problema=="inactivo" else dict(id_rol=1))))
    with pytest.raises(AccesoDenegado):
        consultar(c)


def test_roles_del_llamador_no_sustituyen_el_servidor(registro):
    assert consultar(registro,usuario=replace(registro.usuario,roles=frozenset({Rol.DOCENTE}),activo=False)) == consultar(registro)


def test_ambiguedad_de_resolver_cierra_sin_fallback(registro,monkeypatch):
    # La BD impide crear esa corrupción sobre una participación histórica;
    # se simula únicamente el fallo del contrato externo, sin quitar guards.
    resolver = Mock(side_effect=IntegracionPendiente())
    monkeypatch.setattr(ResolverIdentidadAcademica,"resolver",resolver)
    with pytest.raises(ReglaPendiente):
        consultar(registro)
    assert resolver.call_count==1


def test_zona_no_configurada_no_asume_UTC(registro):
    with pytest.raises(ReglaPendiente):
        consultar(registro,fechas=FechasPersistencia(None))


def test_fallo_sql_no_expone_conexion_ni_datos_privados(registro):
    c=registro
    def fallar(conn,cursor,statement,params,context,many):
        if "FROM intento" in statement:
            raise SQLAlchemyError("secreto privado del servidor")
    event.listen(c.engine,"before_cursor_execute",fallar)
    try:
        with pytest.raises(ReglaPendiente) as error:
            consultar(c)
        assert "secreto" not in str(error.value) and "privado" not in str(error.value)
    finally:
        event.remove(c.engine,"before_cursor_execute",fallar)


def test_lectura_no_hace_flush_commit_ni_fabrica_vencimiento(registro):
    c=registro; sql=[]
    def registrar(conn,cursor,statement,params,context,many):
        sql.append(statement.lstrip().split()[0].upper())
    with c.sesiones() as s:
        pendiente=UsuarioORM(id_rol=2,nombre="No persistir",correo=f"{uuid4()}@fixture.test",clave_hash="sin-uso")
        s.add(pendiente)
        event.listen(c.engine,"before_cursor_execute",registrar)
        try:
            consultar(c,sesion=s)
            assert pendiente in s.new and pendiente.id_usuario is None
            assert not set(sql)&{"INSERT","UPDATE","DELETE","COMMIT"}
            assert s.in_transaction()
        finally:
            event.remove(c.engine,"before_cursor_execute",registrar)
        s.rollback()
