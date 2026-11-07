# RF-03: consulta administrativa privada de docentes

## Contrato y alcance

RF-03 exige administración de docentes, roles y permisos. Fuentes: matriz
`AUDITORIA_COBERTURA_BACKEND_20261105.md`, sección 3, y requisito centralizado
RF-03 en `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, p. 4.
El incremento solicitado añade una lectura administrativa; no completa por sí
solo todas las operaciones de RF-03.

La frontera existente es `ProxyAdministracionUsuarios`: alta y asignación requieren
`Rol.ADMINISTRADOR`. Se reutiliza esa autorización para consultar cuentas docentes.
No se concede acceso al rol DOCENTE ni a un supuesto DOCENTE ADMINISTRADOR. Este
último no tiene definición ejecutable en el catálogo de dominio.

## Endpoint disponible en la aplicación principal

`GET /api/v1/identity/docentes?limite=25&desplazamiento=0`

- Bearer obtenido mediante el login real `POST /api/v1/identity/auth/personal`.
- Límite entre 1 y 100; desplazamiento entero no negativo. Orden por `id_usuario`
  ascendente. Incluye docentes activos e inactivos, con estado explícito.
- Respuesta 200: `docentes` (id_usuario, nombre, correo, activo), `total`, `limite`
  y `desplazamiento`. Página vacía legítima cuando no hay coincidencias o el
  desplazamiento excede el total. Total y página corresponden a una instantánea.
- 401: sin Bearer válido o cuenta inexistente/inactiva; 403: rol vigente distinto
  de ADMINISTRADOR; 422: paginación inválida; 503: integración/configuración no
  disponible o catálogo de rol desconocido. No se exponen detalles SQL.
- `Cache-Control: no-store`, heredado de `RutaIdentity`.

No devuelve permisos, hashes, claves, JWT, rúbricas, notas, respuestas, matrículas
ni UUID académicos. La autorización administrativa existente acredita gestión de
cuentas; no prueba acceso universal a recursos académicos. Por eso no se añade
una consulta de asociaciones sin un contrato de ámbito aprobado. Las asociaciones
ausentes, múltiples o ambiguas no excluyen ni duplican cuentas, ni conceden acceso.

## Implementación y garantías

- DTO y puerto `application/teacher_directory.py`.
- El Proxy existente exige ADMINISTRADOR antes de invocar la consulta.
- `infrastructure/teacher_directory.py` usa una Session nueva, sin cambios
  pendientes, `REPEATABLE READ` y `postgresql_readonly=True`. Revalida existencia,
  estado activo y rol del actor en esa instantánea antes de listar.
- Proyección SQL de columnas públicas, sin cargar hashes de los docentes listados.
  Normaliza nombres de rol exactamente como el repositorio existente.
- Sin joins a identidades académicas y sin conversiones INTEGER/UUID.
- Sin DML, flush ni commit; el cierre de Session revierte la transacción lectora.
  PostgreSQL hace cumplir READ ONLY. Una revocación confirmada antes de abrir la
  instantánea se observa; una lectura ya iniciada no promete revocación retroactiva.
- El orden es determinista por instantánea. La paginación por desplazamiento no
  congela el catálogo entre solicitudes distintas si otros administradores lo cambian.
- Composición en dependencias, esquemas y router Identity ya registrado en main;
  no modifica app.main ni habilita Participation general, inicio o resultados.
- No hay modelos ni migraciones nuevos. Alta, bootstrap y asignación se conservan.

## Aceptación y evidencia

`backend/tests/integration/test_admin_teacher_directory.py`: 13 escenarios HTTP/
SQL sobre PostgreSQL17 desechable. Preparación administrativa de laboratorio;
bootstrap, login, JWT, roles y consultas reales, sin overrides de autorización.

Criterios: listado privado paginado, estados, cuentas con cero/múltiples vínculos,
rechazos de autenticación/rol, cambio de rol después del login, contexto anterior
revalidado en otra Session, sanitización de fallos SQL y conservación del alta.
Lecturas concurrentes iguales, ausencia de DML/flush/commit y verificación de
`SHOW transaction_read_only` / `SHOW transaction_isolation` en la consulta real.

Evidencia: `evidencias/rf03_consulta_20261107T044600Z/`, ejecutor aislado con lectura
de .env deshabilitada solo en el proceso pytest; elimina URLs externas heredadas.
Cada escenario crea su contenedor PG17 propio, sin datos persistentes del equipo.
No se instalan dependencias ni se modifican .env, stash o referencias.

Primera ejecución conservada: 12 aprobadas, 1 fallo de preparación. La fixture
reutilizada compartía el motor entre escenarios; el conteo incluía cuentas previas.
Se sustituyó exclusivamente esa preparación por la fixture desechable por escenario
ya existente de bootstrap; no se relajó la aserción ni el control productivo.
Reejecución: **13 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia Starlette**
en 56.79 s, con fuentes estables durante pytest. Regresión relacionada: **166
aprobadas, 0 omitidas/fallidas/errores, 1 advertencia**, 150.04 s; incluye la
aceptación y bootstrap, login, alta, servicios/proxies, seguimiento y recorrido
estudiantil. No sumar selecciones solapadas.

General final: **2265 aprobadas, 38 omitidas, 0 fallidas, 0 errores, 1 advertencia
Starlette**, 1222.11 s. JUnit: 2303 casos nominales. Las 38 omisiones corresponden
a pruebas históricas que requieren URLs externas de laboratorio explícitas;
no se configuraron para evitar bases permanentes y no se declaran aprobadas.
La nueva aceptación no tiene omisiones. Se conserva el JSON de evidencia BD2-04
generado por su prueba; ninguna fuente preexistente cambió durante pytest.

Las cifras son ejecuciones nuevas de HEAD `8b544f5d7f370076756d38b1d594fb77ab21f31b`
**más los cambios locales del incremento**, no resultados del commit aislado.
Consolas, JUnit, comandos, fecha y SHA-256 de fuentes están en las carpetas
`pruebas_casos_20261107T044857Z`, `pruebas_focal_20261107T045046Z` y
`pruebas_total_20261107T045400Z` de la evidencia. Se conserva también la ejecución
fallida inicial `pruebas_casos_20261107T044810Z`.

Comandos PowerShell desde la raíz del repositorio (cada selección es independiente):

```powershell
.\.venv\Scripts\python.exe -B evidencias\rf03_consulta_20261107T044600Z\ejecutar_validacion.py casos
.\.venv\Scripts\python.exe -B evidencias\rf03_consulta_20261107T044600Z\ejecutar_validacion.py focal
.\.venv\Scripts\python.exe -B evidencias\rf03_consulta_20261107T044600Z\ejecutar_validacion.py total
```

## Archivos del incremento

- `backend/app/modules/identity/application/teacher_directory.py`: DTO y puerto nuevos.
- `backend/app/modules/identity/infrastructure/teacher_directory.py`: lector SQL nuevo.
- `backend/app/modules/identity/application/proxy_administracion.py`: autorización
  del lector con dependencia opcional compatible con los constructores existentes.
- `backend/app/modules/identity/api/dependencies.py`: composición SQL real.
- `backend/app/modules/identity/api/schemas.py`: respuesta pública acotada.
- `backend/app/modules/identity/api/router.py`: GET privado y parámetros limitados.
- `backend/tests/integration/test_admin_teacher_directory.py`: aceptación nueva.
- Este informe y la matriz vigente: alcance acreditado y resultados.

Sin cambios de ORM/Alembic ni de app.main. El router Identity existente publica
la nueva ruta en main. No se modificaron las operaciones previas de administración,
el bootstrap, Evaluation, consentimiento ni las operaciones estudiantiles.

## Límites de RF-03

RF-03 sigue PARCIAL. No se implementan activación/desactivación, recuperación,
permisos individuales, multirrol, administración de asociaciones ni atribuciones
de DOCENTE ADMINISTRADOR sin sus contratos. Tampoco se presenta el catálogo LAB
como configuración operativa institucional. Estado de los 27 RF sin cambio:
14 IMPLEMENTADO, 8 PARCIAL, 5 BLOQUEADO.

Siguiente incremento recomendado: acordar la gestión administrativa de asociaciones
académicas (autoridad, ámbito y conflictos) antes de publicar su consulta/escritura;
reutilizar el resolver persistente y la asignación explícita ya existente.
