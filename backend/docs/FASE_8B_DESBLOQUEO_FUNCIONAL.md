# 8B — Desbloqueo funcional: incremento seguro y límites pendientes

2026-11-02 · `feature/integracion-backend`. **8B permanece incompleta.**
Este informe corresponde a esta solicitud; no sustituye las evidencias históricas
de `FASE_8B_PERSISTENCIA_FUNCIONAL.md` ni las políticas y persistencia de 8C.

## A. Funcionalidades operativas y cambio realizado

Se reutiliza `crear_facade_8b`, los servicios de decisiones/progreso/cierre,
`UnidadTrabajoSQLAlchemy` y el repositorio de Participation. No se reconstruye
la persistencia ni se configura una ruta HTTP productiva.

1. **Protección del efecto de una selección.** Antes de guardar, el adaptador
   comprueba también el recorrido calculado con la selección propuesta. Sustituye
   la opción de la pregunta existente o añade la nueva selección una sola vez.
   El recorrido posterior debe estar disponible, pertenecer a la versión exacta
   e incluir todas las respuestas conservadas, incluida la propuesta.
2. **Conservación de historia.** Si el cambio de rama excluye una respuesta,
   se rechaza íntegramente la operación. No se borran pasos, no se elige qué
   respuesta invalidar y no se modifica la selección anterior. Es una guarda
   conservadora mientras falta la política de cambio de ruta, no esa política.
3. **Sesión finalizada.** El adaptador impide responder/modificar cuando la
   consulta transaccional de Scheduling devuelve `FINALIZADO` (RF-25), incluso
   si un proveedor de autorización fuera permisivo. La consulta factual de
   Scheduling sigue devolviendo estados conocidos: no se cambia su contrato.

Antes de este incremento se validaban la ruta previa y el permiso del punto,
pero el adaptador no contrastaba por sí mismo el efecto de la nueva selección.
Un proveedor permisivo podía autorizar un cambio que excluyera pasos guardados.
La nueva prueba reproduce ese caso con un contrato simulado y SQL real.

Las garantías anteriores siguen operativas: selección única, pertenencia de
opción/pregunta/versión, titularidad, convocatoria y matrícula verificadas,
tiempo individual histórico con reloj inyectado, cierre/vencimiento idempotentes,
recuperación de respuestas y rechazo de modificaciones tras el cierre.
La lectura de progreso sin recorrido sigue mostrando respuestas reales, pero
no inventa preguntas aplicables, pendientes ni denominador.

## B. Archivos y contratos conectados

| Archivo | Cambio / responsabilidad |
|---|---|
| `app/modules/participation/infrastructure/composition.py` | Dos guardas anteriores en `CasesIntentoSQLAlchemy.validar_cambio_conservando_pasos` y `SchedulingIntentoSQLAlchemy.validar_edicion`. |
| `app/modules/participation/application/integration_ports.py` | Precisa que `RecorridoVersionCases.obtener` es consulta sin efectos, utilizable antes/después de una propuesta. No cambia firmas ni añade un segundo puerto. |
| `tests/integration/test_route_change_guards.py` | Once pruebas nuevas de ramas simuladas, conservación, rollback, reemplazo único, sesión finalizada y cierre/vencimiento. |
| `tests/integration/test_cases_scheduling_operations.py` | Refuerza la expectativa existente: `FINALIZADO` ahora se rechaza con `AccesoDenegado`, no por ausencia de política. La consulta factual se sigue verificando para los tres estados. |
| Este documento | Resultado y límite de esta entrega. |

La autorización, consulta de Cases y escritura permanecen dentro de la misma
UoW. Se conservan los bloqueos de participación/intento y sesión/convocatoria.
La nueva validación sucede antes de guardar; las excepciones provocan rollback
y cierre de la Session. No se usa una autorización obtenida en otra transacción.
No se cambia Facade, Strategy, calculador, ORM, migraciones, API ni Identity.

## C. Pruebas ejecutadas

Pruebas focalizadas: `test_route_change_guards.py`,
`test_cases_scheduling_operations.py`, `test_steps_uuid.py` y
`test_evaluation_persisted.py`: **113 aprobadas, 0 omitidas, 0 fallos,
0 errores, 1 advertencia conocida de Starlette; 65,88 s**.

