# Fase 9B: inicio seguro desde convocatoria — contrato condicionado

Ejecución: 4–5 de noviembre de 2026 (America/Bogota).
Directorio: repositorio original `proyecto-nuclear-2`.
Rama `feature/backend-continuidad`; HEAD `ac92b7251c96f81ddcb6f390ef21435ab74b6131`.
**Resultado:** infraestructura transaccional existente comprobada; inicio productivo
bloqueado por decisiones esenciales. No se monta ninguno de los dos candidatos.

## 0. Protección e inventario de 9A

Se verificaron los **16 archivos**, tamaño y SHA-256, contra `CIERRE.json` de 9A:
coinciden los 16. Ocho están modificados respecto de HEAD y ocho son nuevos.
Se inspeccionaron el diff, los contratos y los tests asociados. No se alteró ninguno.
El índice estaba vacío; no se ejecutó git add, commit, push, merge o PR.

| Tipo | Ruta desde backend/ | Contenido apto para revisión de commit |
| --- | --- | --- |
| M | app/main.py | Montaje limitado a las cuatro operaciones de 9A |
| M | app/modules/participation/api/HTTP.md | Contrato de composiciones principal/aislada |
| M | app/modules/participation/api/dependencies.py | Progreso puro y composición autorizada de operaciones |
| M | app/modules/participation/application/services.py | Proyección compartida; semántica escritora anterior conservada |
| M | app/modules/participation/infrastructure/composition.py | Matrícula activa exigida en la composición principal |
| M | app/modules/participation/tests/test_api.py | OpenAPI limitado a las operaciones acreditadas |
| M | docs/FASE_9_APLICACION_PRINCIPAL.md | Enlace al incremento posterior, conserva historia |
| M | tests/integration/test_main_current_scenario.py | Aserciones del montaje permitido |
| Nuevo | app/modules/participation/application/progress.py | Proyección pura del progreso |
| Nuevo | app/modules/participation/infrastructure/progress_query.py | Consulta SQL sin DML, flush ni commit |
| Nuevo | app/modules/participation/api/progress_router.py | GET privado puro |
| Nuevo | app/modules/participation/api/attempt_operations_router.py | POST de primera respuesta y cierre |
| Nuevo | tests/integration/test_main_progress.py | Nueve escenarios de aceptación |
| Nuevo | tests/integration/test_main_decisions.py | Catorce escenarios de aceptación |
| Nuevo | tests/integration/test_main_finish.py | Diez escenarios y recorrido principal |
| Nuevo | docs/FASE_9A_PARTICIPATION.md | Alcance, pruebas y límites del incremento |

**Propuesta, NO ejecutada:** commit local
`feat(participation): progreso puro, respuestas inmutables y cierre en principal`.
Su selección debe limitarse a los 16 archivos anteriores; el detalle con huellas
está en `evidencias/fase9b_20261105T043309Z/inventario_9a.json`.
Excluir `.env`, ZIP, Word, evidencias, logs, XML, cachés y cualquier otro archivo
sin seguimiento. Este informe de 9B es un entregable nuevo, separado del lote 9A.
El escaneo estático de ese lote no encontró JWT literales, claves privadas ni URLs
PostgreSQL con credenciales literales. No equivale a una certificación exhaustiva;
los secretos sintéticos de fixtures permanecen en memoria y no se exportan.

## 1. Fuentes y alcance de confirmación

- F1: [ProyectoNuclear-IngenieriaSoftwareII (1).pdf](<../../_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf>),
  pp. 4–5 (27 RF y RNF) y 7 (reglas). RF-22 y RN-20 dejan explícitamente pendiente
  la base del umbral; no aportan minutos ni una frontera aprobada.
- F2: `docs/FASE_8B_INICIO_TRANSACCIONAL.md`, sección «Límites académicos conservados»:
  P01–P16 son propuestas; ingreso, consentimiento, provisión e intentos excepcionales
  requieren aprobación antes del montaje productivo.
- F3: `docs/FASE_8B_RESPUESTAS_INMUTABLES.md` y `docs/FASE_9A_PARTICIPATION.md`:
  aclaración posterior de respuestas inmutables, aceptación y límites vigentes.
- F4: puertos y código actual inspeccionados bajo `app/modules/participation/`,
  Identity y Scheduling. Una capacidad técnica o dato persistido no es aprobación
  académica de su política.

