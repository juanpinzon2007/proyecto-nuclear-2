-- EXPERIMENTAL: solo retira objetos bd204_, no borra tablas ni datos.
LOCK TABLE public.caso, public.version_caso, public.escenario, public.pregunta,
 public.opcion_respuesta, public.rubrica, public.criterio_rubrica,
 public.nivel_rubrica, public.valoracion_opcion IN SHARE ROW EXCLUSIVE MODE;
DO $drop_triggers$
DECLARE t text; nombre text;
BEGIN
 FOREACH t IN ARRAY ARRAY['caso','version_caso','escenario','pregunta','opcion_respuesta','rubrica','criterio_rubrica','nivel_rubrica','valoracion_opcion'] LOOP
  nombre:=CASE t WHEN 'version_caso' THEN 'version' WHEN 'opcion_respuesta' THEN 'opcion'
    WHEN 'criterio_rubrica' THEN 'criterio' WHEN 'nivel_rubrica' THEN 'nivel'
    WHEN 'valoracion_opcion' THEN 'valoracion' ELSE t END;
  EXECUTE format('DROP TRIGGER %I ON public.%I','bd204_'||nombre,t);
  EXECUTE format('DROP TRIGGER bd204_truncar ON public.%I',t);
 END LOOP;
END
$drop_triggers$;
DROP FUNCTION public.bd204_guardar_hijo();
DROP FUNCTION public.bd204_guardar_version();
DROP FUNCTION public.bd204_guardar_caso();
DROP FUNCTION public.bd204_no_truncar();
DROP FUNCTION public.bd204_borrador(uuid,boolean);
DROP FUNCTION public.bd204_version(text,jsonb);
