from uuid import UUID
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EventoAcademico:
    tipo: str
    entidad_id: UUID


class ObservadorAcademico(Protocol):

    async def notificar(self, evento: EventoAcademico) -> None:
        ...


class ObservadorTransaccional(Protocol):
    """Efectos locales, secuenciales y sin commit sobre la unidad recibida."""

    def preparar(self, evento: EventoAcademico, transaccion: Any) -> None:
        ...


class GestorEventosAcademicos:

    def __init__(self):
        self._observadores = defaultdict(list)
        self._transaccionales = defaultdict(list)

    def suscribir_transaccional(self, tipo: str, observador: ObservadorTransaccional):
        self._transaccionales[tipo].append(observador)

    def preparar(self, evento: EventoAcademico, transaccion: Any) -> None:
        # Una Session no admite uso concurrente ni commits de los observadores.
        for observador in self._transaccionales[evento.tipo]:
            observador.preparar(evento, transaccion)

    def suscribir(self, tipo: str, observador: ObservadorAcademico):
        self._observadores[tipo].append(observador)

    async def publicar(self, evento: EventoAcademico):
        """Solo callbacks efímeros; retornar no acredita efectos SQL ni entrega."""
        observadores = self._observadores[evento.tipo]

        await asyncio.gather(
            *(obs.notificar(evento) for obs in observadores)
        )
