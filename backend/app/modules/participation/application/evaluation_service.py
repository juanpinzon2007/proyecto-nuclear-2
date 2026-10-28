from dataclasses import dataclass, replace

from app.modules.participation.application.dto import EstadoEvaluacion, selecciones_de
from app.modules.participation.application.errors import RecursoNoDisponible
from app.modules.participation.application.evaluation_ports import (
    AusenciasPort, CasesEvaluacionPort, FabricaUnidadTrabajoEvaluacion,
    PoliticaEvaluacionPort, UnidadTrabajoEvaluacion,
)
from app.modules.participation.application.ports import IdentityPort, SchedulingPort
from app.modules.participation.application.services import _cargar_autorizado
from app.modules.participation.domain.calculador_rubrica import CalculadorRubrica
from app.modules.participation.domain.entities import EstadoIntento, Intento
from app.modules.participation.domain.estrategias_evaluacion import (
    EvaluacionAusenciaStrategy, EvaluacionCompletaStrategy, EvaluacionParcialStrategy,
    IEstrategiaEvaluacion,
)
from app.modules.participation.domain.evaluation import (
    CALCULO_PENDIENTE, ContextoEvaluacion, DatosEvaluacion, EvaluacionInconsistente,
    ModalidadEvaluacion, PoliticaEvaluacionPendiente, RubricaEvaluacion,
)


def seleccionar_estrategia(modalidad: ModalidadEvaluacion) -> IEstrategiaEvaluacion:
    if not isinstance(modalidad, ModalidadEvaluacion):
        raise EvaluacionInconsistente("La clasificación no es una modalidad reconocida.")
    return {
        ModalidadEvaluacion.COMPLETA: EvaluacionCompletaStrategy(),
        ModalidadEvaluacion.PARCIAL: EvaluacionParcialStrategy(),
        ModalidadEvaluacion.AUSENCIA: EvaluacionAusenciaStrategy(),
    }[modalidad]


def _estado(datos: DatosEvaluacion, *, confirmada: bool) -> EstadoEvaluacion:
    return EstadoEvaluacion(
        datos.id_participacion, datos.id_intento, datos.modalidad, confirmada, datos.pendientes,
    )