«CONFIRMADA» distingue una regla funcional con fuente de una garantía técnica
comprobada del contrato actual. «PENDIENTE» no se convierte en un valor por defecto.
«INCONSISTENTE» identifica discrepancias documentales o técnicas; los defectos de
código se distinguen mediante su reproducción automatizada.

## 2. Matriz de trazabilidad

Los archivos de implementación indicados son relativos a `app/modules/`.

| Regla / requisito | Estado y fuente | Implementación actual | Riesgo y decisión necesaria |
| --- | --- | --- | --- |
| Correo/código, cuenta activa y rol ESTUDIANTE; RF-01/02, RN-01/02 | CONFIRMADA: F1 pp. 4,7 | identity/application/authentication.py y api/dependencies.py; repositorio real | JWT no equivale a permiso de iniciar; revalidar en escritura |
| Convocatoria individual ACTIVA, titularidad y contexto JWT; RF-20/21, RN-08 | CONFIRMADA: F1 pp. 5,7 | identity/infrastructure/scheduling_access.py; IdentityInicioSQLAlchemy.autorizar_acceso | Retirada, código o cuenta ajenos se rechazan; no confiar en UUID del cliente |
| Matrícula activa y asignación del mismo grupo; RF-04, RN-05 | CONFIRMADA: F1 y contrato vinculado | participation/infrastructure/academic_context.py, ConsultaVinculacionSQLAlchemy.consultar | No crear matrículas ni inferir grupo desde nombre del espacio |
| Sesión EN_CURSO, no iniciar en FINALIZADO; RF-19/25, RN-07 | CONFIRMADA: F1 | scheduling/application/validar_ingreso.py y academic_context.py | Un login válido antes de iniciar sesión no autoriza creación |
| Caso, versión UUID exacta, rúbrica y version_regla propias; RF-09/17/18, RN-04/17 | CONFIRMADA: F1 y contratos actuales | cases/application/published_version.py; SchedulingInicioSQLAlchemy.obtener_condiciones | Nunca sustituir por última edición; la referencia a regla de rúbrica no aprueba una política de inicio |
| Versión asignada que después se archiva | PENDIENTE: alcance de F1 RF-09/RN-04 | published_version.py exige PUBLICADO; ingreso/inicio rechazan ARCHIVADO. 9A sí conserva lectura de intentos existentes archivados | Confirmar si archivar impide iniciar convocatorias previas o solo nuevas programaciones. No ampliar Cases unilateralmente |
| Recorrido ejecutable soportado | CONFIRMADA como restricción técnica, F3/F4 | CasesIntentoSQLAlchemy + RepositorioGrafoSQLAlchemy | Incompleto/multipregunta/ciclos no conceden inicio; esas reglas siguen pendientes, no se inventa linealidad |
| Validar ingreso no crea P ni I | CONFIRMADA: separación RF-01/22/23 y contrato HTTP | scheduling/api/router.py /validar-ingreso | No confundir lectura con provisión o autorización transaccional |
| Ventana de ingreso y límites exactos; RF-22, RN-20 | PENDIENTE explícita: F1 pp. 5,7; F2 | scheduling/domain/ingress_policy.py: PoliticaIngreso; default PoliticaIngresoNoConfigurada | Faltan base, autoridad, valor y fronteras. No adoptar una propuesta ni un test como regla |
| fecha_limite_ingreso y apertura/cierre de asignación | PENDIENTE en su origen académico, F2 | CondicionesInicioIntento y CondicionesVinculacion reciben valores del servidor | La existencia de columnas no autoriza un cálculo ni su procedencia; debe aprobarse quién las fija |
| Consentimiento existente, propio, no revocado y no futuro | CONFIRMADA como guard técnico conservador, F4 | IdentityInicioSQLAlchemy.autorizar_inicio; validar_instante_inicio | Se rechaza el consentimiento ajeno/revocado/aceptado después; no se fabrica aceptación |
| Aplicabilidad, texto/versión vigente y autoridad del consentimiento | PENDIENTE: F2 | PoliticaInicioIntento recibe version_consentimiento y aceptado_en; no hay proveedor aprobado | Definir alcance y fuente de la versión. NOT NULL físico no demuestra obligación académica universal |
| Revocación del consentimiento | PENDIENTE en efectos académicos: F2 | Nuevos inicios rechazan fecha_revocacion no NULL; no hay flujo productivo de revocación | Confirmar alcance temporal y efecto sobre intentos ya iniciados; no alterar 9A en este incremento |
| Momento de creación y estado inicial de participación | PENDIENTE: F2 | PoliticaVinculacionParticipacion.autorizar devuelve estado explícito | Provisión previa o creación con primer intento no están aprobadas. No usar el default físico como permiso |
| Duración individual positiva e histórica; RF-23/RN-06 | CONFIRMADA: F1 y persistencia existente | SchedulingInicioSQLAlchemy compara duración de asignación/sesión; Intento.iniciar y duracion_concedida_segundos | No recalcular duración de intentos existentes. Programación valida máximo frente al estimado |
| Inicio tardío cuando el plazo individual superaría el fin de sesión | PENDIENTE de coordinación RF-22/23, F1/F2 | El dominio calcula inicio + duración; respuestas de 9A respetan fin exclusivo de sesión | Aclarar admisión/tiempo disponible. No truncar duración ni conceder prórroga automáticamente |
| Participación no se repite automáticamente; RF-25/RN-16 | CONFIRMADA: F1 p. 7; discrepancia técnica corregida en 9B | ServicioInicio cuenta previos; permiso ligado a P y docente activo. IdentityInicioSQLAlchemy ahora resuelve su UUID CASES y verifica el creador del caso | Antes solo comprobaba al docente del grupo: faltaba verificar al creador. Tres pruebas negativas reprodujeron el defecto. intentos_base no autoriza por sí solo la repetición |
| Cantidad, vigencia y consumo del intento extra | PENDIENTE de política: F2 | PoliticaInicioIntento; usos contados por I.id_permiso_extra bajo locks de la misma P | El extra positivo de laboratorio no aprueba uno ni varios extras productivos |
| Participación existente y solicitudes duplicadas | CONFIRMADA como contrato actual | Obtener/crear P: 201 nueva, 200 existente; nuevo inicio activo: 409 | No hay un nuevo intento silencioso. Cualquier cambio de respuesta de reintento debe acordarse como contrato HTTP |
| Recuperación/reinicio tras vencimiento | PENDIENTE: solicitud y F2 | 9A puede proyectar vencimiento sin guardarlo; cierre confirma estado; iniciar no revive intentos | No reiniciar reloj ni conceder otro cupo. Recuperar un activo no debe confundirse con revivir un vencido |
| Atomicidad, unicidad y concurrencia; RNF-04/10 | CONFIRMADA técnicamente | ServicioVinculacionSQLAlchemy + UoW READ COMMITTED, advisory lock por convocatoria, locks de filas y UNIQUE | El hash es solo clave de lock, no conversión de IDs. Fallos revierten P e I |
| Falta de políticas indispensables | CONFIRMADA como cierre seguro | None en ingreso/vinculación/inicio produce 503 o error de política, sin confirmar registros | No configurar un proveedor permisivo para pasar aceptación |
| Respuestas modificables del PDF frente a aclaración posterior | INCONSISTENTE en documentación: F1 RF-10/RN-10/11 frente a F3 | Dominio, repositorio y PostgreSQL mantienen respuestas inmutables | Actualizar el documento académico con la aclaración; no reactivar PUT ni alterar 9A |
| Zona de timestamps sin offset | CONFIRMADA como dependencia técnica existente | FechasPersistencia / PARTICIPATION_TIMESTAMP_ZONE sin default | Falta verificar convención del despliegue; UTC del laboratorio no la aprueba |

