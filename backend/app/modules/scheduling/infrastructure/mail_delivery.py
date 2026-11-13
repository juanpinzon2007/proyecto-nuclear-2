"""Despacho recuperable del aviso existente con material secreto cifrado."""
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import ipaddress
import json
import smtplib
import ssl
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.scheduling.infrastructure.mail_models import DespachoCorreoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, EventoAuditoriaModel, NotificacionModel
from app.modules.scheduling.domain.access_codes import coincide_codigo


@dataclass(frozen=True)
class ConfiguracionCorreo:
    host: str
    puerto: int
    tls: str
    remitente: str
    url_publica: str
    clave: bytes = field(repr=False)
    usuario: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)


def _loopback(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def configuracion_correo():
    settings = get_settings()
    if not settings.scheduling_mail_enabled:
        return None
    try:
        from cryptography.fernet import Fernet
        host = settings.scheduling_mail_host
        puerto = settings.scheduling_mail_port
        tls = settings.scheduling_mail_tls
        remitente = settings.scheduling_mail_from
        url = settings.scheduling_mail_public_url
        clave = settings.scheduling_mail_encryption_key
        if not host or puerto is None or not remitente or not url or clave is None:
            raise ValueError()
        if tls not in {'STARTTLS', 'SSL', 'LAB_LOOPBACK'}:
            raise ValueError()
        if tls == 'LAB_LOOPBACK' and not _loopback(host):
            raise ValueError()
        direccion = parseaddr(remitente)[1]
        if direccion != remitente or '@' not in direccion or any(c in remitente for c in '\r\n'):
            raise ValueError()
        parsed = urlsplit(url)
        if parsed.username or parsed.password or not parsed.hostname or parsed.fragment:
            raise ValueError()
        if parsed.scheme != 'https' and not (tls == 'LAB_LOOPBACK' and parsed.scheme == 'http' and _loopback(parsed.hostname)):
            raise ValueError()
        password = settings.scheduling_mail_password
        usuario = settings.scheduling_mail_username
        if bool(usuario) != bool(password):
            raise ValueError()
        key = clave.get_secret_value().encode('ascii')
        Fernet(key)
        return ConfiguracionCorreo(host, puerto, tls, remitente, url, key, usuario,
                                   password.get_secret_value() if password else None)
    except (ValueError, TypeError, UnicodeError, ImportError):
        raise IntegracionPendiente() from None


def encolar_correo(db, *, notificacion, caso, sesion, codigo=None):
    """Usa la misma transacción de convocatoria/aviso. No abre conexión SMTP."""
    config = configuracion_correo()
    if config is None:
        return
    from cryptography.fernet import Fernet
    correo = db.scalar(select(UsuarioORM.correo).join(IdentidadAcademicaORM,
        IdentidadAcademicaORM.id_usuario == UsuarioORM.id_usuario).where(
        IdentidadAcademicaORM.sistema == 'SCHEDULING',
        IdentidadAcademicaORM.id_academico == notificacion.destinatario_id))
    if not correo:
        raise IntegracionPendiente()
    if notificacion.tipo == 'CONVOCATORIA' and not codigo:
        raise IntegracionPendiente()
    payload = dict(notificacion_id=str(notificacion.id), convocatoria_id=str(notificacion.convocatoria_id),
                   destinatario_id=str(notificacion.destinatario_id), correo=correo,
                   tipo=notificacion.tipo, caso=caso, inicio=sesion.fecha_inicio.isoformat(),
                   mensaje=sesion.mensaje_personalizado or '', codigo=codigo, url=config.url_publica)
    cifrado = Fernet(config.clave).encrypt(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8'))
    db.add(DespachoCorreoModel(id_notificacion=notificacion.id, payload_cifrado=cifrado))
    db.flush()


def enviar_smtp(config, *, id_notificacion, payload):
    mensaje = EmailMessage()
    mensaje['From'] = config.remitente
    mensaje['To'] = payload['correo']
    mensaje['Message-ID'] = f'<{id_notificacion}@{config.remitente.rsplit("@", 1)[1]}>'
    mensaje['Subject'] = 'Convocatoria académica' if payload['tipo'] == 'CONVOCATORIA' else 'Retiro de convocatoria académica'
    texto = [f"Caso: {payload['caso']}", f"Inicio programado: {payload['inicio']}", payload['mensaje'],
             f"URL: {payload['url']}"]
    if payload['tipo'] == 'CONVOCATORIA':
        texto.append(f"Código individual: {payload['codigo']}")
    else:
        texto.append('El docente retiró tu autorización para esta sesión.')
    mensaje.set_content('\n'.join(texto))
    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL(config.host, config.puerto, timeout=15, context=context) if config.tls == 'SSL' else smtplib.SMTP(config.host, config.puerto, timeout=15)
    with client:
        if config.tls == 'STARTTLS':
            client.starttls(context=context)
        if config.usuario:
            client.login(config.usuario, config.password)
        rechazados = client.send_message(mensaje, from_addr=config.remitente, to_addrs=[payload['correo']])
        if rechazados:
            raise smtplib.SMTPRecipientsRefused(rechazados)


def _auditar(db, notificacion, convocatoria, despacho, resultado):
    db.add(EventoAuditoriaModel(id=uuid4(), sesion_id=convocatoria.sesion_id, tipo='DESPACHO_CORREO',
        origen='SISTEMA', descripcion=json.dumps(dict(id_notificacion=str(notificacion.id),
            intento=despacho.intentos, resultado=resultado), sort_keys=True), creado_en=datetime.now(timezone.utc)))


def _despachar_uno(crear_sesion, config, identificador):
    from cryptography.fernet import Fernet, InvalidToken
    with crear_sesion.begin() as db:
        despacho = db.scalar(select(DespachoCorreoModel).where(
            DespachoCorreoModel.id_notificacion == identificador,
            DespachoCorreoModel.estado.in_(('PENDIENTE', 'REINTENTAR'))).with_for_update(skip_locked=True))
        if despacho is None:
            return 'OMITIDO'
        aviso = db.get(NotificacionModel, identificador)
        convocatoria = db.scalar(select(ConvocatoriaModel).where(
            ConvocatoriaModel.id == aviso.convocatoria_id).with_for_update(read=True))
        if convocatoria is None or convocatoria.estudiante_id != aviso.destinatario_id:
            raise IntegracionPendiente()
        despacho.intentos += 1
        despacho.ultimo_intento_en = datetime.now(timezone.utc)
        if aviso.tipo == 'CONVOCATORIA' and convocatoria.estado != 'ACTIVA':
            despacho.estado = 'CANCELADO'
            despacho.ultimo_error = 'CONVOCATORIA_RETIRADA'
            _auditar(db, aviso, convocatoria, despacho, 'CANCELADO')
            return 'CANCELADO'
        try:
            payload = json.loads(Fernet(config.clave).decrypt(despacho.payload_cifrado).decode('utf-8'))
            if (payload['notificacion_id'] != str(aviso.id)
                or payload['convocatoria_id'] != str(convocatoria.id)
                or payload['destinatario_id'] != str(aviso.destinatario_id)
                or payload['tipo'] != aviso.tipo):
                raise ValueError()
            if aviso.tipo == 'CONVOCATORIA' and not coincide_codigo(payload['codigo'], convocatoria.codigo_hash):
                despacho.estado = 'CANCELADO'
                despacho.ultimo_error = 'CREDENCIAL_CAMBIO'
                _auditar(db, aviso, convocatoria, despacho, 'CANCELADO')
                return 'CANCELADO'
            persona = db.scalar(select(UsuarioORM).join(IdentidadAcademicaORM,
                IdentidadAcademicaORM.id_usuario == UsuarioORM.id_usuario).where(
                IdentidadAcademicaORM.sistema == 'SCHEDULING', IdentidadAcademicaORM.id_academico == aviso.destinatario_id)
                .with_for_update(read=True, of=UsuarioORM))
            if persona is None or not persona.activo or payload['correo'] != persona.correo:
                despacho.estado = 'CANCELADO'
                despacho.ultimo_error = 'DESTINATARIO_CAMBIO'
                _auditar(db, aviso, convocatoria, despacho, 'CANCELADO')
                return 'CANCELADO'
            enviar_smtp(config, id_notificacion=aviso.id, payload=payload)
        except (InvalidToken, ValueError, KeyError, TypeError, UnicodeError):
            despacho.estado = 'REINTENTAR'
            despacho.ultimo_error = 'PAYLOAD_NO_VERIFICABLE'
        except (OSError, smtplib.SMTPException):
            despacho.estado = 'REINTENTAR'
            despacho.ultimo_error = 'SMTP_NO_CONFIRMADO'
        else:
            despacho.estado = 'ACEPTADO_PROVEEDOR'
            despacho.aceptado_en = datetime.now(timezone.utc)
            despacho.ultimo_error = None
        _auditar(db, aviso, convocatoria, despacho, despacho.estado)
        return despacho.estado


def despachar_pendientes(crear_sesion, *, limite=20):
    """Un lote operativo; cada pendiente se intenta una vez por invocación."""
    if type(limite) is not int or limite <= 0:
        raise ValueError('El tamaño del lote debe ser positivo.')
    config = configuracion_correo()
    if config is None:
        raise IntegracionPendiente()
    with crear_sesion() as db:
        if db.get_bind().dialect.name != 'postgresql':
            raise IntegracionPendiente()
        ids = db.scalars(select(DespachoCorreoModel.id_notificacion).where(
            DespachoCorreoModel.estado.in_(('PENDIENTE', 'REINTENTAR')))
            .order_by(DespachoCorreoModel.id_notificacion).limit(limite)).all()
    resultados = []
    for identificador in ids:
        resultados.append(_despachar_uno(crear_sesion, config, identificador))
    return resultados


def main():
    parser = argparse.ArgumentParser(description='Despacha un lote de correos durables pendientes.')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    try:
        from app.db.models import registrar_modelos_integrados
        from app.db.session import get_session_factory
        registrar_modelos_integrados()
        resultados = despachar_pendientes(get_session_factory(), limite=args.limit)
        print('Lote procesado. Registros:', len(resultados))
        return 0
    except Exception:
        print('Despacho no disponible. Revise configuración y registro de operaciones.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
