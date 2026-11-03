# BD2-05 — Inicio persistente: límite y autorización mínima pendiente

2026-11-02 · Rama `feature/integracion-backend` · **Sin ORM, migración ni escritor nuevo.**

## 1. Resultado de esta etapa

El primer incremento seguro es materializar el puente de asignación/matrícula/
convocatoria y fijar la edición antes de persistir intentos. **No puede
implementarse con el esquema integrado y los contratos actuales sin una decisión
adicional de esquema.** No se creó un repositorio incompleto que oculte esa falta.

El bloqueo inicial es comprobable: asignacion_caso.id_caso del ER exige INTEGER
y FK a caso.id_caso; el caso actual tiene PK UUID id y carece de id_caso INTEGER.
Además, una convocatoria no identifica por sí sola la matrícula ni una
participación. La autorización de BD2-04 no aprobó cambiar esas relaciones.

Se conserva el mecanismo caso/version_caso y no se reintroducen A1–A3 ni una fila
de caso por edición. La propuesta de abajo es distinta: conservar la familia
actual y agregar, **solo si se autoriza**, una clave INTEGER alternativa para
enlazarla desde las entidades originales. No se aplica ahora.

## 2. Dependencias resueltas y faltantes, con evidencia específica

| Componente | Resuelto actualmente | Falta para iniciar y guardar |
|---|---|---|
| Identity | JWT; usuario INTEGER expuesto como cadena decimal; activo/rol del servidor; resolver persistente por sistema | Autorizar matrícula/participación/consentimiento en la misma transacción de escritura; no basta el JWT inicial |
| Organización académica | grupo_academico, grupo_estudiante y consentimiento fieles al ER | No existe correspondencia aprobada espacio→grupo ni convocatoria→matrícula. Las filas no se deducen de UUID de estudiante |
| Scheduling | Convocatoria UUID por (sesión,estudiante UUID), código individual, estado; sesión con versión UUID y duración | No implementa SchedulingPort INTEGER; no conserva asignacion_caso ni sus cupos. La validación de ingreso actual es de lectura sin bloqueos de inicio |
| Cases | Edición exacta y rúbrica UUID/regla; guardas PostgreSQL BD2-04; consulta inyectable | No hay id_caso INTEGER alternativo. Los puertos de decisiones INTEGER tampoco están conectados a preguntas/opciones UUID |
| 8A | Relee cuenta/rol, valida contexto de convocatoria, titularidad, código, horario y referencia exacta | Proyección informativa: no permiso persistente ni transacción que inserte intento |
| Participation dominio/Application | Intento inmutable, reloj, estados, guardas, ServicioInicio y Facade | No hay repositorio de escritura ni adaptadores transaccionales concretos de sus puertos |
| Infraestructura | UnidadTrabajoSQLAlchemy comparte Session entre repositorio y resultados; lecturas bloqueables y codecs existentes | Los puertos Identity/Scheduling del servicio no quedan automáticamente ligados a esa Session. Lecturas requieren duración histórica explícita |
| Permiso adicional | Clase/repositorio nativo de Identity, fuera del metadata integrado | FK a participacion pendiente; no valida/consume cupos por sí solo |

Fuentes: [ports.py](../../app/modules/participation/application/ports.py),
[ServicioInicio](../../app/modules/participation/application/services.py),
[8A](../../app/modules/participation/infrastructure/integration.py),
[unidad de trabajo](../../app/modules/participation/infrastructure/unit_of_work.py),
[lecturas](../../app/modules/participation/infrastructure/queries.py),
[organización/consentimiento](../../app/modules/identity/infrastructure/academic_base_models.py),
[resolver SQL](../../app/modules/identity/infrastructure/academic_identity_repository.py),
[validador de convocatoria](../../app/modules/identity/infrastructure/scheduling_access.py),
[Scheduling](../../app/modules/scheduling/application/validar_ingreso.py).

Verificación en memoria, sin engine ni conexión: **22 tablas integradas; una
cabeza 20261102_cases_history_guard**. Asignación, participación, intento,
paso_simulacion y permiso_intento_extra no están en ese metadata. Esto no es una
inspección del estado físico de las bases del equipo, que no se consultaron.

