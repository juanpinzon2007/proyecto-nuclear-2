# Consistencia de eventos académicos: diagnóstico, checkpoint y propuesta

> **Actualización posterior, 5 de noviembre de 2026:** se eligió e implementó la
> alternativa A (avisos internos en la transacción de State). Las secciones 1–6
> conservan el diagnóstico y la propuesta histórica B, que **no se implementó**.
> La decisión vigente, sus pruebas y límites están en la sección 7.

5 de noviembre de 2026, America/Bogota. Repositorio original
`proyecto-nuclear-2`, rama `feature/backend-continuidad`, HEAD
`ac92b7251c96f81ddcb6f390ef21435ab74b6131` más modificaciones locales.

**Resultado de esta etapa:** trabajo acumulado verificado; pérdida de aviso y
duplicación por replay reproducidas en PostgreSQL17. No se implementó todavía
una cola ni se alteraron producción, ORM o migraciones. Se presenta primero el
contrato técnico mínimo, conforme a la condición de la etapa 3 del encargo:
«Si la solución exige cambios arquitectónicos extensos o contratos todavía no
definidos, presenta primero una propuesta técnica y sus riesgos sin forzar la
implementación».

No se trata de falta de Docker ni de una prohibición genérica de migrar: hace
falta ampliar los contratos de identidad causal y confirmación del consumidor,
que hoy no existen. Una captura de excepción o un retry de State no los reemplaza.

## 1. Protección y checkpoint propuesto, sin ejecutarlo

Se verificaron contra el cierre RF-19 los **28 archivos del candidato**:
15 modificados rastreados y 13 nuevos. Sus contenidos coinciden por SHA-256 con
`evidencias/rf19_cierre_unico_20261105T125836Z/CIERRE.json` y el inventario de fuentes
de la última general; el informe actualizado se contrasta con su hash de cierre.
No se encontraron cambios accidentales en esas fuentes.

Se inventariaron también todos los archivos nuevos/modificados existentes:
15 rastreados modificados y 634 no rastreados fuera de la raíz `evidencias/`, en
el corte inicial. De los nuevos, 13 pertenecen al checkpoint y **621 quedan fuera**:
incluyen documentación/evidencias/artefactos y otros archivos locales que requieren
revisión separada. No se clasifican todos como basura ni se elimina ninguno.
El estado Git completo incluye además la raíz de evidencias, excluida del commit.

Inventarios en `evidencias/eventos_academicos_20261105T141210Z/`:

- `preservacion_inicial.json`: HEAD, rama, refs/stash, estado Git con `-uall`, rutas,
  tamaños y SHA-256 de las fuentes existentes; `.env` solo se verifica por hash.
- `inventario_cambios.json`: cambios fuera de la raíz de evidencias, con clasificación.
- `checkpoint_propuesto.json`: selección exacta de 28 archivos, tamaño y SHA-256.
- `fuera_checkpoint.json`: listado nominal de los 621 nuevos excluidos.
- `revision_estatica_checkpoint.json`: no detectó bloques de clave privada,
  JWT literales ni URL PostgreSQL con credenciales en los 28 seleccionados.
  Es una revisión limitada, no una certificación exhaustiva de secretos.

### Commits recomendados

Son propuestas: **no se preparó el índice ni se ejecutó ningún commit**.
Las rutas siguientes son relativas a `backend/`.

**C1 — `feat(participation): operaciones privadas sobre intentos existentes`**

| Tipo actual | Archivo |
|---|---|
| M | app/main.py |
| M | app/modules/participation/api/HTTP.md |
| M | app/modules/participation/api/dependencies.py |
| M | app/modules/participation/application/services.py |
| M | app/modules/participation/infrastructure/composition.py |
| M | app/modules/participation/tests/test_api.py |
| M | docs/FASE_9_APLICACION_PRINCIPAL.md |
| M | tests/integration/test_main_current_scenario.py |
| Nuevo | app/modules/participation/application/progress.py |
| Nuevo | app/modules/participation/infrastructure/progress_query.py |
| Nuevo | app/modules/participation/api/progress_router.py |
| Nuevo | app/modules/participation/api/attempt_operations_router.py |
| Nuevo | tests/integration/test_main_progress.py |
| Nuevo | tests/integration/test_main_decisions.py |
| Nuevo | tests/integration/test_main_finish.py |
| Nuevo | docs/FASE_9A_PARTICIPATION.md |

