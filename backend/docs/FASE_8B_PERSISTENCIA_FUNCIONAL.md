# Fase 8B — Cierre de integración funcional: resultado parcial verificable

Actualización 2026-11-02 · Rama `feature/integracion-backend`.

## Revalidación de la solicitud «Integración final de Cases, Scheduling y Participation»

La solicitud recibida repite el alcance de los adaptadores ya implementados.
Se verificó el código actual, sin rehacer la auditoría del ER ni duplicar servicios.
Su línea base de 1374 aprobadas es anterior a las 20 pruebas de integración
incorporadas en la entrega previa. Esta revalidación **no añade código productivo,
contratos, tablas ni migraciones**. Los cambios de la entrega previa descritos
más abajo siguen siendo antecedentes, no implementaciones nuevas de esta solicitud.

| Comprobación actual | Implementación real / límite |
|---|---|
| Edición asignada, relaciones y opciones | `CasesIntentoSQLAlchemy` consume `consultar_estructura_version` y `validar_opcion_version`. Consulta IDs reales y relaciones de la versión exacta, incluida la histórica archivada; no cambia por la última edición. La proyección no es un DTO de contenido narrativo para Angular ni revela corrección. |
| Respuestas y progreso | Repositorio SQL + `ServicioProgreso` recuperan selecciones persistidas. Solo el proveedor de recorrido puede determinar aplicables/pendientes/total. Sin proveedor, esos campos siguen en `None`. |
| Punto y conservación de respuestas | `validar_cambio_conservando_pasos` exige el validador de Cases en toda selección, incluso primera respuesta o modificación única. No descarta pasos posteriores ni interpreta el orden editorial como permiso. |
| Titularidad, grupo y asignación | `IdentityIntentoSQLAlchemy` reutiliza `ConsultaEstadoIntentoSQLAlchemy`: verifica cuenta, rol, contexto JWT y las uniones participación–matrícula–grupo–asignación–convocatoria–sesión–versión–caso. `SchedulingIntentoSQLAlchemy` comprueba matrícula activa y resuelve el UUID académico persistente. |
| Estado y condiciones de sesión | `consultar_operacion_sesion` relee y bloquea sesión/convocatoria dentro de la UoW escritora. Comprueba ACTIVA, titularidad, versión exacta, estado conocido y fechas coherentes; el permiso de RESPONDER/MODIFICAR requiere la política explícita. |
| Atomicidad | `crear_facade_8b` comparte la Session entre autorizadores y repositorio. No se usa la lectura 8A como permiso definitivo. La UoW conserva commit único, rollback y tratamiento de conflictos existentes. |
| Inicio | Los puertos pueden usar una Session común, pero esta composición conserva `autorizar_inicio` y `obtener_condiciones` cerrados. Ningún intento de fixture constituye autorización productiva. |

No existe una implementación real adicional que pueda conectarse para resolver
las ramificaciones o autorizar edición sin tomar decisiones aún no aprobadas:

| Responsable | Contrato/decisión pendiente concreta | Lo que no debe inferirse |
|---|---|---|
| Cases | Entrada de cada edición, transición por opción, terminal frente a dato ausente y tratamiento de selecciones posteriores al cambiar ruta. Proveer esos datos al contrato `RecorridoVersionCases`. | `escenario.orden` y `pregunta.orden` no son reglas de avance. El ORM de `opcion_respuesta` no contiene destino ni transición. |
| Scheduling | Política de RESPONDER y MODIFICAR por estado de sesión y condiciones temporales, distinguiendo ventana de ingreso y duración individual histórica. Proveerla mediante `AutorizacionEdicionIntento`. | EN_CURSO o una convocatoria ACTIVA no bastan como permiso; el retraso del Worker tampoco concede prórroga. |
| Diseño/persistencia, si Cases necesita guardar transiciones | Aprobar previamente destino/tipo de clave, pertenencia a la misma edición, entrada/terminalidad e inmutabilidad de relaciones históricas. La propuesta deberá usar entidades autorizadas y justificar cada cambio de columna o relación. | La autorización para persistir pasos UUID no autoriza modificar el grafo de Cases. No se propone ni crea una tabla adicional. |

La prueba de recorrido calculable utiliza un proveedor explícito de laboratorio;
la pertenencia y persistencia se verifican con PostgreSQL real. No se declara
probado un recorrido ramificado productivo que no está representado en el código.
Para cerrar la integración interna faltan esas dos implementaciones reales y
sus pruebas de recorrido/autorización. Su cierre tampoco habilitará por sí solo
RF-22 ni el inicio/API productivos: esos controles mantienen su aprobación separada.

Resultados nuevos de esta revalidación:

| Ejecución | Resultado |
|---|---|
| `backend/tests/integration/test_cases_scheduling_operations.py` | 20 aprobadas, 0 omitidas/fallos/errores, 16,84 s |
| Suite completa de Backend y Participation | **1394 aprobadas, 38 omitidas, 0 fallos, 0 errores, 1 advertencia conocida de Starlette; 222,65 s** |

Se ejecutó la misma configuración aislada descrita en este documento: URLs
externas retiradas del proceso hijo, PostgreSQL Docker desechable habilitado y
SQLite aislado. Las 38 omitidas requieren conexiones externas no habilitadas y
siguen pendientes; no representan pruebas aprobadas. Los escenarios positivos
de recorrido/autorización usan proveedores de fixtures, mientras que las
consultas, relaciones, guardado, bloqueos y rollback PostgreSQL son reales.

Verificación estática posterior: **27 tablas**, **11 revisiones**, cabeza única
`20261102_steps_uuid`. El inventario final de contenedores etiquetados
`sps.identity.mapping.lab=true` está vacío. `git diff --check` termina con código
0; conserva el aviso preexistente de LF/CRLF, sin errores de espacios.

El único documento editado en esta solicitud es este informe. La suite generó
automáticamente una evidencia adicional de BD2-04, sin sobrescribir las previas:
`backend/docs/bd/laboratorio_bd2_04/evidencia_27dd12072dcd4cfcad052693b650fb04.json`.
La comparación SHA-256 con el inventario al recibir esta solicitud confirma que
no cambió ningún archivo de código, ORM, migración, ER ni prueba, y que no se
eliminó ningún archivo anterior. No hubo commit/push/merge, cambio de rama, acceso
a bases persistentes, apertura de endpoints, calificaciones oficiales ni inicio
de 8C. No se repitieron los laboratorios de modelos ER alternativos.

