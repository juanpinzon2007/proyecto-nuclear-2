# BD2-04 — Integración autorizada de las guardas históricas

2026-11-02 · `feature/integracion-backend` · Aplicación exclusiva en laboratorios.

## 1. Revisión incorporada

- Archivo: [20261102_cases_history_guard.py](../../alembic/versions/20261102_cases_history_guard.py).
- Revisión: `20261102_cases_history_guard`.
- Padre: `20261101_er28_base_academica`, verificado como única cabeza antes de escribir.
- Estado estático posterior: una cabeza nueva, ocho revisiones, 22 tablas ORM.
- Ninguna tabla, columna, PK/FK/UQ/índice, UUID o dato histórico se modifica.
- SQL de upgrade/downgrade copiado literalmente en la revisión; no se lee docs
  durante una migración. La prueba compara ambos literales con el SQL autorizado.

SHA256 de los textos SQL, iguales al experimento autorizado:

```text
upgrade   99b9ed5ad4ff70cbcf57e3c03b65906166cd68cb02af9448dc79e857f41d1ece
downgrade 86d6959fb813532a88b15fbfb57b3b6c4c5886fd9a71646c19410e139902be91
```

PostgreSQL instala las guardas. SQLite avanza el historial sin simular triggers
PostgreSQL; sus pruebas verifican únicamente aplicación/esquema portable. Otro
dialecto se rechaza explícitamente. No se modificó ORM ni se habilitó un bypass.

## 2. Funciones, triggers e integridad

Se integran exactamente seis funciones SECURITY INVOKER, con search_path fijo y
tablas public.*: `bd204_version`, `bd204_borrador`, `bd204_guardar_hijo`,
`bd204_guardar_version`, `bd204_guardar_caso` y `bd204_no_truncar`.

En nueve tablas se instala un trigger por fila y otro BEFORE TRUNCATE: caso,
version_caso, escenario, pregunta, opcion_respuesta, rubrica, criterio_rubrica,
nivel_rubrica y valoracion_opcion. Son **18 triggers**, sin otros objetos añadidos.
Nombres y definición completos: [especificación histórica aprobada](laboratorio_bd2_04/ESPECIFICACION_MIGRACION.md)
y SQL congelado en la revisión.

Se protege contenido PUBLICADO/ARCHIVADO y su grafo contra INSERT/UPDATE/DELETE;
no se permite volver a BORRADOR ni borrar historia. Identidades/padres permanecen
estables y se exige misma versión para opción/criterio. Los borradores conservan
edición mediante DELETE/INSERT del escritor actual y publicación/archivo legítimos.
Crear directamente PUBLICADO o hacer TRUNCATE queda prohibido, conforme a lo autorizado.

El upgrade toma SHARE ROW EXCLUSIVE en las nueve tablas y audita estados, FK
validadas y valoraciones existentes antes de instalar. Datos incoherentes abortan
sin reparación, funciones parciales ni avance del head. El downgrade retira solo
sus 18 triggers y seis funciones en transacción, sin DROP CASCADE ni DML de datos.
Se verifican upgrade, downgrade y reupgrade reales con filas/catálogo conservados.

## 3. Adaptaciones de pruebas, sin cambiar los triggers

Los fixtures de login/Identity/Scheduling/8A que insertaban PUBLICADO antes de
cargar su contenido ahora crean BORRADOR, cargan los hijos y finalmente publican.
No se desactiva ningún trigger ni se usa variable de sesión para saltarlo.

Los negativos 8A de versión borrador/sin rúbrica se preparan como nuevas versiones
sintéticas de ese escenario, en vez de corromper una versión publicada existente.
El caso sin rúbrica representa deliberadamente un dato académico incompleto para
comprobar que el lector lo rechaza; no se lo declara publicación válida por Chain.
La unicidad de rúbrica se comprueba en borrador (SQLSTATE 23505); reparentado de
rúbrica histórica se rechaza por trigger (23514), manteniendo FK originales en
las otras referencias inexistentes (23503). No se debilitan las verificaciones.

Cases/Scheduling HTTP sobre PG usan una transacción externa por prueba, con
savepoints de Session, y rollback al terminar. Los commits de aplicación se
ejercitan dentro de esos savepoints; no se usa DELETE/TRUNCATE de historia como
limpieza. SQLite aislado conserva la estrategia previa porque no instala guardas PG.

La regresión de BD2-03B cambia sus expectativas con la nueva capacidad real:
valorar un criterio ajeno se rechaza ya al persistir el borrador y SQL directo
contra publicado se rechaza por 23514. Se comprueba también rollback/grafo intacto.
Los tests de cadena Alembic conservan la revisión ER28 como padre histórico y
comprueban la nueva cabeza, sin eliminar las verificaciones de los merges anteriores.