## 3. Flujo real y límite transaccional

1. Identity valida correo/código y emite JWT con contexto de convocatoria. No crea
   participación ni intento ni confirma permiso temporal de inicio.
2. Validar ingreso comprueba convocatoria, estado y ventana suministrada por una
   política del servidor. Sin política productiva, la ruta sigue cerrada.
3. El inicio combinado recibe referencias y código, nunca identidad, estado,
   tolerancia o política elegidos por el cliente. Identity los vuelve a comprobar.
4. ServicioVinculacionSQLAlchemy abre una UoW PostgreSQL READ COMMITTED; el lock por
   convocatoria serializa incluso la ausencia de P. Recupera/bloquea la P existente
   y las fuentes de cuenta/rol/asociación/matrícula/convocatoria/sesión/asignación,
   caso y edición/rúbrica. Consulta el contexto después de bloquear sus fuentes.
5. La política de vinculación debe autorizar y aportar el estado inicial. Si P ya
   existe debe corresponder exactamente a convocatoria, asignación y matrícula;
   no se reasigna una participación ajena por coincidencia de datos.
6. `preparar_inicio_en_uow` reutiliza ServicioInicio.preparar y la misma UoW. Valida
   consentimiento y permiso, grafo, duración, previos y condiciones. El instante
   efectivo del registro vuelve a validarse en la misma transacción.