**C2 — `fix(participation): verificar al creador del caso en permisos de intento`**

| Tipo actual | Archivo |
|---|---|
| M | app/modules/participation/infrastructure/start.py |
| Nuevo | tests/integration/test_attempt_permission_creator.py |
| Nuevo | docs/FASE_9B_INICIO_DESDE_CONVOCATORIA.md |

**C3 — `fix(scheduling): cierre único y bloqueo de avisos oficiales no verificados`**

| Tipo actual | Archivo |
|---|---|
| M | app/modules/scheduling/api/router.py |
| M | app/modules/scheduling/application/cambiar_estado_sesion.py |
| M | app/modules/scheduling/application/worker_cierre.py |
| M | tests/unit/scheduling/test_api_endpoints.py |
| M | tests/unit/scheduling/test_cambiar_estado_sesion.py |
| M | tests/integration/scheduling/test_scheduling_endpoints.py |
| Nuevo | tests/integration/test_grade_notice_closed.py |
| Nuevo | tests/integration/test_session_state_consistency.py |
| Nuevo | docs/AUDITORIA_COBERTURA_BACKEND_20261105.md |

RF-27 y RF-19 comparten `router.py` y el informe acumulado. Agruparlos evita
preparar un archivo completo en el primer bloque y adjudicar inadvertidamente
los cambios del segundo. Si se prefieren dos commits separados, requieren revisión
por hunks y una versión coherente del informe para cada corte, no `git add .`.
C1 precede C2/C3; C3 contiene pruebas que consumen las composiciones consolidadas.

**C4 opcional — `docs(scheduling): proponer entrega recuperable de eventos`**:
únicamente este archivo, después de su revisión. No se mezcla una propuesta sin
aprobar con una migración supuestamente terminada.

Excluir de todos: `.env`, `evidencias/`, logs/JUnit, JSON generados por laboratorios,
Word/ZIP, respaldos, cachés y los archivos ajenos a la selección. Los futuros cambios
de confiabilidad pertenecerían a otro bloque, una vez acordado el contrato.

## 2. Diagnóstico comprobado

### Componentes existentes

| Componente | Contrato actual | Límite demostrado |
|---|---|---|
| `cambiar_estado_sesion` | Lock con refresco, State y auditoría en la misma transacción; devuelve sesión | Auditoría tiene UUID e historia durable, pero no pendiente/recibo de procesamiento |
| `cambiar_estado_y_publicar` | Commit estado/auditoría; después `await gestor.publicar` | Fallo posterior no puede revertir el commit; no registra recuperación |
| `cerrar_sesiones_vencidas` | Selecciona candidatos y reutiliza el coordinador | Una sesión ya FINALIZADO no vuelve a ser candidata, aunque falte su aviso |
| `EventoAcademico` | Dataclass con `tipo` y `entidad_id` de sesión | ID de sesión no es ID de la transición; no transporta UUID de auditoría |
| `GestorEventosAcademicos` | Lista dinámica de observadores y `asyncio.gather`; retorna None | Retorna también sin suscriptores. Retorno sin excepción no prueba persistencia de efectos |
| `ObservadorNotificaciones` | Nueva Session, consulta convocatorias ACTIVA, crea todos los avisos y commit propio | No relaciona avisos con auditoría/evento; replay vuelve a insertar |
| `NotificacionModel` | Mensaje, destinatario, convocatoria, canal, estado y fecha | PENDIENTE de una notificación no es recibo de un evento; si el INSERT falló, ni siquiera existe esa fila |
| `worker_runner` | Revisión periódica del cierre | No busca ni recupera eventos; no contiene dispatcher durable |

