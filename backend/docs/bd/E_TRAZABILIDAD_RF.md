# E — Cobertura de los 27 RF con el ER oficial de 28 tablas

**BD-1.2.** Fuente central: ProyectoNuclear-IngenieriaSoftwareII (1).pdf, páginas 4–5; reglas en página 7. «Soporte estructural» significa capacidad del modelo para guardar los datos principales; no equivale a implementación, prueba aprobada o seguridad completa.

## 1. Respuesta a la pregunta de cobertura

El número **28 no impide por sí mismo** resolver los 27 RF. No se necesita una tabla por RF ni nuevas entidades para progreso, reloj, reporte, JWT o worker. Sin embargo, **no puede certificarse que el DDL original exacto soporte íntegramente todos los RF y preserve a la vez los contratos actuales**.

Hay discrepancias concretas: código grupal frente a individual (RF-01/20/21), feedback por asignación frente a individual (RF-15/26/27), estimado/lugar/mensaje ausentes (RF-05/18), y pérdida de referencia versionada respecto del backend. Se presentan ajustes dentro de las mismas 28 entidades para aprobación, no se amplía el objetivo. RF-22 y evaluación siguen sujetos a reglas explícitamente pendientes.

## 2. Matriz completa

| RF | Requisito | Tablas/campos oficiales | Soporte del ER | Qué permite | Límite / aprobación |
|---|---|---|---|---|---|
| RF-01 | Autenticación estudiantil | usuario, grupo_estudiante, asignacion_caso, participacion | Conflicto de integración | Cuenta y vínculo académico representables; no hay convocatoria ni hash individual por alumno en el ER. | Login actual usa convocatoria UUID/JWT y código propio. Requiere R03, no un código grupal aceptado como identidad. |
| RF-02 | Rol y permiso | rol, permiso, rol_permiso, usuario | Soporte estructural | Las cuatro tablas de acceso coinciden; autenticación/autoridad/alcance siguen en servidor. | No nueva tabla JWT ni cabeceras confiables. Servicios/permisos deben comprobarse. |
| RF-03 | Administrar docentes | usuario, rol, permiso, rol_permiso | Soporte estructural | Rol, estado, correo y hash persistibles. | No demuestra que todos los servicios administrativos estén completos ni autoriza duplicar usuarios. |
| RF-04 | Espacio y estudiantes autorizados | grupo_academico, grupo_estudiante, asignacion_caso, participacion | Parcial | Grupo/nombre/período y membresías pueden organizar una oferta académica si se acuerda la equivalencia. | Espacio actual UUID no contiene matrícula/período; no asumir grupo=espacio. R03/R08. |
| RF-05 | Estructura del caso | caso, escena, objetivo_aprendizaje, personaje, personaje_escena | Parcial | Título/introducción/contextos están representados con nombres oficiales. | Falta tiempo estimado del caso, presente en versión actual. No confundir con máximo de asignación ni renombrar texto sin validar semántica. R02/R03. |
| RF-06 | Contextos y preguntas | escena, decision, opcion_respuesta | Soporte estructural | Contexto y enunciados/opciones por escena. | La aplicabilidad de ramas no la define una FK; no contar todas las preguntas como progreso. |
| RF-07 | Opciones y corrección | decision, opcion_respuesta | Soporte estructural | es_correcta y vínculo opción/decisión, orden UNIQUE. | No implica publicación válida ni autoriza mostrar corrección durante intento. |
| RF-08 | Justificar opciones | opcion_respuesta.justificacion_teorica | Soporte estructural | Explicación por opción. | Acceso posterior al cierre por servicio; no tabla adicional necesaria. |
| RF-09 | Borrador/publicar/archivar | caso, rubrica, criterio_rubrica, nivel_criterio | Parcial | Campo estado y rúbrica asociada permiten validación de publicación. | Estados no tienen CHECK; original default borrador difiere de enum actual. Inmutabilidad/versiones y archivo requieren R02. |
| RF-10 | Responder y modificar | intento, paso_simulacion, decision, opcion_respuesta | Soporte estructural | Última selección puede actualizarse o proyectarse desde registros ordenados de la misma tabla. | Elegir contrato, guardas de cerrado y política de cambio de ruta; no implica que el escritor exista. R08. |
| RF-11 | Persistencia/progreso privado | participacion, intento, paso_simulacion | Parcial | Selecciones almacenables sin tabla de progreso; puede derivarse. | Falta escritor, atomicidad y contrato de decisiones aplicables; filtrar datos correctivos. R08. |
| RF-12 | Inicio/fin/nota/feedback por pregunta | intento, paso_simulacion, resultado_intento, resultado_criterio, opcion_respuesta | Parcial | Tiempos y nota por intento; explicación por pregunta reconstruible desde selección/opción. | Feedback histórico solo reproducible con contenido/rúbrica estables; no detalle por pregunta persistido explícito. R02/R06. |
| RF-13 | Calcular y guardar nota | rubrica, criterio_rubrica, nivel_criterio, resultado_intento, resultado_criterio | Parcial | Máximo, pesos/logros porcentuales y nota tienen columnas. | Fórmula/redondeo/equivalencia con puntajes actuales pendientes; decision solo tiene un criterio. R06. |
| RF-14 | Resultado/feedback final | resultado_intento, resultado_criterio, paso_simulacion, opcion_respuesta | Parcial | Puede consultar nota y aciertos/explicaciones tras cierre. | Solo persistido definitivo autorizado; conservar contenido exacto, no la edición más nueva. R02/R06. |
| RF-15 | Seguimiento por estudiante | grupo_estudiante, participacion, intento, paso_simulacion, resultados, retroalimentacion_docente | Parcial | Existe cadena usuario→membresía→participación→respuesta/resultado. | Feedback original es por asignación, no individual. Restringir docente/alcance; R04. |
| RF-16 | Reporte con parciales/ausencias | asignacion_caso, grupo_estudiante, participacion, intento, resultado_participacion | Parcial | Un roster confirmado permite LEFT JOIN sin intento; no se necesita tabla reporte. | Una fila faltante no certifica ausencia. Definir convocados antes de inicio, parcial/consolidación y universo; R03/R06. |
| RF-17 | Registrar rúbrica | rubrica, criterio_rubrica, nivel_criterio, caso | Soporte estructural | Una rúbrica por caso, con máximo y porcentajes. | No equivale a varias rúbricas por versión de un mismo caso estable; R02/R06 para importar. |
| RF-18 | Programar condiciones | asignacion_caso, grupo_academico, caso | Parcial | Apertura/cierre/umbral/máximo están representados. | No hay lugar ni mensaje de programación ni estimado del caso para comparar; preservar datos actuales hasta R03. |
| RF-19 | Estados de sesión | asignacion_caso.estado y fechas | Soporte estructural | Puede representar ciclo de programación con contrato State adaptado y proceso temporal. | No hay sesión separada/cierre real/auditoría. El cierre automático requiere servicio/worker, no tabla Worker nueva. R03/R07. |
| RF-20 | Código individual | asignacion_caso, participacion, grupo_estudiante | Conflicto de granularidad | El ER solo tiene codigo_acceso_hash por asignación grupal. | No demuestra asociación de código a alumno. Campos en participación o contrato alternativo seguro requieren R03; no nueva convocatoria por inferencia. |
| RF-21 | Notificar convocatoria/cambios | notificacion, usuario, asignacion_caso, participacion | Parcial | Destino por usuario y asignación; mensaje, envío/lectura. | No roster individual ACTIVA/RETIRADA ni reintentos persistidos. Hash no permite recuperar código para correo. R03/R09. |
| RF-22 | Límite de ingreso | asignacion_caso.fecha_limite_ingreso, apertura, cierre | Política pendiente | Hay campo para un umbral confiable del servidor. | RF-22 no aprobó base/fórmula/fronteras. Columna existente no autoriza inventar tolerancia ni abrir ingreso. R07. |
| RF-23 | Tiempo individual | intento.inicio/fin, asignacion_caso.tiempo_maximo_min, paso_simulacion | Parcial | Puede reconstruir plazo si asignación mantiene máximo histórico. | Dominio conserva duración pero ER no; cambios posteriores exigen contrato inmutable o columna aprobada en intento. R07. |
| RF-24 | Parcial y ausencia | resultado_intento, resultado_criterio, resultado_participacion, decision | Parcial | Ausencia puede tener cabecera definitiva por participación sin intento. Ceros por pregunta reconstruibles bajo regla/universo estable. | Detalle de criterio obligatorio por intento/nivel no sirve para ausencia sin ficticios. Fórmula y ámbito pendientes R06. |
| RF-25 | Repetición excepcional | participacion, intento, permiso_intento_extra, caso, asignacion_caso | Parcial | Profesor autoriza por participación; número/cantidad y creador derivable. | Bloquear/contar cupos, validar creador y estado finalizado; intentos_base no autoriza repetición automática contraria a RF-25. R06/R07. |
| RF-26 | Feedback general individual | retroalimentacion_docente, participacion | Conflicto de alcance | La tabla oficial tiene id_asignacion UNIQUE, sin destinatario/participación. | No satisface por sí sola RF-26 individual para varios alumnos. Aprobar ajuste en la misma entidad o alternativa explícita R04. |
| RF-27 | Notificar nota y feedback | notificacion, usuario, resultado_participacion, retroalimentacion_docente | Parcial | Se puede notificar por usuario tras persistir resultado/feedback. | Debe resolverse comentario individual, reintento/idempotencia y entrega tras commit; no se requiere automáticamente una tabla outbox. R04/R09. |