7. Solo el coordinador confirma al terminar ambos registros. Una política de inicio
   faltante puede descubrirse después del INSERT de P, pero provoca rollback de P
   e I. No se abre una UoW anidada ni se confirma P por adelantado.

El endpoint independiente `/participacion` tiene su propio commit y no recibe
consentimiento. No debe publicarse junto al combinado por conveniencia si se
aprueba crear P únicamente con el primer intento. El factory actual produce las
dos rutas: el futuro montaje debe seleccionar explícitamente la operación aprobada.
Hoy ninguna está registrada en main; no existe contradicción productiva que corregir.

## 4. Avance de 9B y pruebas actuales

**Los 16 archivos de 9A se conservaron sin cambios.** No se duplica el inicio ni
la provisión. Se corrigió únicamente una omisión demostrada de autorización en
`IdentityInicioSQLAlchemy.autorizar_inicio`, fuera de esos 16 archivos:

- El permiso extra comprobaba al docente del grupo, pero no al creador del caso
  exigido por RN-16. Un docente del grupo con asociación CASES ajena, ausente o
  ambigua superaba ese control.
- Ahora reutiliza `ResolverIdentidadAcademica` y su repositorio SQL, exige una
  asociación CASES inequívoca y compara el UUID con `CasoModel.docente_creador_id`
  del caso asignado. No convierte identificadores ni crea asociaciones.
- Conserva los controles previos de grupo, rol, cuenta activa y cantidad. Bloquea
  el usuario docente, sus vínculos CASES existentes y el caso dentro de la misma
  transacción; ausencia/discordancia deniega y ambigüedad devuelve regla pendiente.
  El bloqueo del usuario coordina los INSERT de vínculos mediante su FK, conforme
  al escritor actual `agregar_verificado`. No se certifican aquí procedimientos
  administrativos externos que reasignen vínculos por SQL sin ese protocolo.
- No concede repeticiones: la política de inicio sigue siendo indispensable y no
  existe un proveedor productivo aprobado.

Archivos de 9B: `app/modules/participation/infrastructure/start.py` (modificado),
`tests/integration/test_attempt_permission_creator.py` (nuevo, cuatro casos), y
este informe (nuevo). Evidencias locales separadas, excluidas de cualquier commit.
No se añaden proveedores, rutas, modelos, migraciones ni datos productivos.

### Ejecuciones, sin sumar suites solapadas

1. Antes de la corrección, la nueva prueba reprodujo **1 aprobada y 3 fallidas**,
   cero omisiones/errores, una advertencia: `pruebas_seguridad_20261105T044652Z`.
   Los tres fallos fueron `DID NOT RAISE`, no fallos de infraestructura.
2. Después: **4 aprobadas**, cero omisiones/fallos/errores y una advertencia,
   7.79 s: `pruebas_seguridad_20261105T044723Z`. Método exacto:
   `backend/tests/integration/test_attempt_permission_creator.py::test_permiso_exige_identidad_cases_inequivoca_del_creador`
   con parámetros `creador`, `ajeno`, `ausente`, `ambigua`.
   Prueba el adaptador real con PostgreSQL y contexto de fixture controlado;
   no sustituye la aceptación HTTP/JWT del inicio combinado ya existente.
3. Regresión general **posterior a la corrección: 2001 aprobadas, 38 omitidas,
   0 fallidas, 0 errores y 1 advertencia**, 750.05 s.
   Evidencia: `pruebas_total_20261105T044741Z/{ejecucion.json,consola.log,junit.xml,resultado.json}`.
   Incluye los cuatro casos nuevos y los grupos de la tabla inferior, además del
   resto del backend y Participation/Evaluation. Los archivos fuente preexistentes
   no cambiaron durante pytest; el laboratorio BD2-04 generó su JSON de evidencia
   habitual, que se conserva.

Las 38 omisiones se mantienen: 29 de persistencia Identity sin URL externa,
3 de conexión Participation sin habilitación externa y 6 de laboratorio
Participation sin `SPS_PERSISTENCE_LAB_URL`. No se habilitaron conexiones del
proyecto para convertirlas artificialmente en aprobadas.

