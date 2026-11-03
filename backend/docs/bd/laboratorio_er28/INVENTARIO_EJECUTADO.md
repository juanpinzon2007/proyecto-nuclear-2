# Inventario PostgreSQL ejecutado — ER28

Fuente de evidencia: [evidencia_6942afe5800a40b6836f2e43b3e74793.json](evidencia_6942afe5800a40b6836f2e43b3e74793.json).

28 tablas de usuario en todos los schemas, todas en public; 144 columnas, 28 PK, 40 FK, 19 UNIQUE y 47 índices de PK/UNIQUE. Sin tablas auxiliares, sin CHECK ni triggers de usuario añadidos.

## Tablas y claves

| Tabla | Columnas | PK | UNIQUE | FK salientes |
|---|---:|---|---|---|
| asignacion_caso | 10 | id_asignacion | — | id_grupo → grupo_academico(id_grupo); id_caso → caso(id_caso) |
| caso | 7 | id_caso | — | id_profesor → usuario(id_usuario) |
| consentimiento | 5 | id_consentimiento | — | id_estudiante → usuario(id_usuario) |
| criterio_rubrica | 4 | id_criterio | — | id_rubrica → rubrica(id_rubrica) |
| decision | 5 | id_decision | id_escena,orden | id_escena → escena(id_escena); id_criterio → criterio_rubrica(id_criterio) |
| escena | 6 | id_escena | id_caso,orden | id_caso → caso(id_caso) |
| grupo_academico | 4 | id_grupo | — | id_profesor → usuario(id_usuario) |
| grupo_estudiante | 5 | id_grupo_estudiante | id_grupo,id_estudiante | id_grupo → grupo_academico(id_grupo); id_estudiante → usuario(id_usuario) |
| intento | 8 | id_intento | id_participacion,numero_intento | id_participacion → participacion(id_participacion); id_consentimiento → consentimiento(id_consentimiento); id_permiso_extra → permiso_intento_extra(id_permiso_extra) |
| nivel_criterio | 4 | id_nivel | id_nivel,id_criterio; id_criterio,nombre | id_criterio → criterio_rubrica(id_criterio) |
| notificacion | 8 | id_notificacion | — | id_usuario → usuario(id_usuario); id_asignacion → asignacion_caso(id_asignacion) |
| objetivo_aprendizaje | 4 | id_objetivo | id_caso,orden | id_caso → caso(id_caso) |
| opcion_respuesta | 7 | id_opcion | id_decision,orden; id_opcion,id_decision | id_decision → decision(id_decision); id_escena_destino → escena(id_escena) |
| participacion | 5 | id_participacion | id_asignacion,id_grupo_estudiante | id_asignacion → asignacion_caso(id_asignacion); id_grupo_estudiante → grupo_estudiante(id_grupo_estudiante) |
| paso_simulacion | 8 | id_paso | id_intento,numero_paso | id_intento → intento(id_intento); id_opcion,id_decision → opcion_respuesta(id_opcion,id_decision) |
| permiso | 3 | id_permiso | codigo | — |
| permiso_intento_extra | 6 | id_permiso_extra | — | id_participacion → participacion(id_participacion); id_profesor → usuario(id_usuario) |
| personaje | 4 | id_personaje | — | id_caso → caso(id_caso) |
| personaje_escena | 2 | id_personaje,id_escena | — | id_personaje → personaje(id_personaje); id_escena → escena(id_escena) |
| pista | 3 | id_pista | — | id_decision → decision(id_decision) |
| resultado_criterio | 5 | id_resultado_criterio | id_resultado,id_criterio | id_resultado → resultado_intento(id_resultado); id_nivel,id_criterio → nivel_criterio(id_nivel,id_criterio) |
| resultado_intento | 5 | id_resultado | id_intento | id_intento → intento(id_intento) |
| resultado_participacion | 6 | id_resultado_participacion | id_participacion | id_participacion → participacion(id_participacion) |
| retroalimentacion_docente | 5 | id_retroalimentacion | id_asignacion | id_asignacion → asignacion_caso(id_asignacion); id_profesor → usuario(id_usuario) |
| rol | 3 | id_rol | nombre | — |
| rol_permiso | 2 | id_rol,id_permiso | — | id_rol → rol(id_rol); id_permiso → permiso(id_permiso) |
| rubrica | 4 | id_rubrica | id_caso | id_caso → caso(id_caso) |
| usuario | 6 | id_usuario | correo | id_rol → rol(id_rol) |

## Las 144 columnas observadas

