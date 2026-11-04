from dataclasses import dataclass

from app.modules.participation.application.dto import (
    ProgresoIntento, ResumenIntento, SeleccionDecision, selecciones_de,
)
from app.modules.participation.application.errors import ErrorAplicacionParticipacion, ReglaPendiente
from app.modules.participation.application.ports import (
    CasesPort, FabricaUnidadTrabajo, IdentityPort, RepositorioParticipacion, SchedulingPort,
)
from app.modules.participation.domain.clock import Reloj
from app.modules.participation.domain.entities import EstadoIntento, Intento, Participacion, IdentificadorCases
from app.modules.participation.domain.errors import IntentoNoEditable, RespuestaInmutable


def _cargar_autorizado(
    repositorio: RepositorioParticipacion, identity: IdentityPort,
    id_estudiante: int, id_intento: int,
) -> tuple[Intento, Participacion]:
    intento = repositorio.obtener_intento(id_intento)
    participacion = repositorio.obtener_participacion(intento.id_participacion)
    identity.autorizar_acceso(
        id_estudiante=id_estudiante, id_participacion=participacion.id_participacion,
    )
    return intento, participacion


@dataclass(frozen=True)
class ServicioInicio:
    fabrica: FabricaUnidadTrabajo
    identity: IdentityPort
    scheduling: SchedulingPort
    reloj: Reloj

    def iniciar(
        self, *, id_estudiante: int, id_participacion: int,
        id_consentimiento: int, id_permiso_extra: int | None = None,
    ) -> ResumenIntento:
        # La participación ya existe; no se inventa aquí su estado ni convocatoria.
        with self.fabrica() as trabajo:
            resultado = self.preparar(trabajo=trabajo, id_estudiante=id_estudiante,
                id_participacion=id_participacion, id_consentimiento=id_consentimiento,
                id_permiso_extra=id_permiso_extra)
            trabajo.commit()
            return resultado

    def preparar(self, *, trabajo, id_estudiante: int, id_participacion: int,
                 id_consentimiento: int, id_permiso_extra: int | None = None) -> ResumenIntento:
        """Mismas reglas en una UoW activa; el coordinador conserva commit/rollback.

        Permite crear participación e intento atómicamente, sin transacciones
        anidadas ni copiar las reglas del inicio ya implementado.
        """
        repo = trabajo.repositorio
        participacion = repo.obtener_participacion(id_participacion)
        self.identity.autorizar_acceso(id_estudiante=id_estudiante,id_participacion=id_participacion)
        self.identity.autorizar_inicio(id_estudiante=id_estudiante,id_participacion=id_participacion,
            id_grupo_estudiante=participacion.id_grupo_estudiante,
            id_consentimiento=id_consentimiento,id_permiso_extra=id_permiso_extra)
        previos = repo.listar_intentos(id_participacion)
        if any(i.estado == EstadoIntento.EN_CURSO for i in previos):
            raise ErrorAplicacionParticipacion("Ya existe un intento en curso; recupérelo o procese su vencimiento.")
        condiciones = self.scheduling.obtener_condiciones(id_asignacion=participacion.id_asignacion,
            id_grupo_estudiante=participacion.id_grupo_estudiante)
        numero = max((i.numero_intento for i in previos),default=0)+1
        self.scheduling.autorizar_nuevo_intento(id_asignacion=participacion.id_asignacion,
            id_grupo_estudiante=participacion.id_grupo_estudiante,
            numero_intento=numero,id_permiso_extra=id_permiso_extra)
        intento = Intento.iniciar(id_intento=repo.nuevo_id_intento(),id_participacion=id_participacion,
            id_consentimiento=id_consentimiento,numero_intento=numero,
            tiempo_maximo=condiciones.tiempo_maximo,reloj=self.reloj,id_permiso_extra=id_permiso_extra)
        self.scheduling.validar_instante_inicio(instante=intento.inicio)
        repo.agregar_intento(intento)
        return ResumenIntento.desde(intento)


