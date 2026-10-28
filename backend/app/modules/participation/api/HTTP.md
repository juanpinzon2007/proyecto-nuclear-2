# Cuarto incremento: contrato HTTP PROVISIONAL

Estas rutas están preparadas para revisión del equipo. **No son un contrato
público definitivo ni están registradas en `app/main.py`.** No hay autenticación
real, adaptadores de otros módulos ni persistencia PostgreSQL conectados.
No iniciar Angular contra ellas como si el backend completo estuviera operativo.

## Correspondencia con el ER y las rutas propuestas

| Concepto | Recurso propuesto | Alcance |
| --- | --- | --- |
| `participacion` | `participations/{participation_id}` | Relación existente entre asignación y membresía del estudiante |
| `intento` | `attempts/{attempt_id}` | Una ejecución individual, con inicio, tiempo y cierre |
| `decision` | `decisions/{decision_id}` | Decisión académica del recorrido que entrega Cases |
| `paso_simulacion` | Selección del intento para una decisión | Su ID lo genera el repositorio; no lo decide el navegador |

El PDF propone `/participations/start` y `/answers/{questionId}`. Aquí el inicio
crea un **intento de una participación ya existente**, porque eso es lo que
implementa Application. No crea convocatorias ni participaciones nuevas. No se
declara que `questionId` y `decision_id` sean equivalentes ni se crean aliases.
Estos nombres, la separación POST/PUT y los cuerpos deben acordarse antes de
integrar Angular o habilitar el router. No se modifican contratos de otros módulos.

## Rutas propuestas

Todas requieren identidad obtenida en el servidor y autorización de Application.
Prefijo común: `/api/v1`.

| Método | Ruta | Solicitud | Respuesta satisfactoria |
| --- | --- | --- | --- |
| POST | `/participations/{participation_id}/attempts` | `id_consentimiento`, `id_permiso_extra` opcional | 201, resumen del intento |
| POST | `/attempts/{attempt_id}/decisions/{decision_id}` | `id_opcion`, `reflexion_estudiante` opcional | 201, selección nueva confirmada y resumen del intento |
| PUT | `/attempts/{attempt_id}/decisions/{decision_id}` | Mismo cuerpo | 200, selección existente reemplazada y resumen |
| GET | `/attempts/{attempt_id}/progress` | Sin cuerpo | 200, progreso del recorrido aplicable |
| POST | `/attempts/{attempt_id}/finish` | Sin cuerpo | 200, cierre confirmado, sin nota |
| GET | `/participations/{participation_id}/attempts/{attempt_id}/result` | Sin cuerpo | 200, evaluación pendiente o definitiva confirmada |
| GET | `/participations/{participation_id}/absence-result` | Sin cuerpo | 200, estado de la evaluación sin intento |

Las rutas son síncronas (`def`) y delegan directamente en `ParticipacionFacade`.
Los routers no calculan tiempos, recorridos, notas, permisos ni estados.
La relación entre participación e intento se valida en Application al consultar
el resultado. Un ID presente en la URL no constituye autorización.

POST de decisión registra una selección nueva. Repetirlo para una decisión ya
registrada no crea otra fila: devuelve error de dominio. PUT modifica una selección
existente, **no es un upsert**. La reflexión se reemplaza con el valor enviado;
si se omite, se transmite `None`, conforme al caso de uso existente. No hay PATCH.

Los cuerpos de inicio y selección rechazan campos adicionales. IDs del cuerpo
deben ser enteros positivos reales: no se convierten `true`, floats o cadenas.
Los IDs de URL se interpretan como enteros positivos. No hay campos para que el
cliente establezca el inicio, el límite de tiempo, estado, nivel o calificación.
El servidor obtiene todos esos datos mediante sus componentes existentes.

## Ejemplos de solicitudes y progreso

Inicio de un intento para la participación 20:

```http
POST /api/v1/participations/20/attempts
Content-Type: application/json

{"id_consentimiento": 30}
```

Registro de una selección:

```http
POST /api/v1/attempts/10/decisions/50
Content-Type: application/json

{"id_opcion": 60, "reflexion_estudiante": "Mi análisis de la situación"}
```

