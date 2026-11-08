"""RF-16: exportación de una publicación inmutable, sin cálculo académico."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente


@dataclass(frozen=True)
class FiltrosReporte:
    version_publicacion: int | None = None
    id_grupo: int | None = None
    estudiantes: tuple[int, ...] = ()
    estado: str | None = None
    agrupar_por: Literal['grupo', 'estudiante'] = 'grupo'


@dataclass(frozen=True)
class PublicacionReporte:
    id: UUID
    sesion_id: UUID
    version: int
    sha256: str
    publicada_en: datetime
    generada_en: datetime
    caso: str
    version_caso_id: UUID
    filas: tuple[dict, ...]
    retiradas: tuple[str, ...]
    filtros: FiltrosReporte


@dataclass(frozen=True)
class ArchivoReporte:
    contenido: bytes
    media_type: str
    nombre: str
    publicacion_id: UUID
    version: int
    sha256: str


class LectorPublicacion(Protocol):
    def consultar(self, id_sesion: UUID, filtros: FiltrosReporte) -> PublicacionReporte: ...


class ServicioReporteOficial:
    def __init__(self, lector: LectorPublicacion, exportador):
        self.lector, self.exportador = lector, exportador

    def descargar(self, id_sesion: str, formato: str, filtros: FiltrosReporte) -> ArchivoReporte:
        try:
            sid = UUID(id_sesion)
        except (ValueError, TypeError):
            raise AccesoDenegado() from None
        if formato not in {'xlsx', 'pdf'}:
            raise IntegracionPendiente()
        fuente = self.lector.consultar(sid, filtros)
        try:
            return self.exportador.exportar(fuente, formato)
        except Exception:
            # No exponer contenido del reporte ni mensajes internos del generador.
            raise IntegracionPendiente() from None