No se encontró incompatibilidad del SQL con los escritores productivos probados.
No se modificó su comportamiento, servicios, endpoints o implementación 8A.

## 4. Pruebas ejecutadas y evidencias

Archivo nuevo: [test_cases_guard_migration.py](../../tests/integration/test_cases_guard_migration.py).
Sus cuatro pruebas comprueban copia literal/cadena, dialecto SQLite, regresión
PostgreSQL de revisión real y HTTP de Cases/Scheduling en PostgreSQL migrado.

El laboratorio reutiliza las 109 comprobaciones y agrega cuatro de revisión real:
head tras upgrade, head tras downgrade, reupgrade con mismo catálogo y filas
conservadas. Son **113 comprobaciones internas**, dentro de una prueba pytest;
no se suman como 113 casos adicionales al conteo de suite.

- Específicas: **147 passed, 0 failed, 0 errors, 1 warning**, en 58.50 s.
  Selección: migración nueva, historia Cases, 8A e Identity HTTP/SQL.
- Verificación adicional de SQLSTATE en 8A: **8 passed, 98 deselected, 1 warning**,
  en 10.02 s. Deseleccionadas por filtro explícito, no omitidas por fallo.
- Primera suite general: **1160 passed, 38 skipped, 1 failed, 0 errors, 1 warning**,
  en 150.80 s. El fixture de `test_migracion_aditiva_ciclo_y_datos_previos` aún
  insertaba PUBLICADO directamente; el rechazo fue correcto. Se adaptó a
  BORRADOR→PUBLICADO sin cambiar SQL ni la prueba de preservación de datos.
- Grupo del fixture corregido: **33 passed, 0 failed, 0 errors, 1 warning**, en 6.08 s.

Evidencias de revisión Alembic real con 113 comprobaciones y limpieza verificadas:
[618c730d](laboratorio_bd2_04/evidencia_618c730daa674063ba801fce1e0ec86e.json),
[9ec7a685](laboratorio_bd2_04/evidencia_9ec7a68555da4b22904bd44ff1804c0d.json).
La evidencia de la repetición final es
[7fe865e7](laboratorio_bd2_04/evidencia_7fe865e7252441f19da2d9af48b5c4cc.json):
113 comprobaciones satisfechas, revisión real y limpieza verificada.

Tras quitar una línea vacía final del archivo de revisión (sin cambiar SQL ni
lógica), se repitieron copia literal y ciclo real de migración: **2 passed,
2 deselected**, en 9.48 s. La evidencia
[8fb271b0](laboratorio_bd2_04/evidencia_8fb271b0130141afaa3cf4acc788fd31.json)
contiene 113 comprobaciones y hashes que coinciden con los artefactos finales;
las anteriores conservan los hashes de cada ejecución original.

**Suite general final: 1161 passed, 38 skipped, 0 failed, 0 errors, 1 warning**, en
148.98 s. Son cuatro pruebas pytest nuevas frente a 1157, no 113 añadidas al
conteo. Las 38 omitidas son 29 de persistencia Identity sin URL independiente,
3 de conexión Participation deshabilitadas y 6 de su laboratorio sin URL; no se
declaran aprobadas ni verificadas por las otras pruebas PostgreSQL.

Comando de suite, ejecutado en proceso hijo con el entorno seguro descrito:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Advertencia conocida: StarletteDeprecationWarning sobre httpx/TestClient.
No se instalaron dependencias para ocultarla. Las omitidas no se cuentan aprobadas.

## 5. Aislamiento PostgreSQL y alcance de la regresión

Las pruebas eliminan URLs externas heredadas de su proceso hijo y fijan
SPS_TEST_POSTGRESQL=0; solo activan SPS_TEST_IDENTITY_MAPPING_DOCKER=1, que crea
contenedor nuevo por módulo. El helper comprueba ID/nombre/etiqueta propios,
tmpfs, ausencia de volúmenes/binds persistentes, puerto efímero 127.0.0.1, conexión
TCP a la base esperada y esquema vacío. Las evidencias agregan montaje real tmpfs.

Para HTTP real de integración, la prueba crea además `sps_test` **dentro de su
contenedor nuevo**, desde su engine verificado. Comprueba que está vacía, aplica
el head y constata los 18 triggers antes de lanzar Cases/Scheduling en un proceso
pytest separado. La URL se construye de ese engine, nunca de `.env` o del usuario;
la contraseña queda solo en memoria/entorno hijo y se redacta en diagnósticos.

