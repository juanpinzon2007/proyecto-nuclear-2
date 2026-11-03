"""Tres tablas del ER oficial: grupos, matrícula y consentimiento.

Sin backfill ni cambios sobre las tablas anteriores. Las fechas conservan el
tipo original sin zona; no se aplica ninguna política académica al crear tablas.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261101_er28_base_academica"
down_revision = "20261031_academic_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grupo_academico",
        sa.Column("id_grupo", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_profesor", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("periodo", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_profesor"], ["usuario.id_usuario"], name="fk_grupo_academico_profesor_usuario",
        ),
    )
    op.create_table(
        "grupo_estudiante",
        sa.Column("id_grupo_estudiante", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_grupo", sa.Integer(), nullable=False),
        sa.Column("id_estudiante", sa.Integer(), nullable=False),
        sa.Column("fecha_ingreso", sa.DateTime(timezone=False), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["id_grupo"], ["grupo_academico.id_grupo"], name="fk_grupo_estudiante_grupo",
        ),
        sa.ForeignKeyConstraint(
            ["id_estudiante"], ["usuario.id_usuario"], name="fk_grupo_estudiante_estudiante_usuario",
        ),
        sa.UniqueConstraint("id_grupo", "id_estudiante", name="uq_grupo_estudiante_grupo_estudiante"),
    )
    op.create_table(
        "consentimiento",
        sa.Column("id_consentimiento", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_estudiante", sa.Integer(), nullable=False),
        sa.Column("version_texto", sa.String(30), nullable=False),
        sa.Column("fecha_aceptacion", sa.DateTime(timezone=False), nullable=False),
        sa.Column("fecha_revocacion", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_estudiante"], ["usuario.id_usuario"], name="fk_consentimiento_estudiante_usuario",
        ),
    )


def downgrade() -> None:
    conexion = op.get_bind()
    # Exclusión durante comprobar-vacío/retirar. No usar CASCADE ni borrar filas
    # para permitir la reversión. Su validación se realiza solo en laboratorio.
    if conexion.dialect.name == "postgresql":
        conexion.exec_driver_sql(
            "LOCK TABLE grupo_academico, grupo_estudiante, consentimiento IN ACCESS EXCLUSIVE MODE"
        )
    for nombre in ("grupo_academico", "grupo_estudiante", "consentimiento"):
        existe = conexion.scalar(sa.select(sa.literal(1)).select_from(sa.table(nombre)).limit(1))
        if existe is not None:
            raise RuntimeError(f"Downgrade rechazado: {nombre} contiene datos; se deben conservar.")
    op.drop_table("consentimiento")
    op.drop_table("grupo_estudiante")
    op.drop_table("grupo_academico")
