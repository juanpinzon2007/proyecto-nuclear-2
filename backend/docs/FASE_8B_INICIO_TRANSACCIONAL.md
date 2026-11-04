# 8B — Inicio transaccional sobre participación existente

## Continuación 8B: composición HTTP explícita (3 de noviembre de 2026, Bogotá)

Worktree `C:\SPS\consolidacion`, rama `codex/consolidacion-backend`, sin commit.
Se extrae la composición que antes solo existía en las fixtures, sin duplicar
ServicioVinculacionSQLAlchemy ni el inicio, los autorizadores, repositorios o UoW.

### Operaciones distintas

| Ruta en la aplicación de integración | Función y resultado |
|---|---|
| POST `/scheduling/validar-ingreso` | Consulta existente: valida contexto/código/ventana; no crea P ni intento. La política global continúa cerrada. |
| POST `/api/v1/convocatorias/{convocatoria_id}/participacion` | Obtiene/crea P mediante el servicio existente. 201 nueva; 200 existente. No inicia el contador ni consume un permiso de intento. Exige política explícita de provisión. |
| POST `/api/v1/convocatorias/{convocatoria_id}/intentos` | Provisión e inicio en una sola UoW; 201. Un intento activo repetido se rechaza con 409, no se reemplaza ni duplica. |
| POST decisión / GET progreso / POST cierre | Router existente compuesto explícitamente para el intento: primera selección 201, progreso privado 200 y cierre idempotente 200. PUT sigue rechazado con 409. |
| POST intento por participación, de la composición anterior | Permanece 503 en esta app; no se abre una segunda entrada sin código/políticas por la nueva composición. |
| Resultados oficiales y ausencias | Permanecen cerrados. No se conecta Evaluation ni se publican notas. |

`api/provision_router.py::crear_router_inicio_8b` construye un APIRouter opt-in.
`crear_dependencia_vinculacion_8b` crea el servicio existente por solicitud, usando
Identity/JWT real y conexiones/reloj/políticas aportados por el servidor. Ningún
proveedor LAB se importa en producción; los tres valores predeterminados de
política son None y conservan el rechazo 503 `INTEGRACION_O_POLITICA_PENDIENTE`.
No se registra este router ni Participation en app.main.

Los cuerpos estrictos contienen asignación y código SecretStr, más consentimiento
y permiso extra opcional al iniciar. No admiten identidad, rol, estado, tolerancia,
horario o política del cliente. La respuesta no devuelve el código; validaciones
y errores usan el saneamiento existente y Cache-Control no-store.

Los locks, advisory lock por convocatoria, unicidad, revalidación del instante,
consumo de permiso y commit/rollback son los existentes. No cambia código de
Infrastructure, modelos, migraciones, DBML, Scheduling, Cases o Evaluation.

### Evidencia de aceptación

`tests/integration/test_participation_http_composition.py`: 21 escenarios nuevos.
Cuenta/roles/identidad persistentes y JWT reales; login efectivo correo/código;
Cases, grafo y publicación creados por HTTP; programación, convocatoria y cambio
de estado mediante Scheduling HTTP. Grupo/matrícula/consentimiento/puente de
asignación son datos sintéticos sembrados expresamente: no se presenta su carga
como un API académico ya implementado. Las relaciones críticas se verifican con
PostgreSQL desechable, sin mocks en los positivos.

Se acreditan ingreso sin escrituras, P idempotente, inicio combinado, primera
respuesta inmutable/progreso/cierre, referencias exactas, ausencia de políticas,
actor ajeno, convocatoria inválida/retirada, matrícula inactiva, sesión cerrada,
fronteras LAB, intento de suplantar campos, dos solicitudes HTTP concurrentes,
rollback después de INSERT de intento (revierte también P) y consumo único de
permiso adicional bajo una política explícita SOLO de laboratorio.

- Focal/regresión relacionada: **344 aprobadas, 0 omitidas/fallos/errores,
  1 advertencia conocida**, 142.02 s. Incluye las 21 nuevas.
- Comprobación histórica/contexto adicional existente: **7 aprobadas,
  0 omitidas/fallos/errores, 1 advertencia**, 9.79 s; incluye edición asignada
  cuando existe otra posterior de la misma familia. Selección distinta de la focal.
