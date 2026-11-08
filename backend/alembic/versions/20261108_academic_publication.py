"""Ausencias explícitas y publicación oficial versionada; sin recalificar historia."""
from alembic import op
import sqlalchemy as sa
revision='20261108_academic_publication'
down_revision='20261107_question_results'
branch_labels=None
depends_on=None

SQL=r"""
CREATE FUNCTION aa_permiso_uso() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE capacidad integer; propietario integer;
BEGIN
 IF NEW.id_permiso_extra IS NULL THEN RETURN NEW;END IF;
 PERFORM 1 FROM public.participacion WHERE id_participacion=NEW.id_participacion FOR UPDATE;
 SELECT cantidad_autorizada,id_participacion INTO capacidad,propietario FROM public.permiso_intento_extra WHERE id_permiso_extra=NEW.id_permiso_extra FOR UPDATE;
 IF capacidad IS NULL OR propietario<>NEW.id_participacion OR capacidad<=0 OR
 (SELECT count(*) FROM public.intento WHERE id_permiso_extra=NEW.id_permiso_extra)>=capacidad THEN
 RAISE EXCEPTION 'Permiso de repeticion inexistente, ajeno o consumido' USING ERRCODE='23514';END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION aa_validar() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE previo public.ausencia_academica; v uuid;
BEGIN
 PERFORM 1 FROM public.convocatoria WHERE id=NEW.convocatoria_id FOR UPDATE;
 SELECT * INTO previo FROM public.ausencia_academica WHERE convocatoria_id=NEW.convocatoria_id ORDER BY revision DESC LIMIT 1;
 IF NEW.revision<>COALESCE(previo.revision,0)+1 OR NEW.anterior_id IS DISTINCT FROM previo.id
 OR (previo.id IS NULL AND NOT NEW.confirmada) OR (previo.id IS NOT NULL AND previo.confirmada=NEW.confirmada) THEN
 RAISE EXCEPTION 'Ausencia: secuencia inconsistente' USING ERRCODE='23514';END IF;
 SELECT s.version_caso_id INTO v FROM public.convocatoria c JOIN public.sesion_programada s ON s.id=c.sesion_id
 WHERE c.id=NEW.convocatoria_id AND c.estado='ACTIVA' AND s.id=NEW.sesion_id AND s.estado='FINALIZADO';
 IF v IS NULL OR v<>NEW.version_caso_id OR NOT EXISTS(SELECT 1 FROM public.identidad_academica ia
 WHERE ia.id_usuario=NEW.id_estudiante AND ia.sistema='SCHEDULING' AND ia.id_academico=(SELECT estudiante_id FROM public.convocatoria WHERE id=NEW.convocatoria_id))
 OR EXISTS(SELECT 1 FROM public.participacion p JOIN public.intento i USING(id_participacion) WHERE p.convocatoria_id=NEW.convocatoria_id) THEN
 RAISE EXCEPTION 'Ausencia: contexto o evidencia incompatibles' USING ERRCODE='23514';END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION pe_completa(pid uuid) RETURNS void LANGUAGE plpgsql AS $$
DECLARE h public.publicacion_evaluacion; f record; n int; maximo numeric;
BEGIN
 SELECT * INTO h FROM public.publicacion_evaluacion WHERE id=pid;
 IF NOT FOUND THEN RETURN;END IF;
 IF encode(sha256(convert_to(h.fuente_documento,'UTF8')),'hex')<>h.fuente_sha256
 OR (SELECT estado FROM public.sesion_programada WHERE id=h.sesion_id)<>'FINALIZADO' THEN
 RAISE EXCEPTION 'Publicacion: fuente o cierre inválido' USING ERRCODE='23514';END IF;
 SELECT count(*) INTO n FROM public.convocatoria WHERE sesion_id=h.sesion_id AND estado='ACTIVA';
 IF n=0 OR n<>(SELECT count(*) FROM public.resultado_participacion WHERE publicacion_id=pid) THEN
 RAISE EXCEPTION 'Publicacion: padron incompleto' USING ERRCODE='23514';END IF;
 IF jsonb_array_length(h.fuente_documento::jsonb->'filas')<>n
 OR (SELECT count(*) FROM public.notificacion WHERE publicacion_evaluacion_id=pid)<>n OR NOT EXISTS(
 SELECT 1 FROM public.evento_auditoria WHERE sesion_id=h.sesion_id AND tipo='RESULTADOS_PUBLICADOS'
 AND (CASE WHEN tipo='RESULTADOS_PUBLICADOS' THEN descripcion::jsonb ELSE NULL END)->>'publicacion_id'=pid::text) THEN
 RAISE EXCEPTION 'Publicacion: snapshot o auditoria incompletos' USING ERRCODE='23514';END IF;
 FOR f IN SELECT x.*,c.sesion_id,c.estado estado_conv,c.estudiante_id uuid_estudiante,a.sesion_programada_id,a.version_caso_id
 FROM public.resultado_participacion x JOIN public.convocatoria c ON c.id=x.convocatoria_id
 JOIN public.asignacion_caso a ON a.id_asignacion=x.id_asignacion WHERE x.publicacion_id=pid LOOP
 IF f.sesion_id<>h.sesion_id OR f.sesion_programada_id<>h.sesion_id OR f.estado_conv<>'ACTIVA'
 OR f.version_caso_id<>(SELECT version_caso_id FROM public.sesion_programada WHERE id=h.sesion_id)
 OR NOT EXISTS(SELECT 1 FROM public.identidad_academica WHERE id_usuario=f.id_estudiante AND sistema='SCHEDULING' AND id_academico=f.uuid_estudiante) THEN
 RAISE EXCEPTION 'Publicacion: referencias cruzadas' USING ERRCODE='23514';END IF;
 IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(h.fuente_documento::jsonb->'filas') d
 WHERE d->>'convocatoria_id'=f.convocatoria_id::text AND d=f.detalle::jsonb
 AND d->>'situacion'=f.situacion AND (d->>'nota')::numeric=f.nota_definitiva AND (d->>'id_estudiante')::integer=f.id_estudiante
 AND (d->>'id_asignacion')::integer=f.id_asignacion
 AND (d->>'id_participacion')::integer IS NOT DISTINCT FROM f.id_participacion
 AND (d->>'id_resultado_intento')::integer IS NOT DISTINCT FROM f.id_resultado_intento
 AND (d->>'id_ausencia')::uuid IS NOT DISTINCT FROM f.id_ausencia)
 OR NOT EXISTS(SELECT 1 FROM public.notificacion WHERE publicacion_evaluacion_id=pid AND convocatoria_id=f.convocatoria_id
 AND destinatario_id=f.uuid_estudiante AND tipo='CALIFICACION' AND canal='INTERNA') THEN
 RAISE EXCEPTION 'Publicacion: snapshot o aviso incoherentes' USING ERRCODE='23514';END IF;
 IF f.situacion='AUSENTE' THEN
 IF NOT EXISTS(SELECT 1 FROM public.ausencia_academica a WHERE a.id=f.id_ausencia AND a.convocatoria_id=f.convocatoria_id AND a.confirmada
 AND a.id=(SELECT id FROM public.ausencia_academica WHERE convocatoria_id=f.convocatoria_id ORDER BY revision DESC LIMIT 1))
 OR EXISTS(SELECT 1 FROM public.participacion p JOIN public.intento i USING(id_participacion) WHERE p.convocatoria_id=f.convocatoria_id) THEN
 RAISE EXCEPTION 'Publicacion: ausencia sin confirmacion' USING ERRCODE='23514';END IF;
 ELSE
 IF NOT EXISTS(SELECT 1 FROM public.participacion p WHERE p.id_participacion=f.id_participacion AND p.convocatoria_id=f.convocatoria_id AND p.id_asignacion=f.id_asignacion)
 OR NOT EXISTS(SELECT 1 FROM public.resultado_intento r JOIN public.intento i USING(id_intento) WHERE r.id_resultado=f.id_resultado_intento AND i.id_participacion=f.id_participacion
 AND r.ambito='TECNICO' AND r.version_regla='PREGUNTAS_100_V1' AND r.nota_final=f.nota_definitiva AND r.modalidad=f.situacion)
 OR EXISTS(SELECT 1 FROM public.intento i LEFT JOIN public.resultado_intento r USING(id_intento) WHERE i.id_participacion=f.id_participacion
 AND (i.estado NOT IN ('FINALIZADO','VENCIDO') OR r.id_resultado IS NULL OR r.ambito<>'TECNICO' OR r.version_regla<>'PREGUNTAS_100_V1')) THEN
 RAISE EXCEPTION 'Publicacion: intentos pendientes o incompatibles' USING ERRCODE='23514';END IF;
 IF EXISTS(SELECT 1 FROM public.intento i JOIN public.participacion p USING(id_participacion)
 JOIN public.asignacion_caso a USING(id_asignacion) LEFT JOIN public.permiso_intento_extra e ON e.id_permiso_extra=i.id_permiso_extra
 WHERE i.id_participacion=f.id_participacion AND i.numero_intento>1
 AND (e.id_permiso_extra IS NULL OR e.id_participacion<>p.id_participacion OR e.id_profesor<>h.id_profesor
 OR e.cantidad_autorizada<>1 OR (SELECT count(*) FROM public.intento j WHERE j.id_permiso_extra=e.id_permiso_extra)<>1)) THEN
 RAISE EXCEPTION 'Publicacion: repeticion no autorizada' USING ERRCODE='23514';END IF;
 SELECT max(r.nota_final) INTO maximo FROM public.resultado_intento r JOIN public.intento i USING(id_intento) WHERE i.id_participacion=f.id_participacion;
 IF maximo IS DISTINCT FROM f.nota_definitiva THEN RAISE EXCEPTION 'Publicacion: no conserva mejor nota' USING ERRCODE='23514';END IF;
 END IF;
 END LOOP;
END $$;
CREATE FUNCTION pe_comprobar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='publicacion_evaluacion' THEN PERFORM public.pe_completa(NEW.id);
 ELSE PERFORM public.pe_completa(NEW.publicacion_id);END IF;
 RETURN NULL;
END $$;
"""


