"""Datos del servidor para decisiones de inicio todavía sin política por defecto."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CondicionesInicioIntento:
    id_participacion: int
    id_estudiante: int
    sesion_id: UUID
    version_id: UUID
    rubrica_id: UUID
    version_regla: str
    estado_asignacion: str
    apertura: datetime
    cierre: datetime
    limite_ingreso: datetime
    ahora: datetime
    version_consentimiento: str
    aceptado_en: datetime
    numero_intento: int
    intentos_base: int
    id_permiso_extra: int | None
    cantidad_extra: int | None
    usos_permiso: int


class PoliticaInicioIntento(Protocol):
    def autorizar(self, condiciones: CondicionesInicioIntento) -> None:
        """Exige regla explícita de consentimiento/aplicabilidad, asignación y cupos.

        Datos bloqueados de la misma transacción; no una autorización previamente
        calculada ni valores elegidos por HTTP. None significa autorización;
        cualquier otro retorno es un contrato inválido. Ausencia de proveedor
        mantiene el inicio cerrado. No existe una implementación permisiva aquí.
        """
        ...
