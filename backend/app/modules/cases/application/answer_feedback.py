"""Explicaciones de las selecciones en una edición exacta, sin calificar.

Consulta interna: el consumidor debe verificar actor y cierre en su transacción.
No autoriza publicación ni devuelve respuestas de preguntas no seleccionadas.
"""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.application.simulation_structure import consultar_estructura_version
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import EscenarioModel, PreguntaModel, OpcionRespuestaModel


@dataclass(frozen=True)
class ExplicacionSeleccion:
    pregunta_id: UUID
    opcion_id: UUID
    enunciado: str
    texto_seleccionado: str
    es_correcta: bool
    justificacion: str


def consultar_explicaciones_seleccionadas(
    db: Session, *, version_id: UUID, selecciones: tuple[tuple[UUID, UUID], ...],
) -> tuple[ExplicacionSeleccion, ...]:
    """Conserva el orden de las selecciones, sin completar faltantes con ficticios.

    Comparte Session sin flush/commit/cierre. No reemplaza edición archivada por
    la vigente ni genera explicaciones nuevas a partir de aciertos/puntajes.
    """
    consultar_estructura_version(db, version_id=version_id)
    if len({q for q, _ in selecciones}) != len(selecciones):
        raise CasoNoEncontradoError("Selecciones históricas inconsistentes.")
    if not selecciones:
        return ()
    q, o, e = PreguntaModel, OpcionRespuestaModel, EscenarioModel
    with db.no_autoflush:
        filas = db.execute(select(q.id.label("pregunta_id"), o.id.label("opcion_id"), q.enunciado,
            o.texto, o.es_correcta, o.justificacion)
            .select_from(o).join(q, q.id == o.pregunta_id).join(e, e.id == q.escenario_id)
            .where(e.version_caso_id == version_id, o.id.in_([opcion for _, opcion in selecciones]))).all()
    por_seleccion = {(f.pregunta_id, f.opcion_id): f for f in filas}
    if set(selecciones) != por_seleccion.keys():
        raise CasoNoEncontradoError("Las selecciones no corresponden a la edición histórica.")
    return tuple(ExplicacionSeleccion(f.pregunta_id, f.opcion_id, f.enunciado, f.texto,
        f.es_correcta, f.justificacion) for par in selecciones for f in (por_seleccion[par],))
