# Fase 9: recorrido vertical estudiantil verificado

Fecha: 4 de noviembre de 2026 (America/Bogota).
Worktree: `C:\SPS\consolidacion`, rama `codex/consolidacion-backend`.
Base: `368b07308a0472804d7e5710e599ab43396fbb4d` más los dos archivos nuevos
de esta entrega, sin commit. No hay cambios productivos ni de esquema.

## Alcance y preparación

Se reutilizó `test_participation_http_composition.integracion`: PostgreSQL 17
nuevo, migrado mediante Alembic; HTTP ASGI con TestClient, JWT y repositorios
reales. No es una prueba contra un servidor desplegado ni contra una base permanente.

Preparación de laboratorio: cuentas, roles, permiso de autoría, asociaciones
académicas, asignación docente-espacio, grupo, matrícula, consentimiento y puente
de asignación. Los contenidos y el grafo se crean/publican mediante Cases API;
Scheduling programa, convoca e inicia la sesión por API. El token del docente se
emite con el componente JWT real para una cuenta sintética: NO acredita un login
docente por credenciales. El estudiante sí realiza login HTTP real correo/código.

`IngresoLaboratorio`, `InicioLaboratorio` y `VinculacionLaboratorio` son políticas
explícitas solo de pruebas. No aprueban RF-22, consentimiento/revocación, provisión
ni repetición. No sustituyen la comprobación SQL de identidad, contexto,
convocatoria, matrícula, versión o titularidad.

## Recorrido ejecutado

Test nuevo único:
`backend/tests/integration/test_student_vertical_journey.py::test_recorrido_vertical_desde_login_hasta_cierre_sin_publicar_resultados`.

| Paso real | Resultado observado |
| --- | --- |
| POST `/api/v1/identity/auth/estudiantes`, correo/código del convocado | 200; JWT sin imprimirlo |
| GET `/api/v1/identity/me` con ese JWT | 200 |
| POST `/scheduling/validar-ingreso` | 200; cero participaciones e intentos |
| POST `/api/v1/convocatorias/{id}/intentos` con cuenta ajena | 403; cero escrituras |
| Mismo POST con titular y consentimiento de laboratorio | 201; participación e intento vinculados atómicamente |
| Repetir inicio | 409; una participación y un intento |
| Nueva Session SQL | Convocatoria/sesión/asignación/version UUID exactas e intento vinculado |
| GET `/api/v1/attempts/{id}/progress` con cuenta ajena | 403 |
| GET `/api/v1/participations/{p}/attempts/{i}/result` activo | 503; composición de resultados cerrada |
| POST `/api/v1/attempts/{i}/decisions/{q}` primera selección | 201 |
| PUT de la misma pregunta con otra opción | 409; selección original conservada |
| POST de la pregunta siguiente, validada contra el grafo SQL | 201 |
| GET progreso del titular | 200; dos respondidas, cero pendientes; sin corrección, justificación, puntaje, nota o código |
| POST `/api/v1/attempts/{i}/finish` ajeno | 403 |
| POST cierre titular y repetición | 200 y 200; FINALIZADO |
| GET resultado tras cerrar | 503; cierre no equivale a nota |
| Otra Session SQL | FINALIZADO, dos respuestas, opción original, cero resultados |
| Consulta interna `consultar_evidencias_8c` del MISMO intento | Dos respuestas y rúbrica de la versión exacta, con `version_regla` |
| `crear_evaluacion_8c(...).previsualizar_intento` sin mapeo sintético | `PoliticaEvaluacionPendiente`: falta mapeo aprobado; cero resultados persistidos |

El contexto de la consulta interna 8C se obtiene nuevamente del JWT y del
repositorio mediante `obtener_usuario_actual`; no se acepta una cuenta del cliente.
No se añade una ruta HTTP de resultados ni un motor de evaluación.

Limitación de presentación: las preguntas/opciones provienen de la respuesta de
autoría usada en la preparación. Se demuestra navegación y validación reales,
no una nueva API estudiantil de descarga del contenido del escenario. Las rutas
GET de Cases existentes siguen protegidas como operaciones docentes.

## Regresión reutilizada

- `test_participation_http_composition.py`: políticas ausentes 503, inicio ajeno,
  matrícula/convocatoria/sesión inválidas, concurrencia HTTP sin duplicados,
  rollback tras INSERT y versión asignada conservada.
- `test_attempt_start.py`, `test_participation_provision.py`: transacción de
  inicio/vinculación, titularidad, persistencia, permisos y concurrencia.
- `test_scheduling_participation.py`: sesión EN_CURSO, inicio inclusivo y fin
  exclusivo, zonas equivalentes, duración individual histórica, cierre concurrente,
  relectura de autoridad y rechazo de recorridos no soportados.
- `test_immutable_answers.py`: integridad SQL, concurrencia y rollback de respuestas.
- `test_evaluation_persisted.py`, `test_evaluation_result_storage.py`: evidencia
  histórica, referencias cruzadas rechazadas, cálculo y persistencia técnica SOLO
  con reglas de laboratorio versionadas, rollback e inmutabilidad. Esos resultados
  se prueban por separado; no se atribuyen al nuevo intento vertical.
