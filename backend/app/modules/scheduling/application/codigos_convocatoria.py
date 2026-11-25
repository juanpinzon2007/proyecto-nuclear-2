"""Huellas de códigos de convocatoria, con lectura de las convocatorias anteriores."""

import hmac
from uuid import UUID

from app.core.config import get_settings
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.scheduling.domain.access_codes import hash_codigo


class CorreoConvocatoriaNoDisponible(IntegracionPendiente):
    pass


def _clave_codigos() -> bytes | None:
    clave = get_settings().scheduling_mail_encryption_key
    if not clave:
        return None
    return hmac.digest(clave.get_secret_value().encode(), b"sps:convocatoria:codigo:v2", "sha256")


def _huella_numerica(codigo: str, estudiante_id: UUID, clave: bytes) -> str:
    mensaje = estudiante_id.bytes + codigo.encode("ascii")
    return "v2$" + hmac.digest(clave, mensaje, "sha256").hex()


def hash_codigo_numerico(codigo: str, estudiante_id: UUID) -> str:
    clave = _clave_codigos()
    if clave is None:
        raise CorreoConvocatoriaNoDisponible()
    return _huella_numerica(codigo, estudiante_id, clave)


def huellas_de_consulta(codigo: str, estudiante_id: UUID) -> tuple[str, ...]:
    anterior = hash_codigo(codigo)
    if len(codigo) == 6 and codigo.isascii() and codigo.isdecimal():
        clave = _clave_codigos()
        if clave is not None:
            return _huella_numerica(codigo, estudiante_id, clave), anterior
    return (anterior,)


def coincide_codigo_convocatoria(codigo: str, guardado: str, estudiante_id: UUID) -> bool:
    return any(hmac.compare_digest(huella, guardado) for huella in huellas_de_consulta(codigo, estudiante_id))
