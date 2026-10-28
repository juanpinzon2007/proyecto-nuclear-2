"""Mapeo exacto del bloque de acceso del DBML proporcionado por el equipo."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RolORM(Base):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)


class PermisoORM(Base):
    __tablename__ = "permiso"

    id_permiso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)


class RolPermisoORM(Base):
    __tablename__ = "rol_permiso"

    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), primary_key=True, nullable=False)
    id_permiso: Mapped[int] = mapped_column(ForeignKey("permiso.id_permiso"), primary_key=True, nullable=False)


class UsuarioORM(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    clave_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