def upgrade():
    op.create_table('ausencia_academica',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('convocatoria_id',sa.Uuid(),sa.ForeignKey('convocatoria.id'),nullable=False),
        sa.Column('sesion_id',sa.Uuid(),sa.ForeignKey('sesion_programada.id'),nullable=False),
        sa.Column('id_estudiante',sa.Integer(),sa.ForeignKey('usuario.id_usuario'),nullable=False),
        sa.Column('id_profesor',sa.Integer(),sa.ForeignKey('usuario.id_usuario'),nullable=False),
        sa.Column('version_caso_id',sa.Uuid(),sa.ForeignKey('version_caso.id'),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False),sa.Column('confirmada',sa.Boolean(),nullable=False),
        sa.Column('anterior_id',sa.Uuid(),sa.ForeignKey('ausencia_academica.id')),sa.Column('motivo',sa.Text(),nullable=False),
        sa.Column('fecha',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('convocatoria_id','revision',name='uq_aa_revision'),
        sa.CheckConstraint('revision>0 AND length(trim(motivo))>0',name='ck_aa_datos'))
    op.create_table('publicacion_evaluacion',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('sesion_id',sa.Uuid(),sa.ForeignKey('sesion_programada.id'),nullable=False),
        sa.Column('id_profesor',sa.Integer(),sa.ForeignKey('usuario.id_usuario'),nullable=False),
        sa.Column('version',sa.Integer(),nullable=False),sa.Column('fecha',sa.DateTime(timezone=True),nullable=False),
        sa.Column('fuente_documento',sa.Text(),nullable=False),sa.Column('fuente_sha256',sa.String(64),nullable=False),
        sa.UniqueConstraint('sesion_id','version',name='uq_pe_version'),sa.CheckConstraint('version>0 AND length(fuente_sha256)=64',name='ck_pe_datos'))
    op.create_table('resultado_participacion',sa.Column('id_resultado_participacion',sa.Integer(),primary_key=True),
        sa.Column('publicacion_id',sa.Uuid(),sa.ForeignKey('publicacion_evaluacion.id'),nullable=False),
        sa.Column('convocatoria_id',sa.Uuid(),sa.ForeignKey('convocatoria.id'),nullable=False),
        sa.Column('id_participacion',sa.Integer(),sa.ForeignKey('participacion.id_participacion')),
        sa.Column('id_estudiante',sa.Integer(),sa.ForeignKey('usuario.id_usuario'),nullable=False),
        sa.Column('id_asignacion',sa.Integer(),sa.ForeignKey('asignacion_caso.id_asignacion'),nullable=False),
        sa.Column('id_resultado_intento',sa.Integer(),sa.ForeignKey('resultado_intento.id_resultado')),
        sa.Column('id_ausencia',sa.Uuid(),sa.ForeignKey('ausencia_academica.id')),
        sa.Column('situacion',sa.String(20),nullable=False),sa.Column('nota_definitiva',sa.Numeric(5,2),nullable=False),sa.Column('detalle',sa.Text(),nullable=False),
        sa.UniqueConstraint('publicacion_id','convocatoria_id',name='uq_rp_publicacion_convocatoria'),
        sa.CheckConstraint("nota_definitiva>=0 AND nota_definitiva<=100 AND situacion IN ('COMPLETA','PARCIAL','AUSENTE')",name='ck_rp_oficial_nota'),
        sa.CheckConstraint("(situacion='AUSENTE' AND id_ausencia IS NOT NULL AND id_resultado_intento IS NULL AND nota_definitiva=0) OR (situacion IN ('COMPLETA','PARCIAL') AND id_ausencia IS NULL AND id_resultado_intento IS NOT NULL AND id_participacion IS NOT NULL)",name='ck_rp_oficial_origen'))
    op.add_column('sesion_programada',sa.Column('mostrar_resultados_provisionales',sa.Boolean()))
    op.add_column('sesion_programada',sa.Column('visibilidad_docente_id',sa.Integer(),sa.ForeignKey('usuario.id_usuario')))
    op.add_column('sesion_programada',sa.Column('visibilidad_actualizada_en',sa.DateTime(timezone=True)))
    op.create_check_constraint('ck_sesion_visibilidad','sesion_programada',"(mostrar_resultados_provisionales IS NULL AND visibilidad_docente_id IS NULL AND visibilidad_actualizada_en IS NULL) OR (mostrar_resultados_provisionales IS NOT NULL AND visibilidad_docente_id IS NOT NULL AND visibilidad_actualizada_en IS NOT NULL)")
    op.add_column('notificacion',sa.Column('publicacion_evaluacion_id',sa.Uuid(),sa.ForeignKey('publicacion_evaluacion.id')))
    op.create_unique_constraint('uq_notificacion_publicacion','notificacion',['publicacion_evaluacion_id','convocatoria_id'])
    op.create_check_constraint('ck_aviso_publicacion','notificacion',"publicacion_evaluacion_id IS NULL OR (tipo='CALIFICACION' AND canal='INTERNA' AND convocatoria_id IS NOT NULL)")
    op.execute(SQL)
    op.execute('CREATE TRIGGER aa_permiso_uso BEFORE INSERT ON intento FOR EACH ROW EXECUTE FUNCTION aa_permiso_uso()')
    op.execute('CREATE TRIGGER aa_contexto BEFORE INSERT ON ausencia_academica FOR EACH ROW EXECUTE FUNCTION aa_validar()')
    for t in ('ausencia_academica','publicacion_evaluacion','resultado_participacion'):
        op.execute(f'CREATE TRIGGER {t}_inmutable BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION f8c_inmutable()')
        op.execute(f'CREATE TRIGGER {t}_no_truncate BEFORE TRUNCATE ON {t} FOR EACH STATEMENT EXECUTE FUNCTION f8c_inmutable()')
    for t in ('publicacion_evaluacion','resultado_participacion'):
        op.execute(f'CREATE CONSTRAINT TRIGGER {t}_completo AFTER INSERT ON {t} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pe_comprobar()')


def downgrade():
    c=op.get_bind()
    c.exec_driver_sql('LOCK TABLE ausencia_academica,publicacion_evaluacion,resultado_participacion,notificacion,sesion_programada IN ACCESS EXCLUSIVE MODE')
    if any(c.scalar(sa.text(f'SELECT EXISTS(SELECT 1 FROM {t})')) for t in ('ausencia_academica','publicacion_evaluacion','resultado_participacion')) or c.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM sesion_programada WHERE mostrar_resultados_provisionales IS NOT NULL)')):
        raise RuntimeError('Downgrade rechazado: conservar historia académica/configuración; no se elimina.')
    op.execute('DROP TRIGGER aa_permiso_uso ON intento');op.execute('DROP FUNCTION aa_permiso_uso()')
    op.drop_constraint('ck_aviso_publicacion','notificacion',type_='check');op.drop_constraint('uq_notificacion_publicacion','notificacion',type_='unique')
    op.drop_column('notificacion','publicacion_evaluacion_id')
    op.drop_constraint('ck_sesion_visibilidad','sesion_programada',type_='check')
    for col in ('visibilidad_actualizada_en','visibilidad_docente_id','mostrar_resultados_provisionales'):op.drop_column('sesion_programada',col)
    op.drop_table('resultado_participacion');op.drop_table('publicacion_evaluacion');op.drop_table('ausencia_academica')
    op.execute('DROP FUNCTION pe_comprobar()');op.execute('DROP FUNCTION pe_completa(uuid)');op.execute('DROP FUNCTION aa_validar()')
