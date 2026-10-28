# Verificación del incremento de Identity

Fecha: 28 de octubre de 2026, America/Bogota.

## Incremento DBML posterior al commit 351169b

La rama inició limpia en `351169b`. Se conservaron los archivos de las pruebas
originales sin cambios, verificado con git diff contra ese commit. No se hizo
commit, push, Pull Request ni se alteró el commit base.

Se ejecutó nuevamente la suite completa con `SPS_IDENTITY_TEST_URL` apuntando a
un clúster local temporal independiente, base `sps_identity_test`, limitado a
127.0.0.1. Las pruebas usan esquemas aleatorios y los eliminan al finalizar.
El servidor informó PostgreSQL **18.4**; no se presenta como prueba de PostgreSQL
17, que sigue siendo la versión de Compose del proyecto.

Comando real, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend/tests -c backend/pyproject.toml -q -p no:cacheprovider
```

Resultado:

```text
174 passed, 1 warning in 9.07s
```

Incluye las 109 pruebas originales, las pruebas de mapeo y las nuevas pruebas
parametrizadas de persistencia sobre SQLite y PostgreSQL. La advertencia restante
es la de Starlette/HTTPX ya documentada; no se ocultó mediante filtros.

Se comprobaron:

- Upgrade/downgrade de la migración real de las cuatro tablas de acceso.
- Correspondencia de los seis mapeos con columnas, longitudes, nulabilidad y FK
  del DBML conservado como fuente de prueba.
- Unicidad de correo, PK compuesta, FK reales, defaults y rollback atómico.
- Identidad y permisos por rol recuperados mediante el repositorio real.
- Alta HTTP con proxy/servicio/UoW/repositorio reales y clave verificada con Argon2.
- HTTP 403 del estudiante usando JWT y usuario leído de la BD, además de la prueba
  original que utiliza dobles de persistencia.
- Rechazo de multirrol y concesiones individuales no representadas en el ER,
  sin modificar los permisos globales del rol.
- Usuario inactivo pierde acceso con su JWT anterior.
- Persistencia nativa de permiso_intento_extra, FK y rollback sin consumir intentos.
- LEFT OUTER JOIN ejecutado en ambas BD, preservando NULL y resultados oficiales
  sin calcular notas ni reclasificar ausencias.
- Persistencia académica no integrada sigue respondiendo 503.

La consulta final al catálogo del laboratorio mostró **0 esquemas temporales**
restantes. No se conectó ni migró la BD del proyecto. Docker no estaba disponible;
se utilizó la instalación local de PostgreSQL en un directorio temporal aislado.
El clúster temporal se detuvo al terminar la verificación.
La revisión automática rechazó eliminar su directorio temporal con el motivo
`blocked by policy`; sus archivos permanecen en el directorio de laboratorio,
sin servidor activo. No se intentó eludir esa restricción.

`pip check`: `No broken requirements found.`
`git diff --check`: sin errores. OpenAPI conserva 10 rutas.

**Límites:** siguen sin comprobarse el padrón completo real, el mapeo académico de
situacion, la concurrencia entre módulos y el feedback individual incompatible
con el ER. Las tablas académicas de los fixtures se construyen exclusivamente en
el laboratorio desde el DBML; no son implementación de módulos de compañeros.

## Evidencia histórica del incremento anterior

Lo que sigue corresponde a la entrega de 109 pruebas conservada en `351169b`;
sus bloqueos históricos se actualizan en [PERSISTENCE_DBML.md](PERSISTENCE_DBML.md).

## Estado inicial y alcance de los cambios

- Rama activa: `alejandro`. Árbol inicialmente limpio.
- HEAD inicial: `ae45e95`, igual a `main` y `origin/main`.
- Verificación `git merge-base --is-ancestor origin/main HEAD`: código 0.
- `origin/alejandro` permanece en `c3cda63`; la rama local ya tenía incorporada
  la base arquitectónica. Este incremento no hizo merge, commit ni push.
- Código nuevo concentrado en `backend/app/modules/identity/`; pruebas en
  `backend/tests/identity/`. Cambios compartidos: registro del router,
  configuración, dependencia PyJWT, variables de entorno, su paso a API en
  Compose y actualización del estado en README.
- Sin cambios a cases, participation, scheduling, frontend, Worker, Base común,
  fábrica de sesiones, modelos de otros compañeros o migraciones.

## Ejecuciones reales

Desde la raíz del repositorio, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -c backend/pyproject.toml -q
```

Último resultado sobre el código final:

```text
109 passed, 1 warning in 4.48s
```

Incluye la prueba técnica `/health` existente y las nuevas pruebas de Identity.
La advertencia procede de Starlette 1.10.0: su TestClient depreca HTTPX en favor
de HTTPX2. No es un fallo de prueba y no se ocultó con filtros. No se cambió la
infraestructura de pruebas del equipo para silenciarla.

Otras comprobaciones:

