"""Transacción técnica reutilizando la fábrica SQLAlchemy común del backend.

Los constructores deben proporcionar adaptadores reales sobre la misma Session.
No define tablas, repositorios ficticios ni una Base/motor alternativos.
"""

from collections.abc import Callable
from types import TracebackType
from typing import Self, cast

from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.application.ports import (
    ConsultaEscrituraAcademica, RepositorioAutorizaciones, RepositorioFeedback, RepositorioUsuarios,
)


class UnidadTrabajoIdentitySQLAlchemy:
    def __init__(
        self, *, usuarios: Callable[[Session], RepositorioUsuarios],
        autorizaciones: Callable[[Session], RepositorioAutorizaciones] | None = None,
        feedback: Callable[[Session], RepositorioFeedback] | None = None,
        academia: Callable[[Session], ConsultaEscrituraAcademica] | None = None,
        sesiones: Callable[[], Session] | None = None,
    ) -> None:
        self._constructores = (usuarios, autorizaciones, feedback, academia)
        self._sesiones = sesiones
        self._sesion: Session | None = None
        self._confirmada = False
        self._adaptadores: dict[str, object] = {}

    def _adaptador(self, nombre: str):
        if nombre not in self._adaptadores:
            raise IntegracionPendiente()
        return self._adaptadores[nombre]

    @property
    def usuarios(self) -> RepositorioUsuarios:
        return cast(RepositorioUsuarios, self._adaptador("usuarios"))

    @property
    def autorizaciones(self) -> RepositorioAutorizaciones:
        return cast(RepositorioAutorizaciones, self._adaptador("autorizaciones"))

    @property
    def feedback(self) -> RepositorioFeedback:
        return cast(RepositorioFeedback, self._adaptador("feedback"))

    @property
    def academia(self) -> ConsultaEscrituraAcademica:
        return cast(ConsultaEscrituraAcademica, self._adaptador("academia"))

    def __enter__(self) -> Self:
        if self._sesion is not None:
            raise RuntimeError("La unidad de trabajo ya está abierta.")
        self._sesion = (self._sesiones or get_session_factory())()
        self._confirmada = False
        try:
            for nombre, construir in zip(("usuarios", "autorizaciones", "feedback", "academia"), self._constructores):
                if construir is not None:
                    self._adaptadores[nombre] = construir(self._sesion)
        except BaseException:
            self._cerrar()
            raise
        return self

    def commit(self) -> None:
        if self._sesion is None or self._confirmada:
            raise RuntimeError("No hay una transacción pendiente para confirmar.")
        try:
            self._sesion.commit()
        except BaseException:
            self._sesion.rollback()
            raise
        self._confirmada = True

    def _cerrar(self) -> None:
        self._adaptadores.clear()
        sesion, self._sesion = self._sesion, None
        if sesion is not None:
            try:
                # También descarta trabajo accidental iniciado después de commit.
                sesion.rollback()
            finally:
                sesion.close()

    def __exit__(self, tipo: type[BaseException] | None, error: BaseException | None,
                 traceback: TracebackType | None) -> None:
        self._cerrar()
