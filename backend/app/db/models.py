"""Registro explícito del esquema integrado y validación de sus dependencias.

No crea tablas ni completa FK con placeholders. Los modelos académicos que aún
no tienen contrato/esquema integrado se conservan en su metadata pendiente.
"""

from sqlalchemy import MetaData

from app.db.base import Base


def validar_referencias(metadata: MetaData) -> None:
    """Falla explícitamente si cualquier FK registrada no se puede resolver."""
    for tabla in metadata.tables.values():
        for referencia in tabla.foreign_keys:
            _ = referencia.column


def registrar_modelos_integrados() -> MetaData:
    # Ambos conjuntos tienen revisiones publicadas; no registrar modelos de
    # Participation/Scheduling mientras no exista su definición integrada real.
    from app.modules.identity.infrastructure import models as identity_models  # noqa: F401
    from app.modules.cases.infrastructure import models as cases_models  # noqa: F401

    validar_referencias(Base.metadata)
    return Base.metadata
