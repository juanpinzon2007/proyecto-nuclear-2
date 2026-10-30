"""Tablas de acceso confirmadas por el DBML; no incluye entidades académicas.

Revision ID: 20261028_identity_access
Revises: None
"""

from alembic import op
import sqlalchemy as sa

revision = "20261028_identity_access"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("rol",
        sa.Column("id_rol", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(40), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
    )
    op.create_table("permiso",
        sa.Column("id_permiso", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(80), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
    )
    op.create_table("rol_permiso",
        sa.Column("id_rol", sa.Integer(), sa.ForeignKey("rol.id_rol"), primary_key=True, nullable=False),
        sa.Column("id_permiso", sa.Integer(), sa.ForeignKey("permiso.id_permiso"), primary_key=True, nullable=False),
    )
    op.create_table("usuario",
        sa.Column("id_usuario", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_rol", sa.Integer(), sa.ForeignKey("rol.id_rol"), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("correo", sa.String(200), nullable=False, unique=True),
        sa.Column("clave_hash", sa.String(255), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("usuario")
    op.drop_table("rol_permiso")
    op.drop_table("permiso")
    op.drop_table("rol")
