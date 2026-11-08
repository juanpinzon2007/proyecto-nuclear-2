# API privada de consentimiento — contrato previo a implementación

6 de noviembre de 2026. Composición opt-in en aplicación aislada, NO app.main.
Reutiliza Identity/JWT, ValidadorConvocatoriaScheduling, resolver SQL, fuente
documental, servicio de aceptación y sus restricciones. No aprueba el borrador.

Base nueva bajo el prefijo existente de Identity:
`/api/v1/identity/convocatorias/{convocatoria_id}/asignaciones/{id_asignacion}/consentimiento`.
No había rutas de consentimiento públicas: la ruta explicita los dos contextos
del contrato existente, sin convertirlos en prueba de identidad.

* GET base: documento exacto vigente (texto UTF-8, identidad, versión y huella).
* GET base/aceptacion: aceptación válida del titular o `aceptado=false`.
* POST base/aceptacion: id_version_documento, referencia, huella y acepta=true;
  todos deben corresponder al documento resuelto por el servidor. 200 también
  para la repetición válida; no se crea otra evidencia.

JWT estudiantil real; usuario/rol activo revalidado, UUID Scheduling inequívoco,
contexto JWT igual a convocatoria solicitada, convocatoria ACTIVA del titular,
matrícula activa y asignación/sesión/caso/versión exactas. Sin cabeceras de actor
ni student_id en solicitudes. Consentir no exige ni concede admisión, no inicia
simulación, no cambia RF-22, no crea P/I y no decide ventanas/consentimientos.
Se reutiliza la vigencia del validador de convocatoria, no una política nueva.

GET usa Session nueva, no_autoflush, locks compartidos de autorización y selector,
rollback al salir, sin flush/DML/commit; la fuente mantiene el lock transaccional
para no mezclar dos versiones. POST usa locks compatibles, serializa por cuenta
y comparte la misma Session con aceptación; un commit solamente tras completar
la operación. Ausencia de configuración/documento/selector: 503; autenticación
ausente/inválida: 401; ámbito ajeno/retirado/inválido: 403; documento sustituido
o identificador/huella incorrectos: 409; forma inválida: 422. Sin detalles SQL.
Cache-Control no-store. Los documentos sintéticos existen solo en tests.

Criterios: HTTP/JWT real/PG17 desechable; titularidad, matrícula, convocatoria,
referencias históricas, ausencia documental, aceptación explícita/idempotente,
versión obsoleta, concurrencia, rollback, GET sin DML/flush/commit, sin P/I ni
rutas nuevas en main, y preservación de revocación bloqueada durante ejecución.
No nuevas tablas ni migraciones. Proceso institucional de publicación sigue
pendiente; metadatos y huellas no prueban por sí solos aprobación real.


## Implementación y límites acreditados

`identity/api/consent.py::crear_router_consentimiento` declara los tres contratos
con esquemas estrictos (campos extra prohibidos, bool explícito, huella de 64
hexadecimales). Dependencia `obtener_estudiante_actual` intacta; nunca un actor
obtenido de cabeceras o del cuerpo. Devuelve solamente contenido/identidad del
documento y estado de aceptación propios, sin datos de aprobación/personas ajenas.

`identity/infrastructure/consent_access.py::ConsentimientoEstudiantilSQLAlchemy`
revalida cuenta/rol, vínculos, matrícula y convocatoria con el validador real de
Scheduling y su resolver. Contrasta asignación y sesión, UUID exacto de versión
y la relación real entre caso INTEGER y UUID. No usa la ?ltima versión. Delegación
a `FuenteConsentimientoSQLAlchemy`, `ServicioConsentimientoSQLAlchemy.aceptar`
y `exigir_aceptacion`, sin segundo motor de consentimiento.