Se buscaron outbox/recibos/reintentos en código y migraciones. La tabla
`evento_salida` aparece solo en el DBML histórico de 40 tablas **no aprobado**.
No se utiliza como arquitectura vigente. Los documentos BD-1.2/R09 señalan que
`notificacion` puede reutilizarse, pero no implementan deduplicación ni recuperación.

**Sí existe un hecho durable reutilizable:** `evento_auditoria` ya conserva UUID,
sesión, transición, origen y fecha. No hace falta duplicar ese hecho en una nueva
tabla por defecto. Lo que falta es representar el trabajo pendiente por consumidor
y vincular inequívocamente sus efectos confirmados.

### Secuencia de fallo

1. Se confirma FINALIZADO y una auditoría: RF-19 funciona.
2. Observer intenta guardar avisos y su SQL falla: rollback de su propia transacción.
3. La solicitud recibe error después del commit; la sesión permanece FINALIZADO.
4. Repetir el cierre recibe 409, sin nueva auditoría/evento: comportamiento correcto
   de State, pero no recuperación del aviso.
5. Republicar manualmente el mensaje tampoco es seguro: no identifica la transición
   causal y puede crear otro aviso aun si el primer efecto ya estaba confirmado.

## 3. Decisión arquitectónica recomendada, todavía no implementada

Recomiendo **reutilizar `evento_auditoria` como origen durable del evento y añadir
recibo transaccional del único consumidor SQL actual de avisos de sesión**.
No recomiendo introducir ahora una tabla outbox genérica o importar el diseño de 40.
No se reutilizan `descripcion`, `tipo` o el estado de la notificación como un JSON
opaco o marca de entrega que cambie su significado histórico.

### Ampliación física propuesta: cinco columnas, cero tablas nuevas

| Tabla / columna | Tipo y semántica propuesta |
|---|---|
| evento_auditoria.notificaciones_estado | VARCHAR(12) NULL: NULL para legado no encolado, PENDIENTE o PROCESADO para nuevas transiciones |
| evento_auditoria.notificaciones_intentos | INTEGER NOT NULL DEFAULT 0, CHECK >=0; intentos registrados cuando la infraestructura permite persistirlos |
| evento_auditoria.notificaciones_procesadas_en | TIMESTAMPTZ NULL; solo cuando los efectos del consumidor SQL están confirmados |
| evento_auditoria.notificaciones_ultimo_error | VARCHAR(64) NULL, código técnico controlado; nunca str(exception), stack, token, correo o credenciales |
| notificacion.evento_auditoria_id | UUID NULL, FK a evento_auditoria.id con ON DELETE RESTRICT; procedencia de avisos nuevos de sesión |

Restricciones propuestas:

- UNIQUE(`notificacion.evento_auditoria_id`, `notificacion.convocatoria_id`), solo
  relevante para procedencias no NULL. Los avisos heredados permanecen intactos.
- CHECK: si existe procedencia, convocatoria debe ser no NULL, canal INTERNA y
  tipo SESION_INICIADA/SESION_FINALIZADA. Evita que NULL eluda la deduplicación nueva.
- CHECK de consistencia: PENDIENTE sin fecha de procesamiento; PROCESADO con fecha
  y al menos un intento registrado. NULL de legado no representa entrega verificada.
- CHECK del origen encolado: CAMBIO_ESTADO y transición reconocida por el contrato
  actual. No usar CHECK para comparar filas entre tablas.
- Índice parcial sobre pendientes para el barrido. Correspondencia sesión del
  evento–convocatoria–destinatario se revalida en el consumidor con las relaciones
  reales; la FK simple no se presenta como una garantía intertabla completa.

Estas son adaptaciones físicas PROPUESTAS. Se conservarían las 31 tablas ORM
actuales y el DBML académico original. No se ha creado ORM ni revisión Alembic.

### Contrato técnico que debe fijarse antes de implementar

1. **Identidad causal:** ampliar `EventoAcademico` con `evento_id` igual al UUID
   persistido de auditoría, sin generarlo otra vez al reintentar. El consumidor
   durable rechaza mensajes sin identidad verificable o con tipo/sesión discordantes.
