"""Despacho recuperable del aviso existente con material secreto cifrado."""
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
import ipaddress
import json
import logging
import smtplib
import ssl
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import case, or_, select

from app.core.config import get_settings
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.scheduling.infrastructure.mail_models import DespachoCorreoModel
from app.modules.scheduling.infrastructure.mail_templates import renderizar_correo
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, EventoAuditoriaModel, NotificacionModel
from app.modules.scheduling.application.codigos_convocatoria import (
    CorreoConvocatoriaNoDisponible,
    coincide_codigo_convocatoria,
)

logger = logging.getLogger(__name__)
PAUSA_REINTENTO = timedelta(minutes=1)


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


def _es_url_local(parsed) -> bool:
    return parsed.scheme == 'http' and (parsed.hostname == 'localhost' or _loopback(parsed.hostname))


def configuracion_correo():
    settings = get_settings()
    if not settings.scheduling_mail_enabled:
        return None
    try:
        from cryptography.fernet import Fernet
        host = (settings.scheduling_mail_host or '').strip().casefold()
        puerto = settings.scheduling_mail_port
        tls = settings.scheduling_mail_tls
        remitente = settings.scheduling_mail_from
        url = settings.scheduling_mail_public_url
        clave = settings.scheduling_mail_encryption_key
        if not host or puerto is None or not 1 <= puerto <= 65535 or not remitente or not url or clave is None:
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
        if parsed.scheme != 'https' and not _es_url_local(parsed):
            raise ValueError()
        password = settings.scheduling_mail_password
        usuario = settings.scheduling_mail_username
        if bool(usuario) != bool(password):
            raise ValueError()
        key = clave.get_secret_value().encode('ascii')
        Fernet(key)
        raw_pass = password.get_secret_value() if password else None
        if host == 'smtp.gmail.com':
            raw_pass = ''.join((raw_pass or '').split())
            if (tls, puerto) not in {('STARTTLS', 587), ('SSL', 465)}:
                raise ValueError()
            if not usuario or usuario.casefold() != remitente.casefold() or len(raw_pass) != 16:
                raise ValueError()
        if usuario and tls == 'LAB_LOOPBACK':
            raise ValueError()
        return ConfiguracionCorreo(host, puerto, tls, remitente, url, key, usuario, raw_pass)
    except (ValueError, TypeError, UnicodeError, ImportError):
        raise IntegracionPendiente() from None


