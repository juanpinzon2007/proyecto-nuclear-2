# Auditoría de cobertura y siguiente incremento — 5 de noviembre de 2026

> Corte vigente 11/11, candidato acelerado. 21 IMPLEMENTADO, 6 PARCIAL y 0 BLOQUEADO en la matriz de implementación. Aceptación Postman 21 APROBADOS y 6 BLOQUEADOS en laboratorio. Véase CANDIDATO_INTEGRADO_20261111.md. Las secciones fechadas anteriores conservan resultados históricos, no nuevas ejecuciones.

Repositorio original, rama `feature/backend-continuidad`, HEAD
`ac92b7251c96f81ddcb6f390ef21435ab74b6131`, más cambios locales preservados.
Este documento distingue requisito completo de capacidad técnica aislada.

> Actualización RF-19 del 5 de noviembre de 2026: el defecto de doble cierre está corregido y acreditado; ver sección 10. Se conservan los resultados históricos de la auditoría y de RF-27.

> Actualización posterior de consistencia: los avisos internos de inicio/fin
> comparten ahora la transacción de estado/auditoría. Ver sección 11; no se
> implementó outbox ni se acreditó correo. Los cortes anteriores se conservan.

> Actualización RF-19 operativo: sección 12. Proceso independiente y periodicidad
> real acreditados en PostgreSQL17; la matriz distingue implementación de despliegue.

## 0. Registro de selección previo a modificar código

Inicialmente se consideró un incremento acotado de **RF-19 / RNF-04 / RNF-10 / RNF-12**:
comprobar y, solo si se reproduce el defecto, proteger las transiciones de sesión
contra estados obsoletos precargados en el identity map de SQLAlchemy. Un cierre
confirmado no puede repetirse ni producir otra auditoría o cambiar su fecha.
Se reutilizan State, `cambiar_estado_sesion` y el worker existentes. No se crea
otro ejecutor, endpoint, permiso o mecanismo de eventos.

Criterios de aceptación registrados antes de implementar:

1. Reproducir con dos sesiones PostgreSQL independientes la lectura obsoleta y
   exigir rechazo de la segunda transición sobre el estado ya FINALIZADO.
2. Dos transacciones con el mismo estado precargado: un solo cierre confirmado,
   un rechazo de State y una sola auditoría de cierre.
3. El rollback del llamador conserva estado, auditoría y versión asignada.
4. El worker conserva la frontera vigente `fecha_fin + 24 horas <= ahora`, usando
   su reloj controlable y fechas equivalentes con distinto offset.
5. Las operaciones HTTP docentes legítimas siguen usando JWT y resolver reales,
   sin cabeceras de identidad alternativas. Los JWT de personal son emitidos por
   fixtures explícitas: no acreditan un login docente productivo.
6. No modificar Participation 9A/9B, esquemas, migraciones, políticas pendientes
   ni registro de rutas. Si la reproducción no falla, no se parchea por conjetura.

Esto no cierra por sí solo RF-19: el despliegue del proceso periódico y la entrega
recuperable de eventos después del commit son verificaciones independientes.

La selección definitiva es RF-27, según la repriorización inferior. La matriz y
los resultados finales están en las secciones siguientes. La evidencia inicial está en
`evidencias/auditoria_cobertura_20261105T051832Z/preservacion_inicial.json`.

### Repriorización antes de modificar producción

La reproducción RF-19 confirmó dos fallos (estado obsoleto y doble cierre).
Se conservan código y logs en `reproduccion_rf19.py` y
`pruebas_seguridad_20261105T052343Z` dentro de la carpeta de evidencia. Es un
defecto abierto, no una prueba aprobada. La primera ejecución había fallado en
la composición de la fixture: faltaba apuntar el Observer al laboratorio, sin
conectar ninguna base externa. Esos cuatro fallos también se conservan.

Antes de aplicar el parche se encontró una brecha superior en RF-27/RNF-02:
`POST /scheduling/calificaciones/notificar` acepta UUID arbitrarios, no verifica
resultado oficial ni titularidad y puede anunciar una calificación inexistente.
También usa UUID para participación mientras la persistencia real utiliza INTEGER.
Por prioridad de seguridad se selecciona **solo el cierre seguro de este emisor
HTTP de calificaciones**, sin implementar publicación oficial. RF-19 queda como
siguiente corrección técnica propuesta; no se cambia su código en este incremento.

Criterios previos del incremento finalmente seleccionado:

- JWT y rol docente siguen siendo obligatorios; sin token/rol, 401/403.
- Ni un docente propio ni uno ajeno pueden anunciar resultados sin el contrato
  oficial: 503 explícito, `Cache-Control: no-store`, sin DML ni commit.
- No aceptar el UUID del cliente como una relación comprobada ni convertirlo a
  INTEGER. No publicar notas ni añadir proveedor permisivo de laboratorio.
- Concurrencia y reintentos sobre esta ruta cerrada no generan avisos.
- Conservar bandeja, avisos de convocatoria y feedback individual existentes.
- Adaptar únicamente las dos pruebas previas que esperaban 201 sin comprobar
  resultado/ámbito, documentando la sustitución del contrato inseguro.

## 1. Fuentes, aprobación y discrepancias

Fuente central utilizada por el repositorio: `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`,
pp. 4–5: RF-01 a RF-27; p. 7: reglas de negocio. SHA-256 comienza por
`21501b8b1ab51922`. Es también la fuente declarada en `docs/bd/E_TRAZABILIDAD_RF.md`.
El usuario ha identificado estos 27 RF como alcance académico. No hay un acta
firmada/versionada disponible que permita certificar que el PDF incorpora todas
las aprobaciones posteriores. No se deduce vigencia de la fecha de modificación.

Se contrastaron además las otras dos fuentes locales:

- `Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf`, 38 páginas,
  SHA-256 `6af572e1a172ef3a…`: analiza los mismos 27 identificadores y patrones;
  sus propuestas arquitectónicas no prueban implementación ni agregan RF.
- `Agile Inception SPS.pdf`, 39 páginas, SHA-256 `b0206ee9c49e3140…`: interpreta
  los 27 RF y delimita decisiones negociables. No constituye aprobación de esos
  negociables. Tampoco acredita despliegue, rendimiento o disponibilidad.

Discrepancias que afectan la auditoría:

| Tema | Documentación central/derivada | Definición posterior y tratamiento actual |
|---|---|---|
| RF-10, RN-10/11 | Permite cambiar selecciones antes del cierre; Agile y análisis repiten ese texto | Profesora confirmó respuestas inmutables. Se audita la regla posterior; no se reabre PUT. Corregir texto académico por aprobación documental, no código. |
| RF-13/24 | No especifica toda la fórmula | Fuente posterior del usuario, §30: media uniforme por pregunta, ramas inaccesibles excluidas, perfiles equilibrados y ROUND_HALF_UP final. Cálculo y persistencia exacta acreditados (§31); lectura técnica docente privada en main (§32). Consolidación/ausencias/publicación siguen pendientes. |
| RF-26 | Valoración individual, sin precisión de edición | Usuario aprobó una valoración editable por participación. La persistencia/privacidad lo implementan. |
| RF-22 | Sala de espera y admisión congelada aprobadas por el equipo | Sin anticipación ni tolerancia tardía; ver sección 20. Consentimiento productivo no aprobado. |
| RF-27 | Aviso de notas y feedback | Feedback interno funciona; anunciar notas no está respaldado por publicación oficial. Se reproduce y cierra la ruta insegura en este incremento. |
| RNF-01 a RNF-14 | El PDF los denomina «propuestos» | Se evalúa evidencia frente a esos objetivos, sin presentarlos como SLA aceptados. |
| Historia técnica | Informes antiguos indican ausencia total de rutas Participation o contratos ya resueltos | Prevalece código actual: cuatro operaciones 9A en main y corrección RN-16 de 9B. No se reimplementan. |

RF-28/29 no aparecen en el catálogo académico local de 27: no se agregan ni se
consideran aprobados por referencias previas a Jira. No se ha consultado Jira en
esta ejecución. Extracciones completas, hashes y rutas están en la evidencia local.

## 2. Cómo interpretar el estado

- **IMPLEMENTADO**: comportamiento del RF demostrado con servicios reales,
  persistencia y composición HTTP existentes dentro del alcance definido, sin
  políticas sintéticas que concedan ese comportamiento.
- **PARCIAL**: parte comprobada, pero falta una operación, integración o garantía
  necesaria del RF.
- **BLOQUEADO**: existe trabajo técnico, pero una decisión/contrato indispensable
  impide completar su comportamiento sin inventarlo.
- **NO IMPLEMENTADO**: no hay realización verificable del requisito. No se usa
  como sinónimo de «sin despliegue» ni para borrar componentes ya desarrollados.

IMPLEMENTADO no certifica despliegue ni un recorrido de producto completo.
**Dependencia transversal de personal:** las pruebas docentes/administrativas
emiten JWT reales desde fixtures con cuentas/roles/asociaciones persistidos.
Eso acredita autorización, pero NO login de personal: el mecanismo contractual
de autenticación docente/administrativa sigue pendiente. Las capacidades docentes
clasificadas implementadas no están listas para un usuario final sin esa dependencia.
El login estudiantil sí tiene HTTP real correo/código. No hay aceptación sobre una
base permanente y no se conectó ninguna para esta auditoría.

Las referencias a tests existentes son inspeccionadas y contrastables con el JUnit
de 9B (2001/38), **una ejecución anterior**, no una nueva ejecución de todos ellos.
La sección de validación separa los tests efectivamente ejecutados en esta entrega.

## 3. Matriz individual de los 27 RF

Rutas de código relativas a `backend/app/modules/`; tests relativos a `backend/`.
PG significa PostgreSQL desechable real, no una base compartida. Los nombres de
pruebas se verifican en el código; los parámetros concretos figuran en el JUnit.

