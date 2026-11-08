# Cuarto incremento: contrato HTTP PROVISIONAL

Actualización Fase 9A: `app/main.py` registra exclusivamente escenario, progreso
puro, POST de primera selección y POST de finalización de un intento existente.
El router completo NO está registrado. Inicio, provisión, PUT y resultados siguen
fuera de la principal. Véase [continuidad 9A](../../../../docs/FASE_9A_PARTICIPATION.md).
Todas las operaciones principales requieren configuración temporal explícita,
JWT real y autoridad persistente; no hay una zona horaria predeterminada.

La fase 8A conecta la
dependencia de autenticación a Identity real. 8B incorpora composición interna
SQL por operación; la dependencia HTTP sigue cerrada con 503.
`crear_dependencia_facade_8b` permite composición explícita para intentos existentes,
con Identity/JWT, horario de respuesta confirmado y grafo SQL reales; no está
instalada en la app principal. No habilita inicio ni resultados oficiales.
Ver [INTEGRACION_8A.md](../INTEGRACION_8A.md).
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
implementa Application. No crea convocatorias ni participaciones nuevas.
La autorización UUID posterior de 8B establece que `decision_id` referencia
físicamente `pregunta.id` y `id_opcion` referencia `opcion_respuesta.id`; ambos UUID
reales. Esto no equipara la pregunta a toda la entidad académica decisión/criterio.
Estos nombres, la separación POST/PUT y los cuerpos deben acordarse antes de
integrar Angular o habilitar el router. No se modifican contratos de otros módulos.

## Rutas y composiciones

Todas requieren identidad obtenida en el servidor y autorización de Application.
Prefijo común: `/api/v1`.

| Método | Ruta | Solicitud | Respuesta satisfactoria |
| --- | --- | --- | --- |
| GET (principal, condicionado) | `/attempts/{attempt_id}/current-scenario` | Sin cuerpo ni parámetros query | 200, escenario/pregunta actuales; FIN sin contenido; 503 si falta zona/configuración |
| GET (principal, puro) | `/attempts/{attempt_id}/progress` | Sin cuerpo ni query | 200, estado efectivo/progreso sin guardar vencimiento |
| POST (solo integración aislada) | `/participations/{participation_id}/attempts` | `id_consentimiento`, `id_permiso_extra` opcional | 201, resumen del intento |
| POST (principal e integración) | `/attempts/{attempt_id}/decisions/{decision_id}` | `id_opcion`, `reflexion_estudiante` opcional | 201, selección nueva confirmada y resumen del intento |
| PUT (obsoleto) | `/attempts/{attempt_id}/decisions/{decision_id}` | Mismo cuerpo | 409, `RESPUESTA_INMUTABLE` para intento activo autorizado; nunca crea ni reemplaza |
| GET (integración aislada, comportamiento anterior) | `/attempts/{attempt_id}/progress` | Sin cuerpo | 200, progreso; puede confirmar vencimiento |
| POST (principal e integración) | `/attempts/{attempt_id}/finish` | Sin cuerpo | 200, cierre confirmado, sin nota |
| GET (solo integración aislada) | `/participations/{participation_id}/attempts/{attempt_id}/result` | Sin cuerpo | 200, evaluación pendiente o definitiva confirmada |
| GET (solo integración aislada) | `/participations/{participation_id}/absence-result` | Sin cuerpo | 200, estado de la evaluación sin intento |

Las rutas son síncronas (`def`). La principal delega escenario en
`ConsultaEscenarioActualSQLAlchemy`, progreso en `ConsultaProgresoSQLAlchemy` y
POST de selección/cierre en `ParticipacionFacade`. El router de integración
aislada conserva su progreso anterior mediante Facade, que puede persistir el
vencimiento. Son composiciones distintas: no se monta ese GET escritor en main.
Los routers no calculan tiempos, recorridos, notas, permisos ni estados.
La relación entre participación e intento se valida en Application al consultar
el resultado. Un ID presente en la URL no constituye autorización.

POST de decisión registra una selección nueva. Repetirlo para una decisión ya
registrada devuelve 409 `RESPUESTA_INMUTABLE`, incluso con la misma opción.
La aclaración posterior de la profesora prohíbe modificar cualquier respuesta.
PUT conserva validación/autenticación/autorización y se rechaza: no es un upsert.
Tampoco se permite cambiar la reflexión ni eliminar una selección. No hay PATCH.
El registro sobre intento cerrado/vencido mantiene 409 `INTENTO_NO_EDITABLE`.
La composición principal exige configuración temporal válida (503 si falta),
además de identidad y autorización persistentes. No habilita inicio ni resultados.

