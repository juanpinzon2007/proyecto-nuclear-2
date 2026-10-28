"""Tablas del DBML con FK externas; no crean ni duplican tablas de compañeros.

No se importan en Alembic hasta integrar las tablas referenciadas. Estos mapeos
no equivalen por sí mismos a los contratos de AutorizacionRepeticion/FeedbackDocente.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.identity.infrastructure import models as _access_models  # registra usuario


class PermisoIntentoExtraORM(Base):
    __tablename__ = "permiso_intento_extra"

    id_permiso_extra: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_participacion: Mapped[int] = mapped_column(ForeignKey("participacion.id_participacion"), nullable=False)
    id_profesor: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False)
    cantidad_autorizada: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_autorizacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class RetroalimentacionDocenteORM(Base):
    __tablename__ = "retroalimentacion_docente"

    id_retroalimentacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_asignacion: Mapped[int] = mapped_column(ForeignKey("asignacion_caso.id_asignacion"), nullable=False, unique=True)
    id_profesor: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
