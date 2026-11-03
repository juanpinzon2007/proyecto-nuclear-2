"""Mecánica temporal; no contiene una fórmula ni tolerancia académica por defecto."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID


class PoliticaTemporalNoDisponible(Exception):
    """Política ausente o datos temporales insuficientes/incoherentes."""


def fecha_utc(valor: datetime) -> datetime:
    if not isinstance(valor, datetime) or valor.utcoffset() is None:
        raise PoliticaTemporalNoDisponible()
    return valor.astimezone(timezone.utc)


@dataclass(frozen=True)
class VentanaIngreso:
    apertura: datetime
    cierre: datetime
    incluye_apertura: bool
    incluye_cierre: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "apertura", fecha_utc(self.apertura))
        object.__setattr__(self, "cierre", fecha_utc(self.cierre))
        if (self.cierre < self.apertura or type(self.incluye_apertura) is not bool
                or type(self.incluye_cierre) is not bool):
            raise PoliticaTemporalNoDisponible()

    def contiene(self, instante: datetime) -> bool:
        instante = fecha_utc(instante)
        return ((instante > self.apertura or self.incluye_apertura and instante == self.apertura)
                and (instante < self.cierre or self.incluye_cierre and instante == self.cierre))


class PoliticaIngreso(Protocol):
    def obtener_ventana(self, *, id_sesion: UUID, inicio: datetime, fin: datetime) -> VentanaIngreso:
        """Fuente autorizada del servidor; jamás datos del comando estudiantil."""
        ...


class PoliticaIngresoNoConfigurada:
    def obtener_ventana(self, *, id_sesion: UUID, inicio: datetime, fin: datetime) -> VentanaIngreso:
        raise PoliticaTemporalNoDisponible()


class RelojIngreso(Protocol):
    def ahora(self) -> datetime: ...


class RelojServidor:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)
