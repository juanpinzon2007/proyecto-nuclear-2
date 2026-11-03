"""Traducción académica explícita; sin implementación predeterminada de puntajes."""
from typing import Protocol

from app.modules.cases.application.evaluation_snapshot import RubricaHistorica
from app.modules.participation.domain.evaluation import RubricaEvaluacion, EvaluacionInconsistente


def validar_mapeo_historico(fuente: RubricaHistorica, rubrica: RubricaEvaluacion) -> None:
    if not isinstance(rubrica, RubricaEvaluacion):
        raise EvaluacionInconsistente("El mapeo no entregó una rúbrica evaluable.")
    ref = rubrica.referencia
    if (ref.id_caso, ref.id_rubrica, ref.version) != (fuente.id_caso_academico, fuente.rubrica_id, fuente.referencia_versionada):
        raise EvaluacionInconsistente("El mapeo sustituyó la referencia histórica.")
    originales = {c.id: c for c in fuente.criterios}
    if {c.id_criterio for c in rubrica.criterios} != originales.keys():
        raise EvaluacionInconsistente("El mapeo cambió los criterios históricos.")
    for c in rubrica.criterios:
        original = originales[c.id_criterio]
        if c.peso_porcentaje != original.peso or {n.id_nivel for n in c.niveles} != {n.id for n in original.niveles}:
            raise EvaluacionInconsistente("El mapeo cambió pesos o pertenencia de niveles.")


class MapeoRubricaEvaluacion(Protocol):
    def preparar(self, fuente: RubricaHistorica) -> RubricaEvaluacion:
        """Fija máximo y significado de puntajes/logros con una regla aprobada.

        Conservar IDs reales, referencia exacta, pesos y pertenencia nivel–criterio.
        No convierte puntajes a porcentajes por defecto ni resuelve la agregación
        de varias decisiones a un nivel: eso pertenece a PoliticaEvaluacionPort.
        """
        ...
