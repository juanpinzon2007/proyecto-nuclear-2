
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4
from types import SimpleNamespace

import pytest

from app.modules.cases.infrastructure.models.caso import VersionCasoModel
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
)
from app.modules.scheduling.application.programar_sesion import (
    ErrorProgramacion,
    programar_sesion,
)


def datos_validos():
    inicio = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)

    return {
        "espacio_academico_id": uuid4(),
        "version_caso_id": uuid4(),
        "docente_id": uuid4(),
        "fecha_inicio": inicio,
        "fecha_fin": inicio + timedelta(hours=2),
        "tiempo_maximo_minutos": 30,
        "lugar": "Laboratorio 1",
    }


def crear_db_simulada(estado_version="PUBLICADO"):
    db = Mock()

    def buscar(modelo, identificador, **kwargs):
        if modelo is EspacioAcademicoModel:
            return SimpleNamespace(id=identificador)

        if modelo is VersionCasoModel:
            return SimpleNamespace(
                id=identificador,
                tiempo_estimado_min=45,
                estado=estado_version,
            )

        return None

    db.get.side_effect = buscar
    return db


def test_programacion_correcta():
    db = crear_db_simulada()

    sesion = programar_sesion(db, **datos_validos())

    assert isinstance(sesion, SesionProgramadaModel)
    assert sesion.estado == "SIN_INICIAR"
    assert sesion.tiempo_maximo_minutos == 30

    db.add.assert_called_once_with(sesion)
    db.flush.assert_called_once()
    db.get.assert_any_call(VersionCasoModel, sesion.version_caso_id, populate_existing=True, with_for_update=True)


def test_rechazar_fecha_final_anterior():
    db = crear_db_simulada()
    datos = datos_validos()

    datos["fecha_fin"] = datos["fecha_inicio"] - timedelta(hours=1)

    with pytest.raises(ErrorProgramacion):
        programar_sesion(db, **datos)

    db.add.assert_not_called()


def test_rechazar_fechas_sin_zona_horaria():
    db = crear_db_simulada()
    datos = datos_validos()

    datos["fecha_inicio"] = datetime(2026, 11, 10, 8, 0)

    with pytest.raises(ErrorProgramacion):
        programar_sesion(db, **datos)


def test_rechazar_tiempo_cero():
    db = crear_db_simulada()
    datos = datos_validos()

    datos["tiempo_maximo_minutos"] = 0

    with pytest.raises(ErrorProgramacion):
        programar_sesion(db, **datos)


def test_rechazar_tiempo_superior_al_caso():
    db = crear_db_simulada()
    datos = datos_validos()

    datos["tiempo_maximo_minutos"] = 60

    with pytest.raises(ErrorProgramacion):
        programar_sesion(db, **datos)


def test_rechazar_espacio_inexistente():
    db = crear_db_simulada()
    db.get.return_value = None
    db.get.side_effect = None

    with pytest.raises(
        ErrorProgramacion,
        match="espacio academico no existe",
    ):
        programar_sesion(db, **datos_validos())


def test_rechazar_version_inexistente():
    db = crear_db_simulada()

    def buscar(modelo, identificador, **kwargs):
        if modelo is EspacioAcademicoModel:
            return SimpleNamespace(id=identificador)
        return None

    db.get.side_effect = buscar

    with pytest.raises(
        ErrorProgramacion,
        match="version del caso no existe",
    ):
        programar_sesion(db, **datos_validos())


def test_rechazar_version_no_publicada_borrador():
    db = crear_db_simulada(estado_version="BORRADOR")

    with pytest.raises(
        ErrorProgramacion,
        match="Solo se pueden programar versiones publicadas del caso",
    ):
        programar_sesion(db, **datos_validos())


def test_rechazar_version_no_publicada_archivada():
    db = crear_db_simulada(estado_version="ARCHIVADO")

    with pytest.raises(
        ErrorProgramacion,
        match="Solo se pueden programar versiones publicadas del caso",
    ):
        programar_sesion(db, **datos_validos())


def test_version_sin_estado_no_se_considera_publicada():
    db = crear_db_simulada(estado_version=None)
    with pytest.raises(ErrorProgramacion, match='publicadas'):
        programar_sesion(db, **datos_validos())
    db.add.assert_not_called()
