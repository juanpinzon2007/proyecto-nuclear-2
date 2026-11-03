# BD2-03B — Protección del versionamiento existente

2026-11-02 · Rama `feature/integracion-backend`.

Se conserva `caso` / `version_caso`. No se implementa A1–A3 del ER alternativo.
Los cambios son guardas del repositorio y relectura bloqueada al programar una
sesión. **No equivalen a inmutabilidad garantizada por el esquema PostgreSQL.**

## 1. Caminos de escritura revisados

| Camino actual | Control existente | Riesgo / resultado de la revisión |
|---|---|---|
| POST cases → crear_borrador → guardar | Identity/resolver, permiso de creación 503 en producción; Builder crea BORRADOR; inserción con PK/UNIQUE y rollback | Inserta agregado nuevo, no upsert sobre versión anterior. No se habilitó creación ni se implementó endpoint de nueva edición |
| PUT cases/{version_id} → actualizar → reemplazar | Versión del docente, asegurar_editable antes de construir; conserva caso_id/id/número | Antes de este ajuste el repositorio no verificaba de nuevo el estado. Una lectura BORRADOR obsoleta podía reemplazar contenido ya PUBLICADO |
| publish → publicar → actualizar_estado | CoR valida estructura, respuestas, rúbrica y todas las valoraciones; solo BORRADOR | Existía ventana entre lectura/validación y escritura: un editor podía cambiar el contenido validado. El repositorio asignaba el estado solicitado sin revalidar |
| archive → archivar → actualizar_estado | Solo PUBLICADO→ARCHIVADO | Persistencia anterior no rechazaba por sí misma la reversión o identidad manipulada desde un llamador interno |
| Escenarios/preguntas/opciones/rúbricas | No hay endpoints individuales de modificación; reemplazo del agregado borra/recrea solo su estructura | Se protegen por la guarda de su raíz en reemplazar. No se modifica Builder ni se inventan nuevos contratos de edición |
| Programar sesión | UUID exacto, existencia de versión, PUBLICADO y duración compatible con estimado | Session.get podía devolver versión previamente cargada obsoleta; no coordinaba bloqueo con archivo |
| Cambiar estado de sesión | State y auditoría existentes, bloqueo de sesión | No reasigna version_caso_id; no se modificó |
| Acceso ORM directo, Core UPDATE/DELETE o SQL | FK/UNIQUE originales | No impide cambiar contenido publicado ni enlazar una valoración a criterio de otra versión; sigue siendo bloqueo de esquema |

Fuentes: [CasoService](../../app/modules/cases/application/services/caso_service.py),
[router](../../app/modules/cases/api/router.py), [repositorio](../../app/modules/cases/infrastructure/repositories/caso_repository.py),
[programar_sesion](../../app/modules/scheduling/application/programar_sesion.py).
Los defectos previos del repositorio se identificaron por lectura de sus métodos;
no se ejecutó una explotación contra bases existentes ni se afirma que un atacante
sin autenticación tuviera acceso a esas operaciones internas.

## 2. Protecciones implementadas

### Repositorio de Cases

- `reemplazar` y `actualizar_estado` bloquean la fila exacta de versión con
  SELECT FOR UPDATE, releen el grafo y usan populate_existing para no confiar
  en objetos antiguos del identity map. Todos los escritores de estos métodos
  serializan sobre la misma raíz hasta commit/rollback.
- Se comprueban caso_id, número y creador contra lo persistido. No se permite
  usar una versión existente como vehículo para cambiar familia/propietario.
- `reemplazar` exige BORRADOR tanto en la versión persistida como en la recibida,
  antes de borrar escenarios/rúbrica. PUBLICADO/ARCHIVADO rechazan con el error
  de dominio existente y revierten la transacción.
- `actualizar_estado` compara todo el contenido leído con el solicitado, salvo
  estado. Incluye IDs, escenarios, preguntas, textos, opciones, valoraciones,
  rúbrica, regla, criterios, pesos, niveles y descriptores. Normaliza orden físico
  de colecciones sin perder sus campos `orden`. Cambio concurrente implica
  ErrorPersistenciaCaso y rollback; no publica contenido diferente del leído.
- Publicar reejecuta **la cadena y método de dominio existentes** sobre el grafo
  fresco/bloqueado. La validación previa del servicio se conserva como respuesta
  temprana; esta segunda comprobación protege el límite de persistencia. Archivar
  reutiliza `VersionCaso.archivar`; no admite asignar arbitrariamente BORRADOR.
- No hay autoflush antes de las guardas; commit/flush explícito y rollback
  continúan en la transacción original del repositorio. No hay nueva política
  académica ni tabla/columna de revisión optimista.

### Scheduling