| ID y descripción | Responsable / implementación y persistencia | Endpoint o servicio; registro en main | Estado | Prueba identificable y alcance | Dependencia / próxima acción y aceptación |
|---|---|---|---|---|---|
| RF-01 Autenticar estudiantes | Identity: `application/authentication.py::ServicioAutenticacion.autenticar_estudiante`, `infrastructure/scheduling_access.py::ValidadorConvocatoriaScheduling`; usuario, identidad_academica, convocatoria/sesión | POST `/api/v1/identity/auth/estudiantes`, GET `/api/v1/identity/me`; sí | IMPLEMENTADO | `tests/identity/test_student_login_scheduling.py::test_flujo_login_autorizado_jwt_y_notificaciones_reales`; SQLite/PG, sin password inventado | Configurar dominios/JWT en despliegue; login no autoriza ingreso ni crea intento. Aceptación: correo/código propios, rol y cuenta actuales, contexto legítimo. |
| RF-02 Controlar rol y permiso específico de crear casos | Identity: obtener_usuario_actual, ServicioAutorizacion, ServicioAutenticacion.autenticar_personal; roles/permisos SQL; Cases exigir_permiso_creacion_configurado | POST `/api/v1/identity/auth/personal`, /me y dependencias Cases registradas | IMPLEMENTADO | `tests/integration/test_main_staff_login.py::test_login_real_no_otorga_casos_ajenos_ni_permisos_eliminados` y `test_estado_y_rol_persistidos_se_revalidan_despues_del_login`; HTTP main/JWT real/PG17 | Acreditado en el alcance vigente de permisos por rol, sin conceder permisos individuales ni vínculos académicos. Login autorizado por decisión del equipo; políticas operativas institucionales pendientes. Sección 16. |
| RF-03 Administrar docentes, roles y permisos | Identity, UoW y rol_permiso global; cuenta y rol revalidados con locks | GET/PUT /api/v1/identity/roles/docente/permisos y alta/listado/autorizaciones existentes en main | IMPLEMENTADO | test_global_teacher_permissions.py, test_admin_write_authorization.py; Newman 26 HTTP y 85 aserciones | Permisos globales DOCENTE confirmados por el responsable funcional. Actualización atómica, tokens existentes revalidados, concurrencia y rollback acreditados. Concesiones individuales y roles compuestos conservan sus contratos. |
| RF-04 Asociar espacio y estudiantes | Scheduling/Identity, asignacion_caso y convocatorias en la misma UoW | POST /scheduling/sesiones con grupo_id, estudiantes_ids y fecha_limite_ingreso; main | IMPLEMENTADO | test_academic_assignment_programming.py y test_assignment_mail_composition.py; Newman 14 HTTP y 46 aserciones | Contrato del equipo confirmado, límite aware explícito dentro del horario, intentos_base=1 y estado programada. Grupos, matrículas y grants administrativos preexistentes. La asignación y convocatorias se crean por API sobre la misma sesión. |
| RF-05 Registrar estructura del caso | Cases: `CasoService.crear_borrador`, `ConstructorCaso`; caso/version_caso/escenario, estimado e historia | POST/PUT `/api/v1/cases[/{version_id}]`; sí | IMPLEMENTADO | `tests/integration/test_cases_graph_authoring.py::test_http_crear_configurar_publicar_y_consumir_misma_version` PG, contenido por API | Login personal real acreditado; configurar cuentas/JWT institucionales para despliegue. La preparación de nuevas ediciones históricas por ORM en algunos tests NO acredita un endpoint de nueva edición. |
| RF-06 Contextos y preguntas por escenario | Cases: `CasoPayload`, `CasoService._construir`, escenario/pregunta | POST/PUT/GET `/api/v1/cases`; sí | IMPLEMENTADO | Mismo test HTTP PG de autoría; `tests/unit/cases/test_builder.py` valida construcción | Autoría guarda estructura; ejecución multipregunta sigue bloqueada y se clasifica en RF-10. No confundir guardar una lista con poder navegarla. |
| RF-07 Preguntas y alternativas correctas/incorrectas | Cases: `OpcionSchema`, Builder/validadores; pregunta/opcion_respuesta.es_correcta | DSL JSON y detalle en `/api/v1/cases`; sí | IMPLEMENTADO | Autoría HTTP PG anterior y `tests/unit/cases/test_validators.py` | Mantener varias alternativas; una selección por pregunta en Participation no significa una sola alternativa disponible. Aceptación: flags y referencias se recuperan fielmente. |
| RF-08 Justificar cada alternativa | Cases: OpcionSchema.justificacion y validadores; opcion_respuesta | DSL autoría y detalle docente; sí; explicación al estudiante todavía condicionada a RF-14 | IMPLEMENTADO | `tests/integration/test_evaluation_feedback.py::test_respuesta_incorrecta_usa_su_justificacion_no_la_de_otra_opcion` PG; validadores | Registro académico sí. No confundir este RF con publicación estudiantil de nota/explicación final. |
| RF-09 Borrador, validar/publicar y archivar | Cases: `CasoService.publicar/archivar`, cadena validación, repositorio de grafo/guards PG | POST `/api/v1/cases/{version_id}/publish` y `/archive`; sí | IMPLEMENTADO | Autoría HTTP PG; `tests/integration/test_cases_guard_migration.py::test_revision_real_preflight_DML_locks_downgrade_y_reupgrade` | Recorridos soportados: una pregunta/escena y sin ciclos alcanzables. No rellenar grafos históricos ficticios; decidir semántica de recorridos pendientes para ampliar publicación ejecutable. |
| RF-10 Consultar contextos y responder; aclaración posterior INMUTABLE | Participation/Cases: `current_scenario.py`, grafo SQL y Facade; intento/paso_simulacion y guard PG | GET `/api/v1/attempts/{id}/current-scenario`, POST `/decisions/{decision_id}`; sí. PUT no montado | PARCIAL | `tests/integration/test_main_decisions.py::test_primer_registro_inmutable_progreso_y_siguiente_escenario_main` PG/JWT real | Funciona para intento existente y grafo soportado. Inicio productivo bloqueado; faltan decisiones sobre varias preguntas/ciclos/revisitas. Actualizar RF documental para no pedir edición prohibida. |
| RF-11 Guardar respuestas y progreso privado sin revelar corrección | Participation: repositorio/UoW, `progress_query.py`, `progress.py`; paso_simulacion único por intento/pregunta | POST decisiones y GET `/api/v1/attempts/{id}/progress`; sí | IMPLEMENTADO | `tests/integration/test_main_progress.py::test_progreso_efectivo_repetido_sin_dml_flush_commit`; `test_main_decisions.py::test_registros_concurrentes_conservan_una_sola_seleccion` PG | GET proyecta vencimiento sin persistir; escritura separada. Requiere zona histórica explícita y un intento ya existente. No autoriza inicio productivo. |
| RF-12 Inicio/fin, nota y feedback por pregunta | Participation start/provision, admisión SQL en la misma UoW, consentimiento versionado/evidencia P→C y API aislada; Evaluation técnica | Operaciones de intentos existentes y resultado oficial privado; consentimiento e inicio en main condicionados a puertos obligatorios, cerrados sin aprobación/políticas. Provisión independiente no registrada | PARCIAL | test_lab_student_journey.py: 2 E2E nuevos, main + composición aislada sin overrides de auth; aceptación actual 13 y relacionada 682, 0 fallidas/errores. General 2224/38 es histórica. RECORRIDO_ESTUDIANTIL_INTEGRAL_LAB.md | Resuelta la composición técnica de concesión/consentimiento antes de INSERT P y creación P/I atómica. Faltan documento/proceso institucional y composición productiva obligatoria de inicio. Publicación de resultados válidos disponible por autorización expresa (§34); sin recuperación inventada. |
| RF-13 Calcular y almacenar nota por rúbrica | PREGUNTAS_100_V1: Strategies y calculador existentes, versión histórica, detalle exacto y persistencia canónica | GET/POST /scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico en main; docente autorizado | PARCIAL | Nueva Fase6: 39 focales, 108 relacionadas, Newman RF13 32/141; PostgreSQL17, JWT, concurrencia/rollback. No sumar suites | Tramo técnico acreditado. Conciliar UC05/disparador docente y política aplicable a otras rúbricas/alcance; no convertir legado con 503 en calificación ni exigir publicación como parte de RF13. Ver RF13_AUDITORIA_Y_DTO_PROGRAMACION_20261110.md. |
| RF-14 Mostrar nota/aciertos/errores/explicaciones tras cerrar | Consulta privada del titular, provisional configurable y snapshot oficial; feedback exacto de selecciones históricas, sin correcciones durante sesión activa | GET /scheduling/convocatorias/{convocatoria_id}/resultado en main; visibilidad/publicación docentes separadas | IMPLEMENTADO | Nueva Fase7:13 aceptaciones específicas,180 relacionadas,general2538/38; Newman RF14:19/68; RR/READ ONLY, JWT/PG17 y feedback correcto/incorrecto | Consumidor acreditado para resultados válidos existentes; no aprueba productor RF13 ni inicio/asignación. Resultado cerrado sin cálculo corregido a404 sin escritura. Ver RF14_CIERRE_CONTROLADO_20261110.md y RF14_CONTRATO_ANGULAR.md. |
| RF-15 Seguimiento docente por estudiante y caso | Identity `infrastructure/followup.py::ConsultaSeguimientoSQLAlchemy`, ProxySeguimiento y servicios existentes; joins P/I/pasos/feedback | Tres GET `/api/v1/identity/seguimiento/casos`, `/casos/{id}/participaciones`, `/participaciones/{id}` en main | IMPLEMENTADO | Pruebas históricas de `test_teacher_followup_http.py` y 11 casos actuales PG17 sobre main en `test_main_teacher_followup.py`: recorrido, versión histórica, privacidad, ámbito, concurrencia y cero DML/flush/commit; sección 14 | Lectura sin commit acreditada; no publica notas ni RF-16. Login personal sigue pendiente y JWT docente de aceptación se emite solo dentro del laboratorio. No equivale a integración productiva completa desde credenciales. |
| RF-16 Descargar resultados, parciales y ausentes | ServicioReporteOficial, ConsultaReporteOficialSQLAlchemy y exportadores openpyxl/ReportLab; snapshot oficial verificado por CicloAcademicoSQL, sin recalcular | GET `/api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte?formato=xlsx` o `pdf`, main | IMPLEMENTADO | `test_official_reports_http.py`: 21 casos PG17/JWT real, archivos leídos, versiones, ausencias/retiros, máximo, autorización y cero DML/flush/commit; §35 | Publicación oficial previa indispensable. Filtros por grupo, estudiante y estado; orden estable; versión de publicación seleccionable. Retiradas como identificadores históricos sin nota, sin inventar nombres ausentes de la fuente; CSV sin formato conserva 503. |
| RF-17 Registrar/asociar rúbrica | Cases: ConstructorCaso, `rubrica`, `criterio_rubrica`, `nivel_rubrica`, `valoracion_opcion` por versión | DSL `/api/v1/cases`; sí | IMPLEMENTADO | Autoría HTTP PG y `tests/integration/test_evaluation_persisted.py::test_evidencias_historicas_reales_sin_calificacion` | Historia preservada; ponderación efectiva igualitaria aprobada no reescribe rúbricas anteriores. La semántica de puntajes para evaluar sigue pendiente en RF-13. |
| RF-18 Programar horarios, duración, lugar y mensaje con caso publicado | Scheduling `programming_access.py::programar_sesion_autorizada`; docente_espacio_academico/sesion_programada con versión UUID exacta | POST `/scheduling/sesiones`, GET listado/detalle; sí | IMPLEMENTADO | `tests/integration/test_session_programming_http.py::test_programacion_autorizada_persiste_datos_y_uuid_de_scheduling`, `test_publicacion_posterior_no_sustituye_uuid_de_version_programada` PG | Grants son administrativos, no autovinculación; login personal acreditado en main, sin conceder grants implícitos. No se deduce autorización de matrícula ni RF-22 de programar una sesión. |
| RF-19 Estados de sesión y cierre automático +24h | Scheduling State, coordinador transaccional, Observer SQL y worker_runner; evento_auditoria/notificacion | POST `/scheduling/sesiones/{id}/estado` en main; cierre automático en proceso separado/perfil worker optativo | IMPLEMENTADO | Diez casos PG17 de State, seis de atomicidad y cuatro nuevos de proceso real en `test_worker_process.py`, incluidos dos ciclos separados por 60 s, fallo/reintento y competencia de procesos; sección 12 | Comportamiento funcional acreditado sin dobles en los procesos. Activar/supervisar el worker es una condición de despliegue: no arranca dentro de main ni se instaló en un servidor permanente. Callbacks externos/correo siguen fuera de esta garantía |
| RF-20 Código individual y validación/notificación | Scheduling, hash de acceso, notificacion y despacho_correo cifrado | POST convocatorias, login estudiantil y validación existentes; CLI mail_delivery | IMPLEMENTADO | test_durable_mail.py; Newman 17 HTTP y 57 aserciones con SMTP TCP local y SQL | Código único entregado al docente en el POST autorizado, cifrado durable para despacho, titular SQL y código verificados. Aceptación por capturador real acreditada. Configuración y entrega del proveedor externo pendientes de despliegue. |
| RF-21 Correo convocatoria/altas/retiros | Cola cifrada asociada al aviso canónico, SMTP configurable y recuperación | POST/DELETE convocatorias y GET notificaciones existentes en main; despacho CLI | IMPLEMENTADO | test_durable_mail.py, test_assignment_mail_composition.py; Newman 17 HTTP y 57 aserciones | Alta y retiro llegan al capturador correcto, reintentos y cancelación seguros, rollback transaccional. SMTP aceptado antes del commit puede repetirse tras una caída. El despliegue requiere proveedor, remitente, URL y custodia de clave. |
| RF-22 Restringir ingreso tardío | Scheduling admission.py, coordinador RF-19, JWT/matrícula/asignación SQL y versión histórica | POST /scheduling/convocatorias/{id}/espera; GET /scheduling/convocatorias/{id}/admision; POST /scheduling/validar-ingreso; sí en main | IMPLEMENTADO | 32 aceptaciones main/JWT real/PG17, test_waiting_admission.py; regresión focal 606 sin fallos. Sección 20 | Cumplido para sala aprobada, concesión previa y recuperación, no presencia online. No habilita P/I ni consentimiento productivo. Despliegue de migración aún no realizado. |
| RF-23 Tiempo individual máximo y conservación | Intento, reloj inyectado, snapshot duracion_concedida_segundos, cierre y guards | Operaciones 9A sí; nuevo inicio en main condicionado, bloqueado sin aprobación/políticas | PARCIAL | `tests/integration/test_main_finish.py::test_cierre_confirma_vencimiento_que_get_no_persistio`; `tests/integration/test_attempt_start.py::test_inicio_real_y_segunda_session_con_version_y_duracion` PG, inicio LAB | Rechazo por tiempo y respuestas conservadas sí; aprobar inicio y coordinación con fin de sesión. Proyección VENCIDO no equivale a transición persistida ni nota PARCIAL. |
| RF-24 Incompletos y ausencias | VENCIDO y FINALIZADO sin FIN como resultados parciales; ausencia docente explícita y rectificación durable sin intentos ficticios. | POST ausencia/rectificacion y GET consolidacion en Scheduling/main; guard SQL de historia | PARCIAL | test_voluntary_partial_http.py y test_academic_cycle_http.py; PG17, SQL, concurrencia/rollback y publicación explícita. | Fase9: parcial/ausencia verificados; 116 focales/180 relacionadas y Newman18HTTP/62aserciones, sin sumar. Pendientes compartidos con RF13: alcance de rúbricas y disparador UC05; v2 voluntaria conserva procedencia propuesta. Ver RF24_CIERRE_CONTROLADO_20261110.md; no hay ausencia automática. |
| RF-25 Repetición solo por creador y nunca sesión finalizada | Proxy/ServicioExcepciones y permiso_intento_extra nativo reutilizados; cupo uno y fecha original en replay; guard SQL de consumo | POST /api/v1/identity/excepciones/repeticiones y composición de inicio en main; inicio productivo cerrado por políticas obligatorias | PARCIAL | test_repeticion_http_reutiliza_permiso_nativo_idempotente; test_mejor_nota_misma_participacion_no_mezcla_otro_caso; rechazo de cupo base sin permiso [1/2]; PG17 | Permiso individual verificable, creador real, sesión EN_CURSO y anteriores cerrados. Inicio extra productivo depende de consentimiento oficial/composición segura. Distinto caso separado hasta vínculo explícito; no concesión por cupo implícito. |
| RF-26 Valoración individual editable y privada | Participation `individual_feedback.py`, Identity seguimiento; UNIQUE retroalimentacion_docente.id_participacion, aviso atómico | POST/GET `/api/v1/identity/seguimiento/participaciones/{id}/feedback`; sí | IMPLEMENTADO | `tests/integration/test_teacher_followup_http.py::test_feedback_se_crea_edita_y_recupera_sin_duplicar_desde_otra_sesion`; `test_student_general_feedback_http.py::test_titular_lee_actualizacion_confirmada_sin_escrituras_ni_notas` PG | Respeta visibilidad: al menos un intento y todos cerrados. Falta decisión de entrega en ausencia sin intento; no cambiarla silenciosamente. Login personal disponible; conserva autorización individual del recurso. |
| RF-27 Avisos de nota y feedback | Reutiliza Notificacion INTERNA; publicación, auditoría y aviso por titular en la misma UoW; UQ causal e idempotencia | POST publicaciones y GET bandeja registrados en main; antigua /calificaciones/notificar sigue cerrada y no se usa como bypass | IMPLEMENTADO | test_publicacion_explicita_idempotente_y_lectura_privada; test_publicaciones_concurrentes_no_duplican_efectos; test_fallo_aviso_revierte_publicacion_y_auditoria y regresión de feedback real | Avisos internos acreditados para publicación explícita y feedback. No se afirma correo enviado ni entrega externa exactamente una vez; proveedor de correo corresponde a RF-21. |

### Lectura cuantitativa sin porcentajes inventados

La clasificación actual contiene **21 IMPLEMENTADO, 6 PARCIAL y 0 BLOQUEADO**;
ningún RF está enteramente sin componentes. No hay pesos de esfuerzo aprobados
para convertir esas categorías a un porcentaje global. **21/27 = 77,8 %** es
únicamente la proporción de RF con comportamiento acreditado bajo la definición
anterior, no un porcentaje de código, despliegue ni recorridos de producto cerrados.
Los requisitos acreditados siguen sujetos a las dependencias transversales expresadas. El login
de personal ya tiene aceptación HTTP SQL, sin certificar su operación institucional.
La estimación conversacional previa de 80–85 % era
orientativa sobre construcción técnica; esta auditoría no la certifica como
cumplimiento contractual y no debe emplearse como cifra de aceptación.

## 4. Estado por módulo y disponibilidad (corte histórico; ver tabla RF y §34 vigentes)

| Módulo | Real y reutilizable | Falta / límite de disponibilidad |
|---|---|---|
| Identity | Login estudiantil, JWT, roles/permisos vigentes, resolver SQL, proxies, seguimiento/feedback y administración parcial | Login personal contractual; alta de asociaciones/matrículas autorizada; permisos solo por rol en modelo actual; reportes/excepciones cerrados |
| Cases | Autoría HTTP protegida, DSL, rúbrica, grafo, publicación/archivo, lectura histórica, guards PG | Login docente; flujo público de nuevas ediciones no demostrado; semántica multipregunta/ciclos/revisitas pendiente. No se reemplaza versión asignada |
| Scheduling | Programación con grants explícitos, convocatorias/retirada, avisos internos, bandeja, State y worker | Entrega real de correo/códigos; despliegue worker; cierre único RF-19 y avisos SQL atómicos acreditados; callbacks externos sin recuperación durable; ingreso RF-22 y avisos oficiales de nota cerrados |
| Participation | P/I/pasos persistidos, provisión/inicio atómicos condicionados, cuatro operaciones privadas 9A en main, respuestas inmutables | Tres proveedores de inicio sin aprobación (ingreso/vinculación/inicio), más reglas de consentimiento/repetición. Provisión/inicio de convocatoria no registrados |
| Evaluation (dentro de Participation) | Strategy, calculador, escala 100/pesos iguales/ceros confirmados, resultados técnicos y procedencia verificable | No hay política completa ni publicación oficial; consolidación resultado_participacion y ausencia oficial pendientes. Las definiciones de laboratorio siguen identificadas |

OpenAPI real de `app.main`, generado sin conectar BD: **29 paths distintos**, 31
tablas ORM registradas. El número de paths no es el número de RF terminados.
`evidencias/.../rutas_main.json` enumera métodos y tablas. Además de las rutas
compuestas, hay servicios/factories aislados; no se registró ninguno nuevo.
No se comparó el esquema físico de una base permanente y no se afirma que esté
migrada. El ER académico original de 28 entidades se conserva; el esquema técnico
actual no se presenta como un conteo físico de exactamente 28 tablas.

## 5. Requisitos no funcionales disponibles

Los catorce son objetivos **propuestos** de la fuente central, no SLA certificados.

