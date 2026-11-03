from collections.abc import Callable
from types import TracebackType

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.modules.participation.application.errors import ConflictoActualizacion
from app.modules.participation.application.evaluation_ports import RepositorioResultados
from app.modules.participation.application.ports import RepositorioParticipacion
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente


class UnidadTrabajoSQLAlchemy:
    """Una sesión compartida por repositorios; una confirmación por caso de uso.

    No compone repositorios incompletos ni crea motores/tablas. Los constructores
    concretos se inyectarán cuando se apruebe su mapeo de escritura.
    """

    def __init__(
        self, crear_repositorio: Callable[[Session], RepositorioParticipacion], *,
        crear_resultados: Callable[[Session], RepositorioResultados] | None = None,
        crear_sesion: Callable[[], Session] | None = None,
    ) -> None:
        self._crear_repositorio = crear_repositorio
        self._crear_resultados = crear_resultados
        self._crear_sesion = crear_sesion
        self._sesion: Session | None = None
        self._repositorio: RepositorioParticipacion | None = None
        self._resultados: RepositorioResultados | None = None
        self._usada = False
        self._terminada = False

    def __enter__(self) -> "UnidadTrabajoSQLAlchemy":
        if self._usada:
            raise RuntimeError("Cada unidad de trabajo debe usarse una sola vez.")
        self._usada = True
        self._sesion = self._crear_sesion() if self._crear_sesion else get_session_factory()()
        if self._sesion.in_transaction():
            # La sesión no es nueva: no cerrar ni revertir la transacción ajena.
            self._sesion = None
            self._terminada = True
            raise RuntimeError("La fábrica debe entregar una sesión nueva sin transacción ajena.")
        try:
            self._sesion.begin()
            self._repositorio = self._crear_repositorio(self._sesion)
            if self._crear_resultados is not None:
                self._resultados = self._crear_resultados(self._sesion)
        except BaseException:
            self._sesion.close()
            self._sesion = None
            self._terminada = True
            raise
        return self

    def _activa(self) -> Session:
        if self._sesion is None or self._terminada:
            raise RuntimeError("La unidad de trabajo no está activa.")
        return self._sesion

    @property
    def sesion(self) -> Session:
        """Session activa para componer autorizadores de la misma operación."""
        return self._activa()

    @property
    def repositorio(self) -> RepositorioParticipacion:
        self._activa()
        if self._repositorio is None:
            raise RuntimeError("No se ha construido el repositorio.")
        return self._repositorio

    @property
    def resultados(self) -> RepositorioResultados:
        self._activa()
        if self._resultados is None:
            raise MapeoPersistenciaPendiente("Falta aprobar el mapeo íntegro de resultados de evaluación.")
        return self._resultados

    def commit(self) -> None:
        sesion = self._activa()
        try:
            # Session.commit incluye flush. Los repositorios no confirman por separado.
            sesion.commit()
        except DBAPIError as error:
            sesion.rollback()
            codigo = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
            if codigo in {"23505", "40001", "40P01"}:
                raise ConflictoActualizacion("Conflicto transaccional; vuelva a leer antes de reintentar.") from error
            raise
        except BaseException:
            sesion.rollback()
            raise
        finally:
            self._terminada = True

    def __exit__(
        self, tipo: type[BaseException] | None,
        error: BaseException | None, traceback: TracebackType | None,
    ) -> None:
        if self._sesion is not None:
            try:
                if self._sesion.in_transaction():
                    self._sesion.rollback()
            finally:
                self._sesion.close()
                self._sesion = None
                self._repositorio = None
                self._resultados = None
                self._terminada = True
        # Constraints inmediatas y SELECT FOR UPDATE pueden fallar antes de
        # commit. Mantener el mismo contrato de conflicto, después del rollback.
        if isinstance(error, DBAPIError):
            codigo = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
            if codigo in {"23505", "40001", "40P01"}:
                raise ConflictoActualizacion("Conflicto transaccional; vuelva a leer antes de reintentar.") from error
