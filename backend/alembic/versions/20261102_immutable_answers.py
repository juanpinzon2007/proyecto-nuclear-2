"""Política académica confirmada: respuestas persistidas solo de inserción."""
from alembic import op

revision = "20261102_immutable_answers"
down_revision = "20261102_cases_graph"
branch_labels = None
depends_on = None

SQL = r"""
CREATE FUNCTION public.f8b_respuesta_inmutable() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 RAISE EXCEPTION '8B: respuesta registrada inmutable' USING ERRCODE='23514';
END $f$;
CREATE TRIGGER f8b_respuesta_inmutable BEFORE UPDATE OR DELETE ON public.paso_simulacion
 FOR EACH ROW EXECUTE FUNCTION public.f8b_respuesta_inmutable();
"""


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("La inmutabilidad SQL se valida exclusivamente en PostgreSQL.")
    op.execute("LOCK TABLE public.paso_simulacion IN SHARE ROW EXCLUSIVE MODE")
    op.get_bind().exec_driver_sql(SQL, execution_options={"no_parameters": True})


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Downgrade reservado a PostgreSQL.")
    op.execute("LOCK TABLE public.paso_simulacion IN ACCESS EXCLUSIVE MODE")
    op.execute("DROP TRIGGER f8b_respuesta_inmutable ON public.paso_simulacion")
    op.execute("DROP FUNCTION public.f8b_respuesta_inmutable()")