| RNF | Objetivo | Evidencia actual / tipo | Evaluación y aceptación faltante |
|---|---|---|---|
| 01 | Proteger códigos/secretos y no registrarlos | Hash de códigos, SecretStr/JWT, tests de login y logs de laboratorio redactados | PARCIAL: hash verificado; faltan pruebas operativas de gestión/rotación de secretos y revisión de logging/despliegue completo. No imprimir .env |
| 02 | Autorizar rol/permiso/ámbito en servidor | Identity real y aceptación PG de Cases, Scheduling, seguimiento; cierre RF-27 de esta entrega | PARCIAL: bloqueo de publicación remedia brecha demostrada; falta contrato login personal y revisión de cada futura ruta. Un Bearer válido no concede alcance universal |
| 03 | Privacidad por estudiante/docente | Tests main 9A, seguimiento y feedback privado, consultas SQL autorizadas | PARCIAL en sistema global: garantías fuertes en operaciones acreditadas; reportes/ausencias/publicación oficiales no disponibles. Sin prueba de despliegue |
| 04 | Persistencia transaccional y rollback | UoW, locks, rollback y concurrencia PG en respuestas/inicio/feedback/convocatorias | PARCIAL global: RF-19 confirma cierre/auditoría/avisos SQL atómicamente; callbacks externos no durables. No generalizar garantías de un módulo a todos |
| 05 | Tiempo del servidor confiable | Relojes inyectados, zona sin default, proyección de vencimiento sin escribir y snapshots | PARCIAL: RF-22 y coordinación de plazos sin aprobación; ninguna prueba del reloj del navegador amplía derechos |
| 06 | Envío/fallo/reintento sin duplicados indebidos | Avisos de sesión atómicos; convocatorias transaccionales, feedback deduplicado y retiro idempotente | PARCIAL: correo y recuperación universal pendientes. El fallo del Observer SQL revierte ahora la transición; un callback efímero postcommit aún puede fallar. PENDIENTE no acredita entrega externa |
| 07 | Propuesta 25 concurrentes, p95 ≤2s | Tests de carreras comprueban integridad, no percentiles de latencia | NO ACREDITADO: acordar carga/entorno y medir; no usar el tiempo total de pytest como benchmark |
| 08 | Reporte filtrado/paginado con participantes, parciales y ausentes | Serializador CSV con escape de celdas y pruebas con dobles | BLOQUEADO/PARCIAL: roster y calificación/consolidación pendientes; adaptador oficial y paginación no acreditados |
| 09 | Usabilidad/accesibilidad de preguntas, tiempo y errores | Contratos HTTP, DTOs privados y errores; sin frontend en esta tarea | NO ACREDITADO integralmente: requiere aceptación UI/teclado y criterios acordados. No se inició frontend |
| 10 | FK, pertenencia, unicidad e integridad histórica | Migraciones/guards/constraints de PG, 31 modelos, pruebas UUID/FK/duplicados/rollback | PARCIAL global: estado obsoleto RF-19 corregido; la conciliación académica/física y escrituras SQL fuera de los servicios no quedan certificadas por ello. Constraints no equivalen a todas las políticas |
| 11 | Modularidad y pruebas | Cinco responsabilidades, puertos/UoW, Builder/Chain/State/Observer/Strategy/Facade/Proxy existentes | PARCIAL: buena base verificable; application Cases importa schemas API y varios adaptadores cruzan ORM de módulos. Registrar deuda sin refactorización general ni alterar patrones |
| 12 | Trazar roster, permisos, inicio/cierre, notas y feedback sin secretos | Auditoría de estados, snapshots, procedencia versionada de resultado, feedback editable | PARCIAL: sin historial completo de feedback (cardinalidad aprobada: una editable) ni correlación universal de cambios/permisos. Duplicación RF-19 corregida, sin certificar trazabilidad global |
| 13 | Compatibilidad Chrome/Edge/Firefox escritorio/móvil propuesta | TestClient acredita HTTP, no motores de navegador | NO ACREDITADO: aceptación de frontend y matriz de versiones/entornos. No se navegaron ni certificaron browsers |
| 14 | Propuesta reporte 100 convocados ≤5s o entrega paginada | No hay generador oficial completo ni medición de carga | BLOQUEADO/NO ACREDITADO: completar RF-16 y luego medir; no inventar resultados de rendimiento |

## 6. Priorización y criterios de los siguientes trabajos

| Prioridad | Trabajo | Naturaleza / dependencia | Aceptación concreta |
|---|---|---|---|
| P0 — este incremento | Cerrar emisor HTTP de avisos de nota no verificados RF-27 | Técnica, independiente de 9B; defecto reproducido en main/PG | 401/403 sin identidad/rol; 503 con docente válido; cero DML/commits, también bajo concurrencia; avisos de feedback/convocatoria intactos |
| REALIZADO — actualización RF-19 | Refrescar estado bajo lock antes de State | Técnica; dos fallos PG reproducidos y corregidos, con diez casos PG acreditados | Una transición/auditoría, conservación del fin previo, rollback, frontera +24h y carrera docente/worker. Resultados negativos previos conservados; sección 10 |
| P1 — dependencia de producto | Contrato de autenticación docente/admin y gestión autorizada de datos académicos | Equipo/Identity: decidir mecanismo, bootstrap, provisión de asociaciones/grants y cuentas | Flujo real login personal→crear caso→programar→matricular/asignar/convocar sin emitir token manual ni insertar permisos SQL en pasos funcionales |
| P1 — en paralelo, aprobación | Políticas ingreso, consentimiento/revocación, provisión e intento extra | Profesora/responsable académico; 9B | Definición versionada y verificable, proveedores existentes sobre misma UoW; luego aceptar creación P/I por main, sin proveedores LAB |
| P2 | Mapeo y agregación de evaluación/ausencias/consolidación | Aprobación académica y contrato de roster | Resultado oficial reproducible con rúbrica histórica, ausencia sin intento ficticio y consolidación explícita; después RF-14/16/27 oficiales |
| P2 | Entrega recuperable de correo RF-21 | Infraestructura/proveedor y diseño de transporte seguro de código | Commit anterior al aviso externo, fallo/reintento verificable, URL/remitente confiables y destinatario correcto; sin secreto en logs o mensaje persistido en claro |
| P2 | Recuperación durable de eventos de estado | Contrato técnico de entrega/almacenamiento; no inventar tabla fuera de autorizaciones | Fallo tras commit no pierde evento, reintento no duplica aviso; distinguir de rollback de persistencia |
| P3 | Medir RNF de rendimiento, compatibilidad y operación | Criterios aceptados/entorno representativo | Reportes p95, carga 25/100 según aprobación, métricas reales y aceptación UI; no equivalencia con cantidad de tests |

### Decisiones para la profesora

1. Ingreso: base del umbral, minutos/autoridad y frontera inclusiva/exclusiva;
   tiempo individual disponible si excede el fin de sesión.
2. Consentimiento: aplicabilidad, versión vigente, autoridad que la publica y
   efecto temporal de revocación. No fabricar aceptación para cumplir NOT NULL.
3. Provisión: creación con el primer intento o previa; estado inicial y alcance
   de la operación independiente.
4. Repetición: número, vigencia, consumo y condiciones del permiso excepcional.
5. Recorrido: varias preguntas por escena, elección de transición, destinos
   contradictorios, ciclos y revisitas. Inmutabilidad de respuestas ya confirmada.
6. Evaluación: nivel→logro, agregación preguntas→criterio, cierre voluntario
   incompleto, precisión/redondeo necesario; no reabrir escala/pesos aprobados.
7. Ausencias: autoridad/fuente para confirmarlas, aplicación del mapeo y persistencia
   sin intento; consolidación de varios intentos. Precisar visibilidad de feedback
   cuando nunca hubo intento, sin cambiar una valoración editable por participación.
8. Inicio de convocatoria histórica cuya versión se archivó después: aclarar
   alcance frente a prohibición de nuevas programaciones; conservar lectura histórica.

El mecanismo de login personal, proveedor de correo, secretos, URL institucional,
protocolo de reintentos y medición de SLA son decisiones técnicas/operativas del
equipo; no deben mezclarse con las fórmulas académicas.

## 7. Incremento efectivamente implementado y pruebas

Se implementó exclusivamente el cierre seguro del emisor HTTP de notas de
Scheduling. No se creó un publicador alternativo. Antes, dos UUID cualesquiera
y rol DOCENTE bastaban para persistir un aviso de «evaluación disponible», aun
sin participación, resultado oficial o ámbito comprobado. La reproducción usó
`app.main.app`, JWT y resolver/roles SQL reales, PostgreSQL17 desechable.

Ahora la ruta exige la autenticación/rol existentes y responde **503**, con
`Cache-Control: no-store`, sin DML ni commits. OpenAPI declara 503, no 201.
No devuelve ni publica una nota. El contrato de entrada legado conserva sus
tipos: no se convierte un UUID a INTEGER. El helper interno genérico
`application/notificar_calificacion.py` se conserva, pero ya no tiene ningún
llamador bajo `backend/app` que exponga este envío mediante HTTP. Eso no lo
convierte en un servicio de publicación oficial verificado.

La reapertura requerirá resultado oficial persistido/publicable, ámbito docente,
destinatario derivado de relaciones reales y contrato de ID compatible, dentro de
un límite transaccional y de entrega definido. Ninguno se infiere de los IDs
enviados por el cliente. No afecta los avisos ya autorizados de feedback o roster.

### Ejecuciones reales de esta entrega

| Ejecución / evidencia dentro de `evidencias/auditoria_cobertura_20261105T051832Z/` | Aprobadas | Omitidas | Fallos | Errores | Advertencias / interpretación |
|---|---:|---:|---:|---:|---|
| `pruebas_seguridad_20261105T052220Z` | 0 | 0 | 4 | 0 | 1; preparación RF-19 incompleta: faltó inyectar la fábrica SQL propia al Observer; no se utilizó la base externa |
| `pruebas_seguridad_20261105T052343Z` | 2 | 0 | 2 | 0 | 1; reproducción válida de RF-19: cierre obsoleto y dos cierres concurrentes; defectos abiertos en ese corte histórico, corregidos posteriormente en sección 10 |
| `pruebas_seguridad_20261105T052634Z` | 3 | 0 | 3 | 0 | 1; reproducción del emisor de notas inseguro: devolvía 201 y persistía avisos |
| `pruebas_seguridad_20261105T052739Z` | 6 | 0 | 0 | 0 | 1; cierre HTTP corregido, antes del ajuste final de OpenAPI |
| `pruebas_focal_20261105T053158Z` | 244 | 0 | 0 | 0 | 1; primera regresión relacionada, antes de ajustar OpenAPI |
| **`pruebas_focal_20261105T122422Z`** | **244** | **0** | **0** | **0** | **1; regresión FINAL, incluido contrato OpenAPI 503; 202.20 s** |

No se suman ejecuciones solapadas. Los **2001 aprobados y 38 omitidos de 9B son
históricos** y no se atribuyen a esta versión modificada. No se repitió la suite
general; se ejecutó la regresión relacionada autorizada. La advertencia actual
es Starlette/TestClient-httpx. Ninguna omisión externa se transforma en aprobado.

Composición de los 244 tests finales:

| Grupo | Casos | Qué acredita / límite |
|---|---:|---|
| `test_grade_notice_closed.py` | 6 | main, JWT/roles/resolver reales, PG17 propio; dos docentes, estudiante, anónimo, token inválido, concurrencia/reintento y ausencia de DML/commit; JWT docente emitido por fixture |
| `unit/scheduling/test_api_endpoints.py`, `test_api_security.py`, `test_notificar_calificacion.py`, `test_crear_notificacion.py` | 28 | Unitarias/HTTP con dobles; no se presentan como persistencia PostgreSQL |
| `test_academic_identity_security.py` | 44 | JWT real, vínculos/servicios/Session con mocks; no PG |
| `integration/scheduling/test_scheduling_endpoints.py` | 1 | Recorrido con SQLite aislado, no proveedor externo ni publicación de notas |
| `test_convocation_management_http.py` | 20 | Roster/retiro/avisos autorizados, JWT y PG real |
| `test_student_general_feedback_http.py` | 20 | Consulta privada/aviso de feedback, JWT y PG real |
| `test_teacher_followup_http.py` | 20 | Seguimiento/feedback docente sobre relaciones SQL reales |
| `test_main_finish.py` | 10 | Cierre y privacidad 9A; políticas de preparación de inicio identificadas como LAB |
| `test_evaluation_persisted.py` | 53 | SQLite/PG y motor existente; reglas académicas positivas sintéticas, no notas oficiales |
| `test_evaluation_result_storage.py` | 42 | Persistencia técnica/guards/rollback y verificaciones de procedencia; políticas LAB, no publicación oficial |

Los seis escenarios añadidos están en:
`tests/integration/test_grade_notice_closed.py::test_principal_no_anuncia_resultado_inexistente_ni_escribe`
(cinco actores) y
`::test_reintentos_y_solicitudes_concurrentes_no_generan_avisos`.

Se adaptaron **dos expectativas antiguas**, sin eliminar sus pruebas: el unitario
que esperaba 201 solo por rol ahora exige 503 y cero llamadas al emisor/commit;
el paso final del recorrido Scheduling ya no asume que finalizar una sesión
crea automáticamente una calificación. El resto del recorrido se conserva.

La reproducción RF-19 fue creada durante esta auditoría y se conservó por SHA-256
como `evidencias/.../reproduccion_rf19.py`, separada de los tests del incremento
RF-27. No se eliminó ningún test previo ni se usó skip/xfail. En ese corte, los dos fallos
demostrados no quedaban resueltos por los 244 aprobados: esa regresión NO acredita
que el defecto de estado precargado esté corregido.

### Reproducción de la validación final

Desde la carpeta original:

```powershell
& C:\Python313\python.exe -B .\evidencias\auditoria_cobertura_20261105T051832Z\ejecutar_validacion.py seguridad
& C:\Python313\python.exe -B .\evidencias\auditoria_cobertura_20261105T051832Z\ejecutar_validacion.py focal
Get-Content .\evidencias\auditoria_cobertura_20261105T051832Z\pruebas_focal_20261105T122422Z\resultado.json
```

El ejecutor usa `.venv/Scripts/python.exe`, desactiva lectura de `.env` solo en el
proceso hijo y elimina URLs externas del entorno heredado. El fixture propio crea
PostgreSQL17 en contenedor etiquetado, tmpfs, puerto efímero de loopback y sin
volúmenes persistentes. Las fuentes permanecieron iguales durante cada pytest.
Cada ejecución conserva comando, versión/hash de fuentes, consola y JUnit nominal.

## 8. Preservación, archivos afectados y estado Git

Se verificó inicialmente y al cierre `feature/backend-continuidad`, HEAD
`ac92b7251c96f81ddcb6f390ef21435ab74b6131`, sin índice preparado para commit.
Las referencias main/develop/martin/feature-integration y el stash original se
comparan por hash con `preservacion_inicial.json`; no se modificaron.

Los 16 archivos de 9A conservan sus SHA-256 de cierre:

| Tipo previo | Archivo bajo backend/ |
|---|---|
| Modificado | app/main.py |
| Modificado | app/modules/participation/api/HTTP.md |
| Modificado | app/modules/participation/api/dependencies.py |
| Modificado | app/modules/participation/application/services.py |
| Modificado | app/modules/participation/infrastructure/composition.py |
| Modificado | app/modules/participation/tests/test_api.py |
| Modificado | docs/FASE_9_APLICACION_PRINCIPAL.md |
| Modificado | tests/integration/test_main_current_scenario.py |
| Nuevo | app/modules/participation/application/progress.py |
| Nuevo | app/modules/participation/infrastructure/progress_query.py |
| Nuevo | app/modules/participation/api/progress_router.py |
| Nuevo | app/modules/participation/api/attempt_operations_router.py |
| Nuevo | tests/integration/test_main_progress.py |
| Nuevo | tests/integration/test_main_decisions.py |
| Nuevo | tests/integration/test_main_finish.py |
| Nuevo | docs/FASE_9A_PARTICIPATION.md |

También se conservan sin cambios los tres archivos locales de 9B:
`participation/infrastructure/start.py`, `test_attempt_permission_creator.py` y
`docs/FASE_9B_INICIO_DESDE_CONVOCATORIA.md`. El manifiesto inicial incluye rutas,
tamaños y SHA-256 de los archivos rastreados/no rastreados no ignorados, incluyendo
Word/ZIP/documentación previa; no se sobrescribieron ni eliminaron originales.

Archivos de ESTE incremento, separados del trabajo anterior:

