"""Tipos y utilidades compartidas por los modelos ORM del módulo de casos."""

import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column


def uuid_pk() -> Mapped[uuid.UUID]:
    """Clave primaria UUID generada en la aplicación (portable entre motores)."""
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

