# Auditoría de cobertura y siguiente incremento — 5 de noviembre de 2026

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
| RF-13/24 | No especifica toda la fórmula | Confirmados escala 0–100, pesos iguales y cero por pendientes al vencer. No están definidos mapeo de niveles, agregación, redondeo necesario y consolidación. |
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
| RF-03 Administrar docentes, roles y permisos | ServicioAdministracionUsuarios, repositorios SQL, ProxyAdministracionUsuarios y login personal reutilizado | POST `/api/v1/identity/docentes`, PUT `/docentes/{id_docente}/autorizaciones`; sí | PARCIAL | `tests/integration/test_main_staff_login.py::test_admin_ingresa_crea_docente_con_hash_y_docente_ingresa_sin_crear_vinculos`: HTTP main/PG17, alta, login y asignación compatible; rechazo de alteración global del catálogo | Login administrativo ya acreditado; sigue pendiente bootstrap institucional y definición de granularidad individual/multirrol. No declarar completo por añadir autenticación. Los 29 tests antiguos condicionados a URL siguen omitidos. Sección 16. |
| RF-04 Asociar espacio y estudiantes | Scheduling/Identity: espacio_academico, docente_espacio_academico, grupo_academico/grupo_estudiante, asignacion_caso y convocatoria; `convocation_management.py::_autorizar` | `/scheduling/espacios`, `/sesiones`, `/sesiones/{id}/convocatorias`; sí | PARCIAL | `tests/integration/test_convocation_management_http.py::test_alta_exige_ambito_academico_persistente` PG | Asociación/verificación sí; altas de matrículas, puente de asignación y grants siguen preparados administrativamente en fixtures. Definir su proceso autorizado, sin autovinculación ni inferir grupo desde espacio. |
| RF-05 Registrar estructura del caso | Cases: `CasoService.crear_borrador`, `ConstructorCaso`; caso/version_caso/escenario, estimado e historia | POST/PUT `/api/v1/cases[/{version_id}]`; sí | IMPLEMENTADO | `tests/integration/test_cases_graph_authoring.py::test_http_crear_configurar_publicar_y_consumir_misma_version` PG, contenido por API | Completar dependencia transversal de login personal. La preparación de nuevas ediciones históricas por ORM en algunos tests NO acredita un endpoint de nueva edición. |
| RF-06 Contextos y preguntas por escenario | Cases: `CasoPayload`, `CasoService._construir`, escenario/pregunta | POST/PUT/GET `/api/v1/cases`; sí | IMPLEMENTADO | Mismo test HTTP PG de autoría; `tests/unit/cases/test_builder.py` valida construcción | Autoría guarda estructura; ejecución multipregunta sigue bloqueada y se clasifica en RF-10. No confundir guardar una lista con poder navegarla. |
| RF-07 Preguntas y alternativas correctas/incorrectas | Cases: `OpcionSchema`, Builder/validadores; pregunta/opcion_respuesta.es_correcta | DSL JSON y detalle en `/api/v1/cases`; sí | IMPLEMENTADO | Autoría HTTP PG anterior y `tests/unit/cases/test_validators.py` | Mantener varias alternativas; una selección por pregunta en Participation no significa una sola alternativa disponible. Aceptación: flags y referencias se recuperan fielmente. |
| RF-08 Justificar cada alternativa | Cases: OpcionSchema.justificacion y validadores; opcion_respuesta | DSL autoría y detalle docente; sí; explicación al estudiante todavía condicionada a RF-14 | IMPLEMENTADO | `tests/integration/test_evaluation_feedback.py::test_respuesta_incorrecta_usa_su_justificacion_no_la_de_otra_opcion` PG; validadores | Registro académico sí. No confundir este RF con publicación estudiantil de nota/explicación final. |
| RF-09 Borrador, validar/publicar y archivar | Cases: `CasoService.publicar/archivar`, cadena validación, repositorio de grafo/guards PG | POST `/api/v1/cases/{version_id}/publish` y `/archive`; sí | IMPLEMENTADO | Autoría HTTP PG; `tests/integration/test_cases_guard_migration.py::test_revision_real_preflight_DML_locks_downgrade_y_reupgrade` | Recorridos soportados: una pregunta/escena y sin ciclos alcanzables. No rellenar grafos históricos ficticios; decidir semántica de recorridos pendientes para ampliar publicación ejecutable. |
| RF-10 Consultar contextos y responder; aclaración posterior INMUTABLE | Participation/Cases: `current_scenario.py`, grafo SQL y Facade; intento/paso_simulacion y guard PG | GET `/api/v1/attempts/{id}/current-scenario`, POST `/decisions/{decision_id}`; sí. PUT no montado | PARCIAL | `tests/integration/test_main_decisions.py::test_primer_registro_inmutable_progreso_y_siguiente_escenario_main` PG/JWT real | Funciona para intento existente y grafo soportado. Inicio productivo bloqueado; faltan decisiones sobre varias preguntas/ciclos/revisitas. Actualizar RF documental para no pedir edición prohibida. |
| RF-11 Guardar respuestas y progreso privado sin revelar corrección | Participation: repositorio/UoW, `progress_query.py`, `progress.py`; paso_simulacion único por intento/pregunta | POST decisiones y GET `/api/v1/attempts/{id}/progress`; sí | IMPLEMENTADO | `tests/integration/test_main_progress.py::test_progreso_efectivo_repetido_sin_dml_flush_commit`; `test_main_decisions.py::test_registros_concurrentes_conservan_una_sola_seleccion` PG | GET proyecta vencimiento sin persistir; escritura separada. Requiere zona histórica explícita y un intento ya existente. No autoriza inicio productivo. |
| RF-12 Inicio/fin, nota y feedback por pregunta | Participation start/provision, consentimiento versionado interno Identity, UoW y guard previo a INSERT P; Evaluation técnica existente | POST finish sí; provisión/inicio/aceptación/resultados oficiales fuera de main | PARCIAL | `test_consent_before_provision.py`: 24 casos PG17, fuente LAB, ausencia de INSERT, aceptación/consulta/rollback/concurrencia; general actual 2126/38. Sección 19 | Orden corregido internamente; falta documento/fuente oficial, procedencia durable del consentimiento, señal de admisión y demás contratos productivos. No equiparar fuente LAB con autorización real ni resultado técnico con nota oficial. |
| RF-13 Calcular y almacenar nota por rúbrica | Evaluation dentro de Participation: ServicioEvaluacion, Strategy/CalculadorRubrica, `academic_policy.py`, repositorio resultados; procedencia inmutable | Motor interno; rutas generales de resultados NO montadas | BLOQUEADO | `tests/integration/test_academic_policy.py::test_sin_mapeo_agregacion_no_hay_nota_academica_completa`; `test_evaluation_result_storage.py::test_evaluar_guardar_y_recuperar_otra_session` PG con política LAB | Definir nivel→logro, agregación preguntas→criterio y precisión/redondeo necesario. Aceptación: resultado real reproducible con definición aprobada, no convención de fixture. |
| RF-14 Mostrar nota/aciertos/errores/explicaciones tras cerrar | Evaluation: servicio y `cases/application/answer_feedback.py`, DTO/API provisional | `/participations/{p}/attempts/{i}/result` solo router no montado; main no publica resultados | BLOQUEADO | `tests/integration/test_evaluation_feedback.py::test_feedback_no_expuesto_a_otro_actor_o_contexto`; pruebas API Participation con fakes no acreditan publicación | Primero cálculo/persistencia oficial y autorización/visibilidad; integrar lector aprobado sin devolver resultados LAB. |
| RF-15 Seguimiento docente por estudiante y caso | Identity `infrastructure/followup.py::ConsultaSeguimientoSQLAlchemy`, ProxySeguimiento y servicios existentes; joins P/I/pasos/feedback | Tres GET `/api/v1/identity/seguimiento/casos`, `/casos/{id}/participaciones`, `/participaciones/{id}` en main | IMPLEMENTADO | Pruebas históricas de `test_teacher_followup_http.py` y 11 casos actuales PG17 sobre main en `test_main_teacher_followup.py`: recorrido, versión histórica, privacidad, ámbito, concurrencia y cero DML/flush/commit; sección 14 | Lectura sin commit acreditada; no publica notas ni RF-16. Login personal sigue pendiente y JWT docente de aceptación se emite solo dentro del laboratorio. No equivale a integración productiva completa desde credenciales. |
| RF-16 Descargar resultados, parciales y ausentes | ServicioReportes/CSV reforzado: rechaza duplicados/contradicciones y nota fuera de 0–100; consulta cruda no compuesta, `reportes=None`, sin resultado_participacion integrado | GET `/api/v1/identity/seguimiento/sesiones/{id}/reporte` registrado y cerrado con 503 para docente válido | BLOQUEADO | Seis pruebas de componente `test_report_integrity.py` con CSV sintético explícito; siete PG17/main `test_main_report_closed.py` de cierre seguro, autorización, padrón sin P, concurrencia y cero escrituras; sección 15 | La mejora no publica un reporte ni certifica procedencia oficial. Faltan padrón académico/corte/retiros, ausencia confirmada, consolidación y notas oficiales. No usar resultado_intento LAB como fuente alternativa; formato institucional pendiente. |
| RF-17 Registrar/asociar rúbrica | Cases: ConstructorCaso, `rubrica`, `criterio_rubrica`, `nivel_rubrica`, `valoracion_opcion` por versión | DSL `/api/v1/cases`; sí | IMPLEMENTADO | Autoría HTTP PG y `tests/integration/test_evaluation_persisted.py::test_evidencias_historicas_reales_sin_calificacion` | Historia preservada; ponderación efectiva igualitaria aprobada no reescribe rúbricas anteriores. La semántica de puntajes para evaluar sigue pendiente en RF-13. |
| RF-18 Programar horarios, duración, lugar y mensaje con caso publicado | Scheduling `programming_access.py::programar_sesion_autorizada`; docente_espacio_academico/sesion_programada con versión UUID exacta | POST `/scheduling/sesiones`, GET listado/detalle; sí | IMPLEMENTADO | `tests/integration/test_session_programming_http.py::test_programacion_autorizada_persiste_datos_y_uuid_de_scheduling`, `test_publicacion_posterior_no_sustituye_uuid_de_version_programada` PG | Grants son administrativos, no autovinculación; falta login personal transversal. No se deduce autorización de matrícula ni RF-22 de programar una sesión. |
| RF-19 Estados de sesión y cierre automático +24h | Scheduling State, coordinador transaccional, Observer SQL y worker_runner; evento_auditoria/notificacion | POST `/scheduling/sesiones/{id}/estado` en main; cierre automático en proceso separado/perfil worker optativo | IMPLEMENTADO | Diez casos PG17 de State, seis de atomicidad y cuatro nuevos de proceso real en `test_worker_process.py`, incluidos dos ciclos separados por 60 s, fallo/reintento y competencia de procesos; sección 12 | Comportamiento funcional acreditado sin dobles en los procesos. Activar/supervisar el worker es una condición de despliegue: no arranca dentro de main ni se instaló en un servidor permanente. Callbacks externos/correo siguen fuera de esta garantía |
| RF-20 Código individual y validación/notificación | Scheduling `crear_convocatoria`, hash y Identity ValidadorConvocatoriaScheduling | POST convocatorias; login real; `/scheduling/validar-ingreso` exige habilitación real; sin política temporal suficiente permanece cerrado, sin P/I | PARCIAL | `tests/identity/test_student_login_scheduling.py::test_login_rechaza_credenciales_o_titularidad_invalidas`; `test_convocation_management_http.py::test_altas_individuales_y_avisos_personalizados_sin_correo_ni_codigos_persistidos` PG | Código se entrega una vez al docente y se guarda hash. Falta entrega segura por correo. No tratar validación de código como aprobación temporal de ingreso. |
| RF-21 Correo convocatoria/altas/retiros | Scheduling convocation_management, avisos atómicos y retiro lógico; notificacion/convocatoria | POST/DELETE convocatorias y GET `/scheduling/notificaciones`; sí | PARCIAL | `tests/integration/test_convocation_management_http.py::test_retiro_revoca_login_ingreso_y_escritura_con_jwt_previo_sin_borrar_historia`, `test_fallo_tras_persistir_aviso_revierte_y_reintento_recupera` PG | Falta proveedor/remitente/URL institucional y contrato de entrega recuperable del código (hash no reconstruible). Aviso interno no prueba SMTP ni exactamente-una-vez externo. |
| RF-22 Restringir ingreso tardío | Scheduling admission.py, coordinador RF-19, JWT/matrícula/asignación SQL y versión histórica | POST /scheduling/convocatorias/{id}/espera; GET /scheduling/convocatorias/{id}/admision; POST /scheduling/validar-ingreso; sí en main | IMPLEMENTADO | 32 aceptaciones main/JWT real/PG17, test_waiting_admission.py; regresión focal 606 sin fallos. Sección 20 | Cumplido para sala aprobada, concesión previa y recuperación, no presencia online. No habilita P/I ni consentimiento productivo. Despliegue de migración aún no realizado. |
| RF-23 Tiempo individual máximo y conservación | Intento, reloj inyectado, snapshot duracion_concedida_segundos, cierre y guards | Operaciones 9A de intento existente sí; nuevo inicio no | PARCIAL | `tests/integration/test_main_finish.py::test_cierre_confirma_vencimiento_que_get_no_persistio`; `tests/integration/test_attempt_start.py::test_inicio_real_y_segunda_session_con_version_y_duracion` PG, inicio LAB | Rechazo por tiempo y respuestas conservadas sí; aprobar inicio y coordinación con fin de sesión. Proyección VENCIDO no equivale a transición persistida ni nota PARCIAL. |
| RF-24 Incompletos y ausencias | Strategy PARCIAL/AUSENCIA, PoliticaAcademicaConfirmada: cero por pendiente al vencer, sin selección/intento ficticio | Servicio interno; sin ruta oficial en main | BLOQUEADO | `tests/integration/test_academic_policy.py::test_vencido_recibe_ceros_sin_opciones_ficticias`, `test_ausencia_misma_regla_sin_intento_y_sin_nivel_cero_inventado` PG/unitarias según caso | Mapeo/agregación, cierre voluntario incompleto, confirmación/persistencia de ausencia y resultado sin intento. No copiar nota anterior por la frase «misma nota». |
| RF-25 Repetición solo por creador y nunca sesión finalizada | Identity ProxyExcepciones sin proveedor; Participation start/permisos/locks; guard creador corregido en 9B | POST `/api/v1/identity/excepciones/repeticiones` registrado pero 503; inicio extra solo LAB | BLOQUEADO | `tests/integration/test_attempt_permission_creator.py::test_permiso_exige_identidad_cases_inequivoca_del_creador` PG; extra positivo HTTP es LAB | Aprobar cantidad/vigencia/consumo y condiciones excepcionales, conectar UoW común; preservar 403 cuando creador no se verifica. |
| RF-26 Valoración individual editable y privada | Participation `individual_feedback.py`, Identity seguimiento; UNIQUE retroalimentacion_docente.id_participacion, aviso atómico | POST/GET `/api/v1/identity/seguimiento/participaciones/{id}/feedback`; sí | IMPLEMENTADO | `tests/integration/test_teacher_followup_http.py::test_feedback_se_crea_edita_y_recupera_sin_duplicar_desde_otra_sesion`; `test_student_general_feedback_http.py::test_titular_lee_actualizacion_confirmada_sin_escrituras_ni_notas` PG | Respeta visibilidad: al menos un intento y todos cerrados. Falta decisión de entrega en ausencia sin intento; no cambiarla silenciosamente. Login personal transversal pendiente. |
| RF-27 Avisos de nota y feedback | Aviso RETROALIMENTACION persistido con feedback; emisor CALIFICACION HTTP ahora cerrado; no otro sistema | GET bandeja sí; POST `/scheduling/calificaciones/notificar` registrado pero 503 tras JWT/rol; no nuevas rutas | PARCIAL | `tests/integration/test_student_general_feedback_http.py::test_aviso_persistido_destinatario_real_y_bandeja_privada`; nuevo `test_grade_notice_closed.py` sobre main/PG | Feedback interno acreditado. Nota oficial requiere resultado publicado y destinatario/propiedad verificados en misma transacción; reconciliar UUID API/INTEGER real por contrato aprobado. Cierre seguro no equivale a funcionalidad de publicación completa. |

### Lectura cuantitativa sin porcentajes inventados

La clasificación actual contiene **13 IMPLEMENTADO, 9 PARCIAL y 5 BLOQUEADO**;
ningún RF está enteramente sin componentes. No hay pesos de esfuerzo aprobados
para convertir esas categorías a un porcentaje global. **13/27 = 48,1 %** es
únicamente la proporción de RF con comportamiento acreditado bajo la definición
anterior, no un porcentaje de código, despliegue ni recorridos de producto cerrados.
Los trece siguen sujetos a las dependencias transversales expresadas. El login
de personal ya tiene aceptación HTTP SQL, sin certificar su operación institucional.
La estimación conversacional previa de 80–85 % era
orientativa sobre construcción técnica; esta auditoría no la certifica como
cumplimiento contractual y no debe emplearse como cifra de aceptación.

## 4. Estado por módulo y disponibilidad

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
