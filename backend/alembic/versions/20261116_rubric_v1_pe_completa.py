"""Extiende pe_completa para aceptar resultados ponderados ambito='RUBRICA_V1' al publicar actas oficiales.

Revision ID: 20261116_rubric_v1_pe_completa
Revises: 20261116_rubric_v1_support
Create Date: 2026-11-16 16:30:00.000000
"""

from alembic import op


revision = "20261116_rubric_v1_pe_completa"
down_revision = "20261116_rubric_v1_support"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("La migración 20261116_rubric_v1_pe_completa requiere PostgreSQL.")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.pe_completa(pid uuid)
        RETURNS void
        LANGUAGE plpgsql
        AS $function$
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
         AND ((r.ambito='TECNICO' AND r.version_regla='PREGUNTAS_100_V1') OR (r.ambito='RUBRICA_V1' AND r.version_regla IN ('RUBRICA_V1','PREGUNTAS_100_V1')))
         AND r.nota_final=f.nota_definitiva AND r.modalidad=f.situacion)
         OR EXISTS(SELECT 1 FROM public.intento i LEFT JOIN public.resultado_intento r USING(id_intento) WHERE i.id_participacion=f.id_participacion
         AND (i.estado NOT IN ('FINALIZADO','VENCIDO') OR r.id_resultado IS NULL
         OR NOT ((r.ambito='TECNICO' AND r.version_regla='PREGUNTAS_100_V1') OR (r.ambito='RUBRICA_V1' AND r.version_regla IN ('RUBRICA_V1','PREGUNTAS_100_V1'))))) THEN
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
        END $function$;
        """
    )


def downgrade():
    pass

