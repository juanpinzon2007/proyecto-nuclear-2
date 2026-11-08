# Fase 9A: continuidad del intento estudiantil existente

Fecha local: 4 de noviembre de 2026 (America/Bogota).
Carpeta única: repositorio original `proyecto-nuclear-2`.
Rama `feature/backend-continuidad`, base y HEAD conservado:
`ac92b7251c96f81ddcb6f390ef21435ab74b6131`.
El usuario autorizó trabajar sobre ese commit sin fusionarlo todavía en develop.
Se partió sin modificaciones rastreadas; se preservan los archivos no rastreados,
configuración, stash y evidencias anteriores. Sin commits, push, merges ni worktrees.

## Diagnóstico y decisiones

`ServicioProgreso.consultar` calcula vencimiento, guarda el agregado y hace commit
si cambia. La UoW incluye flush al confirmar; su rollback de salida no revierte un
commit anterior. La Session compartida conserva autoflush por defecto. Por ello
no se monta ese servicio como lectura pura.

`Intento.actualizar_vencimiento` ya es una regla pura sobre una entidad inmutable:
devuelve la misma instancia o una copia VENCIDO con fin igual a vence_en. No fue
necesario inventar una regla temporal ni persistir desde el GET.

Los casos de uso de primera respuesta y cierre ya implementan validaciones,
inmutabilidad y transacciones. Se reutilizaron después de superar la aceptación
del incremento precedente, sin duplicar motores, repositorios ni navegación.

## A — Progreso privado puro: implementado y acreditado

`GET /api/v1/attempts/{attempt_id}/progress` usa una consulta SQL independiente y
`mapear_progreso` / `ProgresoRespuesta` existentes. La proyección de los datos se
extrajo a `application/progress.py` y la comparten el nuevo lector y el servicio
anterior. El servicio anterior conserva guardar/commit y su semántica histórica;
sus pruebas siguen pasando. El router aislado conserva ese comportamiento.

La consulta principal:

- Revalida JWT, cuenta, rol, contexto de convocatoria, titularidad y matrícula activa
  sobre relaciones persistidas, manteniendo los locks existentes en una UoW nueva.
- Usa `Session.no_autoflush` durante la consulta. No añade objetos, no llama guardar,
  flush ni commit. La salida hace rollback y libera los locks.
- Aplica la regla de vencimiento solo a una copia del dominio. Puede devolver
  estado VENCIDO y fin efectivo mientras la fila SQL permanece EN_CURSO y fin NULL.
  Es una vista efectiva; no una confirmación de transición persistente.
- Conserva FINALIZADO/VENCIDO ya guardados. Permite consultar el estado de cierre;
  no confunde permiso de lectura con permiso de responder ni aplica RF-22.
- Usa el recorrido de la versión exacta para contar lo respondido y su frontera
  alcanzada. No cuenta todas las preguntas del caso ni expone ramas futuras.
  Si Cases no puede acreditar el recorrido, los campos opcionales de ruta quedan
  desconocidos conforme al DTO existente; no se inventa navegación.
- Devuelve únicamente resumen del intento, selecciones propias, IDs aplicables y
  pendientes permitidos, total cuando sea conocido y cantidad respondida. No hay
  contenido de rúbrica, correcciones, justificaciones, notas ni evaluación.

No cambia el esquema HTTP existente. `estado` y `fin` del resumen pueden ser
efectivos, calculados en memoria. Una escritura separada debe confirmar el cierre
antes de que otro caso de uso dependa de un vencimiento persistido.

## B — Primera respuesta: implementado y acreditado

`POST /api/v1/attempts/{attempt_id}/decisions/{decision_id}` llama a la Facade y
`ServicioDecisiones` existentes. `decision_id` es el UUID real de pregunta.
Solicitud y respuesta reutilizan `SeleccionSolicitud` e `IntentoRespuesta`.

Se conservan EN_CURSO, plazo individual histórico y autorización de Scheduling
para responder con sesión EN_CURSO e inicio <= hora del servidor < fin. La pregunta
y opción deben pertenecer a la versión asignada y al punto real del grafo.
Se rechazan futuro, referencias ajenas, ciclos y recorridos no soportados.