## Resultado vigente

**8B no está completa.** Se conectaron fuentes reales de Cases y Scheduling a
la composición transaccional existente. No hay en Cases una representación de
transiciones que permita determinar el recorrido, ni una política aprobada de
Scheduling para responder/modificar. Se mantienen cerradas las escrituras sin
ambos proveedores explícitos. No se habilita inicio, RF-22, API ni evaluación.

Este apartado sustituye cualquier interpretación del antecedente que permitiera
la primera respuesta, una modificación de la única respuesta o repetir una
selección sin consultar la autorización del punto del recorrido.

## Integraciones efectivamente implementadas

| Componente / archivo | Responsabilidad y límite |
|---|---|
| Cases `application/simulation_structure.py` | Consulta la edición UUID exacta PUBLICADO/ARCHIVADO, su rúbrica y regla, escenarios, preguntas y opciones reales. Proyección de IDs/orden sin corrección, justificación, puntuaciones ni valoraciones. Valida pertenencia opción–pregunta–versión; no decide elegibilidad en una ruta. |
| Scheduling `application/attempt_operations.py` | Relee y bloquea sesión y convocatoria mediante la Session del escritor. Comprueba titularidad, convocatoria ACTIVA, versión exacta, estado conocido y fechas conscientes/coherentes. Devuelve hechos, nunca un permiso implícito. Exige transacción existente. |
| Participation `infrastructure/composition.py` | Consume ambas fuentes dentro de la UoW existente. Resuelve el UUID académico real de Scheduling desde Identity; exige matrícula activa y la autorización explícita de edición. Valida los IDs del recorrido contra la estructura de la edición asignada. |
| Participation `application/services.py`, `application/ports.py`, `application/integration_ports.py` | Distinguen RESPONDER de MODIFICAR al pedir autorización. Ampliación interna mínima: argumento `operacion` con valor predeterminado RESPONDER y campo homónimo en condiciones. No cambia HTTP, DTO público ni identificadores. |

La Facade, servicios, repositorio de pasos y UoW se reutilizan. No hay tablas,
columnas, ORM, revisiones Alembic, JWT alternativo ni operaciones académicas nuevas.
Las consultas de Cases son internas y no autentican por sí mismas: el consumidor
Participation comprueba previamente el alcance y la titularidad de la edición.
No se reutiliza el DTO docente que contiene corrección y valoraciones.

## Recorrido real encontrado y defecto corregido

Cases guarda `version_caso → escenario → pregunta → opcion_respuesta`, con orden
editorial. En el dominio, persistencia y servicios actuales no se encontró destino
de opción, transición, punto inicial ni algoritmo de recorrido. El atributo
académico `opcion_respuesta.id_escena_destino` del DBML no está implementado en el
ORM actual. Orden, cantidad de preguntas y pertenencia a una versión no prueban
que una pregunta esté disponible para responder.

Se detectó una omisión concreta en el adaptador previo: su salida temprana
permitía la primera respuesta o modificar la única selección sin llamar al
validador de Cases, incluso cuando había un proveedor configurado. Ahora toda
escritura exige `RecorridoVersionCases.validar_cambio`, además de que la pregunta
pertenezca al recorrido declarado. Una respuesta conservada excluida del recorrido
produce rechazo; no se elimina ni invalida automáticamente ningún paso.

Sin proveedor, el progreso recupera selecciones y cantidad respondida reales,
pero devuelve `None` para decisiones aplicables, pendientes y total. No se calcula
porcentaje ni se presenta como recorrido real el orden editorial. La prueba con
recorrido explícito usa una fixture: demuestra el contrato, no una ramificación
productiva. Las preguntas disponibles en un punto requieren el validador; no se
añade un campo público que confunda todas las aplicables con las disponibles.

**Contrato mínimo pendiente de Cases:** fuente inmutable vinculada a la edición
asignada que determine entrada, transiciones por opción, terminación y elegibilidad
del punto; distinguir destino terminal de información ausente; resolver qué
ocurre con respuestas posteriores si cambia una selección. El puerto existente
puede consumir esa fuente, pero no la crea. Persistir esos datos o cambiar su
semántica requiere aprobación previa. Añadir solamente una columna destino no
resuelve las reglas de entrada, conservación ni versionamiento.

## Scheduling, tiempo y límite transaccional

El servicio de Scheduling lee columnas actuales con `FOR UPDATE` de sesión y
convocatoria. La identidad, matrícula y rol se verifican con los controles previos
de Identity; el resolver persistente proporciona el UUID académico real.
Participación/intento y sus respuestas conservan los bloqueos y comparación del
repositorio existente. La consulta de Scheduling y el guardado usan la misma
Session; no se concede permiso desde un DTO de lectura obtenido antes de la UoW.

Se validan SIN_INICIAR/EN_CURSO/FINALIZADO como estados conocidos, **sin concluir
que EN_CURSO autorice editar**. El proveedor de autorización recibe estado,
fechas, reloj del servidor, asignación, matrícula y operación. Sin proveedor o
ante condiciones inválidas, se rechaza la operación. Los errores de infraestructura
se propagan y la UoW revierte; no hay acceso alternativo ni autorización por defecto.

El vencimiento individual y la conservación de respuestas siguen siendo reglas
del dominio existente, con duración histórica y reloj inyectado. El cierre y el
vencimiento se serializan con modificaciones mediante los bloqueos del intento.
El cierre voluntario no se convierte en autorización de nuevas respuestas.

**Decisión pendiente de Scheduling:** matriz aprobada de RESPONDER/MODIFICAR
por estado de sesión, retiro/vigencia de convocatoria y límites de programación
frente al tiempo individual. La política RF-22 sigue sin configurar; su ventana
de ingreso no se reutiliza para editar ni como prórroga. No se inventan tolerancias
ni valores de duración. Los bloqueos probados no equivalen a una garantía de
ausencia de deadlocks en cualquier escritor futuro: deben respetarse órdenes de
locks compatibles y tratar/reintentar conflictos completos donde corresponda.

## Inicio y operaciones demostradas

Las comprobaciones existentes pueden componerse sobre una misma Session, pero
eso no aprueba consentimiento, cupos, permisos adicionales, provisión, duración
ni RF-22. `autorizar_inicio` y `obtener_condiciones` continúan rechazando el inicio
productivo. Los intentos del laboratorio son datos sintéticos, no un alta autorizada.