## 3. Correspondencias que no deben asumirse

| Conceptos | Diferencia real | Contrato que debe aprobarse |
|---|---|---|
| asignacion_caso / sesion_programada | La primera vincula grupo y caso INTEGER con ingreso/cupos; la segunda espacio y versión UUID, sin grupo | Asignación vinculada explícitamente a una sesión y grupo acreditado; nunca grupo=espacio por inferencia |
| convocatoria / participacion | Convocatoria es invitación/código individual por sesión; participación enlaza asignación y matrícula, con otros estado/fecha | Materializar participación antes de ServicioInicio y registrar su convocatoria real; no crearla implícitamente por ID de URL |
| matrícula / UUID estudiante Scheduling | Matrícula pertenece a usuario INTEGER y grupo; UUID pertenece al vínculo de Identity para ese sistema | Resolver usuario→UUID y comprobar que la matrícula es del mismo usuario y del grupo de la asignación |
| caso / edición | Familia UUID estable y varias versiones UUID | Asignación debe fijar una versión de su familia, no «última versión» ni caso_id convertido |
| intento / participación | Un intento es ejecución individual numerada, no convocatoria ni membresía | FK a participación, consentimiento propio y duración concedida histórica; cupos autorizados atómicos |

Identificador de consentimiento o permiso enviado en HTTP es una referencia a
verificar, nunca prueba de titularidad. id_usuario y UUID Scheduling son conceptos
distintos; la adaptación cadena decimal↔INTEGER de la misma PK no crea otra identidad.

## 4. Subconjunto mínimo de persistencia y orden

Para guardar un intento conforme al ER harían falta cuatro entidades oficiales:
**asignacion_caso → participacion → permiso_intento_extra → intento**, usando las
tres de organización/consentimiento ya integradas y usuario. No son nuevas entidades
ajenas a las 28. Un permiso opcional no exige concederlo ni habilitar repeticiones,
pero su tabla sí debe existir para resolver la FK nullable de intento: NULL no
permite una FK a una tabla inexistente. No se duplica la clase de Identity ya creada.

No hay un subconjunto no vacío de esas cuatro que cierre por sí solo el inicio:
asignación está bloqueada por la clave del caso; participación depende de esa
asignación y de una matrícula acreditada; intento depende de participación,
consentimiento y la tabla de permisos. No se elimina una FK para hacer arrancar DDL.

paso_simulacion no es requisito físico para insertar el primer intento, pero sí
para conectar el repositorio completo/lecturas actuales y después registrar
respuestas. Sus decisiones/opciones INTEGER siguen sin equivalencia con Cases
UUID. No se devuelven pasos vacíos por omisión cuando no se puede consultar su
almacenamiento ni se anuncia listo un adaptador del RepositorioParticipacion completo.
No se incluyen resultados ni Evaluation en este primer subconjunto.

## 5. Propuesta específica de cambios — NO APROBADA, NO EJECUTADA

La propuesta evita cambiar los UUID y no convierte caso en edición. **Cinco
atributos adicionales y una relajación de nulabilidad**, más restricciones, serían
el candidato para enlazar el inicio. No es una afirmación de suficiencia para
persistir respuestas/evaluaciones ni una solicitud de aplicar todo en una migración.

