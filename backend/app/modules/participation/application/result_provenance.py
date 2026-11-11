"""Definición declarada y parámetros efectivos: sin fórmulas académicas implícitas."""
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import inspect
import json
from uuid import UUID

from app.modules.participation.domain import calculador_rubrica, estrategias_evaluacion
from app.modules.participation.domain.evaluation import (
    EvaluacionInconsistente, RubricaEvaluacion, ReferenciaAcademica, CriterioEvaluable,
    NivelEvaluable, DatosEvaluacion, EvidenciaDecision, ResultadoCriterio, ModalidadEvaluacion,
)
from app.modules.participation.domain.calculador_rubrica import PlanCalculo, PoliticaCalculo, NivelObtenido, FormulaCalculo


def _serializar(x):
    if is_dataclass(x): return asdict(x)
    if isinstance(x, (Decimal, UUID)): return str(x)
    if isinstance(x, datetime): return x.isoformat()
    if isinstance(x, timedelta): return {"microsegundos": (x.days*86400+x.seconds)*1000000+x.microseconds}
    raise TypeError(f"Tipo no admitido en procedencia: {type(x).__name__}")


def canonico(x) -> str:
    return json.dumps(x, default=_serializar, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def huella(texto: str) -> str:
    return sha256(texto.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DefinicionPoliticaLaboratorio:
    """Valor inmutable: JSON canónico, no una referencia a un dict mutable."""
    documento: str

    def __post_init__(self):
        try:
            d=json.loads(self.documento)
            if (d["ambito"]!="LABORATORIO" or not d["id"].strip() or not d["version"].strip()
                or not all(isinstance(d[k],dict) and d[k] for k in ("clasificacion","mapeo","agregacion"))
                or canonico(d)!=self.documento):
                raise ValueError("Definición incompleta")
        except (ValueError, TypeError, KeyError, AttributeError):
            raise EvaluacionInconsistente("Se requiere definición versionada de laboratorio, no solo un nombre.") from None

    @classmethod
    def crear(cls, *, identificador, version, clasificacion, mapeo, agregacion):
        return cls(canonico(dict(id=identificador, version=version, ambito="LABORATORIO",
            clasificacion=clasificacion, mapeo=mapeo, agregacion=agregacion)))


def fuentes_motor():
    return {m.__name__: inspect.getsource(m) for m in (calculador_rubrica, estrategias_evaluacion)}


# Huella del motor real anterior a la aprobación de Diana, capturada antes de
# añadir la fórmula igualitaria. La rama porcentual se conserva sin cambios;
# jamás ejecutar código recibido de la BD para reproducir un resultado antiguo.
MOTOR_V1_COMPATIBLE = "00571eb465608fa91d158aa399882d744846c2ff4cf8f34f1cfaf9d876a740cc"
# Motor de HEAD 9a1d133 antes de añadir calcular_preguntas. Las dos ramas
# anteriores de calcular y las estrategias se conservan byte a byte.
MOTOR_V2_COMPATIBLE = "c3dcc7853b0db8809650707503e18abb3f4b955c8c14d756bfbd2ac9a00c2582"

# Dos capturas verificadas del motor PREGUNTAS_100_V1. Las fuentes difieren
# únicamente en cadenas explicativas de Strategy. Se aceptan sus documentos
# exactos, conservando la fuente y el hash que acompañan a cada resultado.
MOTORES_PREGUNTAS_COMPATIBLES = frozenset({
    "88f16a1abdebbbe3367c40a13ce3255f10a7bdd6872d3df20ce487777c872960",
    "38bbef396cb982fa6d32ab3f0620c9765a7fc32ab8ec4866d1668b842a706d08",
})


def motor_preguntas_compatible(motor):
    return motor == fuentes_motor() or huella(canonico(motor)) in MOTORES_PREGUNTAS_COMPATIBLES


def motor_compatible(motor, formula):
    return motor_preguntas_compatible(motor) or (huella(canonico(motor))==MOTOR_V1_COMPATIBLE
        and formula==FormulaCalculo.SUMA_PONDERADA_PORCENTUAL.value) or (
        huella(canonico(motor))==MOTOR_V2_COMPATIBLE and formula in (
            FormulaCalculo.SUMA_PONDERADA_PORCENTUAL.value, FormulaCalculo.PROMEDIO_IGUALITARIO_100.value))


def datos_desde(d):
    r=d["referencia"]
    return DatosEvaluacion(ModalidadEvaluacion(d["modalidad"]),
        ReferenciaAcademica(r["id_caso"],UUID(r["id_rubrica"]),r["version"]),
        d["id_participacion"],d["id_intento"],
        tuple(EvidenciaDecision(UUID(e["id_decision"]),UUID(e["id_opcion"]) if e["id_opcion"] else None) for e in d["evidencias"]),
        tuple(ResultadoCriterio(UUID(c["id_criterio"]),UUID(c["id_nivel"]),Decimal(c["puntaje_obtenido"])) for c in d["criterios"]),
        Decimal(d["nota_final"]), d["politica_calculo"], tuple(d["pendientes"]))


def rubrica_desde(d):
    r=d["referencia"]
    return RubricaEvaluacion(ReferenciaAcademica(r["id_caso"],UUID(r["id_rubrica"]),r["version"]),
        Decimal(d["nota_maxima"]),tuple(CriterioEvaluable(UUID(c["id_criterio"]),Decimal(c["peso_porcentaje"]),
            tuple(NivelEvaluable(UUID(n["id_nivel"]),Decimal(n["logro_porcentaje"])) for n in c["niveles"])) for c in d["criterios"]))


def plan_desde(d):
    p=d["politica"]
    return PlanCalculo(tuple(NivelObtenido(UUID(n["id_criterio"]),UUID(n["id_nivel"])) for n in d["niveles"]),
        PoliticaCalculo(p["identificador"],FormulaCalculo(p["formula"]),p["decimales"],p["redondeo"]))