Con proveedores explícitos **solo de pruebas** se demuestra registrar, releer
desde otra Session, modificar, finalizar idempotentemente, conservar respuestas
y rechazar cambios tras cierre/vencimiento. Sin proveedor de recorrido o permiso
de edición, se demuestra rechazo sin pasos nuevos. También se comprueban versión
anterior/rúbrica exacta, relaciones ajenas, Session compartida, acción diferenciada,
cierre concurrente de sesión y modificación concurrente con vencimiento.

## Pruebas y estado técnico

Resultados ejecutados en esta entrega:

| Ejecución | Resultado real |
|---|---|
| `test_steps_uuid.py` + `participation/tests/test_application.py` | 84 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 27,20 s |
| `test_cases_scheduling_operations.py` | 20 aprobadas, 0 omitidas/fallos/errores; 16,61 s |
| Suite `backend/tests backend/app/modules/participation/tests -q -rs --tb=short` | **1394 aprobadas, 38 omitidas, 0 fallos, 0 errores, 1 advertencia; 211,93 s** |

La advertencia conocida es `StarletteDeprecationWarning` sobre TestClient/httpx.
Las 38 omitidas corresponden a pruebas existentes con URLs externas o conexión
PostgreSQL configurable no habilitadas. No se cuentan como aprobadas. El
laboratorio Docker propio sí estuvo habilitado y ejecutó las pruebas SQL reales.

Para reproducir la suite, retirar del entorno del proceso hijo
`TEST_DATABASE_URL`, `SPS_IDENTITY_TEST_URL`, `SPS_PERSISTENCE_LAB_URL`; establecer
`SPS_TEST_POSTGRESQL=0`, `SPS_TEST_IDENTITY_MAPPING_DOCKER=1`, y ejecutar:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

No se modifica `.env`. Debe estar disponible Docker con la imagen `postgres:17`.

Las pruebas nuevas están en
`backend/tests/integration/test_cases_scheduling_operations.py`. Las pruebas
previas de `test_steps_uuid.py` ahora suministran un recorrido explícito en sus
fixtures positivas; las negativas pasan `recorrido=None` expresamente. No se
suprimen escenarios ni se debilitan los rechazos para conservar resultados.

Se desactivaron las URLs externas heredadas y se habilitó únicamente el creador
de laboratorios Docker nuevos. El fixture usa nombre/ID y etiqueta propios,
almacenamiento temporal, puerto TCP efímero, comprobación de identidad de base,
ausencia de volumen persistente y limpieza por ID del contenedor creado. Las
pruebas SQLite usan almacenamiento aislado. Los permisos y recorridos positivos
son fixtures; la SQL, FK, triggers, bloqueos y persistencia PostgreSQL son reales.
No se afirma que exista un recorrido ramificado o política temporal productivos.

El registro estático del metadata conserva **27 tablas**; `ScriptDirectory`
confirma **11 revisiones y una cabeza `20261102_steps_uuid`**. No se ejecutó
Alembic sobre ninguna base persistente. El inventario final de contenedores con
etiqueta `sps.identity.mapping.lab=true` está vacío.

### Archivos de esta entrega y Git

Nuevos:

- `backend/app/modules/cases/application/simulation_structure.py`.
- `backend/app/modules/scheduling/application/attempt_operations.py`.
- `backend/tests/integration/test_cases_scheduling_operations.py`.

Modificados respecto al inventario inicial de esta tarea:

- `backend/app/modules/participation/application/ports.py`.
- `backend/app/modules/participation/application/services.py`.
- `backend/app/modules/participation/application/integration_ports.py`.
- `backend/app/modules/participation/infrastructure/composition.py`.
- `backend/tests/integration/test_steps_uuid.py`.
- Este informe.

La suite generó además su evidencia propia de BD2-04:
`backend/docs/bd/laboratorio_bd2_04/evidencia_8b4add3ddf4f4d00a76166572beb9c88.json`.
Se compararon hashes SHA-256 con los 329 archivos del inventario inicial para
separar estos cambios de los acumulados de fases previas. El diff contra HEAD
contiene también aquellos avances y no se atribuye íntegramente a esta entrega.
`git diff --check` terminó con código 0, sin errores de espacios; Git muestra
solamente su aviso de conversión LF/CRLF de un repositorio de Cases ya modificado
antes de esta tarea. La rama sigue siendo `feature/integracion-backend`.
No hubo commit, push, merge, cambio de rama, modificación del ER/ORM/migraciones
ni acceso a bases persistentes. Se conservan los cambios locales anteriores.

## Qué falta para declarar 8B completa

1. Cases debe proporcionar la fuente de recorrido por versión y las reglas de
   elegibilidad/cambio, con decisiones académicas aprobadas donde correspondan.
2. Scheduling debe proporcionar la política real de RESPONDER/MODIFICAR y resolver
   RF-22 y las condiciones indispensables del inicio sin mezclar ambos permisos.
3. Sustituir proveedores de fixtures por implementaciones reales y demostrar
   extremo a extremo inicio autorizado, recorrido, modificaciones permitidas,
   persistencia, cierre y rechazos con esas políticas reales.

No se solicita ampliar el ER automáticamente, no se inicia otra fase BD ni 8C,
y no se declara terminada la integración esencial pendiente.

<details>
<summary>Antecedentes de 8B: conservar evidencia histórica; prevalece el resultado vigente anterior</summary>

# Fase 8B — Persistencia funcional con UUID reales de Cases

Actualización 2026-11-02 · Rama `feature/integracion-backend`.

## 1. Resultado y alcance real

Se implementa el flujo interno **registrar → recuperar desde otra Session →
modificar → recuperar → finalizar → conservar respuestas y rechazar cambios**.
Se demuestra en PostgreSQL nuevo y desechable mediante los servicios y Facade
existentes, repositorio SQL y una misma UoW para persistencia y autorizadores.

La autorización posterior, rotulada «opción A», especifica **UUID directos**.
Ese texto es la decisión aplicada; no se ejecutó la propuesta anterior de claves
INTEGER alternativas para preguntas/opciones. El antecedente al final queda
superado en ese punto. No se modifica el DBML académico ni se inventan IDs.

**No se habilita el inicio ni la API productiva.** La edición requiere un
autorizador explícito del servidor que no tiene implementación predeterminada.
El recorrido completo y la conservación de otras respuestas ante cambios de ruta
requieren un contrato de Cases. El flujo básico está probado; no se declara
resuelta la ramificación general ni operativo el simulador público.