| Estado | Archivo bajo backend/ | Justificación |
|---|---|---|
| Modificado | app/modules/scheduling/api/router.py | Cierre explícito del emisor de calificación no verificada y OpenAPI 503; sin Session escritora |
| Modificado | tests/unit/scheduling/test_api_endpoints.py | Sustituir expectativa 201 insegura por 503 sin invocar helper/commit |
| Modificado | tests/integration/scheduling/test_scheduling_endpoints.py | Conservar recorrido; no presentar fin de sesión como nota oficial |
| Nuevo | tests/integration/test_grade_notice_closed.py | Aceptación sobre main con JWT/PG real y captura de DML/commits |
| Nuevo | docs/AUDITORIA_COBERTURA_BACKEND_20261105.md | Esta matriz, riesgos, decisiones y resultados |

Evidencia nueva bajo `evidencias/auditoria_cobertura_20261105T051832Z/`, sin
añadirla al índice. No es una copia del repositorio ni un worktree. La reproducción
RF-19 se conserva allí como hallazgo pendiente, no como funcionalidad incorporada.
No se cambió `.env`, ORM, migraciones, DBML, Evaluation ni los archivos de 9A/9B.
No hubo commit, push, merge, PR ni conexiones a bases permanentes.

Cierre verificado: `git diff --check` terminó con código 0 (avisos LF/CRLF de
dos archivos previos de 9A, sin errores de whitespace); Alembic conserva una sola
cabeza `20261104_teacher_spaces`. No quedan contenedores con la etiqueta del
laboratorio. `CIERRE_FINAL.json` conserva estado Git completo, referencias,
preservación, resultados nominales y hash de este informe. No se preparó ningún
archivo en el índice ni se atribuye esta entrega a un commit nuevo.

## 9. Qué falta realmente

El backend tiene una base considerable y reutilizable, pero no puede declararse
completo por contar tests o clases. Faltan tres cierres de producto principales:
acceso/autoría de personal sin fixtures, inicio estudiantil con políticas
académicas aprobadas y evaluación/reporte/publicación oficial reproducibles.
Correo y las garantías operativas/no funcionales completan esa entrega.

El siguiente incremento técnico independiente recomendado es **RF-19: lectura
fresca bajo lock para impedir la doble transición demostrada**, conservando State
y su contrato. No requiere decidir RF-22 ni fórmulas. Después, priorizar el contrato
de autenticación personal con Identity mientras se obtienen las decisiones de
inicio/evaluación. Esta recomendación se ejecutó posteriormente según la actualización
RF-19 inferior. No se implementa ningún otro incremento automáticamente.

## 10. Actualización RF-19: cierre único y auditoría consistente

5 de noviembre de 2026, America/Bogota. Misma rama y HEAD; modificaciones locales
anteriores preservadas. **Se corrige el cierre de sesiones de Scheduling, no el
cierre de intentos de Participation.**

### Causa raíz demostrada

La reproducción conservada se incorporó, sin alterar su artefacto original, a
`backend/tests/integration/test_session_state_consistency.py`. Antes del parche
las dos pruebas originales volvieron a fallar contra PostgreSQL17:

1. T1 precarga una sesión EN_CURSO en su identity map.
2. T2 cierra y confirma FINALIZADO con su auditoría.
3. T1 adquiere el lock mediante `Session.get(..., with_for_update=True)`, pero
   SQLAlchemy conserva los atributos de la instancia previamente cargada.
4. State recibe EN_CURSO obsoleto, autoriza otra finalización, cambia la fecha de
   cierre y añade otra auditoría. El bloqueo SQL existía; faltaba refrescar el ORM.

La prueba `test_lock_sin_refresco_demuestra_causa_del_identity_map` compara una
columna SQL real FINALIZADO con la misma instancia bloqueada todavía EN_CURSO y
comprueba que el refresco actualiza esa instancia a FINALIZADO. No se atribuye
el defecto a un fallo de Docker ni a ausencia de locks. SQLAlchemy local: 2.0.55;
pytest: 9.2.0.

### Corrección mínima y contrato conservado

Se añadió `populate_existing=True` al `Session.get(..., with_for_update=True)`
existente en tres puntos:

- `scheduling/application/cambiar_estado_sesion.py`: State valida el estado
  persistido recuperado bajo lock; el segundo escritor espera y ve el commit del
  primero, no su antigua instancia.
- `scheduling/application/worker_cierre.py`: el candidato se revalida con estado
  y fecha_fin refrescados; si ya fue cerrado, el worker lo omite.
- `scheduling/api/router.py::actualizar_estado`: también la titularidad se comprueba
  desde la fila refrescada y bloqueada, sin modificar su regla de autorización.

No se cambió State: SIN_INICIAR → EN_CURSO → FINALIZADO. Repetir finalizar o
iniciar en FINALIZADO conserva **HTTP 409**, sin auditoría ni evento nuevos. No se
convirtió el cierre de sesión en una operación idempotente 200: ese es un contrato
distinto del cierre de intentos de Participation, que permanece intacto.

El servicio sigue sin commit propio. `cambiar_estado_y_publicar` conserva el commit
conjunto de estado/auditoría y Observer después del commit. Ante State inválido o
fallo antes del commit, hace rollback sin publicar. Worker y docente reutilizan
ese mismo coordinador. No se cambiaron el coordinador, Observer ni sus clases de
State; no se añadieron migraciones, tablas, columnas o restricciones.

### Pruebas individuales y de concurrencia

Los siguientes métodos pertenecen a `tests/integration/test_session_state_consistency.py`:

| Método / parámetro | Resultado actual y aserciones |
|---|---|
| `test_estado_precargado_no_repite_cierre_http_ni_altera_fecha` | Antes FALLÓ; ahora APROBADO. Rechazo de segunda transición, una auditoría, fecha y versión originales conservadas. |
| `test_cierres_concurrentes_con_precarga_solo_una_transicion_y_auditoria` | Antes FALLÓ (dos cerradas); ahora APROBADO: una cerrada, un conflicto y una auditoría. |
| `test_rollback_de_cierre_conserva_estado_auditoria_y_version` | APROBADO. Flush sin commit se revierte; otra Session ve EN_CURSO sin auditoría de cierre. |
| `test_worker_frontera_24_horas_offset_y_no_repite_cierre` | APROBADO. Frontera +24h inclusiva, +1 microsegundo aún no elegible, offset equivalente y segunda revisión sin cierres nuevos. |
| `test_lock_sin_refresco_demuestra_causa_del_identity_map` | APROBADO. Estado SQL, caché obsoleta y refresco sobre el mismo registro comprobados. |
| `test_http_cierre_repetido_y_actor_ajeno_no_publican_otra_auditoria_o_aviso` | APROBADO. Docente ajeno/estudiante 403, anónimo 401, propietario 200, repeticiones 409; una auditoría y un aviso SQL. |
| `test_competencia_docente_worker_con_locks_reales_y_observer_unico[docente]` | APROBADO. Candidato seleccionado antes del commit docente; worker con objeto precargado refresca y omite, devuelve 0. |
| `test_competencia_docente_worker_con_locks_reales_y_observer_unico[worker]` | APROBADO. Worker mantiene lock hasta commit, docente espera y recibe 409; worker devuelve 1. |
| `test_fallo_antes_de_commit_revierte_estado_auditoria_y_no_publica` | APROBADO. Fallo técnico después de flush revierte estado/auditoría, cero avisos; reintento válido publica una sola vez. |
| `test_fallo_observer_postcommit_no_revierte_ni_republica_al_reintentar` | APROBADO. Cierre confirmado permanece; reintento inválido no vuelve a publicar. No acredita entrega durable. |

Las carreras emplean barreras/Event y hooks para coordinar **SQL real**, sin
simular filas, locks, State o auditorías ni usar sleeps para sincronización. Se
fuerzan ambos órdenes de adquisición y se comprueban origen de auditoría y un
único aviso real de SESION_FINALIZADA para la convocatoria activa. Solo los tests
excepcionales inyectan fallos técnicos. Los JWT docentes se emiten desde fixtures
con identidades/roles SQL reales: no se afirma un login productivo del personal.
Las políticas de inicio de la preparación compartida siguen identificadas como LAB;
no se usan para autorizar cierres ni se habilitan en la aplicación principal.

### Resultados reales de esta corrección

Evidencia: `evidencias/rf19_cierre_unico_20261105T125836Z/`.

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias / duración |
|---|---:|---:|---:|---:|---|
| `pruebas_seguridad_20261105T125838Z`: reproducción anterior al parche | 0 | 0 | 2 | 0 | 1; 9.69 s |
| `pruebas_seguridad_20261105T125926Z`: mismos dos métodos corregidos | 2 | 0 | 0 | 0 | 1; 8.13 s |
| `pruebas_casos_20261105T130457Z`: diez casos PG | 10 | 0 | 0 | 0 | 1; 18.95 s |
| `pruebas_focal_20261105T130612Z`: Scheduling e integraciones | 322 | 0 | 0 | 0 | 1; 207.65 s |
| **`pruebas_total_20261105T131009Z`: general actual** | **2017** | **38** | **0** | **0** | **1; 796.89 s** |

La general ejecutó `backend/tests` y `backend/app/modules/participation/tests`.
Es un resultado actual, no suma de suites solapadas. Las 38 omisiones permanecen:
29 de Identity por URL externa ausente, 3 de conexión Participation sin habilitar y
6 sin URL externa de laboratorio. No se cuentan como aprobadas. La advertencia
es Starlette/TestClient-httpx. Los resultados anteriores 2001/38 y 244 pertenecen
a otros cortes, conservados en sus evidencias.

La focalización incluye unitarias e integración Scheduling, programación,
convocatorias, cierre RF-27, Scheduling–Participation, las cuatro operaciones 9A
y Evaluation persistida. Combina unitarias/dobles, SQLite aislado y PG real; los
diez casos nuevos RF-19 sí requieren PG. La general incluye además el seguimiento,
feedback y guards históricos. No se afirma publicación de notas o entrega SMTP.

No se alteraron fuentes durante pytest. La general generó solo su JSON habitual
de evidencia BD2-04, conservado. Cada carpeta guarda comando, HEAD y cambios locales,
hashes de fuentes, log completo, JUnit y resultado nominal. El ejecutor desactiva
lectura de `.env` únicamente en el proceso hijo y elimina conexiones externas del
entorno heredado. Los fixtures crean PostgreSQL17 etiquetado en tmpfs, puerto
efímero de loopback y sin volúmenes persistentes; eliminan solo sus propios IDs.

```powershell
# Desde la carpeta original; cada ejecución crea sus propios laboratorios.
& C:\Python313\python.exe -B .\evidencias\rf19_cierre_unico_20261105T125836Z\ejecutar_validacion.py seguridad
& C:\Python313\python.exe -B .\evidencias\rf19_cierre_unico_20261105T125836Z\ejecutar_validacion.py casos
& C:\Python313\python.exe -B .\evidencias\rf19_cierre_unico_20261105T125836Z\ejecutar_validacion.py focal
& C:\Python313\python.exe -B .\evidencias\rf19_cierre_unico_20261105T125836Z\ejecutar_validacion.py total
Get-Content .\evidencias\rf19_cierre_unico_20261105T125836Z\pruebas_total_20261105T131009Z\resultado.json
```

### Archivos, garantías y riesgos restantes

Archivos afectados exclusivamente por esta corrección:

1. `app/modules/scheduling/application/cambiar_estado_sesion.py`: refresco bajo lock.
2. `app/modules/scheduling/application/worker_cierre.py`: mismo refresco al revalidar candidatos.
3. `app/modules/scheduling/api/router.py`: refresco en comprobación de titularidad/estado; cierre RF-27 intacto.
4. `tests/unit/scheduling/test_cambiar_estado_sesion.py`: expectativa del keyword añadido, conservando las aserciones de State/auditoría/ausencia de commit.
5. `tests/integration/test_session_state_consistency.py`: reproducción incorporada a la suite normal y ampliada a diez escenarios.
6. Este informe: matriz y riesgos actualizados, conservando registros anteriores.

**Defecto corregido y acreditado:** un solo cierre y auditoría por transición
válida coordinada, con rechazo posterior sin nuevos eventos, rollback y exclusión
docente/worker reales. No se necesita migración para esta causa: el lock ya existe
y State ya rechaza la transición repetida cuando recibe el estado correcto.

Límites que no se presentan como resueltos:

- Observer publica después del commit. Si falla o cae el proceso, no puede
  revertirse el cierre; falta recuperación durable/idempotente de la entrega.
  Repetir una transición inválida no es un mecanismo de reenvío. No se añadió
  outbox ni se afirma una garantía universal de «exactamente una vez».
- La garantía corresponde a escritores coordinados de aplicación. SQL directo
  privilegiado puede eludir State; no se añadió un trigger o UNIQUE para ese
  alcance distinto.
- No se consultaron ni limpiaron duplicados históricos en bases del equipo;
  de existir, requieren revisión autorizada. No se borró ningún registro.
- El despliegue periódico del runner no queda certificado por pytest. RF-19
  conserva estado global PARCIAL por aspectos operativos y de entrega, aunque
  el defecto solicitado de cierre está corregido.

No se cambiaron State, `cambiar_estado_y_publicar`, Observer, ORM, migraciones,
DBML, `.env`, Participation o Evaluation. Las 16 huellas 9A y las fuentes 9B
permanecen preservadas. RF-27 sigue cerrado y sus seis pruebas pasan en la general.
No hay nuevas rutas, permisos, políticas académicas ni activaciones productivas.

El estado exacto de Git, refs/stash, hashes, resultados y limpieza está en
`evidencias/rf19_cierre_unico_20261105T125836Z/CIERRE.json`. Rama y HEAD sin cambios,
índice vacío, sin contenedores de laboratorio restantes. No se aplicaron migraciones
a bases permanentes ni se ejecutaron commits, push o merges. Se detiene este incremento.

## 11. Actualización posterior: consistencia de avisos internos de sesión

La sección 10 describe el corte histórico RF-19. Su límite de aviso SQL perdido
se corrige ahora mediante la alternativa A, no mediante una outbox. El contrato
vigente del Observer registra exclusivamente avisos INTERNA de inicio/fin.
RF-21 exige correo para convocatorias y sigue parcial; no se convierte en un
contrato de correo para estos eventos. Comparación y decisión detalladas en
`CONSISTENCIA_EVENTOS_ACADEMICOS_PROPUESTA.md`, sección 7.

El coordinador existente confirma State, auditoría y avisos en una sola transacción.
Se conserva el lock con `populate_existing=True` y la competencia docente/worker.
El Observer SQL es secuencial y no abre Session ni commit propios. Un fallo SQL
revierte el conjunto; el reintento ejecuta una transición todavía válida. Los
callbacks efímeros permanecen después del commit: no son entrega durable, lectura
ni envío externo. No se afirma exactamente una vez ni protección contra SQL
privilegiado que eluda los servicios. No hay migración ni cambio ORM/DBML.

Evidencia: `evidencias/consistencia_notificaciones_20261105T165011Z/`:

- Reproducción previa: 2 fallidas, 0 aprobadas/omitidas/errores, 1 advertencia.
- Regresión relacionada: 196 aprobadas, 0 omitidas/fallos/errores, 1 advertencia.
  Incluye seis casos nuevos PG17, diez RF-19, Scheduling y compatibilidad de
  convocatorias, consulta privada de feedback y bloqueo de notas oficiales.
- Los diagnósticos históricos quedan intactos fuera de la aceptación. La
  expectativa de columna PENDIENTE pertenecía a B; la prueba de aceptación A
  exige rollback completo y reintento 500 → 200 → 409, sin pérdida de aviso.
  El objetivo del segundo diagnóstico se mantiene: replay concurrente sin duplicado.

No cambia el conteo global de RF: RF-19 sigue PARCIAL por despliegue/operación del
worker; sí queda acreditado un tramo técnico adicional. RNF-04/06 conservan sus
límites globales y la distinción de «propuestos» de la fuente. Participation 9A,
9B, Evaluation, inicio productivo, RF-22 y notas oficiales no se modifican.

