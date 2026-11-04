# RF-18 — programación autorizada con versión exacta

Fecha: 4 de noviembre de 2026, America/Bogota.
Worktree `C:\SPS\consolidacion`, rama `codex/consolidacion-backend`.
Base probada: `eec3b1f92be05fdfe9bee13e675df0101f01265b` más los cambios de este incremento.

## Brecha encontrada y decisiones expresamente autorizadas

La autenticación JWT y las identidades académicas ya estaban integradas. El
programador existente comprobaba espacio existente, versión PUBLICADO, fechas
con zona horaria, fin posterior al inicio y máximo positivo no superior al
estimado. Conservaba el UUID solicitado y bloqueaba la versión contra archivo
concurrente. No se reconstruyeron esas reglas.

Faltaban dos controles: autoría del caso y autorización explícita para usar el
espacio. EspacioAcademicoModel solo tenía id/nombre y no equivale a un grupo ni
a una matrícula. El usuario confirmó asignaciones explícitas y autorizó la tabla
técnica M:N, su ORM y una migración aislada, sin autovinculación ni API de concesión.

## Persistencia aprobada

`docente_espacio_academico` tiene exclusivamente:

| Columna | Tipo / restricción |
|---|---|
| id_docente | INTEGER, FK usuario.id_usuario, parte de PK |
| espacio_academico_id | UUID, FK espacio_academico.id, parte de PK |

La PK compuesta evita duplicar la asignación sin imponer exclusividad de docente
o espacio. No se usa el UUID personal de Scheduling como PK de usuario. Los
roles vigentes se comprueban en aplicación: una fila SQL no convierte una cuenta
en docente. No se añaden CHECK entre tablas, columnas académicas ni grants inferidos.

Revisión: `20261104_teacher_spaces`, padre `20261102_immutable_answers`.
Upgrade crea solamente esa tabla vacía, sin backfill ni actualización de registros
anteriores. Downgrade bloquea la tabla y solo permite retirarla si está vacía;
rechaza perder asignaciones existentes. No elimina sesiones ni sus referencias.

El metadata pasa de 30 a **31 tablas ORM**; PostgreSQL contiene además la tabla
técnica de Alembic. El DBML académico oficial mantiene sus 28 entidades intactas.
Los modelos usan la Base y el registro existentes de Scheduling; no otra metadata.

## Flujo real y autorización

`POST /scheduling/sesiones` conserva su contrato HTTP. Identity exige JWT y rol
DOCENTE reales; el adaptador RF-18 revalida cuenta, rol y asociaciones bajo locks
en la misma Session del escritor. Resuelve Cases y Scheduling por separado,
comprueba que el UUID Scheduling corresponde a la cuenta autenticada y reutiliza
`CasoRepository.obtener_version` para la propiedad del caso.

La versión solicitada se bloquea y el permiso docente–espacio se lee con FOR SHARE.
El permiso puede ser revocado sin cambiar sesiones históricas, pero una revocación
confirmada impide nuevas programaciones. No se permite que una autorización
leída previamente se use fuera de la transacción. Proveedor ausente o fallos SQL:
503 sin detalles internos; caso o espacio ajenos/no asignados: 403. Versión
inexistente/no publicada/archivada y reglas de duración inválidas: 422.

Después de autorizar se llama al `programar_sesion` existente. Solo se corrigió
su aceptación accidental de estado None: ahora exige PUBLICADO explícitamente.
No se inventan reglas sobre fechas futuras, solapamientos, modalidad o ingreso
tardío. Lugar sigue siendo opcional; cuando se proporciona, conserva su límite
HTTP existente de 255 caracteres. Se persisten horario, duración, lugar y mensaje.

La respuesta se materializa antes del commit, sin un refresh posterior que pueda
informar error cuando ya existe un registro confirmado. Cualquier error anterior
al commit revierte la operación. No se duplica el motor de programación.

## Rutas y alcance de disponibilidad

- `POST /scheduling/sesiones`: programación protegida con asignación persistente.
- `GET /scheduling/sesiones` y `GET /scheduling/sesiones/{sesion_id}`: consultas
  docentes existentes; conservan la versión histórica y su ámbito de sesión.
- `/scheduling/espacios` conserva el catálogo existente. Crear/ver una entrada
  del catálogo no concede permiso de programación.
- RF-21 sigue usando las sesiones para convocatorias; no se altera su contrato.