Focalización inicial (anterior a la corrección): **208 aprobadas, 0 omitidas, 0 fallidas, 0 errores,
1 advertencia conocida**, 179.54 s. Las fuentes no cambiaron durante pytest.

| Archivo existente | Tests ejecutados | Evidencia y límite |
| --- | ---: | --- |
| test_attempt_start.py | 35 | PostgreSQL propio; autorización, consentimiento, versión, duración, permisos, concurrencia y rollback. Políticas positivas SOLO LAB |
| test_participation_provision.py | 35 | PostgreSQL propio; P idempotente, P→I atómico, integridad, error intermedio y otra sesión SQL |
| test_participation_http_composition.py | 21 | HTTP/JWT/SQL reales; cada política ausente da 503 sin P/I, actor/convocatoria/matrícula/horario, duplicados y fallo tras INSERT |
| test_main_current_scenario.py | 11 | Principal real: consulta privada y exposición limitada |
| test_main_progress.py | 9 | Principal real: progreso efectivo sin DML/flush/commit |
| test_main_decisions.py | 14 | Principal real: primera selección inmutable, ámbito, carrera y rollback |
| test_main_finish.py | 10 | Principal real: cierre y vertical de intento existente, sin notas |
| identity/test_student_login_scheduling.py | 51 | SQLite aislado/PostgreSQL propio y utilidades; login real no equivale a ingreso |
| unit/scheduling/test_ingress_policy.py | 22 | Unitarias de mecánica temporal, no aprobación de una fórmula |

No son 208 inicios productivos ni 208 pruebas PostgreSQL: se distinguen capas y
motores en la tabla. Los cuatro casos añadidos cubren la omisión RN-16 demostrada;
no se crearon pruebas redundantes para aumentar estadísticas. Los positivos
del inicio usan IngresoLaboratorio, InicioLaboratorio y VinculacionLaboratorio;
el consumo extra conserva su etiqueta de laboratorio. Las relaciones críticas de
los recorridos SQL/HTTP positivos son reales, no mocks que siempre concedan acceso.

No se ejecutó nuevamente la suite general porque 9B no cambia código. Las
1997 aprobadas y 38 omitidas de 9A son históricas. La ejecución actual posterior
al cambio es la regresión de 2001/38, no una suma de suites.
La advertencia actual es Starlette/TestClient-httpx.

Evidencia: `evidencias/fase9b_20261105T043309Z/`, con inventario SHA-256, estado Git,
comando, fuentes, consola, JUnit, resultado y `pruebas_nominales.json` con los 208
identificadores exactos. Se excluyen conexiones externas y lectura de `.env` solo
en el proceso hijo; no se modifica el archivo. PostgreSQL17 se crea exclusivamente
en contenedores nuevos con tmpfs y se eliminan solo sus IDs propios.

```powershell
# Desde la carpeta original, sin cambiar de rama ni de carpeta:
& C:\Python313\python.exe -B .\evidencias\fase9b_20261105T043309Z\ejecutar_validacion.py focal
& C:\Python313\python.exe -B .\evidencias\fase9b_20261105T043309Z\ejecutar_validacion.py seguridad
# Regresión completa aislada (crea nuevos laboratorios propios):
& C:\Python313\python.exe -B .\evidencias\fase9b_20261105T043309Z\ejecutar_validacion.py total
Get-Content .\evidencias\fase9b_20261105T043309Z\pruebas_focal_20261105T043515Z\resultado.json
Get-Content .\evidencias\fase9b_20261105T043309Z\pruebas_total_20261105T044741Z\resultado.json
```

## 5. Disponibilidad y riesgos

Main conserva exactamente las cuatro operaciones de 9A: GET escenario, GET progreso,
POST primera selección y POST cierre, sobre intento existente. Inicio/provisión
siguen ausentes (404). No hay recorrido íntegro login→nuevo intento productivo
que pueda acreditarse con las reglas actuales. Los tests ejecutan el inicio en
una aplicación condicionada de laboratorio y el tramo de intento existente en main.

Riesgos bloqueantes: asumir que JWT autoriza iniciar; elevar P01–P16 a aprobación;
usar defaults físicos como permisos; publicar la provisión independiente sin decidir
su momento; considerar cantidad/intentos_base como concesión automática; interpretar
una fecha o string de versión sin fuente autorizada; sustituir la edición archivada
por la más reciente para desbloquear ingreso. Ninguna de esas prácticas se aplicó.

