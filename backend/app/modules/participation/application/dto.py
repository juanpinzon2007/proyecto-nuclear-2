from dataclasses import dataclass
from datetime import datetime

from app.modules.participation.domain.entities import EstadoIntento, Intento, IdentificadorCases, es_referencia_cases
from app.modules.participation.domain.evaluation import ModalidadEvaluacion


@dataclass(frozen=True)
class SeleccionDecision:
    id_decision: IdentificadorCases
    id_opcion: IdentificadorCases


def selecciones_de(intento: Intento) -> tuple[SeleccionDecision, ...]:
    return tuple(SeleccionDecision(p.id_decision, p.id_opcion) for p in intento.pasos)


@dataclass(frozen=True)
class RecorridoAplicable:
    """Cases determina las decisiones aplicables y si conoce el total de la ruta."""

    decisiones: tuple[IdentificadorCases, ...]
    total_conocido: bool
    disponible: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.decisiones, tuple) or any(
            not es_referencia_cases(identificador)
            for identificador in self.decisiones
        ):
            raise ValueError("El recorrido debe contener una tupla de referencias válidas de Cases.")
        if len(set(self.decisiones)) != len(self.decisiones):
            raise ValueError("Cases devolvió decisiones duplicadas en el recorrido.")
        if type(self.total_conocido) is not bool:
            raise ValueError("Cases debe indicar si conoce el total del recorrido.")
        if type(self.disponible) is not bool or (not self.disponible and (self.decisiones or self.total_conocido)):
            raise ValueError("Un recorrido no disponible no declara decisiones ni total.")


@dataclass(frozen=True)
class ResumenIntento:
    id_intento: int
    id_participacion: int
    numero_intento: int
    estado: EstadoIntento
    inicio: datetime
    fin: datetime | None
    vence_en: datetime

    @classmethod
    def desde(cls, intento: Intento) -> "ResumenIntento":
        return cls(
            intento.id_intento, intento.id_participacion, intento.numero_intento,
            intento.estado, intento.inicio, intento.fin, intento.vence_en,
        )


@dataclass(frozen=True)
class ProgresoIntento:
    intento: ResumenIntento
    decisiones_aplicables: tuple[IdentificadorCases, ...] | None
    selecciones: tuple[SeleccionDecision, ...]
    pendientes: tuple[IdentificadorCases, ...] | None
    total_aplicable: int | None

    @property
    def respondidas(self) -> int:
        return len(self.selecciones)


@dataclass(frozen=True)
class EstadoEvaluacion:
    """Confirmación de Application sin publicar notas de candidatos no persistidos."""

    id_participacion: int
    id_intento: int | None
    modalidad: ModalidadEvaluacion
    confirmada: bool
    pendientes: tuple[str, ...]
