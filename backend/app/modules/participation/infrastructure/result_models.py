"""Dos entidades ER28: adaptación física UUID y procedencia técnica, sin publicación."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, Uuid, Numeric, DateTime, Text, String, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.modules.cases.infrastructure.models import CriterioRubricaModel, NivelRubricaModel

# Claves candidatas necesarias para FK compuestas; sin cambiar PK ni columnas.
Index("uq_8c_criterio_rubrica", CriterioRubricaModel.id, CriterioRubricaModel.rubrica_id, unique=True)
Index("uq_8c_nivel_criterio", NivelRubricaModel.id, NivelRubricaModel.criterio_id, unique=True)


class ResultadoIntentoModel(Base):
    __tablename__ = "resultado_intento"
    __table_args__ = (
        UniqueConstraint("id_intento", name="uq_8c_resultado_intento"),
        UniqueConstraint("id_resultado", "rubrica_id", name="uq_8c_resultado_rubrica"),
        CheckConstraint("ambito = 'LABORATORIO' OR (ambito = 'TECNICO' AND version_regla = 'PREGUNTAS_100_V1')", name="ck_resultado_ambito"),
        CheckConstraint("modalidad IN ('COMPLETA','PARCIAL') AND nota_final >= 0 AND nota_final <= 100", name="ck_8c_resultado"),
        CheckConstraint("length(procedencia_sha256)=64 AND length(politica_hash)=64", name="ck_8c_hash"),
    )
    id_resultado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_intento: Mapped[int] = mapped_column(ForeignKey("intento.id_intento"), nullable=False)
    nota_final: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    fecha_calculo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comentario_automatico: Mapped[str | None] = mapped_column(Text)
    id_caso: Mapped[int] = mapped_column(ForeignKey("caso.id_caso"), nullable=False)
    caso_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("caso.id"), nullable=False)
    version_caso_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("version_caso.id"), nullable=False)
    rubrica_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("rubrica.id"), nullable=False)
    version_regla: Mapped[str] = mapped_column(String(20), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(20), nullable=False)
    ambito: Mapped[str] = mapped_column(String(16), nullable=False)
    politica_id: Mapped[str] = mapped_column(Text, nullable=False)
    politica_version: Mapped[str] = mapped_column(Text, nullable=False)
    politica_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    procedencia: Mapped[str] = mapped_column(Text, nullable=False)
    procedencia_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class ResultadoCriterioModel(Base):
    __tablename__ = "resultado_criterio"
    __table_args__ = (
        UniqueConstraint("id_resultado", "id_criterio", name="uq_8c_resultado_criterio"),
        ForeignKeyConstraint(["id_resultado", "rubrica_id"], ["resultado_intento.id_resultado", "resultado_intento.rubrica_id"], name="fk_8c_detalle_cabecera"),
        ForeignKeyConstraint(["id_criterio", "rubrica_id"], ["criterio_rubrica.id", "criterio_rubrica.rubrica_id"], name="fk_8c_detalle_rubrica"),
        ForeignKeyConstraint(["id_nivel", "id_criterio"], ["nivel_rubrica.id", "nivel_rubrica.criterio_id"], name="fk_8c_detalle_nivel"),
        CheckConstraint("puntaje_obtenido >= 0 AND puntaje_obtenido < 1000", name="ck_8c_puntaje"),
    )
    id_resultado_criterio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_resultado: Mapped[int] = mapped_column(Integer, nullable=False)
    rubrica_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    id_criterio: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    id_nivel: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    puntaje_obtenido: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