Los tests de HTTP son TestClient/ASGI, no un servidor público. Conservan los
fixtures explícitos de JWT/identidad/permisos; no se habilitan esos permisos en
producción. Los escritores SQL son los reales. 8A y login se ejecutan en sus
laboratorios SQLite/PG; fórmula, RF-22 e inicio de intentos permanecen cerrados.

Solo se aplica Alembic a esas bases nuevas y SQLite en memoria. Los finally del
helper retiran exclusivamente sus IDs; los JSON comprueban su ausencia posterior.
No hubo Compose, contenedores/volúmenes ajenos, limpieza global ni conexión a bases
persistentes. La tabla alembic_version es la técnica preexistente: no se añade
ninguna entidad a las 22 ORM actuales ni se modifica el ER oficial de 28.

## 6. Bloqueos, permisos y límites restantes

- Hijos y publicación serializan sobre la raíz. READ COMMITTED espera y rechaza
  edición posterior a publicación; REPEATABLE READ puede producir 40001. El orden
  inverso confirma una edición anterior antes de congelar. Se observa bloqueo
  real con pg_blocking_pids; no se simula con mocks.
- Las transacciones multirraíz pueden producir deadlock 40P01; requieren rollback
  y reintento del caso completo. No se añadió retry automático ni se promete
  ausencia universal de deadlocks. El orden de locks del SQL aprobado no cambió.
- Se ensayó un rol no propietario que no puede desactivar triggers ni usar
  session_replication_role. No se asegura esa condición para usuarios reales del
  equipo: antes de desplegar debe verificarse separación migrador/aplicación.
  Propietario/superusuario puede retirar la barrera. No se cambiaron roles persistentes.
- **La reasignación SQL directa de sesion_programada.version_caso_id no queda
  protegida por esta revisión.** La FK sigue aceptando otra versión existente.
  Los escritores probados conservan su referencia; otra guarda necesita otro alcance.
- Los triggers no autentican JWT ni replican toda la validación académica de la
  Chain; no aprueban notas, políticas o publicación de datos incompletos por la API.
- La protección comienza al instalar: no recupera historia ya corrompida. Preflight
  se detiene ante inconsistencias; no las corrige. Downgrade reabre los bypass,
  aunque conserve filas; no es una operación productiva automática.

## 7. Archivos y estado de entrega

Único cambio de ejecución productiva: nueva revisión Alembic. Ningún cambio de
ORM, servicios, endpoints, DBML, identificadores, arquitectura/patrones o 8A productivo.

Pruebas/fixtures adaptados:

- `tests/identity/test_student_login_scheduling.py`, `test_academic_identity_http_sql.py`
  y `test_academic_identity_repository.py`: secuencia de preparación y nueva cabeza.
- `tests/integration/test_participation_8a.py`: datos iniciales/negativos compatibles,
  manteniendo referencias/seguridad y comprobando SQLSTATE específicos.
- `tests/integration/test_cases_history.py`: expectativas fortalecidas con triggers.
- `tests/integration/cases/conftest.py` y `scheduling/conftest.py`: rollback PG por prueba.
- `tests/integration/scheduling/test_scheduling_endpoints.py` y `test_worker_integration.py`:
  preparar BORRADOR antes de publicar.
- `tests/integration/test_schema_integration.py` y `test_er28_academic_base.py`: cadena.
- Nuevo `tests/integration/test_cases_guard_migration.py`: migración/HTTP PG reales.
- `docs/bd/laboratorio_bd2_04/run_lab.py` y README: baseline histórico fijo y modo
  de revisión real sin alterar SQL; JSON nuevos y este informe.

Los documentos experimentales anteriores se conservan como antecedentes de la
propuesta previa, ahora enlazados con esta entrega. No se aplicó la revisión a
bases persistentes ni se hace commit/push/merge/cambio de rama. No se inicia BD2-05.

Cierre de Git: frente a los 294 archivos preexistentes registrados, solo cambian
15 archivos de pruebas/documentación; se agregan siete (revisión, prueba, informe
y cuatro evidencias JSON). No hay archivos eliminados. Los demás cambios locales
anteriores conservan sus hashes, incluidos todos los módulos productivos/ORM y
ER originales. La rama sigue en feature/integracion-backend, con cambios locales
sin commit; no se hace staging, push, merge ni operación destructiva.

Análisis sintáctico, enlaces y whitespace de los 22 archivos intervenidos:
correctos. `git diff --check` no presenta errores; Git conserva un aviso LF/CRLF
de un archivo modificado en una fase anterior. No quedaron contenedores con la
etiqueta del laboratorio después de las pruebas. La evidencia final coincide
con los hashes del código/SQL ejecutado y confirma su eliminación por ID propio.
