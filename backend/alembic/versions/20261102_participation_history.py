"""BD2-07 D1-D4: estructuras históricas, sin habilitar escritores académicos."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_participation_history"
down_revision = "20261102_assignment_bridge"
branch_labels = None
depends_on = None

GUARDS = r"""
CREATE FUNCTION public.bd207_participacion() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE alumno integer; grupo integer; grupo_asignado integer; sesion uuid;
 convocado uuid; referencia uuid; cantidad integer; estado_conv text; matriculado boolean;
BEGIN
 IF current_setting('transaction_isolation')='repeatable read' THEN
  RAISE EXCEPTION 'BD207: usar READ COMMITTED o SERIALIZABLE' USING ERRCODE='40001';
 END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'BD207: historial no eliminable' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (NEW.id_participacion,NEW.id_asignacion,NEW.id_grupo_estudiante,NEW.convocatoria_id,NEW.fecha_registro)
   IS DISTINCT FROM (OLD.id_participacion,OLD.id_asignacion,OLD.id_grupo_estudiante,OLD.convocatoria_id,OLD.fecha_registro) THEN
   RAISE EXCEPTION 'BD207: contexto historico inmutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 SELECT id_estudiante INTO alumno FROM public.grupo_estudiante WHERE id_grupo_estudiante=NEW.id_grupo_estudiante FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD207: matricula inexistente' USING ERRCODE='23503'; END IF;
 -- La cuenta serializa también inserciones de nuevos vínculos: no hay fila
 -- inexistente de identidad que pudiera bloquearse para impedir ambigüedad.
 PERFORM 1 FROM public.usuario WHERE id_usuario=alumno FOR UPDATE;
 SELECT estudiante_id,sesion_id,estado INTO convocado,sesion,estado_conv FROM public.convocatoria
  WHERE id=NEW.convocatoria_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD207: convocatoria inexistente' USING ERRCODE='23503'; END IF;
 SELECT id_grupo INTO grupo_asignado FROM public.asignacion_caso
  WHERE id_asignacion=NEW.id_asignacion AND sesion_programada_id=sesion FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD207: asignacion incompatible' USING ERRCODE='23514'; END IF;
 SELECT id_estudiante,id_grupo,activo INTO alumno,grupo,matriculado FROM public.grupo_estudiante
  WHERE id_grupo_estudiante=NEW.id_grupo_estudiante FOR SHARE;
 IF grupo<>grupo_asignado OR NOT matriculado OR estado_conv<>'ACTIVA' THEN
  RAISE EXCEPTION 'BD207: pertenencia no acreditada' USING ERRCODE='23514';
 END IF;
 SELECT count(*) INTO cantidad FROM public.identidad_academica WHERE id_usuario=alumno AND sistema='SCHEDULING';
 SELECT id_academico INTO referencia FROM public.identidad_academica WHERE id_usuario=alumno AND sistema='SCHEDULING' LIMIT 1;
 IF cantidad<>1 OR referencia IS DISTINCT FROM convocado THEN
  RAISE EXCEPTION 'BD207: identidad no inequivoca' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;

CREATE FUNCTION public.bd207_padre() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE usado boolean; cambia boolean;
BEGIN
 IF current_setting('transaction_isolation')='repeatable read' THEN
  RAISE EXCEPTION 'BD207: usar READ COMMITTED o SERIALIZABLE' USING ERRCODE='40001';
 END IF;
 IF TG_TABLE_NAME='convocatoria' THEN
  SELECT EXISTS(SELECT 1 FROM public.participacion WHERE convocatoria_id=OLD.id) INTO usado;
  cambia=TG_OP='DELETE' OR (NEW.id,NEW.sesion_id,NEW.estudiante_id) IS DISTINCT FROM (OLD.id,OLD.sesion_id,OLD.estudiante_id);
 ELSIF TG_TABLE_NAME='grupo_estudiante' THEN
  SELECT EXISTS(SELECT 1 FROM public.participacion WHERE id_grupo_estudiante=OLD.id_grupo_estudiante) INTO usado;
  cambia=TG_OP='DELETE' OR (NEW.id_grupo_estudiante,NEW.id_grupo,NEW.id_estudiante) IS DISTINCT FROM (OLD.id_grupo_estudiante,OLD.id_grupo,OLD.id_estudiante);
 ELSIF TG_TABLE_NAME='consentimiento' THEN
  SELECT EXISTS(SELECT 1 FROM public.intento WHERE id_consentimiento=OLD.id_consentimiento) INTO usado;
  cambia=TG_OP='DELETE' OR (NEW.id_consentimiento,NEW.id_estudiante,NEW.version_texto,NEW.fecha_aceptacion)
   IS DISTINCT FROM (OLD.id_consentimiento,OLD.id_estudiante,OLD.version_texto,OLD.fecha_aceptacion);
 ELSE
  SELECT EXISTS(SELECT 1 FROM public.intento WHERE id_permiso_extra=OLD.id_permiso_extra) INTO usado;
  cambia=TG_OP='DELETE' OR NEW IS DISTINCT FROM OLD;
 END IF;
 IF usado AND cambia THEN RAISE EXCEPTION 'BD207: referencia historica protegida' USING ERRCODE='23514'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $f$;

