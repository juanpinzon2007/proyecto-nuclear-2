
"""Pruebas de validación de ingreso RF-22."""

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.modules.scheduling.application.validar_ingreso import (
    ErrorIngreso,
    validar_ingreso,
)
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    SesionProgramadaModel,
)


AHORA = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
CODIGO = "codigo-seguro-de-prueba"


def preparar():
    db = Mock()
    estudiante_id = uuid4()
    convocatoria_id = uuid4()
    sesion_id = uuid4()

    convocatoria = SimpleNamespace(
        id=convocatoria_id,
        sesion_id=sesion_id,
        estudiante_id=estudiante_id,
        estado="ACTIVA",
        codigo_hash=hashlib.sha256(
            CODIGO.encode()
        ).hexdigest(),
    )

    sesion = SimpleNamespace(
        id=sesion_id,
        estado="EN_CURSO",
        fecha_inicio=AHORA - timedelta(minutes=10),
        fecha_fin=AHORA + timedelta(hours=1),
    )

    def buscar(modelo, identificador):
        if modelo is ConvocatoriaModel:
            return convocatoria
        if modelo is SesionProgramadaModel:
            return sesion
        return None

    db.get.side_effect = buscar

    datos = {
        "convocatoria_id": convocatoria_id,
        "estudiante_id": estudiante_id,
        "codigo_acceso": CODIGO,
        "tolerancia_minutos": 15,
        "ahora": AHORA,
    }

    return db, convocatoria, sesion, datos


def test_ingreso_correcto():
    db, _, sesion, datos = preparar()
    assert validar_ingreso(db, **datos) is sesion


def test_codigo_incorrecto():
    db, _, _, datos = preparar()
    datos["codigo_acceso"] = "incorrecto"

    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)


def test_estudiante_no_autorizado():
    db, _, _, datos = preparar()
    datos["estudiante_id"] = uuid4()

    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)


def test_convocatoria_retirada():
    db, convocatoria, _, datos = preparar()
    convocatoria.estado = "RETIRADA"

    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)


def test_sesion_no_iniciada():
    db, _, sesion, datos = preparar()
    sesion.estado = "SIN_INICIAR"

    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)


def test_ingreso_fuera_de_tolerancia():
    db, _, _, datos = preparar()
    datos["tolerancia_minutos"] = 5

    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)


def test_tolerancia_invalida():
    db, _, _, datos = preparar()
    datos["tolerancia_minutos"] = -1

    with pytest.raises(ValueError):
        validar_ingreso(db, **datos)
