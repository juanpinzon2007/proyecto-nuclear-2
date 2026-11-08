# RF-03: inicialización controlada del primer administrador

## Selección y contrato del incremento

RF-03 (documento de Ingeniería, p.4) asigna al administrador el alta de docentes,
roles y permisos. Esas rutas y el login personal ya existen en app.main. La matriz
marca como dependencia el bootstrap: solo había preparación SQL de laboratorio.
El usuario exige que siga siendo una operación controlada por el equipo.

Se implementa exclusivamente un comando interno de despliegue, sin endpoint ni
registro público. Reutiliza el hasheador, repositorio de usuarios y UoW de Identity.
No añade roles ni permisos al catálogo ni genera asociaciones académicas.

Precondiciones técnicas y criterios de aceptación:

- PostgreSQL con esquema vigente y un único rol ADMINISTRADOR inequívoco ya
  configurado por el equipo. No se supone su ID. Catálogo ausente/ambiguo: rechazo.
- Ninguna cuenta administrativa existente, incluyendo inactivas. Un correo ocupado
  tampoco se reutiliza ni se eleva a administrador. No es recuperación de cuentas.
- Nombre, correo y clave explícitos; se conservan los límites del alta existente.
  La clave se hashea con el mismo mecanismo; sin clave predeterminada o en argv.
- Transacción READ COMMITTED y locks de usuario/rol durante comprobación e INSERT.
  Dos inicializaciones concurrentes no pueden confirmar dos primeras cuentas.
- Commit único; un fallo revierte el alta y no informa un ID exitoso.
- El administrador puede usar el login personal real y crear docentes mediante
  las rutas existentes. El rol administrativo no concede rol docente ni permisos
  académicos implícitos. No se altera el catálogo compartido rol_permiso.
- Consola interactiva sin eco, doble introducción y confirmación explícita del
  nombre de base. No hay argumento de contraseña ni salida de hash/token/clave.

## Límites comprobados en la inspección

Hay ADMINISTRADOR, DOCENTE y ESTUDIANTE en el dominio; no existe un rol
DOCENTE ADMINISTRADOR. Usuario tiene un rol físico y permisos por rol. El repositorio
rechaza multirrol y permisos individuales distintos del catálogo existente.
No se modifica esa cardinalidad ni se concede acceso docente a todo administrador.

El estado activo ya se revalida en login y JWT. No se encontraron rutas de
activación/desactivación ni recuperación con contrato funcional suficiente para
añadirlas aquí. El alta de vínculos académicos/grants/matrículas sigue necesitando
su procedimiento administrativo; no se inventa autovinculación.

El catálogo de roles/permisos no se inicializa por este comando. Un despliegue que
no lo tenga continuará cerrado hasta su configuración autorizada. El bootstrap
elimina la inserción manual de la primera cuenta, no sustituye toda la preparación
administrativa ni completa por sí solo RF-03.

La autoridad del operador proviene del acceso controlado al sistema de despliegue
y a sus credenciales PostgreSQL, no del parámetro confirmar-base. Ese parámetro
solo reduce errores de destino. Proteger ese acceso y registrar la intervención
son responsabilidades operativas del equipo. No protege frente a SQL privilegiado
ni crea una restricción universal de una sola cuenta administrativa para siempre.

## Uso controlado (no ejecutado sobre bases permanentes en esta entrega)

Desde la carpeta original y con configuración segura previamente autorizada:

```powershell
$env:PYTHONPATH = (Resolve-Path .\backend).Path
$correoInicial = Read-Host "Correo autorizado del primer administrador"
$nombreInicial = Read-Host "Nombre autorizado"
$baseConfirmada = Read-Host "Nombre exacto de la base configurada y autorizada"
.\.venv\Scripts\python.exe -B -m app.modules.identity.infrastructure.bootstrap_admin --correo $correoInicial --nombre $nombreInicial --confirmar-base $baseConfirmada
```

El comando exige una consola real; solicita la clave dos veces sin eco. No pasar la clave por argumentos,
variables de entorno, archivos ni tuberías. No publica JWT. Tras la inicialización,
se usa POST /api/v1/identity/auth/personal con configuración JWT válida existente.
No se ejecutan migraciones automáticamente ni se lee/escribe una política académica.

Salida: 0 creado, 1 configuración/catálogo/infraestructura no disponibles,
2 entrada/consola inválida, 3 inicialización/correo en conflicto, 130 cancelación.
Los errores no reflejan parámetros SQL, argv desconocido, hash o credenciales.

## Validación

Fecha local: 6 de noviembre de 2026, America/Bogota. HEAD de partida y final:
8b544f5d7f370076756d38b1d594fb77ab21f31b más estos cambios locales, sin commit.

| Ejecución nueva | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Aceptación de bootstrap | 13 | 0 | 0 | 0 | 1 |
| Relacionada, incluye esa aceptación | 153 | 0 | 0 | 0 | 1 |

