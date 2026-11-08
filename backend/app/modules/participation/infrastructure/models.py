"""Estructuras BD2-07/8B. Su presencia no autoriza iniciar ni editar intentos."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ParticipacionModel(Base):
    __tablename__ = "participacion"
    __table_args__ = (UniqueConstraint("id_asignacion", "id_grupo_estudiante", name="uq_participacion_asignacion_matricula"),)
    id_participacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_asignacion: Mapped[int] = mapped_column(ForeignKey("asignacion_caso.id_asignacion"), nullable=False)
    id_grupo_estudiante: Mapped[int] = mapped_column(ForeignKey("grupo_estudiante.id_grupo_estudiante"), nullable=False)
    convocatoria_id: Mapped[UUID] = mapped_column(ForeignKey("convocatoria.id"), nullable=False, unique=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pendiente")
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    id_consentimiento: Mapped[int | None] = mapped_column(ForeignKey('consentimiento.id_consentimiento', name='fk_participacion_consentimiento'), nullable=True)


class IntentoModel(Base):
    __tablename__ = "intento"
    __table_args__ = (
        UniqueConstraint("id_participacion", "numero_intento", name="uq_intento_participacion_numero"),
        CheckConstraint("numero_intento > 0", name="ck_intento_numero"),
        CheckConstraint("duracion_concedida_segundos > 0", name="ck_intento_duracion"),
        CheckConstraint("estado IN ('EN_CURSO','FINALIZADO','VENCIDO')", name="ck_intento_estado"),
        CheckConstraint("(estado='EN_CURSO' AND fin IS NULL) OR (estado IN ('FINALIZADO','VENCIDO') AND fin IS NOT NULL AND fin>=inicio)", name="ck_intento_cierre"),
        Index("uq_intento_un_activo", "id_participacion", unique=True,
              postgresql_where=text("estado='EN_CURSO'"), sqlite_where=text("estado='EN_CURSO'")),
    )
    id_intento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_participacion: Mapped[int] = mapped_column(ForeignKey("participacion.id_participacion"), nullable=False)
    id_consentimiento: Mapped[int] = mapped_column(ForeignKey("consentimiento.id_consentimiento"), nullable=False)
    id_permiso_extra: Mapped[int | None] = mapped_column(ForeignKey("permiso_intento_extra.id_permiso_extra"), nullable=True)
    numero_intento: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    # Seis decimales conservan microsegundos de timedelta sin truncar duración.
    duracion_concedida_segundos: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)


class PasoSimulacionModel(Base):
    __tablename__ = "paso_simulacion"
    __table_args__ = (
        ForeignKeyConstraint(["id_opcion", "id_decision"], ["opcion_respuesta.id", "opcion_respuesta.pregunta_id"], name="fk_paso_opcion_pregunta"),
        UniqueConstraint("id_intento", "numero_paso", name="uq_paso_intento_numero"),
        UniqueConstraint("id_intento", "id_decision", name="uq_paso_seleccion_actual"),
        CheckConstraint("numero_paso > 0 AND tiempo_segundos >= 0", name="ck_paso_orden_tiempo"),
    )
    id_paso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_intento: Mapped[int] = mapped_column(ForeignKey("intento.id_intento"), nullable=False)
    id_decision: Mapped[UUID] = mapped_column(ForeignKey("pregunta.id"), nullable=False)
    id_opcion: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    numero_paso: Mapped[int] = mapped_column(Integer, nullable=False)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    tiempo_segundos: Mapped[int] = mapped_column(Integer, nullable=False)
    reflexion_estudiante: Mapped[str | None] = mapped_column(Text, nullable=True)
