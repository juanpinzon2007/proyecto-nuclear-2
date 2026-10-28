"""Contratos nuevos de consumo; no modifican implementaciones de otros módulos."""

from decimal import Decimal
from typing import Callable, Protocol

from app.modules.participation.application.dto import RecorridoAplicable, SeleccionDecision
from app.modules.participation.application.ports import CasesPort, UnidadTrabajo
from app.modules.participation.domain.calculador_rubrica import PlanCalculo
from app.modules.participation.domain.entities import Intento
from app.modules.participation.domain.evaluation import (
    DatosEvaluacion, ModalidadEvaluacion, RubricaEvaluacion,
)


class CasesEvaluacionPort(CasesPort, Protocol):
    def obtener_marco_evaluacion(
        self, *, id_caso: int, id_participacion: int, id_intento: int | None,
        selecciones: tuple[SeleccionDecision, ...],
    ) -> tuple[RubricaEvaluacion, RecorridoAplicable]:
        """Entrega rúbrica y recorrido coherentes de una referencia inmutable.

        Valida las decisiones/opciones en esa misma referencia. Debe corresponder
        al contenido usado por el intento, no a una edición posterior. Recibe
        su identidad para recuperar el contexto histórico, sin crear versionado
        ficticio. Si no puede garantizarlo, rechazar con política pendiente.
        """
        ...


class PoliticaEvaluacionPort(Protocol):
    def clasificar(
        self, *, intento: Intento, decisiones_aplicables: tuple[int, ...]
    ) -> ModalidadEvaluacion:
        """Clasifica académicamente; no equipara sin regla estados y modalidades."""
        ...

    def preparar_calculo(self, *, datos: DatosEvaluacion, rubrica: RubricaEvaluacion) -> PlanCalculo:
        """Determina niveles y suministra fórmula/redondeo explícitos.

        Para parciales debe resolver expresamente las decisiones sin respuesta.
        Sin una regla suficiente lanza PoliticaEvaluacionPendiente. No consolidar
        aquí los resultados de múltiples intentos.
        """
        ...


class PoliticaConsolidacionPort(Protocol):
    def consolidar(self, *, id_participacion: int, resultados: tuple[DatosEvaluacion, ...]) -> Decimal:
        """Contrato pendiente, sin implementación ni conexión en este incremento.

        Debe decidir intentos aplicables, regla de selección/agregación y redondeo.
        No hay una política predeterminada de mejor nota, última nota o promedio.
        """
        ...


class AusenciasPort(Protocol):
    def confirmar_ausencia(self, *, id_asignacion: int, id_grupo_estudiante: int) -> None:
        """Exige convocatoria real, ausencia y condiciones de cierre cumplidas.

        El servicio verifica además que no exista ningún intento; una consulta
        sin filas por sí sola no acredita ausencia académica.
        """
        ...


class RepositorioResultados(Protocol):
    def obtener_definitiva(self, *, id_participacion: int, id_intento: int | None) -> DatosEvaluacion | None:
        """Solo devuelve evaluaciones previamente confirmadas, nunca borradores."""
        ...

    def agregar_definitiva(self, datos: DatosEvaluacion) -> None:
        """Inserta sin upsert: rechaza pendientes y duplicados por clave académica.

        Debe conservar referencia, políticas y precisión necesarias para reproducir
        la nota. Un mapeo al ER no aprobado debe rechazarse, nunca inventarse.
        """
        ...


class UnidadTrabajoEvaluacion(UnidadTrabajo, Protocol):
    resultados: RepositorioResultados
    # El mismo commit confirma todos los cambios. Serializar sobre el intento o
    # participación para ausencia, y garantizar unicidad también en almacenamiento.


FabricaUnidadTrabajoEvaluacion = Callable[[], UnidadTrabajoEvaluacion]
