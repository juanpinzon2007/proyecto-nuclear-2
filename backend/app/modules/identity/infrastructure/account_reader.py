"""Lectura breve de identidad HTTP, independiente de las UoW escritoras."""
from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling


class ConsultaCuentaPorIdSQLAlchemy:
    def __init__(self, crear_sesion: Callable[[], Session]):
        self.crear_sesion = crear_sesion

    def obtener(self, id_usuario: str) -> ContextoAcceso | None:
        try:
            with self.crear_sesion() as sesion:
                return RepositorioUsuariosSQLAlchemy(sesion).obtener(id_usuario)
        except (ValueError, SQLAlchemyError):
            raise IntegracionPendiente() from None


class ConsultaVinculosSesionBreveSQLAlchemy:
    def __init__(self, crear_sesion: Callable[[], Session]):
        self.crear_sesion = crear_sesion

    def obtener(self, *, id_usuario, sistema):
        try:
            with self.crear_sesion() as sesion:
                return RepositorioIdentidadAcademicaSQLAlchemy(sesion).obtener(
                    id_usuario=id_usuario, sistema=sistema)
        except (ValueError, SQLAlchemyError):
            raise IntegracionPendiente() from None


class ValidadorContextoSesionBreveSQLAlchemy:
    def __init__(self, crear_sesion: Callable[[], Session]):
        self.crear_sesion = crear_sesion

    def validar_contexto(self, *, id_usuario, contexto, solicitada):
        try:
            with self.crear_sesion() as sesion:
                resolver = ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(sesion))
                validador = ValidadorConvocatoriaScheduling(sesion, RepositorioUsuariosSQLAlchemy(sesion), resolver)
                return validador.validar_contexto(id_usuario=id_usuario, contexto=contexto, solicitada=solicitada)
        except (ValueError, SQLAlchemyError):
            raise IntegracionPendiente() from None
