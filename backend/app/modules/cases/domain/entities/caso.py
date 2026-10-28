"""Entidades de dominio del agregado Caso (independientes de SQLAlchemy)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, NoReturn

from app.modules.cases.domain.enums import EstadoCaso

if TYPE_CHECKING:
    from app.modules.cases.domain.validators.base import ValidadorCaso


def _nuevo_id() -> uuid.UUID:
    return uuid.uuid4()


@dataclass(slots=True)
class OpcionRespuesta:
    orden: int
    texto: str
    es_correcta: bool
    justificacion: str
    id: uuid.UUID = field(default_factory=_nuevo_id)
    # criterio_id -> puntaje (Valoracion_Opcion)
    valoraciones: dict[uuid.UUID, Decimal] = field(default_factory=dict)

    @property
    def tiene_justificacion(self) -> bool:
        return bool(self.justificacion and self.justificacion.strip())


@dataclass(slots=True)
class Pregunta:
    orden: int
    enunciado: str
    id: uuid.UUID = field(default_factory=_nuevo_id)
    opciones: list[OpcionRespuesta] = field(default_factory=list)

    @property
    def correctas(self) -> list[OpcionRespuesta]:
        return [o for o in self.opciones if o.es_correcta]

    @property
    def incorrectas(self) -> list[OpcionRespuesta]:
        return [o for o in self.opciones if not o.es_correcta]


@dataclass(slots=True)
class Escenario:
    orden: int
    contexto_situacional: str
    id: uuid.UUID = field(default_factory=_nuevo_id)
    preguntas: list[Pregunta] = field(default_factory=list)


@dataclass(slots=True)
class NivelRubrica:
    nombre: str
    puntaje: Decimal
    descriptor: str
    id: uuid.UUID = field(default_factory=_nuevo_id)


@dataclass(slots=True)
class CriterioRubrica:
    nombre: str
    peso: Decimal
    id: uuid.UUID = field(default_factory=_nuevo_id)
    niveles: list[NivelRubrica] = field(default_factory=list)


@dataclass(slots=True)
class Rubrica:
    nombre: str
    version_regla: str
    id: uuid.UUID = field(default_factory=_nuevo_id)
    criterios: list[CriterioRubrica] = field(default_factory=list)

    @property
    def peso_total(self) -> Decimal:
        return sum((c.peso for c in self.criterios), Decimal(0))


@dataclass(slots=True)
class VersionCaso:
    """Raíz del agregado: encapsula la regla de publicación."""

    nombre: str
    desarrollo_situacional: str
    contexto_historia: str
    tiempo_estimado_min: int
    docente_creador_id: uuid.UUID
    numero: int = 1
    estado: EstadoCaso = EstadoCaso.BORRADOR
    caso_id: uuid.UUID = field(default_factory=_nuevo_id)
    id: uuid.UUID = field(default_factory=_nuevo_id)
    escenarios: list[Escenario] = field(default_factory=list)
    rubrica: Rubrica | None = None

    def publicar(self, cadena: ValidadorCaso) -> None:
        """Valida con la cadena y pasa a PUBLICADO solo si no hay errores (RF-09)."""
        from app.modules.cases.domain.exceptions import CasoInvalidoError
        from app.modules.cases.domain.validators.resultado import ResultadoValidacion

        if self.estado is not EstadoCaso.BORRADOR:
            resultado = ResultadoValidacion()
            resultado.agregar_error(f"Solo una versión en BORRADOR puede publicarse (actual: {self.estado}).")
            raise CasoInvalidoError(resultado)
        resultado = cadena.comprobar(self)
        if not resultado.es_valido:
            raise CasoInvalidoError(resultado)
        self.estado = EstadoCaso.PUBLICADO

    def asegurar_editable(self) -> None:
        """Solo una versión en BORRADOR admite cambios."""
        if self.estado is not EstadoCaso.BORRADOR:
            self._rechazar(f"Solo una versión en BORRADOR puede editarse (actual: {self.estado}).")

    def archivar(self) -> None:
        """Pasa de PUBLICADO a ARCHIVADO (evita nuevas programaciones, RF-09)."""
        if self.estado is not EstadoCaso.PUBLICADO:
            self._rechazar(f"Solo una versión PUBLICADA puede archivarse (actual: {self.estado}).")
        self.estado = EstadoCaso.ARCHIVADO

    @staticmethod
    def _rechazar(mensaje: str) -> NoReturn:
        from app.modules.cases.domain.exceptions import CasoInvalidoError
        from app.modules.cases.domain.validators.resultado import ResultadoValidacion

        resultado = ResultadoValidacion()
        resultado.agregar_error(mensaje)
        raise CasoInvalidoError(resultado)


@dataclass(frozen=True, slots=True)
class ResumenVersion:
    """Proyección de lectura para listados."""

    version_id: uuid.UUID
    caso_id: uuid.UUID
    numero: int
    nombre: str
    tiempo_estimado_min: int
    estado: EstadoCaso
    creado_en: datetime