El resumen contiene `id_intento`, `id_participacion`, `numero_intento`, `estado`,
`inicio`, `fin` y `vence_en`. Las fechas se serializan con zona horaria.
Progreso contiene ese resumen más:

```json
{
  "decisiones_aplicables": [50, 51],
  "selecciones": [{"id_decision": 50, "id_opcion": 60}],
  "pendientes": [51],
  "total_aplicable": 2,
  "respondidas": 1
}
```

`total_aplicable` es `null` cuando Cases no conoce aún el total del recorrido.
No se infiere del número de decisiones del caso ni se añade un porcentaje.
Estos esquemas no incluyen corrección, niveles, criterios, puntajes o justificaciones.
La reflexión se guarda pero el DTO actual de progreso no la devuelve; acordar con
Angular un contrato de lectura si necesita recuperarla para editarla.

## Identidad y composición cerradas por defecto

`obtener_estudiante_actual` debe conectarse al mecanismo que implemente Alejandro
y producir `EstudianteAutenticado` desde credenciales/sesión verificadas. No se
recibe ese modelo como cuerpo ni se obtiene de `student_id`, correo, query o
`X-Student-ID`. No hay JWT alternativo. En este incremento la dependencia devuelve
503 `SEGURIDAD_NO_CONFIGURADA`, incluso si el cliente presenta un token inventado.

`obtener_facade` también depende de la identidad y devuelve 503
`INTEGRACION_NO_CONFIGURADA` hasta componer adaptadores reales. Cada endpoint
exige además su propia dependencia de identidad; sustituir únicamente la fachada
no elimina ese requisito. Identity sigue verificando propiedad y permisos en
Application, además de obtener la identidad HTTP.

Los únicos overrides están en `tests/test_api.py`, sobre una aplicación aislada.
Las pruebas utilizan `ParticipacionFacade` real y los repositorios/servicios falsos
de los incrementos anteriores. No hay fakes importados por el API ni composición
permisiva en producción. El OpenAPI de la aplicación principal sigue sin estas
rutas; el OpenAPI de prueba las identifica como provisionales y describe sus modelos.

## Lectura de resultados y modalidades

Un intento activo no permite consultar una evaluación: devuelve 409, sin datos
académicos. Si la participación/intento no existe, devuelve 404; si el usuario no
tiene autorización, 403. Esas situaciones no se convierten en evaluación pendiente.

Un recurso autorizado y cerrado sin evaluación confirmada devuelve HTTP 200:

```json
{
  "estado": "PENDIENTE",
  "id_participacion": 20,
  "id_intento": 10,
  "codigo": "EVALUACION_NO_CONFIRMADA",
  "mensaje": "Todavía no hay una evaluación persistida y confirmada."
}
```

No contiene nota ni modalidad deducida. HTTP 200 informa el estado de esta lectura;
no es 202 porque no existe un trabajo encolado ni una promesa de cálculo iniciado.
GET no invoca `evaluar_intento`, no calcula y no guarda una evaluación.

La distinción usa `EvaluacionNoConfirmada`, una subclase nueva de
`RecursoNoDisponible`, lanzada únicamente después de validar recurso, cierre y
autorización. Se conserva la compatibilidad con consumidores anteriores de la
excepción base. No se infiere el estado examinando mensajes de error.

Cuando Application recupera una evaluación persistida y confirmada, la respuesta
discriminada por `estado=DEFINITIVA` incluye IDs, `modalidad`, `referencia`,
`nota_final`, `politica_calculo` y `criterios`. La modalidad conserva COMPLETA,
PARCIAL o AUSENCIA; PARCIAL no se traduce al estado temporal VENCIDO.
Los importes Decimal se serializan como **cadenas decimales exactas**, sin pasar
por float. Por ejemplo, `"4.00"` en las fixtures representa un cálculo de prueba,
no una calificación oficial de SPS.

La lectura de ausencia usa `id_intento=null`; no crea intentos ni declara una
ausencia por el mero hecho de no encontrar intentos. El motor existente conserva
el pendiente de mapeo ER para su detalle. Por ello no hay una ausencia definitiva
publicada por ese flujo hoy: se prueba su estado pendiente y el esquema contempla
la modalidad futura sin simular la integración.

