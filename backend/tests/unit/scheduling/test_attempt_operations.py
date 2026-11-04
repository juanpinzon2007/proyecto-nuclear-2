"""Límites temporales para responder un intento existente, sin Session real."""

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.scheduling.application.attempt_operations import (
    CondicionesOperacionNoDisponibles, OperacionSesionDenegada, autorizar_respuesta_sesion,
)

INICIO = datetime(2026, 11, 3, 14, tzinfo=timezone.utc)
FIN = INICIO + timedelta(hours=1)


def autorizar(**cambios):
    datos = dict(estado="EN_CURSO", inicio=INICIO, fin=FIN, ahora=INICIO, operacion="RESPONDER")
    autorizar_respuesta_sesion(**(datos | cambios))


@pytest.mark.parametrize("instante", [FIN - timedelta(microseconds=1)])
def test_permite_ultimo_microsegundo(instante):
    autorizar(ahora=instante)


@pytest.mark.parametrize("instante", [INICIO - timedelta(microseconds=1), FIN + timedelta(microseconds=1)])
def test_rechaza_un_microsegundo_fuera_del_intervalo(instante):
    with pytest.raises(OperacionSesionDenegada):
        autorizar(ahora=instante)


@pytest.mark.parametrize("estado", ["SIN_INICIAR", "FINALIZADO"])
def test_estado_no_habilitado_impide_responder(estado):
    with pytest.raises(OperacionSesionDenegada):
        autorizar(estado=estado)


@pytest.mark.parametrize("operacion", ["MODIFICAR", "INICIAR", "", None])
def test_no_extiende_permiso_a_otras_operaciones(operacion):
    with pytest.raises(OperacionSesionDenegada):
        autorizar(operacion=operacion)


@pytest.mark.parametrize("cambios", [
    {"fin": INICIO - timedelta(seconds=1)},
    {"fin": FIN.replace(tzinfo=None)},
    {"ahora": INICIO.replace(tzinfo=None)},
])
def test_datos_incoherentes_no_producen_autorizacion(cambios):
    with pytest.raises(CondicionesOperacionNoDisponibles):
        autorizar(**cambios)


def test_offsets_equivalentes_autorizan_el_mismo_instante():
    bogota = timezone(timedelta(hours=-5))
    autorizar(inicio=INICIO.astimezone(bogota), fin=FIN.astimezone(bogota), ahora=INICIO)
