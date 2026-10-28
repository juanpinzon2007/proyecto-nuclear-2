"""Transacción técnica reutilizando la fábrica SQLAlchemy común del backend.

Los constructores deben proporcionar adaptadores reales sobre la misma Session.
No define tablas, repositorios ficticios ni una Base/motor alternativos.
"""

from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.modules.identity.application.ports import (
    ConsultaEscrituraAcademica, RepositorioAutorizaciones, RepositorioFeedback, RepositorioUsuarios,
)


class UnidadTrabajoIdentitySQLAlchemy:
    def __init__(
        self, *, usuarios: Callable[[Session], RepositorioUsuarios],
        autorizaciones: Callable[[Session], RepositorioAutorizaciones],
        feedback: Callable[[Session], RepositorioFeedback],
        academia: Callable[[Session], ConsultaEscrituraAcademica],
        sesiones: Callable[[], Session] | None = None,
    ) -> None:
        self._constructores = (usuarios, autorizaciones, feedback, academia)
        self._sesiones = sesiones
        self._sesion: Session | None = None
        self._confirmada = False

    def __enter__(self) -> Self:
        if self._sesion is not None:
            raise RuntimeError("La unidad de trabajo ya está abierta.")
        self._sesion = (self._sesiones or get_session_factory())()
        self._confirmada = False
        try:
            self.usuarios, self.autorizaciones, self.feedback, self.academia = (
                construir(self._sesion) for construir in self._constructores
            )
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
