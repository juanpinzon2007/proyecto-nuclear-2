from decimal import Decimal
from typing import Protocol

from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.evaluation import (
    CALCULO_PENDIENTE, MAPEO_AUSENCIA_PENDIENTE, ContextoEvaluacion,
    DatosEvaluacion, EvaluacionInconsistente, EvidenciaDecision, ModalidadEvaluacion,
)


class IEstrategiaEvaluacion(Protocol):
    def preparar(self, contexto: ContextoEvaluacion) -> DatosEvaluacion: ...


def _datos_intento(contexto: ContextoEvaluacion, modalidad: ModalidadEvaluacion) -> DatosEvaluacion:
    intento = contexto.intento
    if contexto.modalidad != modalidad or intento is None or intento.estado == EstadoIntento.EN_CURSO:
        raise EvaluacionInconsistente("La estrategia requiere un intento cerrado de su modalidad.")
    selecciones = {p.id_decision: p.id_opcion for p in intento.pasos}
    if not set(selecciones).issubset(contexto.decisiones_aplicables):
        raise EvaluacionInconsistente("Hay selecciones ajenas al recorrido evaluable.")
    evidencias = tuple(EvidenciaDecision(d, selecciones.get(d)) for d in contexto.decisiones_aplicables)
    return DatosEvaluacion(
        modalidad=modalidad, referencia=contexto.referencia,
        id_participacion=contexto.id_participacion, id_intento=intento.id_intento,
        evidencias=evidencias,
    )


class EvaluacionCompletaStrategy:
    def preparar(self, contexto: ContextoEvaluacion) -> DatosEvaluacion:
        if contexto.intento is None or contexto.intento.estado != EstadoIntento.FINALIZADO:
            raise EvaluacionInconsistente("Evaluación completa requiere un intento finalizado voluntariamente.")
        return _datos_intento(contexto, ModalidadEvaluacion.COMPLETA)


class EvaluacionParcialStrategy:
    def preparar(self, contexto: ContextoEvaluacion) -> DatosEvaluacion:
        # Un cierre voluntario también puede ser parcial. La clasificación proviene
        # del contrato académico, no de equiparar FINALIZADO con COMPLETA.
        return _datos_intento(contexto, ModalidadEvaluacion.PARCIAL)


class EvaluacionAusenciaStrategy:
    def preparar(self, contexto: ContextoEvaluacion) -> DatosEvaluacion:
        if (
            contexto.modalidad != ModalidadEvaluacion.AUSENCIA
            or contexto.intento is not None or contexto.ausencia_confirmada is not True
        ):
            raise EvaluacionInconsistente("La ausencia exige confirmación y ningún intento iniciado.")
        return DatosEvaluacion(
            modalidad=ModalidadEvaluacion.AUSENCIA, referencia=contexto.referencia,
            id_participacion=contexto.id_participacion, id_intento=None,
            evidencias=tuple(EvidenciaDecision(d, None, Decimal(0)) for d in contexto.decisiones_aplicables),
            pendientes=(CALCULO_PENDIENTE, MAPEO_AUSENCIA_PENDIENTE),
        )
