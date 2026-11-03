"""8C: resultados técnicos de laboratorio con procedencia histórica verificable."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_evaluation_results"
down_revision = "20261102_steps_uuid"
branch_labels = None
depends_on = None

SQL = r"""
CREATE FUNCTION public.f8c_inmutable() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN RAISE EXCEPTION '8C: resultado historico inmutable' USING ERRCODE='23514'; END $f$;

CREATE FUNCTION public.f8c_cabecera() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE p integer; contexto record; j jsonb; d jsonb;
BEGIN
 IF current_database()<>'sps_identity_test_resolver' THEN
  RAISE EXCEPTION '8C: escrituras tecnicas solo en laboratorio identificado' USING ERRCODE='23514';
 END IF;
 IF current_setting('transaction_isolation') <> 'read committed' THEN
  RAISE EXCEPTION '8C: escritor requiere READ COMMITTED' USING ERRCODE='40001';
 END IF;
 SELECT id_participacion INTO p FROM public.intento WHERE id_intento=NEW.id_intento;
 PERFORM 1 FROM public.participacion WHERE id_participacion=p FOR UPDATE;
 PERFORM 1 FROM public.intento WHERE id_intento=NEW.id_intento FOR UPDATE;
 SELECT i.estado,a.version_caso_id,v.caso_id,c.id_caso,r.id AS rubrica_id,r.version_regla
 INTO contexto FROM public.intento i JOIN public.participacion x USING(id_participacion)
 JOIN public.asignacion_caso a USING(id_asignacion)
 JOIN public.version_caso v ON v.id=a.version_caso_id JOIN public.caso c ON c.id=v.caso_id
 JOIN public.rubrica r ON r.version_caso_id=v.id WHERE i.id_intento=NEW.id_intento;
 IF NOT FOUND OR contexto.estado NOT IN ('FINALIZADO','VENCIDO') THEN
  RAISE EXCEPTION '8C: intento cerrado requerido' USING ERRCODE='23514';
 END IF;
 IF (NEW.version_caso_id,NEW.caso_id,NEW.id_caso,NEW.rubrica_id,NEW.version_regla)
  IS DISTINCT FROM (contexto.version_caso_id,contexto.caso_id,contexto.id_caso,contexto.rubrica_id,contexto.version_regla)
  OR (NEW.modalidad='COMPLETA' AND contexto.estado<>'FINALIZADO') THEN
  RAISE EXCEPTION '8C: referencia historica incompatible' USING ERRCODE='23514';
 END IF;
 IF encode(sha256(convert_to(NEW.procedencia,'UTF8')),'hex') IS DISTINCT FROM NEW.procedencia_sha256 THEN
  RAISE EXCEPTION '8C: huella de procedencia invalida' USING ERRCODE='23514';
 END IF;
 j:=NEW.procedencia::jsonb; d:=(j->>'definicion_documento')::jsonb;
 IF (j->>'formato') IS DISTINCT FROM '1' OR (d->>'ambito') IS DISTINCT FROM 'LABORATORIO'
  OR (d->>'id') IS DISTINCT FROM NEW.politica_id OR (d->>'version') IS DISTINCT FROM NEW.politica_version
  OR encode(sha256(convert_to(j->>'definicion_documento','UTF8')),'hex') IS DISTINCT FROM NEW.politica_hash
  OR jsonb_typeof(d->'mapeo') IS DISTINCT FROM 'object'
  OR jsonb_typeof(d->'clasificacion') IS DISTINCT FROM 'object'
  OR jsonb_typeof(d->'agregacion') IS DISTINCT FROM 'object'
  OR d->'mapeo'='{}'::jsonb OR d->'clasificacion'='{}'::jsonb OR d->'agregacion'='{}'::jsonb
  OR coalesce(d#>>'{implementaciones,mapeo}','')=''
  OR coalesce(d#>>'{implementaciones,clasificacion_calculo}','')=''
  OR coalesce(d#>>'{implementaciones,recorrido}','')=''
  OR coalesce(length(d->>'motor_sha256'),0)<>64
  OR jsonb_typeof(j->'motor') IS DISTINCT FROM 'object' OR j->'motor'='{}'::jsonb
  OR jsonb_typeof(j->'intento') IS DISTINCT FROM 'object'
  OR jsonb_typeof(j->'fuente_rubrica') IS DISTINCT FROM 'object'
  OR jsonb_typeof(j#>'{plan,niveles}') IS DISTINCT FROM 'array'
  OR jsonb_typeof(j#>'{plan,politica}') IS DISTINCT FROM 'object'
  OR (j->>'motor_documento')::jsonb IS DISTINCT FROM j->'motor'
  OR encode(sha256(convert_to(j->>'motor_documento','UTF8')),'hex') IS DISTINCT FROM d->>'motor_sha256'
  OR jsonb_typeof(j->'plan') IS DISTINCT FROM 'object'
  OR jsonb_typeof(j->'rubrica') IS DISTINCT FROM 'object'
  OR (j#>>'{plan,politica,identificador}') IS DISTINCT FROM (j#>>'{datos,politica_calculo}')
  OR (j#>>'{datos,id_intento}')::integer IS DISTINCT FROM NEW.id_intento
  OR (j#>>'{datos,id_participacion}')::integer IS DISTINCT FROM p
  OR (j#>>'{datos,nota_final}')::numeric IS DISTINCT FROM NEW.nota_final
  OR (j#>>'{datos,modalidad}') IS DISTINCT FROM NEW.modalidad
  OR (j#>>'{datos,referencia,id_caso}')::integer IS DISTINCT FROM NEW.id_caso
  OR (j#>>'{datos,referencia,id_rubrica}')::uuid IS DISTINCT FROM NEW.rubrica_id
  OR (j#>>'{datos,referencia,version}') IS DISTINCT FROM (NEW.version_caso_id::text||':'||NEW.version_regla)
  OR (j#>'{datos,pendientes}') IS DISTINCT FROM '[]'::jsonb THEN
  RAISE EXCEPTION '8C: procedencia incompleta o incompatible' USING ERRCODE='23514';
 END IF;
 -- Una definición publicada bajo id/versión no admite otra huella. Un lock por
 -- clave serializa escritores aunque pertenezcan a intentos diferentes.
 PERFORM pg_advisory_xact_lock(hashtextextended(NEW.politica_id||':'||NEW.politica_version,0));
 IF EXISTS(SELECT 1 FROM public.resultado_intento WHERE politica_id=NEW.politica_id
  AND politica_version=NEW.politica_version AND politica_hash<>NEW.politica_hash) THEN
  RAISE EXCEPTION '8C: definicion de politica ya vinculada a otra huella' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;

CREATE FUNCTION public.f8c_completo() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE r public.resultado_intento; n integer; j jsonb;
BEGIN
 SELECT * INTO r FROM public.resultado_intento WHERE id_resultado=NEW.id_resultado;
 j:=r.procedencia::jsonb;
 SELECT count(*) INTO n FROM public.criterio_rubrica WHERE rubrica_id=r.rubrica_id;
 IF n=0 OR n<>(SELECT count(*) FROM public.resultado_criterio WHERE id_resultado=r.id_resultado)
  OR n IS DISTINCT FROM jsonb_array_length(j#>'{datos,criterios}') THEN
  RAISE EXCEPTION '8C: detalle incompleto' USING ERRCODE='23514';
 END IF;
 IF EXISTS(SELECT 1 FROM public.resultado_criterio c WHERE c.id_resultado=r.id_resultado
  AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(j#>'{datos,criterios}') e
   WHERE (e->>'id_criterio')::uuid=c.id_criterio AND (e->>'id_nivel')::uuid=c.id_nivel
    AND (e->>'puntaje_obtenido')::numeric=c.puntaje_obtenido)) THEN
  RAISE EXCEPTION '8C: detalle no coincide con procedencia' USING ERRCODE='23514';
 END IF;
 IF EXISTS(SELECT 1 FROM public.paso_simulacion s WHERE s.id_intento=r.id_intento
  AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(j#>'{datos,evidencias}') e
    WHERE (e->>'id_decision')::uuid=s.id_decision AND (e->>'id_opcion')::uuid=s.id_opcion))
  OR (SELECT count(*) FROM public.paso_simulacion WHERE id_intento=r.id_intento)
   IS DISTINCT FROM (SELECT count(*) FROM jsonb_array_elements(j#>'{datos,evidencias}') e
    WHERE e->>'id_opcion' IS NOT NULL) THEN
  RAISE EXCEPTION '8C: respuestas no coinciden con intento' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $f$;
CREATE TRIGGER f8c_cabecera BEFORE INSERT ON public.resultado_intento FOR EACH ROW EXECUTE FUNCTION public.f8c_cabecera();
CREATE TRIGGER f8c_historia BEFORE UPDATE OR DELETE ON public.resultado_intento FOR EACH ROW EXECUTE FUNCTION public.f8c_inmutable();
CREATE TRIGGER f8c_historia BEFORE UPDATE OR DELETE ON public.resultado_criterio FOR EACH ROW EXECUTE FUNCTION public.f8c_inmutable();
CREATE TRIGGER f8c_truncate BEFORE TRUNCATE ON public.resultado_intento FOR EACH STATEMENT EXECUTE FUNCTION public.f8c_inmutable();
CREATE TRIGGER f8c_truncate BEFORE TRUNCATE ON public.resultado_criterio FOR EACH STATEMENT EXECUTE FUNCTION public.f8c_inmutable();
CREATE CONSTRAINT TRIGGER f8c_completo AFTER INSERT ON public.resultado_intento DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION public.f8c_completo();
CREATE CONSTRAINT TRIGGER f8c_completo AFTER INSERT ON public.resultado_criterio DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION public.f8c_completo();
"""


def upgrade():
    if op.get_bind().dialect.name!="postgresql":
        raise RuntimeError("La revisión 8C se valida exclusivamente en PostgreSQL aislado.")
    op.create_index("uq_8c_criterio_rubrica","criterio_rubrica",["id","rubrica_id"],unique=True)
    op.create_index("uq_8c_nivel_criterio","nivel_rubrica",["id","criterio_id"],unique=True)
    op.create_table("resultado_intento",
        sa.Column("id_resultado",sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column("id_intento",sa.Integer(),sa.ForeignKey("intento.id_intento"),nullable=False),
        sa.Column("nota_final",sa.Numeric(4,2),nullable=False),
        sa.Column("fecha_calculo",sa.DateTime(timezone=True),nullable=False),
        sa.Column("comentario_automatico",sa.Text()),
        sa.Column("id_caso",sa.Integer(),sa.ForeignKey("caso.id_caso"),nullable=False),
        sa.Column("caso_id",sa.Uuid(),sa.ForeignKey("caso.id"),nullable=False),
        sa.Column("version_caso_id",sa.Uuid(),sa.ForeignKey("version_caso.id"),nullable=False),
        sa.Column("rubrica_id",sa.Uuid(),sa.ForeignKey("rubrica.id"),nullable=False),
        sa.Column("version_regla",sa.String(20),nullable=False),
        sa.Column("modalidad",sa.String(20),nullable=False),
        sa.Column("ambito",sa.String(16),nullable=False),
        sa.Column("politica_id",sa.Text(),nullable=False),
        sa.Column("politica_version",sa.Text(),nullable=False),
        sa.Column("politica_hash",sa.String(64),nullable=False),
        sa.Column("procedencia",sa.Text(),nullable=False),
        sa.Column("procedencia_sha256",sa.String(64),nullable=False),
        sa.UniqueConstraint("id_intento",name="uq_8c_resultado_intento"),
        sa.UniqueConstraint("id_resultado","rubrica_id",name="uq_8c_resultado_rubrica"),
        sa.CheckConstraint("ambito = 'LABORATORIO'",name="ck_8c_solo_laboratorio"),
        sa.CheckConstraint("modalidad IN ('COMPLETA','PARCIAL') AND nota_final >= 0 AND nota_final < 100",name="ck_8c_resultado"),
        sa.CheckConstraint("length(procedencia_sha256)=64 AND length(politica_hash)=64",name="ck_8c_hash"))
    op.create_table("resultado_criterio",
        sa.Column("id_resultado_criterio",sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column("id_resultado",sa.Integer(),nullable=False),
        sa.Column("rubrica_id",sa.Uuid(),nullable=False),
        sa.Column("id_criterio",sa.Uuid(),nullable=False),
        sa.Column("id_nivel",sa.Uuid(),nullable=False),
        sa.Column("puntaje_obtenido",sa.Numeric(5,2),nullable=False),
        sa.UniqueConstraint("id_resultado","id_criterio",name="uq_8c_resultado_criterio"),
        sa.ForeignKeyConstraint(["id_resultado","rubrica_id"],["resultado_intento.id_resultado","resultado_intento.rubrica_id"],name="fk_8c_detalle_cabecera"),
        sa.ForeignKeyConstraint(["id_criterio","rubrica_id"],["criterio_rubrica.id","criterio_rubrica.rubrica_id"],name="fk_8c_detalle_rubrica"),
        sa.ForeignKeyConstraint(["id_nivel","id_criterio"],["nivel_rubrica.id","nivel_rubrica.criterio_id"],name="fk_8c_detalle_nivel"),
        sa.CheckConstraint("puntaje_obtenido >= 0 AND puntaje_obtenido < 1000",name="ck_8c_puntaje"))
    if op.get_bind().dialect.name=="postgresql":
        op.get_bind().exec_driver_sql(SQL,execution_options={"no_parameters":True})


def downgrade():
    b=op.get_bind()
    if b.dialect.name=="postgresql":
        b.exec_driver_sql("LOCK TABLE resultado_intento,resultado_criterio IN ACCESS EXCLUSIVE MODE")
    if b.scalar(sa.text("SELECT 1 FROM resultado_intento LIMIT 1")) is not None or b.scalar(sa.text("SELECT 1 FROM resultado_criterio LIMIT 1")) is not None:
        raise RuntimeError("Downgrade 8C rechazado: existen resultados historicos.")
    if b.dialect.name=="postgresql":
        for tabla in ("resultado_criterio","resultado_intento"):
            for nombre in ("f8c_completo","f8c_historia","f8c_truncate"):
                b.exec_driver_sql(f"DROP TRIGGER {nombre} ON public.{tabla}")
        b.exec_driver_sql("DROP TRIGGER f8c_cabecera ON public.resultado_intento; DROP FUNCTION public.f8c_completo(); DROP FUNCTION public.f8c_cabecera(); DROP FUNCTION public.f8c_inmutable()")
    op.drop_table("resultado_criterio")
    op.drop_table("resultado_intento")
    op.drop_index("uq_8c_nivel_criterio",table_name="nivel_rubrica")
    op.drop_index("uq_8c_criterio_rubrica",table_name="criterio_rubrica")
