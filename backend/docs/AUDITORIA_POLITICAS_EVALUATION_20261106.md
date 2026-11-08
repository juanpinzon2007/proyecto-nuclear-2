# Checkpoint y políticas de calificación de Evaluation

> Documento histórico de su fecha. Se conserva el análisis/propuesta original;
> los bloqueos y menciones «sin commit» se refieren a aquel corte. Para las decisiones
> posteriores efectivamente implementadas ver EVALUATION_CICLO_ACADEMICO.md y la
> matriz vigente §34. Publicarlo no constituye aprobación institucional.

2026-11-06, America/Bogota. Auditoría dirigida; sin cambios de algoritmo, ORM,
migraciones, rutas o datos. No es una aprobación académica.

## 1. Checkpoint protegido y alcance

Commit local `8b544f5d7f370076756d38b1d594fb77ab21f31b`:
`feat(evaluation): preparar consolidacion academica por sesion`.
Padre: `48c2638b3d0b90fe18016fe56024d05237765a4a`.
Se verificaron las seis huellas del manifiesto de la entrega anterior, los diffs,
las evidencias JUnit y el contenido íntegro del índice. Solo contiene:

- backend/app/modules/participation/application/evaluation_readiness.py
- backend/app/modules/participation/infrastructure/evaluation_readiness.py
- backend/app/modules/participation/infrastructure/result_repository.py
- backend/tests/integration/test_evaluation_readiness.py
- backend/docs/EVALUATION_PREPARACION_SESION.md
- backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md

No contiene evidencias, configuración privada ni credenciales. Los marcadores
`sin-login-LAB` y correos aleatorios de fixture.test son preparación sintética,
no credenciales operativas. Índice comprobado con rutas explícitas y
`git diff --cached --check`. No push, merge, PR ni segundo commit.

## 2. Fuentes, autoridad y límites

Las páginas citadas son posiciones PDF, empezando en 1. Se extrajo el texto completo
de los tres PDF con PyMuPDF ya instalado en el Python del sistema, sin instalar
dependencias ni modificar .venv. Se inspeccionaron visualmente las páginas 7, 14 y
31 del documento de Ingeniería para distinguir reglas, tablas y propuestas.

| Fuente | Ubicación exacta | Uso y límite |
|---|---|---|
| S1: `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf` | p.4 RF-13/14/16/17; p.5 RF-24/25/27; p.7 RN-14/15/16/17/18/19; p.11 UC-05; p.12 UC-07; p.14 invariantes; pp.27-31 modelo/DSL/OCL | Base funcional. VALORACION_OPCION se presenta como propuesta técnica; p.31 titula sus invariantes OCL como propuestas. El diagrama o el esquema no completan una fórmula aprobada. |
| S2: `_referencias_locales/Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf` | p.6 RF-13/24; p.7 RF-16/27; p.32 §5.7 Strategy; p.37 §6.3 | Exige rúbrica común, evidencia y ausencia sin intento iniciado. El propio documento distingue propuesta de diseño e implementación detallada. No especifica una fórmula de agregación. |
| S3: `_referencias_locales/Agile Inception SPS.pdf` | p.3 §1.1/1.3; p.8 RF-16/17; p.9 §4.3; p.25 mitigación de errores de calificación | Declara pendientes ejemplos precisos de parciales, ausencias y redondeo. Valores no aprobados se califican de propuestos. No aporta un algoritmo alternativo que cierre esos pendientes. |
| S4: respuestas de Diana Ma Valencia trasladadas por el usuario | `backend/docs/FASE_8C_EVALUATION_INTEGRACION.md:17`, §1-2, registro del 2026-11-02; conversación del proyecto | Fuente posterior para selección única, escala 0-100, igualdad entre criterios y cero por preguntas pendientes al vencer. El archivo registra la comunicación del usuario; no contiene una comunicación institucional firmada adjunta. No se desconoce la autorización funcional recibida. |
| S5: decisiones posteriores del equipo comunicadas por el usuario | Prompt del incremento anterior de Evaluation, etapa 2; copia trazable en `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`, §26 | Publicación de toda la sesión, confirmación expresa docente de ausencias, autorización de publicación por docente con ámbito, repeticiones individuales y ninguna publicación automática al finalizar. Son decisiones funcionales del equipo; no aprobación de algoritmos no expresados. |
| S6: ER académico aprobado | `backend/app/modules/identity/reference/sps.dbml:163` rubrica; `:170` criterio_rubrica; `:177` nivel_criterio; `:269` resultado_intento; `:277` resultado_criterio; `:293` resultado_participacion | Define almacenamiento conceptual, incluido logro_porcentaje. No demuestra que puntaje del ORM actual equivalga a ese porcentaje, ni una política de consolidación. No se modifica el original. |