En RF-15 «resultados» abrevia las tres tablas oficiales: resultado_intento, resultado_criterio y resultado_participacion; no propone otra entidad.

## 3. Cómo resolver funciones sin ampliar automáticamente entidades

| Función | Opción compatible con 28 | Condición |
|---|---|---|
| Historial de selección | Varias filas en paso_simulacion, número secuencial y última por decisión al leer | Aprobar semántica R08 y adaptar repositorio/DTO; no afirmar que ya funciona |
| Progreso | Derivar desde pasos y decisiones aplicables del caso | Contrato Cases, sin filtrar corrección ni borrar ramas sin política |
| Tiempo individual | Inicio + máximo histórico de asignación | Máximo inmutable o campo de plazo dentro de intento aprobado R07 |
| Ausencia | resultado_participacion sin intento; ceros por pregunta derivados de contenido/regla establecidos | Roster y universo confiables; no inventar intento/nivel/respuesta |
| Reporte | Consulta filtrada con joins y LEFT JOIN desde roster | Ausencia no se infiere de error de persistencia; autorización docente |
| Publicación/historia | Contenido y rúbrica de caso usados quedan estables; otra edición como caso distinto si se aprueba | No conserva por sí sola identidad estable/versionado actual; R02 |
| Entrega básica | notificacion pendiente por fecha_envio NULL, ID estable y destino real | Eso no registra todos los reintentos/errores ni garantiza dedup de negocio; R09 puede requerir columnas, no nueva entidad automática |
| Código por alumno / feedback individual | Revisar campos/relaciones de participacion y retroalimentacion_docente | Ajustes académicos explícitos R03/R04; no presentes en el DBML fiel al original |