Duraciones: 50.32 s y 97.14 s. No sumar selecciones solapadas. Advertencia conocida
de Starlette/httpx. No hubo fallos en estas dos ejecuciones, ni skip/xfail nuevos.
No se ejecutó general: no cambió código ni contratos compartidos, configuración,
modelos, migraciones o rutas. Las 2239 aprobadas/38 omitidas de Evaluation son
históricas y no se presentan como una nueva ejecución o como omisiones resueltas.

Los 13 escenarios nominales están en tests/integration/test_admin_bootstrap.py:

- Primera cuenta persistida y hash Argon2 verificado desde otra Session; login
  real sobre app.main, JWT real, alta/login docente por HTTP y separación de roles.
- Administrador existente activo/inactivo: no repetición ni recuperación.
- Catálogo ausente, ambiguo (también tabulaciones) o normalizado; ID de rol 17 en
  laboratorio para demostrar que no se presupone 3. El catálogo no lo crea el comando.
- Correo existente normalizado: no elevación de una cuenta previa.
- Dos inicializaciones concurrentes con correos diferentes: una creada y una rechazada.
- Error SQL real SELECT 1/0 después del INSERT: rollback completo, reintento válido.
- Rechazo de REPEATABLE READ para no comprobar inexistencia contra un snapshot antiguo.
- Entrada de terminal controlada y SQL real, rechazo de argv secreto/tubería,
  y confirmación de clave/destino sin crear una cuenta cuando falla.

Doce casos usan PostgreSQL 17 nuevo por escenario; uno verifica solo la negativa
del parser/consola sin BD. getpass/isatty se simulan en las pruebas de interfaz,
no las relaciones o los repositorios. No se acredita una captura manual de terminal
real ni un despliegue permanente. HTTP es ASGI/TestClient; no un servidor TLS desplegado.
No hay overrides de autenticación ni autorización en la aceptación HTTP.

La relacionada reutiliza test_main_staff_login.py, test_application.py, test_http.py,
test_security.py, test_unit_of_work.py, test_main_teacher_followup.py y
test_lab_student_journey.py. Mezcla pruebas unitarias con dobles, integración SQL
y HTTP/JWT real. No se afirma que las 153 sean todas PostgreSQL o HTTP.

Evidencia local, con comandos, HEAD, fuentes SHA-256, logs y JUnit:

```text
evidencias/rf03_bootstrap_20261107T043239Z/
  pruebas_casos_20261107T043251Z/
  pruebas_focal_20261107T043431Z/
```

Carpetas en UTC. Fuentes estables en ambas ejecuciones, sin artefactos nuevos
fuera de evidencias. Runner desactiva .env y URLs externas en el proceso de pytest;
solo habilita el fixture Docker que crea recursos propios tmpfs, verifica la base
esperada y los elimina al terminar. No usa bases compartidas ni aplica allí migraciones.

Reproducción segura de las pruebas, desde la carpeta original con Docker disponible:

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf03_bootstrap_20261107T043239Z/ejecutar_validacion.py casos
.\.venv\Scripts\python.exe -B evidencias/rf03_bootstrap_20261107T043239Z/ejecutar_validacion.py focal
```

## Antes/después, integración y brechas

Antes: la primera cuenta administrativa se insertaba mediante preparación SQL de
fixtures. Ahora: existe una operación interna ejecutable y transaccional para
crearla con contraseña explícita y hash, solo si el catálogo y la inexistencia
están acreditados. El flujo de login/alta docente posterior reutiliza la API real.

No hay endpoint nuevo ni un endpoint de bootstrap escondido en app.main. Continúan
POST /api/v1/identity/auth/personal, POST /api/v1/identity/docentes y
PUT /api/v1/identity/docentes/{id_docente}/autorizaciones, con GET /me y sus
dependencias actuales. No se amplían las autorizaciones de Cases/Scheduling.

Archivos del incremento: infrastructure/bootstrap_admin.py,
tests/integration/test_admin_bootstrap.py, este informe y la matriz vigente.
No se modifica código de Evaluation, rúbricas, Participation, Identity compartido,
app.main ni los archivos de auditoría de políticas pendientes de versionar.

RF-03 conserva PARCIAL; se cierra su dependencia técnica de primera cuenta inicial
con catálogo configurado, no toda la administración. No se cambian otros estados:
14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO. Quedan pendientes el procedimiento de
configuración del catálogo, DOCENTE ADMINISTRADOR/multirrol, permisos individuales,
gestión autorizada de asociaciones académicas y políticas de recuperación/vida
de cuentas. No se agregan reglas de caducidad, complejidad, revocación o reactivación.

Siguiente incremento recomendado: lectura administrativa privada de docentes para
operar el alta/asignación ya existentes sin conocer IDs por fuera de la API, previa
verificación de su alcance RF-03. No implementada en esta entrega. La activación,
desactivación y recuperación requieren concretar sus contratos antes de añadirlas.
