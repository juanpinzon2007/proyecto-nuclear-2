# RF-21 — altas, retiro lógico y avisos transaccionales

Fecha: 4 de noviembre de 2026 (America/Bogota).
Worktree: `C:\SPS\consolidacion`, rama `codex/consolidacion-backend`.
**RF-21 sigue parcial: el aviso interno no sustituye el envío de correo exigido.**

## Operaciones implementadas

El modelo existente representa una convocatoria individual por estudiante y
sesión. Agregar otro estudiante crea otra convocatoria mediante el POST existente;
no se sustituye el estudiante de una convocatoria histórica ni se añade otra tabla.

| Endpoint | Comportamiento |
|---|---|
| `POST /scheduling/sesiones/{sesion_id}/convocatorias` | Alta con código individual de entrega única, aviso interno y respuesta 201 con `Cache-Control: no-store`. Mantiene la regla existente de sesión SIN_INICIAR. Una repetición se rechaza con 422 y no regenera código ni aviso. |
| `GET /scheduling/sesiones/{sesion_id}/convocatorias` | Listado docente existente; no devuelve código ni hash. |
| `DELETE /scheduling/sesiones/{sesion_id}/convocatorias/{convocatoria_id}` | Nuevo retiro lógico a RETIRADA, respuesta 200. No DELETE físico. Repetirlo no añade otro aviso. |
| `GET /scheduling/notificaciones?destinatario_id=<UUID académico>` | Bandeja privada existente; el filtro debe coincidir con el destinatario resuelto por Identity. |

Scheduling ya está registrado en la principal; no cambió `main.py`. Las rutas
están compuestas allí, pero su funcionamiento se acreditó únicamente en aplicaciones
aisladas y bases desechables. No se habilitó globalmente Participation ni notas.

## Autorización e integridad

El adaptador `convocation_management.py` reutiliza `crear_convocatoria` y
`crear_notificacion`; no introduce otro motor de convocatorias o notificaciones.
La cuenta autenticada mediante Identity debe coincidir con la propietaria del
UUID docente resuelto. Dentro de la transacción se revalidan cuenta activa, rol
DOCENTE y asociaciones estrictamente inequívocas de Scheduling y Cases.

Además se exige sesión propia, asignación persistida a su versión exacta, caso
del docente y grupo del docente con matrícula del destinatario. El alta exige
cuenta ESTUDIANTE activa y matrícula activa. El retiro no exige que el destinatario
siga activo: reduce acceso, no concede permisos. Si falta la asignación, se
responde 503; referencias ajenas o matrícula no autorizada se rechazan con 403.
No se infiere grupo desde espacio_academico, no se inventan asociaciones legadas
ni se presupone una sola asignación/grupo por sesión.

Los bloqueos de cuentas/roles/asociaciones y sesión/matrículas mantienen la
autorización durante la escritura. El retiro comparte el advisory lock de
provisión y bloquea la participación existente y convocatoria. La sesión
serializa altas concurrentes y se conserva UNIQUE(sesión, estudiante).
Convocatoria y aviso usan la misma Session y commit: un fallo revierte ambos.
No se declara un protocolo universal de exactamente una vez para proveedores
externos ni una restricción de unicidad adicional sobre todos los avisos SQL.

El retiro permite registrar `CONVOCATORIA_RETIRADA` sin alterar referencias
históricas. Los JWT previos siguen acreditando identidad hasta su expiración,
pero el estado RETIRADA revoca login por ese código, ingreso, inicio de intento,
progreso y escritura académica. No se elimina ni se reclasifica el intento o sus
respuestas. La cuenta puede consultar su identidad y avisos con un JWT vigente.
No se implementa reactivación de retiros, rotación de códigos ni reingreso.

## Avisos y correo pendiente

El alta registra un aviso `CONVOCATORIA/INTERNA/PENDIENTE` para el UUID real del
destinatario, con nombre de la versión, inicio programado y mensaje personalizado.
El retiro genera un aviso `CONVOCATORIA_RETIRADA/INTERNA/PENDIENTE` para el mismo
titular. La creación genérica comprueba la correspondencia convocatoria/destinatario.
La consulta de la bandeja no concede acceso a una convocatoria retirada.

Solo se conserva el hash del código. El código original se devuelve una vez al
docente autorizado: no se añade al mensaje persistido, listados ni logs. El
ejecutor de pruebas redacta JWT, credenciales de conexión y códigos de laboratorio.
No se generan registros CORREO como si acreditaran un envío real.

Para completar RF-21 faltan:

1. Proveedor SMTP/API, remitente y secretos configurados de forma segura en el servidor.
2. URL pública institucional confiable para la invitación; no se inventa una URL de frontend.
3. Diseño aprobado de entrega recuperable del código de un solo uso. Su hash no
   permite reconstruirlo; enviar antes del commit puede anunciar una convocatoria
   revertida. No se improvisa almacenamiento en claro ni una rotación automática.
4. Adaptador de entrega y pruebas de errores/reintentos/idempotencia del proveedor.
   Las pruebas actuales acreditan rollback/reintento de persistencia, no SMTP.

Las convocatorias legadas sin correspondencia académica demostrada necesitan
conciliación de datos autorizada antes de gestionarse por estas rutas.

## Pruebas y evidencia

