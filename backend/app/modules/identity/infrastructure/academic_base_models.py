"""Organización y consentimiento del ER oficial, sin políticas ni servicios.

La matrícula conserva UNIQUE(grupo, estudiante): no modela episodios de
reingreso. Crear estas tablas no acredita aceptación ni autoriza participación.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.identity.infrastructure.models import UsuarioORM


class GrupoAcademicoORM(Base):
    __tablename__ = "grupo_academico"

    id_grupo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_profesor: Mapped[int] = mapped_column(
        Integer, ForeignKey(UsuarioORM.id_usuario, name="fk_grupo_academico_profesor_usuario"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    periodo: Mapped[str] = mapped_column(String(30), nullable=False)


class GrupoEstudianteORM(Base):
    __tablename__ = "grupo_estudiante"

    id_grupo_estudiante: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_grupo: Mapped[int] = mapped_column(
        Integer, ForeignKey("grupo_academico.id_grupo", name="fk_grupo_estudiante_grupo"),
        nullable=False,
    )
    id_estudiante: Mapped[int] = mapped_column(
        Integer, ForeignKey(UsuarioORM.id_usuario, name="fk_grupo_estudiante_estudiante_usuario"),
        nullable=False,
    )
    fecha_ingreso: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    __table_args__ = (
        UniqueConstraint("id_grupo", "id_estudiante", name="uq_grupo_estudiante_grupo_estudiante"),
    )


class ConsentimientoORM(Base):
    __tablename__ = "consentimiento"

    id_consentimiento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_estudiante: Mapped[int] = mapped_column(
        Integer, ForeignKey(UsuarioORM.id_usuario, name="fk_consentimiento_estudiante_usuario"),
        nullable=False,
    )
    version_texto: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_aceptacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_revocacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
