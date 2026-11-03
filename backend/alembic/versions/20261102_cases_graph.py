"""Grafo Cases autorizado: tres columnas, sin datos ni tablas nuevas."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_cases_graph"
down_revision = "20261102_academic_policy"
branch_labels = None
depends_on = None

COHERENCIA = "(tipo_transicion IS NULL AND escenario_destino_id IS NULL) OR " \
    "(tipo_transicion IS NOT NULL AND ((tipo_transicion = 'ESCENA' AND escenario_destino_id IS NOT NULL) " \
    "OR (tipo_transicion = 'FIN' AND escenario_destino_id IS NULL)))"

SQL = r"""
CREATE FUNCTION public.f8b_validar_grafo() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE v uuid;
BEGIN
 v:=public.bd204_version(TG_TABLE_NAME,CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END);
 -- Cascada cuyo padre ya desapareció: sus ancestros/FK conservan el control.
 IF v IS NULL THEN RETURN NULL; END IF;
 -- BD2-04 mantiene inmutables id y padre y bloquea la raíz de cada escritor.
 -- Comprobación diferida: admite insertar/reemplazar un borrador completo en
 -- una transacción, pero nunca confirmar destinos de otra edición.
 IF EXISTS (
   SELECT 1 FROM public.opcion_respuesta o
   JOIN public.pregunta p ON p.id=o.pregunta_id
   JOIN public.escenario origen ON origen.id=p.escenario_id
   JOIN public.escenario destino ON destino.id=o.escenario_destino_id
   WHERE (origen.version_caso_id=v OR destino.version_caso_id=v)
     AND origen.version_caso_id<>destino.version_caso_id
 ) THEN
   RAISE EXCEPTION '8B: destino de otra version' USING ERRCODE='23514';
 END IF;
 -- Estas garantías transaccionales se verifican bajo READ COMMITTED; rechazar
 -- snapshots antiguos para grafos configurados, en vez de asumir su frescura.
 IF current_setting('transaction_isolation')<>'read committed' AND (
   EXISTS(SELECT 1 FROM public.escenario WHERE version_caso_id=v AND es_inicial) OR
   EXISTS(SELECT 1 FROM public.opcion_respuesta o JOIN public.pregunta p ON p.id=o.pregunta_id
     JOIN public.escenario e ON e.id=p.escenario_id WHERE e.version_caso_id=v AND o.tipo_transicion IS NOT NULL)) THEN
   RAISE EXCEPTION '8B: escritura de grafo requiere READ COMMITTED' USING ERRCODE='40001';
 END IF;
 RETURN NULL;
END $f$;
CREATE CONSTRAINT TRIGGER f8b_grafo_opcion AFTER INSERT OR UPDATE OR DELETE ON public.opcion_respuesta
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.f8b_validar_grafo();
CREATE CONSTRAINT TRIGGER f8b_grafo_escenario AFTER INSERT OR UPDATE OR DELETE ON public.escenario
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.f8b_validar_grafo();
CREATE CONSTRAINT TRIGGER f8b_grafo_pregunta AFTER INSERT OR UPDATE OR DELETE ON public.pregunta
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.f8b_validar_grafo();
"""


def agregar_columnas():
    """También usado por DDL SQLite aislado; no simula triggers PostgreSQL."""
    op.add_column("escenario", sa.Column("es_inicial", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("uq_8b_escena_inicial", "escenario", ["version_caso_id"], unique=True,
                    postgresql_where=sa.text("es_inicial"), sqlite_where=sa.text("es_inicial = 1"))
    with op.batch_alter_table("opcion_respuesta") as b:
        b.add_column(sa.Column("escenario_destino_id", sa.Uuid(), nullable=True))
        b.add_column(sa.Column("tipo_transicion", sa.String(10), nullable=True))
        b.create_foreign_key("fk_8b_destino", "escenario", ["escenario_destino_id"], ["id"],
                             deferrable=True, initially="DEFERRED")
        b.create_check_constraint("ck_8b_transicion", COHERENCIA)


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("La revisión del grafo requiere PostgreSQL; SQLite solo prueba DDL aislado.")
    op.execute("LOCK TABLE version_caso,escenario,pregunta,opcion_respuesta IN SHARE ROW EXCLUSIVE MODE")
    agregar_columnas()
    op.get_bind().exec_driver_sql(SQL, execution_options={"no_parameters": True})


def downgrade():
    b = op.get_bind()
    if b.dialect.name != "postgresql":
        raise RuntimeError("Downgrade de grafo reservado a PostgreSQL.")
    op.execute("LOCK TABLE version_caso,escenario,pregunta,opcion_respuesta IN ACCESS EXCLUSIVE MODE")
    if b.scalar(sa.text("SELECT 1 FROM escenario WHERE es_inicial LIMIT 1")) is not None or b.scalar(
        sa.text("SELECT 1 FROM opcion_respuesta WHERE tipo_transicion IS NOT NULL OR escenario_destino_id IS NOT NULL LIMIT 1")) is not None:
        raise RuntimeError("No eliminar un grafo configurado; downgrade sin pérdida de datos únicamente.")
    for tabla in ("opcion_respuesta", "escenario", "pregunta"):
        op.execute(f"DROP TRIGGER f8b_grafo_{'opcion' if tabla == 'opcion_respuesta' else tabla} ON public.{tabla}")
    op.execute("DROP FUNCTION public.f8b_validar_grafo()")
    op.drop_constraint("fk_8b_destino", "opcion_respuesta", type_="foreignkey")
    op.drop_constraint("ck_8b_transicion", "opcion_respuesta", type_="check")
    op.drop_column("opcion_respuesta", "tipo_transicion")
    op.drop_column("opcion_respuesta", "escenario_destino_id")
    op.drop_index("uq_8b_escena_inicial", table_name="escenario")
    op.drop_column("escenario", "es_inicial")
