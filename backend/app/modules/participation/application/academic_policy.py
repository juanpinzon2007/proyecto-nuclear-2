"""Respuestas aprobadas de Diana Ma Valencia. Sin mapeo/agregación inventados."""
from dataclasses import dataclass, replace
from decimal import Decimal
from fractions import Fraction
from typing import Protocol

from app.modules.participation.domain.entities import EstadoIntento, IdentificadorCases
from app.modules.participation.domain.evaluation import ModalidadEvaluacion, PoliticaEvaluacionPendiente, EvaluacionInconsistente
from app.modules.participation.domain.calculador_rubrica import PlanCalculo, PoliticaCalculo, FormulaCalculo
from app.modules.participation.application.evaluation_mapping import validar_mapeo_historico


@dataclass(frozen=True)
class PreguntaParaEvaluar:
    id_decision: IdentificadorCases
    id_opcion: IdentificadorCases | None
    valor_no_respondida: Decimal | None


class ResolucionNivelesAcademicos(Protocol):
    def resolver(self, *, preguntas: tuple[PreguntaParaEvaluar, ...], rubrica):
        """Mapeo/agregación aprobado a un nivel REAL por criterio, incluidos ceros.

        No sustituir faltantes por selecciones/niveles ficticios. Ausencia de esta
        regla es política pendiente, no el promedio automático de valoraciones.
        """
        ...


class MapeoEscala100:
    """Aplica la escala aprobada; la interpretación de niveles sigue siendo explícita."""
    def __init__(self, base): self.base=base
    def preparar(self, fuente):
        if self.base is None:
            raise PoliticaEvaluacionPendiente("Falta mapeo aprobado de puntajes a logros.")
        r=self.base.preparar(fuente)
        validar_mapeo_historico(fuente,r)
        return replace(r,nota_maxima=Decimal(100))


@dataclass(frozen=True)
class PoliticaAcademicaConfirmada:
    resolucion: ResolucionNivelesAcademicos | None = None
    identificador: str = "diana-valencia-evaluation-v1"

    @staticmethod
    def pesos_efectivos(rubrica):
        return tuple((c.id_criterio,Fraction(1,len(rubrica.criterios))) for c in rubrica.criterios)

    def clasificar(self, *, intento, decisiones_aplicables):
        if intento.estado == EstadoIntento.VENCIDO:
            return ModalidadEvaluacion.PARCIAL
        if intento.estado == EstadoIntento.FINALIZADO and {p.id_decision for p in intento.pasos}==set(decisiones_aplicables):
            return ModalidadEvaluacion.COMPLETA
        raise PoliticaEvaluacionPendiente("Precisar el tratamiento del cierre voluntario incompleto.")

    def preguntas_para_evaluar(self, *, datos, intento):
        if datos.modalidad == ModalidadEvaluacion.AUSENCIA:
            if intento is not None or datos.id_intento is not None:
                raise EvaluacionInconsistente("Una ausencia no contiene un intento.")
            return tuple(PreguntaParaEvaluar(e.id_decision,None,Decimal(0)) for e in datos.evidencias)
        if intento is None or intento.id_intento!=datos.id_intento or intento.estado==EstadoIntento.EN_CURSO:
            raise EvaluacionInconsistente("Se requiere el intento cerrado correspondiente.")
        if any(e.id_opcion is None for e in datos.evidencias) and intento.estado!=EstadoIntento.VENCIDO:
            raise PoliticaEvaluacionPendiente("Los ceros aprobados cubren preguntas pendientes al vencer el tiempo.")
        return tuple(PreguntaParaEvaluar(e.id_decision,e.id_opcion,
            Decimal(0) if e.id_opcion is None else None) for e in datos.evidencias)

    def preparar_calculo_para_intento(self, *, datos, rubrica, intento):
        if rubrica.nota_maxima != Decimal(100):
            raise EvaluacionInconsistente("La escala aprobada es 0–100.")
        preguntas=self.preguntas_para_evaluar(datos=datos,intento=intento)
        if self.resolucion is None:
            raise PoliticaEvaluacionPendiente("Falta mapeo de niveles/agregación de preguntas, incluidos ceros, aprobado.")
        niveles=self.resolucion.resolver(preguntas=preguntas,rubrica=rubrica)
        return PlanCalculo(niveles,PoliticaCalculo(self.identificador,FormulaCalculo.PROMEDIO_IGUALITARIO_100,None,None))

    def preparar_calculo(self, *, datos, rubrica):
        # ServicioEvaluacion aporta el intento real dentro de la UoW. Para ausencia
        # ya debe haberse confirmado ausencia; no se crea un Intento artificial.
        return self.preparar_calculo_para_intento(datos=datos,rubrica=rubrica,intento=None)
