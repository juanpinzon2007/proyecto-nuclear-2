"""Soporte productivo para evaluación ponderada con criterios y niveles (ambito='RUBRICA_V1', RF-13/RF-17).

Conserva intactas todas las validaciones históricas de 'LABORATORIO' y 'TECNICO'.

Revision ID: 20261116_rubric_v1_support
Revises: 20261116_complete_27rf_support
Create Date: 2026-11-16 16:00:00.000000
"""

from alembic import op


revision = "20261116_rubric_v1_support"
down_revision = "20261116_complete_27rf_support"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("La migración 20261116_rubric_v1_support requiere PostgreSQL.")

    op.drop_constraint("ck_resultado_ambito", "resultado_intento", type_="check")
    op.create_check_constraint(
        "ck_resultado_ambito",
        "resultado_intento",
        "ambito = 'LABORATORIO' OR (ambito = 'TECNICO' AND version_regla = 'PREGUNTAS_100_V1') "
        "OR (ambito = 'RUBRICA_V1' AND version_regla IN ('RUBRICA_V1', 'PREGUNTAS_100_V1'))",
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.f8c_cabecera()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        DECLARE p integer; contexto record; j jsonb; d jsonb; contexto_estado text;
        BEGIN
         IF NEW.ambito='TECNICO' THEN PERFORM public.fp8_cabecera(to_jsonb(NEW)); RETURN NEW; END IF;
         IF NEW.ambito='RUBRICA_V1' THEN
          IF current_setting('transaction_isolation') <> 'read committed' THEN
           RAISE EXCEPTION '8C: escritor requiere READ COMMITTED' USING ERRCODE='40001';
          END IF;
          SELECT i.estado INTO contexto_estado FROM public.intento i WHERE i.id_intento=NEW.id_intento;
          IF NOT FOUND OR contexto_estado NOT IN ('FINALIZADO','VENCIDO') THEN
           RAISE EXCEPTION '8C: intento cerrado requerido' USING ERRCODE='23514';
          END IF;
          IF encode(sha256(convert_to(NEW.procedencia,'UTF8')),'hex') IS DISTINCT FROM NEW.procedencia_sha256 THEN
           RAISE EXCEPTION '8C: huella de procedencia invalida' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
         END IF;
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
         PERFORM pg_advisory_xact_lock(hashtextextended(NEW.politica_id||':'||NEW.politica_version,0));
         IF EXISTS(SELECT 1 FROM public.resultado_intento WHERE politica_id=NEW.politica_id
          AND politica_version=NEW.politica_version AND politica_hash<>NEW.politica_hash) THEN
          RAISE EXCEPTION '8C: definicion de politica ya vinculada a otra huella' USING ERRCODE='23514';
         END IF;
         RETURN NEW;
        END $function$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.f8c_completo()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        DECLARE r public.resultado_intento; n integer; j jsonb;
        BEGIN
         SELECT * INTO r FROM public.resultado_intento WHERE id_resultado=NEW.id_resultado;
         IF r.ambito='TECNICO' THEN PERFORM public.fp8_completo(r.id_resultado); RETURN NULL; END IF;
         SELECT count(*) INTO n FROM public.criterio_rubrica WHERE rubrica_id=r.rubrica_id;
         IF r.ambito='RUBRICA_V1' THEN
          IF n=0 OR n<>(SELECT count(*) FROM public.resultado_criterio WHERE id_resultado=r.id_resultado) THEN
           RAISE EXCEPTION '8C: detalle incompleto' USING ERRCODE='23514';
          END IF;
          RETURN NULL;
         END IF;
         j:=r.procedencia::jsonb;
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
        END $function$;
        """
    )


def downgrade():
    op.drop_constraint("ck_resultado_ambito", "resultado_intento", type_="check")
    op.create_check_constraint(
        "ck_resultado_ambito",
        "resultado_intento",
        "ambito = 'LABORATORIO' OR (ambito = 'TECNICO' AND version_regla = 'PREGUNTAS_100_V1')",
    )