2. **Alcance del recibo:** los campos propuestos acreditan SOLO
   `scheduling.notificaciones_sesion.v1`, el consumidor SQL actualmente registrado.
   No acreditan todos los callbacks del Gestor, lectura del usuario ni envío SMTP.
3. **Compatibilidad:** los observadores efímeros pueden conservar su uso actual,
   pero no se declara durable su procesamiento. Si se necesita recuperar N
   consumidores independientes, hace falta otro contrato de recibo por consumidor;
   no se simula con un único booleano ni se añade otra tabla sin revisión.
4. **Destinatarios:** conservar la consulta actual de convocatorias ACTIVA al
   procesar, con pertenencia real. Congelar el roster al producir sería otro
   comportamiento y no se introduce automáticamente.
5. **HTTP y errores:** conservar autorización y 409 de transición inválida. La
   recuperación debe operar por `evento_id`, nunca por repetir State. Mantener
   explícita la diferencia entre transición confirmada y aviso pendiente cuando
   el callback inmediato falle; no convertir silenciosamente 500 en 200/202.

La definición vigente de `publicar(...) -> None` no es un contrato de acuse. Por
eso este cambio no puede presentarse como añadir un simple try/except o una sola
columna. Afecta productor, mensaje, consumidor, recibo SQL, worker y compatibilidad
de sus pruebas; se presenta primero esta ampliación, tal como permite la etapa 3.

### Flujo propuesto de ejecución y recuperación

1. Bajo el lock RF-19, confirmar estado + auditoría con PENDIENTE en el MISMO commit.
2. Después del commit, intentar publicar el mensaje con el ID de esa auditoría.
3. El consumidor abre su transacción, bloquea/refresca la auditoría y valida el
   mensaje. Si ya está PROCESADO, no repite efectos.
4. Guardar los avisos vinculados al evento y el recibo PROCESADO en el MISMO commit.
   Si falla, rollback de ambos; el pendiente productor permanece recuperable.
5. Dispatcher acotado selecciona IDs pendientes desde la BD. Libera la transacción
   de selección antes de esperar callbacks: no retiene un lock que bloquearía al
   propio Observer con Session independiente.
6. Dispatchers concurrentes pueden entregar el mismo mensaje: el lock de consumidor,
   la comprobación de recibo y la restricción UNIQUE impiden repetir sus efectos.
7. El dispatcher consulta el recibo persistido; no marca procesado por el mero
   retorno de `Gestor.publicar` o por no existir suscriptores.
8. Fallos registran código técnico y contador si la BD está accesible. Si la BD
   está caída, no puede prometerse registrar ese intento; el pendiente previo sigue
   durable. No descartar eventos por alcanzar un contador sin política operacional.
9. La revisión periódica recupera pendientes independientemente de qué sesiones
   sigan EN_CURSO. Límite de lote y timeout son configuración técnica explícita
   del servidor, no reglas académicas ni bucles de retry ilimitados.

No reclamar «exactamente una vez»: se propone entrega al menos una vez y efectos
idempotentes para un consumidor concreto. Una caída después del commit de efectos
antes de responder provoca otra entrega, que se resuelve leyendo el recibo ya
confirmado. Tampoco se acredita correo, lectura ni consumidores no registrados.

## 4. Migración futura y orden ejecutable

Cabeza comprobada: `20261104_teacher_spaces`. Una eventual revisión aditiva tendría
ese padre, sin nuevas ramas Alembic. No se eligió un identificador definitivo ni
se creó archivo bajo `alembic/versions`.

1. Acordar contrato causal/recibo y aprobar las cinco columnas/restricciones.
2. Añadir campos con NULL legado y contador 0. No encolar ni notificar auditorías
   históricas automáticamente: no hay evidencia para reconocer qué se entregó.
3. Incorporar FK/UQ/CHECK/índice; preflight de esquema y operaciones revisadas,
   sin autogeneración ciega ni cambio de PK/UUID existentes.
4. Integrar productores y consumidor antes de habilitar dispatcher. El productor
   debe obtener la auditoría recién creada sin consultas ambiguas sobre registros
   históricos duplicados ni marcadores transitorios ocultos en Session.info.
5. Añadir recuperación interna al runner existente, sin un endpoint público de
   publicación y sin repetir la transición académica.
