-- EXPERIMENTAL. Ejecutar en UNA transacción sobre esquema actual migrado.
-- No crea tablas/columnas ni reemplaza PK/FK. No integra Alembic productivo.
-- El bloqueo impide escrituras durante auditoría e instalación atómica.
LOCK TABLE public.caso, public.version_caso, public.escenario, public.pregunta,
 public.opcion_respuesta, public.rubrica, public.criterio_rubrica,
 public.nivel_rubrica, public.valoracion_opcion IN SHARE ROW EXCLUSIVE MODE;

DO $audit$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_catalog.pg_constraint c
  JOIN pg_catalog.pg_class r ON r.oid=c.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=r.relnamespace
  WHERE n.nspname='public' AND r.relname IN ('caso','version_caso','escenario','pregunta',
   'opcion_respuesta','rubrica','criterio_rubrica','nivel_rubrica','valoracion_opcion')
   AND c.contype='f' AND NOT c.convalidated) THEN
  RAISE EXCEPTION 'BD204: FK previa sin validar' USING ERRCODE='23514';
 END IF;
 IF EXISTS (SELECT 1 FROM public.version_caso WHERE estado NOT IN ('BORRADOR','PUBLICADO','ARCHIVADO')) THEN
  RAISE EXCEPTION 'BD204: estados legados incompatibles' USING ERRCODE='23514';
 END IF;
 IF EXISTS (
  SELECT 1 FROM public.valoracion_opcion v
  JOIN public.opcion_respuesta o ON o.id=v.opcion_id
  JOIN public.pregunta p ON p.id=o.pregunta_id
  JOIN public.escenario e ON e.id=p.escenario_id
  JOIN public.criterio_rubrica c ON c.id=v.criterio_id
  JOIN public.rubrica r ON r.id=c.rubrica_id
  WHERE e.version_caso_id<>r.version_caso_id
 ) THEN
  RAISE EXCEPTION 'BD204: valoraciones legadas entre versiones; no se reparan automaticamente' USING ERRCODE='23514';
 END IF;
END
$audit$;