- No se ejecuta de nuevo la suite general. Las 1834 aprobadas/38 omitidas son
  el corte anterior de autoría, no un resultado nuevo de esta implementación.
- Dos pasadas iniciales se detuvieron con un error de fixture cada una: importación
  explícita de payload_valido y consulta por versión/caso incorrecta. Corregidas
  solo en preparación de pruebas; todos los logs y XML anteriores se conservan.
- Evidencias/comandos/XML: `C:\SPSBackups\8B-composicion-http-20261104T022157Z`.

### Límites académicos conservados

P01–P16 son propuestas. Antes de habilitar producción debe aprobarse la política
RF-22 (base, minutos/umbral y fronteras); aplicabilidad, versión y revocación de
consentimiento; permiso/estado inicial y momento de provisión de P; cupos y regla
de repetición excepcional. El extra positivo de la prueba no aprueba un intento
adicional para producción. Validar ingreso no sustituye autorizar la escritura.
El contrato de rutas sigue condicionado a esas decisiones y a la configuración
explícita del servidor. 8B no se declara terminada; no se inicia otra fase.

2026-11-03. Rama `feature/integracion-backend`, HEAD `3e09def`, sin commit/push/pull/merge/rebase ni cambios de rama. **8B todavía no está terminada.**

Actualización de esta misma iteración 8B: ya está implementado el tramo convocatoria
→ participación → intento en una aplicación aislada. Véase la ampliación al final.
Las secciones previas conservan el corte del incremento sobre P existente; su
pendiente de provisión queda sustituido por la implementación descrita abajo.

## Implementación funcional

`crear_facade_inicio_8b` compone la Facade, `ServicioInicio`, repositorio y UoW existentes. No reemplaza el motor de Participation ni Evaluation. Se crea una Facade y una Session nueva por solicitud.

El alcance es iniciar un intento nuevo de una **participación ya persistida y vinculada**. No crea automáticamente participación, matrícula, consentimiento ni convocatoria. No elige un estado inicial de participación ni asociaciones históricas.

Flujo comprobado:

1. El repositorio bloquea la participación (`FOR UPDATE`) antes de autorizar y contar intentos.
2. El adaptador relee y bloquea cuenta/rol, asociaciones académicas, matrícula, convocatoria, sesión y asignación. Ignora roles suministrados por el solicitante y verifica cuenta activa ESTUDIANTE, pertenencia al grupo y contexto JWT de convocatoria mediante Identity real.
3. Verifica que el consentimiento existe, pertenece al estudiante y no está revocado. Bloquea el registro. Su versión/aplicabilidad se somete a política explícita, sin aceptación automática. La aceptación debe ser anterior o igual al instante registrado.
4. Si se aporta un permiso extra, comprueba participación destinataria, profesor propietario del grupo activo y con rol DOCENTE, cantidad positiva y autorización no futura. Bloquea sus referencias y rechaza si sus usos ya alcanzaron la cantidad autorizada. Esto **no decide** cómo sumar cupos base y excepcionales; la política debe autorizarlo expresamente.
5. Bloquea el caso, la versión UUID **exactamente asignada** y su rúbrica; consulta `consultar_version_publicada` y el grafo SQL real. Rechaza versiones archivadas y recorridos no ejecutables. Nunca sustituye por la última versión.
6. Obtiene la duración de las columnas reales de asignación/sesión. Si discrepan, rechaza como regla pendiente: no elige una fuente arbitraria. Conserva la duración autorizada en el intento.
7. Reutiliza `validar_ingreso` de Scheduling para código, convocatoria ACTIVA, sesión EN_CURSO y ventana temporal del servidor. Requiere además una política explícita de asignación, consentimiento y cupos, alimentada con fechas reales, límite de ingreso, `intentos_base`, número siguiente y datos/usos del permiso.
8. El servicio existente rechaza otro intento EN_CURSO y calcula el número siguiente con los intentos ya persistidos bajo el lock de participación.
9. `Intento.iniciar` obtiene su instante del reloj inyectado. El nuevo puerto `validar_instante_inicio` vuelve a validar **ese instante concreto**, con los mismos datos bloqueados y la misma transacción, antes de insertar. Evita usar un permiso concedido justo antes del cierre para registrar después del límite.
10. El repositorio inserta y la UoW confirma una sola vez. Cualquier excepción anterior al commit revierte la escritura. Las secuencias PostgreSQL pueden dejar huecos tras un rollback; no se confunden con intentos registrados.

