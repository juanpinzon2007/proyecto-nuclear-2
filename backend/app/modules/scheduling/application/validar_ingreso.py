
"""Validación de ingreso de estudiantes a sesiones académicas."""

import hashlib
import hmac

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    SesionProgramadaModel,
)


class ErrorIngreso(ValueError):
    """El estudiante no cumple las condiciones de acceso."""
    pass


def validar_ingreso(
    db: Session,
    *,
    convocatoria_id: UUID,
    estudiante_id: UUID,
    codigo_acceso: str,
    tolerancia_minutos: int,
    ahora: datetime | None = None,
) -> SesionProgramadaModel:
    """Verifica código, convocatoria, estado y horario."""

    if type(tolerancia_minutos) is not int or tolerancia_minutos < 0:
        raise ValueError("La tolerancia de ingreso es inválida.")

    if ahora is None:
        ahora = datetime.now(timezone.utc)

    if ahora.utcoffset() is None:
        raise ValueError("La fecha debe incluir zona horaria.")

    # Validar la convocatoria.
    convocatoria = db.get(
        ConvocatoriaModel,
        convocatoria_id,
    )

    if (
        convocatoria is None
        or convocatoria.estado != "ACTIVA"
        or convocatoria.estudiante_id != estudiante_id
    ):
        raise ErrorIngreso("Acceso no autorizado.")

    # Verificar el código generado durante la convocatoria.
    codigo_hash = hashlib.sha256(
        codigo_acceso.encode("utf-8")
    ).hexdigest()

    if not hmac.compare_digest(
        codigo_hash,
        convocatoria.codigo_hash,
    ):
        raise ErrorIngreso("Acceso no autorizado.")

    # Comprobar la sesión académica.
    sesion = db.get(
        SesionProgramadaModel,
        convocatoria.sesion_id,
    )

    if sesion is None:
        raise ErrorIngreso("La sesión no existe.")

    if sesion.estado != "EN_CURSO":
        raise ErrorIngreso("La sesión no está en curso.")

    if ahora < sesion.fecha_inicio:
        raise ErrorIngreso("La sesión todavía no comienza.")

    limite_ingreso = min(
        sesion.fecha_inicio + timedelta(minutes=tolerancia_minutos),
        sesion.fecha_fin,
    )

    if ahora > limite_ingreso:
        raise ErrorIngreso(
            "Se superó el tiempo permitido de ingreso."
        )

    return sesion
