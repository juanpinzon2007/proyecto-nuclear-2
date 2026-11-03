"""Tablas del DBML con FK externas; no crean ni duplican tablas de compañeros.

Comparten Base y su registry. BD2-07 integró el permiso de intento; la aprobación
académica posterior integra feedback individual, una valoración editable por
participación. academic_metadata vacío se conserva por compatibilidad de imports.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, MetaData, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.identity.infrastructure.models import UsuarioORM


academic_metadata = MetaData(info={
    "estado_integracion": "pendiente",
    "dependencias": ("participacion", "asignacion_caso"),
})


class PermisoIntentoExtraORM(Base):
    # Dependencia oficial de intento, integrada por BD2-07 sin duplicar la clase.
    metadata = Base.metadata
    __tablename__ = "permiso_intento_extra"

    id_permiso_extra: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_participacion: Mapped[int] = mapped_column(ForeignKey("participacion.id_participacion"), nullable=False)
    id_profesor: Mapped[int] = mapped_column(ForeignKey(UsuarioORM.id_usuario), nullable=False)
    cantidad_autorizada: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_autorizacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class RetroalimentacionDocenteORM(Base):
    metadata = Base.metadata
    __tablename__ = "retroalimentacion_docente"

    id_retroalimentacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_asignacion: Mapped[int] = mapped_column(ForeignKey("asignacion_caso.id_asignacion"), nullable=False)
    id_participacion: Mapped[int] = mapped_column(ForeignKey("participacion.id_participacion"), nullable=False, unique=True)
    id_profesor: Mapped[int] = mapped_column(ForeignKey(UsuarioORM.id_usuario), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
