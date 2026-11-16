"""Mecánica temporal; no contiene una fórmula ni tolerancia académica por defecto."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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


class AutorizacionAdmision(Protocol):
    def autorizar(self, *, convocatoria_id:UUID, estudiante_id:UUID,
                  sesion_id:UUID, version_id:UUID) -> None: ...


class PoliticaIngresoNoConfigurada:
    def obtener_ventana(self, *, id_sesion: UUID, inicio: datetime, fin: datetime) -> VentanaIngreso:
        raise PoliticaTemporalNoDisponible()


class RelojIngreso(Protocol):
    def ahora(self) -> datetime: ...


class RelojServidor:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)


def calcular_limite_ingreso_mitad_tiempo(
    *,
    inicio: datetime,
    fin: datetime,
    tiempo_maximo_minutos: int,
    fecha_limite_explicita: datetime | None = None,
) -> datetime:
    """Calcula el límite operativo RF-22: 50% del tiempo máximo asignado desde fecha_inicio."""
    inicio_utc = fecha_utc(inicio)
    fin_utc = fecha_utc(fin)
    mitad_minutos = max(1.0, float(tiempo_maximo_minutos) / 2.0)
    mitad = inicio_utc + timedelta(minutes=mitad_minutos)
    cierre = min(fin_utc, mitad)
    if fecha_limite_explicita is not None:
        cierre = min(cierre, fecha_utc(fecha_limite_explicita))
    if cierre < inicio_utc:
        return inicio_utc
    return cierre


class PoliticaIngresoMitadTiempo:
    """Política RF-22: restringe ingreso tardío al 50% del tiempo máximo asignado."""

    def __init__(
        self,
        *,
        tiempo_maximo_minutos: int,
        fecha_limite_explicita: datetime | None = None,
    ) -> None:
        if tiempo_maximo_minutos <= 0:
            raise PoliticaTemporalNoDisponible()
        self.tiempo_maximo_minutos = tiempo_maximo_minutos
        self.fecha_limite_explicita = fecha_limite_explicita

    def obtener_ventana(self, *, id_sesion: UUID, inicio: datetime, fin: datetime) -> VentanaIngreso:
        inicio_utc = fecha_utc(inicio)
        cierre = calcular_limite_ingreso_mitad_tiempo(
            inicio=inicio_utc,
            fin=fin,
            tiempo_maximo_minutos=self.tiempo_maximo_minutos,
            fecha_limite_explicita=self.fecha_limite_explicita,
        )
        return VentanaIngreso(
            apertura=inicio_utc,
            cierre=cierre,
            incluye_apertura=True,
            incluye_cierre=True,
        )
