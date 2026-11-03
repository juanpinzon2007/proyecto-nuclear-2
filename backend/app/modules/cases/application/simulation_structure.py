"""Estructura verificable de una edición; el orden editorial NO es una ruta.

Fuente interna sin autorización de actor. El consumidor debe acreditar sesión/
convocatoria y usar la edición asignada. No entrega corrección ni valoraciones.
"""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import (
    VersionCasoModel, RubricaModel, EscenarioModel, PreguntaModel, OpcionRespuestaModel,
)


@dataclass(frozen=True)
class PreguntaVersion:
    id: UUID
    escenario_id: UUID
    orden_escenario: int
    orden_pregunta: int
    opciones: tuple[UUID, ...]


@dataclass(frozen=True)
class EstructuraVersion:
    version_id: UUID
    caso_id: UUID
    numero: int
    estado: EstadoCaso
    rubrica_id: UUID
    version_regla: str
    preguntas: tuple[PreguntaVersion, ...]


def consultar_estructura_version(db: Session, *, version_id: UUID) -> EstructuraVersion:
    """IDs/orden de la edición exacta, incluso archivada para lectura histórica.

    No equivale a decisiones disponibles: no hay transiciones en este contrato.
    Comparte Session sin flush/commit/cierre; nunca sustituye por última edición.
    """
    v, r, e, q, o = VersionCasoModel, RubricaModel, EscenarioModel, PreguntaModel, OpcionRespuestaModel
    with db.no_autoflush:
        version = db.execute(select(v.id, v.caso_id, v.numero, v.estado, r.id.label("rubrica_id"), r.version_regla)
            .join(r, r.version_caso_id == v.id)
            .where(v.id == version_id, v.estado.in_([EstadoCaso.PUBLICADO, EstadoCaso.ARCHIVADO]))).one_or_none()
        if version is None:
            raise CasoNoEncontradoError("La edición solicitada no está disponible.")
        filas = db.execute(select(q.id, e.id.label("escenario_id"), e.orden.label("orden_escenario"),
            q.orden.label("orden_pregunta"), o.id.label("opcion_id"))
            .select_from(e).join(q, q.escenario_id == e.id).outerjoin(o, o.pregunta_id == q.id)
            .where(e.version_caso_id == version_id).order_by(e.orden, q.orden, o.orden)).all()
    preguntas = {}
    for f in filas:
        if f.id not in preguntas:
            preguntas[f.id] = (f.escenario_id, f.orden_escenario, f.orden_pregunta, [])
        if f.opcion_id is not None:
            preguntas[f.id][3].append(f.opcion_id)
    return EstructuraVersion(version.id, version.caso_id, version.numero, version.estado,
        version.rubrica_id, version.version_regla, tuple(PreguntaVersion(i, *datos[:3], tuple(datos[3]))
            for i, datos in preguntas.items()))


def validar_opcion_version(db: Session, *, version_id: UUID, pregunta_id: UUID, opcion_id: UUID) -> None:
    """Pertenencia relacional, NO elegibilidad de ese punto en un recorrido."""
    q, o, e, v = PreguntaModel, OpcionRespuestaModel, EscenarioModel, VersionCasoModel
    with db.no_autoflush:
        encontrada = db.scalar(select(o.id).join(q, q.id == o.pregunta_id).join(e, e.id == q.escenario_id)
            .join(v, v.id == e.version_caso_id).where(o.id == opcion_id, q.id == pregunta_id,
                v.id == version_id, v.estado.in_([EstadoCaso.PUBLICADO, EstadoCaso.ARCHIVADO])))
    if encontrada is None:
        raise CasoNoEncontradoError("Selección no disponible en la edición solicitada.")