No se utiliza un JSON/mensaje/observación como sustituto opaco de rúbrica, roster o respuestas. Un campo de texto destinado a observación no puede simular autor/fecha/relaciones ausentes sin reconocer el cambio semántico.

## 4. Reglas y límites no resueltos por el conteo

- RN-11 exige última selección por pregunta; no exige una tabla nueva de historial. El ER permite registros múltiples, el dominio actual una selección vigente: se necesita contrato de persistencia.
- RN-14 indica evaluación parcial al vencer; VENCIDO es estado temporal, no nota cero ni catálogo INCOMPLETA.
- RN-15 exige incluir ausentes y ceros por pregunta; el esquema de resultados por intento no debe forzarse creando intentos ficticios.
- RN-17 exige rúbrica de la referencia utilizada: conservar contenido/versiones actuales durante reconciliación, no usar la última rúbrica disponible.
- RN-20 mantiene RF-22 pendiente. RN-21/22 eran propuestas; no se implementan como políticas aprobadas por tener campos estado.
- RNF-04/05/10 requieren transacción/reloj/integridad. PK/FK no sustituyen locking, acceso o política.
- RNF-06/12 de entrega/auditoría no quedan completos en fecha_envio/lectura ni en una fila de mensaje; evaluar R09 sin crear automáticamente evento_salida.

## 5. Verificación prevista, no ejecutada

| Tipo de evidencia futura | Qué debe demostrar |
|---|---|
| Unitarias/fakes | Estado/tiempo, política ausente, clasificación, permisos, contratos de ruta y no fuga de corrección |
| HTTP/TestClient | JWT/rol/titularidad, código ajeno, estado finalizado, tolerancia no manipulable, resultado prematuro y API revisada |
| SQLite | Repositorios portables y transacciones básicas; no sustituye PostgreSQL |
| PostgreSQL efímero autorizado | Migraciones/metadata, PK/FK/UQ/CK, precisión, zona, rollback y dos conexiones para concurrencia |
| Conciliación de datos | Versiones y dueños sin pérdida, roster real, mapeo completo y referencias externas conservadas |

**En BD-1.2 no se ejecuta ninguna prueba.** 1061 aprobadas y 38 omitidas (más 199 específicas de 8A en su fase) son línea base histórica del usuario. Las omitidas no son aprobadas y no se afirma que este rediseño haya pasado la suite.