6. Probar upgrade/downgrade/reupgrade solo en PG17 desechable. Downgrade debe
   rechazar eliminar pendientes o recibos/procedencias nuevos, salvo conciliación
   autorizada; no borrar trazabilidad ni reabrir sesiones.

Archivos de la implementación posterior:

- `scheduling/domain/events.py`: identidad causal y contrato de consumidor.
- `scheduling/application/cambiar_estado_sesion.py` y `cambiar_estado_y_publicar.py`:
  registro atómico y referencia inequívoca a la auditoría creada, manteniendo State.
- `scheduling/infrastructure/models.py`: cinco columnas y restricciones propuestas.
- `scheduling/application/crear_notificacion.py`: procedencia opcional y validación.
- `scheduling/infrastructure/observador_notificaciones.py`: efectos/recibo atómicos.
- Nuevo servicio acotado de recuperación y `infrastructure/worker_runner.py`.
- `application/registrar_observadores.py`: identificación explícita del consumidor SQL.
- Una revisión Alembic y pruebas unitarias/integración/metadata. Revisar fixtures
  que prueban revisiones antiguas sin debilitar sus aserciones ni simular PG con SQLite.

No requiere cambiar Participation, Evaluation, políticas de ingreso, consentimiento,
repetición, calificaciones o el DSL de Cases.

## 5. Pruebas actuales y aceptación futura

Evidencia: `evidencias/eventos_academicos_20261105T141210Z/`, con comandos, versión
local, hashes, consola y JUnit. No se suman suites solapadas.

| Ejecución actual | Resultado | Interpretación |
|---|---|---|
| `pruebas_focal_20261105T141212Z` | 2 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 10.72 s | Pruebas existentes RF-19: error postcommit no repite State y cierre repetido no duplica avisos por esa vía. No acreditan recuperación. |
| `pruebas_diagnostico_20261105T141545Z` | 0 aprobadas, 2 fallidas, 0 omitidas/errores, 1 advertencia; 9.82 s | Carencias reproducidas con SQL/Observer reales: falta pendiente reconocible y replay produce 2 avisos donde se requiere 1. No se ocultan ni usan skip/xfail. |

El primer diagnóstico verifica primero FINALIZADO, una auditoría, cero avisos y
409 al repetir. Su última aserción usa el nombre de campo de la PROPUESTA y falla
porque aún no está implementado; no demuestra que ese nombre/columna sea la única
solución posible. El segundo demuestra funcionalmente duplicación: una auditoría,
dos avisos después de republicar el mensaje real tipo/sesión. El archivo experimental
queda solo en evidencias, excluido del checkpoint y sin alterar tests previos.

Las 2017 aprobadas/38 omitidas de RF-19 son históricas; no se repitió la general
porque no se modificó lógica, modelos ni migraciones. No se declara una recuperación
implementada ni una aceptación verde. La advertencia actual es Starlette/TestClient.

Pruebas obligatorias de la implementación futura:

| Escenario | Resultado necesario, todavía NO demostrado |
|---|---|
| Transición válida | Estado, auditoría y pendiente confirmados en la misma transacción |
| Fallo antes del commit | Ninguno de los tres queda persistido ni se publican efectos |
| Fallo SQL de Observer | Pendiente conservado, cero recibos falsos y cero efectos parciales |
| Recuperación desde otra Session | Avisos y recibo confirmados sin nueva transición/auditoría |
| Dos reintentos concurrentes | Un efecto por evento/convocatoria; entregas repetidas toleradas |
| Duplicado SQL de procedencia | Rechazo por UNIQUE; rollback no altera efectos previos |
| Caída después de confirmar efectos | Replay consulta recibo y no duplica notificaciones |
| Cero observadores o uno que solo retorna | No marcar procesado sin recibo SQL verificable |
| Evento ajeno/no verificable | Rechazo sin producir avisos para otra sesión o estudiante |
| Docente frente a worker | Una transición RF-19, una fuente durable y efectos idempotentes |
| Legado sin procedencia | No backfill ni reenvíos automáticos inventados |
| Retiro durante la espera y secuencia inicio/fin | Preservar alcance vigente y acordar orden por sesión sin suprimir eventos silenciosamente |
| Migración y reversión | Preflight, constraints, datos previos conservados y downgrade sin pérdida |

