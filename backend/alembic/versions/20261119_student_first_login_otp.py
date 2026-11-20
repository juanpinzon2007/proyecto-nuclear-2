"""Agrega tabla verificacion_primer_ingreso para código único en primer inicio de sesión estudiantil.

Revision ID: 20261119_student_first_login_otp
Revises: 20261116_fix_rubric_compat
Create Date: 2026-11-19 07:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20261119_student_first_login_otp"
down_revision = "20261116_fix_rubric_compat"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "verificacion_primer_ingreso",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "id_usuario",
            sa.Integer(),
            sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verificado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("codigo_hash", sa.String(length=255), nullable=True),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id_usuario", name="uq_verificacion_primer_ingreso_usuario"),
    )


def downgrade():
    op.drop_table("verificacion_primer_ingreso")