La selección se inserta una vez. Duplicados y sustituciones producen 409, aun con
sesión activa. PUT no se registra (405 donde coincide la ruta POST); no es un upsert.
Locks, UNIQUE y guards PostgreSQL existentes mantienen la integridad concurrente.
Un fallo posterior al INSERT hace rollback; el reintento válido puede confirmarse.

Importante: se conserva la semántica existente del comando vencido. Un POST
autorizado cuyo plazo ya venció puede confirmar VENCIDO y devolver 409 sin insertar
respuesta. Esa transición NO procede del GET de progreso. No se oculta este efecto
ni se redefine silenciosamente el servicio existente.

## C — Finalización: implementado y acreditado

`POST /api/v1/attempts/{attempt_id}/finish` reutiliza `Facade.finalizar` y
`ServicioCierre`. Devuelve `IntentoRespuesta`, sin cálculo ni publicación de notas.
Confirma FINALIZADO o VENCIDO según estado y reloj del dominio. Es idempotente:
dos cierres concurrentes devuelven lo mismo y producen un único UPDATE.

La finalización no exige que el grafo termine en FIN: conserva la regla de cierre
voluntario que ya tenía el dominio. No decide cómo calificar ese cierre incompleto.
Tampoco concede permiso de ingreso o respuesta fuera de horario: cerrar un recurso
existente no equivale a continuar respondiendo. Las respuestas confirmadas se
conservan; un cierre concurrente con una respuesta serializa ambos resultados sin
perder selecciones. El fallo posterior al UPDATE revierte completamente.

## Composición y autorización

La principal registra solo estas cuatro operaciones de Participation:

| Método | Ruta | Efecto |
| --- | --- | --- |
| GET | `/api/v1/attempts/{attempt_id}/current-scenario` | Contenido actual, sin escritura |
| GET | `/api/v1/attempts/{attempt_id}/progress` | Estado efectivo y progreso, sin escritura |
| POST | `/api/v1/attempts/{attempt_id}/decisions/{decision_id}` | Primera selección o confirmación del vencimiento existente |
| POST | `/api/v1/attempts/{attempt_id}/finish` | Cierre persistido idempotente, sin notas |

No se registra el router completo. Inicio, provisión, PUT, resultados y ausencias
oficiales permanecen fuera de main. No se cambian autenticación, API de Cases,
reglas confirmadas de Scheduling, ORM, DBML ni migraciones.

Las nuevas dependencias reutilizan fábrica de sesiones, reloj y configuración de
la consulta de escenario. `PARTICIPATION_TIMESTAMP_ZONE` continúa sin valor
predeterminado: falta o zona inválida implica 503. No se toca `.env`.

Se amplían firmas internas con `matricula_activa=False` para conservar los
consumidores anteriores de `crear_facade_8b` y `crear_dependencia_facade_8b`.
La composición principal fuerza True, dentro de la misma transacción, antes de
cualquier escritura, incluso la de vencimiento. El cliente no controla ese flag.
No se altera globalmente la autorización de los adaptadores de otros incrementos.

Los códigos existentes se conservan: 401 sin identidad válida, 403 sin autoridad,
404 sin recurso/ruta, 409 por cierre o respuesta inmutable, 422 por solicitud
inválida y 503 por configuración/dependencia pendiente. Errores inesperados
inyectados retornan 500 y se comprueba rollback, no un éxito ficticio.

## Aceptación y regresión

Pruebas nuevas sobre `app.main.app`, PostgreSQL17 propio y JWT real:

- `test_main_progress.py`: 9 escenarios; estado activo/vencido/finalizado, cero
  DML/flush/commit, autoridad/configuración, historia y lecturas concurrentes.
- `test_main_decisions.py`: 14; primer registro, duplicados/PUT, ámbito y tiempo,
  pregunta futura/opción ajena, concurrencia y rollback.
- `test_main_finish.py`: 10; vertical completo por main, persistencia del vencimiento
  proyectado, autoridad, cierre concurrente, carrera respuesta/cierre y rollback.