El orden de locks es participación → cuenta/rol/asociaciones → matrícula → convocatoria → sesión → asignación → consentimiento/permiso → caso/versión/rúbrica. Los locks se mantienen hasta commit/rollback. Para una misma participación, la segunda solicitud espera y vuelve a consultar los intentos confirmados. No hay un conteo separado seguido de una escritura en otra Session. Los guards e índices existentes siguen siendo una defensa adicional de integridad; no implementan JWT ni la aprobación académica.

## Políticas y contrato HTTP

No se agregó una política productiva por defecto. `PoliticaInicioIntento` es un contrato interno, con un DTO inmutable de hechos del servidor. `politica_ingreso=None` o `politica_inicio=None` mantiene cerrado el inicio. Un retorno distinto de `None` del proveedor se rechaza; debe autorizar mediante ejecución normal o rechazar mediante excepción. Un fallo inesperado se propaga y revierte la UoW, nunca concede acceso.

Las implementaciones `IngresoLaboratorio` e `InicioLaboratorio` están **solo en el archivo de pruebas**. Definen expresamente, para datos sintéticos, ventana [inicio, fin), consentimiento `sintetico`, asignación `programada`, límite de ingreso configurado y cupo tomado de `intentos_base`; rechazan permisos excepcionales. Esas convenciones no pasan al código productivo. No se aprobaron RF-22 ni una fórmula de repetición.

La dependencia HTTP anterior y `main.py` no cambian. La aplicación aislada de prueba registra el router existente e inyecta la nueva Facade mediante una dependencia que exige `obtener_estudiante_actual` real:

| Operación en app aislada | Resultado comprobado |
|---|---|
| `POST /api/v1/participations/{participation_id}/attempts` con JWT real y política LAB | 201, EN_CURSO, persistido |
| Repetir el POST con intento activo | 409 |
| JWT ausente o inválido | 401, sin escritura |
| Falta política obligatoria | 503, `INTEGRACION_O_POLITICA_PENDIENTE`, sin escritura |

La titularidad y demás rechazos de autorización se traducen por el router existente a 403; versión no disponible a 404; conflicto de aplicación a 409. Los fallos inesperados mantienen el tratamiento ASGI 500, sin abrir acceso ni publicar datos internos. Las pruebas HTTP usan TestClient ASGI, **no un despliegue HTTP de red**.

El contrato público de solicitud conserva `id_consentimiento` y `id_permiso_extra`. No se añadió un campo de código ni un nuevo endpoint. La fábrica interna exige `codigo_acceso` y el laboratorio suministra el código real generado para su convocatoria, sin almacenarlo en el JWT. La futura conexión HTTP productiva debe resolver expresamente cómo entregar ese código a la composición, sin recuperarlo de su hash ni usar un código global. El override de pruebas ligado a sus datos no es una dependencia productiva.

## Archivos

| Archivo | Cambio |
|---|---|
| `app/modules/participation/application/start_policy.py` | DTO de condiciones reales y puerto de política de inicio, sin valores académicos por defecto |
| `app/modules/participation/infrastructure/start.py` | Adaptadores SQL de inicio y composición con la Facade/UoW existentes; reutiliza Identity, Scheduling y Cases |
| `app/modules/participation/application/ports.py` | Ampliación interna mínima: `SchedulingPort.validar_instante_inicio` |
| `app/modules/participation/application/services.py` | Revalidación del instante del intento antes de insertarlo |
| `app/modules/participation/infrastructure/composition.py` | Implementación cerrada de ese puerto en la composición anterior; no abre su inicio |
| `app/modules/participation/tests/fakes.py` | Actualiza el doble de Scheduling al nuevo puerto |
| `app/modules/participation/tests/test_application.py` | Exige la nueva llamada de revalidación y comprueba rollback ante su fallo |
| `tests/integration/test_attempt_start.py` | 35 escenarios PostgreSQL/HTTP de inicio y controles negativos |
| `docs/FASE_8B_SCHEDULING_PARTICIPATION.md` | Aviso de actualización que distingue ambas composiciones |
| `docs/FASE_8B_INICIO_TRANSACCIONAL.md` | Este informe y comandos |

