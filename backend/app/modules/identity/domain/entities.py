"""Valores de aplicación; los modelos físicos del DBML viven en Infrastructure.

Los identificadores públicos son cadenas opacas. Su adaptación a los tipos del ER
corresponde a los adaptadores. Usuario usa INTEGER según el DBML; no se deducen
equivalencias entre usuario, membresía, participación, sesión y asignación.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
import re

from app.modules.identity.domain.errors import ReglaIdentidadInvalida


class Rol(StrEnum):
    ADMINISTRADOR = "ADMINISTRADOR"
    DOCENTE = "DOCENTE"
    ESTUDIANTE = "ESTUDIANTE"


def validar_id(valor: str) -> None:
    if not isinstance(valor, str) or not valor.strip() or len(valor) > 200:
        raise ReglaIdentidadInvalida()
    if any(ord(caracter) < 33 or ord(caracter) == 127 for caracter in valor):
        raise ReglaIdentidadInvalida()


def normalizar_correo(correo: str) -> str:
    correo = correo.strip().casefold()
    if len(correo) > 254 or not re.fullmatch(r"[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+", correo):
        raise ReglaIdentidadInvalida()
    local, dominio = correo.split("@")
    if len(local) > 64 or local.startswith(".") or local.endswith(".") or ".." in local:
        raise ReglaIdentidadInvalida()
    if not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", dominio):
        raise ReglaIdentidadInvalida()
    return correo


@dataclass(frozen=True)
class ContextoAcceso:
    """Identidad recuperada por el servidor; nunca se recibe como cuerpo HTTP."""

    id_usuario: str
    correo: str
    roles: frozenset[Rol]
    permisos: frozenset[str] = frozenset()
    activo: bool = True
    id_convocatoria: str | None = None

    def __post_init__(self) -> None:
        validar_id(self.id_usuario)
        if not isinstance(self.roles, frozenset) or any(not isinstance(r, Rol) for r in self.roles):
            raise ReglaIdentidadInvalida()
        if not isinstance(self.permisos, frozenset) or type(self.activo) is not bool:
            raise ReglaIdentidadInvalida()
        if self.id_convocatoria is not None:
            validar_id(self.id_convocatoria)


@dataclass(frozen=True)
class AccesoConvocatoria:
    id_usuario: str
    id_convocatoria: str


@dataclass(frozen=True)
class AutorizacionesDocente:
    roles: frozenset[Rol]
    permisos: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.roles, frozenset) or not isinstance(self.permisos, frozenset):
            raise ReglaIdentidadInvalida()
        if Rol.DOCENTE not in self.roles or any(not isinstance(r, Rol) for r in self.roles):
            raise ReglaIdentidadInvalida()


@dataclass(frozen=True)
class DatosAltaDocente:
    nombre: str
    clave_hash: str = field(repr=False)


@dataclass(frozen=True)
class ResumenCaso:
    id_caso: str
    nombre: str
    version_caso_id: str | None = None


@dataclass(frozen=True)
class RespuestaSeguimiento:
    id_pregunta: str
    id_opcion: str | None
    retroalimentacion: str | None
    id_intento: str | None = None
    numero_paso: int | None = None
    reflexion_estudiante: str | None = None


@dataclass(frozen=True)
class IntentoSeguimiento:
    id_intento: str
    numero_intento: int
    estado: str
    inicio: datetime
    fin: datetime | None
    respondidas: int


@dataclass(frozen=True)
class ResumenParticipacion:
    id_participacion: str
    id_estudiante: str
    id_caso: str
    version_caso_id: str
    id_convocatoria: str
    id_sesion: str
    estado: str


@dataclass(frozen=True)
class DetalleParticipacion:
    id_participacion: str
    id_estudiante: str
    id_caso: str
    respuestas: tuple[RespuestaSeguimiento, ...]
    feedback_docente: str | None
    intentos: tuple[IntentoSeguimiento, ...] = ()
    version_caso_id: str | None = None
    id_convocatoria: str | None = None
    id_sesion: str | None = None
    estado: str | None = None


class EstadoReporte(StrEnum):
    COMPLETA = "COMPLETA"
    PARCIAL = "PARCIAL"
    AUSENCIA = "AUSENCIA"


@dataclass(frozen=True)
class FilaReporte:
    """Estado y nota ya determinados por los módulos académicos responsables."""

    id_estudiante: str
    id_participacion: str | None
    estado: EstadoReporte
    nota: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.estado, EstadoReporte):
            raise ReglaIdentidadInvalida()
        if self.nota is not None and (not isinstance(self.nota, Decimal) or not self.nota.is_finite()):
            raise ReglaIdentidadInvalida()


@dataclass(frozen=True)
class CondicionesRepeticion:
    es_docente_creador: bool
    existe_participacion: bool
    sesion_finalizada: bool

    def __post_init__(self) -> None:
        if any(type(valor) is not bool for valor in (
            self.es_docente_creador, self.existe_participacion, self.sesion_finalizada,
        )):
            raise ReglaIdentidadInvalida()


@dataclass(frozen=True)
class AutorizacionRepeticion:
    id_sesion: str
    id_estudiante: str
    id_docente_autorizador: str
    fecha_autorizacion: datetime
    id_permiso_extra: int | None = None


@dataclass(frozen=True)
class FeedbackDocente:
    id_participacion: str
    id_docente: str
    texto: str
    fecha: datetime

    def __post_init__(self) -> None:
        if not self.texto.strip() or len(self.texto) > 10_000 or "\x00" in self.texto:
            raise ReglaIdentidadInvalida()
