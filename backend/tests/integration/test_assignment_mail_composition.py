"""Composición nueva RF04 y despacho RF20/21 sobre main y PostgreSQL propio."""
from email import message_from_bytes

from cryptography.fernet import Fernet
from pydantic import SecretStr
import pytest
import sqlalchemy as sa

from app.core.config import get_settings
from app.db.session import get_engine
from app.modules.scheduling.infrastructure.mail_delivery import despachar_pendientes
from app.modules.scheduling.infrastructure.mail_models import DespachoCorreoModel as Mail
from tests.integration.test_academic_assignment_programming import (
    asignable, personal, lab, inicializar, payload_valido, programar, cantidades,
)  # noqa: F401
from tests.integration.test_durable_mail import smtp_local


@pytest.fixture
def asignacion_con_correo(asignable, monkeypatch):
    with smtp_local() as (captura, puerto):
        settings = get_settings()
        configuracion = dict(scheduling_mail_enabled=True, scheduling_mail_host='127.0.0.1',
            scheduling_mail_port=puerto, scheduling_mail_tls='LAB_LOOPBACK',
            scheduling_mail_from='nuclear@universidad.test',
            scheduling_mail_public_url='http://127.0.0.1/simulador',
            scheduling_mail_encryption_key=SecretStr(Fernet.generate_key().decode()),
            scheduling_mail_username=None, scheduling_mail_password=None)
        for nombre, valor in configuracion.items():
            monkeypatch.setattr(settings, nombre, valor)
        yield asignable, captura


def test_programacion_asignacion_y_correo_comparten_commit_y_recuperacion(asignacion_con_correo):
    h, captura = asignacion_con_correo
    motor = get_engine()
    transacciones = []
    def observar(conn, cursor, sql, *args):
        if sql.lstrip().lower().startswith(('insert into sesion_programada', 'insert into asignacion_caso',
                'insert into convocatoria', 'insert into notificacion', 'insert into despacho_correo')):
            transacciones.append(conn.scalar(sa.text('SELECT txid_current()')))
    sa.event.listen(motor, 'after_cursor_execute', observar)
    try:
        respuesta = programar(h)
    finally:
        sa.event.remove(motor, 'after_cursor_execute', observar)
    assert respuesta.status_code == 201
    codigo = respuesta.json()['convocatorias'][0]['codigo_acceso']
    assert len(transacciones) == 5 and len(set(transacciones)) == 1
    assert cantidades(h.h) == (1, 1, 1, 1) and captura.mensajes == []
    with h.h.sesiones() as sesion:
        pendiente = sesion.scalars(sa.select(Mail)).one()
        assert pendiente.estado == 'PENDIENTE' and codigo.encode() not in pendiente.payload_cifrado
    assert despachar_pendientes(h.h.sesiones) == ['ACEPTADO_PROVEEDOR']
    assert len(captura.mensajes) == 1
    destinatarios, contenido = captura.mensajes[0]
    assert destinatarios == (h.h.estudiante[1],)
    mensaje = message_from_bytes(contenido)
    assert codigo in mensaje.get_payload(decode=True).decode('utf-8')
    assert despachar_pendientes(h.h.sesiones) == [] and len(captura.mensajes) == 1


def test_fallo_outbox_revierte_toda_la_programacion(asignacion_con_correo):
    h, captura = asignacion_con_correo
    motor = get_engine()
    def fallar(conn, cursor, sql, *args):
        if sql.lstrip().lower().startswith('insert into despacho_correo'):
            conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(motor, 'after_cursor_execute', fallar)
    try:
        respuesta = programar(h)
    finally:
        sa.event.remove(motor, 'after_cursor_execute', fallar)
    assert respuesta.status_code == 503
    assert cantidades(h.h) == (0, 0, 0, 0) and captura.mensajes == []
    with h.h.sesiones() as sesion:
        assert sesion.scalar(sa.select(sa.func.count()).select_from(Mail)) == 0
