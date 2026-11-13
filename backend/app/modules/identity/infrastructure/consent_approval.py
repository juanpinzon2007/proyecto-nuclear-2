"""Atestación del operador configurado. La aprobación institucional procede externamente.

Formato JSON canónico UTF-8, sort_keys=True, separators=(',', ':'), ensure_ascii=False.
La firma Ed25519 cubre los bytes canónicos de payload. El pin cubre el archivo completo.
La clave pública es base64 estándar de los 32 bytes Ed25519. Nunca se carga clave privada.
"""
import base64
import binascii
from hashlib import sha256
import json
from typing import Annotated, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.scheduling.domain.ingress_policy import fecha_utc


Hash = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
Id = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
Texto = Annotated[str, Field(strict=True, min_length=1)]


class DocumentoAtestado(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id_version_documento: Id
    referencia: Annotated[str, Field(strict=True, min_length=1, max_length=30)]
    documento_id: Texto
    version: Texto
    sha256_texto: Hash
    sha256_original: Hash
    sha256_aprobacion: Hash
    autoridad_aprobadora: Texto
    aprobado_en: AwareDatetime
    publicado_en: AwareDatetime
    vigente_desde: AwareDatetime
    asignaciones: tuple[Id, ...] = Field(min_length=1, max_length=10000)


class Atestacion(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal[1]
    scope: Literal['PRODUCCION', 'LABORATORIO']
    valid_from: AwareDatetime
    expires_at: AwareDatetime
    documentos: tuple[DocumentoAtestado, ...] = Field(min_length=1, max_length=1000)


def canonico(valor):
    return json.dumps(valor, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


class PoliticaConsentimientoAtestado:
    def __init__(self, atestacion):
        self.atestacion = atestacion

    @classmethod
    def desde_settings(cls, settings):
        try:
            if (settings.academic_runtime_scope not in ('PRODUCCION', 'LABORATORIO')
                    or settings.identity_consent_approval_manifest is None
                    or settings.identity_consent_approval_sha256 is None
                    or settings.identity_consent_approval_public_key is None):
                raise ValueError()
            with settings.identity_consent_approval_manifest.open('rb') as archivo:
                contenido = archivo.read(1_048_577)
            if (len(contenido) > 1_048_576
                    or sha256(contenido).hexdigest() != settings.identity_consent_approval_sha256):
                raise ValueError()
            paquete = json.loads(contenido)
            if (type(paquete) is not dict or set(paquete) != {'payload', 'signature'}
                    or canonico(paquete) != contenido):
                raise ValueError()
            clave = base64.b64decode(settings.identity_consent_approval_public_key, validate=True)
            firma = base64.b64decode(paquete['signature'], validate=True)
            Ed25519PublicKey.from_public_bytes(clave).verify(firma, canonico(paquete['payload']))
            atestacion = Atestacion.model_validate(paquete['payload'])
            if (atestacion.scope != settings.academic_runtime_scope
                    or atestacion.valid_from >= atestacion.expires_at
                    or len({d.id_version_documento for d in atestacion.documentos}) != len(atestacion.documentos)
                    or any(d.aprobado_en > d.publicado_en for d in atestacion.documentos)):
                raise ValueError()
            return cls(atestacion)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, ValidationError,
                InvalidSignature, binascii.Error, RecursionError):
            raise IntegracionPendiente() from None

    def autorizar(self, documento, *, id_asignacion, ahora):
        ahora = fecha_utc(ahora)
        a = self.atestacion
        if (type(id_asignacion) is not int or not documento.vigente
                or not a.valid_from <= ahora < a.expires_at):
            raise IntegracionPendiente()
        for d in a.documentos:
            if d.id_version_documento != documento.id_version_documento:
                continue
            iguales = (
                d.referencia == documento.referencia,
                d.documento_id == documento.documento_id,
                d.version == documento.version,
                d.sha256_texto == documento.huella,
                d.sha256_original == documento.sha256_original,
                d.sha256_aprobacion == documento.sha256_aprobacion,
                d.autoridad_aprobadora == documento.autoridad_aprobadora,
                d.aprobado_en == documento.aprobado_en,
                d.publicado_en == documento.publicado_en,
                d.vigente_desde == documento.vigente_desde,
                id_asignacion in d.asignaciones,
                ahora >= d.publicado_en,
                ahora >= d.vigente_desde,
            )
            if all(iguales):
                return None
            break
        raise IntegracionPendiente()