## 2. Esquema físico verificado de Cases

| Registro | Tabla real / clave | Relaciones relevantes |
|---|---|---|
| Familia | `caso.id UUID PK` | `id_caso INTEGER` alternativo existente de BD2-05; no se convierte entre ambos |
| Edición | `version_caso.id UUID PK` | FK a caso; UNIQUE(caso_id,numero) |
| Escenario | `escenario.id UUID PK` | FK a versión; UNIQUE(versión,orden) |
| Pregunta | `pregunta.id UUID PK` | FK a escenario; UNIQUE(escenario,orden) |
| Opción | `opcion_respuesta.id UUID PK` | FK pregunta_id; UNIQUE(pregunta_id,orden). Es tabla propia, no un campo JSON |

Los modelos, migraciones vigentes y pruebas de FK sobre PostgreSQL confirman los
destinos relacionales. `paso_simulacion.id_decision` referencia **pregunta.id**;
`id_opcion` referencia la opción de esa misma pregunta. No se equipara toda la
entidad académica decisión/criterio a pregunta ni se rediseña la evaluación.

## 3. Modelo y revisión Alembic

Revisión nueva **`20261102_steps_uuid`**, padre verificado
**`20261102_participation_history`**. Metadata final: **27 tablas integradas**;
una cabeza y once revisiones. No significa que sean 27 de las 28 entidades
académicas completas: se conservan las estructuras técnicas previas y diferencias
documentadas del ER. No se elimina nada para forzar un conteo.

Se añade exclusivamente la entidad oficial `paso_simulacion`, con las nueve
columnas originales y las dos referencias a Cases adaptadas a UUID:

- `id_paso INTEGER PK` autogenerado; `id_intento INTEGER NOT NULL FK intento`.
- `id_decision UUID NOT NULL FK pregunta.id`.
- `id_opcion UUID NOT NULL` con FK compuesta `(id_opcion,id_decision)` a
  `opcion_respuesta(id,pregunta_id)`.
- Número, fecha, segundos transcurridos y reflexión conservan sus tipos del ER.
- UNIQUE(intento,número) original y UNIQUE(intento,decisión) para la proyección
  de selección actual que **ya exige el dominio**; número positivo/tiempo no negativo.

Se añade en `opcion_respuesta` el índice UNIQUE `(id,pregunta_id)` necesario para
el destino compuesto PostgreSQL. No cambia su PK ni sus columnas ni registros;
la unicidad ya se deriva de su PK, pero PostgreSQL necesita la clave compuesta.
No hay tablas de traducción, backfill ni generación de UUID para representar IDs
INTEGER. Los UUID leídos son los persistidos por Cases.

Cada paso conserva la **selección actual**, según el dominio existente. Modificar
antes de cerrar reemplaza esa selección; no se declara un registro append-only
de todas sus ediciones. Al cerrar se congelan las respuestas conservadas.

## 4. Integridad: qué protege PostgreSQL y qué protege Application

FK reales garantizan intento/pregunta existentes y opción de la pregunta indicada.
No se sustituyen por validaciones de Python. Dos funciones nuevas y tres triggers
amplían las protecciones, sin reemplazar BD2-04/05/07: **31 triggers en total**.

`f8b_paso` bloquea participación y después intento y exige:

- Intento EN_CURSO; claves/decisión/número de un paso ya existente inmutables.
- Pregunta de la **versión exacta** fijada en la asignación, no otra edición de la
  misma familia. La FK compuesta rechaza opción de otra pregunta.
- Registro entre inicio inclusive y vencimiento exclusivo, duración histórica
  BD2-07, segundos transcurridos coherentes y ausencia de retroceso respecto de
  las respuestas guardadas. El cálculo conserva microsegundos sin multiplicar
  intervalos grandes por float8.
- Prohibición de borrar pasos. La política de eliminar respuestas por cambio de
  ruta no está aprobada y no se implementa por suposición.

`f8b_cierre` rechaza un fin anterior a la última respuesta; complementa las reglas
BD2-07 de estado/cierre/inmutabilidad. El tercer trigger prohíbe TRUNCATE de pasos
mediante la función histórica BD2-07, sin modificarla.

Los guards son SECURITY INVOKER y usan tablas public explícitas. No autentican
JWT ni conceden permisos de actor: esa responsabilidad sigue en Application.
El reloj real se valida en dominio mediante el reloj inyectado del servidor, no
mediante un NOW() SQL imposible de controlar en pruebas. Los triggers comprueban
estado y coherencia temporal de los valores persistidos, no una política RF-22.

READ COMMITTED es la modalidad principal probada. REPEATABLE READ se rechaza en
mutaciones para evitar validaciones históricas sobre snapshots obsoletos, como
en BD2-07. No se promete ausencia universal de deadlocks o soporte de aislamiento
no verificado por estas pruebas; abortar obliga a rollback y nueva autorización.

## 5. Servicios, repositorio y transacción conectados

`RepositorioParticipacionSQLAlchemy` reutiliza el lector existente con locks y
la fuente de duración histórica. Implementa el contrato del repositorio sobre las
tablas reales: recuperación completa de participación/intento/pasos, IDs de
secuencias PostgreSQL, alta estructural y guardado con estado previo esperado.
Los pasos nuevos se insertan, solo los modificados se actualizan y nunca se
borran los restantes. No hay upsert ni commit propio. Rechaza instantáneas obsoletas.

El escritor exige transacción PostgreSQL: SQLite se utiliza para DDL/contratos/
lecturas cuando corresponda, sin simular secuencias concurrentes o locks de fila.
Las secuencias pueden dejar huecos tras rollback; no son números académicos.

`crear_facade_8b` compone una **Facade por operación**, con UoW nueva y Session
explícita. No reutilizar esa instancia para otra petición: la UoW existente es de
un solo uso. Cada operación siguiente construye otra Facade, sobre la misma BD.
La propiedad interna `UnidadTrabajoSQLAlchemy.sesion` permite a los adaptadores
usar exactamente la misma transacción; no hay Session global ni conexión de `.env`.

- `IdentityIntentoSQLAlchemy`: exige coincidencia entre cuenta del servidor y
  estudiante del caso de uso, bloquea cuenta/convocatoria/matrícula y comparte el
  lock del rol. Reutiliza la consulta autorizada de estado y el resolver persistente;
  relee activo/rol/titularidad/contexto JWT, sin creer cabeceras o campos del cliente.
