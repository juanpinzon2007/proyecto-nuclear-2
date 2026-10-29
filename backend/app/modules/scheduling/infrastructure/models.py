"""Modelos ORM del módulo de Programación de Sesiones."""

import uuid
from datetime import datetime, timezone


from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)


from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.cases.infrastructure.models.mixins import uuid_pk


class EspacioAcademicoModel(Base):
    """Representa un espacio académico del simulador."""

    __tablename__ = "espacio_academico"

    id: Mapped[uuid.UUID] = uuid_pk()

    nombre: Mapped[str] = mapped_column(
        String(160),
        nullable=False
    )



class SesionProgramadaModel(Base):
    """Representa una sesión académica programada."""

    __tablename__ = "sesion_programada"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Relación con el espacio académico
    espacio_academico_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("espacio_academico.id"),
        nullable=False,
        index=True,
    )

    # Relación con la versión del caso académico
    version_caso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("version_caso.id"),
        nullable=False,
        index=True,
    )

    # Referencia lógica al docente responsable
    docente_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    # Fecha y hora programadas
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    fecha_fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Tiempo máximo permitido al estudiante
    tiempo_maximo_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Lugar físico cuando corresponda
    lugar: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Mensaje personalizado del docente
    mensaje_personalizado: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Estado actual de la sesión
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="SIN_INICIAR",
        server_default="SIN_INICIAR",
    )

    # Fecha real de finalización
    finalizado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relación ORM con EspacioAcademicoModel
    espacio_academico: Mapped[EspacioAcademicoModel] = (
        relationship()
    )

    __table_args__ = (
        CheckConstraint(
            "fecha_fin > fecha_inicio",
            name="ck_sesion_fechas",
        ),
        CheckConstraint(
            "tiempo_maximo_minutos > 0",
            name="ck_sesion_tiempo_positivo",
        ),
        CheckConstraint(
            "estado IN "
            "('SIN_INICIAR', 'EN_CURSO', 'FINALIZADO')",
            name="ck_sesion_estado",
        ),
    )



class ConvocatoriaModel(Base):
    """Representa la convocatoria de un estudiante a una sesión."""

    __tablename__ = "convocatoria"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Sesión a la que pertenece la convocatoria
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sesion_programada.id"),
        nullable=False,
        index=True,
    )

    # Estudiante autorizado
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Hash del código de autorización
    codigo_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Estado de la convocatoria
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVA",
        server_default="ACTIVA",
    )

    # Relación con la sesión programada
    sesion: Mapped["SesionProgramadaModel"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "sesion_id",
            "estudiante_id",
            name="uq_convocatoria_sesion_estudiante",
        ),
        CheckConstraint(
            "estado IN ('ACTIVA', 'RETIRADA')",
            name="ck_convocatoria_estado",
        ),
    )


class NotificacionModel(Base):
    """Representa una notificación académica."""

    __tablename__ = "notificacion"

    # Identificador único
    id: Mapped[uuid.UUID] = uuid_pk()

    # Convocatoria relacionada, cuando aplique
    convocatoria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("convocatoria.id"),
        nullable=True,
        index=True,
    )

    # Estudiante destinatario
    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Tipo de notificación
    tipo: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    # Canal: correo o notificación interna
    canal: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Contenido de la notificación
    mensaje: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Estado de procesamiento
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDIENTE",
        server_default="PENDIENTE",
    )

    # Fecha de creación
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relación con convocatoria
    convocatoria: Mapped["ConvocatoriaModel | None"] = (
        relationship()
    )


class EventoAuditoriaModel(Base):
    """Registra los eventos importantes de una sesión."""

    __tablename__ = "evento_auditoria"

    # Identificador único del evento
    id: Mapped[uuid.UUID] = uuid_pk()

    # Sesión relacionada con el evento
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sesion_programada.id"),
        nullable=False,
        index=True,
    )

    # Tipo de evento realizado
    tipo: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    # Estado anterior de la sesión
    estado_anterior: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Nuevo estado de la sesión
    estado_nuevo: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Origen del evento: DOCENTE, WORKER o SISTEMA
    origen: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Descripción de la acción
    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Fecha y hora del evento
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relación con la sesión programada
    sesion: Mapped["SesionProgramadaModel"] = relationship()


