"""Contrato de lectura administrativa; no concede acceso a recursos académicos."""
from dataclasses import dataclass
from typing import Protocol

from app.modules.identity.domain.entities import ContextoAcceso


@dataclass(frozen=True)
class CuentaDocente:
    id_usuario: str
    nombre: str
    correo: str
    activo: bool


@dataclass(frozen=True)
class PaginaDocentes:
    docentes: tuple[CuentaDocente, ...]
    total: int
    limite: int
    desplazamiento: int


class ConsultaDocentes(Protocol):
    def consultar(self, contexto: ContextoAcceso, *, limite: int, desplazamiento: int) -> PaginaDocentes: ...