`programar_sesion` conserva Session.get pero incorpora populate_existing y
with_for_update para la versión exacta indicada. Usa la misma fila raíz que el
repositorio; no acepta un estado PUBLICADO antiguo retenido en memoria. El
llamador mantiene la responsabilidad de commit/rollback; función/firma, fechas,
duración, UUID asignado y estado inicial no cambiaron.

La serialización garantiza el orden de estas operaciones **si todos los
escritores usan estas rutas**. En SQLite SELECT FOR UPDATE no proporciona la
garantía concurrente; la prueba de bloqueo se ejecuta en PostgreSQL real desechable.

Estas guardas no son una unidad de trabajo que inspeccione cualquier cambio
pendiente de una Session compartida. Un llamador que añada cambios ORM directos
fuera del agregado y después haga commit también elude el límite revisado; el
contrato operativo debe mantener las escrituras por sus rutas autorizadas. No
se declara protección global mediante no_autoflush ni mediante el bloqueo raíz.

## 3. Integridad de opciones, criterios y resultados

Builder resuelve criterios por nombre dentro de su rúbrica; la Chain exige una
valoración por cada criterio propio y rechaza criterios ajenos. Los borradores
pueden seguir incompletos. La persistencia no convierte una incompletitud de
borrador en una versión publicable; ahora revalida esa condición al publicar.

La base tiene FK de valoración a opción y a criterio por separado; **no una
restricción de misma versión**. Se demostró en un laboratorio del esquema actual:
un UPDATE de valoración hacia un criterio existente de otra versión se acepta,
igual que un UPDATE del nombre de una versión PUBLICADO. Ambos se revirtieron.
La prueba `test_esquema_actual_no_es_barrera_ante_SQL_directo` documenta esa
limitación; su aprobación no significa que se haya cerrado el defecto de esquema.

Cambiar textos, justificación, corrección, valores, regla o rúbrica publicados
alteraría la interpretación de respuestas anteriores aunque una nota almacenada
siguiera igual. Las nuevas guardas evitan esos reemplazos por el repositorio, pero
no certifican reproducibilidad académica completa: siguen pendientes políticas,
marco histórico y persistencia de resultados donde aún no estén integrados.

## 4. Garantías de aplicación frente a base de datos

| Garantía | Aplicación después del ajuste | Base de datos actual |
|---|---|---|
| Editar solo BORRADOR | Servicio + relectura/guardas de repositorio | No existe barrera contra UPDATE directo de PUBLICADO |
| Transiciones/publicación coherentes | Dominio/Chain reutilizados en servicio y límite de escritura | Estado admitido por tipo no impone irreversibilidad histórica |
| Validación sobre contenido actual | Comparación estructural, refresh y bloqueo raíz | No hay columna de revisión ni trigger global |
| Bloqueo concurrente de escritores del repositorio | Comprobado en PostgreSQL | FOR UPDATE real, pero solo participa quien toma ese bloqueo |
| Programación de versión publicada exacta | UUID explícito y relectura bloqueada; sin selección de última versión | FK a version_caso.id; no impide UPDATE posterior de referencia a otra existente |
| Identidad de versión, familia y dueño en escritores revisados | Comparación antes de persistir | FK no demuestra autorización del actor ni congela el creador |
| Opción y criterio de la misma edición | Builder/Chain y validación antes de publicar | FK individuales no garantizan misma edición |
| Ausencia de huérfanos / duplicados | Manejo de error y rollback existentes | FK y UNIQUE originales continúan protegiendo referencias y claves |

Para una garantía contra cualquier escritor SQL se necesitan cambios de esquema
expresamente aprobados: triggers de inmutabilidad/identidad sobre raíz e hijos,
guardas de reasignación de sesiones, y restricción transaccional o estructura
relacional para pertenencia de valoraciones a una edición. Ninguno se implementó.
No basta un trigger en version_caso si permite mutar sus opciones/criterios.
Privilegios mínimos y rutas únicas de escritura son complementos, no sustitutos
de esas restricciones. No se modificó ninguna base/rol de PostgreSQL del equipo.

## 5. Pruebas y alcance de los dobles

Archivo nuevo: [test_cases_history.py](../../tests/integration/test_cases_history.py).
Usa exclusivamente el fixture existente de PostgreSQL nuevo/destruible, sin URL
del equipo. Aplica la cadena Alembic existente solo al laboratorio, sin crear
entidades nuevas ni revisiones. Los 15 casos nuevos cubren:

- Rechazo de edición de PUBLICADO/ARCHIVADO aunque se presente como BORRADOR.
- Rechazo de caso_id, número o creador manipulados.
- Edición legítima de borrador, publicación y archivo con grafo íntegro; sin reversión.
- Publicación obsoleta tras cambios de enunciado, puntaje, descriptor o regla,
  incluyendo un identity map previamente cargado.
