from app.modules.participation.application.dto import EstadoEvaluacion, ProgresoIntento, ResumenIntento
from app.modules.participation.application.errors import ReglaPendiente
from app.modules.participation.application.evaluation_service import ServicioEvaluacion
from app.modules.participation.application.ports import (
    CasesPort, FabricaUnidadTrabajo, IdentityPort, SchedulingPort,
)
from app.modules.participation.application.services import (
    ServicioCierre, ServicioDecisiones, ServicioInicio, ServicioProgreso,
)
from app.modules.participation.domain.clock import Reloj
from app.modules.participation.domain.evaluation import DatosEvaluacion


class ParticipacionFacade:
    """Punto de entrada de Application; requiere adaptadores explícitos y reloj."""

    def __init__(
        self, *, fabrica: FabricaUnidadTrabajo, identity: IdentityPort,
        cases: CasesPort, scheduling: SchedulingPort, reloj: Reloj,
        evaluacion: ServicioEvaluacion | None = None,
    ) -> None:
        self._inicio = ServicioInicio(fabrica, identity, scheduling, reloj)
        self._decisiones = ServicioDecisiones(fabrica, identity, scheduling, cases, reloj)
        self._progreso = ServicioProgreso(fabrica, identity, scheduling, cases, reloj)
        self._cierre = ServicioCierre(fabrica, identity, reloj)
        self._evaluacion = evaluacion

    def iniciar_intento(
        self, *, id_estudiante: int, id_participacion: int,
        id_consentimiento: int, id_permiso_extra: int | None = None,
    ) -> ResumenIntento:
        return self._inicio.iniciar(
            id_estudiante=id_estudiante, id_participacion=id_participacion,
            id_consentimiento=id_consentimiento, id_permiso_extra=id_permiso_extra,
        )

    def registrar_decision(
        self, *, id_estudiante: int, id_intento: int, id_decision: int,
        id_opcion: int, reflexion_estudiante: str | None = None,
    ) -> ResumenIntento:
        return self._decisiones.guardar(
            id_estudiante=id_estudiante, id_intento=id_intento, id_decision=id_decision,
            id_opcion=id_opcion, reflexion_estudiante=reflexion_estudiante, modificar=False,
        )

    def modificar_decision(
        self, *, id_estudiante: int, id_intento: int, id_decision: int,
        id_opcion: int, reflexion_estudiante: str | None = None,
    ) -> ResumenIntento:
        return self._decisiones.guardar(
            id_estudiante=id_estudiante, id_intento=id_intento, id_decision=id_decision,
            id_opcion=id_opcion, reflexion_estudiante=reflexion_estudiante, modificar=True,
        )

    def consultar_progreso(self, *, id_estudiante: int, id_intento: int) -> ProgresoIntento:
        return self._progreso.consultar(id_estudiante=id_estudiante, id_intento=id_intento)

    def finalizar(self, *, id_estudiante: int, id_intento: int) -> ResumenIntento:
        return self._cierre.cerrar(
            id_estudiante=id_estudiante, id_intento=id_intento, solo_si_vencio=False,
        )

    def procesar_vencimiento(self, *, id_estudiante: int, id_intento: int) -> ResumenIntento:
        return self._cierre.cerrar(
            id_estudiante=id_estudiante, id_intento=id_intento, solo_si_vencio=True,
        )

    def _motor_evaluacion(self) -> ServicioEvaluacion:
        if self._evaluacion is None:
            raise ReglaPendiente("Faltan adaptadores y políticas de evaluación explícitos.")
        return self._evaluacion

    def evaluar_intento(self, *, id_estudiante: int, id_intento: int) -> EstadoEvaluacion:
        return self._motor_evaluacion().evaluar_intento(id_estudiante=id_estudiante, id_intento=id_intento)

    def evaluar_ausencia(self, *, id_estudiante: int, id_participacion: int) -> EstadoEvaluacion:
        return self._motor_evaluacion().evaluar_ausencia(
            id_estudiante=id_estudiante, id_participacion=id_participacion,
        )

    def consultar_evaluacion(
        self, *, id_estudiante: int, id_participacion: int, id_intento: int | None,
    ) -> DatosEvaluacion:
        return self._motor_evaluacion().consultar_evaluacion(
            id_estudiante=id_estudiante, id_participacion=id_participacion, id_intento=id_intento,
        )