CREATE FUNCTION public.bd207_identidad() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 IF current_setting('transaction_isolation')='repeatable read' THEN
  RAISE EXCEPTION 'BD207: usar READ COMMITTED o SERIALIZABLE' USING ERRCODE='40001';
 END IF;
 IF TG_OP='UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
 IF (TG_OP<>'INSERT' AND OLD.sistema='SCHEDULING') OR (TG_OP<>'DELETE' AND NEW.sistema='SCHEDULING') THEN
  PERFORM 1 FROM public.usuario WHERE id_usuario IN (OLD.id_usuario,NEW.id_usuario) ORDER BY id_usuario FOR UPDATE;
  IF EXISTS(SELECT 1 FROM public.participacion p JOIN public.grupo_estudiante m USING(id_grupo_estudiante)
    WHERE m.id_estudiante IN (OLD.id_usuario,NEW.id_usuario)) THEN
   RAISE EXCEPTION 'BD207: vinculo historico protegido' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $f$;

CREATE FUNCTION public.bd207_intento() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE alumno integer; propietario integer; permiso_part integer; limite timestamp;
BEGIN
 IF current_setting('transaction_isolation')='repeatable read' THEN
  RAISE EXCEPTION 'BD207: usar READ COMMITTED o SERIALIZABLE' USING ERRCODE='40001';
 END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'BD207: intento historico no eliminable' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.estado<>'EN_CURSO' AND NEW IS DISTINCT FROM OLD THEN
   RAISE EXCEPTION 'BD207: intento cerrado inmutable' USING ERRCODE='23514';
  END IF;
  IF (NEW.id_intento,NEW.id_participacion,NEW.id_consentimiento,NEW.id_permiso_extra,NEW.numero_intento,NEW.inicio,NEW.duracion_concedida_segundos)
   IS DISTINCT FROM (OLD.id_intento,OLD.id_participacion,OLD.id_consentimiento,OLD.id_permiso_extra,OLD.numero_intento,OLD.inicio,OLD.duracion_concedida_segundos) THEN
   RAISE EXCEPTION 'BD207: identidad y tiempo historicos inmutables' USING ERRCODE='23514';
  END IF;
 ELSE
  PERFORM 1 FROM public.participacion WHERE id_participacion=NEW.id_participacion FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'BD207: participacion inexistente' USING ERRCODE='23503'; END IF;
  SELECT m.id_estudiante INTO alumno FROM public.participacion p JOIN public.grupo_estudiante m USING(id_grupo_estudiante)
   WHERE p.id_participacion=NEW.id_participacion;
  SELECT id_estudiante INTO propietario FROM public.consentimiento WHERE id_consentimiento=NEW.id_consentimiento FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'BD207: consentimiento inexistente' USING ERRCODE='23503'; END IF;
  IF propietario<>alumno THEN RAISE EXCEPTION 'BD207: consentimiento ajeno' USING ERRCODE='23514'; END IF;
  IF NEW.id_permiso_extra IS NOT NULL THEN
   SELECT id_participacion INTO permiso_part FROM public.permiso_intento_extra WHERE id_permiso_extra=NEW.id_permiso_extra FOR SHARE;
   IF NOT FOUND THEN RAISE EXCEPTION 'BD207: permiso inexistente' USING ERRCODE='23503'; END IF;
   IF permiso_part<>NEW.id_participacion THEN RAISE EXCEPTION 'BD207: permiso ajeno' USING ERRCODE='23514'; END IF;
  END IF;
 END IF;
 -- interval * numeric se resuelve mediante float8. Separar días y segundos
 -- acota la parte fraccionaria y conserva microsegundos sin esa conversión.
 limite=NEW.inicio
  +(trunc(NEW.duracion_concedida_segundos/86400)::text||' days')::interval
  +(mod(NEW.duracion_concedida_segundos,86400)::text||' seconds')::interval;
 IF (NEW.estado='FINALIZADO' AND NEW.fin>=limite) OR (NEW.estado='VENCIDO' AND NEW.fin IS DISTINCT FROM limite) THEN
  RAISE EXCEPTION 'BD207: cierre fuera de duracion historica' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;