Validación final actual: **2023 aprobadas, 38 omitidas, 0 fallos/errores y una
advertencia conocida**, general `pruebas_total_20261105T180509Z` (766.90 s).
El replay del diagnóstico original también pasa sin modificarlo: 1 aprobada,
0 omitidas/fallos/errores, una advertencia, 7.77 s. No se suma a la general.
Consolas, JUnit y motivos de las omisiones permanecen en el paquete. No hubo
cambios de fuentes durante pytest; únicamente un JSON de evidencia BD2-04 nuevo,
conservado y excluido del checkpoint. Sin migraciones ni conexiones permanentes.

## 12. RF-19: cierre automático acreditado como proceso independiente

Continuidad posterior a C1/C2/C3 (`33981c8`), sin commits nuevos. Se priorizaron
RF-19, RF-03 y RF-21 utilizando esta matriz. Los dos últimos tienen contratos
técnicos pendientes (login administrativo y transporte recuperable de códigos);
no se inventaron implementaciones para declararlos completos. Selección, criterios
previos y comandos seguros en `RF19_WORKER_OPERATIVO.md`.

El perfil `worker` ya existía en Compose. Se reutilizan `worker_runner`, State,
el coordinador y Observer transaccional. El cambio productivo se limita al runner:
validación CLI, salida 1 en fallo de revisión única, manejo de interrupción y
errores periódicos con código/clase, sin volcar excepción/SQL/parámetros.
No cambiaron fecha límite +24 h, intervalo de 60 s, transacciones ni rutas.

Evidencia actual en `evidencias/rf19_worker_20261105T195818Z/`:

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Focal `pruebas_casos_20261105T200215Z` | 6 | 0 | 0 | 0 | 1 |
| Relacionada `pruebas_focal_20261105T200444Z` | 162 | 0 | 0 | 0 | 1 |

La primera duró 80.88 s y la segunda 116.54 s. Las suites se solapan: no se suman.
Dos pruebas son unitarias de CLI con dobles; cuatro usan procesos independientes,
PostgreSQL17 y SQL/State/Observer reales. Las salidas de los hijos quedan como
propiedades nominales del JUnit de la relacionada:

- Revisión única: `Sesiones cerradas: 1`; repetición: `Sesiones cerradas: 0`.
- Dos procesos detenidos en locks reales de PG: resultados 1 y 0; una auditoría
  WORKER y un aviso al titular, comprobados desde otra Session.
- Proceso periódico: error SQL controlado, rollback; siguiente revisión real a
  los 60 s cierra la sesión sin reiniciar el proceso. Error registrado solo como
  `REVISION_FALLIDA tipo=ProgrammingError`, sin el marcador privado de PostgreSQL.
- Base inexistente dentro del servidor desechable: salida 1 y error saneado
  `OperationalError`, sin nombre de base, contraseña ni traceback; sin cambios SQL.

Este conjunto cubre la brecha operativa que mantenía RF-19 parcial, por eso pasa
a IMPLEMENTADO en alcance funcional verificable. No es una certificación de
despliegue institucional: la ruta docente ya está en main; el worker debe activarse
y supervisarse como proceso independiente. No se construyó/certificó la imagen
Docker ni se ejecutó Compose contra una base persistente. Los RNF operativos,
monitorización y correo conservan sus límites globales.

La general 2023/38 sigue siendo histórica; no se repitió porque no cambiaron
contratos compartidos, esquemas HTTP ni lógica académica. La regresión relacionada
incluye Scheduling, RF-19, atomicidad y bloqueo de notas RF-27. No se calcula un
nuevo total general sumando los seis casos. Sin cambios a 9A/9B/Evaluation,
`.env`, ORM, Alembic, DBML ni bases permanentes.

## 13. Autenticación del personal: contrato no confirmado

Se contrastaron RF-01/02/03 y RN-01/02 de los PDF, README y contratos históricos
con el código y OpenAPI actuales. Resultado detallado y decisión necesaria en
`AUTENTICACION_PERSONAL_CONTRATO_PENDIENTE.md`. RF-03 sigue siendo administración
docente: implementar solo un login no resolvería permisos individuales/multirrol,
bootstrap y aceptación integral de sus operaciones.

Existe hash Argon2 de alta, primitiva de verificación pwdlib, emisor/verificador
TokensJWT, recarga SQL de roles/permisos y autorización de recursos. No existe
un servicio HTTP de autenticación de personal desde esas credenciales. Tampoco
se encontró contrato que autorice local o exija un proveedor SSO concreto. No
se implementó un mecanismo por deducción de la columna `clave_hash`.

El único login registrado en main sigue siendo `/api/v1/identity/auth/estudiantes`.
Las operaciones administrativas están registradas y protegidas por JWT/Proxy,
pero no se añadió una vía pública para emitir esos tokens. Las fixtures de
personal prueban autorización con tokens emitidos dentro del laboratorio.

No cambian estados ni conteos: 12 IMPLEMENTADO, 9 PARCIAL y 6 BLOQUEADO. Solo se
precisan las dependencias de RF-02/03. No se ejecutó pytest ni PostgreSQL en este
incremento documental: no hay implementación autorizable por contrato ni cambios
productivos. La introspección OpenAPI sin BD es una verificación de registro,
no una prueba de login. Resultados 2023/38 y 162 relacionados permanecen históricos.

Evidencia de fuentes, rutas y preservación:
`evidencias/autenticacion_personal_20261105T201553Z/`. Todos los cambios operativos
RF-19 y las secciones anteriores permanecen; sin cambios en código, endpoints,
`.env`, bases permanentes, ramas, stash, checkpoints o políticas académicas.

## 14. RF-15: recorrido de consulta docente de solo lectura en main

Se reutilizaron los tres GET ya compuestos, ProxySeguimiento, ServicioSeguimiento,
consulta SQL y contratos internos de Cases. RF-15 no estaba completamente bloqueado
ni requería otro proveedor: su autorización JWT/SQL existe, aunque el login del
personal continúa pendiente. Alcance y preparación de laboratorio en la sección
de continuidad de `RF15_RF26_SEGUIMIENTO_DOCENTE.md`.

El defecto técnico reproducido era commit innecesario en las lecturas: dos casos
PG17 sobre main observaron seis COMMIT por recorrido de cuatro GET. No se atribuye
DML al comportamiento anterior. `_operar` ahora usa `no_autoflush` y cierre de
Session sin commit; conserva los locks y la revalidación de ámbito. El escritor
de feedback y Participation no se modificaron.

| Ejecución actual | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Reproducción `pruebas_seguridad_20261105T202708Z` | 0 | 0 | 2 | 0 | 1 |
| Aceptación `pruebas_casos_20261105T202801Z` | 11 | 0 | 0 | 0 | 1 |
| Relacionada `pruebas_focal_20261105T202910Z` | 129 | 0 | 0 | 0 | 1 |

Evidencia: `evidencias/rf15_lectura_20261105T202511Z/`. No se suman ejecuciones.
Incluye app.main, JWT/roles/vínculos SQL reales, edición histórica, respuestas y
valoración individual, lecturas concurrentes, denegaciones y error SQL saneado.
Datos/cuentas son sintéticos; se emite JWT docente dentro de la fixture, sin
afirmar login institucional. La preparación de intento y nueva edición sigue
identificada como LAB, no habilita inicio productivo ni otra API.

RF-15 mantiene IMPLEMENTADO en este alcance; conteos 12/9/6 sin cambios. No se
afirma lectura en una réplica PostgreSQL READ ONLY: los locks de autorización
siguen presentes. No cambian contratos públicos/compartidos, no se repitió la
general y 2023/38 permanece histórico. Se conservan RF-19 operativo, contrato
pendiente de personal, RF-27, 9A/9B, Evaluation y todos los bloqueos académicos.

## 15. RF-16: integridad del CSV, reporte oficial todavía bloqueado

Diagnóstico y selección previa en `RF16_REPORTE_Y_BLOQUEOS.md`. RF-16 exige
resultados, parciales y ausentes; no autoriza inventar estados/nota desde I o una
fila faltante. La consulta existente parte de participaciones y no es el padrón
completo; el consolidado no está integrado. ResultadoIntento solo permite ámbito
LABORATORIO. Por ello no se compuso el proveedor ni se abrió el endpoint.

Mejora limitada: ServicioReportes valida estudiante/participación únicos y nota
presente dentro de escala antes de escribir el CSV. No deduplica seleccionando
último/mayor intento, no cambia columnas, no transforma vacíos en cero ni toca
Evaluation. Ese control no demuestra procedencia oficial de una fila.

| Ejecución actual | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Focal `pruebas_casos_20261105T204245Z` | 13 | 0 | 0 | 0 | 1 |
| Relacionada `pruebas_focal_20261105T204324Z` | 140 | 0 | 0 | 0 | 1 |
| General `pruebas_total_20261105T204545Z` | 2053 | 38 | 0 | 0 | 1 |

Evidencia en `evidencias/rf16_integridad_20261105T203847Z/`. No se suman suites.
Seis casos prueban el serializador con fuente sintética explícita; su CSV LAB
real se guardó con hash, no proviene de PostgreSQL ni de descarga HTTP oficial.
Siete casos PG17 sobre main comprueban 503 para docentes (incluido ajeno), 403
estudiante, 401 sin JWT válido, cero DML/flush/commit, concurrencia y dos convocados
con una sola P sin inferir ausencia. El 503 global no acredita ámbito de sesión
completo: esa autorización está pendiente junto con la composición del reporte.

RF-16 permanece BLOQUEADO; conteos 12/9/6 sin cambios. La nueva general incluye
también los incrementos RF-19 y RF-15 aún sin commit. Las 38 omitidas no son
aprobaciones; motivos y advertencia conocida quedan en consola/JUnit. Sin nuevas
tablas/rutas, políticas, login, calificaciones oficiales ni bases permanentes.

## 16. Login del personal con correo y contraseña asignada por administrador

Decisión funcional posterior del equipo: mecanismo local autorizado para este
incremento; no se atribuye aprobación institucional adicional. Se sustituye el
bloqueo de elección local/SSO del diagnóstico de la sección 13, que se conserva
como antecedente. Contrato y límites: `LOGIN_PERSONAL_CORREO_CLAVE.md`.

Se reutilizan Identity, pwdlib/Argon2, repositorio y TokensJWT. La ruta
`POST /api/v1/identity/auth/personal` está registrada realmente en main. Solo
cuentas activas DOCENTE/ADMINISTRADOR con clave correcta emiten JWT; no admiten
roles del cliente, convocatoria ficticia ni autovinculación UUID. Los permisos y
estado siguen consultándose en PostgreSQL en las operaciones protegidas.

RF-02 pasa a IMPLEMENTADO dentro de su alcance de permiso de creación por rol:
login real, creación propia, caso ajeno rechazado y revocación de permiso/rol
acreditados. RF-03 sigue PARCIAL: alta y asignación compatibles funcionan, pero
bootstrap y granularidad de permisos no se inventan. RF-16 sigue BLOQUEADO para
CSV oficial; inicio productivo, repetición y notas no se habilitan.

Resultados actuales, sin sumar suites solapadas:

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Primera focalizada | 18 | 0 | 1 | 0 | 1 |
| Focalizada corregida | 19 | 0 | 0 | 0 | 1 |
| Regresión relacionada final | 421 | 29 | 0 | 0 | 1 |
| General final | 2072 | 38 | 0 | 0 | 1 |

La primera falla fue una expectativa de prueba que leía `id` en la respuesta de
Cases en vez del contrato existente `version_id`; se corrigió únicamente esa
expectativa y se conserva el log fallido. Después se añadieron aserciones del PUT
administrativo, incluidas en las regresiones finales. Las 19 pruebas nuevas usan
app.main, JWT real y PostgreSQL 17 desechable, sin overrides de autenticación o
repositorios; el primer administrador y las asociaciones de casos se preparan
explícitamente como fixtures de laboratorio. Las 29 omisiones antiguas de Identity
y 9 de Participation requieren URLs/configuración explícita y no se dan por
aprobadas. La advertencia es la conocida de Starlette/TestClient-httpx.

Evidencia: `evidencias/login_personal_20261105T211338Z/`, JUnit, consola y huellas
por ejecución. General `pruebas_total_20261105T212350Z`, 885.54 s. Base `33981c8`
más cambios locales sin commit; no debe atribuirse este código al commit base.
La general no cambió fuentes; generó una evidencia BD2-04 que se conserva.

## 17. Antecedente RF-22: anticipación DESCARTADA por corrección posterior

**No vigente:** esta sección conserva evidencia de la decisión anterior, sustituida
por la sección 18. No permite ingreso anticipado.

Decisión funcional comunicada por el equipo: ingreso anticipado desde diez minutos
antes del inicio. No se atribuye aprobación institucional de otras políticas.
`POST /scheduling/validar-ingreso` usa JWT real, convocatoria propia ACTIVA y
matrícula activa vinculada por asignación a la versión exacta de la sesión.
Se aplica `[inicio - 10 minutos, inicio)` a SIN_INICIAR. EN_CURSO conserva su
política posterior no configurada (503); FINALIZADO rechaza. Inicio exacto con
SIN_INICIAR sigue rechazado. No se inventa tolerancia tardía ni permite cambiar
la ventana desde el cliente. Todos los instantes requieren zona explícita.

RF-22 pasa de BLOQUEADO a PARCIAL, no a completo. La anticipación está disponible
en main; no crea participación/intento ni habilita el router de inicio. RF-20
conserva su parcialidad por entrega externa pendiente. RF-16 y notas oficiales
no cambian. Contrato, archivos, casos y evidencia: `RF22_INGRESO_ANTICIPADO.md`.

Aceptación: 26 casos nuevos HTTP main, JWT y PG17; cuatro unidades de límites del
proveedor. Relacionada FINAL: 558 aprobadas, 0 omitidas/fallidas/errores, una
advertencia, 149.94 s. General FINAL: 2102 aprobadas, 38 omitidas, 0 fallidas y
0 errores, una advertencia, 938.51 s. No sumar suites solapadas. Las omisiones son
las 29 antiguas Identity y 9 Participation condicionadas a configuración/URL.
No se modificó código durante las ejecuciones. Advertencia conocida Starlette.

Se conserva la primera general fallida: 2063 aprobadas, 38 omitidas, 12 fallidas,
27 errores. La preparación de matrícula se había añadido a una fixture compartida
de login; sus nuevas FK impedían casos de versiones/sesiones aún no asignadas.
Se movió SOLO a la fixture temporal de ingreso. Las pruebas históricas afectadas
permanecen y pasan; no se alteraron FK ni lógica productiva para evitarlas.
Logs, JUnit, comandos y huellas: `evidencias/rf22_anticipado_20261105T231718Z/`,
finales `pruebas_focal_20261105T234704Z` y `pruebas_total_20261105T235005Z`.
Fecha local final 2026-11-05 19:05:56 (America/Bogota). Base `33981c8` más cambios
locales sin commit. No hubo migración nueva ni conexión a una base permanente.

Consentimiento: se registra la decisión posterior de aceptación antes de crear P
y no revocación mientras se ejecuta la simulación. Sigue faltando la fuente del
texto/version vigente y cómo comprobar su aplicabilidad. Los servicios técnicos
reutilizables no acreditan ese contrato por sí mismos: la provisión independiente
LAB no exige aún esa aceptación antes de P y no está montada en main. Revocación
fuera de ejecución, versión aplicable, política desde inicio y repetición requieren
precisión; no se implementan en este incremento. La política de anticipación no
se inyecta al iniciador de Participation ni concede permiso para simular.

## 18. RF-22 corregido: habilitación efectiva indispensable

