"""Proyección interna histórica; puntaje almacenado NO equivale a logro porcentual.

No autoriza actores ni entrega esta información por HTTP. El consumidor debe
comprobar titularidad y cierre; comparte su Session sin confirmar ni cerrar.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.application.simulation_structure import consultar_estructura_version
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import (
    CasoModel, RubricaModel, CriterioRubricaModel, NivelRubricaModel,
    ValoracionOpcionModel, OpcionRespuestaModel, PreguntaModel, EscenarioModel,
)


@dataclass(frozen=True)
class NivelHistorico:
    id: UUID
    puntaje: Decimal


@dataclass(frozen=True)
class CriterioHistorico:
    id: UUID
    peso: Decimal
    niveles: tuple[NivelHistorico, ...]


@dataclass(frozen=True)
class ValoracionHistorica:
    opcion_id: UUID
    criterio_id: UUID
    puntaje: Decimal


@dataclass(frozen=True)
class RubricaHistorica:
    version_id: UUID
    caso_id: UUID
    id_caso_academico: int | None
    rubrica_id: UUID
    version_regla: str
    criterios: tuple[CriterioHistorico, ...]
    valoraciones: tuple[ValoracionHistorica, ...]

    @property
    def referencia_versionada(self) -> str:
        return f"{self.version_id}:{self.version_regla}"


def consultar_rubrica_historica(db: Session, *, version_id: UUID) -> RubricaHistorica:
    estructura = consultar_estructura_version(db, version_id=version_id)
    c, n, v, o, q, e = CriterioRubricaModel, NivelRubricaModel, ValoracionOpcionModel, OpcionRespuestaModel, PreguntaModel, EscenarioModel
    with db.no_autoflush:
        academico = db.scalar(select(CasoModel.id_caso).where(CasoModel.id == estructura.caso_id))
        criterios = db.execute(select(c.id, c.peso).where(c.rubrica_id == estructura.rubrica_id).order_by(c.id)).all()
        niveles = db.execute(select(n.id, n.criterio_id, n.puntaje).join(c, c.id == n.criterio_id)
            .where(c.rubrica_id == estructura.rubrica_id).order_by(n.id)).all()
        valores = db.execute(select(v.opcion_id, v.criterio_id, v.puntaje)
            .join(o, o.id == v.opcion_id).join(q, q.id == o.pregunta_id).join(e, e.id == q.escenario_id)
            .where(e.version_caso_id == version_id).order_by(v.opcion_id, v.criterio_id)).all()
    ids = {f.id for f in criterios}
    if any(f.criterio_id not in ids for f in valores):
        raise CasoNoEncontradoError("La edición contiene valoraciones de una rúbrica ajena.")
    return RubricaHistorica(version_id, estructura.caso_id, academico, estructura.rubrica_id,
        estructura.version_regla,
        tuple(CriterioHistorico(f.id, f.peso, tuple(NivelHistorico(x.id, x.puntaje)
            for x in niveles if x.criterio_id == f.id)) for f in criterios),
        tuple(ValoracionHistorica(f.opcion_id, f.criterio_id, f.puntaje) for f in valores))
