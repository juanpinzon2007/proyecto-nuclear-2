"""Registro de modelos ORM del módulo de casos (importar para poblar Base.metadata)."""

from app.modules.cases.infrastructure.models.caso import (
    CasoModel,
    EscenarioModel,
    OpcionRespuestaModel,
    PreguntaModel,
    VersionCasoModel,
)
from app.modules.cases.infrastructure.models.rubrica import (
    CriterioRubricaModel,
    NivelRubricaModel,
    RubricaModel,
    ValoracionOpcionModel,
)

__all__ = [
    "CasoModel",
    "CriterioRubricaModel",
    "EscenarioModel",
    "NivelRubricaModel",
    "OpcionRespuestaModel",
    "PreguntaModel",
    "RubricaModel",
    "ValoracionOpcionModel",
    "VersionCasoModel",
]
