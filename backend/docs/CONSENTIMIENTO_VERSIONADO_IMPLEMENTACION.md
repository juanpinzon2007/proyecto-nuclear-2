# Consentimiento versionado: decisión técnica previa al código

Se reutilizan DocumentoConsentimiento, FuenteConsentimiento, el servicio de
aceptación y la UoW de Participation. El alcance actual autoriza infraestructura
interna; no aprueba el borrador, autoridad institucional ni publicación productiva.

La propuesta anterior ponía el selector en asignacion_caso. Se descarta esa
ubicación: bd205_asignacion valida PUBLICADO en cada UPDATE y bloquea la versión
del caso. No se cambia esa función. El selector será una tabla técnica separada,
con PK/FK id_asignacion y FK id_version_documento. El contexto por asignación es
el parámetro del puerto existente, no una regla global de institución inferida.
Ausencia del selector falla cerrada. No se infieren defaults o MAX(version).

Dos tablas necesarias: documento_consentimiento_version y
seleccion_consentimiento. Son adaptaciones físicas autorizadas en este incremento
de infraestructura, no un cambio del DBML académico original. Documentos solo
publicados, inmutables, con bytes/texto y huellas separadas, autoridad/evidencia de
aprobación, operador y fechas explícitos. Ningún dato institucional se instala.

Consentimiento incorpora referencia FK documental/evidencia explícita y huella;
Participation incorpora FK a la aceptación utilizada. Columnas nullable preservan
legado sin backfill. Fuente SQL nunca acepta un registro legado sin prueba. Las
composiciones históricas LAB no constituyen consentimiento institucional.
Los enlaces presentes son inmutables y se comprueban en la misma transacción.
No se fuerza un enlace retrospectivo ni una igualdad universal para intentos
históricos/repeticiones no autorizadas. Nuevos flujos modernos conservan el mismo
consentimiento durante la creación combinada de P/I.

Fuente SQL comparte un advisory lock por asignación con la selección del servidor;
el lock persiste hasta terminar la UoW, también cuando aún no hay selector.
Cambiar el selector no actualiza la asignación ni la P existente. El servicio
resuelve vigente antes del INSERT P; los guards verifican titularidad/referencias
de vínculos no nulos. NULL legado no se presenta como evidencia verificada.
No se promete impedir SQL privilegiado que desactive controles o inserte formas
legadas aún admitidas por transición; los endpoints productivos quedan cerrados.

Publicación/selección son operaciones internas de repositorio, no concesiones de
permisos ni APIs administrativas. Verificar la autenticidad institucional de la
aprobación sigue siendo responsabilidad del proceso autorizado de publicación;
una huella o un rol de software no prueba esa autoridad. No se compone una fuente
por defecto. Se probará solo PG17 nuevo/destructible y SQLite aislado para DDL.


## Auditoría resuelta y composición interna

El incremento anterior dejó como propuesta una tabla documental y un selector en
A. La autorización actual permite la infraestructura interna; al auditar el guard
bd205_asignacion se resuelve técnicamente con selector separado, sin excepciones
al guard ni UPDATE de A. Se pasa de 31 a 33 tablas físicas, no se modifica el ER
académico original de 28 entidades. No se implementa un sistema de publicación
institucional ni se atribuye esa autoridad al rol ADMINISTRADOR.

### Persistencia implementada

- documento_consentimiento_version: INTEGER PK; referencia <=30 UNIQUE;
  documento_id/version UNIQUE; bytes originales y texto separados, sus SHA-256;
  autoridad/evidencia/fecha de aprobación, SHA-256 de evidencia, operador FK usuario,
  fecha de publicación y vigente_desde explícitos. Sin datos ni defaults de versión.
  CHECK de campos no vacíos y fechas; trigger verifica hashes en PG17 y rechaza
  UPDATE/DELETE. TRUNCATE también se rechaza. SHA-256 no autentica a una institución:
  los datos deben proceder de un proceso autorizado que todavía no se publica.
- seleccion_consentimiento: PK/FK id_asignacion, FK a versión documental, operador
  FK usuario y fecha. Una selección explícita por contexto, muchas asignaciones
  pueden reutilizar un documento. No cambia la pertenencia ni la versión de Cases.
  La ausencia o selección aún no aplicable falla cerrada; no se usa MAX ni default.
- consentimiento: id_version_documento nullable FK, aceptacion_explicita nullable,
  huella_aceptada nullable; CHECK todo legado NULL o evidencia completa True/hash.
  Índice UNIQUE parcial estudiante/documento explícito no revocado. No se convierte
  legado por UPDATE. La evidencia nueva se protege contra modificación/eliminación.
