# 8B — Grafo persistente de Cases

## Continuación: autoría HTTP protegida (3 de noviembre de 2026, Bogotá)

Worktree `C:\SPS\consolidacion`, rama `codex/consolidacion-backend`, base
`3e09defb608b3162b728f8b73b50dc772dd43693`, cambios locales sin commit.
Este apartado sustituye la limitación anterior de autoría exclusivamente interna.
Los antecedentes y sus resultados históricos se conservan abajo.

### Contrato y recorrido probado

1. `POST /api/v1/cases` conserva el DSL editorial y crea un BORRADOR.
2. `GET /api/v1/cases/{version_id}` proporciona los UUID reales de escenas,
   preguntas y opciones. No se transforman órdenes en identidades.
3. `PUT /api/v1/cases/{version_id}/graph` recibe `escenario_inicial_id` y
   `transiciones`, cada una con `opcion_id`, `tipo` (`ESCENA` o `FIN`) y
   `destino_id` (obligatorio para ESCENA y nulo para FIN).
4. `GET /api/v1/cases/{version_id}/graph` recupera la configuración propia.
5. `POST /api/v1/cases/{version_id}/publish` exige tanto la cadena editorial
   existente como un grafo ejecutable, revalidados bajo el lock de la versión.

PUT sustituye la configuración completa: las opciones omitidas quedan sin
configurar; si una es necesaria en el recorrido alcanzable, se rechaza y revierte
toda la escritura. No se mezclan silenciosamente aristas antiguas con nuevas.
La entrada debe ser única y válida. Se conservan las reglas existentes: una
pregunta por escena alcanzable, todas sus alternativas definidas, destinos de
la misma versión, FIN explícito y ausencia de ciclos alcanzables. No se inventa
navegación para varias preguntas, escenas vacías o revisitas.

El DSL editorial no cambia. Su reemplazo integral sigue rechazándose si borraría
un grafo ya configurado; se conserva la secuencia contenido → grafo → publicación.

### Seguridad y transacción

Se reutilizan JWT, cuenta activa, rol DOCENTE, permisos vigentes del repositorio
Identity y resolver persistente CASES. `CREAR_CASOS`, código ya usado por el
contrato de Identity, debe existir y estar asignado al rol; no se siembran permisos
ni se concede autoría por el simple rol. Se exige en creación, edición, escritura
de grafo, publicación y archivo. Su ausencia devuelve 403 (antes era un guard
503 pendiente). Las lecturas siguen exigiendo identidad docente y titularidad.
Las cabeceras de identidad no sustituyen esas comprobaciones.

CasoService consume un puerto mínimo de autoría implementado por CasoRepository.
Este coordina la transacción reutilizando RepositorioGrafoSQLAlchemy, sin crear
otro repositorio de grafos. Configuración y publicación bloquean la misma versión;
una configuración inválida revierte entrada y aristas. PUBLICADO/ARCHIVADO no
son editables y se conservan literalmente los guards PostgreSQL existentes.

La exigencia de ejecutabilidad es del flujo HTTP conectado. Los consumidores
editoriales internos anteriores conservan su contrato; no se añade un trigger que
obligue a tener grafo para cualquier publicación por SQL directo. Una versión sin
recorrido válido sigue siendo no ejecutable para Participation. No se modifican
tablas, ORM, migraciones, DBML, main.py, Participation ni Evaluation.

### Aceptación y regresión reales

`backend/tests/integration/test_cases_graph_authoring.py`: 20 casos nuevos con
PostgreSQL desechable, JWT y repositorios/resolver reales. Solo se siembran las
cuentas, roles, permiso y asociaciones sintéticas; el caso y todas las relaciones
del grafo se crean por API. La prueba positiva recupera el mismo grafo desde otra
Session mediante RecorridoCasesSQLAlchemy y recorre una rama hasta FIN.

También cubre acceso sin JWT/inválido/estudiante/sin permiso/sin asociación,
docente ajeno, referencias inexistentes/cruzadas, coherencia tipo/destino,
duplicados, ramas incompletas, ciclos, múltiples preguntas, rollback, publicación
sin grafo, conservación histórica y dos configuraciones HTTP concurrentes.

Las pruebas editoriales anteriores ahora configuran una escena terminal por HTTP
antes de publicar. No se desactiva la nueva validación. La prueba Identity sin
permiso específico pasa de esperar 503 a exigir 403; conserva la denegación.

- Focalizada: 265 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 79.39 s.
- General: 1834 aprobadas, 38 omitidas, 0 fallos/errores, 53 advertencias; 458.48 s.
- La general incluye las focalizadas; no se suman. Las 38 omitidas corresponden
  a conexiones externas no habilitadas; no se consideran aprobadas.
- Se usan SQLite aislado y PostgreSQL 17 desechable; no bases permanentes.
- Logs, JUnit y comandos: `C:\SPSBackups\8B-autoria-grafo-20261104T015852Z`.
- Sin cambios de fuente durante pytest. Una prueba genera su evidencia BD2-04.
- Sin laboratorios remanentes, sin commit/merge/push y referencias originales
  martin/feature y stash conservadas. Cabeza Alembic sin cambios.

