"""Detalles exactos PREGUNTAS_100_V1, una cabecera canónica por intento."""
import ast
from pathlib import Path
import re
from alembic import op
import sqlalchemy as sa

revision='20261107_question_results'
down_revision='20261106_consent_versions'
branch_labels=None
depends_on=None


def funciones_anteriores():
    # Lee exclusivamente el SQL literal de la revisión versionada inmutable.
    # No ejecuta código recibido de PostgreSQL ni modifica esa revisión.
    tree=ast.parse(Path(__file__).with_name('20261102_evaluation_results.py').read_text('utf-8'))
    sql=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SQL' for t in n.targets))
    return [re.search(r'CREATE FUNCTION public\.'+name+r'\(\).*?END \$f\$;',sql,re.S).group().replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1)
            for name in ('f8c_cabecera','f8c_completo')]


SQL=r"""
CREATE FUNCTION public.fp8_longitud(vid uuid) RETURNS integer
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE inicial uuid; estado jsonb='{}'; eid uuid; qid uuid; hijo integer; largo integer; arista record; listo boolean; cambio boolean; maximo integer;
BEGIN
 IF (SELECT count(*) FROM public.escenario WHERE version_caso_id=vid AND es_inicial)<>1 THEN
  RAISE EXCEPTION 'PREGUNTAS: inicial no inequivoca' USING ERRCODE='23514'; END IF;
 SELECT id INTO inicial FROM public.escenario WHERE version_caso_id=vid AND es_inicial;
 SELECT count(*) INTO maximo FROM public.escenario WHERE version_caso_id=vid;
 FOR iteracion IN 1..maximo LOOP
  cambio=false;
  FOR eid IN WITH RECURSIVE alcanzables(id) AS (
   SELECT inicial UNION SELECT o.escenario_destino_id FROM alcanzables a
   JOIN public.pregunta q ON q.escenario_id=a.id JOIN public.opcion_respuesta o ON o.pregunta_id=q.id
   WHERE o.tipo_transicion='ESCENA' AND o.escenario_destino_id IS NOT NULL)
   SELECT id FROM alcanzables LOOP
   IF estado ? eid::text THEN CONTINUE; END IF;
   IF (SELECT count(*) FROM public.pregunta WHERE escenario_id=eid)<>1 THEN CONTINUE; END IF;
   SELECT id INTO qid FROM public.pregunta WHERE escenario_id=eid;
   listo=true; largo=NULL;
   FOR arista IN SELECT * FROM public.opcion_respuesta WHERE pregunta_id=qid LOOP
    IF arista.tipo_transicion='FIN' AND arista.escenario_destino_id IS NULL THEN hijo=1;
    ELSIF arista.tipo_transicion='ESCENA' AND arista.escenario_destino_id IS NOT NULL
      AND EXISTS(SELECT 1 FROM public.escenario WHERE id=arista.escenario_destino_id AND version_caso_id=vid)
      AND estado ? arista.escenario_destino_id::text THEN hijo=1+(estado->>arista.escenario_destino_id::text)::integer;
    ELSE listo=false; EXIT; END IF;
    IF largo IS NOT NULL AND largo<>hijo THEN
     RAISE EXCEPTION 'PREGUNTAS: rutas desiguales' USING ERRCODE='23514'; END IF;
    largo=hijo;
   END LOOP;
   IF listo AND largo IS NOT NULL THEN estado=jsonb_set(estado,ARRAY[eid::text],to_jsonb(largo)); cambio=true; END IF;
  END LOOP;
  IF estado ? inicial::text THEN RETURN (estado->>inicial::text)::integer; END IF;
  IF NOT cambio THEN EXIT; END IF;
 END LOOP;
 RAISE EXCEPTION 'PREGUNTAS: recorrido incompleto, ciclico o no soportado' USING ERRCODE='23514';
END $f$;

CREATE FUNCTION public.fp8_cabecera(entrada jsonb) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE n public.resultado_intento; ctx record; p integer; j jsonb; d jsonb;
BEGIN
 n=jsonb_populate_record(NULL::public.resultado_intento,entrada);
 IF current_setting('transaction_isolation')<>'read committed' THEN
  RAISE EXCEPTION 'PREGUNTAS: escritor READ COMMITTED requerido' USING ERRCODE='23514'; END IF;
 SELECT id_participacion INTO p FROM public.intento WHERE id_intento=n.id_intento;
 PERFORM 1 FROM public.participacion WHERE id_participacion=p FOR UPDATE;
 PERFORM 1 FROM public.intento WHERE id_intento=n.id_intento FOR UPDATE;
 SELECT i.estado,v.estado AS estado_version,a.version_caso_id,v.caso_id,c.id_caso,r.id rubrica_id,r.version_regla INTO ctx
 FROM public.intento i JOIN public.participacion x USING(id_participacion) JOIN public.asignacion_caso a USING(id_asignacion)
 JOIN public.version_caso v ON v.id=a.version_caso_id JOIN public.caso c ON c.id=v.caso_id
 JOIN public.rubrica r ON r.version_caso_id=v.id WHERE i.id_intento=n.id_intento;
 IF NOT FOUND OR ctx.estado NOT IN ('FINALIZADO','VENCIDO') OR ctx.estado_version NOT IN ('PUBLICADO','ARCHIVADO') OR
 (n.version_caso_id,n.caso_id,n.id_caso,n.rubrica_id,n.version_regla) IS DISTINCT FROM
 (ctx.version_caso_id,ctx.caso_id,ctx.id_caso,ctx.rubrica_id,ctx.version_regla) OR
 n.modalidad IS DISTINCT FROM (CASE WHEN ctx.estado='VENCIDO' THEN 'PARCIAL' ELSE 'COMPLETA' END) THEN
  RAISE EXCEPTION 'PREGUNTAS: contexto historico incompatible' USING ERRCODE='23514'; END IF;
 j=n.procedencia::jsonb; d=(j->>'politica_documento')::jsonb;
 IF n.ambito<>'TECNICO' OR n.politica_id<>'PREGUNTAS_100_V1' OR n.politica_version<>'1'
  OR (j->>'formato') IS DISTINCT FROM 'preguntas-100-v1'
  OR (d->>'id') IS DISTINCT FROM n.politica_id OR (d->>'version') IS DISTINCT FROM n.politica_version
  OR (d->>'formula') IS DISTINCT FROM 'suma_puntajes/total_ruta'
  OR (d->>'redondeo') IS DISTINCT FROM 'ROUND_HALF_UP' OR (d->>'decimales') IS DISTINCT FROM '2'
  OR jsonb_typeof(d->'motor') IS DISTINCT FROM 'object' OR jsonb_typeof(j->'exacto') IS DISTINCT FROM 'object'
  OR (j#>>'{intento,id_intento}')::integer IS DISTINCT FROM n.id_intento
  OR (j#>>'{intento,id_participacion}')::integer IS DISTINCT FROM p
  OR (j#>>'{rubrica,version_id}')::uuid IS DISTINCT FROM n.version_caso_id
  OR (j#>>'{configuracion,grafo,version_id}')::uuid IS DISTINCT FROM n.version_caso_id
  OR (j#>>'{rubrica,rubrica_id}')::uuid IS DISTINCT FROM n.rubrica_id
  OR (j#>>'{rubrica,caso_id}')::uuid IS DISTINCT FROM n.caso_id
  OR (j#>>'{rubrica,id_caso_academico}')::integer IS DISTINCT FROM n.id_caso
  OR (j#>>'{rubrica,version_regla}') IS DISTINCT FROM n.version_regla
  OR (j->>'nota_final')::numeric IS DISTINCT FROM n.nota_final
  OR encode(sha256(convert_to(n.procedencia,'UTF8')),'hex') IS DISTINCT FROM n.procedencia_sha256
  OR encode(sha256(convert_to(j->>'politica_documento','UTF8')),'hex') IS DISTINCT FROM n.politica_hash
  OR (j->>'configuracion_documento')::jsonb IS DISTINCT FROM j->'configuracion' THEN
  RAISE EXCEPTION 'PREGUNTAS: procedencia incompatible' USING ERRCODE='23514'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(n.politica_id||':'||n.politica_version,0));
 IF EXISTS(SELECT 1 FROM public.resultado_intento WHERE politica_id=n.politica_id AND politica_version=n.politica_version AND politica_hash<>n.politica_hash) THEN
  RAISE EXCEPTION 'PREGUNTAS: definicion versionada ya vinculada' USING ERRCODE='23514'; END IF;
 RETURN;
END $f$;

CREATE FUNCTION public.fp8_completo(rid integer) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE r public.resultado_intento; x public.resultado_calculo_preguntas; aporte record; paso record; j jsonb; nc integer; real_suma numeric; an numeric=0; ad numeric=1; actual uuid; esperada uuid; destino uuid; tipo varchar; esperada_nota numeric;
BEGIN
 SELECT * INTO r FROM public.resultado_intento WHERE id_resultado=rid;
 IF r.version_regla IS DISTINCT FROM 'PREGUNTAS_100_V1' OR r.ambito<>'TECNICO' THEN
  RAISE EXCEPTION 'PREGUNTAS: detalle sobre otro motor' USING ERRCODE='23514'; END IF;
 SELECT * INTO x FROM public.resultado_calculo_preguntas WHERE id_resultado=rid;
 IF NOT FOUND THEN RAISE EXCEPTION 'PREGUNTAS: resumen obligatorio' USING ERRCODE='23514'; END IF;
 j=r.procedencia::jsonb;
 SELECT count(*) INTO nc FROM public.criterio_rubrica WHERE rubrica_id=r.rubrica_id;
 -- Todas las alternativas, no solo las respondidas: sin valores faltantes,
 -- puntajes contradictorios ni criterios ajenos en una edición evaluable.
 IF EXISTS(SELECT 1 FROM public.opcion_respuesta op JOIN public.pregunta pr ON pr.id=op.pregunta_id
  JOIN public.escenario es ON es.id=pr.escenario_id WHERE es.version_caso_id=r.version_caso_id AND (
   nc<>(SELECT count(*) FROM public.valoracion_opcion vo JOIN public.criterio_rubrica cr ON cr.id=vo.criterio_id
     WHERE vo.opcion_id=op.id AND cr.rubrica_id=r.rubrica_id AND vo.puntaje>=0 AND vo.puntaje<=100)
   OR 1<>(SELECT count(DISTINCT vo.puntaje) FROM public.valoracion_opcion vo WHERE vo.opcion_id=op.id))) THEN
  RAISE EXCEPTION 'PREGUNTAS: configuracion incompleta o contradictoria' USING ERRCODE='23514'; END IF;
 IF nc=0 OR EXISTS(SELECT 1 FROM public.resultado_criterio WHERE id_resultado=rid)
  OR x.preguntas_exigidas<>public.fp8_longitud(r.version_caso_id)
  OR x.preguntas_respondidas<>(SELECT count(*) FROM public.resultado_pregunta WHERE id_resultado=rid)
  OR x.preguntas_respondidas<>(SELECT count(*) FROM public.paso_simulacion WHERE id_intento=r.id_intento)
  OR nc<>(SELECT count(*) FROM public.resultado_criterio_exacto WHERE id_resultado=rid)
  OR x.preguntas_respondidas IS DISTINCT FROM jsonb_array_length(j#>'{exacto,preguntas}')
  OR nc IS DISTINCT FROM jsonb_array_length(j#>'{exacto,criterios}')
  OR x.suma_puntajes IS DISTINCT FROM (j#>>'{exacto,suma_puntajes}')::numeric
  OR x.preguntas_exigidas IS DISTINCT FROM (j#>>'{exacto,preguntas_exigidas}')::integer
  OR x.preguntas_respondidas IS DISTINCT FROM (j#>>'{exacto,preguntas_respondidas}')::integer
  OR x.preguntas_pendientes IS DISTINCT FROM (j#>>'{exacto,preguntas_pendientes}')::integer
  OR x.configuracion_sha256 IS DISTINCT FROM encode(sha256(convert_to(j->>'configuracion_documento','UTF8')),'hex') THEN
  RAISE EXCEPTION 'PREGUNTAS: detalle incompleto o incoherente' USING ERRCODE='23514'; END IF;
 SELECT coalesce(sum(puntaje),0) INTO real_suma FROM public.resultado_pregunta WHERE id_resultado=rid;
 esperada_nota=(div(real_suma*100,x.preguntas_exigidas)+CASE WHEN 2*mod(real_suma*100,x.preguntas_exigidas)>=x.preguntas_exigidas THEN 1 ELSE 0 END)/100;
 IF real_suma<>x.suma_puntajes OR esperada_nota<>r.nota_final THEN
  RAISE EXCEPTION 'PREGUNTAS: promedio global incorrecto' USING ERRCODE='23514'; END IF;
 SELECT id INTO actual FROM public.escenario WHERE version_caso_id=r.version_caso_id AND es_inicial;
 FOR paso IN SELECT * FROM public.resultado_pregunta WHERE id_resultado=rid ORDER BY numero_paso LOOP
  SELECT id INTO esperada FROM public.pregunta WHERE escenario_id=actual;
  IF paso.pregunta_id IS DISTINCT FROM esperada OR NOT EXISTS(
   SELECT 1 FROM public.paso_simulacion p WHERE p.id_intento=r.id_intento AND p.id_decision=paso.pregunta_id AND p.id_opcion=paso.opcion_id AND p.numero_paso=paso.numero_paso)
   OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(j#>'{exacto,preguntas}') e WHERE
    (e->>'pregunta_id')::uuid=paso.pregunta_id AND (e->>'opcion_id')::uuid=paso.opcion_id AND (e->>'puntaje')::numeric=paso.puntaje AND (e->>'numero_paso')::integer=paso.numero_paso)
   OR nc<>(SELECT count(*) FROM public.valoracion_opcion v JOIN public.criterio_rubrica c ON c.id=v.criterio_id
    WHERE v.opcion_id=paso.opcion_id AND c.rubrica_id=r.rubrica_id AND v.puntaje=paso.puntaje) THEN
   RAISE EXCEPTION 'PREGUNTAS: seleccion o puntaje ajeno' USING ERRCODE='23514'; END IF;
  SELECT o.tipo_transicion,o.escenario_destino_id INTO tipo,destino FROM public.opcion_respuesta o WHERE o.id=paso.opcion_id;
  actual=CASE WHEN tipo='ESCENA' THEN destino ELSE NULL END;
 END LOOP;
 IF r.modalidad='COMPLETA' AND actual IS NOT NULL THEN
  RAISE EXCEPTION 'PREGUNTAS: recorrido no completo' USING ERRCODE='23514'; END IF;
 FOR aporte IN SELECT * FROM public.resultado_criterio_exacto WHERE id_resultado=rid LOOP
  IF aporte.rubrica_id<>r.rubrica_id OR aporte.preguntas_evaluables<>x.preguntas_exigidas OR aporte.suma_puntajes<>real_suma
   OR aporte.numerador*(x.preguntas_exigidas::numeric*nc)<>real_suma*aporte.denominador
   OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(j#>'{exacto,criterios}') e WHERE
    (e->>'criterio_id')::uuid=aporte.criterio_id AND (e->>'suma_puntajes')::numeric=aporte.suma_puntajes
    AND (e->>'preguntas_evaluables')::integer=aporte.preguntas_evaluables AND (e->>'numerador')::numeric=aporte.numerador AND (e->>'denominador')::numeric=aporte.denominador) THEN
   RAISE EXCEPTION 'PREGUNTAS: contribucion no exacta' USING ERRCODE='23514'; END IF;
  an=an*aporte.denominador+aporte.numerador*ad; ad=ad*aporte.denominador;
 END LOOP;
 IF an*x.preguntas_exigidas<>real_suma*ad THEN
  RAISE EXCEPTION 'PREGUNTAS: contribuciones no suman promedio' USING ERRCODE='23514'; END IF;
END $f$;

CREATE FUNCTION public.fp8_detalle() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN PERFORM public.fp8_completo(NEW.id_resultado); RETURN NULL; END $f$;
"""


