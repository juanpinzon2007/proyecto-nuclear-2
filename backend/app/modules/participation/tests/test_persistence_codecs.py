from datetime import datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
from zoneinfo import ZoneInfo

import pytest

from app.modules.participation.infrastructure.codecs import FechasPersistencia, decimal_exacto
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente


def test_timestamp_con_zona_se_normaliza_sin_cambiar_instante():
    fecha = datetime(2026, 10, 27, 10, tzinfo=timezone(timedelta(hours=-5)))
    assert FechasPersistencia(None).desde_db(fecha) == datetime(2026, 10, 27, 15, tzinfo=timezone.utc)


def test_timestamp_naive_no_infiere_zona_de_la_maquina():
    with pytest.raises(MapeoPersistenciaPendiente):
        FechasPersistencia(None).desde_db(datetime(2026, 10, 27, 10))


@pytest.mark.parametrize("offset", [0, -5, 3])
def test_roundtrip_timestamp_naive_requiere_politica_explicita(offset):
    fechas = FechasPersistencia(timezone(timedelta(hours=offset)))
    utc = datetime(2026, 10, 27, 15, 30, 45, 123456, tzinfo=timezone.utc)
    fila = fechas.hacia_db(utc, sin_offset=True)
    assert fila.tzinfo is None
    assert fechas.desde_db(fila) == utc


def test_no_se_elimina_offset_sin_acuerdo():
    with pytest.raises(MapeoPersistenciaPendiente):
        FechasPersistencia(None).hacia_db(datetime(2026, 10, 27, tzinfo=timezone.utc), sin_offset=True)


def test_no_se_acepta_fecha_naive_del_dominio():
    with pytest.raises(MapeoPersistenciaPendiente):
        FechasPersistencia(timezone.utc).hacia_db(datetime(2026, 10, 27), sin_offset=False)


@pytest.mark.parametrize("mes,dia,hora", [(11, 1, 1), (3, 8, 2)])
def test_timestamp_local_ambiguo_o_inexistente_no_se_adivina(mes, dia, hora):
    fechas = FechasPersistencia(ZoneInfo("America/New_York"))
    with pytest.raises(MapeoPersistenciaPendiente):
        fechas.desde_db(datetime(2026, mes, dia, hora, 30))


@pytest.mark.parametrize("valor,esperado", [("4", "4.00"), ("1.230", "1.23"), ("0", "0.00"), ("99.99", "99.99")])
def test_numeric_preserva_valor_decimal_exacto(valor, esperado):
    actual = decimal_exacto(Decimal(valor), precision=4, escala=2)
    assert str(actual) == esperado


@pytest.mark.parametrize("valor", [Decimal("1.235"), Decimal("100"), Decimal("NaN"), Decimal("Infinity"), Decimal("-1"), 0.1])
def test_no_redondea_trunca_o_desborda_calificaciones(valor):
    with pytest.raises(MapeoPersistenciaPendiente):
        decimal_exacto(valor, precision=4, escala=2)


def test_criterio_5_2_no_pierde_aporte_exacto():
    with pytest.raises(MapeoPersistenciaPendiente):
        decimal_exacto(Decimal("0.333333"), precision=5, escala=2)


def test_conversion_no_depende_del_contexto_decimal_global():
    with localcontext() as contexto:
        contexto.prec = 2
        contexto.traps[Inexact] = True
        assert decimal_exacto(Decimal("99.99"), precision=4, escala=2) == Decimal("99.99")


@pytest.mark.parametrize("precision,escala", [(0, 0), (2, 3), (4, -1), (True, 0)])
def test_validacion_de_parametros_tecnicos_numeric(precision, escala):
    with pytest.raises(ValueError):
        decimal_exacto(Decimal(1), precision=precision, escala=escala)
