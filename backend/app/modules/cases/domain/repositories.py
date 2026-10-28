"""Puerto de persistencia del agregado Caso (el dominio no conoce SQLAlchemy)."""

import uuid
from abc import ABC, abstractmethod

from app.modules.cases.domain.entities.caso import ResumenVersion, VersionCaso


class ICasoRepository(ABC):
    @abstractmethod
    def guardar(self, version: VersionCaso) -> None:
        """Persiste la versión completa de forma atómica.

        Raises:
            ErrorPersistenciaCaso: si la transacción falla (se hace rollback).
        """

    @abstractmethod
    def obtener_version(
        self, version_id: uuid.UUID, docente_creador_id: uuid.UUID
    ) -> VersionCaso | None:
        """Reconstruye la versión si existe y pertenece al docente; si no, ``None``."""

    @abstractmethod
    def listar_por_docente(self, docente_creador_id: uuid.UUID) -> list[ResumenVersion]:
        """Resumen de las versiones del docente, más recientes primero."""

    @abstractmethod
    def reemplazar(self, version: VersionCaso) -> None:
        """Reemplaza la estructura de una versión existente (mismo ``id``) en una transacción.

        Raises:
            ErrorPersistenciaCaso: si falla; el contenido anterior se conserva (rollback).
        """

    @abstractmethod
    def actualizar_estado(self, version: VersionCaso) -> None:
        """Persiste únicamente el estado de una versión existente (commit atómico).

        Raises:
            ErrorPersistenciaCaso: si la transacción falla (se hace rollback).
        """
