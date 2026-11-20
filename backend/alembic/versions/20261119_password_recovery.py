"""Agrega tabla recuperacion_contrasena y trigger de control OTP de recuperación.

Revision ID: 20261119_password_recovery
Revises: 20261119_db_views_and_triggers
Create Date: 2026-11-19 08:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20261119_password_recovery"
down_revision = "20261119_db_views_and_triggers"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recuperacion_contrasena",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "id_usuario",
            sa.Integer(),
            sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codigo_hash", sa.String(length=255), nullable=True),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("solicitado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("id_usuario", name="uq_recuperacion_contrasena_usuario"),
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION public.sps_validar_recuperacion_contrasena_fn()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $function$
            BEGIN
                IF NEW.intentos < 0 THEN
                    RAISE EXCEPTION 'El contador de intentos de recuperación no puede ser negativo.'
                        USING ERRCODE = '23514';
                END IF;
                IF NEW.intentos >= 5 THEN
                    NEW.codigo_hash := NULL;
                    NEW.expira_en := NULL;
                END IF;
                RETURN NEW;
            END;
            $function$;

            CREATE TRIGGER trg_recuperacion_contrasena_guard
            BEFORE INSERT OR UPDATE ON public.recuperacion_contrasena
            FOR EACH ROW
            EXECUTE FUNCTION public.sps_validar_recuperacion_contrasena_fn();
            """
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_recuperacion_contrasena_guard ON public.recuperacion_contrasena;")
        op.execute("DROP FUNCTION IF EXISTS public.sps_validar_recuperacion_contrasena_fn();")

    op.drop_table("recuperacion_contrasena")