RF cubiertos: RF-02, RF-05, RF-06, RF-07 y RF-09; soporte de RF-10/11 y referencias
históricas para RF-13/17. 8B sigue abierta: falta componer las operaciones de
provisión/inicio con políticas autorizadas de ingreso, consentimiento, estado y
cupos. No se registra Participation en main, no se habilitan RF-22 ni notas.

Actualización posterior: [respuestas inmutables confirmadas](FASE_8B_RESPUESTAS_INMUTABLES.md).
La modificación de respuestas dejó de ser una decisión pendiente; se prohíbe.
Los resultados y límites de este informe se conservan como evidencia de su entrega.

2026-11-02 · Rama `feature/integracion-backend`. **8B no está terminada.**

## Implementación

- Revisión `20261102_cases_graph`, dependiente de `20261102_academic_policy`:
  únicamente las tres columnas autorizadas, índice inicial único parcial,
  CHECK de transición, FK diferible al destino y tres constraint triggers
  diferidos de pertenencia. No añade tablas ni modifica revisiones anteriores.
- `escenario.es_inicial` identifica explícitamente la entrada. `ESCENA` exige
  destino; `FIN` exige destino nulo. Tipo/destino nulos significan **sin configurar**,
  nunca final implícito. Las versiones legadas no reciben aristas ni entradas.
- BD2-04 conserva íntegros sus guards: IDs/padres no se reasignan y los hijos de
  PUBLICADO/ARCHIVADO no se editan. La FK impide destinos huérfanos; los nuevos
  triggers comprueban pertenencia también al cambiar escenarios/preguntas.
- Los constraint triggers comprueban la versión afectada, no imponen condiciones
  a otra versión sin grafo. Las escrituras de grafos configurados exigen READ
  COMMITTED para no aprobar referencias desde snapshots antiguos. Se prueban
  tanto el rechazo como la conservación del comportamiento de otros borradores.
- El downgrade se permite únicamente sin entradas/aristas configuradas, para
  no perder datos. Se prueba subida, bajada y nueva subida sobre datos legados.

## Componentes conectados

| Archivo | Responsabilidad |
|---|---|
| `cases/infrastructure/models/caso.py` | Tres columnas, índice, CHECK y FK. Carga diferida sin exigir estas columnas a los lectores antiguos. |
| `cases/infrastructure/repositories/graph_repository.py` | Lee grafo exacto PUBLICADO/ARCHIVADO, o borrador explícito para autoría. Configura entrada/aristas de un BORRADOR del propietario dentro de una transacción ajena, bloqueando su versión. Valida todos los argumentos antes de escribir; no hace commit. |
| `cases/application/graph.py` | DTOs sin corrección ni puntajes, validación de ejecutabilidad y navegación por las opciones seleccionadas, nunca por orden editorial. |
| `participation/infrastructure/cases_route.py` | Implementación SQL real de `RecorridoVersionCases` en la Session de la UoW. |
| `participation/infrastructure/composition.py` | Usa ese adaptador por defecto cuando no se inyecta otro proveedor. Sin esquema/configuración/regla válida devuelve recorrido no disponible. |
| `cases/infrastructure/repositories/caso_repository.py` | Impide que el reemplazo editorial antiguo borre accidentalmente un grafo configurado. No se cambian sus DTOs ni se habilita un endpoint de autoría del grafo. |

El grafo se gestiona explícitamente en su repositorio, sin duplicarlo en las
entidades editoriales antiguas. Para un borrador configurado, el reemplazo
integral antiguo se rechaza: debe editarse el contenido antes de configurar el
grafo. No se presenta ese editor como un editor completo de grafos.

## Qué funciona sin proveedor simulado de recorrido

Una versión publicada configurada, con una pregunta por escena y sin ciclos
alcanzables, permite recuperar entrada/contexto/preguntas/alternativas, seleccionar
una rama real, identificar la escena siguiente y reconocer un `FIN` explícito.
Se validan todas las ramas alcanzables antes de habilitar la navegación. Datos
sin configurar o destinos incompatibles no autorizan avanzar.

La Facade utiliza ese recorrido, guarda respuestas en PostgreSQL, rechaza una
pregunta de la rama no elegida y recupera el progreso desde otra operación.
El adaptador no permite modificar una respuesta previa: falta esa política.
Los proveedores explícitos anteriores se conservan para sus pruebas controladas;
no se instalan como políticas productivas.

Evaluation reutiliza el mismo adaptador y recibe únicamente las preguntas de la
rama elegida. Solo un `FIN` seleccionado acredita el conjunto completo de la
ruta; mientras falta una decisión de rama, el total permanece desconocido.
Un vencimiento antes de resolver la rama no autoriza a inventar sus preguntas
futuras ni a producir una nota con todas las preguntas del caso.
Se conservan los bloqueos de mapeo de niveles/agregación/redondeo de 8C.