Implementaciones y tests son evidencia de comportamiento, no fuentes de aprobación.
Una rúbrica sintética no prueba que todos los casos reales usen sus valores.
No se consultó ninguna base permanente para inferir reglas a partir de datos.

## 3. Matriz de las ocho políticas

En esta tabla, `P/` significa backend/app/modules/participation/; las referencias
T01-T16 se desarrollan en la sección 5 con métodos y archivos exactos.

| Regla | Fuente y comportamiento exigido | Implementación actual | Pruebas y alcance | Información ausente | ¿Desarrollable sin decisión académica nueva? |
|---|---|---|---|---|---|
| 1. Respuesta a nivel | S1 p.4 RF-13/17, p.14 Rubrica/ValoracionOpcion, p.27 y S4. Calificar con la rúbrica de la versión exacta, escala 0-100 e igual peso de criterios. | `P/application/evaluation_mapping.py:23` MapeoRubricaEvaluacion; `academic_policy.py:20` ResolucionNivelesAcademicos y `:30` MapeoEscala100. Cases guarda puntajes por opción/criterio, niveles y descriptores. | T01/T02 prueban cierre seguro y preservación histórica. T03 convierte puntaje*20 SOLO LAB. | Tabla o función autorizada puntaje→nivel→logro, máximos, empates, valores sin nivel y criterio no aplicable. El booleano es_correcta no es un nivel. | Sí a validaciones y carga histórica ya existentes; NO a una conversión oficial predeterminada. |
| 2. Varias preguntas en escenario | S1 p.4 RF-06/13 y pp.29-31 DSL permiten listas; S4 fija una selección por pregunta, no una sola pregunta por escena. | `P/application/academic_policy.py:69` delega en resolver; no hay agregador académico concreto. El grafo ejecutable soportado exige una pregunta por escena. | T02/T03 muestran que falta resolución; el resolver positivo de T03 exige len(preguntas)==1 y es fixture. | Qué preguntas aportan a cada criterio, cómo combinarlas, denominador, pendientes, conflictos y nivel final si no coincide con uno discreto. | NO a media/suma/máximo ni a navegación multipregunta por deducción. |
| 3. Varios escenarios e intento | S1 p.7 RN-14/17 y S4: conservar respuestas y evaluar PARCIAL al vencer con cero por pendiente. No define pesos de escenarios ni ramas no visitadas. | `P/application/evaluation_service.py:61` _marco exige ruta disponible y total conocido; `P/infrastructure/cases_route.py:14` solo declara total al llegar a FIN. `PoliticaAcademicaConfirmada.clasificar` reconoce VENCIDO como PARCIAL. | T04/T05 prueban ceros y conservación; T06 exige recorrido definido. Los positivos de rutas completas de fixture no acreditan un marco real para todo vencimiento/ausencia. | Conjunto evaluable cuando falta la opción que define una rama, escenas no visitadas, ausencias sin ruta y combinación de aportes entre escenas. También cierre voluntario incompleto. | Sí a conservar y rechazar lo indeterminado, ya hecho; NO a contar todas las preguntas del caso o promediar escenas automáticamente. |
| 4. Precisión/redondeo | S3 p.9 lo deja negociable; S4 aprueba 0-100, no decimales ni modo. S6 contiene NUMERIC; la adaptación física vigente admite 100.00. | `P/domain/calculador_rubrica.py:21` PoliticaCalculo y `:58` calcular usan 1/N exacto; fracción no finita bloqueada. `P/infrastructure/result_repository.py:87` rechaza pérdidas al guardar; NUMERIC(5,2) en resultados. | T07/T08 prueban igualdad exacta, bloqueo del redondeo no aprobado, fracciones y rechazo de precisión incompatible. | Decimales y modo; si redondear preguntas, criterio, aporte ponderado o nota final; conciliación de detalle y total. | Sí al cálculo exacto ya existente; NO a adoptar ROUND_HALF_UP/HALF_EVEN ni truncamiento como política. |
| 5. Varios intentos autorizados | S1 p.5 RF-25 y p.7 RN-16; S5 exige autorización individual. No seleccionan mejor/último/promedio. | `P/application/evaluation_ports.py:59` PoliticaConsolidacionPort sin implementación. Preparación por sesión conserva todos los intentos; un resultado técnico por intento. | T09 no consolida implícitamente; T10 conserva ambos intentos. T11 acredita unicidad/concurrencia del resultado individual, no selección de nota oficial. | Regla de selección/agregación, intentos incluidos/excluidos y circunstancias de cierre/repetición aplicables al resultado final. | Sí a persistencia separada y autorización existente; NO a elegir un resultado definitivo por participación. |
| 6. Convocatorias retiradas | S1 p.5 RF-21 y p.7 RN-08/09 revocan acceso y notifican. S5 exige considerar toda la sesión, sin decidir la nota de retirados. | Scheduling conserva RETIRADA; preparación de Evaluation la incluye con TRATAMIENTO_RETIRO_PENDIENTE. No borra intentos ni notas históricas. | T12 conserva retiradas y no las clasifica; tests de RF-21 acreditan revocación, no una política de nota. | Corte del padrón, inclusión en consolidación y efecto de retiro anterior/posterior al intento o publicación. | Sí a revocación, historia e inventario ya existentes; NO a excluirlas, marcarlas AUSENTE o asignarles cero automáticamente. |
| 7. Confirmación de ausencias | S1 p.5 RF-24 y p.7 RN-15: cero por pregunta; S2 p.32 sin intento; S5 añade confirmación docente expresa. S4 no permite copiar una nota previa. | `P/application/evaluation_ports.py:69` AusenciasPort; `evaluation_service.py:134` exige cero intentos y confirmación. Strategy prepara ceros; el proveedor real en infrastructure/evaluation.py mantiene el bloqueo. No hay registro durable de confirmación. | T13 exige confirmación; T04 conserva ausencia sin intento ficticio; T12 y T14 prueban que no iniciar no crea ausencia/nota automática. Parte de T13 usa dobles unitarios. | Momento de confirmación, corrección/historial, concurrencia con inicio y soporte persistente por convocatoria sin P/I. Preguntas aplicables sin ruta. | Sí a controles de rechazo ya existentes; NO a inferir ausencia, inventar P/I o reutilizar un comentario como confirmación. |
| 8. Consolidar/publicar oficialmente | S1 RF-13/16/27, RN-17/18/19 y UC-05/07; S5 exige todos los estudiantes, actor autorizado y ninguna publicación automática al cierre. | `P/infrastructure/result_models.py:21` CHECK ambito=LABORATORIO; id_intento NOT NULL y solo COMPLETA/PARCIAL. No resultado_participacion ORM ni estado durable de publicación. Main no monta evaluación/publicación; RF-16/RF-27 registrados y cerrados. | T15/T16: no lectura técnica por contrato oficial; reporte y aviso sin escrituras. Cerrar un intento no publica. | Padrón/corte, consolidación, ausencias, habilitación exacta del publicador, momento permitido, rectificaciones y transición durable de publicación integral. | Sí a los cierres seguros actuales; NO a publicar LAB, elegir un subconjunto ni notificar una calificación no publicada. |