@dataclass(frozen=True)
class ServicioEvaluacion:
    fabrica: FabricaUnidadTrabajoEvaluacion
    identity: IdentityPort
    scheduling: SchedulingPort
    cases: CasesEvaluacionPort
    politica: PoliticaEvaluacionPort
    ausencias: AusenciasPort

    def _existente(
        self, trabajo: UnidadTrabajoEvaluacion, id_participacion: int, id_intento: int | None,
    ) -> DatosEvaluacion | None:
        datos = trabajo.resultados.obtener_definitiva(
            id_participacion=id_participacion, id_intento=id_intento,
        )
        if datos is not None and (
            datos.id_participacion != id_participacion or datos.id_intento != id_intento
            or not datos.lista_para_persistir
        ):
            raise EvaluacionInconsistente("El repositorio devolvió un resultado incoherente o pendiente.")
        return datos

    def _marco(
        self, id_asignacion: int, id_participacion: int, intento: Intento | None,
    ) -> tuple[RubricaEvaluacion, tuple[int, ...]]:
        id_caso = self.scheduling.obtener_id_caso(id_asignacion=id_asignacion)
        selecciones = selecciones_de(intento) if intento is not None else ()
        rubrica, ruta = self.cases.obtener_marco_evaluacion(
            id_caso=id_caso, id_participacion=id_participacion,
            id_intento=intento.id_intento if intento is not None else None,
            selecciones=selecciones,
        )
        if rubrica.referencia.id_caso != id_caso:
            raise EvaluacionInconsistente("La rúbrica corresponde a otro caso.")
        if not ruta.total_conocido:
            raise PoliticaEvaluacionPendiente("Cases no ha definido el recorrido completo evaluable.")
        return rubrica, ruta.decisiones

    def _calcular(self, datos: DatosEvaluacion, rubrica: RubricaEvaluacion) -> DatosEvaluacion:
        try:
            plan = self.politica.preparar_calculo(datos=datos, rubrica=rubrica)
            calculo = CalculadorRubrica().calcular(rubrica, plan.niveles, plan.politica)
        except PoliticaEvaluacionPendiente as error:
            return replace(datos, pendientes=(*datos.pendientes, str(error)))
        return replace(
            datos, criterios=calculo.criterios, nota_final=calculo.nota_final,
            politica_calculo=calculo.politica,
            pendientes=tuple(p for p in datos.pendientes if p != CALCULO_PENDIENTE),
        )

    def _confirmar(self, trabajo: UnidadTrabajoEvaluacion, datos: DatosEvaluacion) -> EstadoEvaluacion:
        if not datos.lista_para_persistir:
            return _estado(datos, confirmada=False)
        trabajo.resultados.agregar_definitiva(datos)
        trabajo.commit()
        # Se devuelve confirmación sin nota; la lectura académica es independiente.
        return _estado(datos, confirmada=True)

    def evaluar_intento(self, *, id_estudiante: int, id_intento: int) -> EstadoEvaluacion:
        with self.fabrica() as trabajo:
            intento, participacion = _cargar_autorizado(
                trabajo.repositorio, self.identity, id_estudiante, id_intento,
            )
            if intento.estado == EstadoIntento.EN_CURSO:
                raise EvaluacionInconsistente("Primero debe confirmarse el cierre del intento.")
            existente = self._existente(trabajo, participacion.id_participacion, id_intento)
            if existente is not None:
                return _estado(existente, confirmada=True)
            rubrica, decisiones = self._marco(participacion.id_asignacion, participacion.id_participacion, intento)
            modalidad = self.politica.clasificar(intento=intento, decisiones_aplicables=decisiones)
            contexto = ContextoEvaluacion(
                rubrica.referencia, participacion.id_participacion, modalidad, decisiones, intento,
            )
            datos = seleccionar_estrategia(modalidad).preparar(contexto)
            return self._confirmar(trabajo, self._calcular(datos, rubrica))

    def evaluar_ausencia(self, *, id_estudiante: int, id_participacion: int) -> EstadoEvaluacion:
        with self.fabrica() as trabajo:
            participacion = trabajo.repositorio.obtener_participacion(id_participacion)
            self.identity.autorizar_acceso(id_estudiante=id_estudiante, id_participacion=id_participacion)
            if trabajo.repositorio.listar_intentos(id_participacion):
                raise EvaluacionInconsistente("Una participación con intentos no es una ausencia.")
            existente = self._existente(trabajo, id_participacion, None)
            if existente is not None:
                return _estado(existente, confirmada=True)
            self.ausencias.confirmar_ausencia(
                id_asignacion=participacion.id_asignacion,
                id_grupo_estudiante=participacion.id_grupo_estudiante,
            )
            rubrica, decisiones = self._marco(participacion.id_asignacion, id_participacion, None)
            contexto = ContextoEvaluacion(
                rubrica.referencia, id_participacion, ModalidadEvaluacion.AUSENCIA,
                decisiones, None, ausencia_confirmada=True,
            )
            datos = EvaluacionAusenciaStrategy().preparar(contexto)
            return self._confirmar(trabajo, self._calcular(datos, rubrica))

    def consultar_evaluacion(
        self, *, id_estudiante: int, id_participacion: int, id_intento: int | None,
    ) -> DatosEvaluacion:
        with self.fabrica() as trabajo:
            trabajo.repositorio.obtener_participacion(id_participacion)
            self.identity.autorizar_acceso(id_estudiante=id_estudiante, id_participacion=id_participacion)
            if id_intento is not None:
                intento = trabajo.repositorio.obtener_intento(id_intento)
                if intento.id_participacion != id_participacion or intento.estado == EstadoIntento.EN_CURSO:
                    raise EvaluacionInconsistente("El resultado no corresponde a un intento cerrado propio.")
            elif trabajo.repositorio.listar_intentos(id_participacion):
                raise EvaluacionInconsistente("No corresponde consultar una ausencia con intentos reales.")
            datos = self._existente(trabajo, id_participacion, id_intento)
            if datos is None:
                raise RecursoNoDisponible("No existe una evaluación confirmada para consultar.")
            return datos
