"""Contrato interno de documentos, sin documento ni proveedor oficial implícitos."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol

from app.modules.identity.domain.errors import IntegracionPendiente


@dataclass(frozen=True)
class DocumentoConsentimiento:
    referencia: str  # Clave estable de definición histórica; cabe en version_texto.
    documento_id: str
    version: str
    texto: str
    vigente: bool
    id_version_documento: int | None = None  # Solo procede del registro SQL verificado.

    def __post_init__(self):
        if (not all(type(v) is str and v.strip() for v in
                    (self.referencia,self.documento_id,self.version,self.texto))
                or len(self.referencia)>30 or type(self.vigente) is not bool
                or (self.id_version_documento is not None and
                    (type(self.id_version_documento) is not int or self.id_version_documento<=0))):
            raise IntegracionPendiente()

    @property
    def huella(self) -> str:
        return sha256(self.texto.encode('utf-8')).hexdigest()


class FuenteConsentimiento(Protocol):
    def vigente(self, *, id_asignacion: int, ahora: datetime) -> DocumentoConsentimiento:
        """Resuelve ámbito del servidor, nunca versión elegida por el cliente.

        La referencia identifica bytes/documento/version inmutables y recuperables
        históricamente. No se reutiliza una referencia para otra definición.
        Fuente ausente/ambigua o sin documento aprobado falla cerrada.
        """
        ...