## 6. Decisión pendiente y cierre

**Recomendación concreta para aprobar:** alcance durable limitado al consumidor
SQL de avisos de inicio/fin de sesión, reutilizando auditoría como identidad/fuente
y notificación como efecto, con las cinco columnas y restricciones anteriores.
Si se requiere durabilidad genérica para todos los observadores, debe diseñarse
primero recibo por consumidor; no fingir esa capacidad con el estado de un único
procesador. Esta es una decisión técnica del equipo, no una nueva política que
deba inventarse a la profesora.

Hasta acordarlo, no se cambia el protocolo interno ni el esquema físico para
forzar una implementación parcial presentada como garantía general. Se conserva
RF-19 corregido, RF-27 cerrado, las cuatro operaciones 9A y las barreras de 9B/8C.

No se creó tabla, columna, ORM, migración, ruta o worker nuevo. El único documento
nuevo de backend es este. Todos los archivos existentes mantienen sus huellas;
los contenedores de pruebas fueron propios y desechables. Referencias y stash
originales conservados, índice vacío, sin commits/push/merge y sin cambios en
`.env` o bases permanentes. `CIERRE.json` del paquete conserva la verificación final.

## 7. Decisión vigente: atomicidad SQL para los avisos internos

### Contrato acreditado y comparación

La fuente centralizada `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`,
páginas impresas 4–5, define RF-19 como estados y cierre automático de sesiones.
RF-21 sí exige correo para convocatorias, con mensaje/URL/código; RF-27 distingue
el aviso interno de feedback. No exige correo para inicio/fin. La implementación
de `ObservadorNotificaciones` genera exclusivamente `SESION_INICIADA` y
`SESION_FINALIZADA`, canal `INTERNA`, para convocatorias ACTIVA. No hay adaptador
de transporte externo registrado en ese Observer. Los correos de RF-21 siguen
pendientes según `RF21_CONVOCATORIAS_AVISOS.md`; no se resuelven ni se reinterpretan
en este incremento. Los RNF del PDF están titulados «propuestos».

| Aspecto | A: una transacción SQL, elegida | B: auditoría/outbox, no implementada |
|---|---|---|
| Atomicidad | Estado, auditoría y avisos internos en un commit; fallo de cualquiera revierte todo | Estado/auditoría/pendiente atómicos; efectos posteriores en otra transacción |
| Concurrencia | Lock RF-19 refrescado; Observer secuencial en la misma Session; existencia del aviso comprobada bajo el lock | Requiere identidad causal, recibo por consumidor, locks y deduplicación de entregas repetidas |
| Recuperación | No hay transición confirmada sin sus avisos. Tras rollback se puede repetir la transición válida | Recupera efectos pendientes sin repetir State; necesario para entregas desacopladas |
| Observer | Suscripción transaccional explícita para efectos SQL; callbacks efímeros conservan publicación postcommit | Necesita diferenciar entrega y confirmación durable del consumidor |
| ORM/migración | Ningún cambio | Cinco columnas/restricciones propuestas en sección 3, no autorizadas por mera existencia del documento anterior |
| Complejidad | Dos fases explícitas en el gestor existente; sin hilo ni segunda Session para los avisos | Productor, consumidor idempotente, dispatcher, recibos, política operacional y migración |
| Disponibilidad | Si no se puede guardar un aviso interno, falla la transición y queda reintentable | La transición puede confirmarse aunque el consumidor esté caído; aviso eventual |
| Pruebas | Rollback del conjunto, reintento, serialización y no duplicación | Además: crash/reanudación, falta de consumidor, ack perdido, upgrade/downgrade y replay durable |

**Se elige A porque cubre íntegramente el efecto interno actual con menor cambio.**
No se necesita garantizar que la transición continúe disponible mientras falla
su INSERT interno. Si el equipo requiere ese desacoplamiento, o entrega externa
recuperable, deberá adoptar explícitamente B y su contrato; A no lo simula.