- participacion: id_consentimiento nullable FK. El escritor existente exige id real
  antes de INSERT y la provisión pasa la aceptación ya validada. Se conserva al
  recuperar P; no se sustituye ni se completa automáticamente una P legada.

### Reutilización y garantías

RepositorioDocumentosConsentimientoSQLAlchemy no hace commit ni concede permisos;
recibe publicación/selección de una composición interna explícita. Su lectura
histórica conserva definición e identifica que no es la consulta de vigencia.
FuenteConsentimientoSQLAlchemy implementa el puerto actual y valida las tres
huellas al recuperar. No se configura automáticamente en producción.

ServicioConsentimientoSQLAlchemy conserva actor/rol revalidados, True explícito,
referencia/hash contrastados con servidor, reloj y Session prestada. Con documento
SQL conserva evidencia y devuelve el mismo id ante repetición inequívoca válida.
Una fila legada que solo comparte etiqueta no se declara explícita. El contrato
externo/LAB anterior se conserva para las pruebas históricas aisladas; sus éxitos
NO prueban consentimiento institucional y no se instalan como fuente productiva.

ServicioVinculacionSQLAlchemy admite crear_fuente_consentimiento(Session) privado
del servidor: la fuente SQL usa la MISMA UoW, no otra conexión de lectura. Valida
antes del INSERT y guarda el enlace en esa escritura. RepositorioParticipacion
exige id_consentimiento; ni la fachada ni el servicio hacen un segundo commit.
IdentityInicioSQLAlchemy revalida una aceptación moderna contra el selector
actual con el reloj inyectado, tanto en inicio combinado como en inicio directo.
P moderna con documento sustituido queda cerrada, sin reescribir su enlace.
P legada sin enlace no se reclasifica al aportar una aceptación moderna: aplicación
y guard de INSERT de I lo rechazan. No se inventa una política de repetición.

### Concurrencia

Fuente y selector comparten un advisory lock transaccional por id_asignacion,
compartido para resolver y exclusivo para seleccionar. Antes se adquiere KEY SHARE
de A, necesario también para la FK, compatible con el orden de provisión que ya
tiene A bloqueada. No se evalúa bd205_asignacion por leer/bloquear A.
El trigger de selector usa try-lock para rechazar DML que ya tenga la fila del
selector bloqueada en orden inverso (55P03 reintentable con rollback completo).
Las operaciones normales adquieren el advisory antes de escribir el selector.
Esto evita depender de timestamps para ordenar publicación y creación.

Si P gana primero, publicación espera y P conserva su C/documento original; si
selección gana primero, P revalida y rechaza una aceptación obsoleta antes de
insertar. Los tests observan pg_stat_activity.wait_event_type=Lock, no esperan
un tiempo fijo para declarar concurrencia. Inicio y revocación se serializan
sobre C; inicio confirmado impide revocación, revocación confirmada impide I.
La revocación no tiene nuevo endpoint ni política general fuera del caso dado.

### Alcance exacto de la protección SQL y del legado

Los vínculos NO nulos validan titular/fecha/no revocación; si la aceptación es
moderna se comprueba que el selector coincida con su documento. Los guards
impiden cambiar el enlace de P y la evidencia publicada/aceptada. Inicio moderno
no permite otro C ni una P sin enlace. SQL no introduce automáticamente historia.

NULL sigue permitido para filas/formas legadas durante la transición. No se
promete que todo INSERT SQL manual NULL represente una participación autorizada:
solo los escritores de aplicación actualizados garantizan enlace previo. No hay
ruta pública que use esos escritores sin fuente/políticas obligatorias. La fuente
SQL no acepta legado como prueba moderna. Usuarios capaces de deshabilitar
triggers o alterar funciones no están cubiertos por una promesa de inmutabilidad.
Las fechas antiguas naive conservan FechasPersistencia y configuración de zona;
no se convierten datos ni se introduce una zona predeterminada.

## Migración

20261106_consent_versions → 20261105_waiting_admission. Dos tablas, tres columnas
nullable en C y una en P, sus FK/CHECK/índice; cinco funciones y ocho triggers
propios. No sustituye ni edita migraciones existentes ni guards de Cases.
No hay UPDATE/backfill de datos en upgrade. Los valores nulos no se completan con
el borrador, con un intento posterior ni con MAX(fecha). El downgrade bloquea las
tablas afectadas y se niega si borraría publicaciones/evidencias/vínculos; en vacío
retira únicamente sus objetos y columnas. Se prueba solo en PG17 desechable.