## Reglas pendientes y límites

- Varias preguntas en una escena: no se elige cuál provoca la salida ni se
  presupone que responder todas autoriza destinos contradictorios.
- Ciclos/revisitas: se pueden **persistir**, pero no ejecutar hasta definir
  su semántica y correspondencia con selección única por pregunta. No hay un
  CHECK que prohíba ciclos permanentemente.
- Escenas sin preguntas: no se inventa un salto automático ni un final.
- Modificación: permanece bloqueada en el proveedor real. Las protecciones
  existentes de conservación de respuestas siguen vigentes.
- Scheduling: la autorización temporal de responder/modificar e inicio todavía
  requieren políticas reales. El recorrido SQL no las sustituye. Las pruebas
  positivas de Facade usan autorización temporal explícita de laboratorio.

No se habilitan RF-22, inicio/API productivos, notas oficiales ni notificaciones.
No se cambia la fórmula académica, resultados históricos, DBML ni patrones.

## Pruebas y estado

`tests/integration/test_cases_graph.py`: **51 pruebas nuevas**;
SQLite aislado y PostgreSQL nuevo/destruible. Prueba ramas/FIN/recuperación,
configuración incompleta, SQL CHECK/FK, referencias entre versiones, inmutabilidad,
rollback, concurrencia de entrada y publicación, downgrade protegido, Facade y
evidencias evaluables con recorrido SQL real. Las garantías de triggers, locks y
migraciones se prueban en PostgreSQL, no se atribuyen a SQLite. Incluye el caso
SQL que borra un destino y reinserta el mismo UUID en otra edición: la FK por sí
sola no lo impide, pero el constraint trigger rechaza y revierte la operación.

Regresión focalizada final (grafo, cambios de ruta, Cases/Scheduling, pasos y
Evaluation): **164 aprobadas, 0 omitidas/fallos/errores, 1 advertencia conocida
de Starlette; 88,14 s**. Antes del ajuste de alcance transaccional, también pasó
una suite general con 1605 aprobadas, 38 omitidas y una advertencia (347,52 s).
Suite general final del código ajustado: **1608 aprobadas, 38 omitidas,
0 fallos, 0 errores y 1 advertencia conocida de Starlette; 354,38 s**.
Incremento de 51 aprobadas sobre las 1557 reportadas. Las omitidas son pruebas
de conexiones externas deshabilitadas (29 Identity, tres de conexión Participation
y seis de otro laboratorio por URL), no pruebas aprobadas ni laboratorios fallidos.

Se adapta el DDL SQLite vacío de `academic_identity_support.py` sin estampar una
migración PostgreSQL que no ejecutó. Las pruebas antiguas de cabeza/metadata se
actualizan al nuevo head y 43 triggers; no se eliminan pruebas negativas ni se
modifica SQL congelado de migraciones anteriores.

Archivos de pruebas anteriores adaptados exclusivamente para cabeza/DDL actual:
`identity/test_academic_identity_repository.py`,
`integration/test_cases_guard_migration.py`, `integration/test_er28_academic_base.py`,
`integration/test_participation_persistence.py`,
`integration/test_evaluation_result_storage.py` y `integration/test_schema_integration.py`.
Los ciclos históricos que apuntan a revisiones anteriores conservan sus revisiones
y recuentos correspondientes; no se exige a un esquema anterior tener el grafo.

La cadena tiene una cabeza, `20261102_cases_graph`, 14 revisiones y **30 tablas
ORM físicas**, igual cantidad que antes. El modelo conceptual oficial de 28
entidades y sus DBML no se modifican.

La suite retira URLs externas del subproceso, usa `SPS_TEST_POSTGRESQL=0` y
`SPS_TEST_IDENTITY_MAPPING_DOCKER=1`. Los contenedores son nuevos, identificados por
ID/etiqueta propios y tmpfs sin volúmenes persistentes; `finally` los elimina.
No se modifica `.env`, no se conecta una base compartida y no se realiza commit,
push, merge, cambio de rama ni fase 9.

Comprobación final: `git diff --check` termina con código 0 (aviso informativo
LF/CRLF de `caso_repository.py`); la rama permanece en
`feature/integracion-backend`. No quedan contenedores con etiqueta
`sps.identity.mapping.lab=true`. La comparación SHA-256 conserva intactos el
código y las revisiones anteriores de Evaluation, su informe y ambos DBML.
La única prueba anterior de Evaluation adaptada es la comparación del metadata
contra la cabeza actual, sin eliminar su ciclo de downgrade ni sus verificaciones.
Los cambios anteriores sin commit se conservan.

Las dos suites generales generaron automáticamente evidencias adicionales de
BD2-04: `bd/laboratorio_bd2_04/evidencia_c13c556729b846b8ac95858b1104d9cb.json`
y `bd/laboratorio_bd2_04/evidencia_fc517a1483bc439fa3749107c788dc5e.json`.
No se sobrescribieron las anteriores ni se aplicó una migración a una base persistente.