CREATE FUNCTION public.bd207_no_truncar() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN RAISE EXCEPTION 'BD207: TRUNCATE historico prohibido' USING ERRCODE='23514'; END $f$;
"""

TRIGGERS = (
    ("participacion", "bd207_contexto", "INSERT OR UPDATE OR DELETE", "bd207_participacion", "ROW"),
    ("intento", "bd207_historia", "INSERT OR UPDATE OR DELETE", "bd207_intento", "ROW"),
    ("convocatoria", "bd207_convocatoria", "UPDATE OR DELETE", "bd207_padre", "ROW"),
    ("grupo_estudiante", "bd207_matricula", "UPDATE OR DELETE", "bd207_padre", "ROW"),
    ("consentimiento", "bd207_consentimiento", "UPDATE OR DELETE", "bd207_padre", "ROW"),
    ("permiso_intento_extra", "bd207_permiso", "UPDATE OR DELETE", "bd207_padre", "ROW"),
    ("identidad_academica", "bd207_identidad", "INSERT OR UPDATE OR DELETE", "bd207_identidad", "ROW"),
    ("participacion", "bd207_no_truncar_p", "TRUNCATE", "bd207_no_truncar", "STATEMENT"),
    ("intento", "bd207_no_truncar_i", "TRUNCATE", "bd207_no_truncar", "STATEMENT"),
)


def upgrade():
    op.create_table("participacion",
        sa.Column("id_participacion", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_asignacion", sa.Integer(), sa.ForeignKey("asignacion_caso.id_asignacion"), nullable=False),
        sa.Column("id_grupo_estudiante", sa.Integer(), sa.ForeignKey("grupo_estudiante.id_grupo_estudiante"), nullable=False),
        sa.Column("convocatoria_id", sa.Uuid(), sa.ForeignKey("convocatoria.id"), nullable=False, unique=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("fecha_registro", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("id_asignacion", "id_grupo_estudiante", name="uq_participacion_asignacion_matricula"))
    # Dependencia original obligatoria de la FK nullable de intento. No se crea
    # otra entidad, no se conceden permisos ni se importa el metadata pendiente.
    op.create_table("permiso_intento_extra",
        sa.Column("id_permiso_extra", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_participacion", sa.Integer(), sa.ForeignKey("participacion.id_participacion"), nullable=False),
        sa.Column("id_profesor", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False),
        sa.Column("cantidad_autorizada", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("justificacion", sa.Text(), nullable=False),
        sa.Column("fecha_autorizacion", sa.DateTime(), nullable=False))
    op.create_table("intento",
        sa.Column("id_intento", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_participacion", sa.Integer(), sa.ForeignKey("participacion.id_participacion"), nullable=False),
        sa.Column("id_consentimiento", sa.Integer(), sa.ForeignKey("consentimiento.id_consentimiento"), nullable=False),
        sa.Column("id_permiso_extra", sa.Integer(), sa.ForeignKey("permiso_intento_extra.id_permiso_extra")),
        sa.Column("numero_intento", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fin", sa.DateTime()),
        sa.Column("duracion_concedida_segundos", sa.Numeric(20, 6), nullable=False),
        sa.UniqueConstraint("id_participacion", "numero_intento", name="uq_intento_participacion_numero"),
        sa.CheckConstraint("numero_intento > 0", name="ck_intento_numero"),
        sa.CheckConstraint("duracion_concedida_segundos > 0", name="ck_intento_duracion"),
        sa.CheckConstraint("estado IN ('EN_CURSO','FINALIZADO','VENCIDO')", name="ck_intento_estado"),
        sa.CheckConstraint("(estado='EN_CURSO' AND fin IS NULL) OR (estado IN ('FINALIZADO','VENCIDO') AND fin IS NOT NULL AND fin>=inicio)", name="ck_intento_cierre"))
    op.create_index("uq_intento_un_activo", "intento", ["id_participacion"], unique=True,
                    postgresql_where=sa.text("estado='EN_CURSO'"), sqlite_where=sa.text("estado='EN_CURSO'"))
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql(GUARDS, execution_options={"no_parameters": True})
        for table, name, events, function, scope in TRIGGERS:
            bind.exec_driver_sql(f"CREATE TRIGGER {name} BEFORE {events} ON public.{table} FOR EACH {scope} EXECUTE FUNCTION public.{function}()")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql("LOCK TABLE public.participacion,public.permiso_intento_extra,public.intento IN ACCESS EXCLUSIVE MODE")
    for table in ("intento", "permiso_intento_extra", "participacion"):
        if bind.scalar(sa.text(f"SELECT 1 FROM {table} LIMIT 1")) is not None:
            raise RuntimeError("Downgrade BD207 rechazado: existen datos historicos.")
    if bind.dialect.name == "postgresql":
        for table, name, *_ in reversed(TRIGGERS):
            bind.exec_driver_sql(f"DROP TRIGGER {name} ON public.{table}")
        for name in ("bd207_no_truncar", "bd207_intento", "bd207_identidad", "bd207_padre", "bd207_participacion"):
            bind.exec_driver_sql(f"DROP FUNCTION public.{name}()")
    for table in ("intento", "permiso_intento_extra", "participacion"):
        op.drop_table(table)