Los cuerpos de inicio y selección rechazan campos adicionales. IDs del cuerpo
de participación/intento siguen siendo enteros positivos reales. Las referencias
a Cases usan UUID. Se conservan INTEGER en esquemas de pruebas antiguas, pero el
adaptador SQL real los rechaza; nunca se convierten entre INTEGER y UUID.
No se convierten `true`, floats o cadenas numéricas del cuerpo a IDs enteros.
No hay campos para que el
cliente establezca el inicio, el límite de tiempo, estado, nivel o calificación.
El servidor obtiene todos esos datos mediante sus componentes existentes.

## Ejemplos de solicitudes y progreso

Los ejemplos INTEGER de decisiones que siguen son antecedentes de los dobles de
prueba del cuarto incremento; no identifican preguntas UUID reales de Cases.
En 8B los clientes deben utilizar los UUID recibidos de Cases. Si no existe un
contrato de recorrido, `decisiones_aplicables`, `pendientes` y `total_aplicable`
son `null`: las selecciones y `respondidas` siguen procediendo de PostgreSQL.

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

`obtener_estudiante_actual` utiliza las dependencias de Alejandro para JWT, cuenta
activa, rol ESTUDIANTE vigente y UUID académico Scheduling inequívoco. Produce
`EstudianteAutenticado` desde credenciales/sesión verificadas. No se
recibe ese modelo como cuerpo ni se obtiene de `student_id`, correo, query o
`X-Student-ID`. No hay JWT alternativo. Sin Bearer responde 401; token inválido
responde 401 cuando JWT está configurado; sin infraestructura/configuración
requerida responde 503. Cuenta sin vínculo: 403; vínculo ambiguo: 503.
Su campo interno `id_estudiante` conserva el INTEGER de la cuenta, separado de
`id_estudiante_scheduling` UUID y del contexto de convocatoria firmado.

`obtener_facade` también depende de la identidad y devuelve 503
`INTEGRACION_NO_CONFIGURADA` hasta componer adaptadores reales. Cada endpoint
exige además su propia dependencia de identidad; sustituir únicamente la fachada
no elimina ese requisito. La autorización del agregado mediante IdentityPort
sigue pendiente: autenticar la cuenta no demuestra titularidad de una participación.

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
- **Alejandro:** mantener JWT y resolver ya reutilizados; completar el contrato
  de propiedad/consentimiento/permisos del agregado sin equiparar UUID y membresía.
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

## Consentimiento versionado: actualización interna condicionada

Las rutas de provisión e inicio desde convocatoria continúan exclusivamente en
composición aislada, fuera de app.main. No cambia el cuerpo HTTP ni se añade
aceptación productiva. La fábrica privada admite fuente_consentimiento=None;
sin fuente vigente del servidor no se crea una P nueva. El cliente no puede
inyectar esa fuente ni una política por JSON.

Antes de INSERT P se verifica aceptación propia, no revocada/no futura y versión
actual inequívoca. Inicio ausente o política rechazada también impiden INSERT.
La política de inicio es pura, recibe id_participacion=None antes de crear P y se
revalida con su PK real antes de I; no consume permisos en la prevalidación.
Se mantienen la misma UoW, locks, grafo y control de duración/versión históricos.
La recuperación de P existente conserva su historia; no es creación autorizada
por un consentimiento implícito ni permiso de repetición.

El servicio interno de aceptación requiere True explícito y referencia/huella
coincidentes con el documento resuelto en servidor. No hace commit; no hay ruta
pública ni fuente oficial. Las pruebas de aceptación usan SQL real y documentos
LAB; no justifican instalar estos routers en main. Ver
`backend/docs/CONSENTIMIENTO_E_INICIO_INTERNO.md` para contratos pendientes.


## Admisión aprobada de Scheduling (sin abrir inicio)

Scheduling publica espera y comprobante en su propio router. La validación de
ingreso de main usa AdmisionSQLAlchemy y exige concesión individual congelada.
ConsultaIngresoSQLAlchemy puede recibir ese mismo puerto del servidor; no se
reinterpreta una política LAB como autorización productiva. No cambian cuerpos
HTTP de Participation, sus cuatro rutas acreditadas ni cierres de provisión/inicio.
Ver backend/docs/SALA_ESPERA_ADMISION_DISENO.md. La fuente oficial de consentimiento
y el enlace histórico P→aceptación siguen pendientes; este incremento no los simula.