| Tabla.columna | Tipo PostgreSQL | NULL | Identidad | Default |
|---|---|---|---|---|
| asignacion_caso.id_asignacion | integer | NO | YES | — |
| asignacion_caso.id_grupo | integer | NO | NO | — |
| asignacion_caso.id_caso | integer | NO | NO | — |
| asignacion_caso.apertura | timestamp without time zone | NO | NO | — |
| asignacion_caso.cierre | timestamp without time zone | NO | NO | — |
| asignacion_caso.fecha_limite_ingreso | timestamp without time zone | NO | NO | — |
| asignacion_caso.intentos_base | integer | NO | NO | 1 |
| asignacion_caso.tiempo_maximo_min | integer | NO | NO | — |
| asignacion_caso.codigo_acceso_hash | character varying(255) | NO | NO | — |
| asignacion_caso.estado | character varying(20) | NO | NO | 'programada'::character varying |
| caso.id_caso | integer | NO | YES | — |
| caso.id_profesor | integer | NO | NO | — |
| caso.titulo | character varying(160) | NO | NO | — |
| caso.introduccion_teorica | text | NO | NO | — |
| caso.estado | character varying(20) | NO | NO | 'borrador'::character varying |
| caso.fecha_creacion | timestamp without time zone | NO | NO | — |
| caso.fecha_validacion | timestamp without time zone | YES | NO | — |
| consentimiento.id_consentimiento | integer | NO | YES | — |
| consentimiento.id_estudiante | integer | NO | NO | — |
| consentimiento.version_texto | character varying(30) | NO | NO | — |
| consentimiento.fecha_aceptacion | timestamp without time zone | NO | NO | — |
| consentimiento.fecha_revocacion | timestamp without time zone | YES | NO | — |
| criterio_rubrica.id_criterio | integer | NO | YES | — |
| criterio_rubrica.id_rubrica | integer | NO | NO | — |
| criterio_rubrica.nombre | character varying(120) | NO | NO | — |
| criterio_rubrica.peso_porcentaje | numeric(5,2) | NO | NO | — |
| decision.id_decision | integer | NO | YES | — |
| decision.id_escena | integer | NO | NO | — |
| decision.id_criterio | integer | NO | NO | — |
| decision.enunciado | text | NO | NO | — |
| decision.orden | integer | NO | NO | — |
| escena.id_escena | integer | NO | YES | — |
| escena.id_caso | integer | NO | NO | — |
| escena.titulo | character varying(160) | NO | NO | — |
| escena.contexto | text | NO | NO | — |
| escena.orden | integer | NO | NO | — |
| escena.tipo | character varying(30) | NO | NO | — |
| grupo_academico.id_grupo | integer | NO | YES | — |
| grupo_academico.id_profesor | integer | NO | NO | — |
| grupo_academico.nombre | character varying(120) | NO | NO | — |
| grupo_academico.periodo | character varying(30) | NO | NO | — |
| grupo_estudiante.id_grupo_estudiante | integer | NO | YES | — |
| grupo_estudiante.id_grupo | integer | NO | NO | — |
| grupo_estudiante.id_estudiante | integer | NO | NO | — |
| grupo_estudiante.fecha_ingreso | timestamp without time zone | NO | NO | — |
| grupo_estudiante.activo | boolean | NO | NO | true |
| intento.id_intento | integer | NO | YES | — |
| intento.id_participacion | integer | NO | NO | — |
| intento.id_consentimiento | integer | NO | NO | — |
| intento.id_permiso_extra | integer | YES | NO | — |
| intento.numero_intento | integer | NO | NO | — |
| intento.estado | character varying(20) | NO | NO | — |
| intento.inicio | timestamp without time zone | NO | NO | — |
| intento.fin | timestamp without time zone | YES | NO | — |
| nivel_criterio.id_nivel | integer | NO | YES | — |
| nivel_criterio.id_criterio | integer | NO | NO | — |
| nivel_criterio.nombre | character varying(80) | NO | NO | — |
| nivel_criterio.logro_porcentaje | numeric(5,2) | NO | NO | — |
| notificacion.id_notificacion | integer | NO | YES | — |
| notificacion.id_usuario | integer | NO | NO | — |
| notificacion.id_asignacion | integer | YES | NO | — |
| notificacion.tipo | character varying(40) | NO | NO | — |
| notificacion.mensaje | text | NO | NO | — |
| notificacion.fecha_creacion | timestamp without time zone | NO | NO | — |
| notificacion.fecha_envio | timestamp without time zone | YES | NO | — |
| notificacion.fecha_lectura | timestamp without time zone | YES | NO | — |
| objetivo_aprendizaje.id_objetivo | integer | NO | YES | — |
| objetivo_aprendizaje.id_caso | integer | NO | NO | — |
| objetivo_aprendizaje.descripcion | text | NO | NO | — |
| objetivo_aprendizaje.orden | integer | NO | NO | — |
| opcion_respuesta.id_opcion | integer | NO | YES | — |
| opcion_respuesta.id_decision | integer | NO | NO | — |
| opcion_respuesta.id_escena_destino | integer | YES | NO | — |
| opcion_respuesta.texto | text | NO | NO | — |
| opcion_respuesta.es_correcta | boolean | NO | NO | — |
| opcion_respuesta.justificacion_teorica | text | NO | NO | — |
| opcion_respuesta.orden | integer | NO | NO | — |
| participacion.id_participacion | integer | NO | YES | — |
| participacion.id_asignacion | integer | NO | NO | — |
| participacion.id_grupo_estudiante | integer | NO | NO | — |
| participacion.estado | character varying(20) | NO | NO | 'pendiente'::character varying |
| participacion.fecha_registro | timestamp without time zone | NO | NO | — |
| paso_simulacion.id_paso | integer | NO | YES | — |
| paso_simulacion.id_intento | integer | NO | NO | — |
| paso_simulacion.id_decision | integer | NO | NO | — |
| paso_simulacion.id_opcion | integer | NO | NO | — |
| paso_simulacion.numero_paso | integer | NO | NO | — |
| paso_simulacion.registrado_en | timestamp without time zone | NO | NO | — |
| paso_simulacion.tiempo_segundos | integer | NO | NO | — |
| paso_simulacion.reflexion_estudiante | text | YES | NO | — |
| permiso.id_permiso | integer | NO | YES | — |
| permiso.codigo | character varying(80) | NO | NO | — |
| permiso.descripcion | text | NO | NO | — |
| permiso_intento_extra.id_permiso_extra | integer | NO | YES | — |
| permiso_intento_extra.id_participacion | integer | NO | NO | — |
| permiso_intento_extra.id_profesor | integer | NO | NO | — |
| permiso_intento_extra.cantidad_autorizada | integer | NO | NO | 1 |
| permiso_intento_extra.justificacion | text | NO | NO | — |
| permiso_intento_extra.fecha_autorizacion | timestamp without time zone | NO | NO | — |
| personaje.id_personaje | integer | NO | YES | — |
| personaje.id_caso | integer | NO | NO | — |
| personaje.nombre | character varying(100) | NO | NO | — |
| personaje.descripcion | text | YES | NO | — |
| personaje_escena.id_personaje | integer | NO | NO | — |
| personaje_escena.id_escena | integer | NO | NO | — |
| pista.id_pista | integer | NO | YES | — |
| pista.id_decision | integer | NO | NO | — |
| pista.texto | text | NO | NO | — |
| resultado_criterio.id_resultado_criterio | integer | NO | YES | — |
| resultado_criterio.id_resultado | integer | NO | NO | — |
| resultado_criterio.id_criterio | integer | NO | NO | — |
| resultado_criterio.id_nivel | integer | NO | NO | — |
| resultado_criterio.puntaje_obtenido | numeric(5,2) | NO | NO | — |
| resultado_intento.id_resultado | integer | NO | YES | — |
| resultado_intento.id_intento | integer | NO | NO | — |
| resultado_intento.nota_final | numeric(4,2) | NO | NO | — |
| resultado_intento.fecha_calculo | timestamp without time zone | NO | NO | — |
| resultado_intento.comentario_automatico | text | YES | NO | — |
| resultado_participacion.id_resultado_participacion | integer | NO | YES | — |
| resultado_participacion.id_participacion | integer | NO | NO | — |
| resultado_participacion.situacion | character varying(20) | NO | NO | — |
| resultado_participacion.nota_definitiva | numeric(4,2) | NO | NO | — |
| resultado_participacion.fecha_calculo | timestamp without time zone | NO | NO | — |
| resultado_participacion.observacion | text | YES | NO | — |
| retroalimentacion_docente.id_retroalimentacion | integer | NO | YES | — |
| retroalimentacion_docente.id_asignacion | integer | NO | NO | — |
| retroalimentacion_docente.id_profesor | integer | NO | NO | — |
| retroalimentacion_docente.texto | text | NO | NO | — |
| retroalimentacion_docente.fecha_registro | timestamp without time zone | NO | NO | — |
| rol.id_rol | integer | NO | YES | — |
| rol.nombre | character varying(40) | NO | NO | — |
| rol.descripcion | text | YES | NO | — |
| rol_permiso.id_rol | integer | NO | NO | — |
| rol_permiso.id_permiso | integer | NO | NO | — |
| rubrica.id_rubrica | integer | NO | YES | — |
| rubrica.id_caso | integer | NO | NO | — |
| rubrica.nombre | character varying(120) | NO | NO | — |
| rubrica.nota_maxima | numeric(4,2) | NO | NO | — |
| usuario.id_usuario | integer | NO | YES | — |
| usuario.id_rol | integer | NO | NO | — |
| usuario.nombre | character varying(120) | NO | NO | — |
| usuario.correo | character varying(200) | NO | NO | — |
| usuario.clave_hash | character varying(255) | NO | NO | — |
| usuario.activo | boolean | NO | NO | true |