| ID | Original / esquema actual | Delta mínimo propuesto | Integridad, preservación e impacto / aprobación |
|---|---|---|---|
| P1 | ER: caso.id_caso INTEGER PK; actual: caso.id UUID PK | Agregar caso.id_caso INTEGER generado, NOT NULL UNIQUE, manteniendo id UUID PK | Clave académica alternativa, sin UUID derivado ni modificación del valor UUID. **Difiere del PK oficial:** requiere aprobación académica expresa. Relación fuente/destino queda en la misma fila familiar, no por títulos/orden |
| P2 | ER: asignación con grupo/caso INTEGER; sin sesión/versión | Crear asignacion_caso original con FK a la clave P1; agregar sesion_programada_id UUID FK y version_caso_id UUID FK | La versión debe pertenecer al caso P1 y coincidir con sesión al materializar. Guardas recíprocas deben impedir posterior divergencia/reasignación silenciosa; congelar contexto ya usado. No basta la FK individual |
| P3 | ER: codigo_acceso_hash NOT NULL por asignación; actual: código individual por convocatoria | Permitir NULL en el hash grupal de asignación; conservar valores existentes si se acreditan | No copiar un código de alumno a todo el grupo ni inventar uno grupal. La autenticación sigue exigiendo el hash individual NOT NULL de convocatoria. Cambio académico de nulabilidad/uso requiere aprobación |
| P4 | ER: participacion(asignación, matrícula) UNIQUE; sin convocatoria | Agregar convocatoria_id UUID NOT NULL FK, UNIQUE | Propone una convocatoria→0..1 participación, vinculada por provisión explícita; no declara aprobada esa cardinalidad. Mantener UQ original. Verificar usuario, matrícula, grupo y sesión coincidentes en ambos sentidos |
| P5 | ER: intento inicio/fin, sin duración concedida | Agregar duracion_concedida_segundos INTEGER NOT NULL >0 | Capturar duración del servidor al iniciar; no reconstruir con programación posteriormente editada. Inicio+duración determina vence_en sin otra columna ni tiempo del cliente |
| P6 | ER: UQ(participación,número), FK independientes de consentimiento/permiso | Conservarlas y proponer índice UNIQUE parcial por participación con estado EN_CURSO, controles de estado/fechas y pertenencia | El único activo ya es regla de ServicioInicio; requiere aprobar su nueva restricción SQL. Consentimiento y permiso deben pertenecer al alumno/participación; sus FK separadas no lo garantizan |

Delta de atributos ilustrativo, **no SQL ejecutado ni modelo objetivo nuevo**:

```text
caso actual:        + id_caso INTEGER (alternativo UNIQUE; id UUID PK intacto)
asignacion_caso:    + sesion_programada_id UUID
                   + version_caso_id UUID
                   ~ codigo_acceso_hash admite NULL; jamás sustituye código individual
participacion:     + convocatoria_id UUID UNIQUE
intento:           + duracion_concedida_segundos INTEGER
```

Cardinalidades recomendadas para someter a aprobación: una sesión puede tener
asignaciones de varios grupos, máximo una por (sesión,grupo); cada convocatoria
se vincula a una matrícula/grupo elegidos explícitamente y a una sola participación.
Un estudiante con varias matrículas no recibe selección automática de la primera.
Si se requiere otra cardinalidad, P2/P4 deben revisarse antes de implementarse.
Espacio y grupo siguen separados; no se trasladan estudiantes de un espacio a
un grupo inventado para completar estas FK.

La rúbrica exacta no necesita otra columna para este comienzo: la versión fija
determina su rúbrica única y version_regla, protegidas por BD2-04. Esa deducción
solo es válida si se hace inmutable toda la cadena intento→participación→asignación→
versión y se rechazan referencias cruzadas. La revisión actual de BD2-04 **no**
inmoviliza sesion_programada.version_caso_id; por eso P2 exige guardas explícitas,
no copiar su valor sin protegerlo.

Crear la clave P1 sobre familias existentes necesita un procedimiento revisado
en laboratorio que preserve filas y conviva con las guardas de caso de BD2-04;
no se desactivarán esas guardas para improvisar un backfill. UUID existentes no
se reemplazan ni se generan de nuevo. Los nuevos INTEGER son independientes y
su correspondencia se verifica fila por fila. No se altera la PK UUID sin otro acuerdo.

Para fechas, conservar timestamp sin zona del ER requiere política explícita de
codificación y procedencia; [FechasPersistencia](../../app/modules/participation/infrastructure/codecs.py)
ya rechaza una zona desconocida/ambigua. No asumir UTC o Bogotá para datos legados.
La fecha_limite_ingreso obligatoria de asignación debe proceder de la política
aprobada; mientras falte, no se rellena con cierre de sesión o fecha ficticia.

## 6. Consentimiento, cupos y duración

- ConsentimientoORM existe, pero no un contrato completo de aprobación de texto/
  aplicabilidad. Intento del ER y dominio actuales exigen consentimiento. No
  inferir que login equivale a aceptación ni volver nullable ese campo sin decisión.
  Identity debe acreditar usuario, texto aplicable, aceptación y ausencia de
  revocación relevante para el inicio. Efecto de revocación sobre intentos ya
  comenzados es otra decisión: no se inventa aquí.