Scheduling ya está registrado en la principal; no se modificó main.py ni se
habilitó Participation globalmente. El funcionamiento se acreditó solo en
aplicaciones y PostgreSQL aislados, no en una base permanente o despliegue.

## Evidencia de aceptación

`test_session_programming_http.py` añade 19 escenarios HTTP/JWT/PostgreSQL reales:
permiso persistente, actor y propiedad, UUID distintos Cases/Scheduling, lugar
opcional/datos completos, fechas/zona/duración/lugar inválidos, borrador, archivo,
versión inexistente, proveedor ausente, rollback y revocación concurrente.

Una edición posterior del mismo caso demuestra que la sesión conserva la versión
solicitada. La edición 2 se prepara con el mapeador/ORM existente y luego se publica
por API: no se presenta esa preparación de datos como un endpoint de nuevas
ediciones, que actualmente no existe. No se modifican versiones históricas.

`test_teacher_space_migration.py` comprueba en PostgreSQL 17 nuevo upgrade,
downgrade y reupgrade, tabla inicialmente vacía pese a sesiones previas, PK/FK,
duplicados/referencias huérfanas rechazadas y rechazo de downgrade con permisos.
Se conserva exactamente la sesión anterior a la migración.
Un unitario adicional verifica el rechazo de una versión sin estado.

Se reutilizan las pruebas RF-21 de sesión HTTP → asignación/matrícula persistidas
→ convocatoria. Sus fixtures incorporan grants explícitos de laboratorio antes
de programar; no se sustituyen las relaciones críticas ni la autorización por mocks.
Las políticas de inicio 8B de esas fixtures siguen siendo solo de laboratorio.
Los unitarios antiguos con dobles no se presentan como aceptación PostgreSQL.

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Focal inicial | 450 | 0 | 16 | 0 | 1 |
| Focal final | 466 | 0 | 0 | 0 | 1 |
| General final | 1936 | 38 | 0 | 0 | 53 |

No sumar suites solapadas. Los 16 fallos iniciales fueron aserciones del conteo
global de sesiones en un laboratorio compartido entre escenarios. Se corrigió
el filtro por el espacio de cada escenario, sin borrar datos ni cambiar producción.
Se conserva el registro fallido. Las 38 omisiones siguen siendo configuraciones
externas no habilitadas (29 Identity, 3 PostgreSQL antiguas y 6 laboratorio por URL),
no pruebas aprobadas. Advertencias: Starlette y record_property/JUnit xunit2.

JUnit, logs, comandos exactos, respaldo y huellas quedan fuera del repositorio en
`C:\SPSBackups\rf18-20261104T202212Z`. La revisión nueva solo se ejecutó sobre
PostgreSQL desechable propio. Los ciclos históricos también se prueban en SQLite
aislado; no se les atribuyen los triggers ni la migración nueva de PostgreSQL.

## Cambios y límites

Producción: contrato de autorización y adaptador SQL RF-18; dependencias/router;
programador existente; modelo técnico y revisión Alembic nueva. Las expectativas
globales de metadata/cabeza en pruebas se actualizan a 31/nueva revisión conservando
los ciclos y verificaciones de las revisiones históricas. El auxiliar SQLite solo
retira DDL vacío propio, sin estampar migraciones PostgreSQL que no ejecutó.

Se preservan Identity/Cases, Evaluation, fórmulas y políticas pendientes de 8B.
No se modificó el DBML original. El proceso administrativo para registrar las
asignaciones explícitas no se convierte en un endpoint público ni se simula
con configuraciones de laboratorio. Antes de desplegar deben aprobarse/registrarse
datos reales por un procedimiento administrativo controlado, aplicar la migración
y configurar Identity. Ninguna de esas operaciones se ejecutó sobre bases del equipo.

RF-18 queda implementado y acreditado para las reglas definidas y los datos de
autorización persistidos. Esto no declara completo todo el backend ni acredita
un despliegue productivo. RF-04 se reutiliza para publicación y RF-21 se conserva.

Siguiente bloqueo funcional identificado, sin implementarlo: login HTTP de
docentes/administradores. En Identity el único login público actual es
`POST /api/v1/identity/auth/estudiantes`; el servicio solo expone
`autenticar_estudiante`. Las pruebas docentes usan el emisor JWT real con
configuración/cuentas sintéticas. Cerrar la emisión de tokens desde credenciales
verificadas permitiría usar las APIs docentes sin emisión manual de laboratorio,
reutilizando Identity, su repositorio y pwdlib. Requiere revisar ese incremento;
no nuevas políticas académicas ni otro sistema JWT.