Corrección posterior del responsable funcional: no hay autorización de anticipación.
El alumno solo puede ingresar con sesión habilitada. State produce EN_CURSO por
operación docente protegida y lo persiste junto a auditoría; fecha_inicio no
habilita por sí sola. Se elimina la clase/constante/factory anticipada y su rama
en validar_ingreso. SIN_INICIAR rechaza a -10 minutos, -1 segundo, inicio exacto
y después; FINALIZADO rechaza. EN_CURSO conserva el proveedor temporal cerrado
hasta disponer de una política completa, sin inventar tolerancia tardía.

No cambia el estado PARCIAL ni los conteos de RF. Se conserva autenticación,
convocatoria ACTIVA, matrícula, código, versión exacta, lectura sin DML/flush/commit
y cero P/I. No se modifican Participation, Evaluation, consentimiento ni inicio.
La corrección es de requisito; el código anterior cumplía la interpretación
anterior, ahora descartada. Registro: `DECISIONES_FUNCIONALES_RF22.md`.

Evidencia actual `evidencias/rf22_habilitacion_20261106T002442Z/`: reproducción
previa 2 aprobadas (admitía anticipación); aceptación corregida 30 aprobadas PG17;
relacionada 558 aprobadas; general 2102 aprobadas, 38 omitidas, 0 fallidas/errores,
1 advertencia conocida, 926.08 s. No sumar suites solapadas ni atribuir aprobaciones
a omisiones. General final `pruebas_total_20261106T003253Z`, huellas estables.

Los positivos temporales adicionales son explícitamente LAB; main sin overrides
rechaza con 503 después de habilitar si falta la política. La sesión evaluada se
crea/habilita por HTTP con JWT docente real, estudiante se autentica por correo y
código, y estado/auditoría se recuperan desde otra Session. No se inventan instantes
de habilitación ni se reescribe la auditoría anterior. Informe actualizado en
`RF22_INGRESO_ANTICIPADO.md`, que conserva su nombre e historia.

## 19. Definición definitiva RF-22 y consentimiento/inicio internos

Se mantienen los 27 RF y sus categorías (13 IMPLEMENTADO, 9 PARCIAL, 5 BLOQUEADO).
RF-12 y RF-22 avanzan técnicamente sin cambiar a completos. No se reauditan ni se
atribuyen aprobaciones a otros requisitos. No hay nuevas notas oficiales.

RF-22: sin tolerancia anticipada ni tardía; habilitación real es indispensable,
pero no prueba oportunidad. Falta señal objetiva de admisión, por lo que se
conserva 503. No se introducen minutos, igualdad de timestamps ni permiso durante
todo EN_CURSO. Las pruebas positivas temporales siguen siendo SOLO LAB.

Consentimiento: decisiones de aceptación antes de P, versión vigente/nueva
aceptación para nueva P al cambiar versión y no revocación durante ejecución.
No existe documento oficial. Hay borrador NO aprobado y contrato/fuente interna
sin adaptador productivo. El servicio SQL de aceptación/consulta usa identidad
actual, acción explícita, fecha servidor y versión/huella presentadas frente a
fuente de servidor. Guard interno para revocación con I EN_CURSO, sin nuevo flujo
público ni garantía SQL directa. No se reclasifica legado como aceptación probada.

Antes de crear P, provisión valida consentimiento y, en flujo combinado, grafo,
duración y misma política de inicio. Se conserva UoW/locks/revalidación antes de I,
commit único y rollback. No hay fuente por defecto, autoinicio ni repetición.
Los contratos privados cambian mínimamente; HTTP principal no expone nuevos
routers. Persistencia usa consentimiento existente, sin tablas/migraciones nuevas.

Pruebas actuales: focal inicial 24 aprobadas; relacionada final 582; general final
2126 aprobadas, 38 omitidas, 0 fallidas/errores, una advertencia conocida, 874.69 s.
Final 2026-11-05 20:31:56 America/Bogota. No sumar solapamientos ni contar omisiones
como aprobadas (29 Identity, 9 Participation antiguas condicionadas a URL).
Código estable durante pruebas. Evidencia/JUnit:
`evidencias/consentimiento_inicio_20261106T010714Z/`, finales
`pruebas_focal_20261106T011316Z` y `pruebas_total_20261106T011709Z`.

Detalles, archivos y pendientes: `CONSENTIMIENTO_E_INICIO_INTERNO.md`.
Borrador: `BORRADOR_CONSENTIMIENTO_INFORMADO.md`, no conectado al backend.


## 20. Sala de espera y admisión aprobadas: avance RF-22

La decisión funcional explícita del equipo sustituye el bloqueo de oportunidad
anterior: solicitudes previas válidas, congeladas atómicamente con la habilitación
docente persistida. No hay margen anticipado ni tardío. RF-22 cambia de PARCIAL a
IMPLEMENTADO para este contrato acreditado en main/PG17; no equivale a desplegado
ni a inicio productivo. Conteo actualizado: 14 IMPLEMENTADO, 8 PARCIAL, 5 BLOQUEADO.
Los conteos de secciones anteriores son históricos. RF-12 permanece PARCIAL y los
otros 25 estados no se modifican. No cambian las fórmulas o notas oficiales.

Evidencia y límites: SALA_ESPERA_ADMISION_DISENO.md. Concesión causal inmutable,
una fila por convocatoria, pertenencia de versión y elegibilidad actuales;
read-only al consultar/validar. Espera sí escribe. 32 pruebas nuevas abarcan
varios estudiantes, JWT real, titularidad, corte concurrente en ambos órdenes,
conflicto reintentable, rollback integral, historial, retiro, worker y migración.
Se conservan los fixtures históricos LAB de otras suites, identificados como
tales y sin usarlos para declarar cumplida la admisión real. El documento de
consentimiento oficial sigue ausente; no se abren provisión/inicio ni Evaluation.


Validación final sección 20: general 2158 aprobadas, 38 omitidas, 0 fallidas/errores,
1 advertencia conocida, 948.13 s; `pruebas_total_20261106T025335Z`. Aceptación final
32; relacionada de compatibilidad 333; focal inicial 606. No sumar solapamientos.
La primera general fallida se conserva y se explica en el contrato de sala;
la final acredita la corrección de fixtures/cadena sin saltar pruebas. No cambia
ningún otro RF ni evaluación de RNF por inferencia. El total vigente es 14/8/5.


## 21. Checkpoints y persistencia de consentimiento: sin cambio de estados RF

Los 77 archivos se confirmaron en cuatro commits locales (a6f7e48, 906aec9,
8a08e8b y 28be564), sin modificar su contenido ni publicar. Reejecución actual:
56 aprobadas, 0 omitidas, 0 fallidas/errores y 1 advertencia conocida, consentimiento
interno y admisión; PG17 desechable. No se suma al histórico general 2158/38.

La persistencia documental/versionada no se implementa por asumir aprobación del
borrador. Se entrega diseño físico para aprobación: una tabla técnica adicional
(31→32), selector y evidencia de aceptación/enlace P→C. Se identifica el impacto
concreto de bd205_asignacion en selectores de asignaciones de versiones archivadas.
No hay ORM, migración ni endpoint nuevos de consentimiento. RF-12 sigue PARCIAL,
RF-22 IMPLEMENTADO en su alcance; totales sin cambio, 14/8/5. Documento técnico:
CONSENTIMIENTO_PERSISTENCIA_PROPUESTA_20261105.md.

## 22. Infraestructura interna de consentimiento versionado

Se implementa registro documental SQL y selector independiente por contexto del
puerto, sin modificar asignacion_caso ni el guard de Cases. Evidencia explícita
y vínculo P→C para el flujo moderno; legado nullable sin backfill. 33 tablas
físicas, ER académico original intacto. No documento oficial, publicación ni
rutas nuevas en main. RF-12 permanece PARCIAL: totales 14/8/5 sin cambios.
Detalle, migración y pruebas en CONSENTIMIENTO_VERSIONADO_IMPLEMENTACION.md.

Cierre sección 22: general definitiva 2187 aprobadas, 38 omitidas, 0 fallidas/errores
y una advertencia, 993.01 s, pruebas_total_20261106T043913Z. Sustituye el estado
pendiente de la ejecución; no se suma con 2185/38 ni con 639/257/29. Sin nuevos
estados RF: se mantienen 14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO. RF-22 intacto,
RF-12 PARCIAL. No hay publicación institucional, notas ni rutas nuevas en main.


## 23. API privada de consentimiento en composición aislada

Se implementan consulta vigente, estado de aceptación y aceptación explícita con
JWT real, ?mbito SQL y fuente/servicio existentes. GET sin DML/flush/commit;
POST transaccional, idempotencia, concurrencia y rollback, sin P/I. No se registra
la API en main ni se habilita inicio. No nuevas tablas/migraciones. Borrador sin
aprobación y proceso institucional pendientes. Detalle: API_CONSENTIMIENTO_ESTUDIANTIL.md.

General actual: 2213 aprobadas, 38 omitidas, 0 fallidas/errores, 1 advertencia;
1022.09 s, pruebas_total_20261106T152521Z. Aceptación final: 26. No sumar las
corridas. La relacionada inicial conserva 668 aprobadas y 1 error de preparación
HTTP 401, repetido con ?xito (1) y cubierto por la general. Se registra discontinuidad
horaria y no se atribuye causa JWT definitiva sin evidencia. No se alteró auth.
RF-12 sigue PARCIAL; total 14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO. RF-22/RNF sin
cambios inferidos. Inicio, provisión y calificaciones oficiales permanecen cerrados.


## 24. Inicio interno admitido, con consentimiento en la misma transacción

Scheduling aporta la concesión persistente al coordinador de provisión/inicio y
al inicio directo sobre P existente. Se mantiene la misma UoW READ COMMITTED,
orden de locks y validación de consentimiento anterior al INSERT. Se protege
además la fila causal de auditoría durante el inicio. Sin ORM/migraciones/rutas
nuevas en main. Fuente documental SQL y políticas explícitas SOLO LAB en aceptación.
Detalle: INICIO_ADMITIDO_Y_CONSENTIMIENTO_TRANSACCIONAL.md.

El 401 histórico no se reprodujo: nodo aislado 1, orden inverso 21, relacionada
previa 669, con instrumentación observacional y reloj estable. Causa histórica
no determinada, sin modificación de JWT. La expectativa antigua de fallo de un
proveedor de ventana se adaptó al proveedor activo SQL, conservando el rechazo.
Aceptación final nueva 11; relacionada final 680; general actual 2224 aprobadas,
38 omitidas, 0 fallidas/errores, 1 advertencia conocida (1094.21 s). No sumar corridas.
Logs/XML incluidos los diagnósticos conservados en evidencias/inicio_admitido_20261106T155628Z.
RF-12 PARCIAL; estados 14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO sin cambios. RF-22
mantiene su estado, con nueva evidencia de integración; no se aprueba el borrador
ni se habilita inicio productivo o Evaluation oficial. Los demás RF/RNF no se
reclasifican por inferencia.


## 25. Checkpoints locales y recorrido integral de laboratorio

Commits 6463eec (30 rutas) y 758f00e (11 rutas, incluido el manifiesto), auditados
contra las 40 entradas con hash, sin secretos o código funcional ajeno. Sin push,
merge ni cambio de rama. Archivos excluidos preexistentes preservados.

Nueva evidencia: test_lab_student_journey.py ejecuta bootstrap administrativo LAB,
login de personal, alta docente, autoría/grafo/publicación, programación/convocatoria,
login estudiantil, espera/concesión, consentimiento SQL sintético, inicio P/I y
escenario/respuestas/progreso/cierre. Main y composición aislada están identificados
paso a paso en RECORRIDO_ESTUDIANTIL_INTEGRAL_LAB.md. No se inventan rutas públicas.
Se verifica la misma transacción PostgreSQL en los dos INSERT y un commit, propiedad,
respuestas inmutables y un error SQL real 22012 con rollback y reintento.

Resultado NUEVO: aceptación 13 (2 E2E + 11 previos), relacionada 682; ambas con
0 omitidas, 0 fallidas/errores y 1 advertencia conocida. No sumar solapamientos.
No nueva general: no cambió código compartido ni hubo defectos funcionales nuevos;
2224 aprobadas/38 omitidas corresponde a la general histórica del incremento anterior.
El 401 no reapareció y su causa histórica no está demostrada. No se modificó JWT.

Se corrige el párrafo cuantitativo obsoleto 13/9/5 para concordar con las 27 filas
vigentes: 14 IMPLEMENTADO, 8 PARCIAL, 5 BLOQUEADO. También se concilian referencias
pendientes de login personal ya acreditado. No es una reclasificación de RF.
RF-12 continúa PARCIAL y las políticas/documento institucional siguen pendientes.
Consentimiento/provisión/inicio no se registran en main; no se publican notas.


## 26. Evaluation: preparación autorizada de sesión (6 de noviembre de 2026)

Decisiones funcionales comunicadas por el equipo: publicación sobre todos los
estudiantes de la sesión, ausencia confirmada expresamente por el docente,
publicación autorizada por docente con ámbito, repeticiones individuales y ninguna
publicación automática al cerrar. No sustituyen las fórmulas aún pendientes.

Incremento interno: ConsultaPreparacionEvaluacionSQLAlchemy revisa todas las
convocatorias persistidas, incluidas retiradas y sin participación; conserva todos
los intentos y la versión/rúbrica asignadas. Reutiliza la reproducción del repositorio
de resultados técnicos con el lector existente sin locks de escritura. Instantánea
PG REPEATABLE READ/READ ONLY, sin DML/flush/commit, sin nota ni datos de contacto.
Sin intentos exige revisión docente, nunca acredita ausencia; retiradas/repeticiones
quedan pendientes. El padrón observado no equivale al corte académico aprobado.

RF-13 y RF-24 mantienen BLOQUEADO para notas oficiales; RF-16 continúa cerrado y
RF-27 no publica avisos de notas. No se registra una nueva ruta en app.main ni se
modifican los cuatro endpoints del intento existente. No hay ORM/migración nuevos.
No cambia el conteo 14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO.

Aceptación nueva: 13 escenarios internos PG17 incluidos en la regresión relacionada
actual de 535 aprobadas, 9 omitidas, 0 fallidas/errores y 1 advertencia conocida;
no sumar selecciones solapadas. Primera corrida: 10 aprobadas y 1 fallo de preparación
al convocar una sesión ya cerrada; se corrigió el orden de la fixture, conservando
el rechazo legítimo de Scheduling. Corrida posterior de ese conjunto: 11 aprobadas;
la selección final incluye dos comprobaciones adicionales de ámbito y concurrencia.
Resultados generales y evidencia final: EVALUATION_PREPARACION_SESION.md.

General nueva completada: 2239 aprobadas, 38 omitidas, 0 fallidas/errores y una
advertencia conocida; 1136.73 s. No sumar a las 535 relacionadas ni al histórico
2224/38. Fuentes sin cambios durante la ejecución; un JSON nuevo de evidencia
BD2-04 preservado. Evidencia: evidencias/evaluation_preparacion_20261106T225458Z/
pruebas_total_20261107T033737Z/. La general anterior de este incremento quedó
interrumpida al 28 %, sin veredicto; su log se conserva y no se computa como suite
aprobada. Docker fue reanudado por el usuario antes de ejecutar la general completa.


## 27. RF-03: administrador inicial controlado (6 de noviembre de 2026)

Se seleccionó el bootstrap por su dependencia sobre login/alta docente ya existentes.
La primera cuenta ya no exige un INSERT manual de fixture: comando interno
identity.infrastructure.bootstrap_admin, sin HTTP, sin credenciales predeterminadas
ni asignaciones UUID. Reutiliza hasheador, repositorio y UoW. Catálogo ADMINISTRADOR
existente e inequívoco; rechaza si ya hay un administrador incluso inactivo o
correo ocupado, sin recuperar/reactivar cuentas. Los roles se normalizan como el
repositorio actual, sin suponer IDs. No se modifica rol_permiso ni el modelo de roles.