- `SchedulingIntentoSQLAlchemy`: confirma asignación/matrícula, indicador activo
  y sesión bloqueada; solicita autorización explícita de edición sobre una proyección
  inmutable de esos datos y del reloj del servidor. **Sin proveedor, rechaza**.
- `CasesIntentoSQLAlchemy`: valida UUID reales por opción→pregunta→escenario→
  versión asignada y valida los IDs devueltos por el contrato de recorrido.

Se reutilizan `ServicioDecisiones`, `ServicioProgreso`, `ServicioCierre` y
`ParticipacionFacade`; no se reemplazan sus reglas por SQL o routers gigantes.
Los cambios en Facade/puertos son los tipos de referencias Cases y el contrato
explícito de recorrido/edición. No se cambia la arquitectura de los siete patrones.

La UoW confirma una sola vez y revierte ante cualquier fallo. Los conflictos
23505/40001/40P01 también se traducen si aparecen **antes** de commit, después
de rollback/cierre; no hay reintento automático ni conservación parcial de pasos.
Se prueban dos registros simultáneos y modificación contra cierre, con un resultado
serializado y respuestas conservadas. Los órdenes de otros escritores aún deben
coordinarse al habilitar nuevas operaciones; no se infiere de esto seguridad de
un inicio productivo que todavía no está implementado.

## 6. Ingreso, edición y progreso sin inventar políticas

RF-22 sigue regulando el **ingreso** y permanece sin habilitar. No se reutiliza
su ventana o tolerancia para decidir automáticamente cada edición de un intento
ya iniciado. `AutorizacionEdicionIntento` es un puerto separado, sin implementación
productiva por defecto. Recibe datos bloqueados de la misma operación; no un
permiso cacheado de 8A ni una lectura efectuada en otra Session.

Las pruebas suministran un autorizador **exclusivo de fixtures**, para intentos
creados por fixtures. No hay un autorizador que acepte todo en código productivo.
El dominio aplica siempre el vencimiento individual histórico. Una autorización
ausente, excepción o retorno distinto de None (incluido False) impide guardar.
El inicio de nuevos intentos/cupos sigue rechazándose explícitamente.

Para el recorrido:

- Sin contrato de Cases, el progreso recupera **selecciones y estado reales**, pero
  `decisiones_aplicables`, `pendientes` y `total_aplicable` son **None/null**. No
  informa cero pendientes ni calcula porcentajes contando todas las preguntas.
- Sin otras respuestas que pudieran invalidarse, o sin cambio de opción, el
  cambio puede conservar los pasos conocidos. Si hay otras respuestas y falta
  validación de conservación de Cases, se rechaza con ReglaPendiente.
- Con un proveedor explícito, sus decisiones deben ser UUID de la edición exacta;
  la exclusión de selecciones ya conservadas no se resuelve borrándolas.

El flujo de dos preguntas se prueba con un recorrido explícito **solo de laboratorio**.
No se presenta esa fixture como algoritmo productivo de ramificación. Está pendiente
el contrato real de recorridos generales y su política de invalidación.

`IdentificadorCases = int | UUID` conserva los dobles/contratos INTEGER anteriores
sin convertirlos. Los adaptadores SQL reales exigen UUID. Los esquemas y rutas
HTTP provisionales aceptan UUID y representan null de recorrido desconocido;
siguen sin registrarse globalmente. La dependencia productiva permanece en 503.

## 7. Pruebas ejecutadas y distinción de evidencia

- Regresión inicial Domain/Application/API: **173 passed, 1 warning**, 6,44 s.
- Primer grupo SQL nuevo: **19 passed**, 18,87 s. Su fixture se corrigió antes:
  crear convocatoria con sesión ya iniciada produjo un error de preparación;
  se pasó a SIN_INICIAR→convocar→EN_CURSO, respetando Scheduling.
- Regresión ampliada intermedia: 442 passed, 1 failed, 9 skipped, 1 warning,
  57,09 s. El nuevo FK impidió TRUNCATE intento antes de llegar a su trigger;
  se ajustó la prueba a TRUNCATE de intento y paso juntos, conservando el rechazo
  esperado del guard. No se deshabilitó ninguna protección.
- Tras corrección: **446 passed, 9 skipped, 1 warning**, 48,38 s.
- Primera suite completa: **1371 passed, 38 skipped, 1 warning**, 188,92 s.
  Corresponde al estado anterior a separar explícitamente ingreso/edición y no
  se atribuye al estado final.
- Grupo específico final: **44 passed, 0 skipped, 0 failed/errors, 1 warning**,
  23,46 s: 29 tests de pasos (28 PostgreSQL y uno SQLite/contrato HTTP) y 15
  tests UoW (tres nuevos sin BD para errores antes de commit).
- Suite completa final: **1374 passed, 38 skipped, 0 failed, 0 errors,
  1 warning**, **196,68 s**, después de separar ingreso/edición y verificar
  retornos inválidos. Son **32 aprobadas nuevas** respecto de las 1342 anteriores:
  29 de pasos y tres de UoW. Las omitidas no se cuentan como aprobadas: 29 requieren
  URL externa de Identity, tres conexiones Participation están deshabilitadas y
  seis requieren otra URL de persistencia. La advertencia sigue siendo la
  deprecación conocida Starlette/TestClient/httpx.

Comando ejecutado con las variables de aislamiento descritas abajo:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

En desarrollo hubo tres fallos de ubicación de una prueba nueva (NameError),
corregidos restaurando intacto el test previo. Otra ejecución no pudo preparar
PostgreSQL porque Docker no resolvió el alias corto de la imagen: 16 passed,
1 failed y 25 errors. Se verificó la imagen local por nombre completo, sin pull,
cambio de infraestructura, reutilización de contenedores o skips para ocultarlo;
las ejecuciones posteriores quedaron limpias.

Operaciones verificadas de verdad en PostgreSQL: guardar/modificar UUID, recuperar
en Session nueva, cerrar/idempotencia, conservar respuestas, rechazar cambios tras
cierre y opciones/preguntas de otra pregunta, versión anterior de la misma familia
u otra familia; vencimiento histórico; falta de autorización de edición, cuenta/
matrícula/convocatoria/contexto inválidos; conservación ante ruta no aprobada;
concurrencia, rollback después de INSERT, instantánea obsoleta y ciclo Alembic.

