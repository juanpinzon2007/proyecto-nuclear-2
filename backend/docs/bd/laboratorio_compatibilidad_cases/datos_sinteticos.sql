-- Solo para el PostgreSQL nuevo creado por run_cases_experiment.py.
-- IDs INTEGER locales, sin equivalencias con usuarios o UUID del backend.
-- Fechas, hashes no operativos y porcentajes son datos de ensayo, no políticas.
BEGIN;
INSERT INTO rol (id_rol,nombre) VALUES (1,'docente_laboratorio'),(2,'estudiante_laboratorio');
INSERT INTO usuario (id_usuario,id_rol,nombre,correo,clave_hash) VALUES
 (11,1,'Docente sintético','docente@example.invalid','NO_ES_UN_HASH_OPERATIVO'),
 (12,2,'Estudiante sintético','estudiante@example.invalid','NO_ES_UN_HASH_OPERATIVO');
INSERT INTO grupo_academico (id_grupo,id_profesor,nombre,periodo)
 VALUES (100,11,'Grupo sintético','ensayo');
INSERT INTO grupo_estudiante (id_grupo_estudiante,id_grupo,id_estudiante,fecha_ingreso)
 VALUES (110,100,12,'2030-01-01 09:00:00');
INSERT INTO caso (id_caso,id_profesor,titulo,introduccion_teorica,fecha_creacion)
 VALUES (10,11,'Cooperación en un equipo','Marco sintético inicial','2030-01-01 09:00:00');
INSERT INTO objetivo_aprendizaje (id_objetivo,id_caso,descripcion,orden)
 VALUES (120,10,'Reconocer alternativas de cooperación',1);
INSERT INTO rubrica (id_rubrica,id_caso,nombre,nota_maxima)
 VALUES (20,10,'Rúbrica de ensayo',5.00);
INSERT INTO criterio_rubrica (id_criterio,id_rubrica,nombre,peso_porcentaje)
 VALUES (21,20,'Análisis',60.00),(22,20,'Comunicación',40.00);
INSERT INTO nivel_criterio (id_nivel,id_criterio,nombre,logro_porcentaje)
 VALUES (31,21,'Inicial',0.00),(32,21,'Desarrollado',100.00),
        (33,22,'Inicial',0.00),(34,22,'Desarrollado',100.00);
-- Inserción deliberadamente desordenada: la lectura debe ordenar explícitamente.
INSERT INTO escena (id_escena,id_caso,titulo,contexto,orden,tipo) VALUES
 (103,10,'Cierre','El equipo revisa sus acuerdos',3,'ensayo'),
 (101,10,'Reunión','El equipo discrepa sobre el reparto',1,'ensayo'),
 (102,10,'Diálogo','Dos integrantes conversan',2,'ensayo');
INSERT INTO personaje (id_personaje,id_caso,nombre,descripcion)
 VALUES (130,10,'Integrante A','Personaje ficticio');
INSERT INTO personaje_escena (id_personaje,id_escena) VALUES (130,101),(130,102);
INSERT INTO decision (id_decision,id_escena,id_criterio,enunciado,orden) VALUES
 (203,103,22,'¿Cómo comunicar el acuerdo?',1),
 (201,101,21,'¿Cómo abordar el desacuerdo?',1),
 (202,102,22,'¿Cómo organizar el diálogo?',1);
INSERT INTO opcion_respuesta
 (id_opcion,id_decision,id_escena_destino,texto,es_correcta,justificacion_teorica,orden) VALUES
 (302,201,103,'Omitir el diálogo',false,'Justificación sintética B',2),
 (301,201,102,'Escuchar a los integrantes',true,'Justificación sintética A',1),
 (304,202,103,'Imponer una solución',false,'Justificación sintética D',2),
 (303,202,103,'Acordar turnos',true,'Justificación sintética C',1),
 (306,203,NULL,'Ocultar los acuerdos',false,'Justificación sintética F',2),
 (305,203,NULL,'Compartir los acuerdos',true,'Justificación sintética E',1);
INSERT INTO pista (id_pista,id_decision,texto)
 VALUES (140,201,'Pista sintética sobre escucha');
INSERT INTO asignacion_caso
 (id_asignacion,id_grupo,id_caso,apertura,cierre,fecha_limite_ingreso,tiempo_maximo_min,codigo_acceso_hash)
 VALUES
 (401,100,10,'2030-01-02 09:00:00','2030-01-02 11:00:00','2030-01-02 09:10:00',30,'NO_ES_UN_HASH_OPERATIVO'),
 (402,100,10,'2030-01-03 09:00:00','2030-01-03 11:00:00','2030-01-03 09:10:00',30,'NO_ES_UN_HASH_OPERATIVO');
COMMIT;
