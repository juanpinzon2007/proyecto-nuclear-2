"""Modelos ORM del agregado Caso (Sección 9.2): caso, versión, escenario, pregunta y opción."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    FetchedValue,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models.mixins import uuid_pk


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CasoModel(Base):
    __tablename__ = "caso"
    __table_args__ = (Index("uq_caso_id_caso_academico", "id_caso", unique=True),)
    # El generador vive en PostgreSQL. No pedir RETURNING de una columna nueva
    # permite usar los lectores/escritores históricos sobre revisiones anteriores.
    __mapper_args__ = {"eager_defaults": False}

    id: Mapped[uuid.UUID] = uuid_pk()
    id_caso: Mapped[int | None] = mapped_column(
        Integer, nullable=True, server_default=FetchedValue(), deferred=True,
    )
    # Referencia lógica a identity; UUID suelto para no acoplar módulos.
    docente_creador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    versiones: Mapped[list["VersionCasoModel"]] = relationship(
        back_populates="caso", cascade="all, delete-orphan", order_by="VersionCasoModel.numero"
    )


class VersionCasoModel(Base):
    __tablename__ = "version_caso"
    __table_args__ = (UniqueConstraint("caso_id", "numero", name="uq_version_caso_numero"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    caso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caso.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    desarrollo_situacional: Mapped[str] = mapped_column(Text, nullable=False)
    contexto_historia: Mapped[str] = mapped_column(Text, nullable=False)
    tiempo_estimado_min: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoCaso] = mapped_column(
        Enum(EstadoCaso, name="estado_caso", native_enum=False, length=20),
        nullable=False,
        default=EstadoCaso.BORRADOR,
        index=True,
    )

    caso: Mapped[CasoModel] = relationship(back_populates="versiones")
    escenarios: Mapped[list["EscenarioModel"]] = relationship(
        back_populates="version_caso",
        cascade="all, delete-orphan",
        order_by="EscenarioModel.orden",
    )
    rubrica: Mapped["RubricaModel | None"] = relationship(
        back_populates="version_caso", cascade="all, delete-orphan", uselist=False
    )


class EscenarioModel(Base):
    __tablename__ = "escenario"
    __mapper_args__ = {"eager_defaults": False}
    __table_args__ = (
        UniqueConstraint("version_caso_id", "orden", name="uq_escenario_orden"),
        Index("uq_8b_escena_inicial", "version_caso_id", unique=True,
              postgresql_where=text("es_inicial"), sqlite_where=text("es_inicial = 1")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    version_caso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("version_caso.id", ondelete="CASCADE"), nullable=False, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    contexto_situacional: Mapped[str] = mapped_column(Text, nullable=False)
    es_inicial: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), deferred=True)

    version_caso: Mapped[VersionCasoModel] = relationship(back_populates="escenarios")
    preguntas: Mapped[list["PreguntaModel"]] = relationship(
        back_populates="escenario", cascade="all, delete-orphan", order_by="PreguntaModel.orden"
    )


class PreguntaModel(Base):
    __tablename__ = "pregunta"
    __table_args__ = (UniqueConstraint("escenario_id", "orden", name="uq_pregunta_orden"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    escenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("escenario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)

    escenario: Mapped[EscenarioModel] = relationship(back_populates="preguntas")
    opciones: Mapped[list["OpcionRespuestaModel"]] = relationship(
        back_populates="pregunta",
        cascade="all, delete-orphan",
        order_by="OpcionRespuestaModel.orden",
    )


class OpcionRespuestaModel(Base):
    __tablename__ = "opcion_respuesta"
    __mapper_args__ = {"eager_defaults": False}
    __table_args__ = (
        UniqueConstraint("pregunta_id", "orden", name="uq_opcion_orden"),
        Index("uq_opcion_id_pregunta", "id", "pregunta_id", unique=True),
        CheckConstraint("(tipo_transicion IS NULL AND escenario_destino_id IS NULL) OR "
            "(tipo_transicion IS NOT NULL AND ((tipo_transicion = 'ESCENA' AND escenario_destino_id IS NOT NULL) "
            "OR (tipo_transicion = 'FIN' AND escenario_destino_id IS NULL)))", name="ck_8b_transicion"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    pregunta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pregunta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    es_correcta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    escenario_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("escenario.id", name="fk_8b_destino", deferrable=True, initially="DEFERRED"),
        deferred=True, server_default=FetchedValue())
    tipo_transicion: Mapped[str | None] = mapped_column(String(10), deferred=True, server_default=FetchedValue())

    pregunta: Mapped[PreguntaModel] = relationship(back_populates="opciones")
    valoraciones: Mapped[list["ValoracionOpcionModel"]] = relationship(
        back_populates="opcion", cascade="all, delete-orphan"
    )

