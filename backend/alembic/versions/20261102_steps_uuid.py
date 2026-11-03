"""8B: paso oficial con referencias UUID físicas de Cases, sin conversiones."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_steps_uuid"
down_revision = "20261102_participation_history"
branch_labels = None
depends_on = None

GUARDS = r"""
CREATE FUNCTION public.f8b_paso() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE p integer; estado_intento text; comienzo timestamp; duracion numeric;
 version_asignada uuid; version_pregunta uuid; limite timestamp; ultima timestamp;
BEGIN
 IF current_setting('transaction_isolation')='repeatable read' THEN
  RAISE EXCEPTION '8B: snapshot no soportado para mutacion' USING ERRCODE='40001';
 END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION '8B: respuestas no eliminables' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.id_paso,NEW.id_intento,NEW.id_decision,NEW.numero_paso)
  IS DISTINCT FROM (OLD.id_paso,OLD.id_intento,OLD.id_decision,OLD.numero_paso) THEN
  RAISE EXCEPTION '8B: identidad del paso inmutable' USING ERRCODE='23514';
 END IF;
 SELECT id_participacion INTO p FROM public.intento WHERE id_intento=NEW.id_intento;
 IF NOT FOUND THEN RAISE EXCEPTION '8B: intento inexistente' USING ERRCODE='23503'; END IF;
 PERFORM 1 FROM public.participacion WHERE id_participacion=p FOR UPDATE;
 SELECT estado,inicio,duracion_concedida_segundos INTO estado_intento,comienzo,duracion
  FROM public.intento WHERE id_intento=NEW.id_intento FOR UPDATE;
 IF estado_intento<>'EN_CURSO' THEN RAISE EXCEPTION '8B: intento cerrado' USING ERRCODE='23514'; END IF;
 SELECT a.version_caso_id INTO version_asignada FROM public.participacion x
  JOIN public.asignacion_caso a USING(id_asignacion) WHERE x.id_participacion=p;
 SELECT e.version_caso_id INTO version_pregunta FROM public.pregunta q
  JOIN public.escenario e ON e.id=q.escenario_id WHERE q.id=NEW.id_decision;
 IF NOT FOUND THEN RAISE EXCEPTION '8B: pregunta inexistente' USING ERRCODE='23503'; END IF;
 IF version_pregunta<>version_asignada THEN RAISE EXCEPTION '8B: version ajena' USING ERRCODE='23514'; END IF;
 limite=comienzo+(trunc(duracion/86400)::text||' days')::interval+(mod(duracion,86400)::text||' seconds')::interval;
 SELECT coalesce(max(registrado_en),comienzo) INTO ultima FROM public.paso_simulacion WHERE id_intento=NEW.id_intento;
 IF NEW.registrado_en<comienzo OR NEW.registrado_en>=limite OR NEW.registrado_en<ultima
  OR NEW.tiempo_segundos IS DISTINCT FROM floor(extract(epoch FROM (NEW.registrado_en-comienzo))) THEN
  RAISE EXCEPTION '8B: tiempo del paso incompatible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;

CREATE FUNCTION public.f8b_cierre() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 IF current_setting('transaction_isolation')='repeatable read' THEN
  RAISE EXCEPTION '8B: snapshot no soportado para mutacion' USING ERRCODE='40001';
 END IF;
 IF NEW.fin IS NOT NULL AND EXISTS(SELECT 1 FROM public.paso_simulacion
  WHERE id_intento=NEW.id_intento AND registrado_en>NEW.fin) THEN
  RAISE EXCEPTION '8B: cierre anterior a respuestas' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;
CREATE TRIGGER f8b_paso BEFORE INSERT OR UPDATE OR DELETE ON public.paso_simulacion
 FOR EACH ROW EXECUTE FUNCTION public.f8b_paso();
CREATE TRIGGER f8b_cierre BEFORE UPDATE ON public.intento
 FOR EACH ROW EXECUTE FUNCTION public.f8b_cierre();
CREATE TRIGGER f8b_truncate BEFORE TRUNCATE ON public.paso_simulacion
 FOR EACH STATEMENT EXECUTE FUNCTION public.bd207_no_truncar();
"""


def upgrade():
    op.create_index("uq_opcion_id_pregunta","opcion_respuesta",["id","pregunta_id"],unique=True)
    op.create_table("paso_simulacion",
        sa.Column("id_paso",sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column("id_intento",sa.Integer(),sa.ForeignKey("intento.id_intento"),nullable=False),
        sa.Column("id_decision",sa.Uuid(),sa.ForeignKey("pregunta.id"),nullable=False),
        sa.Column("id_opcion",sa.Uuid(),nullable=False),
        sa.Column("numero_paso",sa.Integer(),nullable=False),
        sa.Column("registrado_en",sa.DateTime(),nullable=False),
        sa.Column("tiempo_segundos",sa.Integer(),nullable=False),
        sa.Column("reflexion_estudiante",sa.Text()),
        sa.ForeignKeyConstraint(["id_opcion","id_decision"],["opcion_respuesta.id","opcion_respuesta.pregunta_id"],name="fk_paso_opcion_pregunta"),
        sa.UniqueConstraint("id_intento","numero_paso",name="uq_paso_intento_numero"),
        sa.UniqueConstraint("id_intento","id_decision",name="uq_paso_seleccion_actual"),
        sa.CheckConstraint("numero_paso > 0 AND tiempo_segundos >= 0",name="ck_paso_orden_tiempo"))
    bind=op.get_bind()
    if bind.dialect.name=="postgresql":
        bind.exec_driver_sql(GUARDS,execution_options={"no_parameters":True})


def downgrade():
    bind=op.get_bind()
    if bind.dialect.name=="postgresql":
        bind.exec_driver_sql("LOCK TABLE public.paso_simulacion IN ACCESS EXCLUSIVE MODE")
    if bind.scalar(sa.text("SELECT 1 FROM paso_simulacion LIMIT 1")) is not None:
        raise RuntimeError("Downgrade 8B rechazado: existen respuestas historicas.")
    if bind.dialect.name=="postgresql":
        bind.exec_driver_sql("DROP TRIGGER f8b_cierre ON public.intento; DROP TRIGGER f8b_paso ON public.paso_simulacion; DROP TRIGGER f8b_truncate ON public.paso_simulacion; DROP FUNCTION public.f8b_paso(); DROP FUNCTION public.f8b_cierre()")
    op.drop_table("paso_simulacion")
    op.drop_index("uq_opcion_id_pregunta",table_name="opcion_respuesta")
