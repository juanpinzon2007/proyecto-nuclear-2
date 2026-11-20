"""Verificación única por código enviado al correo en el primer inicio de sesión estudiantil."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import logging
import secrets
import smtplib

from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.onboarding_models import VerificacionPrimerIngresoORM
from app.modules.scheduling.infrastructure.mail_delivery import (
    configuracion_correo,
    enviar_mensaje_smtp,
)

logger = logging.getLogger(__name__)
TTL_CODIGO_PRIMER_INGRESO_SEGUNDOS = 900
MAX_INTENTOS_CODIGO_PRIMER_INGRESO = 5


def _como_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC)


def enviar_correo_directo(*, destinatario: str, asunto: str, generar_cuerpo: Callable[[str], str]) -> None:
    """Envía un correo transaccional inmediato usando la configuración SMTP activa."""
    config = configuracion_correo()
    if config is None:
        raise IntegracionPendiente()
    try:
        enviar_mensaje_smtp(
            config,
            destinatario=destinatario,
            asunto=asunto,
            cuerpo=generar_cuerpo(config.url_publica),
        )
    except (OSError, smtplib.SMTPException) as error:
        logger.warning("Fallo al enviar correo transaccional SMTP (%s): %s", type(error).__name__, error)
        raise IntegracionPendiente() from None


def estado_primer_ingreso(db: Session, *, id_usuario: int) -> bool:
    """Devuelve True si el usuario ya completó o no requiere verificación de primer ingreso."""
    try:
        with db.begin_nested():
            fila = db.scalar(
                select(VerificacionPrimerIngresoORM).where(VerificacionPrimerIngresoORM.id_usuario == id_usuario)
            )
            return True if fila is None else bool(fila.verificado)
    except SQLAlchemyError:
        # Compatibilidad con esquemas históricos previos a la migración 20261119.
        return True


def registrar_estado_primer_ingreso(
    db: Session,
    *,
    id_usuario: int,
    verificado: bool,
) -> VerificacionPrimerIngresoORM:
    """Crea o actualiza el estado de verificación única de primer ingreso."""
    ahora = datetime.now(UTC)
    fila = db.scalar(
        select(VerificacionPrimerIngresoORM)
        .where(VerificacionPrimerIngresoORM.id_usuario == id_usuario)
        .with_for_update()
    )
    if fila is None:
        fila = VerificacionPrimerIngresoORM(
            id_usuario=id_usuario,
            verificado=verificado,
            verificado_en=ahora if verificado else None,
            creado_en=ahora,
        )
        db.add(fila)
    else:
        fila.verificado = verificado
        fila.verificado_en = ahora if verificado else None
        fila.codigo_hash = None
        fila.expira_en = None
        fila.intentos = 0
    db.flush()
    return fila


def enviar_codigo_primer_ingreso_smtp(*, correo: str, nombre: str, codigo: str) -> None:
    """Envía por SMTP el código de un solo uso para el primer inicio de sesión del estudiante."""
    enviar_correo_directo(
        destinatario=correo,
        asunto="Código de verificación de primer ingreso - SPS",
        generar_cuerpo=lambda url_publica: "\n".join(
            [
                f"Hola {nombre},",
                "",
                "Tu cuenta estudiantil en el Simulador de Psicología Social (SPS) fue habilitada.",
                f"Código de verificación: {codigo}",
                "",
                "Ingresa este código en la plataforma para completar tu primer inicio de sesión.",
                "Este código vence en 15 minutos y solo se solicitará la primera vez que ingreses.",
                f"Plataforma: {url_publica}",
            ]
        ),
    )


def generar_y_enviar_codigo_primer_ingreso(
    db: Session,
    *,
    id_usuario: int,
    correo: str,
    nombre: str,
    remitente_correo: Callable[..., None] = enviar_codigo_primer_ingreso_smtp,
) -> int:
    """Genera un OTP de 6 dígitos, lo persiste cifrado con hash y lo envía por correo."""
    ahora = datetime.now(UTC)
    fila = db.scalar(
        select(VerificacionPrimerIngresoORM)
        .where(VerificacionPrimerIngresoORM.id_usuario == id_usuario)
        .with_for_update()
    )
    if fila is None:
        fila = VerificacionPrimerIngresoORM(
            id_usuario=id_usuario,
            verificado=False,
            creado_en=ahora,
        )
        db.add(fila)

    codigo = f"{secrets.randbelow(1_000_000):06d}"
    fila.verificado = False
    fila.verificado_en = None
    fila.codigo_hash = obtener_hasheador().hash(codigo)
    fila.expira_en = ahora + timedelta(seconds=TTL_CODIGO_PRIMER_INGRESO_SEGUNDOS)
    fila.intentos = 0
    db.flush()

    remitente_correo(correo=correo, nombre=nombre, codigo=codigo)
    return TTL_CODIGO_PRIMER_INGRESO_SEGUNDOS


def verificar_codigo_primer_ingreso(db: Session, *, id_usuario: int, codigo: str) -> bool:
    """Valida el código de primer ingreso y marca la cuenta como verificada permanentemente."""
    ahora = datetime.now(UTC)
    fila = db.scalar(
        select(VerificacionPrimerIngresoORM)
        .where(VerificacionPrimerIngresoORM.id_usuario == id_usuario)
        .with_for_update()
    )
    if fila is None or fila.verificado or not fila.codigo_hash or fila.expira_en is None:
        return False
    if _como_utc(fila.expira_en) <= ahora or fila.intentos >= MAX_INTENTOS_CODIGO_PRIMER_INGRESO:
        return False

    try:
        coincide = obtener_hasheador().verify(codigo.strip(), fila.codigo_hash)
    except UnknownHashError:
        coincide = False

    if not coincide:
        fila.intentos += 1
        if fila.intentos >= MAX_INTENTOS_CODIGO_PRIMER_INGRESO:
            fila.codigo_hash = None
            fila.expira_en = None
        db.flush()
        return False

    fila.verificado = True
    fila.verificado_en = ahora
    fila.codigo_hash = None
    fila.expira_en = None
    fila.intentos = 0
    db.flush()
    return True