La prueba HTTP usa TestClient en una app local de test con dependencias de identidad
sobrescritas y la Facade SQL real: demuestra serialización UUID y persistencia,
**no** un nuevo login HTTP productivo. La titularidad se vuelve a comprobar desde SQL.
Los tests de UoW sin BD no se cuentan como concurrencia PostgreSQL.

## 8. Archivos, migración e integridad anterior

Nuevos: revisión `alembic/versions/20261102_steps_uuid.py`,
`participation/infrastructure/repository.py`,
`participation/infrastructure/composition.py`,
`tests/integration/test_steps_uuid.py`.

Modificados: modelo de Cases (solo índice compuesto de opciones); modelos de
Participation (paso); dominio/DTO/puertos/Facade (tipos UUID); servicio de progreso
(recorrido desconocido explícito); lector (tipos Cases); UoW (Session compartida y
conflictos antes de commit); esquemas/router/documentación HTTP provisionales;
este informe; tests de UoW y seis regresiones de metadata/cabeza/BD2-01/05/07.

Los tests históricos conservan sus revisiones objetivo originales; para comparar
el ORM completo se migra explícitamente al head actual. No se atribuyen nuevas
tablas a cabezas anteriores ni se eliminan pruebas. El SQL congelado de Cases y
los cuerpos de migraciones anteriores no se modifican.

Downgrade: bloquea pasos y **rechaza cualquier respuesta existente**. Solo en vacío
elimina sus triggers/funciones, la tabla y el índice propio, dejando los 28 triggers
anteriores. No elimina respuestas para facilitar una reversión.

## 9. Aislamiento, estado final y pendientes

Solo SQLite aislado y PostgreSQL 17 creado de nuevo por los fixtures propietarios:
ID/nombre/etiqueta propios, datos tmpfs sin volúmenes ajenos, puerto efímero
127.0.0.1, base inicialmente vacía y readiness por conexión SQL TCP real. El finally
elimina únicamente recursos creados por el propio fixture.

El subproceso retira TEST_DATABASE_URL, SPS_IDENTITY_TEST_URL y
SPS_PERSISTENCE_LAB_URL; SPS_TEST_POSTGRESQL=0 impide usar conexiones externas y
SPS_TEST_IDENTITY_MAPPING_DOCKER=1 habilita solo laboratorios nuevos. No se modifica
`.env` ni se consulta/migra ninguna base persistente. No se instalan dependencias.

Verificación final: **27 tablas integradas, una cabeza `20261102_steps_uuid`,
padre `20261102_participation_history`, once revisiones**. No se aplicó este
esquema a ninguna base persistente ni se certifica el estado de las bases del equipo.

`git diff --check` pasa con salida 0. Git advierte sobre futura normalización
LF/CRLF en un archivo previo del repositorio de Cases que no se modificó en esta
fase. Los archivos nuevos también se revisan por separado. La comparación SHA-256
con el inventario inicial no muestra archivos anteriores eliminados ni cambios
fuera de los archivos de esta implementación enumerados en la sección 8.
El ER original, `main.py`, dependencias HTTP de seguridad, módulos Identity/
Scheduling, migraciones anteriores y SQL histórico conservan sus bytes.

La regresión BD2-04 genera JSON nuevos de evidencia dentro de su laboratorio
documental; no sobrescribe evidencia anterior. El inventario final de contenedores
con etiqueta `sps.identity.mapping.lab=true` está vacío. La rama sigue siendo
`feature/integracion-backend`, con los cambios acumulados sin commit, push o merge.

Para producción faltan autorización real de edición de Scheduling, condiciones
académicas de inicio/consentimiento/cupos, RF-22, interpretación aprobada de
timestamps sin zona y recorridos generales de Cases. Las pruebas usan UTC explícito,
no una política temporal inferida del equipo. No se publica ninguna nota.
El incremento básico de persistencia está demostrado; no se habilita el backend
completo, no se inicia 8C y no se hace commit, push, merge ni cambio de rama.

Próximos pasos concretos, fuera de esta ejecución:

1. Integrar en Scheduling un proveedor aprobado de `AutorizacionEdicionIntento`,
   manteniendo separado ingreso RF-22 de la duración individual y la edición.
2. Integrar en Cases `RecorridoVersionCases` y validar conservación de pasos en
   cambios de ruta; mantener null de recorrido mientras no esté disponible.
3. Acordar la interpretación temporal de los timestamps sin zona antes de configurar
   escritores sobre datos reales. Luego completar provisión/inicio y sus políticas
   de consentimiento/cupos/ingreso antes de instalar la dependencia HTTP productiva.
   No se necesita otro puente INTEGER–UUID para los pasos implementados aquí.

---

<details>
<summary>Antecedente previo a autorizar UUID directos (no ejecutado como diseño actual)</summary>

# Fase 8B — Incremento parcial de lectura persistente

2026-11-02 · Rama `feature/integracion-backend`.

**8B NO está completa.** Se implementa una funcionalidad independiente real:
consulta interna autorizada de la **cabecera persistida del intento**, con su
estado almacenado y vencimiento histórico. No se presenta como progreso de
respuestas ni se habilita el registro/modificación de decisiones o su cierre.

## 1. Implementado y reutilizado

`ConsultaEstadoIntentoSQLAlchemy.consultar(usuario, id_intento)` devuelve el
`ResumenIntento` de Application ya existente. El nuevo puerto interno
`ConsultaEstadoPersistidoIntento` define ese alcance, sin cambiar contratos previos.

La consulta:

1. Exige un ID válido y contexto de usuario proporcionado por Identity del servidor.
   Relee cuenta activa y rol ESTUDIANTE desde el repositorio real; no usa roles
   o estado de cuenta declarados por el llamador como prueba suficiente.
2. Resuelve el UUID Scheduling mediante el vínculo persistente inequívoco. La
   adaptación de la cadena de usuario a su misma PK INTEGER reutiliza `id_entero`.
3. Enlaza intento→participación→matrícula/grupo→asignación→convocatoria/sesión→
   versión exacta/familia/rúbrica. Filtra la cuenta de matrícula y el UUID convocado.
   No utiliza la última edición del caso ni consulta datos de evaluación.
4. Reutiliza `ValidadorConvocatoriaScheduling.validar_contexto`: el contexto de
   convocatoria debe coincidir con el persistido y la convocatoria debe ser propia
   y ACTIVA. Una sesión FINALIZADO no impide esta lectura; no concede un ingreso.