Se bloquea la cuenta (exclusivo al aceptar, compartido al consultar), rol,
vínculos, matrícula, convocatoria, sesión y asignación; la fuente mantiene su
advisory compartido hasta terminar la transacción. El orden coincide con el
coordinador existente. La asignación usa SHARE para que sus campos no puedan
cambiar mientras se autoriza la aceptación. Dos POST serializan por cuenta;
el ?ndice existente respalda la unicidad. Se confirma una sola vez tras obtener
la respuesta; cualquier error revierte. GET mantiene locks compartidos cortos y
termina por cierre/rollback, no por commit; no hace DML ni flush. Esto no pretende
ser una conexión SET TRANSACTION READ ONLY, incompatible con los locks actuales.

Los tres contratos devuelven 200 al completar. No disponer de selector/documento
verificable da 503, no publica el borrador ni una versión por defecto. Una
aceptación actual ausente devuelve 200 con aceptado=false. Sustituir la versión
del servidor deja inválida la aceptación anterior para ese contexto, pero no
modifica ni elimina la evidencia anterior. Repetir la aceptación válida devuelve
el mismo identificador y fecha. acepta=false da 403; textos/actores/versiones
arbitrarios o obsoletos dan 409 o 422 según la forma. Errores de infraestructura
son 503 sin SQL, tokens ni datos sensibles. Cache-Control no-store.

No existe ruta de revocación, publicación o selección. Se conserva el guard SQL
que impide revocar la aceptación vinculada a un intento EN_CURSO. No se reinterpretan
filas legadas como prueba moderna; una referencia legada ambigua sigue cerrada.
La API exige convocatoria activa, pero consentir no equivale a ingreso ni depende
de una nueva ventana temporal inventada: se reutiliza validar_contexto existente.

## Pruebas reales y diagnósticos conservados

Archivo nuevo: `backend/tests/integration/test_consent_http.py`. PostgreSQL 17 nuevo,
JWT emitido por el login real correo/código con usuarios/roles y asociaciones SQL.
Las fixtures preparan administrativamente datos sintéticos y metadatos documentales
SOLO LAB; no son un flujo de publicación oficial ni una aprobación institucional.
No se sustituyen relaciones críticas con mocks.

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Primera aceptación HTTP | 24 | 0 | 1 | 0 | 1 |
| Aceptación HTTP final | 26 | 0 | 0 | 0 | 1 |
| Regresión relacionada | 668 | 0 | 0 | 1 | 1 |
| Repetición individual del error | 1 | 0 | 0 | 0 | 1 |
| General final | 2213 | 38 | 0 | 0 | 1 |

No se suman ejecuciones solapadas. General: 1022.09 s, 2251 casos incluyendo 38
omisiones; no se cuentan como aprobadas. Advertencia conocida Starlette/httpx.
Las 38 omisiones son los antiguos 29 casos Identity y 9 Participation condicionados
a URLs externas; los 26 nuevos escenarios PG17 sí se ejecutaron.

La primera aceptación falló en una comprobación nueva de inventario de rutas:
_IncludedRouter no expone path en esta versión de FastAPI. Se corrigió el test
para verificar los contratos OpenAPI de app.main, sin cambiar autorización o
backend para ocultar un fallo funcional. Se añadió también el caso específico
de contexto JWT distinto. Las 26 aceptaciones finales acreditan consulta vigente,
ausencia documental, aceptación/duplicado, sustitución/identificador/huella,
rechazo de actor ajeno, retirada, matrícula, vínculo ausente/ambiguo, cuenta inactiva,
GET sin DML/flush/commit, concurrencia, rollback, no P/I y guard de revocación.

En la regresión relacionada hubo un ERROR de preparación en
`test_participation_http_composition.py::test_sin_politica_no_se_confirma_participacion_ni_intento[integracion1]`:
la petición docente de creación de espacio recibió 401. Los metadatos registran
un retroceso del reloj de pared de aproximadamente cinco horas durante esa
corrida (inicio 20:17 UTC, fin 15:23 UTC). Es compatible con invalidar un JWT
anterior por nbf/iat, pero la respuesta genérica no permite demostrar la causa
exacta de ese 401. No se añadió leeway ni se modificaron JWT, tests existentes o
permisos. El nodo pasó aislado y volvió a pasar en la general completa. Su log y
XML fallidos se conservan. Riesgo externo: mantener sincronizado el reloj del
servidor y del laboratorio; no se afirma una corrección de infraestructura horaria.

