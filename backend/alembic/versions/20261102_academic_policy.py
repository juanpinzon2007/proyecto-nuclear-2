"""Escala inclusiva 100 y feedback individual editable autorizados por el usuario."""
from alembic import op
import sqlalchemy as sa

revision="20261102_academic_policy"
down_revision="20261102_evaluation_results"
branch_labels=None
depends_on=None

SQL=r"""
CREATE FUNCTION public.f8c_feedback_individual() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE a integer; profesor integer;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Feedback: no eliminar registro' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.id_participacion,NEW.id_asignacion,NEW.id_profesor)
  IS DISTINCT FROM (OLD.id_participacion,OLD.id_asignacion,OLD.id_profesor) THEN
  RAISE EXCEPTION 'Feedback: destinatario y autor inmutables' USING ERRCODE='23514';
 END IF;
 SELECT p.id_asignacion,g.id_profesor INTO a,profesor FROM public.participacion p
 JOIN public.asignacion_caso x USING(id_asignacion) JOIN public.grupo_academico g ON g.id_grupo=x.id_grupo
 WHERE p.id_participacion=NEW.id_participacion FOR UPDATE OF p,g;
 IF NOT FOUND OR (a,profesor) IS DISTINCT FROM (NEW.id_asignacion,NEW.id_profesor) THEN
  RAISE EXCEPTION 'Feedback: destinatario o profesor ajeno' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.usuario u JOIN public.rol r USING(id_rol)
  WHERE u.id_usuario=profesor AND u.activo AND r.nombre='DOCENTE') OR btrim(NEW.texto)='' THEN
  RAISE EXCEPTION 'Feedback: autor o texto no valido' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;
CREATE TRIGGER f8c_feedback BEFORE INSERT OR UPDATE OR DELETE ON public.retroalimentacion_docente
 FOR EACH ROW EXECUTE FUNCTION public.f8c_feedback_individual();
CREATE TRIGGER f8c_feedback_truncate BEFORE TRUNCATE ON public.retroalimentacion_docente
 FOR EACH STATEMENT EXECUTE FUNCTION public.f8c_inmutable();
"""


def upgrade():
    if op.get_bind().dialect.name!="postgresql":
        raise RuntimeError("La revisión académica se prueba solo en PostgreSQL desechable.")
    op.alter_column("resultado_intento","nota_final",type_=sa.Numeric(5,2),existing_type=sa.Numeric(4,2),existing_nullable=False)
    op.drop_constraint("ck_8c_resultado","resultado_intento",type_="check")
    op.create_check_constraint("ck_8c_resultado","resultado_intento","modalidad IN ('COMPLETA','PARCIAL') AND nota_final >= 0 AND nota_final <= 100")
    op.create_table("retroalimentacion_docente",
        sa.Column("id_retroalimentacion",sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column("id_asignacion",sa.Integer(),sa.ForeignKey("asignacion_caso.id_asignacion"),nullable=False),
        sa.Column("id_participacion",sa.Integer(),sa.ForeignKey("participacion.id_participacion"),nullable=False,unique=True),
        sa.Column("id_profesor",sa.Integer(),sa.ForeignKey("usuario.id_usuario"),nullable=False),
        sa.Column("texto",sa.Text(),nullable=False),
        sa.Column("fecha_registro",sa.DateTime(),nullable=False))
    op.get_bind().exec_driver_sql(SQL,execution_options={"no_parameters":True})


def downgrade():
    b=op.get_bind()
    if b.dialect.name!="postgresql":raise RuntimeError("Downgrade reservado a PostgreSQL aislado.")
    b.exec_driver_sql("LOCK TABLE resultado_intento,retroalimentacion_docente IN ACCESS EXCLUSIVE MODE")
    if b.scalar(sa.text("SELECT 1 FROM retroalimentacion_docente LIMIT 1")) is not None:
        raise RuntimeError("No eliminar feedback individual existente.")
    if b.scalar(sa.text("SELECT 1 FROM resultado_intento WHERE nota_final>=100 LIMIT 1")) is not None:
        raise RuntimeError("La escala anterior no admite resultados de 100.")
    b.exec_driver_sql("DROP TRIGGER f8c_feedback ON public.retroalimentacion_docente; DROP TRIGGER f8c_feedback_truncate ON public.retroalimentacion_docente; DROP FUNCTION public.f8c_feedback_individual()")
    op.drop_table("retroalimentacion_docente")
    op.drop_constraint("ck_8c_resultado","resultado_intento",type_="check")
    op.create_check_constraint("ck_8c_resultado","resultado_intento","modalidad IN ('COMPLETA','PARCIAL') AND nota_final >= 0 AND nota_final < 100")
    op.alter_column("resultado_intento","nota_final",type_=sa.Numeric(4,2),existing_type=sa.Numeric(5,2),existing_nullable=False)