5. Reconstruye fechas con `FechasPersistencia` explícito y reutiliza
   `consultar_duracion_historica` de BD2-07. No recalcula duración desde Scheduling.
6. Devuelve ID de intento/participación, número, estado almacenado, inicio, fin y
   vencimiento. No devuelve selecciones, total, porcentaje, corrección, nivel,
   puntaje, justificación, correo, códigos o hashes.

Se permite consultar la cabecera de un intento cuya versión luego fue archivada:
el estado y duración históricos siguen siendo los mismos. No se exige una nueva
versión PUBLICADO para leer su propia cabecera. Esto no modifica el requisito de
versión publicada para ingreso que conserva 8A.

La matrícula se utiliza para titularidad y grupo de la participación histórica,
no para emitir una autorización de continuar. No se define una política nueva
de fechas/reingreso. La regla de convocatoria ACTIVA se reutiliza de Identity;
no se habilita acceso nuevo a convocatorias retiradas.

## 2. Lo que esta lectura NO afirma

El estado es **el almacenado**, no una transición automática: si el reloj real
ya superó `vence_en` pero el intento sigue EN_CURSO en PostgreSQL, esta consulta
no persiste VENCIDO ni declara permiso de continuar. No tiene un reloj nuevo,
worker o política temporal. Su respuesta no es `ProgresoIntento`.

No hace flush, commit, rollback, cierre de Session, INSERT/UPDATE/DELETE ni toma
locks de mutación. El llamador es responsable de la Session prestada. Las consultas
sucesivas no se convierten en autorización transaccional de escritura.
No se inventa un `Intento(pasos=())` para poder cerrar un agregado que no se pudo
leer completo. Tampoco se devuelve «cero respondidas» por falta de almacenamiento.

Los errores de recurso inexistente/ajeno comparten respuesta genérica; los errores
SQL/Identity de integración se cierran sin detalles de conexión. Si no está acordada
la zona de timestamps sin offset, la lectura falla con mapeo pendiente: no asume UTC
del servidor. UTC se configura explícitamente solo en las fixtures sintéticas.

No se registra un endpoint ni se compone la fachada productiva. El contexto de
entrada debe proceder del JWT verificado por la dependencia Identity existente;
el adaptador no recibe un token para verificarlo con un sistema alternativo.

## 3. Bloqueo concreto de decisiones y pasos

No se repite la auditoría general del ER. El punto bloqueante es la FK original:

```text
paso_simulacion(id_opcion INTEGER, id_decision INTEGER)
    → opcion_respuesta(id_opcion INTEGER, id_decision INTEGER)
```

En el ORM y PostgreSQL vigentes:

```text
opcion_respuesta.id UUID PK
opcion_respuesta.pregunta_id UUID FK → pregunta.id UUID
pregunta.escenario_id UUID → escenario.version_caso_id UUID
```

No existen las columnas INTEGER destino ni la UNIQUE compuesta que exige el ER.
No hay tabla `decision` integrada. `PreguntaModel` tampoco tiene el criterio único
de `decision` del ER: las valoraciones existentes son opción×criterio. Renombrar
pregunta como decisión no demuestra por sí solo equivalencia académica.

`CasesPort` y `PasoSimulacion` exigen IDs INTEGER. Sus validaciones no pueden
cumplirse contra UUID mediante casts, hashes, ordinales o UUID generados para
simular correspondencias. Por eso no se crea `paso_simulacion` con una FK omitida,
una tabla de opciones ficticia o columnas UUID no autorizadas.

No hay modelo ni migración nuevos en esta entrega. La cabeza sigue siendo
`20261102_participation_history`, con 26 tablas integradas y diez revisiones.

## 4. Cambio exacto que necesita aprobación

**Recomendación para mantener los IDs INTEGER del ER:** autorizar un puente dentro
de las filas actuales de Cases, sujeto a confirmar formalmente la correspondencia
semántica pregunta–decisión. Propuesta técnica, NO implementada:

1. `pregunta.id_decision INTEGER UNIQUE` alternativo, manteniendo su PK UUID.
2. `opcion_respuesta.id_opcion INTEGER UNIQUE` alternativo, manteniendo su PK UUID.
3. `opcion_respuesta.id_decision INTEGER` para el destino compuesto oficial;
   UNIQUE(id_opcion,id_decision) y FK a pregunta.id_decision.
4. UNIQUE(pregunta.id,pregunta.id_decision) y FK compuesta
   `(opcion_respuesta.pregunta_id, opcion_respuesta.id_decision)` a esa pareja,
   para impedir que el INTEGER señale otra pregunta que el UUID real.
5. Solo después, crear `paso_simulacion` original, con FK al intento y FK compuesta
   real de opción/decisión. Validar la cadena opción→pregunta→escenario→versión exacta
   de la asignación; bloquear intento antes de escribir pasos y rechazo SQL de
   cambios sobre intentos cerrados.

Las claves alternativas de históricos tendrían que permanecer nullable al agregar;
se rechazarían selecciones sin correspondencia acreditada. No habría backfill
automático ni conversión de tipos. Completar esos campos en contenido publicado
está impedido por BD2-04: requiere un procedimiento de conciliación expresamente
autorizado compatible con su inmutabilidad, no desactivar triggers. La propuesta
no garantiza que todas las versiones legadas queden utilizables automáticamente.

Este puente es una desviación de atributos respecto del ER y **no resuelve por
sí solo** la diferencia de criterio único/multicriterio ni toda la compatibilidad
ER28–Cases. Debe aprobarse su alcance, no presentarse como ER literal sin cambios.

Alternativa de contrato: autorizar UUID para decisión/opción en `paso_simulacion`
y adaptar dominio/DTO/puertos/API afectados. Cambiaría los dos tipos INTEGER del
modelo académico y los contratos públicos; tampoco está autorizado por esta fase.
No se ejecuta ninguna de las dos alternativas.

## 5. Progreso, modificación y cierre restantes

Reutilizables sin duplicar: `ServicioDecisiones`, `ServicioProgreso`,
`ServicioCierre`, `ParticipacionFacade`, `UnidadTrabajoSQLAlchemy`,
`LecturasParticipacionSQLAlchemy`, codecs de fechas y duración histórica.

