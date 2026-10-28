"""Modelos ORM de la rúbrica (Sección 9.2): rúbrica, criterio, nivel y valoración de opción."""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.cases.infrastructure.models.caso import OpcionRespuestaModel, VersionCasoModel
from app.modules.cases.infrastructure.models.mixins import uuid_pk


class RubricaModel(Base):
    __tablename__ = "rubrica"

    id: Mapped[uuid.UUID] = uuid_pk()
    version_caso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("version_caso.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    version_regla: Mapped[str] = mapped_column(String(20), nullable=False)

    version_caso: Mapped[VersionCasoModel] = relationship(back_populates="rubrica")
    criterios: Mapped[list["CriterioRubricaModel"]] = relationship(
        back_populates="rubrica", cascade="all, delete-orphan"
    )


class CriterioRubricaModel(Base):
    __tablename__ = "criterio_rubrica"

    id: Mapped[uuid.UUID] = uuid_pk()
    rubrica_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rubrica.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    peso: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    rubrica: Mapped[RubricaModel] = relationship(back_populates="criterios")
    niveles: Mapped[list["NivelRubricaModel"]] = relationship(
        back_populates="criterio", cascade="all, delete-orphan"
    )
    valoraciones: Mapped[list["ValoracionOpcionModel"]] = relationship(
        back_populates="criterio", cascade="all, delete-orphan"
    )


class NivelRubricaModel(Base):
    __tablename__ = "nivel_rubrica"

    id: Mapped[uuid.UUID] = uuid_pk()
    criterio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("criterio_rubrica.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    puntaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    descriptor: Mapped[str] = mapped_column(Text, nullable=False)

    criterio: Mapped[CriterioRubricaModel] = relationship(back_populates="niveles")


class ValoracionOpcionModel(Base):
    """Puntaje que una opción aporta a un criterio (PK compuesta)."""

    __tablename__ = "valoracion_opcion"

    opcion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opcion_respuesta.id", ondelete="CASCADE"), primary_key=True
    )
    criterio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("criterio_rubrica.id", ondelete="CASCADE"), primary_key=True
    )
    puntaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    opcion: Mapped[OpcionRespuestaModel] = relationship(back_populates="valoraciones")
    criterio: Mapped[CriterioRubricaModel] = relationship(back_populates="valoraciones")

