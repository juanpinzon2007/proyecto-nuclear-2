# BD2-05 — Implementación autorizada P1–P3

Fecha: 2026-11-02. Rama: `feature/integracion-backend`.

## Alcance y resultado

Se incorpora un puente de persistencia entre la familia UUID de Cases, su clave
académica INTEGER, una versión exacta y una sesión. Se agrega únicamente la entidad
oficial `asignacion_caso`. Se conservan las tablas técnicas anteriores, UUID, ER
original, servicios, contratos HTTP, patrones y bloqueo de escrituras de Participation.
Esto **no implementa el inicio persistente de intentos**.

| Parte | Implementado | Límite |
|---|---|---|
| P1 | `caso.id_caso` INTEGER UNIQUE nullable; secuencia PostgreSQL para nuevas filas; misma fila que el UUID real | Sin backfill. Los casos anteriores siguen NULL. No se impone NOT NULL ni se desactiva BD2-04 para completar claves |
| P2 | `asignacion_caso` con grupo/caso INTEGER y sesión/versión UUID; FK compuesta, unicidad y trigger transaccional | Sin servicio público de provisión. No acredita matrícula ni titularidad por sí sola |
| P3 | Hash grupal nullable, independiente del hash individual de `convocatoria`; prueba de rechazo de código grupal/ajeno | No se define generación, prioridad o autorización mediante códigos grupales. La política sigue pendiente |

La aprobación limitada P1–P3 permite estos cambios; no se aplica P4, P5 ni P6.

## Revisión y modelos

Nueva revisión **`20261102_assignment_bridge`**, dependiente de
**`20261102_cases_history_guard`**. No modifica las revisiones anteriores.

El metadata integrado pasa de **22 a 23 tablas de negocio**; la nueva tabla está
entre las 28 oficiales. Esto no significa que el esquema físico actual sea el ER
literal de 28 tablas: conserva estructuras técnicas previas y divergencias conocidas.
`alembic_version` es una tabla técnica adicional.

- `CasoModel`: añade la clave alternativa y su índice UNIQUE. `id UUID` sigue siendo
  PK. `FetchedValue` indica que la generación depende del servidor/migración; la
  lectura diferida evita pedir la columna en operaciones históricas que no la usan.
  El repositorio actual sigue funcionando sin recibir ni inventar un INTEGER.
- `SesionProgramadaModel`: índice UNIQUE sobre `(id, version_caso_id)`, necesario
  para que PostgreSQL acepte la referencia compuesta. No se cambian atributos ni PK.
- `AsignacionCasoModel`: conserva los once atributos originales de la asignación y
  agrega las dos referencias UUID autorizadas. No duplica `sesion_programada`:
  ésta programa espacio/versión; la asignación vincula explícitamente grupo/caso.
- `registrar_modelos_integrados`: importa el nuevo modelo y valida todas sus FK.

SQLite conserva el DDL de referencia para regresión. **No genera claves académicas
automáticamente ni implementa los triggers PostgreSQL**. La migración Alembic es la
fuente del generador PostgreSQL; `Base.metadata.create_all()` no lo sustituye.

## Cambios exactos respecto del ER académico

| Objeto | Diferencia documentada |
|---|---|
| `caso` | `id_caso` es clave alternativa UNIQUE y temporalmente nullable, en vez de sustituir la PK UUID por la PK INTEGER del ER |
| `asignacion_caso` | `sesion_programada_id UUID NOT NULL` y `version_caso_id UUID NOT NULL` adicionales |
| `asignacion_caso.codigo_acceso_hash` | Admite NULL; no se inventa ni copia un código individual al grupo |
| Relaciones de asignación | UNIQUE(sesión, grupo), FK compuesta sesión–versión y comprobación de familia/publicación/rúbrica mediante trigger |
| `sesion_programada` | Índice UNIQUE adicional sobre sus identificadores existentes; no agrega columnas |

Se conservan fechas de asignación sin zona horaria como en el ER, y las fechas
actuales de Scheduling con zona. No se introduce una conversión implícita ni se
declara una zona académica oficial. No se sincronizan horarios/cupos entre ambas
tablas ni se inventan reglas temporales para llenar sus campos. Los valores de las
pruebas son sintéticos, no una aprobación de RF-22.

## Integridad implementada

PK: `asignacion_caso.id_asignacion INTEGER` autogenerada.

FK de asignación:

1. `id_grupo → grupo_academico.id_grupo`.
2. `id_caso → caso.id_caso` (índice UNIQUE alternativo).
3. `version_caso_id → version_caso.id`.
4. `(sesion_programada_id, version_caso_id) → sesion_programada(id, version_caso_id)`.

