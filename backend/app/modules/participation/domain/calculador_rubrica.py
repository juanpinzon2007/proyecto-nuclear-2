from dataclasses import dataclass
from decimal import (
    Context, Decimal, ROUND_05UP, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_DOWN,
    ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, localcontext,
)
from enum import StrEnum
from fractions import Fraction

from app.modules.participation.domain.evaluation import (
    EvaluacionInconsistente, NivelObtenido, PoliticaEvaluacionPendiente,
    ResultadoCriterio, RubricaEvaluacion,
)


class FormulaCalculo(StrEnum):
    SUMA_PONDERADA_PORCENTUAL = "SUMA_PONDERADA_PORCENTUAL"
    PROMEDIO_IGUALITARIO_100 = "PROMEDIO_IGUALITARIO_100"


@dataclass(frozen=True)
class PoliticaCalculo:
    identificador: str
    formula: FormulaCalculo
    decimales: int | None
    redondeo: str | None

    def __post_init__(self) -> None:
        if not self.identificador.strip() or not isinstance(self.formula, FormulaCalculo):
            raise EvaluacionInconsistente("Se requiere una política y fórmula explícitas.")
        if self.formula == FormulaCalculo.PROMEDIO_IGUALITARIO_100:
            if self.decimales is not None or self.redondeo is not None:
                raise PoliticaEvaluacionPendiente("No hay redondeo aprobado para la política igualitaria.")
            return
        if type(self.decimales) is not int or self.decimales < 0:
            raise EvaluacionInconsistente("La cantidad de decimales debe ser explícita y no negativa.")
        if self.redondeo not in (
            ROUND_05UP, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_DOWN,
            ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP,
        ):
            raise EvaluacionInconsistente("Modo de redondeo desconocido.")


@dataclass(frozen=True)
class PlanCalculo:
    niveles: tuple[NivelObtenido, ...]
    politica: PoliticaCalculo


@dataclass(frozen=True)
class CalculoRubrica:
    criterios: tuple[ResultadoCriterio, ...]
    nota_sin_redondear: Decimal
    nota_final: Decimal
    politica: str


class CalculadorRubrica:
    def calcular(
        self, rubrica: RubricaEvaluacion, niveles: tuple[NivelObtenido, ...],
        politica: PoliticaCalculo | None,
    ) -> CalculoRubrica:
        if politica is None:
            raise PoliticaEvaluacionPendiente("Falta fórmula o redondeo aprobados.")
        if not isinstance(niveles, tuple) or len({n.id_criterio for n in niveles}) != len(niveles):
            raise EvaluacionInconsistente("Se requiere un único nivel por criterio.")
        obtenidos = {n.id_criterio: n.id_nivel for n in niveles}
        if set(obtenidos) != {c.id_criterio for c in rubrica.criterios}:
            raise EvaluacionInconsistente("Faltan criterios o hay criterios ajenos a la rúbrica.")
        if politica.formula == FormulaCalculo.PROMEDIO_IGUALITARIO_100:
            if rubrica.nota_maxima != Decimal(100):
                raise EvaluacionInconsistente("La escala aprobada es 0–100.")
            # Peso efectivo 1/N exacto. No modificar pesos históricos ni redondear
            # 100/3 a 33.33: eso inventaría una regla y perdería igualdad.
            resultados=[]
            for criterio in rubrica.criterios:
                nivel=next((n for n in criterio.niveles if n.id_nivel==obtenidos[criterio.id_criterio]),None)
                if nivel is None:
                    raise EvaluacionInconsistente("El nivel obtenido no pertenece al criterio.")
                fraccion=Fraction(nivel.logro_porcentaje)/len(rubrica.criterios)
                denominador=fraccion.denominator
                potencias={}
                for factor in (2,5):
                    potencia=0
                    while denominador % factor == 0:
                        denominador //= factor
                        potencia+=1
                    potencias[factor]=potencia
                if denominador != 1:
                    raise PoliticaEvaluacionPendiente("El aporte requiere precisión/redondeo todavía no aprobados.")
                escala=max(potencias.values())
                coeficiente=fraccion.numerator*2**(escala-potencias[2])*5**(escala-potencias[5])
                # Construir el Decimal exacto sin división bajo un contexto que
                # pudiera redondear logros de muchas cifras significativas.
                puntos=Decimal((0,Decimal(coeficiente).as_tuple().digits,-escala))
                resultados.append(ResultadoCriterio(criterio.id_criterio,nivel.id_nivel,puntos))
            with localcontext(Context(prec=sum(len(r.puntaje_obtenido.as_tuple().digits)+abs(r.puntaje_obtenido.as_tuple().exponent) for r in resultados)+20)):
                nota=sum((r.puntaje_obtenido for r in resultados),Decimal(0))
            return CalculoRubrica(tuple(resultados),nota,nota,politica.identificador)
        numeros = [rubrica.nota_maxima] + [
            valor for c in rubrica.criterios
            for valor in (c.peso_porcentaje, *(n.logro_porcentaje for n in c.niveles))
        ]
        # Precisión local suficiente para multiplicaciones y divisiones por potencias
        # de diez; no depender del contexto Decimal global ni redondear cada criterio.
        precision = sum(len(n.as_tuple().digits) + abs(n.as_tuple().exponent) for n in numeros) + politica.decimales + 20
        with localcontext(Context(prec=max(28, precision))):
            if sum((c.peso_porcentaje for c in rubrica.criterios), Decimal(0)) != Decimal(100):
                raise EvaluacionInconsistente("La fórmula porcentual exige pesos que sumen 100.")
            resultados = []
            for criterio in rubrica.criterios:
                nivel = next((n for n in criterio.niveles if n.id_nivel == obtenidos[criterio.id_criterio]), None)
                if nivel is None:
                    raise EvaluacionInconsistente("El nivel obtenido no pertenece al criterio.")
                puntos = rubrica.nota_maxima * criterio.peso_porcentaje * nivel.logro_porcentaje / Decimal(10000)
                resultados.append(ResultadoCriterio(criterio.id_criterio, nivel.id_nivel, puntos))
            nota = sum((r.puntaje_obtenido for r in resultados), Decimal(0))
            cuantizador = Decimal(1).scaleb(-politica.decimales)
            final = nota.quantize(cuantizador, rounding=politica.redondeo)
            if final > rubrica.nota_maxima:
                raise EvaluacionInconsistente("El redondeo produce una nota superior al máximo.")
            return CalculoRubrica(tuple(resultados), nota, final, politica.identificador)
