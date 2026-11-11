"""Despacho externo asociado a la notificación canónica existente."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DespachoCorreoModel(Base):
    __tablename__ = 'despacho_correo'
    __table_args__ = (
        CheckConstraint("estado IN ('PENDIENTE','REINTENTAR','ACEPTADO_PROVEEDOR','CANCELADO')", name='ck_despacho_correo_estado'),
        CheckConstraint('intentos >= 0', name='ck_despacho_correo_intentos'),
        CheckConstraint('length(payload_cifrado) > 0', name='ck_despacho_correo_payload'),
        CheckConstraint("(estado='ACEPTADO_PROVEEDOR') = (aceptado_en IS NOT NULL)", name='ck_despacho_correo_aceptacion'),
    )
    id_notificacion: Mapped[UUID] = mapped_column(ForeignKey('notificacion.id'), primary_key=True)
    payload_cifrado: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default='PENDIENTE', server_default='PENDIENTE', index=True)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    ultimo_error: Mapped[str | None] = mapped_column(String(60))
    ultimo_intento_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aceptado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
