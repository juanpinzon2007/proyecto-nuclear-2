"""Consultas con Session doble y compilación PostgreSQL; NO ejecuta una BD."""

from datetime import timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.participation.application.errors import ConflictoActualizacion, RecursoNoDisponible
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente
from app.modules.participation.infrastructure.queries import LecturasParticipacionSQLAlchemy, TablasLecturaParticipacion
from app.modules.participation.tests.fakes import INICIO


def tablas_prueba():
    # Solo descripción en memoria para compilar SQL; nunca se ejecuta DDL.
    metadata = MetaData()
    participacion = Table("participacion", metadata,
        Column("id_participacion", Integer, primary_key=True), Column("id_asignacion", Integer),
        Column("id_grupo_estudiante", Integer), Column("estado", String), Column("fecha_registro", DateTime),
    )
    intento = Table("intento", metadata,
        *(Column(n, Integer, primary_key=n == "id_intento") for n in
          ("id_intento", "id_participacion", "id_consentimiento", "id_permiso_extra", "numero_intento")),
        Column("estado", String), Column("inicio", DateTime), Column("fin", DateTime),
    )
    paso = Table("paso_simulacion", metadata,
        *(Column(n, Integer, primary_key=n == "id_paso") for n in
          ("id_paso", "id_intento", "id_decision", "id_opcion", "numero_paso", "tiempo_segundos")),
        Column("registrado_en", DateTime), Column("reflexion_estudiante", Text),
    )
    return TablasLecturaParticipacion(participacion, intento, paso)


class FilasFalsas:
    def __init__(self, filas):
        self.filas = filas

    def mappings(self):
        return self

    def one_or_none(self):
        return self.filas[0] if self.filas else None

    def all(self):
        return self.filas


PARTICIPACION = dict(id_participacion=20, id_asignacion=100, id_grupo_estudiante=200,
                     estado="REGISTRADA", fecha_registro=INICIO)
INTENTO = dict(id_intento=10, id_participacion=20, id_consentimiento=30, id_permiso_extra=None,
               numero_intento=1, estado="activo_fixture", inicio=INICIO, fin=None)
PASO = dict(id_paso=40, id_intento=10, id_decision=50, id_opcion=60, numero_paso=1,
            tiempo_segundos=12, registrado_en=INICIO + timedelta(seconds=12), reflexion_estudiante="análisis")


def lector(filas, **opciones):
    sesion = Mock(spec=Session)
    sesion.execute.side_effect = [FilasFalsas(f) for f in filas]
    argumentos = dict(fechas=FechasPersistencia(None), estados={"activo_fixture": EstadoIntento.EN_CURSO},
                      duracion_historica=lambda sesion, identificador: timedelta(minutes=10))
    argumentos.update(opciones)
    return sesion, LecturasParticipacionSQLAlchemy(sesion, tablas_prueba(), **argumentos)


def sql_ejecutado(sesion):
    return [str(llamada.args[0].compile(dialect=postgresql.dialect())) for llamada in sesion.execute.call_args_list]


def test_consulta_participacion_reconstruye_entidad_sin_escribir():
    sesion, repo = lector([[PARTICIPACION]])
    actual = repo.obtener_participacion(20)
    assert actual.id_asignacion == 100 and actual.id_grupo_estudiante == 200
    assert "FOR UPDATE" not in sql_ejecutado(sesion)[0]
    sesion.commit.assert_not_called()
    assert len(Base.metadata.tables) == 0


def test_lectura_participacion_no_necesita_inventar_estados_de_intento():
    sesion, repo = lector([[PARTICIPACION]], estados=None, duracion_historica=None)
    assert repo.obtener_participacion(20).id_participacion == 20


def test_consulta_intento_y_pasos_preserva_registros():
    sesion, repo = lector([[INTENTO], [PASO]])
    intento = repo.obtener_intento(10)
    assert intento.tiempo_maximo == timedelta(minutes=10)
    assert intento.pasos[0].id_opcion == 60
    assert intento.pasos[0].reflexion_estudiante == "análisis"
    assert "ORDER BY paso_simulacion.numero_paso" in sql_ejecutado(sesion)[1]
    assert len(sesion.execute.call_args_list) == 2
    sesion.commit.assert_not_called()