- Revalidación de cadena: versión sin rúbrica y valoración de criterio ajeno.
- Dos conexiones concurrentes: el editor espera un bloqueo PostgreSQL observado
  mediante pg_blocking_pids; después de publicar, el editor recibe rechazo.
- Scheduling rechaza una versión archivada por otra conexión aun si estaba
  cargada previamente en su Session.
- Prueba diagnóstica del bypass SQL y rollback, sin presentarlo como protección.

Las pruebas HTTP existentes de Cases usan TestClient/ASGI, JWT y repositorios SQL
de SQLite aislado; sus cuentas/permisos académicos son fixtures y la creación
continúa bloqueada en producción. El unit test de Scheduling usa Mock y se ajustó
solo para aceptar/verificar los argumentos nuevos del get. No se debilitaron sus
expectativas de autorización/estado. 8A se conserva sin cambios y se ejecuta en
la regresión general con sus laboratorios propios.

La primera corrida específica dio 46 aprobadas y 1 fallida: el nuevo fixture de
«sin rúbrica» dejaba valoraciones con FK al criterio eliminado, y fallaba antes de
la publicación que se quería comprobar. Se corrigió el fixture retirando también
esas valoraciones, sin quitar la prueba ni relajar FK. Se ampliaron después los
casos de snapshot obsoleto a cuatro campos.

Corrida específica final: **50 passed, 0 skipped, 0 failed, 0 errors, 1 warning**,
9.95 segundos. Comando: pytest sobre `backend/tests/integration/test_cases_history.py`,
`backend/tests/integration/cases` y `backend/tests/unit/scheduling/test_programar_sesion.py`,
con `-c backend/pyproject.toml -q -rs --tb=short`.

Suite general ejecutada con `python -B -m pytest -c backend/pyproject.toml
backend/tests backend/app/modules/participation/tests -q -rs --tb=short`:
**1157 passed, 38 skipped, 0 failed, 0 errors, 1 warning**, en 120.05 segundos.
Son 15 aprobaciones nuevas respecto a 1142; las 38 omitidas no se atribuyen como
aprobadas (29 de Identity sin URL independiente, 3 de conexión Participation
deshabilitadas y 6 de su laboratorio sin URL). Advertencia conocida:
StarletteDeprecationWarning sobre httpx/TestClient.

El proceso de pruebas retira TEST_DATABASE_URL, SPS_IDENTITY_TEST_URL y
SPS_PERSISTENCE_LAB_URL heredadas; fija SPS_TEST_POSTGRESQL=0 y
SPS_TEST_IDENTITY_MAPPING_DOCKER=1 solo en el hijo. Las demás pruebas SQL usan
SQLite aislado o los laboratorios opt-in nuevos. `.env` no cambia ni se emplea
su conexión para probar bases persistentes. No se instalan dependencias.

## 6. Impacto en Scheduling, 8A y contratos

No se añadió un endpoint para reasignar versiones. No hay consultas que elijan
la última edición como sustitución. `consultar_version_publicada` conserva UUID
exacto, rúbrica de esa versión y version_regla; la inyección y el DTO 8A no cambian.
Se mantienen autenticación, titularidad, RF-22 y fachada cerrada para intentos.

Archivar una versión sigue impidiendo nuevas programaciones. La consulta actual
de ingreso 8A exige PUBLICADO y rechaza ARCHIVADO: **no se modificó esa política**
para abrir sesiones históricas. Si se necesita otro comportamiento para sesiones
ya convocadas, debe aprobarse por separado. Lectura de resultados históricos y
permiso de nuevo ingreso no son el mismo contrato.

Las excepciones y traducciones HTTP existentes se conservan; un conflicto de
snapshot usa ErrorPersistenciaCaso (HTTP genérico existente), no se introduce un
409 público unilateralmente. No se alteran Builder, Chain, Proxy, Facade, Strategy,
State ni Observer; se reutilizan las reglas actuales.

Archivos intervenidos: repositorio de Cases, programar_sesion, su unit test,
archivo nuevo de pruebas PostgreSQL y este informe. No se cambian ORM, migraciones,
DBML, modelos de dominio, endpoints, contratos de repositorio ni 8A. No se inicia
BD2-04 ni se autorizan modificaciones de esquema futuras.

Cierre: la comparación de hashes con el inicio identifica solo tres archivos
preexistentes modificados y dos nuevos, los cinco enumerados arriba; todos los
demás cambios locales previos se conservan. Sin cambios a ORM, migraciones o 8A.
Análisis sintáctico, enlaces locales y `git diff --check` correctos. No quedaron
contenedores con la etiqueta del laboratorio al finalizar las pruebas. Se mantiene
la rama y no hubo commits, pushes o merges.
