# Corrección del arranque del laboratorio PostgreSQL

## Alcance y causa comprobada

Se cambió exclusivamente infraestructura de pruebas. Se conservaron los cambios
locales anteriores de la rama `feature/integracion-backend`. No se modificaron
servicios, modelos, migraciones, `.env` ni conexiones del equipo.

Se inspeccionó `/usr/local/bin/docker-entrypoint.sh` de la imagen local
`postgres:17` (ID
`sha256:b994732fcf33f73776c65d3a5bf1f80c00120ba5007e8ab90307b1a743c1fc16`).
`docker_temp_server_start` añade `-c listen_addresses=''`: el servidor temporal
de inicialización acepta sockets Unix, pero no TCP externo. Después de crear la
base y ejecutar los scripts de inicialización, el entrypoint detiene ese servidor
y arranca el definitivo. Por eso `pg_isready -U resolver_lab`, sin host TCP,
no demostraba disponibilidad desde SQLAlchemy en Windows.

La carrera se reprodujo en un contenedor nuevo, con datos en tmpfs y un script de
inicialización que ejecutaba `SELECT pg_sleep(5)` para ampliar la ventana de
observación. Ese retardo existió solo en la reproducción, no en el fixture:

- ID propio: `55bb6cb323ad1108df9adc02e8dcc97613f40c97735205ad4c8522d92f9a09ae`.
- Puerto publicado exclusivamente en `127.0.0.1`: `53466`.
- `pg_isready` por socket: aceptaba conexiones.
- En ese mismo momento, SQLAlchemy por el puerto publicado: conexión rechazada.
- La espera corregida terminó 5,01 segundos después, al obtener
  `sps_identity_test_resolver` mediante `SELECT current_database()`.
- El contenedor de la reproducción se eliminó por su ID completo.

Esto confirma el falso positivo del mecanismo anterior. No se instrumentó la
ejecución histórica del usuario para atribuir individualmente sus 62 errores.

## Mecanismo corregido

1. Exigir opt-in `SPS_TEST_IDENTITY_MAPPING_DOCKER=1` y una imagen local instalada.
2. Crear un contenedor nuevo y conservar su ID completo antes de iniciarlo.
   Se usa `docker create` y luego `docker start`, sin `--rm`, para conservar los
   registros de un arranque fallido hasta capturarlos.
3. Verificar ID, nombre generado, etiqueta `sps.identity.mapping.lab=true`, ausencia
   de montajes bind/volume y puerto publicado solo en loopback. El directorio de
   datos sigue siendo tmpfs; no se admiten volúmenes persistentes.
4. Construir el engine con el puerto obtenido del contenedor propio y credenciales
   aleatorias del fixture. No se leen URLs de bases externas.
5. Reintentar conexiones SQLAlchemy TCP y `SELECT current_database()` hasta
   confirmar exactamente la base aislada. Una base diferente aborta inmediatamente.
6. Comprobar que no existen tablas antes de entregar el engine. Las migraciones
   de pruebas existentes solo se ejecutan después, sobre ese laboratorio vacío.
7. En `finally`, intentar tanto `engine.dispose()` como la eliminación del ID
   creado, aunque falle la primera operación. Un fallo de limpieza se informa; si
   ya existe otra excepción, se añade una nota sin ocultar la causa original.

La espera tiene un plazo monotónico de 30 segundos, conexiones con
`connect_timeout=2`, sentencias con `statement_timeout=2000` ms y pool con
`pool_timeout=2`. Solo se pausa hasta 0,2 segundos entre intentos fallidos; no se
supone que PostgreSQL esté listo tras una espera fija. El plazo puede excederse
por un intento ya en curso, cuyas operaciones también están acotadas.

Se reintentan errores operativos transitorios. Los errores inesperados y una
identidad de base incorrecta no se ocultan como indisponibilidad temporal. No se
añadieron `skip`, `xfail` ni reintentos de casos de negocio.

Al agotarse el plazo se informa el último error, estado del contenedor y las
últimas 80 líneas de logs, incluyendo stderr. Se redactan la contraseña propia,
sus representaciones URL y patrones habituales de contraseñas. No se imprime
`Config.Env`. Cada consulta diagnóstica tiene un límite de tres segundos.