## 4. Compatibilidades y conflictos que no debe ocultar una fórmula

1. El ER contiene `nivel_criterio.logro_porcentaje`, mientras el ORM de Cases usa
   `nivel_rubrica.puntaje` y `valoracion_opcion.puntaje` (NUMERIC(5,2)). El nombre
   del ER indica porcentaje como representación objetivo, pero no certifica la
   correspondencia con los puntajes actuales. Ni la bandera correcta/incorrecta,
   ni el mayor puntaje observado, ni una convención 0-5 permiten fabricar esa tabla.
2. `resultado_criterio.id_nivel` es obligatorio y tiene FK nivel/criterio. Si una
   futura agregación produce un valor intermedio que no representa un nivel real,
   no se puede elegir el vecino ni crear un nivel cero ficticio. Hay que aprobar
   la interpretación académica y revisar su representación física.
3. Igualdad de criterios NO implica igualdad de preguntas ni de escenarios. Tampoco
   define qué ramas no recorridas cuentan. El promedio final de logros por criterio
   está confirmado; cómo obtener cada logro todavía no.
4. Tres criterios con logro 100 producen matemáticamente una nota 100, pero cada
   aporte 100/3 no cabe exactamente en el detalle de dos decimales. La protección
   actual bloquea ese caso; es un límite real, no autorización para repartir
   33.33/33.33/33.34. El total y su detalle necesitan una decisión de precisión.