Sin motor de evaluación configurado o con una regla indispensable aún pendiente,
la API devuelve 503. No produce un cero ni un resultado definitivo sustituto.
Tampoco ofrece operaciones HTTP para aprobar políticas, generar evaluaciones o
procesar ausencias; esos puntos de ejecución backend siguen pendientes de acuerdo.

## Errores HTTP

`RutaParticipacion` traduce excepciones solo para este router, sin modificar
handlers globales ni la lógica de negocio. El formato normal de error es:

```json
{"detail": {"codigo": "INTENTO_NO_EDITABLE", "mensaje": "El intento está cerrado o su tiempo se agotó."}}
```

| Estado | Código / significado |
| --- | --- |
| 401 | Identidad no autenticada, cuando el adaptador real lo determine |
| 403 | `ACCESO_DENEGADO` |
| 404 | `RECURSO_NO_DISPONIBLE` |
| 409 | `INTENTO_NO_EDITABLE`, `CONFLICTO_ACTUALIZACION`, `EVALUACION_NO_DISPONIBLE` u `OPERACION_NO_PERMITIDA` |
| 422 | `SOLICITUD_INVALIDA` con lista de campos, o `REGLA_DOMINIO` |
| 503 | Seguridad/integración no configurada o `INTEGRACION_O_POLITICA_PENDIENTE` |
| 500 | Error inesperado propagado al límite ASGI; cuerpo genérico con debug desactivado |

La validación devuelve nombres de campos, no los valores rechazados. Los errores
de dominio tampoco reenvían mensajes internos de adaptadores. Se aplica
`Cache-Control: no-store` a éxitos y errores esperados del router.

La revisión funcional retiró la captura general de excepciones inesperadas:
TestClient normal debe propagarlas para que la suite detecte defectos. Con
`raise_server_exceptions=False` se observa el 500 genérico de ASGI sin debug,
sin texto de SQL ni secretos. Ese fallo no promete el formato JSON de los errores
esperados; el OpenAPI provisional lo indica. La observabilidad y el contrato
definitivo de errores de Identity deberán acordarse para despliegue.

## Pruebas y límites comprobados

`tests/test_api.py` utiliza TestClient, overrides de dependencias y reloj fijo.
Prueba solicitudes inválidas, identidad falsa, aislamiento de recursos, progreso,
recorridos pendientes, cierre/vencimiento, idempotencia, lectura prematura,
resultados pendientes y definitivos, precisión serializada y fallos de commit.
Comprueba también que el router permanece fuera de la aplicación principal.
No son pruebas de PostgreSQL, de autenticación real ni de extremo a extremo con Angular.

Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests backend/tests -c backend/pyproject.toml -q
```

## Coordinación necesaria antes de habilitar

- **Juan Andrés:** aprobar `decision_id` frente a `questionId`; entregar contenido
  autorizado sin corrección anticipada, recorrido y cambios válidos; proporcionar
  rúbrica/referencia histórica y mapeo académico aprobado para evaluar.
- **Alejandro:** implementar la dependencia de identidad verificada, comprobar
  propiedad/consentimiento/permisos en los ports y acordar respuestas 401/403.
  Decidir el mecanismo de autenticación institucional sin aceptar IDs del cliente.
- **Maicol:** materializar participaciones vinculadas a convocados, proporcionar
  estado/ventanas/duración, controlar repeticiones y confirmar condiciones de
  ausencia. Acordar quién solicita evaluación después de un cierre confirmado.
- **Equipo y Angular:** aprobar rutas, nombres de campos, semántica POST/PUT,
  mensajes de error, modo de consultar estados pendientes y formato Decimal como
  texto. Este incremento no modifica CORS ni añade una interfaz Angular.
- **Persistencia:** implementar las unidades de trabajo y repositorios reales,
  demostrar commit atómico, unicidad e idempotencia concurrente y resolver escala,
  referencia histórica y detalle de ausencias antes de publicar resultados.

Solo después de esas integraciones y su verificación deberá acordarse el registro
del router en `main.py`. Este incremento no lo hace y no está listo para producción.

Referencias técnicas: [APIRoute de FastAPI](https://fastapi.tiangolo.com/how-to/custom-request-and-route/)
y [overrides de dependencias en pruebas](https://fastapi.tiangolo.com/advanced/testing-dependencies/).
