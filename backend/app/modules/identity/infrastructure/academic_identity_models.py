"""Registro de vínculos explícitos; no genera UUID ni identifica membresías."""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Uuid, column, literal
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdentidadAcademicaORM(Base):
    __tablename__ = "identidad_academica"

    sistema: Mapped[str] = mapped_column(String(16), primary_key=True)
    id_academico: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id_usuario", name="fk_identidad_academica_usuario"), nullable=False,
    )

    __table_args__ = (
        CheckConstraint("sistema IN ('CASES', 'SCHEDULING')", name="ck_identidad_academica_sistema"),
        CheckConstraint(column("id_academico", Uuid()) != literal(UUID(int=0), type_=Uuid()),
                        name="ck_identidad_academica_uuid_no_nulo"),
        Index("ix_identidad_academica_usuario_sistema", "id_usuario", "sistema"),
    )
