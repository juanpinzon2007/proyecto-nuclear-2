"""Contrato del servidor para vincular P; no contiene políticas de laboratorio."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.participation.application.integration_ports import ContextoVinculadoParticipacion
from app.modules.participation.domain.entities import Participacion


@dataclass(frozen=True)
class CondicionesVinculacion:
    contexto: ContextoVinculadoParticipacion
    ahora: datetime
    estado_asignacion: str
    apertura: datetime
    cierre: datetime
    limite_ingreso: datetime
    existente: Participacion | None


class PoliticaVinculacionParticipacion(Protocol):
    def autorizar(self, condiciones: CondicionesVinculacion) -> str:
        """Autoriza la vinculación y devuelve el estado inicial explícito de P.

        Requiere una decisión sobre provisión/estado, no basta con login válido.
        En una P existente autoriza recuperar, sin cambiar su estado histórico.
        Sin proveedor no se crea ni devuelve una participación. Nunca recibe
        estado, estudiante o políticas elegidos por HTTP.
        """
        ...


@dataclass(frozen=True)
class VinculacionParticipacion:
    participacion: Participacion
    creada: bool
