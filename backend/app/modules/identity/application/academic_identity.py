"""Contrato de lectura propuesto; no crea vínculos ni presupone UUID compartidos."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente


class SistemaAcademico(StrEnum):
    CASES = "CASES"
    SCHEDULING = "SCHEDULING"


@dataclass(frozen=True)
class VinculoAcademico:
    id_usuario: str
    sistema: SistemaAcademico
    id_academico: UUID


class ConsultaVinculosAcademicos(Protocol):
    def obtener(self, *, id_usuario: str, sistema: SistemaAcademico) -> tuple[VinculoAcademico, ...]:
        """Solo asociaciones verificadas existentes; no fabricar ni elegir duplicados.

        Debe garantizar también que el UUID no pertenece a otro usuario dentro
        del mismo sistema. Fallos/ambigüedades de esa integridad: IntegracionPendiente.
        """
        ...


class RegistroVinculosAcademicos(Protocol):
    def agregar_verificado(self, vinculo: VinculoAcademico) -> None:
        """Registro interno autorizado, sin upsert, generación ni commit propio.

        Permite varios UUID por cuenta/sistema; resolverlos sigue exigiendo uno.
        La PK por sistema/UUID impide propietarios distintos para el mismo UUID.
        """
        ...


class ResolverIdentidadAcademica:
    def __init__(self, consulta: ConsultaVinculosAcademicos) -> None:
        self._consulta = consulta

    def resolver(self, *, id_usuario: str, sistema: SistemaAcademico) -> UUID:
        vinculos = self._consulta.obtener(id_usuario=id_usuario, sistema=sistema)
        if not isinstance(vinculos, tuple):
            raise IntegracionPendiente()
        if not vinculos:
            raise AccesoDenegado()
        if len(vinculos) != 1:
            raise IntegracionPendiente()
        vinculo = vinculos[0]
        if (not isinstance(vinculo, VinculoAcademico) or vinculo.id_usuario != id_usuario
                or not isinstance(vinculo.sistema, SistemaAcademico) or vinculo.sistema != sistema
                or not isinstance(vinculo.id_academico, UUID) or vinculo.id_academico.int == 0):
            raise IntegracionPendiente()
        return vinculo.id_academico