def test_no_reconstruye_duracion_desde_programacion_actual():
    sesion, repo = lector([[INTENTO]], duracion_historica=None)
    with pytest.raises(MapeoPersistenciaPendiente):
        repo.obtener_intento(10)
    assert sesion.execute.call_count == 1


def test_no_infiere_estado_persistido():
    sesion, repo = lector([[{**INTENTO, "estado": "DESCONOCIDO"}]])
    with pytest.raises(MapeoPersistenciaPendiente):
        repo.obtener_intento(10)


@pytest.mark.parametrize("operacion", ["participacion", "intento"])
def test_no_fabrica_recursos_ausentes(operacion):
    sesion, repo = lector([[]])
    with pytest.raises(RecursoNoDisponible):
        if operacion == "participacion":
            repo.obtener_participacion(20)
        else:
            repo.obtener_intento(10)


def test_compila_bloqueos_en_orden_padre_antes_de_hijo():
    sesion, repo = lector([[INTENTO], [PARTICIPACION], [INTENTO], [PASO]], bloquear=True)
    repo.obtener_intento(10)
    sentencias = sql_ejecutado(sesion)
    assert "FOR UPDATE" not in sentencias[0]
    assert "FROM participacion" in sentencias[1] and "FOR UPDATE" in sentencias[1]
    assert "FROM intento" in sentencias[2] and "FOR UPDATE" in sentencias[2]
    assert "FOR UPDATE" not in sentencias[3]


def test_no_acepta_intento_cambiado_mientras_bloqueaba():
    sesion, repo = lector([[INTENTO], [PARTICIPACION], []], bloquear=True)
    with pytest.raises(ConflictoActualizacion):
        repo.obtener_intento(10)


def test_listado_vacio_no_se_convierte_en_intento_o_ausencia():
    sesion, repo = lector([[]])
    assert repo.listar_intentos(20) == ()


def test_listado_bloquea_participacion_y_ordena_intentos():
    sesion, repo = lector([[PARTICIPACION], [INTENTO], [PASO]], bloquear=True)
    assert len(repo.listar_intentos(20)) == 1
    sentencias = sql_ejecutado(sesion)
    assert "FROM participacion" in sentencias[0] and "FOR UPDATE" in sentencias[0]
    assert "ORDER BY intento.id_intento FOR UPDATE" in sentencias[1]


def test_consultas_usan_parametros_no_interpolacion():
    sesion, repo = lector([[PARTICIPACION]])
    repo.obtener_participacion(20)
    compilado = sesion.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert list(compilado.params.values()) == [20]
    assert "%(id_participacion_1)s" in str(compilado)


def test_faltan_columnas_compartidas_no_se_inventan():
    tablas = tablas_prueba()
    tabla_incompleta = Table("participacion", MetaData(), Column("id_participacion", Integer))
    with pytest.raises(MapeoPersistenciaPendiente):
        TablasLecturaParticipacion(tabla_incompleta, tablas.intento, tablas.paso_simulacion)


def test_identificadores_compartidos_de_otro_tipo_se_rechazan():
    tablas = tablas_prueba()
    tabla = Table("participacion", MetaData(), Column("id_participacion", String),
                  Column("id_asignacion", Integer), Column("id_grupo_estudiante", Integer),
                  Column("estado", String), Column("fecha_registro", DateTime))
    with pytest.raises(MapeoPersistenciaPendiente):
        TablasLecturaParticipacion(tabla, tablas.intento, tablas.paso_simulacion)


def test_timestamp_naive_de_fila_exige_politica():
    sesion, repo = lector([[{**PARTICIPACION, "fecha_registro": INICIO.replace(tzinfo=None)}]])
    with pytest.raises(MapeoPersistenciaPendiente):
        repo.obtener_participacion(20)


def test_timestamp_naive_aprobado_expresamente_se_reconstruye():
    sesion, repo = lector([[{**PARTICIPACION, "fecha_registro": INICIO.replace(tzinfo=None)}]],
                         fechas=FechasPersistencia(timezone.utc))
    assert repo.obtener_participacion(20).fecha_registro == INICIO