5. El resultado técnico exige intento real. El ER original exige participación en
   resultado_participacion, y su nota_definitiva DECIMAL(4,2) no admite 100.00.
   Los PDF proponen otro modelo con resultado por convocatoria y participación
   nullable (S1 pp.14/27/28), pero no sustituye automáticamente el ER28 aprobado.
   Se necesita una propuesta física específica para ausencia sin P/I y consolidación
   oficial; no se autoriza crear una participación sin consentimiento para llenar FK.
6. S1 RF-14/UC-05 y sus secuencias describen resultado/notificación al terminar;
   S5 posterior separa cierre y publicación oficial. También RF-10/RN-10/11 y el
   informe antiguo 8C describen edición, sustituida por respuestas inmutables.
   Se conservan como antecedentes, no como permiso para reabrir respuestas o notas.
7. El catálogo actual tiene DOCENTE y ADMINISTRADOR; no un rol denominado DOCENTE
   ADMINISTRADOR. No conceder facultades docentes a todo administrador ni crear
   multirrol por interpretar una etiqueta. El equipo debe precisar ese encaje.

No se requiere inventar un umbral APROBADO/REPROBADO: estas fuentes exigen nota y
modalidad completa/parcial/ausencia, no una nueva clasificación por umbral.

## 5. Trazabilidad nominal de pruebas existentes

Rutas bajo backend/. Los IDs son referencias a métodos, incluidos sus parámetros
cuando corresponda. `tests/integration` no significa automáticamente política
productiva: los ejemplos positivos de calificación usan reglas LAB explícitas.