- `test_academic_policy.py`: escala 0–100, pesos exactos iguales, pendientes cero
  al vencer sin selecciones ficticias y bloqueo de mapeos/redondeos no aprobados.
- Login Scheduling real y suite de Participation existente. Las pruebas unitarias
  con fakes y SQLite no se presentan como garantía de locks PostgreSQL.

## Resultados auténticos

Evidencia externa: `C:\SPSBackups\fase9-estudiantil-20261104T213047Z\`.
Cada ejecución conserva comando, HEAD, estado Git, huellas de fuentes, consola,
JUnit XML y resumen. No se suman las selecciones solapadas.

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
| --- | ---: | ---: | ---: | ---: | ---: |
| Primera focal, 213142Z | 0 | 0 | 1 | 0 | 2 |
| Focal corregida, 213215Z | 1 | 0 | 0 | 0 | 1 |
| Regresión relacionada inicial, 213236Z | 650 | 9 | 0 | 0 | 1 |
| Focal final con enlace interno 8C, 213557Z | 1 | 0 | 0 | 0 | 1 |
| Regresión relacionada FINAL, 213616Z | **674** | **9** | **0** | **0** | **1** |

La primera expectativa errónea fue HTTP 403 al adelantar el reloj una hora; el
dominio vencía el intento y respondía correctamente 409. Se retiró ese salto del
recorrido exitoso; no se modificó producción. La temporalidad sigue cubierta por
los tests existentes, incluidos frontera, vencimiento y conservación de respuestas.
JUnit se configuró como legacy para admitir propiedades de evidencia sin el aviso
de incompatibilidad xunit2. La advertencia final es Starlette/TestClient-httpx.

Las nueve omisiones corresponden a tres pruebas antiguas de conexión externa y
seis dependientes de `SPS_PERSISTENCE_LAB_URL`; no se consideran aprobadas.
El nombre `general` del ejecutor de esta entrega significa regresión RELACIONADA
(selección explícita en el script), no suite global del Backend.

## Reproducción segura en PowerShell

```powershell
Set-Location C:\SPS\consolidacion
# Script local conservado junto a las evidencias; no requiere cambiar .env.
& C:\Python313\python.exe -B C:\SPSBackups\fase9-estudiantil-20261104T213047Z\ejecutar_validacion.py focal
# Regresión relacionada, no suite global:
& C:\Python313\python.exe -B C:\SPSBackups\fase9-estudiantil-20261104T213047Z\ejecutar_validacion.py general
# Solo visualizar los pasos ya acreditados, sin repetir pruebas:
Get-Content C:\SPSBackups\fase9-estudiantil-20261104T213047Z\recorrido_http.json
```

El ejecutor elimina del entorno hijo las URLs/configuraciones externas de BD,
no admite .env en el worktree, habilita únicamente el laboratorio Docker propio,
desactiva los tests antiguos con conexiones externas, verifica fuentes estables y
redacta códigos/JWT/credenciales en los registros. El fixture identifica su propio
contenedor, comprueba TCP/base aislada y usa tmpfs; elimina solo su ID al finalizar.
No se instalan dependencias ni se conectan bases del equipo.

## Disponibilidad y bloqueos

**Principal:** Identity, Cases y Scheduling siguen registrados como antes. El login
estudiantil dispone de composición real, condicionada a configuración y datos
válidos del despliegue. `/scheduling/validar-ingreso` conserva política ausente por
defecto (503). Participation no está registrado globalmente. Esta entrega no
acredita un despliegue ni cambia disponibilidad productiva.

**8B acreditada en aislamiento:** login, ingreso sin escritura, inicio combinado,
autoridad persistente, versión exacta, grafo soportado, respuestas inmutables,
progreso privado, cierre, concurrencia y rollback. Pendientes productivos:
contratos aprobados de ingreso RF-22, consentimiento/revocación, provisión e
intentos adicionales, más composición limitada de rutas seguras. Ciclos y varias
preguntas por escena siguen cerrados. No se infiere aprobación de P01–P16.

**8C:** el mismo intento cerrado llega a la lectura histórica autorizada. Escala,
igualdad de pesos y ceros por vencimiento están implementados, pero no resuelven
el mapeo de niveles ni la agregación de preguntas; tampoco el redondeo cuando
sea necesario. Falta precisar cierre voluntario incompleto, ausencia oficial y
consolidación de múltiples intentos. No se genera/publica una nota ni se conecta
automáticamente un resultado de laboratorio a HTTP.

RF relacionados: RF-01 y soporte de RF-10/11/12 demostrados en este recorrido;
RF-13/14/24 con evidencia técnica y barreras académicas explícitas. No se declara
cumplimiento total de estos RF por una prueba aislada.

Siguiente incremento recomendado, sin implementarlo: acordar y conectar una
lectura HTTP estudiantil del contenido del escenario actual, usando contexto JWT,
intento autorizado y versión exacta, con lista blanca que excluya corrección,
valoraciones y rúbrica. Es una brecha técnica integrable sin decidir fórmulas ni
RF-22. La habilitación productiva del inicio continúa dependiendo de las
aprobaciones indicadas. No se continúa otro módulo en esta entrega.
