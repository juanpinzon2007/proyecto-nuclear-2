"""Persistencia de verificación única de primer ingreso estudiantil."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VerificacionPrimerIngresoORM(Base):
    __tablename__ = "verificacion_primer_ingreso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    codigo_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    verificado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