### Contratos internos efectivamente modificados

- `GestorEventosAcademicos.suscribir_transaccional` registra un Observer SQL.
  `preparar(evento, transaccion)` lo ejecuta secuencialmente sobre la unidad recibida.
  No se usa `gather` ni `to_thread` con una Session compartida.
- `cambiar_estado_y_publicar`: State + auditoría (flush), preparación de efectos
  internos, commit único; cualquier excepción previa hace rollback. Solo después
  publica callbacks efímeros con la semántica anterior.
- `ObservadorNotificaciones.preparar` reemplaza su antigua transacción propia.
  Bloquea/refresca la sesión, verifica estado y exactamente una auditoría de la
  transición y crea los avisos de las convocatorias ACTIVA. No hace commit/rollback.
- La clave lógica del aviso actual es sesión/tipo de transición/convocatoria:
  State no permite volver al mismo estado. Bajo el lock se comprueba aviso existente
  por convocatoria/destinatario/tipo/canal. Un replay transaccional concurrente no
  duplica sus efectos. No se inventa un UUID causal ni una conversión de identidad.
- `publicar` sigue siendo efímero: ya no registra efectos SQL por replay. Su retorno
  no significa persistencia, lectura por el estudiante ni entrega externa. No es
  un endpoint ni una vía para recuperar transiciones académicas.
- Se conserva la firma `crear_gestor_eventos(session_factory)` para API/worker;
  la fábrica ya no abre una segunda Session para estos avisos. La producción
  registra los Observers transaccionales tanto en la ruta como en el runner actual.

El rechazo HTTP 409 de State, la titularidad y el worker +24 h se conservan.
El fallo SQL de un aviso produce error y rollback; al repetir, el cierre todavía
es válido y puede confirmarse. Esto sustituye deliberadamente el antiguo cierre
confirmado con aviso perdido. El fallo de un callback efímero postcommit conserva
su propagación anterior y no revierte los avisos SQL ya confirmados.

### Evidencia actual y separación de los diagnósticos

Paquete: `evidencias/consistencia_notificaciones_20261105T165011Z/`.

- `pruebas_diagnostico_20261105T165018Z`: reproducción ANTES de modificar código:
  **0 aprobadas, 2 fallidas, 0 omitidas/errores, 1 advertencia**, 13.94 s.
  Perdió el aviso tras commit y el replay produjo dos. Archivos/logs originales
  intactos, sin skip/xfail.
- `pruebas_focal_20261105T180044Z`: **196 aprobadas, 0 omitidas/fallos/errores,
  1 advertencia**, 117.39 s. Incluye Scheduling, diez casos RF-19, seis nuevos
  de atomicidad PostgreSQL17, convocatorias, feedback privado y RF-27 cerrado.
- Los seis nuevos están en `tests/integration/test_session_notification_atomicity.py`:
  fallo SQL y reintento docente/worker (dos casos), replay SQL concurrente,
  fallo de commit después del INSERT real, callback efímero fallido después
  del commit y rechazo de mensaje incompatible.
- El diagnóstico antiguo que exigía `notificaciones_estado=PENDIENTE` se conserva
  separado de la aceptación: era una aserción de la propuesta B, no un requisito
  universal. A la sustituye por ausencia de cierre/auditoría/aviso tras fallo y
  reintento exitoso (HTTP 500 → 200 → 409). El replay sí está cubierto de nuevo
  con el mismo objetivo funcional, además de dos preparaciones SQL concurrentes.
- Se conservan los tests anteriores. La prueba unitaria del Observer ahora exige
  no abrir fábrica ni hacer commit/rollback propio; su excepción se propaga al
  dueño de la transacción. El test RF-19 del callback postcommit conserva sus
  aserciones y solo aclara que ese callback es efímero.

Resultados finales adicionales:

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| General `pruebas_total_20261105T180509Z` | 2023 | 38 | 0 | 0 | 1 |
| Replay original `pruebas_diagnostico_20261105T181847Z` | 1 | 0 | 0 | 0 | 1 |

