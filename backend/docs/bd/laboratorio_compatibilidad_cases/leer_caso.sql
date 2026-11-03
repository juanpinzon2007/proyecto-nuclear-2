-- Consulta interna experimental, NO proyección estudiantil ni autorización.
-- El ejecutor sustituye el marcador exclusivamente por un int positivo local.
SELECT COALESCE((
 SELECT jsonb_build_object(
  'asignacion',to_jsonb(a)-'codigo_acceso_hash',
  'caso',to_jsonb(c),
  'objetivos',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.orden)
    FROM objetivo_aprendizaje x WHERE x.id_caso=c.id_caso),'[]'::jsonb),
  'personajes',COALESCE((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id_personaje)
    FROM personaje x WHERE x.id_caso=c.id_caso),'[]'::jsonb),
  'rubrica',(SELECT to_jsonb(r) || jsonb_build_object('criterios',
    COALESCE((SELECT jsonb_agg(to_jsonb(k) || jsonb_build_object('niveles',
      COALESCE((SELECT jsonb_agg(to_jsonb(n) ORDER BY n.id_nivel)
        FROM nivel_criterio n WHERE n.id_criterio=k.id_criterio),'[]'::jsonb)) ORDER BY k.id_criterio)
      FROM criterio_rubrica k WHERE k.id_rubrica=r.id_rubrica),'[]'::jsonb))
    FROM rubrica r WHERE r.id_caso=c.id_caso),
  'escenas',COALESCE((SELECT jsonb_agg(to_jsonb(e) || jsonb_build_object(
    'personajes',COALESCE((SELECT jsonb_agg(pe.id_personaje ORDER BY pe.id_personaje)
      FROM personaje_escena pe WHERE pe.id_escena=e.id_escena),'[]'::jsonb),
    'decisiones',COALESCE((SELECT jsonb_agg(to_jsonb(d) || jsonb_build_object(
      'pistas',COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.id_pista)
        FROM pista p WHERE p.id_decision=d.id_decision),'[]'::jsonb),
      'opciones',COALESCE((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.orden)
        FROM opcion_respuesta o WHERE o.id_decision=d.id_decision),'[]'::jsonb)) ORDER BY d.orden)
      FROM decision d WHERE d.id_escena=e.id_escena),'[]'::jsonb)) ORDER BY e.orden)
    FROM escena e WHERE e.id_caso=c.id_caso),'[]'::jsonb)
 )
 FROM asignacion_caso a JOIN caso c ON c.id_caso=a.id_caso
 WHERE a.id_asignacion=__ASIGNACION_ID__
), 'null'::jsonb);