| ID | Método(s) pytest exacto(s) | Qué acredita y qué no |
|---|---|---|
| T01 | `tests/integration/test_evaluation_persisted.py::test_mapeo_no_sustituye_referencia_o_pertenencia`; `::test_historia_no_se_sustituye_por_publicacion_posterior` | Fuente y pertenencia históricas SQL; no aprobación del mapeo. |
| T02 | `tests/integration/test_academic_policy.py::test_sin_mapeo_agregacion_no_hay_nota_academica_completa` | Bloqueo con políticas indispensables ausentes. |
| T03 | `tests/integration/test_academic_policy.py::test_100_se_persiste_y_recupera_sin_nota_oficial`; `tests/integration/test_evaluation_persisted.py::test_motor_existente_calcula_UUID_reproducible_SOLO_con_politica_fixture` | Persistencia/cálculo con mapeo y resolución sintéticos. No regla oficial 0-5→100. |
| T04 | `tests/integration/test_academic_policy.py::test_vencido_recibe_ceros_sin_opciones_ficticias`; `::test_ausencia_misma_regla_sin_intento_y_sin_nivel_cero_inventado` | Entradas cero y bloqueo posterior si falta resolución. |
| T05 | `tests/integration/test_evaluation_persisted.py::test_vencido_es_parcial_por_RN14_sin_formula_ni_ausencia_inventada` | Clasificación parcial/conservación, no nota oficial. |
| T06 | `app/modules/participation/tests/test_evaluation_application.py::test_no_evaluar_sin_recorrido_definido` | Contrato de rechazo con dobles unitarios; no ruta académica real de ausencia. |
| T07 | `tests/integration/test_academic_policy.py::test_tres_criterios_no_se_aproximan_a_33_33`; `::test_no_se_inventa_redondeo_ni_escala_alternativa`; `::test_logro_finito_de_alta_precision_no_se_redondea` | Matemática exacta y bloqueo; estas funciones son unitarias aunque el archivo esté en integration. |
| T08 | `tests/integration/test_evaluation_result_storage.py::test_no_redondea_detalle_para_hacerlo_caber` | Rechazo SQL/repo de precisión incompatible; no decisión pedagógica de decimales. |
| T09 | `app/modules/participation/tests/test_evaluation_application.py::test_no_consolida_distintos_intentos_automaticamente` | Contrato unitario sin selección implícita. |
| T10 | `tests/integration/test_evaluation_readiness.py::test_ningun_intento_se_elije_ni_se_vence_al_consultar` | SQL real, ambos intentos conservados, sin escrituras. |
| T11 | `tests/integration/test_evaluation_result_storage.py::test_duplicado_no_sobrescribe`; `::test_concurrencia_mismo_intento_confirma_solo_uno`; `::test_rollback_tras_cabecera_no_deja_parciales` | Unicidad y transacción de resultado LAB individual, no publicación de sesión. |
| T12 | `tests/integration/test_evaluation_readiness.py::test_sesion_completa_incluye_sin_participacion_y_retirada_sin_inferir_ausencias` | Inventario SQL y bloqueo; no corte oficial del padrón. |
| T13 | `app/modules/participation/tests/test_evaluation_application.py::test_ausencia_necesita_confirmacion_academica_ademas_de_no_tener_intentos`; `app/modules/participation/tests/test_evaluation_domain.py::test_ausencia_rechaza_falta_de_confirmacion` | Preparación/confirmación con dobles o valores de dominio; no registro docente durable. |
| T14 | `tests/integration/test_main_report_closed.py::test_convocado_sin_participacion_no_se_convierte_en_ausencia_o_nota` | HTTP/SQL real, no ausencia inferida ni reporte oficial. |
| T15 | `tests/integration/test_evaluation_result_storage.py::test_resultado_laboratorio_nunca_se_obtiene_por_contrato_oficial`; `app/modules/participation/tests/test_evaluation_application.py::test_cierre_no_evalua_ni_altera_su_semantica` | Separación cálculo/publicación; segundo test de aplicación con dobles. |
| T16 | `tests/integration/test_main_report_closed.py::test_reporte_principal_cerrado_no_exporta_ni_escribe`; `tests/integration/test_grade_notice_closed.py::test_principal_no_anuncia_resultado_inexistente_ni_escribe` | HTTP/JWT/PG aislado, cierres 401/403/503 según actor. No publicación exitosa. |

Los resultados se contrastaron con el JUnit histórico
`evidencias/evaluation_preparacion_20261106T225458Z/pruebas_total_20261107T033737Z/junit.xml`.
No se ejecutó pytest en esta auditoría ni se modificó código después del checkpoint.
Últimas ejecuciones verificadas, no nuevas: relacionada 535 aprobadas/9 omitidas;
general 2239 aprobadas/38 omitidas, 0 fallidas/errores y 1 advertencia conocida.
No sumar selecciones solapadas ni atribuir aprobaciones a las omisiones.

## 6. Próximo incremento y decisiones concretas

Las fuentes NO contienen un mapeo/agregación completos. No se implementa un
algoritmo oficial ni nuevos ports: ya existen MapeoRubricaEvaluacion,
ResolucionNivelesAcademicos, PoliticaEvaluacionContextualPort,
PoliticaConsolidacionPort y AusenciasPort. Añadir otros contratos ahora duplicaría
o anticiparía decisiones aún ausentes.

Solicitar a la profesora un caso de aceptación con rúbrica real versionada y estas
respuestas, conservando su aprobación junto a la definición de política:

