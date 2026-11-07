"""Proyección de puntajes; comparte transacción y no escribe."""
from sqlalchemy import select

from app.modules.cases.application.scoring import (
    ConfiguracionPreguntas, PuntajeAlternativa, REGLA_PREGUNTAS,
    ConfiguracionCalificacionInvalida,
)
from app.modules.cases.infrastructure.models import (
    RubricaModel, CriterioRubricaModel, ValoracionOpcionModel,
    OpcionRespuestaModel, PreguntaModel, EscenarioModel,
)
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy


def consultar_configuracion_preguntas(sesion, *, version_id, solo_publicada=True):
    r, c, v, o, q, e = RubricaModel, CriterioRubricaModel, ValoracionOpcionModel, OpcionRespuestaModel, PreguntaModel, EscenarioModel
    with sesion.no_autoflush:
        rubrica = sesion.execute(select(r.id, r.version_regla).where(r.version_caso_id == version_id)).one_or_none()
        if rubrica is None or rubrica.version_regla != REGLA_PREGUNTAS:
            raise ConfiguracionCalificacionInvalida("La versión no declara PREGUNTAS_100_V1; no se reinterpretan puntajes históricos.")
        criterios = tuple(sesion.scalars(select(c.id).where(c.rubrica_id == rubrica.id).order_by(c.id)))
        filas = sesion.execute(select(q.id.label('pregunta_id'), o.id.label('opcion_id'), v.criterio_id, v.puntaje)
            .join(o, o.id == v.opcion_id).join(q, q.id == o.pregunta_id).join(e, e.id == q.escenario_id)
            .where(e.version_caso_id == version_id).order_by(o.id, v.criterio_id)).all()
        grafo = RepositorioGrafoSQLAlchemy(sesion).leer(version_id, solo_publicada=solo_publicada)
    configuracion = ConfiguracionPreguntas(grafo, criterios, tuple(PuntajeAlternativa(*f) for f in filas))
    configuracion.validar()
    return configuracion