Regresión general: **1557 aprobadas, 38 omitidas, 0 fallos, 0 errores,
1 advertencia conocida de Starlette; 316,95 s**. Son once aprobadas adicionales
respecto de la línea base reportada de 1546. No se detectaron regresiones de 8C.
Las 38 omitidas corresponden a 29 pruebas con URL Identity externa, tres de
conexión Participation externa y seis de otro laboratorio por URL no habilitada.

Distinción de evidencia:

- Las once pruebas nuevas usan PostgreSQL nuevo y desechable, Facade/repositorio
  reales y relaciones sintéticas persistidas. El fixture aplica hasta
  `20261102_steps_uuid`; la regresión completa también ejecuta las pruebas de las
  revisiones posteriores de 8C.
- Las rutas y autorizaciones positivas son **fakes exclusivamente de pruebas**.
  Las pruebas de rama no demuestran un grafo guardado en Cases. No hay pruebas
  positivas de escena inicial/transición productivas porque faltan esos datos.
- La consulta estructural, validación de pertenencia, persistencia, rollback y
  concurrencia de los grupos existentes son reales. SQLite aislado cubre lecturas
  y reglas, no bloqueos PostgreSQL. TestClient existente usa una aplicación de
  pruebas; no demuestra un recorrido HTTP productivo habilitado.
- Los escenarios previos repetidos incluyen opciones de otra pregunta/versión,
  referencias de sesión ajenas, conservación al vencer y carreras entre cierre,
  modificación y vencimiento. No se atribuyen como pruebas nuevas de esta entrega.

Se retiran del subproceso `TEST_DATABASE_URL`, `SPS_IDENTITY_TEST_URL` y
`SPS_PERSISTENCE_LAB_URL`; `SPS_TEST_POSTGRESQL=0` impide conexiones externas y
`SPS_TEST_IDENTITY_MAPPING_DOCKER=1` habilita únicamente el laboratorio propietario.
Se ejecuta `python -B -m pytest -c backend/pyproject.toml backend/tests
backend/app/modules/participation/tests -q -rs --tb=short` con esas condiciones.
Las omitidas externas siguen pendientes, nunca se cuentan como aprobadas.

## D. Operaciones que continúan bloqueadas

| Operación | Evidencia / bloqueo exacto |
|---|---|
| Escena inicial | `cases/infrastructure/models/caso.py`: escenarios tienen orden editorial, no marcador de entrada del recorrido. No convertir el menor orden en entrada. |
| Transición / siguiente escena / terminalidad | `OpcionRespuestaModel` tiene pregunta, orden, texto, corrección y justificación, pero no destino ni transición. Tampoco hay un contrato implementado de grafo en Cases. Ausencia de transición no puede interpretarse como final. |
| Ruta real persistida | Se recuperan pasos y selecciones, no un registro completo de visitas a escenas ni un grafo histórico. `numero_paso` no sustituye las aristas ni acredita elegibilidad. |
| Preguntas evaluables reales | `consultar_estructura_version` da pertenencia a edición, no aplicabilidad. `RecorridoVersionCases` sigue sin proveedor productivo. No se usa el total de preguntas como ruta. |
| Responder/modificar en producción | Sin `AutorizacionEdicionIntento` y recorrido explícitos se rechaza. La nueva prohibición para FINALIZADO no concede autorización para EN_CURSO. |
| Inicio / repetición | `IdentityIntentoSQLAlchemy.autorizar_inicio`, `SchedulingIntentoSQLAlchemy.obtener_condiciones` y `autorizar_nuevo_intento` siguen cerrados. Falta la composición autorizada de consentimiento, cupos y condiciones de inicio; no se usa un fixture como política. |
| Ingreso RF-22 / API | Política temporal no configurada y dependencia HTTP cerrada. No se registra un router ni se habilita inicio productivo. |

No se añade una tabla, columna, transición de laboratorio ni política implícita
para ocultar estos límites. Los avances de 8C permanecen independientes.

## E. Decisiones estrictamente necesarias

