
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EventoAcademico:
    tipo: str
    entidad_id: int


class ObservadorAcademico(Protocol):

    async def notificar(self, evento: EventoAcademico) -> None:
        ...


class GestorEventosAcademicos:

    def __init__(self):
        self._observadores = defaultdict(list)

    def suscribir(self, tipo: str, observador: ObservadorAcademico):
        self._observadores[tipo].append(observador)

    async def publicar(self, evento: EventoAcademico):
        observadores = self._observadores[evento.tipo]

        await asyncio.gather(
            *(obs.notificar(evento) for obs in observadores)
        )