@dataclass(frozen=True)
class ServicioDecisiones:
    fabrica: FabricaUnidadTrabajo
    identity: IdentityPort
    scheduling: SchedulingPort
    cases: CasesPort
    reloj: Reloj

    def guardar(
        self, *, id_estudiante: int, id_intento: int, id_decision: IdentificadorCases,
        id_opcion: IdentificadorCases, modificar: bool, reflexion_estudiante: str | None = None,
    ) -> ResumenIntento:
        with self.fabrica() as trabajo:
            repo = trabajo.repositorio
            anterior, participacion = _cargar_autorizado(
                repo, self.identity, id_estudiante, id_intento,
            )
            actual = anterior.actualizar_vencimiento(self.reloj)
            if actual.estado != EstadoIntento.EN_CURSO:
                if actual is not anterior:
                    repo.guardar_intento(actual, esperado=anterior)
                    trabajo.commit()
            else:
                if modificar or any(p.id_decision == id_decision for p in actual.pasos):
                    raise RespuestaInmutable("Las respuestas registradas son inmutables; PUT no está permitido.")
                self.scheduling.validar_edicion(
                    id_asignacion=participacion.id_asignacion,
                    id_grupo_estudiante=participacion.id_grupo_estudiante,
                    operacion="RESPONDER",
                )
                id_caso = self.scheduling.obtener_id_caso(id_asignacion=participacion.id_asignacion)
                self.cases.validar_opcion(
                    id_caso=id_caso, id_decision=id_decision, id_opcion=id_opcion,
                )
                self.cases.validar_cambio_conservando_pasos(
                    id_caso=id_caso, selecciones=selecciones_de(actual),
                    propuesta=SeleccionDecision(id_decision, id_opcion),
                )
                nuevo = actual.registrar_decision(
                    id_paso=repo.nuevo_id_paso(), id_decision=id_decision,
                    id_opcion=id_opcion, reloj=self.reloj,
                    reflexion_estudiante=reflexion_estudiante,
                )
                self.scheduling.validar_instante_registro(instante=nuevo.pasos[-1].registrado_en)
                repo.guardar_intento(nuevo, esperado=anterior)
                trabajo.commit()
                return ResumenIntento.desde(nuevo)
        # El vencimiento se confirma antes de comunicar el rechazo de la selección.
        raise IntentoNoEditable("El intento está cerrado o su tiempo individual se agotó.")


@dataclass(frozen=True)
class ServicioProgreso:
    fabrica: FabricaUnidadTrabajo
    identity: IdentityPort
    scheduling: SchedulingPort
    cases: CasesPort
    reloj: Reloj

    def consultar(self, *, id_estudiante: int, id_intento: int) -> ProgresoIntento:
        with self.fabrica() as trabajo:
            repo = trabajo.repositorio
            anterior, participacion = _cargar_autorizado(
                repo, self.identity, id_estudiante, id_intento,
            )
            actual = anterior.actualizar_vencimiento(self.reloj)
            id_caso = self.scheduling.obtener_id_caso(id_asignacion=participacion.id_asignacion)
            ruta = self.cases.obtener_recorrido(id_caso=id_caso, selecciones=selecciones_de(actual))
            selecciones = selecciones_de(actual)
            if ruta.disponible and any(s.id_decision not in ruta.decisiones for s in selecciones):
                raise ReglaPendiente(
                    "El recorrido excluye selecciones conservadas; debe resolverse su tratamiento."
                )
            respondidas = {s.id_decision for s in selecciones}
            resultado = ProgresoIntento(
                intento=ResumenIntento.desde(actual), decisiones_aplicables=ruta.decisiones if ruta.disponible else None,
                selecciones=selecciones,
                pendientes=tuple(d for d in ruta.decisiones if d not in respondidas) if ruta.disponible else None,
                total_aplicable=len(ruta.decisiones) if ruta.total_conocido else None,
            )
            if actual is not anterior:
                repo.guardar_intento(actual, esperado=anterior)
                trabajo.commit()
            return resultado


@dataclass(frozen=True)
class ServicioCierre:
    fabrica: FabricaUnidadTrabajo
    identity: IdentityPort
    reloj: Reloj

    def cerrar(
        self, *, id_estudiante: int, id_intento: int, solo_si_vencio: bool,
    ) -> ResumenIntento:
        with self.fabrica() as trabajo:
            repo = trabajo.repositorio
            anterior, _ = _cargar_autorizado(repo, self.identity, id_estudiante, id_intento)
            actual = (
                anterior.actualizar_vencimiento(self.reloj)
                if solo_si_vencio else anterior.finalizar(self.reloj)
            )
            if actual is not anterior:
                repo.guardar_intento(actual, esperado=anterior)
                trabajo.commit()
            # La evaluación explícita consume después este cierre confirmado.
            # Un fallo académico no revierte el cierre ni duplica sus efectos.
            return ResumenIntento.desde(actual)