| Responsable / RF | Decisión concreta requerida |
|---|---|
| Cases · RF-05/06/10/11 | Definir entrada por edición, transiciones por opción, terminalidad explícita y si existen ciclos/revisitas. Identificar una fuente persistente versionada verificable para esos datos. Hoy no existen en el ORM; cualquier adaptación física necesita revisión y autorización específica, sin añadir entidades por iniciativa propia. |
| Cases · RF-10/11/12 | Definir el tratamiento de respuestas que dejan de ser aplicables tras un cambio de ruta. Hasta entonces se conserva todo y se rechaza el cambio que las excluiría. No se necesita decidir borrado para aplicar la guarda actual. |
| Scheduling · RF-10/19/23/25 | Confirmar la matriz de RESPONDER/MODIFICAR y qué sucede con un intento aún vigente cuando llega `fecha_fin` de la sesión. Separar estado, plazo individual histórico y horario de sesión. La prohibición de participar en FINALIZADO ya se aplica; no se inventa una prórroga del Worker. |
| Scheduling / Identity · RF-22/23/25 | Resolver únicamente las condiciones aún pendientes de ingreso, consentimiento e intentos adicionales antes de componer inicio real. Mantener RF-22 bloqueado mientras falte su política. |

El siguiente trabajo ejecutable requiere que Cases entregue esos datos y que
Scheduling concrete su proveedor de autorización. Los puertos ya existen:
no hace falta otro motor de recorridos en Participation ni otra autenticación.

## F. Evaluation

La conexión existente `CasesEvaluacionSQLAlchemy.obtener_marco_evaluacion`
comparte `CasesIntentoSQLAlchemy.obtener_recorrido`, conserva la versión/rúbrica
exactas y contrasta las selecciones con el intento almacenado. `ServicioEvaluacion`
exige recorrido disponible y total conocido; las estrategias rechazan selecciones
ajenas. La clasificación de completo/parcial no se sustituye por el cierre técnico.

No se duplica esa conexión. Sin proveedor real no hay decisiones evaluables ni
pendientes de ruta que puedan afirmarse; no se crea una nota usando todas las
preguntas. Las convenciones positivas de laboratorio permanecen explícitas.
Se conservan escala 0–100, pesos igualitarios, ceros por pendientes al vencer,
procedencia histórica y resultados de 8C. Mapeo de niveles, agregación de
preguntas y redondeo necesario continúan pendientes. No se publican notas.

## G. Git, Alembic y laboratorios

La comprobación estática conserva **30 tablas ORM físicas, 13 revisiones y una
cabeza `20261102_academic_policy`**. No se añade ni modifica ninguna revisión.
Las 28 entidades académicas originales y sus DBML no se modifican.

El fixture crea un contenedor propio identificado por ID y etiqueta
`sps.identity.mapping.lab=true`, puerto TCP efímero y almacenamiento tmpfs sin
volúmenes persistentes. Verifica la base aislada esperada mediante conexión real
y elimina exclusivamente su contenedor en `finally`. No se consulta `.env` para
elegir una conexión ni se utiliza una base o contenedor compartido.

Comprobaciones finales:

- `git diff --check`: código 0. Persiste el aviso previo LF/CRLF de
  `cases/infrastructure/repositories/caso_repository.py`; ese archivo no cambió
  en esta entrega.
- Comparación SHA-256 con el inventario de entrada: únicamente cambiaron los
  tres archivos existentes de la tabla B; se crearon este informe y el archivo
  de once pruebas. No se eliminó ningún archivo. Todos los archivos restantes,
  incluidos código de Evaluation, su informe, ORM, DBML y revisiones, conservan
  sus bytes de entrada. Se preservan los cambios anteriores sin commit.
- La suite BD2-04 generó automáticamente una evidencia adicional:
  `bd/laboratorio_bd2_04/evidencia_6f23c163677c4cf9a1e9658863a30b78.json`.
  No se sobrescriben evidencias anteriores.
- `docker ps -a --filter label=sps.identity.mapping.lab=true` terminó sin filas:
  no quedan laboratorios de estas pruebas. No se utilizó una base persistente
  ni un contenedor ajeno.
- Rama final `feature/integracion-backend`; cabeza Alembic sin cambios.
  No se realizó commit, push, merge, cambio de rama ni se inició fase 9.