READ COMMITTED + locks de usuario/rol serializan la comprobación y alta. Rollback
ante fallo; ninguna creación de catálogos o autorización académica implícita.
El operador necesita acceso controlado al despliegue y credenciales SQL; confirmar
el nombre de base evita errores de destino, no prueba su autoridad. No hay registro
público ni vía de recuperación. DOCENTE ADMINISTRADOR sigue sin definición ejecutable.

Aceptación nueva: 13 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia conocida;
12 escenarios PG17 nuevos y uno de parser/consola sin BD. Regresión relacionada:
153 aprobadas, 0 omitidas/fallidas/errores y 1 advertencia, incluye esos 13.
No sumar suites solapadas. HTTP de app.main usa login/JWT/SQL reales; solo la entrada
interactiva del comando se simula. Se acreditan concurrencia, rollback SQL real,
persistencia en otra Session, ausencia de escalamiento y conservación del recorrido
estudiantil. Evidencias: evidencias/rf03_bootstrap_20261107T043239Z/.

No general nueva: solo módulo aislado, tests y documentación nuevos; no cambiaron
servicios, contratos, modelos ni rutas compartidos. Las 2239/38 previas siguen siendo
históricas; sus 38 omisiones no se consideran resueltas. No cambió Evaluation ni
sus documentos/evidencias sin commit. RF-03 permanece PARCIAL; totales sin cambio:
14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO. Detalle: RF03_ADMINISTRADOR_INICIAL.md.

## 28. RF-03: consulta administrativa privada (7 de noviembre de 2026)

GET `/api/v1/identity/docentes` disponible mediante el router Identity ya registrado
en app.main. Reutiliza el Proxy administrativo y exige ADMINISTRADOR. JWT real,
cuenta activa y rol revalidados en PostgreSQL; no se admiten privilegios inferidos
para DOCENTE ADMINISTRADOR ni identidad por cabecera.

Listado de cuentas docentes activas e inactivas, con nombre, correo, ID y estado;
paginación limitada y orden por ID. Instantánea REPEATABLE READ/READ ONLY, sin DML,
flush ni commit. No devuelve hashes, permisos, asociaciones, respuestas o notas.
El permiso administrativo actual no acredita ámbito universal para consultar
asociaciones académicas: ese tramo no se presume aprobado. Tener cero o varios
vínculos no omite ni duplica una cuenta, ni concede permiso sobre recursos académicos.

Nueva aceptación PG17/main/JWT real: 13 aprobadas sin omisiones/fallos/errores.
Regresión relacionada: 166 aprobadas sin omisiones/fallos/errores. General final:
2265 aprobadas, 38 omitidas, 0 fallidas/errores, 1 advertencia conocida; 1222.11 s.
No sumar selecciones solapadas. Se conservan las 38 omisiones de configuraciones
externas históricas; ninguna aceptación nueva se omite. Fallo inicial de preparación
(12 aprobadas/1 fallida) conservado; se corrigió el aislamiento de la fixture, no
se relajó el contrato productivo. Fuentes estables durante todas las ejecuciones.

RF-03 continúa PARCIAL: permanecen decisiones sobre granularidad de permisos,
multirrol, significado DOCENTE ADMINISTRADOR y ámbito administrativo de asociaciones.
No se incorporan operaciones de activación, recuperación o asignación adicionales.
Totales sin cambios: 14 IMPLEMENTADO, 8 PARCIAL, 5 BLOQUEADO.
Detalle: RF03_CONSULTA_ADMINISTRATIVA_DOCENTES.md. Evidencia:
`evidencias/rf03_consulta_20261107T044600Z/`. Código probado: HEAD 8b544f5 más cambios
locales sin commit. No se crearon migraciones ni se modificaron bases permanentes.


## 29. Consulta docente privada de preparación académica (7 de noviembre de 2026)

GET `/scheduling/sesiones/{sesion_id}/evaluacion/preparacion` se incorpora al router
Scheduling de app.main. Reutiliza ConsultaPreparacionEvaluacionSQLAlchemy y conserva
su instantánea REPEATABLE READ/READ ONLY. Cuenta activa/rol vigente desde SQL,
identidades CASES/SCHEDULING, titularidad de sesión/caso y grupos propios. Proyección
HTTP sin rúbrica, nota, respuestas ni ID de resultado; publicable siempre false.
Una matrícula no inequívoca cierra el conjunto con 503 sin datos de alumnos dudosos.

No se calculan ni publican notas, se infieren ausencias o se seleccionan intentos.
Las retiradas y participantes sin intentos se conservan como hechos y pendientes.
No hay configuración temporal predeterminada; falta de zona válida cierra con 503.
No cambia el lector interno ni se montan inicio/consentimiento o resultados.

Aceptación nueva PG17/main/JWT: 19 aprobadas, 0 omitidas/fallidas/errores, una
advertencia conocida, 24.31 s. Relacionada: 84 aprobadas, 0 omitidas/fallidas/errores,
una advertencia, 146.13 s; incluye las 19 y las 13 internas. Sin DML/flush/commit,
privacidad entre grupos, revalidación, concurrencia, versión histórica y errores
saneados. General nueva: 2284 aprobadas, 38 omitidas, 0 fallidas/errores y una
advertencia, 1294.14 s; 2322 casos JUnit. Se conservan las omisiones históricas
por configuración externa, ninguna nueva. Fuentes estables durante las tres
ejecuciones; solo se generó una evidencia BD2-04 nueva, conservada.
No sumar selecciones solapadas ni sustituir cifras históricas.

Postman: 41 operaciones OpenAPI + cuatro rutas documentales GET/HEAD; catálogo
179 solicitudes y colección docente separada de siete. Recorrido integral y
Environment permanecen iguales; los pm.test requieren Desktop, no se declaran
aprobados por validar sintaxis Node o HTTP Python. Evidencias nuevas fuera de
los JSON históricos: evidencias/preparacion_docente_http_20261107T184605Z/.

RF-13, RF-14, RF-16, RF-24 y RF-25 mantienen BLOQUEADO. Totales sin cambios:
14 IMPLEMENTADO, 8 PARCIAL, 5 BLOQUEADO. Detalle: PREPARACION_ACADEMICA_DOCENTE_HTTP.md.
El contrato funcional propuesto de Evaluation queda intacto como antecedente;
este incremento acredita su siguiente paso lector, no aprueba sus políticas.

## 30. Motor técnico por preguntas (7 de noviembre de 2026)

Fuente vigente para este incremento: instrucciones expresas del usuario RF-13/RF-24.
Todas las preguntas pesan igual; ramas inaccesibles excluidas; rutas completas de
igual longitud y perfil de criterios; pendientes al vencer cero; Decimal y único
redondeo final ROUND_HALF_UP a dos decimales. No se adopta el promedio de todas
las ramas descrito como propuesta anterior. El contrato propuesto se conserva.

Opt-in PREGUNTAS_100_V1 en la rúbrica existente. Publicación valida grafo/puntajes
bajo el lock raíz; guard existente conserva inmutabilidad. Nuevas valoraciones
no representables exactamente en NUMERIC(5,2) se rechazan antes del INSERT; no se
reescalan puntajes históricos. Sin rutas de notas nuevas ni cambios al ER/ORM.

Cálculo interno autorizado reutiliza CalculadorRubrica y Strategy completa/parcial.
La persistencia NUEVA no está implementada: id_nivel obligatorio y aporte NUMERIC
por criterio no representan promedios arbitrarios sin inventar niveles/redondeos.
Se devuelve persistido=false, oficial=false. No hay segundo almacén de resultados.

Relacionado final: 212 aprobadas, 0 omitidas/fallidas/errores, una advertencia
Starlette conocida; incluye 39 nuevos. General nueva: 2323 aprobadas, 38 omitidas,
0 fallidas/errores, una advertencia, 1290.02 s; 2361 casos JUnit. Se conservan las
omisiones históricas por configuración externa, ninguna aceptación nueva omitida.
Fuentes sin cambios durante la ejecución; se conserva la evidencia BD2-04 generada.
No sumar ejecuciones
solapadas. Fallos intermedios y JUnit se conservan en evidencias/motor_preguntas_20261107/.

RF-13 y RF-24 pasan de BLOQUEADO a PARCIAL por el cálculo técnico ya acreditado;
no se acredita almacenamiento de la nueva fórmula ni cierre académico completo.
Estado vigente de las 27 filas: 14 IMPLEMENTADO, 10 PARCIAL, 3 BLOQUEADO.
Los totales 14/8/5 de secciones anteriores corresponden a sus cortes históricos.
RF-14, RF-16 y RF-25 conservan BLOQUEADO. Detalle: RF13_RF24_MOTOR_PREGUNTAS.md.

## 31. Persistencia exacta por preguntas (7 de noviembre de 2026)

Motor protegido en checkpoint 2a79dc7d2e8937129932e9f8f10c962c2c042cd9. Los
cambios de persistencia son posteriores y sin commit. Esta sección actualiza el
bloqueo técnico descrito en el corte histórico §30; no se inventaron niveles.

Una cabecera resultado_intento por intento, con ámbito TECNICO no oficial, más
resultado_calculo_preguntas, resultado_pregunta y resultado_criterio_exacto. NUMERIC
sin precisión restrictiva para sumas/intermedios, contribuciones como enteros
numerador/denominador, ROUND_HALF_UP solo final. Revisión 20261107_question_results
sobre 20261106_consent_versions; 36 tablas físicas, sin cambiar el ER28 original.
Legacy LABORATORIO y sus detalles/niveles permanecen intactos y legibles.

Se acredita cálculo/escritura/lectura independiente bajo una UoW, fuente histórica,
idempotencia y concurrencia, rollback real SQL y restricciones diferidas. La
consulta docente main/JWT recupera solo disponibilidad técnica, sin notas ni DML.
No cambia finalización 9A ni se añade cálculo automático, rutas o publicación.

Focalizada: 256 aprobadas, sin omisiones/fallos/errores, una advertencia; incluye
44 nuevas PG17. Esquema final: 215 aprobadas, sin omisiones/fallos/errores, una
advertencia. General final: 2367 aprobadas, 38 omitidas, 0 fallidas/errores, una
advertencia, 1365.04 s (2405 casos JUnit). No sumar ejecuciones solapadas.
Se conserva la primera general con un fallo de comparación de metadata histórica;
se corrigió el filtro de objetos posteriores y se acreditó su ausencia en la revisión
antigua, sin omitir controles de la cabeza actual. Logs/JUnit de ambos intentos
permanecen disponibles. Fuentes estables durante pytest; laboratorios propios limpios.
Evidencias: evidencias/persistencia_preguntas_20261107/.

RF-13/RF-24 conservan PARCIAL por los límites de producto, ausencias y consolidación;
RF-14/RF-16/RF-25 siguen BLOQUEADO. Totales vigentes: 14 IMPLEMENTADO, 10 PARCIAL,
3 BLOQUEADO. Detalle, migración y comandos: RF13_RF24_PERSISTENCIA_EXACTA.md.


## 32. Consulta docente de resultados técnicos (7 de noviembre de 2026)

Persistencia exacta protegida en `6fcbea054d0f141e3e245d0198ae5336273f824e`.
La consulta GET `/scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico`
está registrada en main para DOCENTE activo y ámbito persistente de sesión, caso,
grupos, matrícula, participación e intento. Reutiliza preparación y repositorio
canónico bajo REPEATABLE READ/READ ONLY. Solo recupera resultados existentes,
oficial=false; Decimal y fracciones como cadenas exactas. No expone fuentes de
política/código ni datos personales. Estudiante, docente ajeno y administrador sin
rol docente no reciben acceso. 404 si el intento autorizado aún no tiene resultado.

Se acredita con JWT real y PG17 nuevo: 293 aprobadas en focalizada/relacionada,
sin omisiones/fallos/errores, una advertencia conocida. El laboratorio TCP ejecutó
9 solicitudes guardadas, sin atribuir ejecución de pm.test. General final: **2391
aprobadas, 38 omitidas, 0 fallidas, 0 errores**, una advertencia conocida Starlette,
1385.91 s; 2429 casos JUnit. Incluye las 24 nuevas. Fuentes estables durante pytest
y cero contenedores propios restantes. Las 38 omisiones conservadas requieren URLs
o configuración externa; ninguna aceptación nueva omitida.
No se suman ejecuciones solapadas. Informe: RESULTADO_TECNICO_DOCENTE_HTTP.md.

RF-13/RF-24 continúan PARCIAL: lectura técnica docente disponible, sin nota oficial.
RF-14/RF-16/RF-25 conservan BLOQUEADO. No cambia cierre de intentos ni se introduce
cálculo automático: falta la composición explícita y recuperable del comando tras
cierre. Sin cambios de clasificación; 14 IMPLEMENTADO, 10 PARCIAL, 3 BLOQUEADO.


## 33. Operación explícita después del cierre (7 de noviembre de 2026)

Consulta protegida en checkpoint LOCAL 3aa1c160a02633722572f4e994ef38312c1a8b1f.
POST en la misma ruta resultado-tecnico, sin body/query, exige JWT/cuenta DOCENTE
vigentes y ámbito persistente bloqueado de sesión/caso/grupo/participación/intento.
Reutiliza autorización transaccional de feedback sin escribir valoraciones, UoW,
estrategias, motor y repositorio exactos. No suplanta al alumno ni habilita permisos.

Cierre HTTP -> commit independiente -> POST técnico -> commit Evaluation -> nueva
Session READ ONLY. Fallo SQL previo revierte solo Evaluation; fallo de lectura
posterior permite recuperar el resultado confirmado. Reintentos concurrentes
conservan ID, fecha y hash, sin notas oficiales/avisos de calificación. Worker y
finish no se modifican. Un FINALIZADO sin FIN sigue sin evaluarse automáticamente;
VENCIDO conserva PARCIAL y ceros pendientes sin respuestas ficticias.

Focalizada/relacionada: 346 aprobadas, 0 omitidas/fallidas/errores, una advertencia,
283.29 s. Incluye 25 nuevas; cierre y respuestas por HTTP real, ambas ramas,
rollback, recuperación poscommit, concurrencia y competencia con worker/auditoría.
TCP: 13 solicitudes guardadas aprobadas, una cabecera. No ejecución pm.test.
General final: 2416 aprobadas, 38 omitidas, 0 fallidas/errores, una advertencia,
1411.03 s, 2454 casos JUnit; las 25 nuevas aprobaron. Omisiones históricas por
configuración externa, ninguna nueva artificial. Fuentes estables, laboratorios
propios limpios. No sumar suites solapadas; fallos intermedios conservados.

RF-13/RF-24 siguen PARCIAL: se cierra el tramo técnico soportado, no consolidación,
publicación, ausencias/rectificaciones o cierre voluntario incompleto. RF-14/16/25
siguen BLOQUEADO. Totales sin cambios: 14 IMPLEMENTADO, 10 PARCIAL, 3 BLOQUEADO.
Detalle y capturas: CIERRE_TECNICO_EVALUATION.md. Sin migraciones adicionales ni
cambios de reglas, .env o bases permanentes; no se publicó el checkpoint.

## 34. Ciclo académico explícito — 8 de noviembre de 2026

20 aceptaciones focalizadas actuales y 212 de corrección de compatibilidad aprobadas;
no se suman. General final: consultar RESUMEN_GENERAL_FINAL.json en
`evidencias/implementacion_academica_20261108/`; se conservan los fallos intermedios.
RP oficial se separa de R técnico, ausencia no crea intento, retiro se excluye,
repetición exige permiso individual (cupo base no lo sustituye), publicación exige
cohorte válida y revisión/autoría expresas. Aviso interno atómico e idempotente.
GET docente y titular sin DML/flush/commit; correcciones no reescriben la versión oficial.

RF-27 IMPLEMENTADO en el contrato de aviso interno; RF-14/RF-25 PARCIAL por integración
y alcance aún pendientes. RF-13/RF-24 siguen PARCIAL por cierre voluntario incompleto
sin FIN. RF-16 continúa BLOQUEADO para Excel/PDF oficiales: no se implementan en este lote.
Conteo derivado de las 27 filas: **15 IMPLEMENTADO, 11 PARCIAL, 1 BLOQUEADO**.
No es un porcentaje de backend completo ni acreditación global de RNF.