CREATE FUNCTION public.bd204_version(tabla text, fila jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE v uuid;
BEGIN
 CASE tabla
 WHEN 'escenario' THEN v:=(fila->>'version_caso_id')::uuid;
 WHEN 'pregunta' THEN SELECT version_caso_id INTO v FROM public.escenario WHERE id=(fila->>'escenario_id')::uuid;
 WHEN 'opcion_respuesta' THEN
  SELECT e.version_caso_id INTO v FROM public.pregunta p JOIN public.escenario e ON e.id=p.escenario_id WHERE p.id=(fila->>'pregunta_id')::uuid;
 WHEN 'rubrica' THEN v:=(fila->>'version_caso_id')::uuid;
 WHEN 'criterio_rubrica' THEN SELECT version_caso_id INTO v FROM public.rubrica WHERE id=(fila->>'rubrica_id')::uuid;
 WHEN 'nivel_rubrica' THEN
  SELECT r.version_caso_id INTO v FROM public.criterio_rubrica c JOIN public.rubrica r ON r.id=c.rubrica_id WHERE c.id=(fila->>'criterio_id')::uuid;
 WHEN 'valoracion_opcion' THEN
  SELECT e.version_caso_id INTO v FROM public.opcion_respuesta o JOIN public.pregunta p ON p.id=o.pregunta_id
   JOIN public.escenario e ON e.id=p.escenario_id WHERE o.id=(fila->>'opcion_id')::uuid;
 ELSE RAISE EXCEPTION 'BD204: tabla no admitida' USING ERRCODE='23514';
 END CASE;
 RETURN v;
END
$f$;

CREATE FUNCTION public.bd204_borrador(v uuid, cascada boolean) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE estado_actual text;
BEGIN
 IF v IS NULL THEN
  IF cascada THEN RETURN; END IF;
  RAISE EXCEPTION 'BD204: padre no encontrado' USING ERRCODE='23503';
 END IF;
 -- La comprobación usa el estado de la fila bloqueada, no una lectura previa.
 SELECT estado INTO estado_actual FROM public.version_caso WHERE id=v FOR UPDATE;
 IF NOT FOUND THEN
  IF cascada THEN RETURN; END IF;
  RAISE EXCEPTION 'BD204: version no encontrada' USING ERRCODE='23503';
 END IF;
 IF estado_actual<>'BORRADOR' THEN
  RAISE EXCEPTION 'BD204: contenido historico inmutable' USING ERRCODE='23514';
 END IF;
END
$f$;

CREATE FUNCTION public.bd204_guardar_hijo() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE fila jsonb; k text; v uuid; criterio_v uuid;
BEGIN
 IF TG_OP='UPDATE' THEN
  -- La pertenencia estructural y los IDs se mantienen estables. Los escritores
  -- actuales reemplazan borradores mediante DELETE/INSERT, no reparentado.
  FOREACH k IN ARRAY TG_ARGV LOOP
   IF to_jsonb(NEW)->k IS DISTINCT FROM to_jsonb(OLD)->k THEN
    RAISE EXCEPTION 'BD204: identidad o padre inmutable (%)',k USING ERRCODE='23514';
   END IF;
  END LOOP;
 END IF;
 IF TG_OP='DELETE' THEN fila:=to_jsonb(OLD); ELSE fila:=to_jsonb(NEW); END IF;
 v:=public.bd204_version(TG_TABLE_NAME,fila);
 PERFORM public.bd204_borrador(v,TG_OP='DELETE');
 IF TG_TABLE_NAME='valoracion_opcion' AND TG_OP<>'DELETE' THEN
  SELECT r.version_caso_id INTO criterio_v FROM public.criterio_rubrica c
   JOIN public.rubrica r ON r.id=c.rubrica_id WHERE c.id=(fila->>'criterio_id')::uuid;
  IF criterio_v IS NULL THEN
   RAISE EXCEPTION 'BD204: criterio no encontrado' USING ERRCODE='23503';
  END IF;
  IF criterio_v<>v THEN
   RAISE EXCEPTION 'BD204: opcion y criterio de versiones diferentes' USING ERRCODE='23514';
  END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END
$f$;

CREATE FUNCTION public.bd204_guardar_version() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 IF TG_OP='DELETE' THEN
  IF OLD.estado<>'BORRADOR' THEN
   RAISE EXCEPTION 'BD204: no eliminar version historica' USING ERRCODE='23514';
  END IF;
  RETURN OLD;
 END IF;
 -- Coordina INSERT/publicación con eliminación de su familia (no inventa dueño).
 PERFORM 1 FROM public.caso WHERE id=NEW.caso_id FOR KEY SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'BD204: familia inexistente' USING ERRCODE='23503'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.estado<>'BORRADOR' THEN
   RAISE EXCEPTION 'BD204: nueva version debe comenzar BORRADOR' USING ERRCODE='23514';
  END IF;
 ELSE
  IF (NEW.id,NEW.caso_id,NEW.numero) IS DISTINCT FROM (OLD.id,OLD.caso_id,OLD.numero) THEN
   RAISE EXCEPTION 'BD204: identidad de version inmutable' USING ERRCODE='23514';
  END IF;
  IF OLD.estado='BORRADOR' THEN
   IF NEW.estado NOT IN ('BORRADOR','PUBLICADO') THEN
    RAISE EXCEPTION 'BD204: transicion no admitida' USING ERRCODE='23514';
   END IF;
   IF NEW.estado='PUBLICADO' AND (to_jsonb(NEW)-'estado') IS DISTINCT FROM (to_jsonb(OLD)-'estado') THEN
    RAISE EXCEPTION 'BD204: publicar no edita contenido' USING ERRCODE='23514';
   END IF;
  ELSE
   IF NOT (NEW.estado=OLD.estado OR (OLD.estado='PUBLICADO' AND NEW.estado='ARCHIVADO'))
     OR (to_jsonb(NEW)-'estado') IS DISTINCT FROM (to_jsonb(OLD)-'estado') THEN
    RAISE EXCEPTION 'BD204: version historica inmutable' USING ERRCODE='23514';
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END
$f$;

CREATE FUNCTION public.bd204_guardar_caso() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
DECLARE v record;
BEGIN
 IF TG_OP='UPDATE' THEN
  -- Caso contiene identidad, creador y fecha; el contenido editable está en versión.
  IF NEW IS DISTINCT FROM OLD THEN
   RAISE EXCEPTION 'BD204: identidad familiar inmutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 FOR v IN SELECT id,estado FROM public.version_caso WHERE caso_id=OLD.id ORDER BY id FOR UPDATE LOOP
  IF v.estado<>'BORRADOR' THEN
   RAISE EXCEPTION 'BD204: familia con historia no eliminable' USING ERRCODE='23514';
  END IF;
 END LOOP;
 RETURN OLD;
END
$f$;

CREATE FUNCTION public.bd204_no_truncar() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $f$
BEGIN
 RAISE EXCEPTION 'BD204: TRUNCATE no es operacion de Cases' USING ERRCODE='23514';
END
$f$;

CREATE TRIGGER bd204_caso BEFORE UPDATE OR DELETE ON public.caso FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_caso();
CREATE TRIGGER bd204_version BEFORE INSERT OR UPDATE OR DELETE ON public.version_caso FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_version();
CREATE TRIGGER bd204_escenario BEFORE INSERT OR UPDATE OR DELETE ON public.escenario FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('id','version_caso_id');
CREATE TRIGGER bd204_pregunta BEFORE INSERT OR UPDATE OR DELETE ON public.pregunta FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('id','escenario_id');
CREATE TRIGGER bd204_opcion BEFORE INSERT OR UPDATE OR DELETE ON public.opcion_respuesta FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('id','pregunta_id');
CREATE TRIGGER bd204_rubrica BEFORE INSERT OR UPDATE OR DELETE ON public.rubrica FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('id','version_caso_id');
CREATE TRIGGER bd204_criterio BEFORE INSERT OR UPDATE OR DELETE ON public.criterio_rubrica FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('id','rubrica_id');
CREATE TRIGGER bd204_nivel BEFORE INSERT OR UPDATE OR DELETE ON public.nivel_rubrica FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('id','criterio_id');
CREATE TRIGGER bd204_valoracion BEFORE INSERT OR UPDATE OR DELETE ON public.valoracion_opcion FOR EACH ROW EXECUTE FUNCTION public.bd204_guardar_hijo('opcion_id','criterio_id');
DO $trunc$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY['caso','version_caso','escenario','pregunta','opcion_respuesta','rubrica','criterio_rubrica','nivel_rubrica','valoracion_opcion'] LOOP
  EXECUTE format('CREATE TRIGGER bd204_truncar BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.bd204_no_truncar()',t);
 END LOOP;
END
$trunc$;
