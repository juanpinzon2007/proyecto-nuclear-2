"""Representación del código existente; nunca incluye el código en diagnósticos."""

import hashlib
import hmac


def hash_codigo(codigo: str) -> str:
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


def coincide_codigo(codigo: str, guardado: str) -> bool:
    return hmac.compare_digest(hash_codigo(codigo), guardado)
