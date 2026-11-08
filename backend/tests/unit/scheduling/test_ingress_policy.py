"""Mecánica de ventanas SINTÉTICAS; ninguna es una política académica aprobada."""

from datetime import timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.modules.scheduling.application.validar_ingreso import ErrorIngreso, validar_ingreso
from app.modules.scheduling.domain.ingress_policy import (
    PoliticaIngresoNoConfigurada, PoliticaTemporalNoDisponible, VentanaIngreso,
)
from tests.unit.scheduling.test_validar_ingreso import preparar, AHORA


@pytest.mark.parametrize("estado", ["SIN_INICIAR", "FINALIZADO", "DESCONOCIDO"])
def test_estado_no_habilitado_rechaza_antes_de_politica(estado):
    db, _, sesion, datos = preparar()
    sesion.estado = estado
    politica = Mock()
    datos["politica"] = politica
    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)
    politica.obtener_ventana.assert_not_called()


def test_no_existe_tolerancia_academica_por_defecto():
    db, _, _, datos = preparar()
    datos["politica"] = PoliticaIngresoNoConfigurada()
    with pytest.raises(PoliticaTemporalNoDisponible):
        validar_ingreso(db, **datos)


@pytest.mark.parametrize("objetivo", ["convocatoria", "sesion"])
def test_recurso_inexistente_no_permite_ingreso(objetivo):
    db, _, _, datos = preparar()
    original = db.get.side_effect
    db.get.side_effect = lambda modelo, identificador: None if (
        modelo.__tablename__ == ("convocatoria" if objetivo == "convocatoria" else "sesion_programada")
    ) else original(modelo, identificador)
    with pytest.raises(ErrorIngreso):
        validar_ingreso(db, **datos)


@pytest.mark.parametrize("borde", ["apertura", "cierre"])
@pytest.mark.parametrize("incluido", [True, False])
def test_limite_exacto_lo_decide_expresamente_la_politica(borde, incluido):
    db, _, sesion, datos = preparar()
    apertura, cierre = AHORA - timedelta(minutes=1), AHORA + timedelta(minutes=1)
    ventana = VentanaIngreso(apertura, cierre, incluido if borde == "apertura" else True,
                            incluido if borde == "cierre" else True)
    datos["politica"] = SimpleNamespace(obtener_ventana=lambda **_: ventana)
    instante = apertura if borde == "apertura" else cierre
    datos["reloj"] = SimpleNamespace(ahora=lambda: instante)
    if incluido:
        assert validar_ingreso(db, **datos) is sesion
    else:
        with pytest.raises(ErrorIngreso): validar_ingreso(db, **datos)


@pytest.mark.parametrize("desfase", [-1, 1])
def test_un_microsegundo_fuera_de_ventana_no_autoriza(desfase):
    db, _, _, datos = preparar()
    ventana = VentanaIngreso(AHORA, AHORA + timedelta(minutes=1), True, True)
    instante = (ventana.apertura if desfase < 0 else ventana.cierre) + timedelta(microseconds=desfase)
    datos.update(politica=SimpleNamespace(obtener_ventana=lambda **_: ventana),
                 reloj=SimpleNamespace(ahora=lambda: instante))
    with pytest.raises(ErrorIngreso): validar_ingreso(db, **datos)


def test_zonas_equivalentes_producen_mismo_resultado():
    db, _, sesion, datos = preparar()
    zona = timezone(timedelta(hours=-5))
    ventana = VentanaIngreso((AHORA-timedelta(minutes=1)).astimezone(zona),
                            (AHORA+timedelta(minutes=1)).astimezone(zona), True, True)
    datos["politica"] = SimpleNamespace(obtener_ventana=lambda **_: ventana)
    datos["reloj"] = SimpleNamespace(ahora=lambda: AHORA.astimezone(timezone(timedelta(hours=5, minutes=30))))
    assert validar_ingreso(db, **datos) is sesion


def test_misma_hora_local_con_otro_offset_no_es_el_mismo_instante():
    ventana = VentanaIngreso(AHORA, AHORA + timedelta(minutes=30), True, True)
    assert not ventana.contiene(AHORA.replace(tzinfo=timezone(timedelta(hours=-1))))


@pytest.mark.parametrize("dato", ["fecha_inicio", "fecha_fin", "reloj"])
def test_no_se_infiere_zona_para_fechas_naive(dato):
    db, _, sesion, datos = preparar()
    if dato == "reloj": datos["reloj"] = SimpleNamespace(ahora=lambda: AHORA.replace(tzinfo=None))
    else: setattr(sesion, dato, getattr(sesion, dato).replace(tzinfo=None))
    with pytest.raises(PoliticaTemporalNoDisponible): validar_ingreso(db, **datos)


@pytest.mark.parametrize("problema", ["sin_ventana", "amplia_inicio", "amplia_fin", "invertida"])
def test_no_se_acepta_configuracion_temporal_incoherente(problema):
    db, _, sesion, datos = preparar()
    if problema == "invertida":
        sesion.fecha_fin = sesion.fecha_inicio
    else:
        valor = None if problema == "sin_ventana" else VentanaIngreso(
            sesion.fecha_inicio - timedelta(seconds=1) if problema == "amplia_inicio" else sesion.fecha_inicio,
            sesion.fecha_fin + timedelta(seconds=1) if problema == "amplia_fin" else sesion.fecha_fin, True, True,
        )
        datos["politica"] = SimpleNamespace(obtener_ventana=lambda **_: valor)
    with pytest.raises(PoliticaTemporalNoDisponible): validar_ingreso(db, **datos)


def test_reloj_se_consulta_una_vez_despues_de_la_politica():
    db, _, _, datos = preparar()
    eventos = []
    def obtener(**_):
        eventos.append("politica")
        return VentanaIngreso(AHORA-timedelta(minutes=1), AHORA+timedelta(minutes=1), True, True)
    def ahora():
        eventos.append("reloj")
        return AHORA
    datos.update(politica=SimpleNamespace(obtener_ventana=obtener), reloj=SimpleNamespace(ahora=ahora))
    validar_ingreso(db, **datos)
    assert eventos == ["politica", "reloj"]
    db.commit.assert_not_called()


# Los cuatro casos del proveedor anticipado se sustituyen por los rechazos de
# estado y límites de este archivo y la aceptación HTTP: contrato descartado,
# no una excepción permisiva ni una política nueva para EN_CURSO.