| Comprobación | Resultado real |
| --- | --- |
| `python -m pip check` dentro de `.venv` | `No broken requirements found.` |
| `git diff --check` | Código 0, sin errores de whitespace en archivos seguidos |
| Generación de `app.openapi()` | 10 rutas documentadas: 9 de Identity y `/health` |
| `docker compose config --quiet` | Código 0; configuración válida |

La comprobación Compose utilizó variables temporales ficticias de PostgreSQL y
dominio de prueba únicamente para resolver la configuración. No inició
contenedores, no conectó a PostgreSQL y no persistió esas variables en `.env`.

## Prueba HTTP 403 solicitada

`backend/tests/identity/test_http.py`:
`test_http_403_estudiante_intenta_autorizar_repeticion_excepcional`.

1. Emite un JWT firmado de prueba para un usuario con rol ESTUDIANTE y contexto
   de convocatoria.
2. Envía POST a `/api/v1/identity/excepciones/repeticiones` con una solicitud
   válida de sesión/estudiante.
3. Ejecuta la validación JWT, resolución de usuario y ProxyExcepciones reales.
   No sustituye `obtener_usuario_actual` ni el proxy por un resultado prefijado.
4. Comprueba HTTP 403, código `ACCESO_DENEGADO` y `Cache-Control: no-store`.
   El servicio real predeterminado sigue sin configurar: un acceso indebido a su
   fábrica habría provocado 503, por lo que el 403 demuestra el rechazo previo.

El repositorio de usuarios y la clave usados son exclusivamente dobles/valores de
prueba. Esto demuestra el control HTTP/backend, no autenticación contra una BD real.

## Cobertura funcional comprobada

- JWT: firma, algoritmo fijo, emisor/audiencia, claims obligatorios, expiración,
  fechas futuras, tipos inválidos, token malformado y configuración insegura.
- Autenticación: pareja correo/código, dominio institucional exacto, convocatoria
  rechazada e identidad inactiva, inexistente o ajena a la pareja validada.
- Autorización: el rol no implica permisos específicos; se recuperan los roles
  actuales del servidor y no se aceptan roles añadidos a un JWT ni identidad en
  cabeceras/query. Un JWT estudiantil sin convocatoria es rechazado.
- Proxies: estudiantes reciben 403 al intentar consultar, exportar, añadir feedback,
  conceder repeticiones o administrar docentes. Docentes fuera del ámbito son
  rechazados antes de consultar o modificar datos.
- RF-25: con puertos de prueba, creador válido obtiene concesión; otro docente
  recibe 403, y una sesión finalizada o participación previa inexistente, 409.
- RF-26: autor y fecha del servidor, texto inválido rechazado y ámbito revalidado
  dentro de la transacción de escritura.
- RF-03: administrador crea docentes y asigna autorizaciones; un docente no puede
  administrar usuarios y se rechazan permisos ajenos al catálogo.
- Reportes: exportación CSV de filas completas, parciales y ausencias entregadas
  por un puerto; precisión Decimal y nota no confirmada vacía; descarga protegida
  y neutralización de fórmulas en identificadores.
- Transacciones: laboratorio SQLite en memoria con tabla técnica `prueba_uow`,
  metadata aislada de `Base`. Comprueba Session común para los adaptadores,
  commit explícito, rollback de toda la transacción, cierre ante errores y uso
  de la fábrica común del backend. No crea tablas académicas.
- Fallos de integración: producción sin adaptadores devuelve 503 sin emitir
  tokens ni simular persistencia. Un fallo de commit no devuelve HTTP 201.

## Lo que estas pruebas no demuestran

- No se probaron repositorios académicos en PostgreSQL, FK, DDL o migraciones:
  todavía no existe ER validado disponible para implementarlos.
- No existe todavía la consulta concreta SQLAlchemy con LEFT JOIN. Sus pruebas
  quedan pendientes del mapeo y del contrato de lectura compartido. Las pruebas
  CSV utilizan filas preparadas por un doble y no se presentan como pruebas SQL.
- No se comprobó concurrencia real entre concesión, cierre de sesión y consumo
  posterior de una autorización. Falta el contrato transaccional con los compañeros.
- No se probó integración real de convocatorias, identidad del personal,
  respuestas/resultados, frontend, Worker o notificaciones.
- No se afirma el cumplimiento integrado de los siete RF mientras permanezcan
  los bloqueos detallados en [README.md](README.md).

## Entorno de prueba

Python 3.13, entorno virtual local `.venv` excluido de Git.

| Paquete | Versión ejecutada |
| --- | --- |
| FastAPI | 0.162.0 |
| Starlette | 1.10.0 |
| SQLAlchemy | 2.0.55 |
| PyJWT | 2.15.1 |
| Pytest | 9.2.0 |
| HTTPX | 0.28.1 |
| Psycopg | 3.3.6 |
| Pydantic Settings | 2.16.2 |
