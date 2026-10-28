"""Rúbricas, mapeos y políticas FICTICIOS de prueba; nunca reglas oficiales de SPS."""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from app.modules.participation.application.errors import AccesoDenegado, ConflictoActualizacion
from app.modules.participation.domain.calculador_rubrica import FormulaCalculo, PlanCalculo, PoliticaCalculo
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.evaluation import (
    CriterioEvaluable, DatosEvaluacion, EvaluacionInconsistente, ModalidadEvaluacion,
    NivelEvaluable, NivelObtenido, PoliticaEvaluacionPendiente, ReferenciaAcademica, RubricaEvaluacion,
)
from app.modules.participation.tests.fakes import AlmacenFalso, CasesFalso, UnidadTrabajoFalsa


def rubrica_de_prueba() -> RubricaEvaluacion:
    return RubricaEvaluacion(
        ReferenciaAcademica(300, 400, "referencia-ficticia-v1"), Decimal("5"),
        (
            CriterioEvaluable(1, Decimal("60"), (
                NivelEvaluable(13, Decimal("100")), NivelEvaluable(14, Decimal("50")),
                NivelEvaluable(15, Decimal("0")),
            )),
            CriterioEvaluable(2, Decimal("40"), (
                NivelEvaluable(23, Decimal("100")), NivelEvaluable(24, Decimal("50")),
                NivelEvaluable(25, Decimal("0")),
            )),
        ),
    )


def politica_de_prueba() -> PoliticaCalculo:
    return PoliticaCalculo(
        "politica-ficticia-porcentual-v1", FormulaCalculo.SUMA_PONDERADA_PORCENTUAL,
        2, ROUND_HALF_UP,
    )


@dataclass
class CasesEvaluacionFalso(CasesFalso):
    rubrica: RubricaEvaluacion = field(default_factory=rubrica_de_prueba)

    def obtener_marco_evaluacion(self, *, id_caso, id_participacion, id_intento, selecciones):
        self._comprobar_fallo("rubrica")
        for seleccion in selecciones:
            self.validar_opcion(id_caso=id_caso, id_decision=seleccion.id_decision, id_opcion=seleccion.id_opcion)
        return self.rubrica, self.obtener_recorrido(id_caso=id_caso, selecciones=selecciones)


@dataclass
class PoliticaEvaluacionFalsa:
    modalidad_forzada: ModalidadEvaluacion | None = None
    parcial_definida: bool = False
    mapeo_definido: bool = True
    redondeo_definido: bool = True
    fallo_externo: bool = False
    ausencia_incorrecta: bool = False
    llamadas: int = 0

    def clasificar(self, *, intento, decisiones_aplicables) -> ModalidadEvaluacion:
        if self.modalidad_forzada is not None:
            return self.modalidad_forzada
        # Criterio de clasificación de esta fixture, no una regla del motor real.
        if intento.estado == EstadoIntento.VENCIDO:
            return ModalidadEvaluacion.PARCIAL
        if {p.id_decision for p in intento.pasos} == set(decisiones_aplicables):
            return ModalidadEvaluacion.COMPLETA
        return ModalidadEvaluacion.PARCIAL

    def preparar_calculo(self, *, datos: DatosEvaluacion, rubrica) -> PlanCalculo:
        self.llamadas += 1
        if self.fallo_externo:
            raise RuntimeError("Fallo de dependencia, no una política pendiente.")
        if not self.mapeo_definido:
            raise PoliticaEvaluacionPendiente("No existe mapeo de decisiones a niveles.")
        if datos.modalidad == ModalidadEvaluacion.PARCIAL and not self.parcial_definida:
            raise PoliticaEvaluacionPendiente("Falta política parcial aprobada.")
        if not self.redondeo_definido:
            raise PoliticaEvaluacionPendiente("Falta redondeo aprobado.")
        opciones = {e.id_decision: e.id_opcion for e in datos.evidencias}
        if datos.modalidad == ModalidadEvaluacion.AUSENCIA and self.ausencia_incorrecta:
            return PlanCalculo((NivelObtenido(1, 13), NivelObtenido(2, 23)), politica_de_prueba())
        # Los ceros para pendientes de PARCIAL se autorizan explícitamente solo
        # en esta política de prueba. No hay equivalente en código de producción.
        nivel_uno = {60: 13, 61: 14, None: 15}[opciones[50]]
        nivel_dos = {62: 23, 63: 24, None: 25}[opciones[51]]
        return PlanCalculo((NivelObtenido(1, nivel_uno), NivelObtenido(2, nivel_dos)), politica_de_prueba())


@dataclass
class AusenciasFalsas:
    permitida: bool = True
    llamadas: int = 0

    def confirmar_ausencia(self, **datos) -> None:
        self.llamadas += 1
        if not self.permitida:
            raise AccesoDenegado("No está convocado o aún no se cumplen condiciones de cierre.")


@dataclass
class AlmacenEvaluacionFalso(AlmacenFalso):
    evaluaciones: dict[tuple[int, int | None], DatosEvaluacion] = field(default_factory=dict)
    inserciones_evaluacion: int = 0

    def unidad_evaluacion(self) -> "UnidadEvaluacionFalsa":
        return UnidadEvaluacionFalsa(self)


class RepositorioResultadosFalso:
    def __init__(self, almacen: AlmacenEvaluacionFalso) -> None:
        self.almacen = almacen
        self.nuevos: dict[tuple[int, int | None], DatosEvaluacion] = {}

    def obtener_definitiva(self, *, id_participacion, id_intento) -> DatosEvaluacion | None:
        # Nunca devolver candidatos aún sin confirmar en esta unidad de trabajo.
        return self.almacen.evaluaciones.get((id_participacion, id_intento))

    def agregar_definitiva(self, datos: DatosEvaluacion) -> None:
        if not datos.lista_para_persistir:
            raise EvaluacionInconsistente("No puede persistirse un resultado pendiente.")
        clave = (datos.id_participacion, datos.id_intento)
        if clave in self.almacen.evaluaciones or clave in self.nuevos:
            raise ConflictoActualizacion("Ya existe una evaluación definitiva.")
        self.nuevos[clave] = datos


class UnidadEvaluacionFalsa(UnidadTrabajoFalsa):
    def __init__(self, almacen: AlmacenEvaluacionFalso) -> None:
        super().__init__(almacen)
        self.resultados = RepositorioResultadosFalso(almacen)

    def commit(self) -> None:
        # Super comprueba fallo/versionado antes de confirmar cualquier cambio.
        super().commit()
        self.almacen.evaluaciones.update(self.resultados.nuevos)
        self.almacen.inserciones_evaluacion += len(self.resultados.nuevos)