- El permiso extra existe solo como modelo/repositorio pendientes. Su repositorio
  inserta, pero no verifica creador/estado ni consume cupos. Un permiso debe ser
  de esa participación, concedido por el actor autorizado, y consumirse conforme
  a regla aprobada bajo el mismo bloqueo. No proponer «mejor nota», repetición
  automática, reinicio de cupos ni fórmula de consumo no acordada.
- Mantener DEFAULT intentos_base=1 del ER no aprueba una política de repetición.
  Sin implementación autorizada de SchedulingPort.autorizar_nuevo_intento, no
  se devuelve autorización por defecto. Permiso ajeno/ausente/ambiguo rechaza.
- La duración histórica del intento es positiva y del servidor. Guardar solo
  inicio/fin no permite rehidratar EN_CURSO; releer el tiempo mutable de sesión
  puede ampliarlo o acortarlo. P5 propone persistirla una vez, no una tolerancia.
- ServicioInicio rechaza un EN_CURSO previo incluso si debe procesarse vencimiento;
  no lo convierte automáticamente en nuevo intento. VENCIDO no es clasificación
  académica INCOMPLETA. El reloj es del servidor e inyectable.

## 7. Límite transaccional necesario — diseño, no garantía nueva demostrada

No encadenar «consultar 8A», cerrar su Session y luego abrir otra para insertar.
Tampoco reutilizar el contexto 8A como token de permiso. Se necesita una sola
transacción y Session para repositorio y adaptadores reales de autorización.

Protocolo candidato para probar después de aprobación:

1. Verificar JWT por Identity; dentro de la transacción releer cuenta/rol activos
   y contexto de convocatoria. Bloquear la cuenta y sus vínculos relevantes;
   resolver exactamente el UUID Scheduling, sin primera fila ni nuevas asociaciones.
2. Bloquear sesión, convocatoria y asignación en un orden fijo, con relectura
   fresca. Comprobar ACTIVA/EN_CURSO, código individual, titularidad y contexto JWT;
   no fiarse solo del parámetro de URL ni del usuario recibido fuera de la transacción.
3. Bloquear matrícula/consentimiento, participación y permisos aplicables en el
   orden global acordado. Comprobar misma cuenta/grupo/asignación/convocatoria y
   consentimiento válido. Participación debe existir antes de iniciar; su provisión
   es otro caso de uso idempotente autorizado, no un efecto lateral de este POST.
4. Leer/bloquear la versión exacta y su rúbrica propia, comprobar PUBLICADO y
   referencia completa. Resolver familia INTEGER P1 sin convertir UUID. No se
   elige la última versión. No se abre ingreso de ARCHIVADO por una política nueva.
5. Bajo el bloqueo de participación, consultar intentos/cupos y permiso; reservar
   el número e insertar el intento. Usar secuencia/RETURNING, nunca MAX(id)+1.
   MAX(numero_intento)+1 requiere ese bloqueo y UQ, no una lectura anterior suelta.
6. Evaluar ventana de la política confiable y reloj después de tomar los bloqueos;
   capturar inicio/duración coherentes sin hora del cliente. Si falta RF-22,
   fallar y rollback sin consumir permisos ni registrar un intento.
7. Un commit publica el intento; antes de él no hay éxito HTTP. Cualquier fallo
   revierte todo. 23505/40001/40P01 implican conflicto y relectura/reautorización,
   no un retry ciego de escritura con datos de autorización viejos.

El orden anterior debe contrastarse con todos los escritores de baja de cuenta,
retiro de convocatoria, cambio de horario y concesión de permisos. Bloquear las
filas ya leídas **no prueba** que no pueda aparecer un segundo vínculo de identidad
entre lectura y commit: debe coordinarse el protocolo de modificaciones del
resolver y probar inserción/reasignación concurrentes. No se declara resuelto por
poner FOR UPDATE en una sola consulta o por usar SERIALIZABLE sin validar sus efectos.