## Los 47 índices observados

| Tabla | Índice | Definición |
|---|---|---|
| asignacion_caso | pk_asignacion_caso | `CREATE UNIQUE INDEX pk_asignacion_caso ON public.asignacion_caso USING btree (id_asignacion)` |
| caso | pk_caso | `CREATE UNIQUE INDEX pk_caso ON public.caso USING btree (id_caso)` |
| consentimiento | pk_consentimiento | `CREATE UNIQUE INDEX pk_consentimiento ON public.consentimiento USING btree (id_consentimiento)` |
| criterio_rubrica | pk_criterio_rubrica | `CREATE UNIQUE INDEX pk_criterio_rubrica ON public.criterio_rubrica USING btree (id_criterio)` |
| decision | pk_decision | `CREATE UNIQUE INDEX pk_decision ON public.decision USING btree (id_decision)` |
| decision | uq_decision_1 | `CREATE UNIQUE INDEX uq_decision_1 ON public.decision USING btree (id_escena, orden)` |
| escena | pk_escena | `CREATE UNIQUE INDEX pk_escena ON public.escena USING btree (id_escena)` |
| escena | uq_escena_1 | `CREATE UNIQUE INDEX uq_escena_1 ON public.escena USING btree (id_caso, orden)` |
| grupo_academico | pk_grupo_academico | `CREATE UNIQUE INDEX pk_grupo_academico ON public.grupo_academico USING btree (id_grupo)` |
| grupo_estudiante | pk_grupo_estudiante | `CREATE UNIQUE INDEX pk_grupo_estudiante ON public.grupo_estudiante USING btree (id_grupo_estudiante)` |
| grupo_estudiante | uq_grupo_estudiante_1 | `CREATE UNIQUE INDEX uq_grupo_estudiante_1 ON public.grupo_estudiante USING btree (id_grupo, id_estudiante)` |
| intento | pk_intento | `CREATE UNIQUE INDEX pk_intento ON public.intento USING btree (id_intento)` |
| intento | uq_intento_1 | `CREATE UNIQUE INDEX uq_intento_1 ON public.intento USING btree (id_participacion, numero_intento)` |
| nivel_criterio | pk_nivel_criterio | `CREATE UNIQUE INDEX pk_nivel_criterio ON public.nivel_criterio USING btree (id_nivel)` |
| nivel_criterio | uq_nivel_criterio_1 | `CREATE UNIQUE INDEX uq_nivel_criterio_1 ON public.nivel_criterio USING btree (id_nivel, id_criterio)` |
| nivel_criterio | uq_nivel_criterio_2 | `CREATE UNIQUE INDEX uq_nivel_criterio_2 ON public.nivel_criterio USING btree (id_criterio, nombre)` |
| notificacion | pk_notificacion | `CREATE UNIQUE INDEX pk_notificacion ON public.notificacion USING btree (id_notificacion)` |
| objetivo_aprendizaje | pk_objetivo_aprendizaje | `CREATE UNIQUE INDEX pk_objetivo_aprendizaje ON public.objetivo_aprendizaje USING btree (id_objetivo)` |
| objetivo_aprendizaje | uq_objetivo_aprendizaje_1 | `CREATE UNIQUE INDEX uq_objetivo_aprendizaje_1 ON public.objetivo_aprendizaje USING btree (id_caso, orden)` |
| opcion_respuesta | pk_opcion_respuesta | `CREATE UNIQUE INDEX pk_opcion_respuesta ON public.opcion_respuesta USING btree (id_opcion)` |
| opcion_respuesta | uq_opcion_respuesta_1 | `CREATE UNIQUE INDEX uq_opcion_respuesta_1 ON public.opcion_respuesta USING btree (id_decision, orden)` |
| opcion_respuesta | uq_opcion_respuesta_2 | `CREATE UNIQUE INDEX uq_opcion_respuesta_2 ON public.opcion_respuesta USING btree (id_opcion, id_decision)` |
| participacion | pk_participacion | `CREATE UNIQUE INDEX pk_participacion ON public.participacion USING btree (id_participacion)` |
| participacion | uq_participacion_1 | `CREATE UNIQUE INDEX uq_participacion_1 ON public.participacion USING btree (id_asignacion, id_grupo_estudiante)` |
| paso_simulacion | pk_paso_simulacion | `CREATE UNIQUE INDEX pk_paso_simulacion ON public.paso_simulacion USING btree (id_paso)` |
| paso_simulacion | uq_paso_simulacion_1 | `CREATE UNIQUE INDEX uq_paso_simulacion_1 ON public.paso_simulacion USING btree (id_intento, numero_paso)` |
| permiso | pk_permiso | `CREATE UNIQUE INDEX pk_permiso ON public.permiso USING btree (id_permiso)` |
| permiso | uq_permiso_1 | `CREATE UNIQUE INDEX uq_permiso_1 ON public.permiso USING btree (codigo)` |
| permiso_intento_extra | pk_permiso_intento_extra | `CREATE UNIQUE INDEX pk_permiso_intento_extra ON public.permiso_intento_extra USING btree (id_permiso_extra)` |
| personaje | pk_personaje | `CREATE UNIQUE INDEX pk_personaje ON public.personaje USING btree (id_personaje)` |
| personaje_escena | pk_personaje_escena | `CREATE UNIQUE INDEX pk_personaje_escena ON public.personaje_escena USING btree (id_personaje, id_escena)` |
| pista | pk_pista | `CREATE UNIQUE INDEX pk_pista ON public.pista USING btree (id_pista)` |
| resultado_criterio | pk_resultado_criterio | `CREATE UNIQUE INDEX pk_resultado_criterio ON public.resultado_criterio USING btree (id_resultado_criterio)` |
| resultado_criterio | uq_resultado_criterio_1 | `CREATE UNIQUE INDEX uq_resultado_criterio_1 ON public.resultado_criterio USING btree (id_resultado, id_criterio)` |
| resultado_intento | pk_resultado_intento | `CREATE UNIQUE INDEX pk_resultado_intento ON public.resultado_intento USING btree (id_resultado)` |
| resultado_intento | uq_resultado_intento_1 | `CREATE UNIQUE INDEX uq_resultado_intento_1 ON public.resultado_intento USING btree (id_intento)` |
| resultado_participacion | pk_resultado_participacion | `CREATE UNIQUE INDEX pk_resultado_participacion ON public.resultado_participacion USING btree (id_resultado_participacion)` |
| resultado_participacion | uq_resultado_participacion_1 | `CREATE UNIQUE INDEX uq_resultado_participacion_1 ON public.resultado_participacion USING btree (id_participacion)` |
| retroalimentacion_docente | pk_retroalimentacion_docente | `CREATE UNIQUE INDEX pk_retroalimentacion_docente ON public.retroalimentacion_docente USING btree (id_retroalimentacion)` |
| retroalimentacion_docente | uq_retroalimentacion_docente_1 | `CREATE UNIQUE INDEX uq_retroalimentacion_docente_1 ON public.retroalimentacion_docente USING btree (id_asignacion)` |
| rol | pk_rol | `CREATE UNIQUE INDEX pk_rol ON public.rol USING btree (id_rol)` |
| rol | uq_rol_1 | `CREATE UNIQUE INDEX uq_rol_1 ON public.rol USING btree (nombre)` |
| rol_permiso | pk_rol_permiso | `CREATE UNIQUE INDEX pk_rol_permiso ON public.rol_permiso USING btree (id_rol, id_permiso)` |
| rubrica | pk_rubrica | `CREATE UNIQUE INDEX pk_rubrica ON public.rubrica USING btree (id_rubrica)` |
| rubrica | uq_rubrica_1 | `CREATE UNIQUE INDEX uq_rubrica_1 ON public.rubrica USING btree (id_caso)` |
| usuario | pk_usuario | `CREATE UNIQUE INDEX pk_usuario ON public.usuario USING btree (id_usuario)` |
| usuario | uq_usuario_1 | `CREATE UNIQUE INDEX uq_usuario_1 ON public.usuario USING btree (correo)` |

Las definiciones completas de las 87 restricciones, acciones FK y generación de identidad están en el JSON. Este inventario procede del catálogo nativo del contenedor eliminado, no de los modelos productivos.
