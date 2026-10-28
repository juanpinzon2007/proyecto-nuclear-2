from dataclasses import dataclass
from datetime import datetime

from app.modules.participation.domain.entities import EstadoIntento, Intento
from app.modules.participation.domain.evaluation import ModalidadEvaluacion


@dataclass(frozen=True)
class SeleccionDecision:
    id_decision: int
    id_opcion: int


def selecciones_de(intento: Intento) -> tuple[SeleccionDecision, ...]:
    return tuple(SeleccionDecision(p.id_decision, p.id_opcion) for p in intento.pasos)


@dataclass(frozen=True)
class RecorridoAplicable:
    """Cases determina las decisiones aplicables y si conoce el total de la ruta."""

    decisiones: tuple[int, ...]
    total_conocido: bool

    def __post_init__(self) -> None:
        if not isinstance(self.decisiones, tuple) or any(
            type(identificador) is not int or identificador <= 0
            for identificador in self.decisiones
        ):
            raise ValueError("El recorrido debe contener una tupla de IDs enteros positivos.")
        if len(set(self.decisiones)) != len(self.decisiones):
            raise ValueError("Cases devolvió decisiones duplicadas en el recorrido.")
        if type(self.total_conocido) is not bool:
            raise ValueError("Cases debe indicar si conoce el total del recorrido.")


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
    decisiones_aplicables: tuple[int, ...]
    selecciones: tuple[SeleccionDecision, ...]
    pendientes: tuple[int, ...]
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
