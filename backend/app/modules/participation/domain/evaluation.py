"""Valores de evaluación y proyecciones de lectura; no son entidades de Cases ni ORM."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.modules.participation.domain.entities import Intento, IdentificadorCases, es_referencia_cases, _entero_positivo
from app.modules.participation.domain.errors import ErrorDominioParticipacion

CALCULO_PENDIENTE = "calculo_pendiente"
MAPEO_AUSENCIA_PENDIENTE = "mapeo_er_detalle_ausencia_pendiente"


def _referencia_cases(valor: IdentificadorCases, nombre: str) -> None:
    if not es_referencia_cases(valor):
        raise EvaluacionInconsistente(f"{nombre} debe ser una referencia Cases válida.")


class PoliticaEvaluacionPendiente(ErrorDominioParticipacion):
    """Falta una regla académica: no sustituirla por una nota predeterminada."""


class EvaluacionInconsistente(ErrorDominioParticipacion):
    """Evidencias o resultados no corresponden al contexto académico."""


class ModalidadEvaluacion(StrEnum):
    COMPLETA = "COMPLETA"
    PARCIAL = "PARCIAL"
    AUSENCIA = "AUSENCIA"


def decimal_valido(valor: Decimal, nombre: str, *, maximo: Decimal | None = None) -> None:
    if not isinstance(valor, Decimal) or not valor.is_finite() or valor < 0:
        raise EvaluacionInconsistente(f"{nombre} debe ser Decimal finito no negativo.")
    if maximo is not None and valor > maximo:
        raise EvaluacionInconsistente(f"{nombre} excede el máximo permitido.")


@dataclass(frozen=True)
class ReferenciaAcademica:
    id_caso: int
    id_rubrica: IdentificadorCases
    version: str

    def __post_init__(self) -> None:
        _entero_positivo(self.id_caso, "id_caso")
        _referencia_cases(self.id_rubrica, "id_rubrica")
        if not self.version.strip():
            raise EvaluacionInconsistente("Se requiere una referencia académica estable/versionada.")


@dataclass(frozen=True)
class NivelEvaluable:
    id_nivel: IdentificadorCases
    logro_porcentaje: Decimal

    def __post_init__(self) -> None:
        _referencia_cases(self.id_nivel, "id_nivel")
        decimal_valido(self.logro_porcentaje, "logro_porcentaje", maximo=Decimal(100))


@dataclass(frozen=True)
class CriterioEvaluable:
    id_criterio: IdentificadorCases
    peso_porcentaje: Decimal
    niveles: tuple[NivelEvaluable, ...]

    def __post_init__(self) -> None:
        _referencia_cases(self.id_criterio, "id_criterio")
        decimal_valido(self.peso_porcentaje, "peso_porcentaje", maximo=Decimal(100))
        if not isinstance(self.niveles, tuple) or not self.niveles:
            raise EvaluacionInconsistente("El criterio debe proporcionar sus niveles explícitos.")
        if len({n.id_nivel for n in self.niveles}) != len(self.niveles):
            raise EvaluacionInconsistente("Niveles duplicados en un criterio.")


@dataclass(frozen=True)
class RubricaEvaluacion:
    """Proyección inmutable de la rúbrica que debe suministrar Cases."""

    referencia: ReferenciaAcademica
    nota_maxima: Decimal
    criterios: tuple[CriterioEvaluable, ...]

    def __post_init__(self) -> None:
        decimal_valido(self.nota_maxima, "nota_maxima")
        if self.nota_maxima == 0 or not isinstance(self.criterios, tuple) or not self.criterios:
            raise EvaluacionInconsistente("La rúbrica requiere máximo positivo y criterios.")
        if len({c.id_criterio for c in self.criterios}) != len(self.criterios):
            raise EvaluacionInconsistente("Criterios duplicados en la rúbrica.")
        niveles = [n.id_nivel for c in self.criterios for n in c.niveles]
        if len(niveles) != len(set(niveles)):
            raise EvaluacionInconsistente("Un nivel no puede pertenecer a dos criterios.")


@dataclass(frozen=True)
class NivelObtenido:
    id_criterio: IdentificadorCases
    id_nivel: IdentificadorCases

    def __post_init__(self) -> None:
        _referencia_cases(self.id_criterio, "id_criterio")
        _referencia_cases(self.id_nivel, "id_nivel")


@dataclass(frozen=True)
class EvidenciaDecision:
    id_decision: IdentificadorCases
    id_opcion: IdentificadorCases | None
    cero_por_ausencia: Decimal | None = None

    def __post_init__(self) -> None:
        _referencia_cases(self.id_decision, "id_decision")
        if self.id_opcion is not None:
            _referencia_cases(self.id_opcion, "id_opcion")
        if self.cero_por_ausencia is not None:
            decimal_valido(self.cero_por_ausencia, "cero_por_ausencia", maximo=Decimal(0))
            if self.id_opcion is not None:
                raise EvaluacionInconsistente("Una ausencia no contiene una opción elegida.")


@dataclass(frozen=True)
class ResultadoCriterio:
    id_criterio: IdentificadorCases
    id_nivel: IdentificadorCases
    puntaje_obtenido: Decimal

    def __post_init__(self) -> None:
        _referencia_cases(self.id_criterio, "id_criterio")
        _referencia_cases(self.id_nivel, "id_nivel")
        decimal_valido(self.puntaje_obtenido, "puntaje_obtenido")


@dataclass(frozen=True)
class ContextoEvaluacion:
    referencia: ReferenciaAcademica
    id_participacion: int
    modalidad: ModalidadEvaluacion
    decisiones_aplicables: tuple[IdentificadorCases, ...]
    intento: Intento | None
    ausencia_confirmada: bool = False

    def __post_init__(self) -> None:
        _entero_positivo(self.id_participacion, "id_participacion")
        if not isinstance(self.modalidad, ModalidadEvaluacion):
            raise EvaluacionInconsistente("Modalidad académica desconocida.")
        if not isinstance(self.decisiones_aplicables, tuple) or not self.decisiones_aplicables:
            raise EvaluacionInconsistente("Se requiere el recorrido académico explícito.")
        for identificador in self.decisiones_aplicables:
            _referencia_cases(identificador, "id_decision")
        if len(set(self.decisiones_aplicables)) != len(self.decisiones_aplicables):
            raise EvaluacionInconsistente("Decisiones duplicadas en el contexto.")
        if self.intento is not None and self.intento.id_participacion != self.id_participacion:
            raise EvaluacionInconsistente("El intento pertenece a otra participación.")


@dataclass(frozen=True)
class DatosEvaluacion:
    """Candidato interno; tener una nota aquí NO acredita persistencia/publicación."""

    modalidad: ModalidadEvaluacion
    referencia: ReferenciaAcademica
    id_participacion: int
    id_intento: int | None
    evidencias: tuple[EvidenciaDecision, ...]
    criterios: tuple[ResultadoCriterio, ...] = ()
    nota_final: Decimal | None = None
    politica_calculo: str | None = None
    pendientes: tuple[str, ...] = (CALCULO_PENDIENTE,)

    def __post_init__(self) -> None:
        _entero_positivo(self.id_participacion, "id_participacion")
        if not isinstance(self.modalidad, ModalidadEvaluacion):
            raise EvaluacionInconsistente("Modalidad desconocida.")
        if self.id_intento is not None:
            _entero_positivo(self.id_intento, "id_intento")
        if (self.modalidad == ModalidadEvaluacion.AUSENCIA) != (self.id_intento is None):
            raise EvaluacionInconsistente("Solo una ausencia puede carecer de intento.")
        for valores in (self.evidencias, self.criterios, self.pendientes):
            if not isinstance(valores, tuple):
                raise EvaluacionInconsistente("Los datos de evaluación deben ser inmutables.")
        if len({e.id_decision for e in self.evidencias}) != len(self.evidencias):
            raise EvaluacionInconsistente("Evidencias duplicadas.")
        if not self.evidencias:
            raise EvaluacionInconsistente("Se requieren decisiones académicas explícitas.")
        if len({c.id_criterio for c in self.criterios}) != len(self.criterios):
            raise EvaluacionInconsistente("Resultados de criterio duplicados.")
        if self.modalidad == ModalidadEvaluacion.AUSENCIA:
            if any(e.id_opcion is not None or e.cero_por_ausencia != Decimal(0) for e in self.evidencias):
                raise EvaluacionInconsistente("La ausencia exige ceros sin respuestas ficticias.")
        elif any(e.cero_por_ausencia is not None for e in self.evidencias):
            raise EvaluacionInconsistente("Una respuesta pendiente no es un cero por ausencia.")
        if self.modalidad == ModalidadEvaluacion.COMPLETA and any(e.id_opcion is None for e in self.evidencias):
            raise EvaluacionInconsistente("Una evaluación completa requiere todas sus selecciones.")
        if self.nota_final is not None:
            decimal_valido(self.nota_final, "nota_final")
            if not self.politica_calculo or not self.criterios:
                raise EvaluacionInconsistente("Una nota calculada necesita criterios y política explícitos.")
            if self.modalidad == ModalidadEvaluacion.AUSENCIA and (
                self.nota_final != Decimal(0) or any(c.puntaje_obtenido != Decimal(0) for c in self.criterios)
            ):
                raise EvaluacionInconsistente("Una ausencia no puede producir puntajes distintos de cero.")
        elif not self.pendientes:
            raise EvaluacionInconsistente("Una evaluación sin nota debe indicar qué falta resolver.")

    @property
    def lista_para_persistir(self) -> bool:
        return self.nota_final is not None and not self.pendientes