`test_convocation_management_http.py` añade 20 escenarios: 19 casos HTTP con JWT
y PostgreSQL reales y uno SQL para rechazar discrepancia cuenta/UUID docente.
Cubre altas, ámbito, privacidad, retiro efectivo con JWT anterior, bandeja,
concurrencia, persistencia desde otra sesión y rollback tras flush real del aviso.
Las sustituciones sobre operaciones de persistencia son inyecciones de fallo
para probar rollback; no se sustituyen autorización ni relaciones críticas por mocks.

Se reutilizan fixtures 8B con cuentas/matrículas/asignaciones sintéticas y políticas
explícitas de laboratorio. No son políticas productivas. Las suites unitarias
antiguas mantienen dobles explícitos; no acreditan autenticación PostgreSQL real.

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Primera focal | 241 | 0 | 0 | 0 | 1 |
| Focal con vinculación cuenta/UUID | 242 | 0 | 0 | 0 | 1 |
| Retiro ampliado | 1 | 0 | 0 | 0 | 1 |
| General interrumpida por fixture | 614 | 29 | 1 | 0 | 1 |
| Reproducción corregida SQLite/PostgreSQL | 2 | 0 | 0 | 0 | 1 |
| General interrumpida por mock obsoleto | 1429 | 29 | 1 | 0 | 1 |
| Focal ampliada final | 358 | 0 | 0 | 0 | 1 |
| General final, sin detención temprana | 1915 | 38 | 0 | 0 | 53 |

No sumar suites solapadas. Se conservan las dos ejecuciones fallidas:

- La fixture Scheduling ahora necesita una asignación real. PostgreSQL rechazó
  su versión sin rúbrica propia. Se añadió la rúbrica técnica de laboratorio
  mientras el caso es borrador, sin desactivar el guard BD2-05/BD2-04.
- Dos unitarios parcheaban `router.crear_convocatoria`, que dejó de ser el punto
  de delegación. Ahora comprueban llamada al servicio, commit y rollback. El test
  `test_convocatoria_crea_notificacion` se renombró a
  `test_router_delega_convocatoria_y_aviso_en_una_transaccion`; las aserciones de
  destinatario/tipo/canal se acreditan además mediante persistencia y HTTP reales.

Las 38 omisiones son configuraciones externas deliberadamente no habilitadas
(29 Identity, 3 PostgreSQL antiguas y 6 laboratorio por URL). No se consideran
aprobadas. Advertencias conocidas: Starlette y record_property/JUnit xunit2.

JUnit, logs, comandos exactos, huellas y resultados están fuera del repositorio:
`C:\SPSBackups\rf21-20261104T190517Z`. El laboratorio antiguo crea `sps_test`
exclusivamente dentro de su contenedor nuevo verificado, no en una base del equipo.

## Archivos y control de versiones

- `scheduling/infrastructure/convocation_management.py`: coordinación SQL y ámbito.
- `scheduling/api/router.py`: reutiliza POST y añade retiro lógico protegido.
- `scheduling/application/crear_notificacion.py`: tipo CONVOCATORIA_RETIRADA.
- `tests/integration/test_convocation_management_http.py`: aceptación nueva.
- `tests/integration/test_participation_http_composition.py`: asignación antes de convocar.
- `tests/integration/scheduling/conftest.py` y `test_scheduling_endpoints.py`: datos SQL válidos.
- `tests/unit/scheduling/test_api_convocatorias.py`: límite de delegación actualizado.
- Este informe.

Antes de modificar se verificaron 357 archivos, referencias y bundle. Se crearon
cinco commits locales del trabajo previo: `c278996`, `5c8807b`, `7a0ccc3`,
`687cb71`, `e4aa688`. Las pruebas de este incremento se ejecutaron sobre e4aa688
más los cambios RF-21; el cierre externo identifica el commit final y comprueba
que sus fuentes y tests coincidan byte a byte con la ejecución general.

Se excluyen de los commits los JSON de evidencia y el README pendiente con
enlaces a una guía/ejecutor ausentes. No se eliminan. No se incluyen secretos
reales, configuración privada ni cachés. Los datos y claves de fixtures son
explícitamente sintéticos, no credenciales de despliegue.

No hay cambios en ORM, DBML, Alembic, fórmulas Evaluation ni políticas pendientes
8B. Se conserva la cabeza `20261102_immutable_answers`. No hubo push, merge,
cambio de rama, consumo del stash ni operaciones sobre bases permanentes.


## Aclaración vigente Fase10 (10/11/2026)

La expresión histórica «código de un solo uso» en la propuesta de entrega recuperable no constituye una política de consumo en el login. El código se devuelve en claro una sola vez al crear la convocatoria; su validez se verifica después con hash/estado/contexto. No se definió un TTL propio, consumo por autenticación ni rotación automática. El significado correcto para la limitación de recuperación es «código original expuesto una sola vez en la respuesta de alta».

La ejecución nueva main/PG17/Newman acredita código y avisos internos, no SMTP. El modelo admite CORREO pero carece de emisor y registro de intentos de entrega. Se mantiene el bloqueo integral de RF20/RF21 y no se implementa otra política. Fuentes exactas, 25 focales/74 relacionadas y16HTTP/53aserciones por RF: `backend/docs/RF20_RF21_ENTREGA_SEGURA_20261110.md`.