Rutas relativas a `backend/`. No se modificaron ORM, migraciones, DBML, Cases, Scheduling, Identity, Evaluation, PT-DCP-01 ni los siete patrones.

## Pruebas realmente ejecutadas

| Ejecución | Resultado |
|---|---|
| Focal inicial, Docker Desktop detenido y expectativa unitaria antigua | 54 passed, 1 failed, 25 errors; no evidencia PostgreSQL válida |
| Tras iniciar Docker y exigir la nueva revalidación en el test | 55 passed, 25 errors; puerto Docker todavía no publicado durante arranque |
| Siguiente ejecución de los 25 casos iniciales | 25 errors por una referencia ORM temporal en la **fixture nueva**; corregida conservando una referencia fuerte al caso durante el append |
| Tras corregir la fixture | 25 passed, 0 failed/errors |
| Focal ampliada: nuevo inicio y aplicación | **88 passed**, 0 skipped/failed/errors, 1 advertencia, 19.78 s |
| Regresión final relacionada, con los tres negativos adicionales de permisos | **1000 passed, 9 skipped, 0 failed, 0 errors, 1 advertencia**, 248.05 s |

La regresión final incluye los **35** casos de inicio y la nueva prueba unitaria. No se suman los resultados de distintas ejecuciones ni se presenta esta selección como suite general. Las nueve omitidas requieren conexiones externas: tres de `test_postgresql_connection.py` y seis de `test_postgresql_isolated.py`; no se consideran aprobadas. La advertencia conocida es Starlette/TestClient-httpx, sin instalar paquetes.

El incidente del puerto al iniciar Docker se observó en el helper existente. No se ocultó con skip/reintentos de tests ni se modificó aquí ese helper; los laboratorios posteriores terminaron correctamente. La disponibilidad inmediata del puerto tras un arranque frío de Docker sigue siendo un riesgo de infraestructura a vigilar, no una garantía corregida por este incremento.

**PostgreSQL real:** inicio a través de adaptadores SQL y servicios reales, segunda Session, duración histórica, versión exacta, progreso y primera respuesta posterior al inicio, respuesta inmutable, rechazo de duplicados/repeticiones, dos solicitudes concurrentes con un único intento, rollback después de INSERT, consentimiento/código/rol/matrícula/convocatoria inválidos, permisos no verificados y frontera temporal. Las políticas positivas son LAB, no mocks de persistencia ni permisos implícitos. La prueba unitaria nueva usa el doble existente para aislar el fallo de revalidación.

## Reproducir en PowerShell

Docker Desktop debe estar operativo. La inspección usa la imagen ya instalada, sin pull ni contenedores del equipo. No edite archivos mientras pytest esté ejecutándose.

```powershell
Set-Location 'C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2'
docker image inspect docker.io/library/postgres:17 --format '{{.Id}}'

$lanzador = @'
import os, subprocess, sys
e = os.environ.copy()
for nombre in ('TEST_DATABASE_URL', 'SPS_IDENTITY_TEST_URL', 'SPS_PERSISTENCE_LAB_URL'):
    e.pop(nombre, None)
e.update(SPS_TEST_POSTGRESQL='0', SPS_TEST_IDENTITY_MAPPING_DOCKER='1', PYTHONDONTWRITEBYTECODE='1')
sys.exit(subprocess.run([sys.executable, '-B', '-m', 'pytest', '-c', 'backend/pyproject.toml', *sys.argv[1:], '-q', '-rs', '--tb=short'], env=e).returncode)
'@

# Focal actual: 35 casos PG + 56 de aplicación (91 en esta versión final).
# El resultado 88 anterior corresponde a antes de añadir tres negativos de permisos.
$focal = @('backend/tests/integration/test_attempt_start.py',
           'backend/app/modules/participation/tests/test_application.py')
& .\.venv\Scripts\python.exe -B -c $lanzador @focal
```

La cantidad focal actual de 91 se deduce de los casos finales incluidos; no se presenta como una ejecución separada realizada. Todos están incluidos en la regresión final de 1000 aprobadas. Para repetir exactamente esa regresión:

