"""Tablas del DBML con FK externas; no crean ni duplican tablas de compañeros.

Comparten Base y su registry, pero su metadata NO forma parte del esquema
desplegable: participacion y asignacion_caso aún no existen como modelos
integrados. No se eliminan FK ni se declara una tabla externa ficticia.
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
    metadata = academic_metadata
    __tablename__ = "permiso_intento_extra"

    id_permiso_extra: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_participacion: Mapped[int] = mapped_column(ForeignKey("participacion.id_participacion"), nullable=False)
    id_profesor: Mapped[int] = mapped_column(ForeignKey(UsuarioORM.id_usuario), nullable=False)
    cantidad_autorizada: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_autorizacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class RetroalimentacionDocenteORM(Base):
    metadata = academic_metadata
    __tablename__ = "retroalimentacion_docente"

    id_retroalimentacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_asignacion: Mapped[int] = mapped_column(ForeignKey("asignacion_caso.id_asignacion"), nullable=False, unique=True)
    id_profesor: Mapped[int] = mapped_column(ForeignKey(UsuarioORM.id_usuario), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
