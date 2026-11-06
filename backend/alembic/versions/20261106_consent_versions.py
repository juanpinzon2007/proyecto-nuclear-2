"""Versiones y selector técnico separados de la asignación histórica."""
from alembic import op
import sqlalchemy as sa

revision = '20261106_consent_versions'
down_revision = '20261105_waiting_admission'
branch_labels = None
depends_on = None

SQL = r"""
CREATE FUNCTION public.sps_documento_consentimiento() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 IF TG_OP<>'INSERT' THEN
  RAISE EXCEPTION 'CONSENTIMIENTO: publicacion historica inmutable' USING ERRCODE='23514';
 END IF;
 IF NEW.sha256_original<>encode(sha256(NEW.original),'hex') OR
    NEW.sha256_texto<>encode(sha256(convert_to(NEW.texto,'UTF8')),'hex') OR
    NEW.sha256_aprobacion<>encode(sha256(NEW.evidencia_aprobacion),'hex') THEN
  RAISE EXCEPTION 'CONSENTIMIENTO: huella incompatible' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $f$;
CREATE FUNCTION public.sps_seleccion_consentimiento() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE clave integer;
BEGIN
 IF TG_OP='UPDATE' AND NEW.id_asignacion IS DISTINCT FROM OLD.id_asignacion THEN
  RAISE EXCEPTION 'CONSENTIMIENTO: no reasignar selector' USING ERRCODE='23514';
 END IF;
 clave=CASE WHEN TG_OP='DELETE' THEN OLD.id_asignacion ELSE NEW.id_asignacion END;
 PERFORM 1 FROM public.asignacion_caso WHERE id_asignacion=clave FOR KEY SHARE;
 IF NOT pg_try_advisory_xact_lock(782061,clave) THEN
  RAISE EXCEPTION 'CONSENTIMIENTO: selector ocupado; reintentar transaccion' USING ERRCODE='55P03';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $f$;
CREATE FUNCTION public.sps_evidencia_consentimiento() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE d public.documento_consentimiento_version%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN
  IF OLD.id_version_documento IS NOT NULL THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: evidencia no eliminable' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' AND OLD.id_version_documento IS NULL AND NEW.id_version_documento IS NOT NULL THEN
  RAISE EXCEPTION 'CONSENTIMIENTO: no convertir aceptacion legada' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND OLD.id_version_documento IS NOT NULL AND
   (NEW.id_consentimiento,NEW.id_estudiante,NEW.version_texto,NEW.fecha_aceptacion,
    NEW.id_version_documento,NEW.aceptacion_explicita,NEW.huella_aceptada)
   IS DISTINCT FROM
   (OLD.id_consentimiento,OLD.id_estudiante,OLD.version_texto,OLD.fecha_aceptacion,
    OLD.id_version_documento,OLD.aceptacion_explicita,OLD.huella_aceptada) THEN
  RAISE EXCEPTION 'CONSENTIMIENTO: evidencia inmutable' USING ERRCODE='23514';
 END IF;
 IF NEW.id_version_documento IS NOT NULL THEN
  SELECT * INTO d FROM public.documento_consentimiento_version
   WHERE id_version_documento=NEW.id_version_documento FOR SHARE;
  IF NOT FOUND OR NEW.version_texto<>d.referencia OR NEW.huella_aceptada<>d.sha256_texto THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: definicion incompatible' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='UPDATE' AND NEW.fecha_revocacion IS DISTINCT FROM OLD.fecha_revocacion THEN
  IF OLD.fecha_revocacion IS NOT NULL OR EXISTS(SELECT 1 FROM public.intento
    WHERE id_consentimiento=OLD.id_consentimiento AND estado='EN_CURSO') THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: revocacion no disponible' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $f$;
CREATE FUNCTION public.sps_vinculo_consentimiento() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE c public.consentimiento%ROWTYPE; alumno integer;
BEGIN
 IF TG_TABLE_NAME='participacion' THEN
  IF TG_OP='UPDATE' AND NEW.id_consentimiento IS DISTINCT FROM OLD.id_consentimiento THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: vinculo historico inmutable' USING ERRCODE='23514';
  END IF;
  IF TG_OP='INSERT' AND NEW.id_consentimiento IS NOT NULL THEN
   SELECT id_estudiante INTO alumno FROM public.grupo_estudiante
    WHERE id_grupo_estudiante=NEW.id_grupo_estudiante FOR SHARE;
   SELECT * INTO c FROM public.consentimiento WHERE id_consentimiento=NEW.id_consentimiento FOR SHARE;
   IF NOT FOUND OR c.id_estudiante IS DISTINCT FROM alumno OR c.fecha_revocacion IS NOT NULL
      OR c.fecha_aceptacion>NEW.fecha_registro THEN
    RAISE EXCEPTION 'CONSENTIMIENTO: aceptacion incompatible' USING ERRCODE='23514';
   END IF;
   IF c.id_version_documento IS NOT NULL THEN
    PERFORM 1 FROM public.asignacion_caso WHERE id_asignacion=NEW.id_asignacion FOR KEY SHARE;
    PERFORM pg_advisory_xact_lock_shared(782061,NEW.id_asignacion);
    IF NOT EXISTS(SELECT 1 FROM public.seleccion_consentimiento
       WHERE id_asignacion=NEW.id_asignacion AND id_version_documento=c.id_version_documento) THEN
     RAISE EXCEPTION 'CONSENTIMIENTO: version ya sustituida' USING ERRCODE='23514';
    END IF;
   END IF;
  END IF;
 ELSE
  SELECT * INTO c FROM public.consentimiento WHERE id_consentimiento=NEW.id_consentimiento FOR SHARE;
  IF c.fecha_revocacion IS NOT NULL THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: aceptacion revocada' USING ERRCODE='23514';
  END IF;
  IF c.id_version_documento IS NOT NULL AND EXISTS(SELECT 1 FROM public.participacion
       WHERE id_participacion=NEW.id_participacion AND id_consentimiento IS NULL) THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: participacion legada sin enlace verificable' USING ERRCODE='23514';
  END IF;
  IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM public.participacion
       WHERE id_participacion=NEW.id_participacion AND id_consentimiento IS NOT NULL
         AND id_consentimiento<>NEW.id_consentimiento) THEN
   RAISE EXCEPTION 'CONSENTIMIENTO: intento con otro consentimiento' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $f$;
CREATE FUNCTION public.sps_consentimiento_no_truncar() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN RAISE EXCEPTION 'CONSENTIMIENTO: no truncar evidencia' USING ERRCODE='23514'; END $f$;
CREATE TRIGGER sps_documento_version BEFORE INSERT OR UPDATE OR DELETE ON public.documento_consentimiento_version
 FOR EACH ROW EXECUTE FUNCTION public.sps_documento_consentimiento();
CREATE TRIGGER sps_selector_version BEFORE INSERT OR UPDATE OR DELETE ON public.seleccion_consentimiento
 FOR EACH ROW EXECUTE FUNCTION public.sps_seleccion_consentimiento();
CREATE TRIGGER sps_aceptacion_version BEFORE INSERT OR UPDATE OR DELETE ON public.consentimiento
 FOR EACH ROW EXECUTE FUNCTION public.sps_evidencia_consentimiento();
CREATE TRIGGER sps_participacion_consentimiento BEFORE INSERT OR UPDATE ON public.participacion
 FOR EACH ROW EXECUTE FUNCTION public.sps_vinculo_consentimiento();
CREATE TRIGGER sps_intento_consentimiento BEFORE INSERT ON public.intento
 FOR EACH ROW EXECUTE FUNCTION public.sps_vinculo_consentimiento();
CREATE TRIGGER sps_documento_no_truncar BEFORE TRUNCATE ON public.documento_consentimiento_version
 FOR EACH STATEMENT EXECUTE FUNCTION public.sps_consentimiento_no_truncar();
CREATE TRIGGER sps_aceptacion_no_truncar BEFORE TRUNCATE ON public.consentimiento
 FOR EACH STATEMENT EXECUTE FUNCTION public.sps_consentimiento_no_truncar();
CREATE TRIGGER sps_selector_no_truncar BEFORE TRUNCATE ON public.seleccion_consentimiento
 FOR EACH STATEMENT EXECUTE FUNCTION public.sps_consentimiento_no_truncar();
"""


