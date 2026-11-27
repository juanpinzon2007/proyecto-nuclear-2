"""Objetos f?sicos de PostgreSQL que complementan el esquema ORM compartido."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def esquema_postgresql(compartido: sa.MetaData) -> sa.MetaData:
    metadata = sa.MetaData(naming_convention=compartido.naming_convention)
    for tabla in compartido.sorted_tables:
        tabla.to_metadata(metadata)
    intento = metadata.tables["intento"]
    sa.Index(
        "ix_intento_activo_vencimiento",
        sa.text("(inicio + duracion_concedida_segundos::double precision * '00:00:01'::interval)"),
        intento.c.id_intento,
        postgresql_where=sa.text("estado = 'EN_CURSO'"),
    )
    sa.Table(
        "auditoria_trazabilidad_global",
        metadata,
        sa.Column("id_evento", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("modulo", sa.String(length=30), nullable=False),
        sa.Column("tabla_origen", sa.String(length=64), nullable=False),
        sa.Column("operacion", sa.String(length=10), nullable=False),
        sa.Column("registro_id", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("sesion_id", sa.Uuid(), nullable=True),
        sa.Column("convocatoria_id", sa.Uuid(), nullable=True),
        sa.Column("version_caso_id", sa.Uuid(), nullable=True),
        sa.Column("intento_id", sa.Integer(), nullable=True),
        sa.Column("resumen", sa.Text(), nullable=False),
        sa.Column("datos_anteriores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("datos_nuevos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tx_id", sa.BigInteger(), nullable=False, server_default=sa.text("txid_current()")),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("clock_timestamp()")),
        sa.CheckConstraint("operacion IN ('INSERT', 'UPDATE', 'DELETE')", name="ck_auditoria_global_operacion"),
        sa.Index("ix_auditoria_global_fecha", "registrado_en"),
        sa.Index("ix_auditoria_global_modulo_tabla", "modulo", "tabla_origen"),
        sa.Index("ix_auditoria_global_usuario", "usuario_id"),
        sa.Index("ix_auditoria_global_sesion", "sesion_id"),
        sa.Index("ix_auditoria_global_convocatoria", "convocatoria_id"),
        sa.Index("ix_auditoria_global_intento", "intento_id"),
    )
    return metadata
