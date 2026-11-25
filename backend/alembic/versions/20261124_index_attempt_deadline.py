"""Indexa los vencimientos de los intentos activos."""

from alembic import op

revision = "20261124_attempt_deadline"
down_revision = "20261124_decision_counts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE INDEX ix_intento_activo_vencimiento ON public.intento
        ((inicio + duracion_concedida_segundos * INTERVAL '1 second'), id_intento)
        WHERE estado = 'EN_CURSO'
    """)


def downgrade():
    op.execute("DROP INDEX public.ix_intento_activo_vencimiento")