UNIQUE: `caso.id_caso`, `sesion_programada(id, version_caso_id)` y
`asignacion_caso(sesion_programada_id, id_grupo)`. Una sesión puede tener varios
grupos explícitos; no se deduce grupo de espacio ni de docente UUID.

La nueva función/trigger **`bd205_asignacion`**:

- En INSERT resuelve el INTEGER en la misma fila del caso UUID, bloquea la versión
  con `FOR UPDATE` y exige familia coincidente, estado PUBLICADO y rúbrica propia.
- En UPDATE impide cambiar PK, grupo, caso, sesión o versión de una asignación.
- No regula campos académicos restantes ni habilita escritores/HTTP nuevos.
- Se ejecuta como invocador, con `search_path` acotado y referencias `public`
  explícitas. No concede privilegios ni usa `SECURITY DEFINER`.

La FK compuesta impide cambiar por SQL la versión de **sesiones ya enlazadas**.
No protege la reasignación de sesiones que todavía no tengan asignación. El bloqueo
de la versión coordina el alta con publicación/archivo y las guardas BD2-04; las
FK resuelven las carreras con cambios/borrado de sesión. Se prueba concurrencia
real con dos conexiones y límites de espera, no solo mocks.

La rúbrica exacta se conserva por la versión UUID: es única por versión y queda
inmutable con su `version_regla`, criterios y niveles bajo BD2-04. No se busca «la
última versión». Se mantienen **las seis funciones y 18 triggers anteriores** y se
agregan una función y un trigger de asignación (19 triggers en total).

Esto protege escritores ordinarios bajo triggers/FK; no pretende impedir que un
propietario/superusuario desactive guardas o altere el esquema. No hay aún FK desde
participaciones: la preservación de ese historial requiere P4 y siguientes.

## Upgrade, legado y reversión

El upgrade añade `id_caso` primero sin DEFAULT y después instala la secuencia y
su DEFAULT: los casos anteriores conservan NULL, UUID, contenido y relaciones.
Los casos nuevos obtienen un INTEGER independiente, estable y único. La secuencia
puede dejar huecos tras rollback; no es numeración académica consecutiva.
La unicidad rechaza colisiones incluso si un escritor SQL suministra una clave.
No se admiten asociaciones a un caso legado sin clave. Su conciliación requiere
otro procedimiento autorizado compatible con el bloqueo histórico de `caso`.

El downgrade PostgreSQL bloquea `caso` y `asignacion_caso` antes de comprobar datos.
**Se rechaza si existe cualquier asignación o cualquier clave académica no NULL**.
No borra esas filas ni sus identificadores. Sobre estado vacío/legado NULL elimina
solo tabla vacía, función/trigger e índices propios, secuencia/default y columna
nueva NULL. No desinstala las protecciones BD2-04. Pruebas verifican ambos caminos.
La reversión requiere una ventana sin escritores: sus bloqueos pueden esperar o
provocar un deadlock detectado por PostgreSQL ante transacciones competidoras.
En ese caso se revierte la transacción; no se evita el bloqueo borrando referencias.

## Pruebas y aislamiento

Se usa `motor_postgresql_desechable`: crea un contenedor nuevo con imagen local
PostgreSQL 17, etiqueta `sps.identity.mapping.lab=true`, nombre aleatorio, ID completo,
datos en tmpfs y puerto efímero ligado únicamente a 127.0.0.1. Verifica ausencia de
volúmenes/binds persistentes, base inicialmente vacía y `SELECT current_database()`
por TCP real antes de ejecutar migraciones. El `finally` elimina únicamente el ID
propio verificado. No se utilizan contenedores existentes, `.env` ni bases del equipo.

En el proceso de pruebas se retiran `TEST_DATABASE_URL`, `SPS_IDENTITY_TEST_URL` y
`SPS_PERSISTENCE_LAB_URL`; se fija `SPS_TEST_POSTGRESQL=0` y se habilita únicamente
el laboratorio nuevo con `SPS_TEST_IDENTITY_MAPPING_DOCKER=1`. La prueba HTTP
PostgreSQL anidada crea su propia base dentro del contenedor nuevo y pasa esa URL
solo al subproceso. Las demás pruebas HTTP usan TestClient en memoria; no prueban
un despliegue HTTP productivo.

Resultados de esta entrega:

- Prevalidación sin Docker de las regresiones adaptadas: **57 passed, 43 skipped,
  0 failed/errors, 1 warning**, 6,82 s. Los skipped no se cuentan como aprobados.
- Primer desarrollo del nuevo grupo: 25 passed y 2 failed en preparación de fixtures
  (valoraciones huérfanas al retirar una rúbrica; referencia ORM transitoria).
  Se corrigieron las fixtures sin debilitar restricciones ni omitir pruebas.