```powershell
$regresion = @(
 'backend/tests/integration/test_attempt_start.py',
 'backend/app/modules/participation/tests',
 'backend/tests/integration/test_scheduling_participation.py',
 'backend/tests/integration/test_immutable_answers.py',
 'backend/tests/integration/test_cases_graph.py',
 'backend/tests/integration/test_cases_history.py',
 'backend/tests/integration/test_cases_scheduling_operations.py',
 'backend/tests/integration/test_participation_persistence.py',
 'backend/tests/integration/test_participation_8a.py',
 'backend/tests/integration/test_participation_academic_context.py',
 'backend/tests/integration/test_evaluation_persisted.py',
 'backend/tests/integration/test_evaluation_feedback.py',
 'backend/tests/integration/test_evaluation_result_storage.py',
 'backend/tests/integration/test_academic_policy.py',
 'backend/tests/identity/test_student_login_scheduling.py',
 'backend/tests/identity/test_ingress_temporal_sql.py'
)
& .\.venv\Scripts\python.exe -B -c $lanzador @regresion
```

El entorno se configura únicamente en el subproceso. No se modifica `.env`. El laboratorio existente crea contenedores nuevos con etiqueta propia y PGDATA tmpfs, verifica identidad de la base vacía y usa PostgreSQL 17 por TCP. Aplica el historial existente solo allí. Su finally elimina únicamente el contenedor cuyo ID creó. La comprobación final de `docker ps -a --filter label=sps.identity.mapping.lab=true` no devolvió contenedores. Ninguna base permanente fue utilizada o modificada.

## Estado y decisiones restantes

- Alembic: cabeza única **20261102_immutable_answers**. Metadata: **30 tablas** existentes. Sin nuevas revisiones, tablas o columnas; ER conceptual original intacto.
- `git diff --check` sin errores, con aviso LF/CRLF de `composition.py`. Cambios previos y archivos no rastreados conservados. PR #6 sin operaciones.
- El inicio transaccional está implementado y demostrado con **políticas explícitas de laboratorio**, no habilitado productivamente. Falta un proveedor aprobado para ventana de ingreso/RF-22, aplicabilidad y versión de consentimiento, estados/fechas de asignación y reglas de repetición/cupos. No se crea una capacidad de alumnos que el contrato actual no define.
- El esquema actual exige `id_consentimiento NOT NULL`. No se representa un caso de no aplicabilidad mediante consentimientos ficticios; esa alternativa necesita definición y, si procede, adaptación autorizada.
- Falta resolver la provisión autorizada de participación para un usuario sin registro previo y conectar la dependencia HTTP real, incluido el suministro seguro del código, sin un override de fixture.
- Casos con varias preguntas por escena, transiciones contradictorias, ciclos/revisitas siguen cerrados. No se alteró su semántica.
- Se conservan respuestas inmutables y persistencia histórica de Evaluation. No se publican notas oficiales ni se resuelven mapeo/agregación/redondeo pendientes.

Siguiente trabajo para cerrar **8B**, sin iniciar otra fase: aprobar/configurar esos contratos de inicio y provisión; conectar explícitamente la dependencia HTTP a fuentes reales; probar el recorrido desde identidad/convocatoria hasta inicio, respuesta y cierre con esas políticas aprobadas. Esta entrega no declara completo el Backend ni 8B, y no continúa 8C ni fase 9.

## Ampliación: convocatoria → participación → intento

Implementado `ServicioVinculacionSQLAlchemy` con dos operaciones opt-in:

- `obtener_o_crear`: acredita identidad, matrícula, convocatoria, sesión y versión publicada; devuelve la participación existente o inserta una nueva con estado inicial aportado por una política explícita del servidor. Nunca reasigna ni cambia el estado de una existente.
- `iniciar_desde_convocatoria`: ejecuta la misma vinculación y el inicio existente **en una única UoW/Session y con un solo commit**. Si falla consentimiento, política, inserción o confirmación, se revierte la participación nueva junto al intento. Una participación preexistente se conserva.