1. Para cada nivel real, ¿cuál es su logro 0-100? ¿Qué significa el puntaje de
   cada opción/criterio y cómo determina ese nivel? Definir valores sin coincidencia
   exacta y empates, sin usar automáticamente correcto=100/incorrecto=0.
2. Si dos preguntas de una escena valoran el mismo criterio, ¿cómo se combinan?
   Si el valor combinado no coincide con un nivel existente, ¿qué nivel o tipo
   de resultado corresponde? No basta aprobar solo la media final de criterios.
3. ¿Cómo se integran escenas y preguntas de ramas no visitadas? ¿Cuál es el conjunto
   de preguntas evaluables en vencimiento o ausencia cuando no se conoce la ruta
   completa? ¿Cómo clasificar el cierre voluntario incompleto?
4. ¿Qué precisión y modo se aplican, y en qué etapa: pregunta, criterio, aporte o
   total? Resolver expresamente tres criterios de logro 100 y la consistencia
   entre el detalle guardado y la nota final, sin cambiar la igualdad de pesos.
5. Con varios intentos autorizados, ¿cuáles determinan el resultado de participación
   y con qué regla? La autorización individual ya está definida; la selección no.
6. ¿En qué corte se fija el padrón y cómo se tratan retiros antes/después de responder
   o publicar? No eliminar resultados históricos para excluir una convocatoria.
7. ¿Cuándo puede el docente confirmar una ausencia y cómo rectificarla? Definir
   la relación con un inicio concurrente y conservar actor, fecha y causa histórica.
   La necesidad de confirmación ya está decidida; falta su operación y persistencia.
8. ¿Qué condiciones de cierre habilitan la publicación de toda la sesión y cómo
   corregir una nota ya publicada? Precisar el significado funcional de docente
   administrador con el equipo responsable de Identity, sin conceder permisos nuevos.

Preparación técnica posterior, condicionada a esas respuestas:

- Reutilizar el snapshot histórico de Cases y entregar al motor un mapeo explícito,
  resolución de preguntas y política de precisión aprobados, con ID/version/huella
  y parámetros efectivos. No un nombre de política sin definición reproducible.
- Guardar cálculo individual, consolidación y publicación como hechos distintos.
  La consolidación debe conservar los intentos fuente y la política aplicada;
  una cifra Decimal aislada no basta como evidencia histórica de selección.
- Presentar antes de implementar la adaptación física mínima para ausencia sin
  intento/participación y para resultado oficial. No transformar filas LAB en
  oficiales ni generar datos para cumplir NOT NULL. Sin migración en esta etapa.
- Publicar el conjunto autorizado completo en una transacción que revalide roles,
  ámbito, padrón y resultados vigentes, con exclusión/identidad estable para reintentos.
  La consulta de preparación no es un permiso durable ni garantiza publicación.
- Conectar RF-16 y RF-27 únicamente a resultados oficialmente publicados. Reutilizar
  el mecanismo de avisos; no emitir notas al cierre ni abrir rutas por este informe.

Aceptación posterior: resultados esperados firmados/confirmados para caso completo,
vencido con pendientes, ausencia confirmada, dos intentos y retirada; versiones
históricas, precisión, autorización, atomicidad, concurrencia y rollback en PG17
desechable. El conjunto docente debe permitir calcular a mano la nota y su detalle.

## 7. Estado funcional y preservación

RF-13 BLOQUEADO para algoritmo oficial completo; RF-24 BLOQUEADO para completar
calificación de parciales/ausencias; RF-16 BLOQUEADO para descarga oficial; RF-27
PARCIAL (feedback interno existente, notas oficiales cerradas). Se mantienen
14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO. No se reclasifica por elaborar esta auditoría.

No hay código adicional después del checkpoint ni pruebas nuevas que ejecutar.
Este documento y sus extracciones/manifiestos de evidencia quedan sin commit.
No se modifican PDF, DBML, contratos, endpoints, bases de datos ni políticas.
La extracción, las tres páginas renderizadas y la trazabilidad nominal se conservan
en `evidencias/auditoria_politicas_evaluation_20261107T040803Z/`.