Para conectarlos falta un repositorio que pueda recuperar y escribir **todos**
los pasos con sus referencias reales. No se construye una implementación parcial
de `RepositorioParticipacion` ni se sustituyen sus métodos por no-ops.

El progreso necesita además `CasesPort.obtener_recorrido` real: el total puede
depender de selecciones. No se calcula contando todas las preguntas de la versión.
Modificar una decisión que altere la ruta necesita el contrato aprobado de
conservación/invalidación de pasos posteriores; no se borra ni conserva por suposición.

La finalización del agregado requiere conservar respuestas completas y coordinar
sus locks con escritores de pasos. No se utiliza una UPDATE aislada de cabecera
para declarar demostrada la finalización transaccional con respuestas. Los cierres
SQL de las fixtures únicamente preparan estados para probar la lectura.

Contrato futuro: UoW nueva, misma Session para Identity/Scheduling/repositorio,
locks ordenados participación→intento antes de pasos, relectura de estado y
autorización, reloj inyectado, duración histórica, actualización esperada y un commit.
Ante error, rollback total; tras conflicto/deadlock reautorizar en otra transacción.
La consulta informativa de 8A/BD2-06 o de esta entrega no sustituye esa verificación.

## 6. Pruebas ejecutadas

Grupo nuevo: **42 passed, 0 skipped, 0 failed/errors**, **12,67 s**:
21 SQLite en memoria y 21 PostgreSQL 17 nuevo y desechable.

Se verifican cabecera propia, FINALIZADO/VENCIDO persistidos por fixtures, versión
posteriormente archivada, duración no alterada al reprogramar, intento ajeno o
inexistente, IDs inválidos, contexto JWT de convocatoria ausente/incorrecto,
cuenta inactiva/rol docente, convocatoria retirada, roles del llamador ignorados,
fallos del resolver y SQL sin detalles privados, falta de zona configurada y
ausencia de flush/commit/escrituras con objetos pendientes en Session.

Las pruebas usan JWT emitido/verificado por `TokensJWT` existente y repositorios/
vínculos reales de laboratorio. No son pruebas de un nuevo login HTTP o endpoint.
La ambigüedad del resolver se simula como fallo de contrato: los guards BD2-07
impiden introducir un segundo vínculo Scheduling sobre la participación histórica,
y **no** se desactivan para fabricar esa corrupción.

Suite general final ejecutada en esta entrega: **1342 passed, 38 skipped,
0 failed, 0 errors, 1 warning**, **187,63 s**. Son 42 aprobadas más que la línea
base de 1300, que también se repitió. Las omitidas no se cuentan como aprobadas:
29 requieren URL externa Identity, tres conexiones Participation están deshabilitadas
y seis requieren otra URL de persistencia. La advertencia es la deprecación
conocida Starlette/TestClient/httpx. No se cambiaron dependencias ni pruebas previas.

Comando ejecutado con las variables de aislamiento de la sección siguiente:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

No se han ejecutado nuevas pruebas de registro/modificación de decisiones,
progreso de respuestas, cierre de agregado con pasos, concurrencia de pasos o
upgrade/downgrade de una migración 8B: no existen esas implementaciones. La regresión
general repite las pruebas anteriores de Alembic, Cases, Identity, Scheduling,
8A, BD2-06 y BD2-07; no se atribuye a esta lectura esa cobertura funcional nueva.

## 7. Aislamiento y cambios

Los motores son SQLite en memoria o contenedores PostgreSQL nuevos del fixture
propietario, ID/etiqueta propios, puerto TCP efímero 127.0.0.1, datos tmpfs sin
volúmenes ajenos, base vacía inicial y readiness por conexión SQL real. Su finally
elimina exclusivamente el recurso creado. No se reutilizan bases del equipo.

Se retiran TEST_DATABASE_URL, SPS_IDENTITY_TEST_URL y SPS_PERSISTENCE_LAB_URL del
subproceso; SPS_TEST_POSTGRESQL=0 cierra conexiones externas y
SPS_TEST_IDENTITY_MAPPING_DOCKER=1 permite únicamente laboratorios nuevos.
Las fixtures ejecutan las migraciones vigentes solo allí. No se modifica `.env`.

Archivos:

- Modificado: `app/modules/participation/application/integration_ports.py`, puerto
  aditivo de lectura de cabecera.
- Nuevo: `app/modules/participation/infrastructure/attempt_state.py`.
- Nuevo: `tests/integration/test_attempt_state.py`.
- Nuevo: este informe.

No se modifica ORM, migraciones, dominio, Facade, servicios de decisiones/progreso/
cierre, UoW ni API. No se cambian los siete patrones ni políticas académicas.
RF-22, inicio y escrituras públicas siguen cerrados; no se publican notas.

Verificaciones finales: una cabeza `20261102_participation_history`, diez revisiones,
26 tablas integradas. `git diff --check` pasó con salida 0. La advertencia LF/CRLF
afecta a un archivo previo del repositorio de Cases, que no se modificó en esta fase.

La comparación SHA-256 con el inventario inicial confirma que únicamente se
modificó `integration_ports.py`, sin eliminar ningún archivo previo. Los demás
archivos de producción, modelos, revisiones y ER conservan sus bytes. Además de
los tres archivos nuevos enumerados arriba, la regresión BD2-04 produjo
`bd/laboratorio_bd2_04/evidencia_92f9b108fb47472da5f4ba27eeec4ee7.json`, sin
sobrescribir evidencias anteriores. Se conservan todos los cambios acumulados.

El inventario final de contenedores con etiqueta `sps.identity.mapping.lab=true`
está vacío. No se consultó ni modificó una base persistente; no hubo commit, push,
merge, cambio de rama ni limpieza global de Docker/Git.

## 8. Próximo paso para terminar 8B

Se solicita aprobación del contrato de identificación y correspondencia descrito
en la sección 4, antes de tocar Cases o el esquema de pasos. Después deben cerrarse
el puerto de recorrido y la política de modificación de ruta que correspondan a
Cases, y la interpretación de timestamps sin zona. Con ello se podrá implementar
modelo/migración de pasos, repositorio completo, progreso y cierre mediante los
servicios existentes, con sus pruebas PostgreSQL de integridad y concurrencia.

Consentimiento, cupos, duración autorizada y RF-22 siguen pendientes para el
**inicio productivo**, aunque pueda probarse el resto con intentos de fixtures.
No se considera terminada 8B, no se inicia 8C y no se hace commit/push/merge.

</details>

</details>
