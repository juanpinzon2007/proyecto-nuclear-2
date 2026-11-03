"""Regresiones de infraestructura, sin Docker ni bases reales: simulaciones explícitas."""

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.exc import OperationalError

from . import academic_identity_support as lab


ID = "a" * 64
SECRETO = "secreto laboratorio/@?"


class TiempoSimulado:
    def __init__(self):
        self.instante = 0
        self.pausas = []

    def ahora(self):
        return self.instante

    def pausa(self, segundos):
        self.pausas.append(segundos)
        self.instante += segundos


def conexion(base="sps_identity_test_resolver", error=None):
    contexto = MagicMock()
    contexto.__enter__.return_value.scalar.return_value = base
    if error:
        contexto.__enter__.return_value.scalar.side_effect = error
    return contexto


def error_operativo(mensaje="connection refused"):
    return OperationalError(None, None, Exception(mensaje))


def esperar(motor, tiempo, **opciones):
    lab.esperar_postgresql_tcp(motor, secreto=SECRETO, reloj=tiempo.ahora, pausa=tiempo.pausa, **opciones)


def test_reintenta_tcp_temporalmente_indisponible_hasta_select_correcto():
    motor, tiempo = Mock(), TiempoSimulado()
    correcta = conexion()
    motor.connect.side_effect = [error_operativo(), error_operativo("server closed connection"), correcta]
    esperar(motor, tiempo)
    assert motor.connect.call_count == 3 and motor.dispose.call_count == 2
    assert len(tiempo.pausas) == 2
    assert str(correcta.__enter__.return_value.scalar.call_args.args[0]) == "SELECT current_database()"


def test_conectar_no_basta_si_select_falla_durante_reinicio():
    motor, tiempo = Mock(), TiempoSimulado()
    motor.connect.side_effect = [conexion(error=error_operativo()), conexion()]
    esperar(motor, tiempo)
    assert motor.connect.call_count == 2


def test_base_incorrecta_aborta_sin_reintentar_ni_ejecutar_ddl():
    motor, tiempo = Mock(), TiempoSimulado()
    motor.connect.return_value = conexion("sps")
    with pytest.raises(RuntimeError, match="identidad"):
        esperar(motor, tiempo)
    assert motor.connect.call_count == 1 and tiempo.pausas == []


def test_plazo_monotonico_y_ultimo_error_redactado():
    motor, tiempo = Mock(), TiempoSimulado()
    motor.connect.side_effect = error_operativo(f"password='{SECRETO}'; connection refused")
    with pytest.raises(TimeoutError) as fallo:
        esperar(motor, tiempo, timeout=1, intervalo=.3)
    assert tiempo.instante == pytest.approx(1)
    assert motor.connect.call_count == 4
    assert "connection refused" in str(fallo.value) and SECRETO not in str(fallo.value)


def test_un_intento_lento_no_produce_espera_ilimitada():
    motor, tiempo = Mock(), TiempoSimulado()
    def conectar():
        tiempo.instante += 2
        raise error_operativo()
    motor.connect.side_effect = conectar
    with pytest.raises(TimeoutError):
        esperar(motor, tiempo, timeout=3)
    assert motor.connect.call_count == 2 and tiempo.instante < 5


def test_fallo_inesperado_no_se_oculta_como_reintento():
    motor, tiempo = Mock(), TiempoSimulado()
    motor.connect.side_effect = ValueError("fallo de programación")
    with pytest.raises(ValueError):
        esperar(motor, tiempo)
    assert motor.connect.call_count == 1 and tiempo.pausas == []


@pytest.mark.parametrize("mensaje", [
    f"password='{SECRETO}'", "postgresql://usuario:oculto@localhost/base",
    "password=otro-secreto", "POSTGRES_PASSWORD=otra-clave", "pwd:clave",
])
def test_redaccion_no_expone_passwords(mensaje):
    salida = lab.sin_credenciales(mensaje, SECRETO)
    assert "<redactado>" in salida
    for privado in (SECRETO, "oculto", "otro-secreto", "otra-clave", "pwd:clave"):
        assert privado not in salida


def test_diagnosticos_incluyen_estado_stdout_stderr_sin_credenciales(monkeypatch):
    ejecutar = Mock(side_effect=[
        SimpleNamespace(stdout='{"Running":false}', stderr=""),
        SimpleNamespace(stdout="initdb en curso", stderr=f"password='{SECRETO}'"),
    ])
    monkeypatch.setattr(lab.subprocess, "run", ejecutar)
    mensaje = lab.diagnostico_laboratorio(ID, SECRETO)
    assert "Running" in mensaje and "initdb en curso" in mensaje and SECRETO not in mensaje
    assert all(c.args[0][-1] == ID for c in ejecutar.call_args_list)
    assert all(c.kwargs["timeout"] == 3 for c in ejecutar.call_args_list)


def test_fallo_de_diagnosticos_no_oculta_causa(monkeypatch):
    monkeypatch.setattr(lab.subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired("docker", 3)))
    assert "no disponible" in lab.diagnostico_laboratorio(ID, SECRETO)