Se reutiliza `ConsultaVinculacionSQLAlchemy` después de adquirir locks sobre las fuentes del contexto. Un lock asesor transaccional por convocatoria serializa también el caso donde todavía no existe una participación. Su hash es una clave de sincronización, no una conversión de identidad. Luego se bloquean P existente, cuenta/rol/asociaciones, matrícula, convocatoria, sesión, asignación y edición/rúbrica. Se exige PostgreSQL READ COMMITTED para que la segunda solicitud observe la confirmación anterior. Se conservan los UNIQUE de convocatoria y asignación/matrícula y todos los guards históricos.

El contrato exige una asignación explícita que se verifica contra la sesión, versión y matrícula reales; no se elige arbitrariamente un grupo. La hora registrada procede del reloj inyectado. La consulta reutilizada verifica JWT contextual, cuenta/rol actuales, UUID académico persistente, código de convocatoria, estado de sesión, ventana y publicación. Crear P no autoriza por sí solo un intento ni una respuesta.

`PoliticaVinculacionParticipacion` no tiene implementación productiva por defecto. El estado `pendiente` se decide expresamente **solo en la política del test**; no se usa el default físico como permiso académico. La vinculación no fabrica consentimientos; el consentimiento del inicio se verifica por los adaptadores anteriores dentro de la misma transacción. Las políticas de ingreso/inicio siguen siendo obligatorias para iniciar.

Cambios de esta ampliación:

| Archivo bajo `backend/` | Cambio concreto |
|---|---|
| `app/modules/participation/application/provision_policy.py` | Condiciones inmutables, resultado de vinculación y contrato de autorización/estado inicial |
| `app/modules/participation/infrastructure/provision.py` | Coordinación SQL de obtener/crear y de vincular/iniciar atómicamente |
| `app/modules/participation/infrastructure/repository.py` | Consulta por convocatoria e inserción de P, sin commit propio ni upsert |
| `app/modules/participation/application/services.py` | Extrae `ServicioInicio.preparar` sin commit; `iniciar` conserva su comportamiento público y confirma como antes |
| `app/modules/participation/infrastructure/start.py` | Conecta los mismos adaptadores de inicio a la UoW del coordinador, sin Session/transacción anidada |
| `tests/integration/test_attempt_start.py` | Separa la fixture de convocatoria sin P/I de la fixture anterior con P; conserva sus 35 escenarios |
| `tests/integration/test_participation_provision.py` | 35 nuevos escenarios PostgreSQL y HTTP; rutas y políticas LAB exclusivamente aquí |
| `tests/identity/academic_identity_support.py` | Dos referencias de imagen pasan a `docker.io/library/postgres:17`: mismo PostgreSQL instalado, sin pull ni cambios de aislamiento |
| `docs/FASE_8B_INICIO_TRANSACCIONAL.md` | Actualización de este informe, sin otro documento redundante |

La corrección de imagen responde a un fallo reproducido: `inspect postgres:17` devolvía “No such image” mientras la referencia completa devolvía el ID de la imagen existente. La primera ejecución produjo **56 passed, 67 errors de preparación, 0 failed**. No se presentaron esos errores como validación PostgreSQL. Tras corregir la referencia, las pruebas focalizadas de vinculación/inicio/aplicación e infraestructura dieron **149 passed, 0 skipped/failed/errors, 1 advertencia**, 40.85 s. Ese corte tenía 32 escenarios nuevos; luego se añadieron tres negativos (consentimiento ajeno y dos fallos de proveedor).

**Regresión final relacionada: 894 passed, 9 skipped, 0 failed, 0 errors, 1 advertencia, 203.84 s.** Incluye los 35 escenarios nuevos finales. Las nueve omitidas siguen siendo tres de conexión externa y seis por `SPS_PERSISTENCE_LAB_URL`; no se consideran aprobadas. La advertencia conocida es Starlette/TestClient-httpx. Se seleccionaron Participation completa, inicio, vinculación, infraestructura de laboratorio, integración Scheduling/respuestas inmutables/grafo/persistencia/8A/contexto, login y horario; **no es la suite general ni la misma selección de 1000 del corte anterior**. No se trabajó en 8C.

El recorrido HTTP demostrado usa JWT real ya emitido para una cuenta sintética (no demuestra login con contraseña), dependencias Identity reales y PostgreSQL TCP real. No sustituye por mocks titularidad, matrícula, convocatoria, caso, grafo o repositorio. TestClient ejecuta ASGI interno, no un servidor HTTP desplegado:

