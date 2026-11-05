"""Proyección pública mínima de la pregunta habilitada, sin datos de evaluación."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class OpcionActual:
    id: UUID
    texto: str


@dataclass(frozen=True)
class PreguntaActual:
    id: UUID
    enunciado: str
    opciones: tuple[OpcionActual, ...]


@dataclass(frozen=True)
class EscenarioActual:
    id_escenario: UUID | None
    contexto: str | None
    pregunta: PreguntaActual | None
    recorrido_finalizado: bool
    respondidas: int
