"""Esquemas Pydantic v2 del DSL JSON de casos (Sección 10).

Solo validan estructura y tipos. Las reglas cruzadas (mínimo de opciones,
suma de pesos, justificaciones, mapeo de valoraciones) viven en la cadena
de validación del dominio.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class _EsquemaEstricto(BaseModel):
    """Base: rechaza campos no definidos."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class OpcionSchema(_EsquemaEstricto):
    orden: int
    texto: str
    es_correcta: bool = Field(alias="esCorrecta")
    justificacion: str
    # nombre de criterio -> puntaje (Valoracion_Opcion)
    valoraciones: dict[str, Decimal] = Field(default_factory=dict)


class PreguntaSchema(_EsquemaEstricto):
    orden: int
    enunciado: str
    options: list[OpcionSchema] = Field(default_factory=list)


class EscenarioSchema(_EsquemaEstricto):
    orden: int
    contexto_situacional: str = Field(alias="contextoSituacional")
    questions: list[PreguntaSchema] = Field(default_factory=list)


class NivelSchema(_EsquemaEstricto):
    nombre: str
    puntaje: Decimal
    descriptor: str


class CriterioSchema(_EsquemaEstricto):
    nombre: str
    peso: Decimal
    niveles: list[NivelSchema] = Field(default_factory=list)


class RubricaSchema(_EsquemaEstricto):
    nombre: str
    version_regla: str = Field(alias="versionRegla")
    criterios: list[CriterioSchema] = Field(default_factory=list)


class DatosCasoSchema(_EsquemaEstricto):
    """Bloque ``case`` del payload."""

    nombre: str
    desarrollo_situacional: str = Field(alias="desarrolloSituacional")
    contexto_historia: str = Field(alias="contextoHistoria")
    tiempo_estimado_min: int = Field(alias="tiempoEstimadoMin")


class CasoPayload(_EsquemaEstricto):
    """Raíz del DSL: ``case``, ``scenarios`` (con ``questions`` y ``options``) y ``rubric``."""

    case: DatosCasoSchema
    scenarios: list[EscenarioSchema] = Field(default_factory=list)
    rubric: RubricaSchema | None = None

