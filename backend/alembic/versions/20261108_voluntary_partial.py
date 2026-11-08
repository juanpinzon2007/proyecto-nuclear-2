"""Política técnica v2 para FINALIZADO sin FIN; conserva resultados v1."""
import importlib.util
from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision = '20261108_voluntary_partial'
down_revision = '20261108_academic_publication'
branch_labels = None
depends_on = None

# Definición congelada de la migración, independiente del código de aplicación.
POLITICA = '{"id":"CIERRE_VOLUNTARIO_PARCIAL_V1","origen":"PROPUESTA_TECNICA_EQUIPO","condicion":"FINALIZADO_SIN_FIN","denominador":"TOTAL_UNIFORME_RUTAS_COMPLETAS","pendientes":"CERO_POR_CANTIDAD_SIN_SELECCIONES","ramas":"INACCESIBLES_EXCLUIDAS"}'


def originales():
    path=Path(__file__).with_name('20261107_question_results.py')
    spec=importlib.util.spec_from_file_location('preguntas_guard_original',path)
    modulo=importlib.util.module_from_spec(spec);spec.loader.exec_module(modulo)
    funciones=[]
    for nombre in ('fp8_cabecera','fp8_completo'):
        inicio=modulo.SQL.index('CREATE FUNCTION public.'+nombre+'(')
        fin=modulo.SQL.index('END $f$;',inicio)+len('END $f$;')
        funciones.append(modulo.SQL[inicio:fin].replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1))
    return funciones


def modificadas():
    cabecera,completo=originales()
    antes="n.modalidad IS DISTINCT FROM (CASE WHEN ctx.estado='VENCIDO' THEN 'PARCIAL' ELSE 'COMPLETA' END)"
    despues="(ctx.estado='VENCIDO' AND n.modalidad IS DISTINCT FROM 'PARCIAL') OR (ctx.estado='FINALIZADO' AND n.modalidad NOT IN ('COMPLETA','PARCIAL'))"
    assert cabecera.count(antes)==1
    cabecera=cabecera.replace(antes,despues).replace("n.politica_version<>'1'", "n.politica_version NOT IN ('1','2')")
    antes=' PERFORM pg_advisory_xact_lock'
    assert cabecera.count(antes)==1
    control=""" IF n.politica_version='2' THEN
  IF ctx.estado<>'FINALIZADO' OR n.modalidad<>'PARCIAL'
   OR d->'cierre_voluntario' IS DISTINCT FROM '%s'::jsonb
   OR jsonb_typeof(d->'clasificacion') IS DISTINCT FROM 'string' THEN
   RAISE EXCEPTION 'PREGUNTAS: politica voluntaria incompatible' USING ERRCODE='23514'; END IF;
 ELSIF ctx.estado='FINALIZADO' AND n.modalidad<>'COMPLETA' THEN
  RAISE EXCEPTION 'PREGUNTAS: clasificacion v1 incompatible' USING ERRCODE='23514';
 END IF;
""" % POLITICA
    cabecera=cabecera.replace(antes,control+antes)
    antes=" IF r.modalidad='COMPLETA' AND actual IS NOT NULL THEN"
    assert completo.count(antes)==1
    control=""" IF r.politica_version='2' AND (actual IS NULL OR x.preguntas_respondidas>=x.preguntas_exigidas) THEN
  RAISE EXCEPTION 'PREGUNTAS: parcial voluntario requiere prefijo incompleto' USING ERRCODE='23514'; END IF;
"""
    completo=completo.replace(antes,control+antes)
    return cabecera,completo


def upgrade():
    b=op.get_bind()
    b.exec_driver_sql('LOCK TABLE resultado_intento,resultado_calculo_preguntas,resultado_pregunta,resultado_criterio_exacto IN ACCESS EXCLUSIVE MODE')
    for sql in modificadas():b.exec_driver_sql(sql,execution_options={'no_parameters':True})


def downgrade():
    b=op.get_bind()
    b.exec_driver_sql('LOCK TABLE resultado_intento,resultado_calculo_preguntas,resultado_pregunta,resultado_criterio_exacto IN ACCESS EXCLUSIVE MODE')
    if b.scalar(sa.text("SELECT 1 FROM resultado_intento WHERE ambito='TECNICO' AND politica_id='PREGUNTAS_100_V1' AND politica_version='2' LIMIT 1")) is not None:
        raise RuntimeError('Downgrade rechazado: existen resultados historicos de cierre voluntario v2.')
    for sql in originales():b.exec_driver_sql(sql,execution_options={'no_parameters':True})