def upgrade():
    b=op.get_bind()
    if b.dialect.name!='postgresql':raise RuntimeError('Revisión exacta reservada a PostgreSQL aislado.')
    op.drop_constraint('ck_8c_solo_laboratorio','resultado_intento',type_='check')
    op.create_check_constraint('ck_resultado_ambito','resultado_intento',"ambito = 'LABORATORIO' OR (ambito = 'TECNICO' AND version_regla = 'PREGUNTAS_100_V1')")
    # DDL revisado explícitamente, sin autogeneración ni backfill histórico.
    op.create_index('uq_8c_opcion_pregunta','opcion_respuesta',['id','pregunta_id'],unique=True)
    op.create_table('resultado_calculo_preguntas',
        sa.Column('id_resultado',sa.Integer(),sa.ForeignKey('resultado_intento.id_resultado'),primary_key=True),
        sa.Column('suma_puntajes',sa.Numeric(),nullable=False),
        sa.Column('preguntas_exigidas',sa.Integer(),nullable=False),sa.Column('preguntas_respondidas',sa.Integer(),nullable=False),sa.Column('preguntas_pendientes',sa.Integer(),nullable=False),
        sa.Column('configuracion_sha256',sa.String(64),nullable=False),
        sa.CheckConstraint('preguntas_exigidas > 0 AND preguntas_respondidas >= 0 AND preguntas_pendientes >= 0 AND preguntas_respondidas + preguntas_pendientes = preguntas_exigidas',name='ck_rp_cantidades'),
        sa.CheckConstraint('suma_puntajes >= 0 AND suma_puntajes <= 100 * preguntas_exigidas',name='ck_rp_suma'),sa.CheckConstraint('length(configuracion_sha256)=64',name='ck_rp_config_hash'))
    op.create_table('resultado_pregunta',
        sa.Column('id_resultado',sa.Integer(),sa.ForeignKey('resultado_intento.id_resultado'),primary_key=True),
        sa.Column('pregunta_id',sa.Uuid(),sa.ForeignKey('pregunta.id'),primary_key=True),sa.Column('opcion_id',sa.Uuid(),nullable=False),
        sa.Column('puntaje',sa.Numeric(),nullable=False),sa.Column('numero_paso',sa.Integer(),nullable=False),
        sa.ForeignKeyConstraint(['opcion_id','pregunta_id'],['opcion_respuesta.id','opcion_respuesta.pregunta_id'],name='fk_rp_opcion_pregunta'),
        sa.UniqueConstraint('id_resultado','numero_paso',name='uq_rp_numero'),sa.CheckConstraint('puntaje >= 0 AND puntaje <= 100 AND numero_paso > 0',name='ck_rp_puntaje'))
    op.create_table('resultado_criterio_exacto',
        sa.Column('id_resultado',sa.Integer(),primary_key=True),sa.Column('criterio_id',sa.Uuid(),primary_key=True),sa.Column('rubrica_id',sa.Uuid(),nullable=False),
        sa.Column('suma_puntajes',sa.Numeric(),nullable=False),sa.Column('preguntas_evaluables',sa.Integer(),nullable=False),sa.Column('numerador',sa.Numeric(),nullable=False),sa.Column('denominador',sa.Numeric(),nullable=False),
        sa.ForeignKeyConstraint(['id_resultado','rubrica_id'],['resultado_intento.id_resultado','resultado_intento.rubrica_id'],name='fk_rce_resultado'),
        sa.ForeignKeyConstraint(['criterio_id','rubrica_id'],['criterio_rubrica.id','criterio_rubrica.rubrica_id'],name='fk_rce_criterio'),
        sa.CheckConstraint('preguntas_evaluables > 0 AND suma_puntajes >= 0 AND suma_puntajes <= 100 * preguntas_evaluables',name='ck_rce_suma'),
        sa.CheckConstraint("numerador >= 0 AND denominador > 0 AND numerador = round(numerador,0) AND denominador = round(denominador,0) AND numerador NOT IN ('NaN','Infinity','-Infinity') AND denominador NOT IN ('NaN','Infinity','-Infinity')",name='ck_rce_fraccion'))
    b.exec_driver_sql(SQL,execution_options={'no_parameters':True})
    cabecera,completo=funciones_anteriores()
    cabecera=cabecera.replace('BEGIN\n',"BEGIN\n IF NEW.ambito='TECNICO' THEN PERFORM public.fp8_cabecera(to_jsonb(NEW)); RETURN NEW; END IF;\n",1)
    completo=completo.replace('j:=r.procedencia::jsonb;',"IF r.ambito='TECNICO' THEN PERFORM public.fp8_completo(r.id_resultado); RETURN NULL; END IF;\n j:=r.procedencia::jsonb;",1)
    for f in (cabecera,completo):b.exec_driver_sql(f,execution_options={'no_parameters':True})
    for table in ('resultado_calculo_preguntas','resultado_pregunta','resultado_criterio_exacto'):
        b.exec_driver_sql(f'CREATE TRIGGER fp8_historia BEFORE UPDATE OR DELETE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.f8c_inmutable(); CREATE TRIGGER fp8_truncate BEFORE TRUNCATE ON public.{table} FOR EACH STATEMENT EXECUTE FUNCTION public.f8c_inmutable(); CREATE CONSTRAINT TRIGGER fp8_completo AFTER INSERT ON public.{table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fp8_detalle()')


