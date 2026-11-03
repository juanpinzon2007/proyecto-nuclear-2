"""Asignación ER28: puente de referencias, sin autorización de ingreso implícita."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AsignacionCasoModel(Base):
    __tablename__ = "asignacion_caso"
    __table_args__ = (
        ForeignKeyConstraint(
            ["sesion_programada_id", "version_caso_id"],
            ["sesion_programada.id", "sesion_programada.version_caso_id"],
            name="fk_asignacion_sesion_version",
        ),
        UniqueConstraint("sesion_programada_id", "id_grupo", name="uq_asignacion_sesion_grupo"),
    )

    id_asignacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_grupo: Mapped[int] = mapped_column(ForeignKey("grupo_academico.id_grupo", name="fk_asignacion_grupo"), nullable=False, index=True)
    id_caso: Mapped[int] = mapped_column(ForeignKey("caso.id_caso", name="fk_asignacion_caso_academico"), nullable=False, index=True)
    apertura: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    cierre: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_limite_ingreso: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    intentos_base: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    tiempo_maximo_min: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo_acceso_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="programada")
    sesion_programada_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    version_caso_id: Mapped[UUID] = mapped_column(ForeignKey("version_caso.id", name="fk_asignacion_version_exacta"), nullable=False, index=True)