SQLite de pruebas tiene DDL real auxiliar (columnas, FK, CHECK e índices) para
comparar metadata, sin afirmar que reproduce locks o triggers PG. Las revisiones
históricas mantienen sus padres/contadores; fixtures de ORM actual sobre revisiones
antiguas declaran explícitamente columnas auxiliares, sin estampar la revisión
nueva ni atribuirle sus garantías. El test nuevo de upgrade de datos legados usa
reflexión REAL del esquema anterior, sin esas columnas auxiliares, y comprueba C/P
antes/después y su downgrade sin fabricar asociaciones.

## Pruebas y trazabilidad actual

Evidencia: evidencias/consentimiento_versionado_20261106T034258Z/. Cada ejecución
guarda comando, configuración aislada, HEAD, huellas, log, JUnit y resultado.

- Primera aceptación: 2 aprobadas y 14 errores de fixture por reutilizar referencia
  global SQL-LAB-1. Se aisló la identidad documental por contexto de laboratorio;
  no se cambió la restricción UNIQUE.
- Segunda: 15 aprobadas y 1 rechazo de la política LAB que solo aceptaba la etiqueta
  antigua. La política de pruebas admite ahora una referencia explícita con el
  mismo default histórico, sin cambiar reglas productivas.
- Aceptación ampliada: 23 aprobadas y 1 diferencia de traducción de error de
  revocación (503 genérico en lugar de rechazo de acceso). Se corrigió la distinción
  entre aceptación denegada y fuente pendiente.
- Relacionada: 257 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia, 153.38 s,
  pruebas_diagnostico_20261106T035621Z.
- Focalizada: 639 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia, 278.13 s,
  pruebas_focal_20261106T040600Z (antes de las dos últimas protecciones de legado).
- Aceptación final: 27 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia,
  26.38 s, pruebas_casos_20261106T041141Z.
- General de esta implementación: pendiente hasta finalizar la ejecución actual.

Los documentos, autoridades y aprobación de las pruebas son SINTÉTICOS de LAB;
se prueba persistencia y controles técnicos, no un proceso institucional aprobado.
No sumar ejecuciones solapadas ni contar omisiones como aprobaciones.

## Bloqueos productivos conservados

Faltan documento/aprobación reales, representaciones aprobadas, un proceso de
publicación/selección autorizado y su composición productiva. La aceptación HTTP
futura debe autorizar además el ámbito de convocatoria/matrícula/asignación antes
de presentar el documento; el servicio interno de actor no sustituye esa frontera.
La infraestructura no decide la institución/programa aplicable automáticamente.

Se conservan los endpoints principales de intentos existentes; NO se registran
aceptación, provisión, inicio o notas oficiales. RF-22/sala de espera intactos.
RF-12 sigue PARCIAL; Evaluation y repetición mantienen sus políticas pendientes.
No se publica un borrador ni se ejecuta DDL sobre una base permanente.


### Cierre adicional de aislamiento (comprobación reproducida)

Después de la primera general verde se comprobó una precondición técnica del
nuevo adaptador. Una Session con snapshot previo REPEATABLE READ/SERIALIZABLE
seguía leyendo selección 1 tras confirmarse selección 2 desde otra Session.
El advisory no renueva un snapshot. Diagnóstico: dos fallos reproducidos en
pruebas_seguridad_20261106T043519Z; XML conserva la propiedad
version_devuelta_por_snapshot=1 en ambos casos, mientras otra Session verificó 2.

FuenteConsentimientoSQLAlchemy exige ahora READ COMMITTED para consulta de vigencia,
igual que la UoW existente de provisión. Otros modos cierran con IntegracionPendiente;
no se anuncia soporte que dependa de una instantánea vieja. La recuperación
histórica inmutable no se confunde con esta consulta de actualidad.

Primera general: 2185 aprobadas, 38 omitidas, 0 fallidas/errores, 1 advertencia,
992.12 s, pruebas_total_20261106T041430Z. Es anterior a esta última protección.
Se refinaron además precondiciones sin cambiar cantidad: ausencia sin filas y
legado con la misma referencia textual, para probar que la etiqueta no basta.
Aceptación con aislamiento ya corregido: 29 aprobadas, 0 omitidas/fallidas/errores,
1 advertencia, 26.98 s, pruebas_casos_20261106T043632Z. General definitiva pendiente
de la nueva ejecución, no se atribuye el histórico a la protección todavía no probada
por toda la suite. No sumar ejecuciones solapadas.


## Resultado definitivo