Se reutiliza el fixture anterior de la principal: fábricas SQL y JWT reales,
login estudiantil por correo/código y solo reloj sustituido. Grupo, matrícula,
asociaciones, consentimiento e inicio usan preparación administrativa y políticas
explícitas de laboratorio. No se presentan como APIs productivas aprobadas.
Las preguntas y opciones del recorrido vertical se recuperan por GET de la principal.

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
| --- | ---: | ---: | ---: | ---: | ---: |
| Puerta A, 47.16 s | 143 | 0 | 0 | 0 | 1 |
| Puerta B, 73.04 s | 157 | 0 | 0 | 0 | 1 |
| Puerta C, 110.51 s | 167 | 0 | 0 | 0 | 1 |
| General final, 753.74 s | **1997** | **38** | **0** | **0** | **1** |

Las selecciones se solapan; no se suman. Las 33 nuevas están dentro de las cifras
focalizadas y de la general. La general abarca backend/tests y la suite completa
de Participation e incluye la regresión relacionada de los módulos.
El subconjunto relacionado seleccionado en `regresion_relacionada.json` registra
695 aprobadas y 9 omitidas dentro de esa misma general; no es otra ejecución.

Las 38 omisiones antiguas son 29 dependientes de SPS_IDENTITY_TEST_URL, tres de
conexión externa y seis de SPS_PERSISTENCE_LAB_URL. No se usan conexiones del equipo
para hacerlas pasar ni se consideran aprobaciones. Los laboratorios nuevos sí se
ejecutaron. Advertencia conocida: Starlette/TestClient-httpx.

Evidencia relativa: `evidencias/fase9a_20261105T035954Z/`. Cada `pruebas_*/` contiene
comando, rama/HEAD, huellas, consola, JUnit XML y resultado. Se conservan los pasos
en `recorrido_vertical_main.json`, la respuesta efectiva en
`progreso_efectivo_vencido.json` y el estado final en `CIERRE.json`.
El ejecutor elimina credenciales heredadas y desactiva lectura de .env SOLO en el
proceso hijo de pytest. Los fixtures crean PostgreSQL17 en tmpfs y destruyen solo
sus propios IDs. No se instalan dependencias ni se conectan bases permanentes.

```powershell
# Desde la carpeta original autorizada:
& C:\Python313\python.exe -B .\evidencias\fase9a_20261105T035954Z\ejecutar_validacion.py focal
& C:\Python313\python.exe -B .\evidencias\fase9a_20261105T035954Z\ejecutar_validacion.py total
Get-Content .\evidencias\fase9a_20261105T035954Z\recorrido_vertical_main.json -Encoding UTF8
```

## Archivos y límites

- Aplicación: nuevo `application/progress.py`; `services.py` comparte la proyección
  manteniendo el guardado de su servicio anterior.
- Infraestructura: nueva `progress_query.py`; `composition.py` añade el requisito
  explícito de matrícula activa para la composición principal.
- API: nuevos `progress_router.py` y `attempt_operations_router.py`; dependencias
  y montaje acotado en main. Se reutilizan DTOs, mapeadores y esquemas.
- Pruebas: tres archivos de aceptación nuevos; las aserciones de exposición de
  `test_api.py` y `test_main_current_scenario.py` ahora exigen solo las cuatro
  operaciones aprobadas. No se eliminan pruebas ni se debilitan los rechazos.
- Documentación: este informe, contrato HTTP y enlace desde el informe anterior.

La implementación y aceptación de A/B/C están completas dentro de este alcance.
La disponibilidad real sigue condicionada a configuración, esquema y relaciones
persistidas válidas. UTC del laboratorio no aprueba una zona para los datos reales.
Se requiere confirmar su convención histórica antes de configurar el despliegue.

Siguen pendientes ingreso tardío/RF-22, consentimiento y revocación, provisión e
intentos adicionales para el inicio productivo, además de mapeo/agregación/redondeo
y publicación de Evaluation. No se crean ausencias ficticias ni notas oficiales.
No se declara completo todo Participation ni el backend.

Siguiente prioridad, sin implementarla: resolver los contratos de inicio desde
convocatoria y sus políticas pendientes para integrar ese tramo productivo. El
recorrido actual comienza con un intento existente legítimamente autorizado;
su preparación de laboratorio no sustituye esas decisiones.