UnidadTrabajoSQLAlchemy ya proporciona begin/commit/rollback para sus repositorios,
pero la inyección actual de IdentityPort/SchedulingPort no acredita ese ámbito
compartido. Su composición debe ser transaccional antes del escritor; no se
introdujeron proxies de contexto, sesiones globales ni nuevos puertos vacíos.

Para el mínimo inicio no hace falta ejecutar CasesPort de decisiones, pero sí
validar la referencia de versión en el adaptador Scheduling/contexto de esa misma
transacción. Para responder después, `CasesPort(id_caso INTEGER)` sin referencia
de asignación/edición es insuficiente con varias versiones: deberá acordarse un
contrato interno versionado. No cambiar HTTP o convertir questionId a decision INTEGER.

## 8. Primer incremento recomendado tras aprobación

**BD2-05/U0: puente persistente de asignación, todavía sin inicio de intentos.**
Autorizar primero P1–P3, el vínculo de grupos y su integridad, permite una unidad
menor que crear todos los modelos a la vez: clave alternativa de familia y
asignacion_caso con referencias de sesión/versión acreditadas. Sin política RF-22
no se materializan filas que requieran un umbral inventado. Una tabla vacía o un
fixture sintético no se presentará como flujo productivo listo.

Archivos futuros concretos, **no creados/modificados en esta etapa**:

- `cases/infrastructure/models/caso.py`: solo clave alternativa P1 si se aprueba,
  sin reemplazar version_caso ni quitar guardas históricas.
- `scheduling/infrastructure/assignment_models.py`: asignación oficial más las
  referencias P2/P3 aprobadas, sin duplicar sesión o convocatoria.
- `app/db/models.py` y revisión Alembic posterior a 20261102_cases_history_guard:
  registro/dependencias y DDL aditivo revisado, exclusivamente en laboratorio primero.
- `tests/integration/test_participation_assignment_bridge.py`: familias/ediciones
  exactas, grupos, duplicidad, cambios recíprocos de sesión/asignación, rollback y
  preservación de datos/guardas previas. No se añade código de ejemplo a producción.

Después: P4/P5/P6 y participación/permiso/intento, mapeadores y escritor de inicio
ligados a la misma UoW. Pasos/respuestas y Evaluation siguen fuera de esa unidad.
La actual clase PermisoIntentoExtraORM se integra resolviendo sus FK/metadata,
sin crear una segunda clase homónima para suplantar el contrato de Identity.

Pruebas obligatorias antes de habilitar inicio: doble POST simultáneo, retiradas/
revocaciones y segundo vínculo concurrentes, cupo extra compartido o agotado,
versión/rúbrica ajenas, consentimiento de otro usuario/texto no aplicable, fallo
antes de commit y fallo de commit, duración histórica tras cambiar programación,
fronteras/zonas de tiempo y RF-22 ausente. Solo PostgreSQL nuevo desechable; ninguna
prueba positiva con política sintética autoriza producción.

## 9. Entrega, bloqueos y aprobación

No se implementó código, ORM, migración ni nuevo modelo de ensayo: las relaciones
indispensables requieren P1–P6 y decisiones de consentimiento/ingreso aún no
aprobadas. Tampoco se modificó Facade, sus patrones, 8A, BD2-04, autenticación o
los contratos públicos. La dependencia obtener_facade conserva 503 y RF-22 permanece
cerrado. No se calcula ni publica ninguna nota.

No se ejecutaron pytest, Docker o PostgreSQL. La inspección de metadata/grafo fue
solo en memoria; **1161 aprobadas y 38 omitidas es histórico**, no resultado nuevo.
**No hay integridad transaccional de un inicio SQL demostrada en BD2-05**: el
protocolo anterior es criterio de implementación/prueba, no evidencia ejecutada.

Para avanzar, decidir expresamente si se aprueban **P1–P3 solo para U0**, incluido
que id_caso INTEGER sea clave alternativa y no la PK oficial, o solicitar otra
representación. P4 (convocatoria/matrícula), P5/P6 (plazo/concurrencia) y reglas de
consentimiento, cupos/RF-22 se aprueban antes de conectar el inicio. Esta entrega
no interpreta silencio ni aprobación general del proyecto como esa autorización.
No se inicia BD2-06 ni otra unidad automáticamente.