Los controles de transacción y FK no resuelven esas decisiones académicas. Se
conservan hashes de códigos, referencias históricas y reloj del servidor; no se
fabrican consentimientos, usuarios, matrículas, permisos, ausencias o notas.

## 6. Preguntas concretas y siguiente implementación

Para la profesora/responsable académico:

1. RF-22: ¿cuál es la base del umbral, quién fija su valor y qué instantes exactos
   se incluyen? Confirmar expresamente cualquier propuesta de minutos. Si la base
   es inicio efectivo, debe identificarse su fuente persistida; no usar el programado
   como sustituto silencioso.
2. Consentimiento: ¿es obligatorio para todo inicio? ¿Qué texto/versiones son
   vigentes y quién los publica? ¿Una aceptación por versión basta para varias
   convocatorias? Si no aplica, ¿cómo se conciliará el FK obligatorio sin una
   aceptación ficticia?
3. Revocación: ¿impide nuevos inicios, afecta intentos activos o ambas cosas, y
   desde qué instante? No asumir retroactividad ni alterar intentos anteriores.
4. Provisión: ¿P se crea únicamente con el primer intento o puede existir antes?
   ¿Qué estado inicial corresponde? ¿La provisión independiente debe ser interna
   o administrativa, y con qué autorización?
5. Repetición: confirmar cantidad por permiso, vigencia, momento de consumo y
   tratamiento de fallos/cierre/vencimiento. Un permiso o cupo almacenado no sustituye
   una regla aprobada ni permite recuperar un vencido automáticamente.
6. ¿Una convocatoria emitida puede iniciar con su versión exacta si posteriormente
   se archiva, o debe bloquearse? La lectura histórica de un intento ya iniciado
   es un caso distinto que 9A ya conserva.
7. Si el inicio admitido deja menos tiempo de sesión que el máximo individual,
   ¿debe denegarse el inicio o existe otra regla aprobada? No se propone truncar
   ni ampliar automáticamente ningún plazo.

Para el equipo técnico (no requiere inventar política académica): acordar si una
repetición HTTP del inicio mantiene 409 como ahora o recupera el MISMO intento
activo tras perder una respuesta de red; no confundirlo con un nuevo intento ni
con recuperar un vencido.

Después de las aprobaciones: implementar únicamente los proveedores faltantes de
los tres puertos actuales, vinculados a datos/definiciones autorizados y a la misma
transacción. Revisar el montaje para publicar solo la operación aprobada, ejecutar
aceptación con esas definiciones y después el vertical por main. Si cambia el
contrato de versiones archivadas, coordinarlo con Cases sin cambiar el UUID ni
elegir automáticamente la última versión. No se inicia esa implementación aquí.

**Conclusión:** el bloqueo restante no exige otro motor o repositorio. Exige resolver
las decisiones indicadas antes de autorizar la creación productiva. El inventario
9A queda preparado para revisión de commit local, pero no se ejecuta dicho commit.

## 7. Cierre verificable

- Rama y HEAD intactos: `feature/backend-continuidad`,
  `ac92b7251c96f81ddcb6f390ef21435ab74b6131`; índice vacío.
- Los 16 SHA-256 de 9A coinciden al finalizar. Frente al inventario de fuentes de
  la primera ejecución, el único archivo preexistente modificado por 9B es
  `infrastructure/start.py`. Se conservaron los demás archivos locales.
- Referencias de main, develop, martin, feature/integracion-backend y stash original
  iguales al estado inicial. No hubo cambio de rama, commit, push, merge ni PR.
- `alembic -c backend/alembic.ini heads`: una cabeza,
  `20261104_teacher_spaces`. No se creó ni modificó ninguna migración.
- `git diff --check`: código 0; avisos de conversión LF/CRLF en dos archivos
  preexistentes de 9A, sin defectos de whitespace.
- Sin contenedores restantes con la etiqueta del laboratorio al cerrar. Durante
  la ejecución se observaron PostgreSQL17, tmpfs y ausencia de montajes persistentes:
  `aislamiento_observado.json`. No se conectó ninguna base permanente.
- `CIERRE.json` conserva esas verificaciones y el estado Git completo. El JSON
  generado por el test BD2-04 se conserva; no se elimina evidencia.
- El lote propuesto de 9A continúa separado. La corrección de 9B, su prueba y este
  informe requieren revisión propia antes de cualquier selección para commit.
