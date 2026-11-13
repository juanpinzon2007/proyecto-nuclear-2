"""Resultado operativo de una orden docente explícita, separado de la nota."""
from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class IntentoRecuperado:
    id_intento: int
    estado: Literal['DISPONIBLE', 'PENDIENTE']
    id_resultado: int | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class RecuperacionCierres:
    id_sesion: UUID
    intentos: tuple[IntentoRecuperado, ...]