| Ruta exclusivamente en la app del test | Resultado real |
|---|---|
| `POST /lab/v1/convocatorias/{id}/participacion` | 201 al crear; 200 al recuperar la misma, sin duplicar |
| `POST /lab/v1/convocatorias/{id}/intentos` | 201: crea P e intento sin precrearlos; repetición activa 409 |
| Rutas existentes de respuesta/progreso/cierre en esa app | Respuesta 201; PUT 409 `RESPUESTA_INMUTABLE`; progreso 200 privado; cierre 200 FINALIZADO |
| Ausencia/JWT inválido, convocatoria ajena, falta política, suplantación en cuerpo | 401, 403, 503 y 422 respectivamente; sin P/I nuevos |

Las solicitudes LAB contienen asignación y código; para iniciar, consentimiento y permiso extra opcional. No aceptan estudiante, rol ni estado desde HTTP. El código se transporta como `SecretStr`, se verifica contra el hash existente y no se coloca en el JWT o en las respuestas. Las rutas se definen solo en la fixture; no se registran en `app.main` ni se declara aprobado este contrato público.

Se demuestran además: lectura desde otra Session SQL; conservación de P existente; dos provisiones concurrentes con la misma P y dos inicios con un solo intento; rollback tras INSERT de P, de intento y antes de commit; fallo de inicio que no deja P nueva; negativas de cuenta/rol/matrícula/convocatoria/estado, consentimiento ajeno y proveedores no disponibles. Los mocks de fallos se limitan a pruebas negativas, nunca al recorrido positivo.

Comando focal reproducible (solo subproceso con opt-in del laboratorio; no modifica `.env`):

```powershell
Set-Location 'C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2'
docker image inspect docker.io/library/postgres:17 --format '{{.Id}}'
& .\.venv\Scripts\python.exe -B -c "import os,subprocess,sys;e=os.environ.copy();[e.pop(n,None) for n in ('TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL')];e.update(SPS_TEST_POSTGRESQL='0',SPS_TEST_IDENTITY_MAPPING_DOCKER='1',PYTHONDONTWRITEBYTECODE='1');sys.exit(subprocess.run([sys.executable,'-B','-m','pytest','-c','backend/pyproject.toml','backend/tests/integration/test_participation_provision.py','-v','-rs','--tb=short'],env=e).returncode)"
```

La prueba `test_http_recorrido_completo_sin_p_ni_i_precreados` es el recorrido completo pedido. Para repetir exactamente la regresión, use `$lanzador` definido anteriormente y estas rutas:

```powershell
$rutas = @(
 'backend/tests/integration/test_participation_provision.py',
 'backend/tests/integration/test_attempt_start.py',
 'backend/app/modules/participation/tests',
 'backend/tests/identity/test_postgresql_lab_startup.py',
 'backend/tests/integration/test_scheduling_participation.py',
 'backend/tests/integration/test_immutable_answers.py',
 'backend/tests/integration/test_cases_graph.py',
 'backend/tests/integration/test_cases_scheduling_operations.py',
 'backend/tests/integration/test_participation_persistence.py',
 'backend/tests/integration/test_participation_8a.py',
 'backend/tests/integration/test_participation_academic_context.py',
 'backend/tests/identity/test_student_login_scheduling.py',
 'backend/tests/identity/test_ingress_temporal_sql.py'
)
& .\.venv\Scripts\python.exe -B -c $lanzador @rutas
```

Estado final comprobado: sin pytest activo ni contenedores con etiqueta del laboratorio; cabeza única `20261102_immutable_answers`, 30 tablas ORM, sin nuevas migraciones ni cambios de ORM/DBML. `git diff --check` sin errores (avisos LF/CRLF); cambios previos conservados. No se usaron bases permanentes ni se hicieron operaciones Git de publicación/integración.

**Pendiente para producción:** aprobación del estado/provisión de P y proveedores autorizados de ventana RF-22, consentimiento y cupos/repetición; contrato HTTP definitivo y composición de despliegue con zona histórica acreditada. La mecánica de provisión ya no falta en el laboratorio. Permanecen cerrados los recorridos de Cases no soportados y los endpoints productivos. No se declara cerrada 8B ni se inicia otra fase.