def upgrade():
    if op.get_bind().dialect.name != 'postgresql':
        raise RuntimeError('Consentimiento documental requiere PostgreSQL.')
    op.create_table('documento_consentimiento_version',
        sa.Column('id_version_documento', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('referencia', sa.String(30), nullable=False),
        sa.Column('documento_id', sa.Text(), nullable=False), sa.Column('version', sa.Text(), nullable=False),
        sa.Column('original', sa.LargeBinary(), nullable=False), sa.Column('tipo_media', sa.Text(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False), sa.Column('sha256_original', sa.String(64), nullable=False),
        sa.Column('sha256_texto', sa.String(64), nullable=False),
        sa.Column('autoridad_aprobadora', sa.Text(), nullable=False),
        sa.Column('aprobado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidencia_aprobacion', sa.LargeBinary(), nullable=False),
        sa.Column('sha256_aprobacion', sa.String(64), nullable=False),
        sa.Column('publicado_por', sa.Integer(), sa.ForeignKey('usuario.id_usuario'), nullable=False),
        sa.Column('publicado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('vigente_desde', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('referencia', name='uq_documento_consentimiento_referencia'),
        sa.UniqueConstraint('documento_id','version', name='uq_documento_consentimiento_edicion'),
        sa.CheckConstraint("length(trim(referencia))>0 AND length(trim(documento_id))>0 AND length(trim(version))>0 AND length(trim(texto))>0 AND length(trim(tipo_media))>0 AND length(trim(autoridad_aprobadora))>0", name='ck_documento_consentimiento_textos'),
        sa.CheckConstraint('length(original)>0 AND length(evidencia_aprobacion)>0', name='ck_documento_consentimiento_bytes'),
        sa.CheckConstraint('publicado_en>=aprobado_en', name='ck_documento_consentimiento_fechas'))
    op.create_table('seleccion_consentimiento',
        sa.Column('id_asignacion', sa.Integer(), sa.ForeignKey('asignacion_caso.id_asignacion'), primary_key=True),
        sa.Column('id_version_documento',sa.Integer(),sa.ForeignKey('documento_consentimiento_version.id_version_documento'),nullable=False),
        sa.Column('seleccionado_por',sa.Integer(),sa.ForeignKey('usuario.id_usuario'),nullable=False),
        sa.Column('seleccionado_en',sa.DateTime(timezone=True),nullable=False))
    op.add_column('consentimiento',sa.Column('id_version_documento',sa.Integer(),nullable=True))
    op.add_column('consentimiento',sa.Column('aceptacion_explicita',sa.Boolean(),nullable=True))
    op.add_column('consentimiento',sa.Column('huella_aceptada',sa.String(64),nullable=True))
    op.create_foreign_key('fk_consentimiento_documento','consentimiento','documento_consentimiento_version',['id_version_documento'],['id_version_documento'])
    op.create_check_constraint('ck_consentimiento_evidencia','consentimiento',
        '(id_version_documento IS NULL AND aceptacion_explicita IS NULL AND huella_aceptada IS NULL) OR (id_version_documento IS NOT NULL AND aceptacion_explicita IS TRUE AND huella_aceptada IS NOT NULL AND length(huella_aceptada)=64)')
    op.create_index('uq_consentimiento_explicito_vigente','consentimiento',['id_estudiante','id_version_documento'],unique=True,
        postgresql_where=sa.text('aceptacion_explicita IS TRUE AND fecha_revocacion IS NULL'))
    op.add_column('participacion',sa.Column('id_consentimiento',sa.Integer(),nullable=True))
    op.create_foreign_key('fk_participacion_consentimiento','participacion','consentimiento',['id_consentimiento'],['id_consentimiento'])
    op.execute(SQL)


def downgrade():
    op.execute('LOCK TABLE public.documento_consentimiento_version, public.seleccion_consentimiento, public.consentimiento, public.participacion IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().scalar(sa.text('SELECT EXISTS(SELECT 1 FROM documento_consentimiento_version) OR EXISTS(SELECT 1 FROM consentimiento WHERE id_version_documento IS NOT NULL) OR EXISTS(SELECT 1 FROM participacion WHERE id_consentimiento IS NOT NULL)')):
        raise RuntimeError('No eliminar evidencia documental o vinculos de consentimiento.')
    for table, name in [('seleccion_consentimiento','sps_selector_no_truncar'),('consentimiento','sps_aceptacion_no_truncar'),
                        ('documento_consentimiento_version','sps_documento_no_truncar'),('intento','sps_intento_consentimiento'),
                        ('participacion','sps_participacion_consentimiento'),('consentimiento','sps_aceptacion_version'),
                        ('seleccion_consentimiento','sps_selector_version'),('documento_consentimiento_version','sps_documento_version')]:
        op.execute(f'DROP TRIGGER {name} ON public.{table}')
    for name in ['sps_consentimiento_no_truncar','sps_vinculo_consentimiento','sps_evidencia_consentimiento','sps_seleccion_consentimiento','sps_documento_consentimiento']:
        op.execute(f'DROP FUNCTION public.{name}()')
    # Nombres explícitos de esta revisión; no retirar objetos anteriores.
    op.drop_constraint('fk_participacion_consentimiento','participacion',type_='foreignkey')
    op.drop_column('participacion','id_consentimiento')
    op.drop_index('uq_consentimiento_explicito_vigente',table_name='consentimiento')
    op.drop_constraint('ck_consentimiento_evidencia','consentimiento',type_='check')
    op.drop_constraint('fk_consentimiento_documento','consentimiento',type_='foreignkey')
    for name in ['huella_aceptada','aceptacion_explicita','id_version_documento']:op.drop_column('consentimiento',name)
    op.drop_table('seleccion_consentimiento');op.drop_table('documento_consentimiento_version')
