"""Espera/concesión en convocatoria, sin backfill ni tablas nuevas."""
from alembic import op
import sqlalchemy as sa

revision='20261105_waiting_admission'
down_revision='20261104_teacher_spaces'
branch_labels=None
depends_on=None

SQL=r"""
CREATE FUNCTION public.sps_guard_admision() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE estado_sesion text; evento public.evento_auditoria%ROWTYPE;
BEGIN
 IF TG_TABLE_NAME='evento_auditoria' THEN
  IF EXISTS(SELECT 1 FROM public.convocatoria WHERE admision_evento_id=OLD.id) THEN
   IF TG_OP='DELETE' OR NEW IS DISTINCT FROM OLD THEN
    RAISE EXCEPTION 'ADMISION: causa historica inmutable' USING ERRCODE='23514';
   END IF;
  END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
 END IF;
 IF TG_OP='DELETE' THEN
  IF OLD.espera_registrada_en IS NOT NULL THEN
   RAISE EXCEPTION 'ADMISION: solicitud historica protegida' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.espera_registrada_en IS NOT NULL AND
     (NEW.espera_registrada_en,NEW.espera_version_caso_id,NEW.id,NEW.sesion_id,NEW.estudiante_id)
     IS DISTINCT FROM
     (OLD.espera_registrada_en,OLD.espera_version_caso_id,OLD.id,OLD.sesion_id,OLD.estudiante_id) THEN
   RAISE EXCEPTION 'ADMISION: solicitud inmutable' USING ERRCODE='23514';
  END IF;
  IF OLD.admision_evento_id IS NOT NULL AND NEW.admision_evento_id IS DISTINCT FROM OLD.admision_evento_id THEN
   RAISE EXCEPTION 'ADMISION: concesion inmutable' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.espera_registrada_en IS NOT NULL AND
    (TG_OP='INSERT' OR OLD.espera_registrada_en IS NULL) THEN
  SELECT estado INTO estado_sesion FROM public.sesion_programada WHERE id=NEW.sesion_id FOR SHARE;
  IF estado_sesion IS DISTINCT FROM 'SIN_INICIAR' OR NEW.estado<>'ACTIVA' THEN
   RAISE EXCEPTION 'ADMISION: espera cerrada' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.admision_evento_id IS NOT NULL AND
    (TG_OP='INSERT' OR OLD.admision_evento_id IS NULL) THEN
  SELECT * INTO evento FROM public.evento_auditoria WHERE id=NEW.admision_evento_id FOR SHARE;
  SELECT estado INTO estado_sesion FROM public.sesion_programada WHERE id=NEW.sesion_id FOR SHARE;
  IF NOT FOUND OR evento.sesion_id IS DISTINCT FROM NEW.sesion_id OR
     evento.tipo IS DISTINCT FROM 'CAMBIO_ESTADO' OR evento.estado_anterior IS DISTINCT FROM 'SIN_INICIAR'
     OR evento.estado_nuevo IS DISTINCT FROM 'EN_CURSO' OR evento.origen IS DISTINCT FROM 'DOCENTE'
     OR estado_sesion IS DISTINCT FROM 'EN_CURSO' THEN
   RAISE EXCEPTION 'ADMISION: habilitacion incompatible' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $f$;
CREATE FUNCTION public.sps_guard_espera_truncate() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 IF EXISTS(SELECT 1 FROM public.convocatoria WHERE espera_registrada_en IS NOT NULL) THEN
  RAISE EXCEPTION 'ADMISION: no truncar solicitudes historicas' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $f$;
CREATE TRIGGER sps_convocatoria_admision BEFORE INSERT OR UPDATE OR DELETE ON public.convocatoria
 FOR EACH ROW EXECUTE FUNCTION public.sps_guard_admision();
CREATE TRIGGER sps_evento_admision BEFORE UPDATE OR DELETE ON public.evento_auditoria
 FOR EACH ROW EXECUTE FUNCTION public.sps_guard_admision();
CREATE TRIGGER sps_espera_truncate BEFORE TRUNCATE ON public.convocatoria
 FOR EACH STATEMENT EXECUTE FUNCTION public.sps_guard_espera_truncate();
"""


def upgrade():
    if op.get_bind().dialect.name!='postgresql':raise RuntimeError('Admisión requiere PostgreSQL.')
    op.add_column('convocatoria',sa.Column('espera_registrada_en',sa.DateTime(timezone=True),nullable=True))
    op.add_column('convocatoria',sa.Column('espera_version_caso_id',sa.Uuid(),nullable=True))
    op.add_column('convocatoria',sa.Column('admision_evento_id',sa.Uuid(),nullable=True))
    op.create_unique_constraint('uq_evento_id_sesion_admision','evento_auditoria',['id','sesion_id'])
    op.create_foreign_key('fk_espera_sesion_version','convocatoria','sesion_programada',
        ['sesion_id','espera_version_caso_id'],['id','version_caso_id'])
    op.create_foreign_key('fk_admision_evento_sesion','convocatoria','evento_auditoria',
        ['admision_evento_id','sesion_id'],['id','sesion_id'])
    op.create_check_constraint('ck_espera_pareja','convocatoria',
        '(espera_registrada_en IS NULL) = (espera_version_caso_id IS NULL)')
    op.create_check_constraint('ck_admision_espera','convocatoria',
        'admision_evento_id IS NULL OR espera_registrada_en IS NOT NULL')
    op.execute(SQL)


def downgrade():
    if op.get_bind().dialect.name!='postgresql':raise RuntimeError('Admisión requiere PostgreSQL.')
    op.execute('LOCK TABLE public.convocatoria,public.evento_auditoria IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().scalar(sa.text('SELECT 1 FROM public.convocatoria WHERE espera_registrada_en IS NOT NULL OR admision_evento_id IS NOT NULL LIMIT 1')):
        raise RuntimeError('No eliminar evidencia de espera/admisión existente.')
    op.execute('DROP TRIGGER sps_espera_truncate ON public.convocatoria')
    op.execute('DROP TRIGGER sps_evento_admision ON public.evento_auditoria')
    op.execute('DROP TRIGGER sps_convocatoria_admision ON public.convocatoria')
    op.execute('DROP FUNCTION public.sps_guard_espera_truncate()')
    op.execute('DROP FUNCTION public.sps_guard_admision()')
    for n in ('ck_admision_espera','ck_espera_pareja'):op.drop_constraint(n,'convocatoria',type_='check')
    for n in ('fk_admision_evento_sesion','fk_espera_sesion_version'):op.drop_constraint(n,'convocatoria',type_='foreignkey')
    op.drop_constraint('uq_evento_id_sesion_admision','evento_auditoria',type_='unique')
    for n in ('admision_evento_id','espera_version_caso_id','espera_registrada_en'):op.drop_column('convocatoria',n)
