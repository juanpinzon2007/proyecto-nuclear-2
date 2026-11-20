"""Recuperación de contraseña mediante código temporal enviado al correo electrónico."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import secrets

from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.onboarding import _como_utc, enviar_correo_directo
from app.modules.identity.infrastructure.password_reset_models import RecuperacionContrasenaORM

TTL_CODIGO_RECUPERACION_SEGUNDOS = 900
MAX_INTENTOS_CODIGO_RECUPERACION = 5


def enviar_codigo_recuperacion_smtp(*, correo: str, nombre: str, codigo: str) -> None:
    """Envía por SMTP el código temporal para restablecer la contraseña."""
    enviar_correo_directo(
        destinatario=correo,
        asunto="Recuperación de contraseña - SPS",
        generar_cuerpo=lambda url_publica: "\n".join(
            [
                f"Hola {nombre},",
                "",
                "Recibimos una solicitud para restablecer tu contraseña en SPS.",
                f"Código de recuperación: {codigo}",
                "",
                "Ingresa este código en la pantalla de recuperación junto con tu nueva contraseña.",
                "Este código vence en 15 minutos. Si no solicitaste el cambio, ignora este mensaje.",
                f"Plataforma: {url_publica}",
            ]
        ),
    )


def generar_y_enviar_codigo_recuperacion(
    db: Session,
    *,
    id_usuario: int,
    correo: str,
    nombre: str,
    remitente_correo: Callable[..., None] = enviar_codigo_recuperacion_smtp,
) -> int:
    """Genera y almacena un código temporal de 6 dígitos para recuperar contraseña y lo envía por correo."""
    ahora = datetime.now(UTC)
    fila = db.scalar(
        select(RecuperacionContrasenaORM)
        .where(RecuperacionContrasenaORM.id_usuario == id_usuario)
        .with_for_update()
    )
    if fila is None:
        fila = RecuperacionContrasenaORM(id_usuario=id_usuario)
        db.add(fila)

    codigo = f"{secrets.randbelow(1_000_000):06d}"
    fila.codigo_hash = obtener_hasheador().hash(codigo)
    fila.expira_en = ahora + timedelta(seconds=TTL_CODIGO_RECUPERACION_SEGUNDOS)
    fila.intentos = 0
    fila.solicitado_en = ahora
    db.flush()

    remitente_correo(correo=correo, nombre=nombre, codigo=codigo)
    return TTL_CODIGO_RECUPERACION_SEGUNDOS


def confirmar_recuperacion_contrasena(
    db: Session,
    *,
    id_usuario: int,
    codigo: str,
    nueva_clave: str,
) -> bool:
    """Valida el código de recuperación y actualiza la contraseña del usuario."""
    ahora = datetime.now(UTC)
    fila = db.scalar(
        select(RecuperacionContrasenaORM)
        .where(RecuperacionContrasenaORM.id_usuario == id_usuario)
        .with_for_update()
    )
    if fila is None or not fila.codigo_hash or fila.expira_en is None:
        return False
    if _como_utc(fila.expira_en) <= ahora or fila.intentos >= MAX_INTENTOS_CODIGO_RECUPERACION:
        return False

    try:
        coincide = obtener_hasheador().verify(codigo.strip(), fila.codigo_hash)
    except UnknownHashError:
        coincide = False

    if not coincide:
        fila.intentos += 1
        if fila.intentos >= MAX_INTENTOS_CODIGO_RECUPERACION:
            fila.codigo_hash = None
            fila.expira_en = None
        db.flush()
        return False

    usuario = db.get(UsuarioORM, id_usuario, with_for_update=True, populate_existing=True)
    if usuario is None or not usuario.activo:
        return False

    usuario.clave_hash = obtener_hasheador().hash(nueva_clave)
    fila.codigo_hash = None
    fila.expira_en = None
    fila.intentos = 0
    fila.completado_en = ahora
    db.flush()
    return True
