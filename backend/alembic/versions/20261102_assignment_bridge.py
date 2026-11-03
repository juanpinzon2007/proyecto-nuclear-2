"""P1-P3: clave académica alternativa y puente de asignación, sin backfill."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_assignment_bridge"
down_revision = "20261102_cases_history_guard"
branch_labels = None
depends_on = None


GUARD_SQL = r"""
CREATE FUNCTION public.bd205_asignacion() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE familia uuid; familia_version uuid; estado_version text;
BEGIN
 IF TG_OP='UPDATE' THEN
  IF (NEW.id_asignacion,NEW.id_grupo,NEW.id_caso,NEW.sesion_programada_id,NEW.version_caso_id)
    IS DISTINCT FROM
     (OLD.id_asignacion,OLD.id_grupo,OLD.id_caso,OLD.sesion_programada_id,OLD.version_caso_id) THEN
   RAISE EXCEPTION 'BD205: contexto de asignacion inmutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 SELECT id INTO familia FROM public.caso WHERE id_caso=NEW.id_caso;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD205: caso academico inexistente' USING ERRCODE='23503'; END IF;
 SELECT caso_id,estado INTO familia_version,estado_version FROM public.version_caso
  WHERE id=NEW.version_caso_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD205: version inexistente' USING ERRCODE='23503'; END IF;
 IF familia_version<>familia THEN
  RAISE EXCEPTION 'BD205: version de otra familia' USING ERRCODE='23514';
 END IF;
 IF estado_version<>'PUBLICADO' THEN
  RAISE EXCEPTION 'BD205: asignar requiere version publicada' USING ERRCODE='23514';
 END IF;
 PERFORM 1 FROM public.rubrica WHERE version_caso_id=NEW.version_caso_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD205: falta rubrica propia' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END
$f$;
CREATE TRIGGER bd205_asignacion BEFORE INSERT OR UPDATE ON public.asignacion_caso
 FOR EACH ROW EXECUTE FUNCTION public.bd205_asignacion();
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError("Puente soportado solo en PostgreSQL/SQLite de pruebas.")
    # Dos pasos: no DEFAULT al agregar, para que el legado permanezca NULL.
    op.add_column("caso", sa.Column("id_caso", sa.Integer(), nullable=True))
    op.create_index("uq_caso_id_caso_academico", "caso", ["id_caso"], unique=True)
    if bind.dialect.name == "postgresql":
        op.execute(sa.schema.CreateSequence(sa.Sequence("caso_id_caso_seq", data_type=sa.Integer(), start=1, minvalue=1)))
        op.execute("ALTER SEQUENCE public.caso_id_caso_seq OWNED BY public.caso.id_caso")
        op.alter_column("caso", "id_caso", server_default=sa.text("nextval('public.caso_id_caso_seq'::regclass)"))
    # Índices únicos con columnas existentes: sin reconstruir tablas en SQLite.
    op.create_index("uq_sesion_id_version_caso", "sesion_programada", ["id", "version_caso_id"], unique=True)
    op.create_table(
        "asignacion_caso",
        sa.Column("id_asignacion", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_grupo", sa.Integer(), nullable=False),
        sa.Column("id_caso", sa.Integer(), nullable=False),
        sa.Column("apertura", sa.DateTime(timezone=False), nullable=False),
        sa.Column("cierre", sa.DateTime(timezone=False), nullable=False),
        sa.Column("fecha_limite_ingreso", sa.DateTime(timezone=False), nullable=False),
        sa.Column("intentos_base", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("tiempo_maximo_min", sa.Integer(), nullable=False),
        sa.Column("codigo_acceso_hash", sa.String(255), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="programada"),
        sa.Column("sesion_programada_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_caso_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["id_grupo"], ["grupo_academico.id_grupo"], name="fk_asignacion_grupo"),
        sa.ForeignKeyConstraint(["id_caso"], ["caso.id_caso"], name="fk_asignacion_caso_academico"),
        sa.ForeignKeyConstraint(["version_caso_id"], ["version_caso.id"], name="fk_asignacion_version_exacta"),
        sa.ForeignKeyConstraint(["sesion_programada_id", "version_caso_id"],
            ["sesion_programada.id", "sesion_programada.version_caso_id"], name="fk_asignacion_sesion_version"),
        sa.UniqueConstraint("sesion_programada_id", "id_grupo", name="uq_asignacion_sesion_grupo"),
    )
    for name in ("id_grupo", "id_caso", "version_caso_id"):
        op.create_index("ix_asignacion_caso_"+name,"asignacion_caso",[name])
    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql(GUARD_SQL, execution_options={"no_parameters": True})


def downgrade() -> None:
    bind=op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql("LOCK TABLE public.caso, public.asignacion_caso IN ACCESS EXCLUSIVE MODE")
    if bind.scalar(sa.text("SELECT 1 FROM asignacion_caso LIMIT 1")) is not None:
        raise RuntimeError("Downgrade rechazado: existen asignaciones que deben conservarse.")
    if bind.scalar(sa.text("SELECT 1 FROM caso WHERE id_caso IS NOT NULL LIMIT 1")) is not None:
        raise RuntimeError("Downgrade rechazado: existen identidades academicas que deben conservarse.")
    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql("DROP TRIGGER bd205_asignacion ON public.asignacion_caso; DROP FUNCTION public.bd205_asignacion()")
    op.drop_table("asignacion_caso")  # Comprobada vacía; no se borra información.
    op.drop_index("uq_sesion_id_version_caso",table_name="sesion_programada")
    op.drop_index("uq_caso_id_caso_academico",table_name="caso")
    if bind.dialect.name == "postgresql":
        op.alter_column("caso", "id_caso",server_default=None)
        op.execute(sa.schema.DropSequence(sa.Sequence("caso_id_caso_seq")))
    op.drop_column("caso", "id_caso")  # Solo valores NULL, sin backfill ni pérdida.
