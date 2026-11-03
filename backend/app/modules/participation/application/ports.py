"""Puertos de Application; los adaptadores 8B no habilitan el inicio productivo."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from types import TracebackType
from typing import Callable, Protocol, Self

from app.modules.participation.application.dto import RecorridoAplicable, SeleccionDecision
from app.modules.participation.domain.entities import Intento, Participacion, IdentificadorCases


@dataclass(frozen=True)
class CondicionesIntento:
    """Proyección de Scheduling; no es una entidad ni un nuevo modelo de su módulo."""

    id_caso: int
    tiempo_maximo: timedelta


class CasesPort(Protocol):
    def validar_opcion(self, *, id_caso: int, id_decision: IdentificadorCases, id_opcion: IdentificadorCases) -> None:
        """Rechaza decisiones/opciones ajenas al caso o a la decisión indicada.

        No devuelve aciertos, justificaciones ni puntajes durante el intento.
        """
        ...

    def obtener_recorrido(
        self, *, id_caso: int, selecciones: tuple[SeleccionDecision, ...]
    ) -> RecorridoAplicable:
        """Devuelve la ruta aplicable, no todas las decisiones del caso.

        Rechaza un estado incoherente; no devuelve corrección ni puntajes.
        """
        ...

    def validar_cambio_conservando_pasos(
        self,
        *,
        id_caso: int,
        selecciones: tuple[SeleccionDecision, ...],
        propuesta: SeleccionDecision,
    ) -> None:
        """Autoriza guardar la propuesta conservando todas las otras selecciones.

        Debe rechazar con ReglaPendiente si requiere resolver una política de
        invalidación/ramificación no aprobada. Nunca asumir aceptación por defecto.
        """
        ...


class IdentityPort(Protocol):
    def autorizar_inicio(
        self,
        *,
        id_estudiante: int,
        id_participacion: int,
        id_grupo_estudiante: int,
        id_consentimiento: int,
        id_permiso_extra: int | None,
    ) -> None:
        """Exige identidad, consentimiento y permiso vinculado a esta participación."""
        ...

    def autorizar_acceso(self, *, id_estudiante: int, id_participacion: int) -> None:
        """Rechaza acceso a participaciones fuera del ámbito del solicitante."""
        ...


class SchedulingPort(Protocol):
    def obtener_condiciones(
        self, *, id_asignacion: int, id_grupo_estudiante: int
    ) -> CondicionesIntento:
        """Exige asignación habilitada, pertenencia y ventana de ingreso válida.

        La duración debe proceder de la programación aprobada. La política de
        ingreso tardío y la autorización de nuevos intentos no se deducen aquí.
        """
        ...

    def autorizar_nuevo_intento(
        self, *, id_asignacion: int, id_grupo_estudiante: int,
        numero_intento: int, id_permiso_extra: int | None,
    ) -> None:
        """Exige cupo según intentos base/excepcionales y condiciones aprobadas.

        No deducir ni implementar aquí una política académica de repetición.
        """
        ...

    def validar_edicion(self, *, id_asignacion: int, id_grupo_estudiante: int, operacion: str = "RESPONDER") -> None:
        """Rechaza edición si la asignación o la pertenencia ya no la permiten."""
        ...

    def validar_instante_registro(self, *, instante: datetime) -> None:
        """Revalida la hora del paso sobre las condiciones bloqueadas de esta UoW.

        Evita que una validación iniciada antes del cierre registre un paso fuera
        de horario. No acepta una autorización de otra transacción.
        """
        ...

    def obtener_id_caso(self, *, id_asignacion: int) -> int:
        """Consulta el caso asociado incluso tras el cierre, sin reautorizar ingreso.

        No debe sustituir la duración individual ya conservada en el intento.
        """
        ...


class RepositorioParticipacion(Protocol):
    """Persistencia del agregado; no implementada en este incremento.

    Las lecturas para mutación deben serializarse dentro de la unidad de trabajo:
    bloquear participación al iniciar e intento al modificar/cerrar, o proporcionar
    una garantía equivalente. Nunca implementar guardar como upsert incondicional.
    """

    def obtener_participacion(self, id_participacion: int) -> Participacion: ...

    def obtener_intento(self, id_intento: int) -> Intento: ...

    def listar_intentos(self, id_participacion: int) -> tuple[Intento, ...]: ...

    def nuevo_id_intento(self) -> int: ...

    def nuevo_id_paso(self) -> int: ...

    def agregar_intento(self, intento: Intento) -> None:
        """Rechaza duplicidad de ID, número o intento activo por participación."""
        ...

    def guardar_intento(self, intento: Intento, *, esperado: Intento) -> None:
        """Guarda el objeto nuevo; rechaza un estado previo distinto del esperado."""
        ...


class UnidadTrabajo(Protocol):
    repositorio: RepositorioParticipacion

    def __enter__(self) -> Self: ...

    def __exit__(
        self, tipo: type[BaseException] | None,
        error: BaseException | None, traceback: TracebackType | None,
    ) -> None:
        """Descarta cambios sin commit, incluso si falla una dependencia."""
        ...

    def commit(self) -> None:
        """Confirma atómicamente el agregado y sus pasos, o falla sin confirmarlos."""
        ...


FabricaUnidadTrabajo = Callable[[], UnidadTrabajo]