La general duró 766.90 s. El replay original se ejecutó sin modificar el archivo
experimental: `test_republicar_evento_actual_no_debe_duplicar_aviso`, 7.77 s.
El primer diagnóstico original queda separado por su contrato B ya explicado;
su escenario de fallo SQL está corregido y acreditado por la aceptación A.
No se suman suites solapadas. Las 38 omisiones conservan sus motivos en consola
y JUnit (configuraciones de laboratorios alternativos ausentes); no se consideran
aprobadas. La advertencia es la conocida de Starlette/TestClient/httpx.

### Checkpoints y preservación

La selección nominal de los tres checkpoints C1/C2/C3 de la sección 1 se conserva
en `checkpoint_propuesto.json` (16/3/9 archivos). Los 28 hashes originales coincidían
antes de implementar. Los inventarios completos y el listado de 621 archivos
fuera del checkpoint se preservan; no son una autorización para borrar nada.
No hay selección global del índice ni commits.

Adicionales de este incremento, fuera de la selección original de 28:

1. `app/modules/scheduling/domain/events.py`.
2. `app/modules/scheduling/application/cambiar_estado_y_publicar.py`.
3. `app/modules/scheduling/application/registrar_observadores.py`.
4. `app/modules/scheduling/infrastructure/observador_notificaciones.py`.
5. `tests/unit/scheduling/test_observador_notificaciones.py`.
6. `tests/integration/test_session_notification_atomicity.py` (nuevo).
7. Este documento (ya nuevo antes de este incremento).

El informe de auditoría y el comentario del test RF-19, ya incluidos en C3, se
actualizan explícitamente; ningún otro avance 9A/9B/Participation se modifica.
La selección exacta vigente está en `checkpoint_actual_propuesto.json`: C1 conserva
16 archivos, C2 conserva 3 y C3 incorpora estos siete a los nueve anteriores
(16 archivos). Total: **35 archivos**, con rutas, tamaños y SHA-256 finales.
Mensaje C3 recomendado: `fix(scheduling): cierre y avisos internos atómicos sin
publicar notas`. No hacer `git add .` ni preparar solo los archivos antiguos
dejando sus nuevas dependencias fuera. `fuera_checkpoint_actual.json` enumera
todos los archivos locales nuevos/modificados ajenos a esos tres cortes y a la
raíz de evidencias; esta última también se excluye íntegramente.

### Límites

- Garantía en los escritores de aplicación que reutilizan el coordinador y el
  lock, no unicidad física frente a SQL externo arbitrario. No se añade un UNIQUE
  universal sobre notificaciones ni se declara exactamente una vez.
- No se reconstruyen avisos ni se modifican auditorías/notificaciones históricas.
  Si una auditoría es ambigua, el Observer falla cerrado, sin corregirla a ciegas.
- No hay entrega durable para callbacks externos ni correo; una eventual outbox
  requerirá otra aprobación técnica. El runner debe desplegarse y monitorizarse.
- Una pérdida de conexión durante COMMIT puede dejar incierto el resultado para
  el cliente; no se afirma que un error de transporte revierta un commit ya
  confirmado en el servidor. Estado, auditoría y avisos siguen siendo atómicos;
  reconsultar es distinto de forzar otra transición (que conserva su 409).
- RF-19 sigue PARCIAL por operación/despliegue; se elimina el bloqueo de pérdida
  postcommit de sus avisos SQL actuales. RF-21 y RF-27 conservan sus límites de
  correo y notas oficiales. No se modifica ninguna política académica.
- ORM, Alembic, 31 tablas, DBML, Participation, Evaluation y `.env` intactos;
  únicamente PostgreSQL17 propio y desechable para la aceptación.

Cierre técnico: `CIERRE.json` conserva refs/stash/`.env`, archivos afectados y
resultados. No quedaron contenedores del laboratorio. `git diff --check` correcto,
índice vacío, rama/HEAD preservados y sin commits, push, merge ni migraciones.
La general generó un JSON propio de evidencia BD2-04 que se conserva y se excluye
del checkpoint, sin alterar fuentes mientras pytest estaba activo.