- Regresión específica ampliada con PostgreSQL: **248 passed, 0 skipped,
  0 failed/errors, 1 warning**, 80,81 s. Incluye 27 pruebas iniciales del puente,
  migraciones, Identity, BD2-01, BD2-04, Cases histórico y Participation 8A.
- Grupo final del puente: **29 passed, 0 skipped, 0 failed/errors**, 13,73 s,
  ejecución independiente posterior. De ellas 28 usan PostgreSQL real y una SQLite.
- Suite general final: **1190 passed, 38 skipped, 0 failed, 0 errors,
  1 warning**, 132,28 s. Son 29 aprobadas más que la línea base histórica de 1161.
  Las 38 omitidas corresponden a 29 pruebas Identity con URL externa ausente,
  tres conexiones Participation deshabilitadas y seis pruebas de persistencia con
  URL externa ausente. No se cuentan como aprobadas ni se habilitan contra bases
  del equipo. La advertencia es la deprecación conocida Starlette/TestClient/httpx;
  no se instalaron ni cambiaron dependencias.

Comando ejecutado, usando el entorno aislado descrito arriba:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Verificación estática final: una cabeza `20261102_assignment_bridge`, padre
`20261102_cases_history_guard`, nueve revisiones y 23 tablas en metadata.
`git diff --check`: código de salida 0, sin errores de espacios. Git advierte sobre
la futura normalización LF/CRLF de un repositorio de Cases ya modificado en una
fase anterior; ese archivo no se cambió en esta entrega.
El inventario final de contenedores con la etiqueta del laboratorio está vacío.

El grupo nuevo verifica claves generadas/únicas, conservación del UUID, legado sin
backfill, PK/FK/NULL, familia ajena, sesión de otra versión, borrador/archivo/falta
de rúbrica, referencia histórica tras segunda publicación, contexto inmutable,
colisiones concurrentes, carrera de reasignación de sesión, rollback, downgrade
seguro y separación código grupal/individual con repositorios/resolver reales.

## Compatibilidad, pendientes y archivos

No cambian endpoints, autenticación, roles, resolver de usuarios ni servicios de
Cases/Scheduling. 8A conserva titularidad, contexto de convocatoria, código
individual, consulta inyectable de versión exacta y bloqueo por RF-22. No se conecta
el nuevo modelo a una ruta que conceda ingreso o cree participaciones.

Pendientes: conciliación acreditada de claves legadas; provisión autorizada de
asignaciones y grupos; matrícula/usuario/convocatoria coherentes en una transacción;
consentimiento; cupos adicionales; duración histórica y concurrencia de intentos;
P4–P6; semántica de códigos grupales y política temporal aprobada. La FK de grupo
solo acredita existencia, no autorización docente o estudiantil. No se publican notas.

Archivos productivos modificados:

- `backend/app/modules/cases/infrastructure/models/caso.py`: clave alternativa.
- `backend/app/modules/scheduling/infrastructure/models.py`: índice sesión–versión.
- `backend/app/db/models.py`: registro del modelo oficial de asignación.

Archivos nuevos:

- `backend/app/modules/scheduling/infrastructure/assignment_models.py`.
- `backend/alembic/versions/20261102_assignment_bridge.py`.
- `backend/tests/integration/test_assignment_bridge.py`.
- Este informe.

Regresiones adaptadas: `test_schema_integration.py`, `test_er28_academic_base.py`,
`test_cases_guard_migration.py` y `identity/test_academic_identity_repository.py`.
Actualizan cabeza/metadata; conservan revisiones históricas y pruebas de datos.
La fixture del ciclo anterior representa expresamente un caso legado con clave
NULL: las nuevas pruebas demuestran que una clave ya creada impide downgrade.
Los JSON nuevos del laboratorio BD2-04 son evidencias generadas al ejecutar su
regresión; no cambian su SQL autorizado ni sobrescriben resultados históricos.

No se aplicó ninguna migración a bases persistentes. No se hicieron commit, push,
merge, cambio de rama ni operaciones destructivas de Git. No se inicia BD2-06.

Estado de trabajo: permanecen los cambios acumulados sin commit. La comparación
SHA-256 con la captura inicial confirma que solo cambiaron los siete archivos
previos enumerados arriba (tres productivos y cuatro de pruebas), sin eliminar
ninguno. Los demás archivos previos, incluidos ER, revisiones y SQL BD2-04,
Participation 8A y patrones, conservan sus bytes. El diff global de Git incluye
fases anteriores; no debe atribuirse íntegramente a P1–P3.

El siguiente incremento requerirá autorizar y concretar participación–convocatoria–
matrícula y su transacción de ingreso; este puente no resuelve esa autorización ni
el consentimiento, duración histórica, intentos adicionales o RF-22.