Evidencias locales (comando exacto, HEAD, hashes previos, log y JUnit de cada corrida):
`evidencias/api_consentimiento_20261106T201215Z/`.
Aceptación final: `pruebas_casos_20261106T201650Z` (21.85 s).
Relacionada: `pruebas_focal_20261106T201759Z` (322.97 s).
Repetición: `pruebas_repeticion_20261106T152443Z` (7.91 s).
General: `pruebas_total_20261106T152521Z` (1022.09 s).
Los nombres temporales originales se conservan, incluso la discontinuidad horaria.
El ejecutor desactiva lectura de .env y URLs externas, habilita ?nicamente los
fixtures Docker desechables y registra estabilidad de fuentes. Comando PowerShell
reproducible desde la carpeta original:

```powershell
.\.venv\Scripts\python.exe evidencias\api_consentimiento_20261106T201215Z\ejecutar_validacion.py casos
```

Cambiar casos por focal o total reproduce esos grupos. Crea solo laboratorios
propios nuevos; no usar conexiones permanentes ni modificar fuentes durante pytest.

## Preparación del inicio: lo que sí y lo que no

| Condición | Estado real |
|---|---|
| Identidad/JWT y relaciones académicas | Reutilizados y comprobados por esta API |
| Admisión congelada | Ya implementada en Scheduling; falta componerla en la misma UoW de inicio productivo |
| Documento vigente oficial | Infraestructura SQL verificada; documento/proceso institucional auténticos todavía pendientes |
| Aceptación explícita | POST aislado, evidencia durable, pertenencia y versión; no prueba aprobación institucional |
| Validación antes del INSERT P | El coordinador existente exige aceptación con la misma Session y antes del INSERT |
| Asociación histórica P→C | Ya implementada e inmutable; no se reescribe mediante esta API |
| Creación P e inicio I atómicos | Coordinador existente probado con políticas explícitas SOLO LAB; no es habilitación productiva |

Las cuatro operaciones acreditadas sobre intentos existentes permanecen intactas.
No se ha registrado la nueva API ni provisión/inicio en app.main. No se cambian
RF-22, fórmulas, repetición o notas oficiales. El borrador continúa NO APROBADO.
Publicar metadatos/huellas en un repositorio no verifica por sí solo la competencia
de la autoridad. Falta el documento aprobado y un proceso autorizado de publicación
y selección; después se podrá revisar el montaje de esta API, separadamente de
componer admisión, consentimiento y políticas obligatorias en el inicio.
RF-12 permanece PARCIAL; no cambia otro estado RF/RNF por inferencia.

## Archivos y preservación

Nuevos: identity/api/consent.py, identity/infrastructure/consent_access.py,
tests/integration/test_consent_http.py y este informe (rutas bajo backend).
Actualizado: AUDITORIA_COBERTURA_BACKEND_20261105.md, evidencia de RF-12 sin
cambio de estado. Nuevo manifiesto: CHECKPOINT_API_CONSENTIMIENTO_20261106.json.
No nuevas tablas/migraciones, no cambios al ORM, main, borrador, Cases, Scheduling,
Evaluation ni coordinadores de Participation. Se conserva el incremento anterior.
Rama feature/backend-continuidad, HEAD 28be564; sin staging, commits o publicaciones.
El manifiesto agrupa los 29 archivos anteriores y los cuatro nuevos de esta API;
se excluye a sí mismo para evitar una huella circular y su SHA se registra aparte.
No incluye .env, respaldos, ZIP, Word, cachés ni evidencias temporales.