def downgrade():
    b=op.get_bind()
    b.exec_driver_sql('LOCK TABLE resultado_intento,resultado_calculo_preguntas,resultado_pregunta,resultado_criterio_exacto IN ACCESS EXCLUSIVE MODE')
    if b.scalar(sa.text("SELECT 1 FROM resultado_intento WHERE ambito='TECNICO' LIMIT 1")) is not None or any(b.scalar(sa.text('SELECT 1 FROM '+t+' LIMIT 1')) is not None for t in ('resultado_calculo_preguntas','resultado_pregunta','resultado_criterio_exacto')):
        raise RuntimeError('Downgrade rechazado: existen resultados historicos por preguntas.')
    for f in funciones_anteriores():b.exec_driver_sql(f,execution_options={'no_parameters':True})
    op.drop_constraint('ck_resultado_ambito','resultado_intento',type_='check')
    op.create_check_constraint('ck_8c_solo_laboratorio','resultado_intento',"ambito = 'LABORATORIO'")
    for table in ('resultado_criterio_exacto','resultado_pregunta','resultado_calculo_preguntas'):op.drop_table(table)
    for f in ('fp8_detalle()','fp8_completo(integer)','fp8_cabecera(jsonb)','fp8_longitud(uuid)'):b.exec_driver_sql('DROP FUNCTION public.'+f)
    op.drop_index('uq_8c_opcion_pregunta',table_name='opcion_respuesta')
