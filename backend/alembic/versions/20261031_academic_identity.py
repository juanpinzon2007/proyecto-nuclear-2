"""Registro flexible de identidad académica, sin backfill ni cambios académicos."""

from uuid import UUID

from alembic import op
import sqlalchemy as sa

revision = "20261031_academic_identity"
down_revision = "6867083574f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identidad_academica",
        sa.Column("sistema", sa.String(16), nullable=False),
        sa.Column("id_academico", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sistema", "id_academico"),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"], name="fk_identidad_academica_usuario"),
        sa.CheckConstraint("sistema IN ('CASES', 'SCHEDULING')", name="ck_identidad_academica_sistema"),
        sa.CheckConstraint(sa.column("id_academico", sa.Uuid()) != sa.literal(UUID(int=0), type_=sa.Uuid()),
                           name="ck_identidad_academica_uuid_no_nulo"),
    )
    op.create_index("ix_identidad_academica_usuario_sistema", "identidad_academica", ["id_usuario", "sistema"])


def downgrade() -> None:
    # Solo laboratorio: revierte exclusivamente la tabla de esta revisión.
    op.drop_index("ix_identidad_academica_usuario_sistema", table_name="identidad_academica")
    op.drop_table("identidad_academica")
