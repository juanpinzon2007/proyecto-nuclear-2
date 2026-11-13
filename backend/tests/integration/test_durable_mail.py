"""RF20/21 main/JWT/PG17 y capturador SMTP local real, datos exclusivamente LAB."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from email import message_from_bytes
import secrets
import socket
from uuid import UUID

from aiosmtpd.controller import Controller
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa

from app.core.config import get_settings
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.scheduling.infrastructure.mail_delivery import despachar_pendientes
from app.modules.scheduling.infrastructure.mail_models import DespachoCorreoModel as Mail
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C, NotificacionModel as N, EventoAuditoriaModel as E
from tests.integration.test_convocation_management_http import (
    gestion, integracion, autor, pg_autoria, payload_valido, alta,
)  # noqa: F401


class Capturador:
    def __init__(self):
        self.mensajes = []
        self.rechazar = False

    async def handle_DATA(self, server, session, envelope):
        if self.rechazar:
            return '451 Fallo temporal explícito LAB'
        self.mensajes.append((tuple(envelope.rcpt_tos), envelope.content))
        return '250 Mensaje capturado en laboratorio'


@contextmanager
def smtp_local():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    handler = Capturador()
    controller = Controller(handler, hostname='127.0.0.1', port=port)
    controller.start()
    try:
        yield handler, port
    finally:
        controller.stop()


@pytest.fixture
def correo_main(gestion, monkeypatch):
    from app.main import app
    h = gestion
    anterior = dict(app.dependency_overrides)
    app.dependency_overrides.update(h.client.app.dependency_overrides)
    clave = secrets.token_urlsafe(24)
    with h.sesiones.begin() as db:
        usuario = db.get(UsuarioORM, h.a.propio)
        usuario.clave_hash = obtener_hasheador().hash(clave)
        correo = usuario.correo
    with TestClient(app, raise_server_exceptions=False) as client, smtp_local() as (capture, port):
        login = client.post('/api/v1/identity/auth/personal', json={'correo': correo, 'clave': clave})
        assert login.status_code == 200, login.text
        h.client = client
        h.a.headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
        settings = get_settings()
        values = dict(scheduling_mail_enabled=True, scheduling_mail_host='127.0.0.1',
            scheduling_mail_port=port, scheduling_mail_tls='LAB_LOOPBACK',
            scheduling_mail_from='nuclear@universidad.test', scheduling_mail_public_url='http://127.0.0.1/simulador',
            scheduling_mail_encryption_key=Fernet.generate_key().decode(),
            scheduling_mail_username=None, scheduling_mail_password=None)
        # Pydantic convierte SecretStr al construir Settings. La configuración
        # explícita de esta fixture conserva sus tipos al inyectar valores.
        from pydantic import SecretStr
        values['scheduling_mail_encryption_key'] = SecretStr(values['scheduling_mail_encryption_key'])
        for name, value in values.items():
            monkeypatch.setattr(settings, name, value)
        h.capture = capture
        yield h
    app.dependency_overrides.clear()
    app.dependency_overrides.update(anterior)


def filas(h):
    with h.sesiones() as db:
        return db.scalars(sa.select(Mail).join(N, N.id == Mail.id_notificacion).join(C, C.id == N.convocatoria_id).where(C.sesion_id == h.nueva_sesion).order_by(Mail.id_notificacion)).all()


def test_main_crea_cifrado_durable_y_worker_smtp_recupera_otra_session(correo_main):
    h = correo_main
    r = alta(h)
    assert r.status_code == 201, r.text
    code = r.json()['codigo_acceso']
    cid = UUID(r.json()['convocatoria_id'])
    pendiente = filas(h)
    assert len(pendiente) == 1 and pendiente[0].estado == 'PENDIENTE'
    assert code.encode() not in pendiente[0].payload_cifrado and h.capture.mensajes == []
    for invalidos in ({'intentos': -1}, {'estado': 'ENVIADO'}, {'payload_cifrado': b''},
                      {'estado': 'ACEPTADO_PROVEEDOR'}):
        with pytest.raises(sa.exc.IntegrityError):
            with h.sesiones.begin() as db:
                db.execute(sa.update(Mail).where(Mail.id_notificacion == pendiente[0].id_notificacion).values(**invalidos))
    with pytest.raises(sa.exc.IntegrityError):
        with h.sesiones.begin() as db:
            db.add(Mail(id_notificacion=pendiente[0].id_notificacion, payload_cifrado=b'duplicado'))
    with h.sesiones() as db:
        assert db.get(C, cid).codigo_hash != code
        assert code not in db.get(N, pendiente[0].id_notificacion).mensaje
    assert despachar_pendientes(h.sesiones) == ['ACEPTADO_PROVEEDOR']
    assert len(h.capture.mensajes) == 1
    recipients, raw = h.capture.mensajes[0]
    with h.sesiones() as db:
        expected = db.get(UsuarioORM, h.estudiante).correo
    assert recipients == (expected,)
    message = message_from_bytes(raw)
    body = message.get_payload(decode=True).decode('utf-8')
    assert code in body and 'Mensaje docente de laboratorio' in body and 'http://127.0.0.1/simulador' in body
    actual = filas(h)[0]
    assert actual.intentos == 1 and actual.aceptado_en is not None
    assert despachar_pendientes(h.sesiones) == [] and len(h.capture.mensajes) == 1
    with h.sesiones() as db:
        audit = db.scalars(sa.select(E).where(E.tipo == 'DESPACHO_CORREO', E.sesion_id == h.nueva_sesion)).all()
        assert len(audit) == 1 and code not in audit[0].descripcion
    assert alta(h).status_code == 422


def test_fallo_smtp_despues_commit_reintenta_sin_recrear_convocatoria(correo_main):
    h = correo_main
    r = alta(h)
    assert r.status_code == 201
    cid = UUID(r.json()['convocatoria_id'])
    h.capture.rechazar = True
    assert despachar_pendientes(h.sesiones) == ['REINTENTAR']
    assert not h.capture.mensajes and filas(h)[0].ultimo_error == 'SMTP_NO_CONFIRMADO'
    with h.sesiones() as db:
        assert db.get(C, cid).estado == 'ACTIVA'
    h.capture.rechazar = False
    assert despachar_pendientes(h.sesiones) == ['ACEPTADO_PROVEEDOR']
    assert len(h.capture.mensajes) == 1 and filas(h)[0].intentos == 2
    with h.sesiones() as db:
        assert len(db.scalars(sa.select(C).where(C.sesion_id == h.nueva_sesion)).all()) == 1
        assert len(db.scalars(sa.select(E).where(E.tipo == 'DESPACHO_CORREO', E.sesion_id == h.nueva_sesion)).all()) == 2


def test_reintentos_concurrentes_un_solo_envio_aceptado(correo_main):
    h = correo_main
    assert alta(h).status_code == 201
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: despachar_pendientes(h.sesiones), range(2)))
    assert sum(r.count('ACEPTADO_PROVEEDOR') for r in results) == 1
    assert len(h.capture.mensajes) == 1 and filas(h)[0].intentos == 1


def test_retiro_cancela_credencial_pendiente_y_envia_aviso_de_retiro(correo_main):
    h = correo_main
    alta_response = alta(h)
    cid = alta_response.json()['convocatoria_id']
    code = alta_response.json()['codigo_acceso']
    retiro = h.client.delete(h.nuevo_base + '/' + cid, headers=h.a.headers)
    assert retiro.status_code == 200
    assert h.client.delete(h.nuevo_base + '/' + cid, headers=h.a.headers).status_code == 200
    states = despachar_pendientes(h.sesiones)
    assert sorted(states) == ['ACEPTADO_PROVEEDOR', 'CANCELADO']
    assert len(h.capture.mensajes) == 1
    body = h.capture.mensajes[0][1].decode('utf-8')
    assert code not in body
    with h.sesiones() as db:
        assert db.get(C, UUID(cid)).estado == 'RETIRADA'
    assert len(filas(h)) == 2


@pytest.mark.parametrize('field,value', [('scheduling_mail_encryption_key', None), ('scheduling_mail_public_url', None),
    ('scheduling_mail_tls', 'PLAIN'), ('scheduling_mail_host', 'example.invalid')])
def test_configuracion_incompleta_o_insegura_rechaza_antes_commit(correo_main, monkeypatch, field, value):
    h = correo_main
    monkeypatch.setattr(get_settings(), field, value)
    r = alta(h)
    assert r.status_code == 503, r.text
    with h.sesiones() as db:
        assert not db.scalars(sa.select(C).where(C.sesion_id == h.nueva_sesion)).all()
        assert filas(h) == []


def test_fallo_sql_de_outbox_revierte_convocatoria_y_aviso(correo_main):
    h = correo_main
    engine = h.sesiones.kw['bind']
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('INSERT INTO DESPACHO_CORREO'):
            raise sa.exc.OperationalError('INSERT', {}, RuntimeError('SQL LAB'))
    sa.event.listen(engine, 'before_cursor_execute', fail)
    try:
        assert alta(h).status_code == 503
    finally:
        sa.event.remove(engine, 'before_cursor_execute', fail)
    with h.sesiones() as db:
        assert not db.scalars(sa.select(C).where(C.sesion_id == h.nueva_sesion)).all()
        assert filas(h) == []
    assert h.capture.mensajes == []


def test_payload_cambiado_no_se_entrega(correo_main):
    h = correo_main
    assert alta(h).status_code == 201
    with h.sesiones.begin() as db:
        row = db.get(Mail, filas(h)[0].id_notificacion)
        row.payload_cifrado = row.payload_cifrado[:-1] + b'!'
    assert despachar_pendientes(h.sesiones) == ['REINTENTAR']
    assert filas(h)[0].ultimo_error == 'PAYLOAD_NO_VERIFICABLE' and not h.capture.mensajes


@pytest.mark.parametrize('cambio', ['credencial', 'cuenta_inactiva'])
def test_despacho_revalida_credencial_y_destinatario(correo_main, cambio):
    from app.modules.scheduling.domain.access_codes import hash_codigo
    from app.modules.scheduling.infrastructure.mail_delivery import _despachar_uno, configuracion_correo
    h = correo_main
    response = alta(h)
    assert response.status_code == 201
    with h.sesiones.begin() as db:
        if cambio == 'credencial':
            db.get(C, UUID(response.json()['convocatoria_id'])).codigo_hash = hash_codigo(secrets.token_urlsafe(32))
        else:
            db.get(UsuarioORM, h.estudiante).activo = False
    assert _despachar_uno(h.sesiones, configuracion_correo(), filas(h)[0].id_notificacion) == 'CANCELADO'
    assert h.capture.mensajes == []


def test_puerto_vacio_equivale_a_ausente_sin_inferir_default(monkeypatch):
    from app.core.config import Settings
    from app.modules.scheduling.infrastructure.mail_delivery import configuracion_correo
    from app.modules.identity.domain.errors import IntegracionPendiente
    settings = Settings(_env_file=None, scheduling_mail_port='')
    assert settings.scheduling_mail_port is None and settings.scheduling_mail_enabled is False
    monkeypatch.setattr('app.modules.scheduling.infrastructure.mail_delivery.get_settings', lambda: settings)
    assert configuracion_correo() is None
    settings.scheduling_mail_enabled = True
    with pytest.raises(IntegracionPendiente):
        configuracion_correo()


@pytest.mark.parametrize('actor', ['anonimo', 'estudiante', 'ajeno'])
def test_main_no_encola_sin_autorizacion_persistente(correo_main, actor):
    h = correo_main
    headers = {'anonimo': {}, 'estudiante': h.headers, 'ajeno': h.a.ajeno}[actor]
    response = alta(h, headers=headers)
    assert response.status_code == (401 if actor == 'anonimo' else 403)
    assert filas(h) == [] and h.capture.mensajes == []


def test_migracion_upgrade_downgrade_y_fk_sin_reescribir_historia():
    from alembic import command
    from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic
    from uuid import uuid4
    with motor_postgresql_desechable() as engine:
        with engine.begin() as db:
            command.upgrade(config_alembic(db), '20261108_voluntary_partial')
            anteriores = set(sa.inspect(db).get_table_names())
            command.upgrade(config_alembic(db), 'head')
            assert set(sa.inspect(db).get_table_names()) == anteriores | {'despacho_correo'}
            assert db.scalar(sa.text('SELECT count(*) FROM despacho_correo')) == 0
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as db:
                db.execute(sa.text('INSERT INTO despacho_correo (id_notificacion,payload_cifrado) VALUES (:id,:payload)'),
                    {'id': uuid4(), 'payload': b'sin-referencia'})
        with engine.begin() as db:
            command.downgrade(config_alembic(db), '20261108_voluntary_partial')
            assert set(sa.inspect(db).get_table_names()) == anteriores
            command.upgrade(config_alembic(db), 'head')


def test_downgrade_con_historia_rechaza_perdida(correo_main):
    from alembic import command
    from tests.identity.academic_identity_support import config_alembic
    h = correo_main
    assert alta(h).status_code == 201
    with pytest.raises(RuntimeError, match='historial'):
        with h.sesiones.kw['bind'].begin() as db:
            command.downgrade(config_alembic(db), '20261108_voluntary_partial')
    assert filas(h)[0].estado == 'PENDIENTE'
    # Completar el despacho deja esta cola independiente sin pendientes.
    # El test de payload alterado conserva su evidencia en otra sesión.
    own_id = filas(h)[0].id_notificacion
    from app.modules.scheduling.infrastructure.mail_delivery import _despachar_uno, configuracion_correo
    assert _despachar_uno(h.sesiones, configuracion_correo(), own_id) == 'ACEPTADO_PROVEEDOR'