General final **2187 aprobadas, 38 omitidas, 0 fallidas, 0 errores, 1 advertencia
Starlette conocida**, 993.01 s, final UTC 2026-11-06T04:55:59.905768+00:00. Timestamp
registrado en resultado.json: pruebas_total_20261106T043913Z. Código y fixtures
estuvieron estables durante cada ejecución. La general primera 2185 no se suma
ni sustituye ésta. Las 38 omisiones son las 29 antiguas de Identity y las 9 de
Participation condicionadas a URLs externas; no acreditan resultados positivos.
Todas las 29 nuevas aceptaciones se ejecutaron sobre PG17 desechable.

Se conserva el historial de diagnósticos y sus XML, incluidos los dos snapshots
que devolvían 1 después de confirmarse 2. La aceptación final es 29/0/0/0,
pruebas_casos_20261106T043632Z; la general final incluye ambas precondiciones
refinadas de ausencia/legado y la restricción de aislamiento. No hubo skip/xfail
nuevos ni eliminación de tests para esconder fallos.

Una etiqueta legada coincidente nunca se interpreta como evidencia. Su reutilización
sin prueba sigue cerrada y cualquier conciliación exige una acción explícita y
fuente verificable; no se actualizan filas antiguas ni enlaces P a partir de I.
No se anuncia idempotencia automática para referencias legadas ambiguas.

La prueba de concurrencia y vigencia está soportada en READ COMMITTED; el lector
de vigencia rechaza los otros niveles, no oculta un resultado de snapshot viejo.
Histórico inmutable y publicación de datos no se confunden con actualidad del
selector. El adaptador de inicio/provisión sigue exigiendo sus políticas explícitas.
No habilita por sí solo la admisión de Scheduling: la composición productiva deberá
usar la admisión persistente dentro de la misma transacción, nunca IngresoLaboratorio.
El proceso institucional/autorización de publicación, documento/representación
aprobados y frontera HTTP de aceptación por ámbito siguen pendientes.

Las formas SQL NULL de transición se preservan, no son consentimientos oficiales.
Antes de un despliegue productivo deben revisarse escritores/permisos y coordinar
migración antes del ORM nuevo; no se promete que un escritor SQL manual NULL esté
legitimado ni que la migración sea online sin bloqueos. No se ejecutó en una base
persistente. Las funciones/triggers anteriores se preservan. Los recursos PG
propios se eliminan por fixture, sin limpieza global de Docker.

## Archivos afectados respecto al inicio de este incremento

- `backend/alembic/versions/20261106_consent_versions.py`
- `backend/app/db/models.py`
- `backend/app/modules/identity/application/consent.py`
- `backend/app/modules/identity/infrastructure/academic_base_models.py`
- `backend/app/modules/identity/infrastructure/consent.py`
- `backend/app/modules/identity/infrastructure/consent_document_models.py`
- `backend/app/modules/identity/infrastructure/consent_repository.py`
- `backend/app/modules/participation/api/dependencies.py`
- `backend/app/modules/participation/api/provision_router.py`
- `backend/app/modules/participation/infrastructure/models.py`
- `backend/app/modules/participation/infrastructure/provision.py`
- `backend/app/modules/participation/infrastructure/repository.py`
- `backend/app/modules/participation/infrastructure/start.py`
- `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`
- `backend/docs/CONSENTIMIENTO_E_INICIO_INTERNO.md`
- `backend/docs/CONSENTIMIENTO_PERSISTENCIA_PROPUESTA_20261105.md`
- `backend/docs/CONSENTIMIENTO_VERSIONADO_IMPLEMENTACION.md`
- `backend/tests/identity/academic_identity_support.py`
- `backend/tests/identity/test_academic_identity_repository.py`
- `backend/tests/integration/test_assignment_bridge.py`
- `backend/tests/integration/test_attempt_start.py`
- `backend/tests/integration/test_cases_guard_migration.py`
- `backend/tests/integration/test_consent_version_persistence.py`
- `backend/tests/integration/test_er28_academic_base.py`
- `backend/tests/integration/test_evaluation_result_storage.py`
- `backend/tests/integration/test_participation_persistence.py`
- `backend/tests/integration/test_schema_integration.py`
- `backend/tests/integration/test_steps_uuid.py`
- `backend/tests/integration/test_waiting_admission.py`


Git permanece en feature/backend-continuidad, HEAD 28be564; sin staging ni nuevos
commits. Se verifican refs, stash, .env, ER original, borrador y todos los archivos
previos. Se conserva también la documentación pendiente anterior al incremento.
El inventario y las huellas de este delta están en la carpeta de evidencia;
no se reescriben manifiestos de checkpoints anteriores.

Siguiente paso recomendado: revisar el proceso autorizado de publicación/selección
y obtener documento/evidencia institucional reales. Después componer aceptación
privada con ámbito persistente, y la admisión ya implementada en la UoW de inicio.
No activar inicio/provisión o notas oficiales hasta completar sus contratos.