La eliminación utiliza únicamente `docker rm --force <ID completo propio>` y un
plazo de diez segundos. Nunca selecciona por nombre, etiqueta global o contenedor
preexistente; tampoco ejecuta limpiezas globales.

## Validación

`test_postgresql_lab_startup.py` contiene 26 regresiones con mocks y reloj
simulado, sin conexiones reales: indisponibilidad transitoria, reinicio durante
el SELECT, base incorrecta, timeout, errores inesperados, secretos, diagnósticos,
fallos de start/dispose/limpieza y controles de aislamiento.

Los grupos de repositorio académico, HTTP académico, concurrencia PostgreSQL,
política temporal y login aprobaron sus 156 casos sin omisiones. El informe JUnit
de la primera suite confirma 75 casos PostgreSQL en esos grupos; los restantes
81 son SQLite y comprobaciones independientes del motor. Las políticas temporales
positivas siguen usando ventanas sintéticas de pruebas, sin aprobar una política
académica productiva.

Comandos (PowerShell, desde la raíz del repositorio):

```powershell
$env:SPS_TEST_IDENTITY_MAPPING_DOCKER='1'
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_postgresql_lab_startup.py -q --tb=short
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_academic_identity_repository.py backend/tests/identity/test_academic_identity_http_sql.py backend/tests/identity/test_academic_identity_postgresql.py backend/tests/identity/test_ingress_temporal_sql.py backend/tests/identity/test_student_login_scheduling.py -q -rs --tb=short
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Resultados reales, con contenedores nuevos por módulo en cada ejecución:

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias | Tiempo pytest |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Regresiones simuladas | 26 | 0 | 0 | 0 | 1 | 0,36 s |
| Cinco grupos relacionados | 156 | 0 | 0 | 0 | 1 | 33,57 s |
| Suite completa 1, con JUnit | 983 | 38 | 0 | 0 | 53 | 56,19 s |
| Suite completa 2 | 983 | 38 | 0 | 0 | 1 | 55,48 s |
| Suite completa 3 | 983 | 38 | 0 | 0 | 1 | 57,56 s |

La primera suite añadió `--junitxml` en el directorio temporal del sistema. Sus
53 advertencias son una de Starlette y 52 por incompatibilidad de
`record_property` con JUnit xunit2. Las dos siguientes usaron exactamente el
comando de suite solicitado y solo emitieron la advertencia conocida de Starlette.
No se cambió configuración para silenciar avisos.

Durante la construcción de las nuevas pruebas se corrigió una representación
incorrecta de `docker inspect` en el mock (objeto en lugar de lista). La primera
ejecución de esas regresiones había dado 23 aprobadas y tres fallidas; tras
corregir el mock, las 26 pasaron y se conservaron en las tres suites completas.

Las 38 omisiones pertenecen a configuraciones distintas que no se habilitaron:
29 de `SPS_IDENTITY_TEST_URL`, tres de conexión PostgreSQL de Participation y seis
de `SPS_PERSISTENCE_LAB_URL`. No representan pruebas aprobadas.

La comprobación final `docker ps -a --filter label=sps.identity.mapping.lab=true`
no encontró contenedores remanentes. `git diff --check` terminó correctamente;
también se comprobó el whitespace de los tres archivos de esta tarea, que aún
figuran como no rastreados por Git junto con los cambios locales previos.

## Límites

Un Docker detenido, falta de recursos o una inicialización que exceda el plazo
seguirán fallando con diagnóstico; no concederán disponibilidad por socket.
Si Docker deja de responder durante la limpieza, el fallo se reporta y no se
intenta eliminar otros recursos. Una interrupción forzada del proceso tampoco
puede garantizar la ejecución de `finally`. Las repeticiones comprueban estabilidad
en esta máquina; no garantizan todas las condiciones posibles de carga o red.

No se conectó a `sps-identity-pg-test`, `proyecto-nuclear-2-db-1` ni a una base
compartida. Los únicos destinos SQL PostgreSQL habilitados por esta tarea fueron
puertos loopback efímeros de contenedores nuevos de laboratorio.