Migración nueva 20261108_academic_publication, padre 20261107_question_results;
39 tablas físicas, DBML académico original intacto. Validada únicamente en PG17
nuevo, nunca sobre bases permanentes. Worker registra metadata compartido sin
cambiar frontera +24h respaldada por RF-19 original. No se activa inicio/consentimiento
en main ni se reconoce consentimiento institucional inexistente.

Detalle de rutas, datos, fallos/correcciones, precisión, reversión y demostración:
EVALUATION_CICLO_ACADEMICO.md. General por grupos disjuntos con prueba de cobertura,
no suma de suites solapadas. Postman preparado; HTTP TCP Python acreditado, Runner no ejecutado.

Validación final §34: **2436 aprobadas, 38 omitidas, cero fallos/errores**, 2474 casos y 114 módulos en cuatro grupos disjuntos. Cuatro avisos de la misma advertencia conocida (una por proceso). No sumar focalizadas/relacionadas. Ningún nuevo skip/xfail. Ver RESUMEN_GENERAL_FINAL.json; no son cifras históricas reutilizadas.


## 35. RF-16: descargas oficiales Excel y PDF — 8 de noviembre de 2026

El GET existente admite `formato=xlsx|pdf`. Usa la publicación oficial inmutable,
verificación de huella y filas canónicas, autorización actual docente/sesión/caso/grupos
y transacción propia REPEATABLE READ / READ ONLY. No recalcula ni publica resultados.
Fechas y duración provienen exclusivamente de los intentos cerrados referidos por
esa publicación. El alumno/grupo se conserva con el nombre del snapshot, aunque el
registro actual cambie. No deduce ausencia ni reemplaza nota ausente por cero.

21 pruebas focalizadas aprobadas; 450 relacionadas aprobadas; general final
2457 aprobadas, 38 omitidas, 0 fallos/errores. Un tipo conocido de advertencia.
No sumar suites solapadas. JUnit y evidencia visual/TCP se describen en
`RF16_REPORTE_Y_BLOQUEOS.md`. Las primeras ejecuciones fallidas se conservan.
RF-16 pasa de BLOQUEADO a IMPLEMENTADO por descarga binaria real, autorización,
procedencia oficial y lectura del contenido. No cambia ningún otro RF.

Las convocatorias retiradas se identifican como antecedentes sin nota: el snapshot
oficial conserva sus UUID, no sus nombres históricos. No se consulta el nombre
actual para aparentar que fue publicado. CSV sin formato sigue cerrado. No hay
migraciones ni cambios en Evaluation/Participation, fórmulas, consentimiento o DBML.


## 36. Cierre voluntario incompleto — 8 de noviembre de 2026

Propuesta técnica explícita del equipo; no aprobación institucional atribuida a
la profesora. FINALIZADO conserva cierre inmutable y produce PARCIAL cuando no
alcanza FIN, con denominador uniforme acreditado, puntajes reales, pendientes por
cantidad a cero y sin inventar una rama. Política 2 del mismo motor; versión 1 e
historia preservadas. Cálculo no automático, publicación manual independiente.

18 focalizadas y 505 relacionadas aprobadas. General final: 2472 aprobadas,
38 omitidas, 0 fallos/errores; un tipo de advertencia conocido. No sumar suites
solapadas. Cambios, evidencia y migración reversible 20261108_voluntary_partial
en `CIERRE_VOLUNTARIO_PARCIAL.md`.
RF-13/RF-14/RF-24 avanzan en condiciones acreditadas, pero permanecen PARCIAL por
los pendientes descritos en sus filas; conteos vigentes no cambian: 16/11/0.


## Continuación RF-12/RF-23/RF-25 — 9 de noviembre de 2026

La aclaración expresa del equipo confirma que **no existe documento de consentimiento con aprobación oficial verificable ni política productiva definitiva de inicio, provisión o repetición**. No se utiliza el borrador NO APROBADO ni los valores de LAB como configuración productiva.

Se reutilizan documento/versionado/vigencia/huella/aceptación, admisión SQL, UoW e inicio existentes. Se incorpora un puerto obligatorio de aprobación documental y las composiciones privadas de consentimiento e inicio en app.main, sin provisión independiente. Los tres proveedores productivos (aprobación, inicio y vinculación) permanecen cerrados; no se elige un estado inicial ni un cupo por defecto. Una referencia de aprobación escrita en una fila no acredita aprobación institucional.

La colección complementaria y las pruebas main con JWT/PG17 usan proveedores explícitos SOLO LAB para acreditar las relaciones y transacciones. Las rutas de producción sin proveedores devuelven 503 sin insertar consentimiento, participación o intento. No se incorporan migraciones, modelos, notas ni publicación automática. Detalles, contratos y evidencia: PARTICIPATION_FASE1_MAIN_CONDICIONADO.md.

RF-12, RF-23 y RF-25 conservan **PARCIAL** en esta matriz de implementación y **BLOQUEADO** en la matriz de aceptación integral Postman. Los 16 RF acreditados previamente no se reclasifican. No son dos mediciones equivalentes. Los conteos de ejecuciones anteriores siguen siendo históricos.

Evidencia de esta continuación: 59 focalizadas y 763 relacionadas aprobadas; primera general 2492 aprobadas/38 omitidas/2 fallos por contrato histórico de ausencia de ruta. Ambos archivos se actualizaron al contrato main condicionado y su reverificación completa aprobó 41 casos. General conciliada sin solapamientos: 2494 aprobadas/38 omitidas, sin fallos/errores pendientes. Se conservan diagnósticos y la advertencia Starlette/httpx. Newman principal condicionado: 79/291; maestra 27 RF: 545/2080 y 16 APROBADOS/11 BLOQUEADOS. No se suman estas ejecuciones. Ruta de evidencia: evidencias/participation_fase1_20261109T215053Z/.


### RF-10 — continuidad contractual Angular, 9 noviembre 2026 (Bogotá)

RF-10 conserva PARCIAL en implementación y BLOQUEADO en aceptación integral. Se documentan los DTO actuales, INTEGER/UUID históricos, nulabilidad, FIN frente a cierre, errores y diferencia GET/POST al vencer. Se completan las respuestas de error de OpenAPI de decisiones/finish sin cambiar lógica ni montar nuevas rutas. Nuevas pruebas: tests/unit/participation/test_rf10_http_contract.py y tests/integration/test_rf10_angular_journey.py. Contrato: RF10_CONTRATO_ANGULAR.md.

Aceptación nueva de contrato/recorrido: 8 aprobadas; focal ampliada: 124 aprobadas sin omisiones/fallos. Newman complementario: 21 HTTP / 76 aserciones sobre main con preparación del intento SOLO LAB; regresión maestra RF-10: 32/141, estado BLOQUEADO. Son ejecuciones solapadas, no se suman. La regresión general nueva se documentará al finalizar sus cuatro particiones; no se reutiliza la conciliación anterior de 2494/38. No cambian los estados de los otros 26 requisitos.

Cierre de validación RF-10: relacionada 775 aprobadas/9 omitidas; general **nueva completa** 2502 aprobadas/38 omitidas, cero fallos/errores, 120 archivos y 2540 casos únicos en cuatro particiones sin solapamiento. Fuentes estables; advertencia Starlette/httpx conservada. No se suma con focal ni Newman y no se reutiliza la conciliación histórica 2494/38. Registro: evidencias/rf10_contrato_20261109/general_resultado.json. RF-10 sigue PARCIAL/BLOQUEADO según matriz; no cambia el estado de los otros 26 RF.


## Fase 3 — RF-03: seguridad transaccional y alcance exacto

Checkpoint RF-10 creado y verificado: c6beb6f2aefeca02fcc7a3d4d2c7bd9774b1f846; 16 rutas, sin los siete cambios previos ni alteración del respaldo. RF-10 permanece PARCIAL/BLOQUEADO según matriz; no se reabre edición de respuestas.

RF-03 original exige alta docente y asignación de roles/permisos por administrador (PDF central p.4); RN-02 p.7 exige autorización. El Inception p.4 habla de varias funciones institucionales, no define multirrol por cuenta ni un rol DOCENTE ADMINISTRADOR. No se agregan esos criterios unilateralmente. El límite real es la configuración operativa del catálogo global frente a excepciones individuales: el esquema actual tiene un rol por cuenta y rol_permiso compartido.

Se reprodujeron cuatro fallos: revocación de activo/rol tras JWT/Proxy permitía alta 201 o asignación 200. Se corrigen con identidad vigente y bloqueos compartidos de cuenta/rol en la misma UoW; política central de rol reutilizada. Cuenta inactiva rechaza 401, rol revocado 403. La revocación concurrente espera al commit cuando la operación autorizada ya tiene el lock. No cambian DTO, endpoints, ORM, migraciones ni RF-04.

Resultados actuales: nuevos 16 aprobados; focal 109 aprobados; relacionada 560 aprobados y 29 omitidos; general nueva completa 2518 aprobados y 38 omitidos, cero fallos/errores. Los cuatro diagnósticos fallidos se conservan; no son aprobaciones. No sumar suites solapadas. Evidencia: evidencias/rf03_fase3_20261109/. Informe: RF03_AUTORIZACION_TRANSACCIONAL.md. RF-03 conserva PARCIAL en implementación y BLOQUEADO en aceptación integral; no cambian los estados de los otros 26 requisitos.


## Fase 4 — RF-03 preservado y selección privada RF-04

Checkpoint RF03: c2cad50c444175de04fb803badeaf91f3befdf0f, 48 rutas; siete cambios anteriores fuera del commit. Se verificó íntegramente el respaldo de 5701 archivos sin alterarlo. Los cuatro diagnósticos RF03 corregidos vuelven a aprobar en la nueva general.

RF04 original (PDF p.4; RN05 p.7) exige espacio y estudiantes autorizados al agendar. Se reprodujo y corrigió el listado global de espacios: GET /scheduling/espacios ahora consulta solo grants explícitos del docente JWT, con formato id/nombre y orden estable. No hay nuevos endpoints, modelos ni migraciones. No se deduce el INTEGER desde un UUID ni se concede un recurso por haberlo creado.

Focal final 18 aprobadas; relacionada final 139; general final NUEVA COMPLETA 2525 aprobadas/38 omitidas/cero fallos o errores, 123 archivos y 2563 casos únicos, fuentes estables. Se conservan diagnóstico inicial de tres fallos y primera general de dos fallos unitarios, corregidos mediante adaptación del fixture sin relajar los esperados. Advertencia Starlette/httpx conservada; no sumar suites. Newman de 27 carpetas: 556 HTTP/2118 aserciones, sin fallos técnicos. RF04:16/53. Evidencia: evidencias/rf04_fase4_20261109/.

RF04 continúa PARCIAL en esta matriz y BLOQUEADO en aceptación integral: asignacion_caso requiere contrato productivo de fecha_limite_ingreso, intentos_base y estado; grupos/matrículas/grants/asignación siguen preparados administrativamente. Newman programa una sesión y convoca sobre otra sesión preparada con asignación LAB; no acredita todavía el enlace íntegro de la sesión recién creada por API. No cambian los estados de los otros 26 RF: aceptación documentada 16 APROBADOS/11 BLOQUEADOS. Detalles y siguiente decisión: RF04_SELECCION_ACADEMICA_Y_BLOQUEOS.md.


## Fase 6 — RF13 y DTO de programación, 10 noviembre 2026

HEAD verificado 8e1e8a67f6e4ba387b9d0650059e6fe654c704d9. Nueva auditoría dirigida: RF13/RN17/UC05 originales frente a cálculo técnico posterior. Quedaron resueltos para PREGUNTAS_100_V1 escala, pesos, ramas, ROUND_HALF_UP y persistencia exacta; no repetirlos como incógnitas técnicas. No se exige publicación oficial para demostrar calcular/almacenar. Siguen pendientes la aplicabilidad académica de otras rúbricas y la conciliación del flujo UC05 con el comando docente explícito; no se activa finish/worker ni se recalifica historia.

Resultados NUEVOS: 39 focales y 108 relacionadas aprobadas, sin omisiones/fallos/errores; Newman RF13:32 solicitudes/141 aserciones, resultado persistido=1/publicaciones=0, PG17.11. Ocho diagnósticos de DTO sobre main/JWT/PG17 verifican extras ignorados con 201 solo de sesión, y rechazo 422/403 previo a DML para validación conocida/rol. No son aceptación de ignorar extras ni cumplimiento RF04. Se conservan logs/JUnit y advertencia Starlette/httpx. No sumar suites.

No se modifica código productivo ni el DTO: 25 solicitudes de programación en 12 colecciones usan claves declaradas, pero el contrato vigente no ordena rechazar todo extra y no hay garantía sobre clientes externos. Un extra='forbid' requiere aprobación del cambio API. General 2525/38 y regresión de los otros 26 RF son antecedentes verificados, NO nuevas ejecuciones. Estado funcional sin reclasificaciones:16 APROBADOS/11 BLOQUEADOS en aceptación previa; RF13 sigue PARCIAL/BLOQUEADO según matriz. Informe: RF13_AUDITORIA_Y_DTO_PROGRAMACION_20261110.md; evidencia:evidencias/rf13_fase6_20261110/.


## Fase 7 — RF14: consulta privada y corrección de resultado pendiente

Checkpoint documental RF13:48b0bfb61839684e5b3e9fbfdfc88b0bcd204972, cuatro documentos exactos. RF13 sigue PARCIAL/BLOQUEADO por sus contratos, sin otra fórmula ni orquestación automática. Se conservan los ocho cambios anteriores y el DTO de programación.

RF14 original exige nota/aciertos/errores/explicaciones al terminar; la confirmación funcional posterior permite provisional configurable y prohíbe correctas durante sesión activa. Se acredita el GET existente sobre main con JWT/PG17, selecciones históricas correctas e incorrectas, parciales, ausencia publicada, rol/cuenta/titularidad, recarga/concurrencia y RR/READ ONLY sin DML/flush/commit. Solo se corrige la captura que convertía ausencia de resultado de Participation en503: ahora404 sin calcular ni publicar, coherente con el GET docente. No hay endpoint, tabla, migración o política nuevos.

Resultados nuevos finales:13 focales;180 relacionadas; general completa2538 aprobadas/38 omitidas/cero fallos o errores,2576 casos únicos y124 archivos disjuntos. Primer diagnóstico13:10 aprobadas/3 fallidas (dos fixtures y el error503real), preservado. Newman RF14final19/68; selección final27RF560HTTP/2134pm.test, sin fallos técnicos; el primer RF14fallido por sintaxis JS se conserva y se sustituye solo esa carpeta, sin sumar. Advertencia Starlette/httpx conservada.

RF14 pasa a IMPLEMENTADO/APROBADO en los respectivos criterios de esta auditoría; los otros26 estados no cambian. Implementación17/10/0; aceptación17 APROBADOS/10 BLOQUEADOS. Eso no significa backend terminado, despliegue permanente ni aprobación institucional de las fórmulas. Contratos y criterios:RF14_CIERRE_CONTROLADO_20261110.md; guía Angular sin prueba de navegador:RF14_CONTRATO_ANGULAR.md; evidencia:evidencias/rf14_fase7_20261110/.

## Candidato integrado del 11 de noviembre de 2026

RF-03, RF-04, RF-20 y RF-21 avanzan con evidencia actual. Los otros 23 estados se conservan. General final nueva 2611 aprobadas y 38 omitidas, cero fallos y errores. Newman 27 carpetas, 569 solicitudes y 2166 aserciones, 21 APROBADOS y 6 BLOQUEADOS. La recepción SMTP acreditada corresponde a un capturador local. Las ejecuciones anteriores se conservan como antecedentes. La documentación y los bloqueos concretos están en CANDIDATO_INTEGRADO_20261111.md.