@pytest.mark.parametrize("identificador", ["proyecto-nuclear-2-db-1", "sps-identity-pg-test", "abc", ""])
def test_nunca_limpia_por_nombre_o_id_incompleto(monkeypatch, identificador):
    ejecutar = Mock()
    monkeypatch.setattr(lab.subprocess, "run", ejecutar)
    with pytest.raises(RuntimeError): lab.eliminar_laboratorio(identificador)
    ejecutar.assert_not_called()


def test_limpieza_usa_solo_id_creado_y_tolera_ya_eliminado(monkeypatch):
    ejecutar = Mock(return_value=SimpleNamespace(returncode=1, stdout="", stderr="No such container"))
    monkeypatch.setattr(lab.subprocess, "run", ejecutar)
    lab.eliminar_laboratorio(ID)
    assert ejecutar.call_args.args[0] == ["docker", "rm", "--force", ID]


@pytest.fixture
def entorno_simulado(monkeypatch):
    monkeypatch.setenv("SPS_TEST_IDENTITY_MAPPING_DOCKER", "1")
    monkeypatch.setattr(lab.secrets, "token_urlsafe", lambda _: SECRETO)
    nombre = "sps-resolver-lab-" + "b" * 12
    monkeypatch.setattr(lab, "uuid4", lambda: SimpleNamespace(hex="b" * 32))
    datos = {"Id": ID, "Name": "/" + nombre,
             "Config": {"Labels": {"sps.identity.mapping.lab": "true"}}, "Mounts": [],
             "NetworkSettings": {"Ports": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55555"}]}}}
    comando = Mock(side_effect=["imagen", ID, ID, json.dumps([datos])])
    monkeypatch.setattr(lab, "docker", comando)
    motor = Mock()
    crear = Mock(return_value=motor)
    monkeypatch.setattr(lab, "create_engine", crear)
    espera = Mock(side_effect=TimeoutError(f"Último error password='{SECRETO}'; refused"))
    monkeypatch.setattr(lab, "esperar_postgresql_tcp", espera)
    diagnostico = Mock(return_value="estado: stopped; logs: initdb incompleto")
    monkeypatch.setattr(lab, "diagnostico_laboratorio", diagnostico)
    limpiar = Mock()
    monkeypatch.setattr(lab, "eliminar_laboratorio", limpiar)
    return SimpleNamespace(motor=motor, crear=crear, espera=espera, limpiar=limpiar,
                           diagnostico=diagnostico, comando=comando, datos=datos)


def test_timeout_fixture_diagnostica_y_elimina_su_contenedor(entorno_simulado):
    e = entorno_simulado
    with pytest.raises(RuntimeError) as fallo:
        with lab.motor_postgresql_desechable(): pytest.fail("No debe entregar engine")
    assert "initdb incompleto" in str(fallo.value) and "refused" in str(fallo.value)
    assert SECRETO not in str(fallo.value)
    e.limpiar.assert_called_once_with(ID)
    e.motor.dispose.assert_called_once()
    url = e.crear.call_args.args[0]
    assert url.host == "127.0.0.1" and url.port == 55555 and url.database == "sps_identity_test_resolver"
    assert e.crear.call_args.kwargs["connect_args"]["connect_timeout"] == 2


def test_finally_limpia_aunque_dispose_falle_sin_ocultar_timeout(entorno_simulado):
    e = entorno_simulado
    e.motor.dispose.side_effect = RuntimeError("falló dispose")
    with pytest.raises(RuntimeError, match="initdb incompleto") as fallo:
        with lab.motor_postgresql_desechable(): pass
    e.limpiar.assert_called_once_with(ID)
    assert any("dispose" in nota for nota in fallo.value.__notes__)


def test_fallo_limpieza_se_reporta_sin_perder_causa_inicial(entorno_simulado):
    e = entorno_simulado
    e.limpiar.side_effect = RuntimeError("falló Docker rm")
    with pytest.raises(RuntimeError, match="initdb incompleto") as fallo:
        with lab.motor_postgresql_desechable(): pass
    assert any("Docker rm" in nota for nota in fallo.value.__notes__)


def test_start_falla_y_finally_elimina_id_creado(entorno_simulado):
    e = entorno_simulado
    e.comando.side_effect = ["imagen", ID, RuntimeError("falló start")]
    with pytest.raises(RuntimeError, match="start"):
        with lab.motor_postgresql_desechable(): pass
    e.limpiar.assert_called_once_with(ID)


@pytest.mark.parametrize("infraccion", ["etiqueta", "volumen", "puerto", "identidad"])
def test_aislamiento_invalido_no_abre_tcp(entorno_simulado, infraccion):
    e = entorno_simulado
    if infraccion == "etiqueta": e.datos["Config"]["Labels"] = {}
    elif infraccion == "volumen": e.datos["Mounts"] = [{"Type": "volume"}]
    elif infraccion == "puerto": e.datos["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostIp"] = "0.0.0.0"
    else: e.datos["Id"] = "c" * 64
    e.comando.side_effect = ["imagen", ID, ID, json.dumps([e.datos])]
    with pytest.raises((AssertionError, KeyError)):
        with lab.motor_postgresql_desechable(): pass
    e.crear.assert_not_called()
    e.limpiar.assert_called_once_with(ID)
