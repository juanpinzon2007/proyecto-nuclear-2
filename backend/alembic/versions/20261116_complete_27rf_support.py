"""Soporte relacional completo para RF-03 (usuario_permiso) y RF-10 (borradores editables e historial).

Revision ID: 20261116_complete_27rf_support
Revises: 20261110_durable_mail
Create Date: 2026-11-16 15:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20261116_complete_27rf_support"
down_revision = "20261110_durable_mail"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("La migración 20261116_complete_27rf_support requiere PostgreSQL.")

    op.create_table(
        "usuario_permiso",
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), primary_key=True, nullable=False),
        sa.Column("id_permiso", sa.Integer(), sa.ForeignKey("permiso.id_permiso"), primary_key=True, nullable=False),
        sa.Column("concedido", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "borrador_decision_intento",
        sa.Column("id_borrador", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_intento", sa.Integer(), sa.ForeignKey("intento.id_intento"), nullable=False),
        sa.Column("id_decision", sa.Uuid(), sa.ForeignKey("pregunta.id"), nullable=False),
        sa.Column("id_opcion", sa.Uuid(), nullable=False),
        sa.Column("reflexion_estudiante", sa.Text(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_opcion", "id_decision"],
            ["opcion_respuesta.id", "opcion_respuesta.pregunta_id"],
            name="fk_borrador_opcion_pregunta",
        ),
        sa.UniqueConstraint("id_intento", "id_decision", name="uq_borrador_intento_decision"),
    )
    op.create_index("ix_borrador_intento", "borrador_decision_intento", ["id_intento"])

    op.create_table(
        "historial_cambio_decision",
        sa.Column("id_historial", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_intento", sa.Integer(), sa.ForeignKey("intento.id_intento"), nullable=False),
        sa.Column("id_decision", sa.Uuid(), sa.ForeignKey("pregunta.id"), nullable=False),
        sa.Column("id_opcion_anterior", sa.Uuid(), nullable=True),
        sa.Column("id_opcion_nueva", sa.Uuid(), nullable=False),
        sa.Column("cambiado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_opcion_nueva", "id_decision"],
            ["opcion_respuesta.id", "opcion_respuesta.pregunta_id"],
            name="fk_hist_opcion_nueva_pregunta",
        ),
    )
    op.create_index("ix_historial_cambio_intento", "historial_cambio_decision", ["id_intento"])


def downgrade():
    op.drop_index("ix_historial_cambio_intento", table_name="historial_cambio_decision")
    op.drop_table("historial_cambio_decision")
    op.drop_index("ix_borrador_intento", table_name="borrador_decision_intento")
    op.drop_table("borrador_decision_intento")
    op.drop_table("usuario_permiso")

