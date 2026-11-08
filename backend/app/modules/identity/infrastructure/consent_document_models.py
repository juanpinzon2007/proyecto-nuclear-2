"""Registro técnico vacío hasta publicación autorizada; no datos institucionales."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DocumentoConsentimientoVersionORM(Base):
    __tablename__ = 'documento_consentimiento_version'
    __table_args__ = (
        UniqueConstraint('referencia', name='uq_documento_consentimiento_referencia'),
        UniqueConstraint('documento_id', 'version', name='uq_documento_consentimiento_edicion'),
        CheckConstraint("length(trim(referencia))>0 AND length(trim(documento_id))>0 AND length(trim(version))>0 AND length(trim(texto))>0 AND length(trim(tipo_media))>0 AND length(trim(autoridad_aprobadora))>0", name='ck_documento_consentimiento_textos'),
        CheckConstraint('length(original)>0 AND length(evidencia_aprobacion)>0', name='ck_documento_consentimiento_bytes'),
        CheckConstraint('publicado_en>=aprobado_en', name='ck_documento_consentimiento_fechas'),
    )
    id_version_documento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referencia: Mapped[str] = mapped_column(String(30), nullable=False)
    documento_id: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    original: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    tipo_media: Mapped[str] = mapped_column(Text, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_original: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256_texto: Mapped[str] = mapped_column(String(64), nullable=False)
    autoridad_aprobadora: Mapped[str] = mapped_column(Text, nullable=False)
    aprobado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidencia_aprobacion: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256_aprobacion: Mapped[str] = mapped_column(String(64), nullable=False)
    publicado_por: Mapped[int] = mapped_column(ForeignKey('usuario.id_usuario'), nullable=False)
    publicado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SeleccionConsentimientoORM(Base):
    __tablename__ = 'seleccion_consentimiento'
    id_asignacion: Mapped[int] = mapped_column(ForeignKey('asignacion_caso.id_asignacion'), primary_key=True)
    id_version_documento: Mapped[int] = mapped_column(ForeignKey('documento_consentimiento_version.id_version_documento'), nullable=False)
    seleccionado_por: Mapped[int] = mapped_column(ForeignKey('usuario.id_usuario'), nullable=False)
    seleccionado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