def encolar_correo(db, *, notificacion, caso, sesion, codigo=None):
    """Usa la misma transacción de convocatoria/aviso. No abre conexión SMTP."""
    try:
        config = configuracion_correo()
    except IntegracionPendiente:
        if notificacion.tipo == 'CONVOCATORIA':
            raise CorreoConvocatoriaNoDisponible() from None
        raise
    if config is None:
        if notificacion.tipo == 'CONVOCATORIA':
            raise CorreoConvocatoriaNoDisponible()
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
                   fin=sesion.fecha_fin.isoformat(), lugar=sesion.lugar,
                   mensaje=sesion.mensaje_personalizado or '', codigo=codigo, url=config.url_publica)
    cifrado = Fernet(config.clave).encrypt(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8'))
    db.add(DespachoCorreoModel(id_notificacion=notificacion.id, payload_cifrado=cifrado))
    db.flush()


_ASUNTOS_POR_TIPO = {
    'CONVOCATORIA': 'Convocatoria académica SPS',
    'CONVOCATORIA_RETIRADA': 'Retiro de convocatoria académica SPS',
    'CAMBIO_SESION': 'Actualización en sesión académica SPS',
    'CALIFICACION': 'Resultados oficiales publicados SPS',
    'RETROALIMENTACION': 'Nueva retroalimentación docente SPS',
}


class _TransporteSMTP:
    """Reutiliza una conexión autenticada dentro de un único lote."""

    def __init__(self, config: ConfiguracionCorreo):
        self.config = config
        self.cliente: smtplib.SMTP | None = None

    def _conectar(self) -> smtplib.SMTP:
        if self.cliente is not None:
            return self.cliente
        config = self.config
        contexto = ssl.create_default_context()
        if config.tls == 'SSL':
            cliente = smtplib.SMTP_SSL(config.host, config.puerto, timeout=15, context=contexto)
        else:
            cliente = smtplib.SMTP(config.host, config.puerto, timeout=15)
        try:
            if config.tls == 'STARTTLS':
                cliente.ehlo()
                cliente.starttls(context=contexto)
                cliente.ehlo()
            if config.usuario:
                cliente.login(config.usuario, config.password)
        except (OSError, smtplib.SMTPException):
            cliente.close()
            raise
        self.cliente = cliente
        return cliente

    def enviar(self, mensaje: EmailMessage, destinatario: str) -> None:
        cliente = self._conectar()
        try:
            cliente.send_message(mensaje, from_addr=self.config.remitente, to_addrs=[destinatario])
        except (OSError, smtplib.SMTPException):
            # El estado de la conexión tras un fallo es incierto. El siguiente aviso abre otra.
            self.cliente = None
            cliente.close()
            raise

    def cerrar(self) -> None:
        cliente, self.cliente = self.cliente, None
        if cliente is None:
            return
        try:
            cliente.quit()
        except (OSError, smtplib.SMTPException):
            # El resultado de DATA ya determina si el proveedor aceptó el mensaje.
            pass
        finally:
            cliente.close()


def enviar_mensaje_smtp(
    config: ConfiguracionCorreo,
    *,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    message_id: str | None = None,
    codigo: str | None = None,
    transporte: _TransporteSMTP | None = None,
) -> None:
    """Envía un correo electrónico usando el transporte SMTP configurado (STARTTLS, SSL o LAB_LOOPBACK)."""
    mensaje = EmailMessage()
    mensaje['From'] = formataddr(('Simulador de Psicología Social', config.remitente))
    mensaje['To'] = destinatario
    mensaje['Date'] = formatdate(usegmt=True)
    mensaje['Message-ID'] = message_id or make_msgid(domain=config.remitente.rsplit('@', 1)[1])
    mensaje['Subject'] = asunto
    mensaje.set_content(cuerpo)
    mensaje.add_alternative(renderizar_correo(asunto, cuerpo, config.url_publica, codigo), subtype='html')
    smtp = transporte if transporte is not None else _TransporteSMTP(config)
    try:
        smtp.enviar(mensaje, destinatario)
    finally:
        if transporte is None:
            smtp.cerrar()


def enviar_smtp(config, *, id_notificacion, payload, transporte=None):
    tipo = payload['tipo']
    asunto = _ASUNTOS_POR_TIPO.get(tipo, 'Notificación académica SPS')
    texto = [f"Caso: {payload['caso']}", f"Inicio programado: {payload['inicio']}"]
    if tipo in {'CONVOCATORIA', 'CAMBIO_SESION'}:
        if payload.get('fin'):
            texto.append(f"Fin programado: {payload['fin']}")
        if payload.get('lugar'):
            texto.append(f"Lugar o enlace: {payload['lugar']}")
    texto.extend([payload['mensaje'], f"URL: {config.url_publica}"])
    if tipo == 'CONVOCATORIA':
        texto.insert(0, 'Has sido convocado por tu docente a un caso de simulación en SPS.')
        texto.append(f"Código individual: {payload['codigo']}")
        texto.append('Ingresa a la plataforma en el horario indicado e introduce tu código individual para iniciar la sesión.')
        texto.append('Este código es personal. No lo compartas con otras personas.')
    elif tipo == 'CONVOCATORIA_RETIRADA':
        texto.append('El docente retiró tu autorización para esta sesión.')
    elif tipo == 'CAMBIO_SESION':
        texto.append('Se registraron cambios relevantes en la programación de tu sesión.')
    elif tipo == 'CALIFICACION':
        texto.append('Tus resultados oficiales están disponibles en la plataforma.')
    elif tipo == 'RETROALIMENTACION':
        texto.append('Tu docente registró retroalimentación sobre tu participación.')
    if payload.get('nombre'):
        texto.insert(0, f"Hola {payload['nombre']},")
    enviar_mensaje_smtp(
        config,
        destinatario=payload['correo'],
        asunto=asunto,
        cuerpo='\n'.join(texto),
        message_id=f'<{id_notificacion}@{config.remitente.rsplit("@", 1)[1]}>',
        codigo=payload['codigo'] if tipo == 'CONVOCATORIA' else None,
        transporte=transporte,
    )


def _auditar(db, notificacion, convocatoria, despacho, resultado):
    db.add(EventoAuditoriaModel(id=uuid4(), sesion_id=convocatoria.sesion_id, tipo='DESPACHO_CORREO',
        origen='SISTEMA', descripcion=json.dumps(dict(id_notificacion=str(notificacion.id),
            intento=despacho.intentos, resultado=resultado), sort_keys=True), creado_en=datetime.now(timezone.utc)))


def _despachar_uno(crear_sesion, config, identificador, *, ahora_reintentos=None, transporte=None):
    from cryptography.fernet import Fernet, InvalidToken
    with crear_sesion.begin() as db:
        despacho = db.scalar(select(DespachoCorreoModel).where(
            DespachoCorreoModel.id_notificacion == identificador,
            _filtro_pendientes(ahora_reintentos)).with_for_update(skip_locked=True))
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
            if aviso.tipo == 'CONVOCATORIA' and not coincide_codigo_convocatoria(
                payload['codigo'], convocatoria.codigo_hash, convocatoria.estudiante_id,
            ):
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
            enviar_smtp(config, id_notificacion=aviso.id, payload={**payload, 'nombre': persona.nombre},
                        transporte=transporte)
        except ssl.SSLCertVerificationError:
            despacho.estado = 'REINTENTAR'
            despacho.ultimo_error = 'SMTP_CERTIFICADO_NO_VALIDADO'
        except (InvalidToken, ValueError, KeyError, TypeError):
            despacho.estado = 'REINTENTAR'
            despacho.ultimo_error = 'PAYLOAD_NO_VERIFICABLE'
        except smtplib.SMTPAuthenticationError:
            despacho.estado = 'REINTENTAR'
            despacho.ultimo_error = 'SMTP_AUTENTICACION_RECHAZADA'
        except (OSError, smtplib.SMTPException):
            despacho.estado = 'REINTENTAR'
            despacho.ultimo_error = 'SMTP_NO_CONFIRMADO'
        else:
            despacho.estado = 'ACEPTADO_PROVEEDOR'
            despacho.aceptado_en = datetime.now(timezone.utc)
            despacho.ultimo_error = None
        _auditar(db, aviso, convocatoria, despacho, despacho.estado)
        return despacho.estado


def _filtro_pendientes(ahora_reintentos):
    pendiente = DespachoCorreoModel.estado == 'PENDIENTE'
    reintento = DespachoCorreoModel.estado == 'REINTENTAR'
    if ahora_reintentos is not None:
        intentos = DespachoCorreoModel.intentos
        minutos = case((intentos <= 1, 1), (intentos == 2, 2), (intentos == 3, 4),
                        (intentos == 4, 8), (intentos == 5, 16), (intentos == 6, 32), else_=60)
        reintento = reintento & (
            DespachoCorreoModel.ultimo_intento_en + PAUSA_REINTENTO * minutos <= ahora_reintentos
        )
    return or_(pendiente, reintento)


def despachar_pendientes(crear_sesion, *, limite=20, esperar_reintentos=False):
    """Un lote operativo; cada pendiente se intenta una vez por invocación."""
    if type(limite) is not int or limite <= 0:
        raise ValueError('El tamaño del lote debe ser positivo.')
    config = configuracion_correo()
    if config is None:
        raise IntegracionPendiente()
    ahora_reintentos = datetime.now(timezone.utc) if esperar_reintentos else None
    with crear_sesion() as db:
        if db.get_bind().dialect.name != 'postgresql':
            raise IntegracionPendiente()
        ids = db.scalars(select(DespachoCorreoModel.id_notificacion).where(
            _filtro_pendientes(ahora_reintentos))
            .order_by(DespachoCorreoModel.ultimo_intento_en.asc().nulls_first(),
                      DespachoCorreoModel.id_notificacion).limit(limite)).all()
    resultados = []
    transporte = _TransporteSMTP(config)
    try:
        for identificador in ids:
            resultado = _despachar_uno(crear_sesion, config, identificador,
                                       ahora_reintentos=ahora_reintentos, transporte=transporte)
            resultados.append(resultado)
    finally:
        transporte.cerrar()
    return resultados


def main():
    parser = argparse.ArgumentParser(description='Despacha un lote de correos durables pendientes.')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--test-to-sender', action='store_true',
                        help='Envía un único mensaje de prueba al remitente configurado, sin procesar la cola.')
    args = parser.parse_args()
    try:
        if args.test_to_sender:
            config = configuracion_correo()
            if config is None:
                raise IntegracionPendiente()
            enviar_mensaje_smtp(
                config,
                destinatario=config.remitente,
                asunto='Prueba de correo de SPS',
                cuerpo=f'El servicio de notificaciones de SPS envió este mensaje de prueba.\n'
                       f'Plataforma: {config.url_publica}',
            )
            print('SMTP aceptó el mensaje dirigido al remitente. Confirme que llegó al buzón.')
            return 0
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
