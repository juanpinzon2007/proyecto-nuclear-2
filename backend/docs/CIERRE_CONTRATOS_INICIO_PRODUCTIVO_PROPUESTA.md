> Actualización vigente: sala de espera y admisión aprobadas por el equipo.
> Se registran solicitudes propias antes de habilitar y se congela el conjunto
> elegible en la transacción docente SIN_INICIAR → EN_CURSO. EN_CURSO sin concesión
> individual rechaza con 403. No hay tolerancia anticipada ni tardía ni presencia
> online inferida. Las afirmaciones anteriores sobre falta de señal de admisión
> quedan como historia; se conserva el cierre del inicio por consentimiento oficial.
> Contrato, migración y evidencia: `SALA_ESPERA_ADMISION_DISENO.md` (backend/docs).

---

# Cierre de contratos de consentimiento y admisión — propuesta para aprobación

5 de noviembre de 2026, America/Bogota. Repositorio original, rama
`feature/backend-continuidad`, HEAD `33981c8`. Esta revisión prepara decisiones:
**no implementa política de admisión, endpoints, ORM ni migraciones**.

## 1. Dictamen del borrador de consentimiento

El borrador es adecuado como **material de revisión**, no como documento listo
para publicación/aceptación. Su aviso NO APROBADO, ausencia de versión oficial y
campos pendientes están correctamente visibles. No se modificó ni se presentó
como validación jurídica o institucional. Fuentes inspeccionadas:
`BORRADOR_CONSENTIMIENTO_INFORMADO.md`, `CONSENTIMIENTO_E_INICIO_INTERNO.md`,
modelos/servicios Identity, provisión/inicio Participation y matriz vigente.

| Elemento | Estado del borrador | Qué completar o revisar |
|---|---|---|
| Institución, responsables y contacto | Identificados como pendientes | Nombres/cargos/canales oficiales; separar responsable académico, tratamiento de datos y operador técnico |
| Finalidad y actividad | Descritas como académicas | Objetivo de la asignatura, actividad exacta y ámbito de uso aprobados; no extender a investigación u otros fines por inferencia |
| Duración y condiciones académicas | Pendientes explícitos | Información aprobada al participante; no insertar umbrales o consecuencias por no aceptar |
| Datos, destinatarios y privacidad | Tipos principales identificados; no promete anonimato | Inventario autorizado, acceso, conservación/eliminación, terceros y procedimiento de atención |
| Riesgos, molestias, beneficios y apoyo | Solicita completarlos; no afirma ausencia de riesgos | Valoración y medidas del responsable; no inventar evaluación institucional |
| Voluntad explícita e información previa | Declaración propuesta y autenticación contempladas | Forma final de presentación, accesibilidad, canal de preguntas y comprobante |
| No revocación durante ejecución | La decisión técnica se explica con reserva institucional | Revisar cómo se comunica y atienden solicitudes; no convertir una restricción de interfaz en afirmación sobre derechos |
| Identificador, versión, aprobación y vigencia | No existen oficialmente | Acto/evidencia de aprobación y documento exacto; fecha consciente de zona, sin valores inventados |
| Reutilización y cambio de versión | Regla del equipo recogida | Informar al participante de la nueva aceptación para una P nueva tras cambio de versión |

No se agregan condiciones legales, una base jurídica, plazos de retención ni
consecuencias académicas. La revisión de la profesora y la revisión institucional
no deben confundirse con un hash del archivo o con publicar un commit.

## 2. Una fuente oficial versionada, mínima para el plazo

**Recomendación:** registro de artefactos publicados del servidor, de solo lectura
en runtime, reutilizando FuenteConsentimiento. No tabla de documentos nueva ni
endpoint público de publicación en este primer incremento. Es una propuesta, no
un proveedor oficial ya implementado.

Cada definición publicada debe conservar: referencia estable <=30 (para el campo
existente), identificador del documento, versión, ámbito aprobado, vigencia explícita,
contenido canónico exacto, SHA-256, responsable/autoridad de aprobación, fecha y
referencia verificable de esa aprobación, y operador/fecha de publicación técnica.
Publicar no equivale a aprobar. Un ADMINISTRADOR del software no es automáticamente
la autoridad institucional del documento. Nada de esto proviene del estudiante.

Flujo de publicación propuesto: recibir aprobación y archivo exactos; verificar
identidad de la autoridad y metadatos; validar formato/huella/referencias; revisión
por responsable; desplegar registro y contenido inmutables en ubicación controlada;
activar explícitamente la definición aplicable. Una referencia nunca identifica
otro contenido. Se conservan todas las definiciones previas aunque dejen de ser
vigentes. Vigencia/ámbito se resuelven del registro autorizado, no por MAX de una
etiqueta ni por la aceptación más reciente.

El puerto actual expone vigente(id_asignacion,ahora), pero todavía no una consulta
histórica pública. Adaptarlo para recuperar definición histórica por referencia
sin alterar su contenido; no sobrecargar consultar aceptación vigente como historia.
El DTO actual calcula hash del texto UTF-8: si el documento oficial es PDF/DOCX,
se debe preservar su binario y distinguir ese hash del de una representación de
lectura. No tratar texto extraído o un PDF exportado como si fueran el original.
Formato canónico y representación que acepta el estudiante requieren confirmación.

Para el primer despliegue recomiendo **sin publicación en caliente**: bloquear
nuevas aceptaciones/creaciones, drenar UoW en todos los procesos, activar artefacto
y selector consistentes, verificar huellas/configuración en cada instancia y
reabrir. Así no se inventa una transacción atómica entre un archivo y PostgreSQL.
Publicación dinámica futura exigiría otro contrato transaccional. Una instancia
con registro ausente, incoherente o distinto debe fallar cerrada, no usar un default.

## 3. Persistencia y garantías de consentimiento propuestas

Ya existen: consentimiento por usuario INTEGER, versión/referencia y fecha;
servicio interno SQL con acción True explícita, revalidación de usuario, fecha del
servidor y comprobación de referencia/huella presentada; lectura de vigencia;
guard interno de no revocación; validación antes de INSERT P; FK de intento a C.
No existe fuente oficial ni huella/acto explícito persistido separadamente.

**Adaptación propuesta, pendiente de aprobación física y conceptual pertinente:**

| Lugar | Propuesta concreta | Integridad y tratamiento de legado |
|---|---|---|
| consentimiento | Añadir huella_documento VARCHAR(64) nullable y aceptacion_explicita BOOLEAN nullable; conservar version_texto como referencia inmutable del registro publicado | CHECK para nuevas evidencias completas (True, hash hexadecimal completo y referencia); el servicio solo inserta aceptaciones afirmativas. NULL legado no se transforma en aprobación ni se completa con hash del borrador |
| consentimiento / fuente | Referencia estable resuelve documento, versión, responsable y bytes históricos | No hay FK SQL a un archivo. El registro debe conservarse y ser verificable; app comprueba referencia/huella, no solo etiqueta. Si se exige integridad íntegramente SQL, reconsiderar la fuente persistida para aprobación, sin añadir tabla por iniciativa propia |
| participacion | Añadir id_consentimiento INTEGER nullable, FK a consentimiento.id_consentimiento | Legado NULL permanece sin correspondencia inventada. Guard BEFORE INSERT exige enlace/evidencia para nuevas P, titular mediante grupo_estudiante y aceptación previa; proteger enlace contra cambio. No existe hoy este enlace |
| intento | Conservar id_consentimiento existente y exigir correspondencia con el de P en nuevas ejecuciones | Reutilizar/extender guards actuales, sin nuevas entidades ni claves ficticias. No rellenar P legado tomando arbitrariamente un intento |
| Nuevas aceptaciones | Proponer unicidad parcial por estudiante y referencia para registros explícitos NO revocados | Requiere aprobar unicidad vigente; no impone una sola aceptación histórica. Legado queda fuera del índice y no se borra. No abrir reaceptación tras revocación sin su política |

Una aceptación verificada puede reutilizarse para nuevas P mientras siga vigente
la misma definición. Cambiar versión exige nueva aceptación para **P nueva**; no
reescribe ni invalida automáticamente una P/I histórica. Si cambia entre admisión
y creación, el inicio vuelve a resolver versión y rechaza hasta nueva aceptación.
La publicación coordinada evita una mezcla de definiciones a mitad de la UoW.

Para aceptación HTTP futura no basta _titular: hoy revalida cuenta/rol, pero no
acredita por sí solo matrícula y convocatoria/asignación para ese documento.
La composición debe comprobar ese ámbito con relaciones persistidas antes de
presentar/aceptar. Reutilizar la comprobación de contexto de Identity y la consulta
académica sin confundirla con permiso temporal de ingresar; aceptar un documento
no debe exigir ni conceder una admisión anticipada. Solo la versión/huella que
resuelve el servidor puede confirmarse; el cuerpo no identifica al estudiante.

Con la evidencia nueva, un reintento de aceptación podría devolver el mismo id
solo si titular, referencia, huella y acto explícito persistidos coinciden. Ante
legado sin prueba, discrepancia o ambigüedad, rechazar y conciliar; no convertir
el 503 conservador actual en éxito supuesto. Probar este cambio antes de exponerlo.

La migración sería aditiva, sin backfill académico y con preflight de datos,
PK/FK/índices e integridad del legado. El código debe desplegarse coordinadamente
con el guard de INSERT; no instalarlo mientras un escritor legítimo omita el enlace.
Downgrade solo en laboratorio o con comprobación de ausencia de evidencia nueva;
no borrar evidencia para facilitar reversión. No se crea revisión en esta tarea.

No revocación: conservar el guard interno y exigir que cualquier futuro escritor
aplique el chequeo y la actualización en la misma UoW; hoy no se abre un escritor
público. Para SQL directo se necesitaría extender la protección de fecha_revocacion
y comprobar también consentimiento no revocado al insertar I. Ambos caminos deben
serializarse sobre el consentimiento y probarse con PostgreSQL real: inicio gana
primero -> revocación rechazada; revocación autorizada gana primero -> inicio
rechazado. No basta comprobar I con una lectura suelta, ni mantener un lock solo
al abrir sesión y afirmar que protege toda la simulación. El vencimiento efectivo
sin cierre persistido no se usará como permiso implícito de revocación.

## 4. Comparación de admisión sin tolerancias inventadas

Regla confirmada: no ingreso antes de habilitación docente ni autorización de
llegadas tardías. Sala de espera, cohorte y significado de reintento NO están aún
aprobados. La autenticación previa ya es compatible con Identity: no equivale a
entrar al simulador ni a crear P/I.

| Alternativa | Evaluación |
|---|---|
| Permitir durante todo EN_CURSO | Rechazada: no distingue llegada tardía y contradice el límite solicitado |
| Igualdad con timestamp de habilitación, o intervalo técnico de segundos/minutos | Rechazada: igualdad frágil y duración no aprobada; no usar latencia/heartbeat como tolerancia encubierta |
| Admisión individual posterior por docente | Requiere excepciones/criterios nuevos; no aplicar como solución general a la prohibición de tardíos |
| Solicitudes de espera autenticadas, congeladas al habilitar | RECOMENDADA para aprobación: conjunto objetivo, persistente, sin duración nueva; permite reintentos de una admisión ya otorgada |

**La espera registra una solicitud persistida, no presencia online.** No se afirma
que el estudiante siga conectado y no se agrega un TTL, heartbeat o tiempo de
inactividad. Si el negocio requiere presencia online, debe definir otra señal y
su tratamiento de fallos de red antes de implementarla.

Flujo propuesto, sin implementarlo:

1. Con sesión SIN_INICIAR, estudiante autenticado registra solicitud propia de
   espera, comprobando convocatoria ACTIVA, cuenta, matrícula y versión. Es un
   caso de uso escritor separado, NO validar-ingreso y sin P/I. Registro repetido
   devuelve su solicitud existente, sin crear una nueva identidad.
2. La habilitación docente autorizada congela las solicitudes elegibles y registra
   estado EN_CURSO, auditoría, concesiones de admisión y avisos existentes en la
   misma transacción. Un fallo revierte todo; no conceder desde un callback posterior.
3. Solicitudes registradas después no reciben concesión. El orden se decide por
   transacciones/locks y estado, no por igualdad de timestamps. Una petición HTTP
   enviada antes pero recibida/serializada después requiere ese criterio explícito.
4. Estudiante consulta su concesión con JWT/contexto propios. Validar-ingreso sigue
   siendo lectura, sin DML/flush/commit; revalida cuenta, matrícula, convocatoria,
   sesión y versión, y verifica pertenencia de la concesión a esa habilitación.
5. Inicio comprueba de nuevo concesión, consentimiento vigente y demás condiciones
   en la UoW existente. Retiro, cuenta desactivada, matrícula inválida o sesión
   finalizada niegan acceso aunque exista una concesión histórica. No se borra.

Persistencia mínima propuesta, **no aprobada**: dos columnas nullable en
convocatoria: espera_registrada_en TIMESTAMPTZ y admision_evento_id UUID. Reutilizar
la PK de convocatoria como referencia estable de solicitud (no como credencial),
y su UNIQUE(sesion_id,estudiante_id). La concesión referencia la auditoría de esa
habilitación; su fecha se obtiene del evento. No hay tabla paralela de sala ni
conversión de usuario INTEGER a UUID.

CHECK: admision_evento_id exige espera_registrada_en. FK compuesta
(admision_evento_id,sesion_id) a evento_auditoria(id,sesion_id), con UNIQUE parental
necesario; verificar además semántica CAMBIO_ESTADO, SIN_INICIAR -> EN_CURSO y origen
docente. FK sola no acredita ese significado. La concesión ya otorgada y su causa
se protegen contra sustitución. Legado NULL significa sin admisión acreditada,
no se deriva de una convocatoria ACTIVA o de haber tenido un intento. Su transición
requiere conciliación explícita, nunca una concesión histórica ficticia.

### Reintentos y la decisión que no puede omitirse

- Releer una concesión o recuperar la respuesta de una solicitud ya confirmada no
  agrega estudiantes al conjunto admitido. Misma convocatoria/operación, resultado
  estable y titular revalidado; sin duplicar P/I ni consumir otro permiso.
- Un **primer inicio demorado**, aunque el estudiante estuviera en espera, NO es
  automáticamente un reintento. Debe aprobarse si la solicitud de espera representa
  un ingreso ya admitido al congelar y permite materialización posterior bajo las
  condiciones restantes. Si eso no se aprueba, conservar ese primer inicio cerrado;
  no inventar un TTL ni permitir toda la sesión por llamarlo reintento.
- Una solicitud de espera nueva después del corte no hereda la admisión de otro
  usuario/convocatoria. No hay autovinculación, reingreso excepcional ni reconvocación
  permisiva. Un I ya creado se recupera conforme al contrato existente, no se recrea.

### Concurrencia y compatibilidad real

El corte debe tener un único orden verificable. Proponer exclusión transaccional
por sesión antes de adquirir otros locks para los escritores participantes:
registro de espera, habilitación/concesión, retiro y comienzo. Es viable reutilizar
la técnica advisory_xact_lock ya usada en provisión, con una clave por sesión,
**solo si todos esos escritores respetan el mismo coordinador/orden**.
No basta añadir un FOR UPDATE de sesión al nuevo servicio: habilitar hoy toma S
antes de notificaciones/C y start toma P/cuenta/matrícula/C antes de S; una mezcla
puede producir esperas circulares. Revisar rutas reales, orden global y locks de
FK en PG antes de implementar; no se afirma resuelta esa compatibilidad hoy.

Si el registro gana y confirma antes del corte, puede ser incluido; si habilitar
gana, se rechaza registro nuevo. Rollback docente deja SIN_INICIAR y ninguna
concesión; rollback de espera no deja solicitudes elegibles. Validar es lector
sin escrituras. Reintentos del mismo cambio de estado conservan RF-19/auditoría
única; no reejecutar la concesión desde Observer postcommit.

El puerto actual PoliticaIngreso solo recibe sesión/inicio/fin y devuelve una
ventana: **no representa una concesión individual**. La integración propuesta
necesita consulta de admisión por identidad/convocatoria/version/habilitación,
reutilizando la autorización existente y sin otro reloj/motor. No simularlo
retornando una ventana global que autorice todo EN_CURSO. La relación con fechas
programadas y límite de inicio debe confirmarse sin alterar duración histórica.

## 5. Participation: comprobado y pendiente

Inspeccionados provision.py, start_policy.py, start.py, unit_of_work.py, router de
integración y main. Código Python y tests coinciden por SHA-256 con la última
regresión previa: **2126 aprobadas, 38 omitidas, 0 fallos/errores, 1 advertencia**.
No se ejecutaron nuevas pruebas ni PostgreSQL en esta revisión documental.

| Garantía | Estado real y evidencia |
|---|---|
| Consentimiento antes de INSERT P | Implementado interno; test_consent_before_provision.py::test_consentimiento_rechazado_antes_de_cualquier_insert_p observa SQL, no solo rollback |
| Política de inicio rechazada antes de INSERT | Implementado interno; test_politica_inicio_rechazada_antes_de_insert_p. Fuente/políticas positivas LAB |
| Grafo, duración, referencias y consentimiento de servidor | Prevalidados para nueva P y revalidados por iniciador existente; no se fabrica PK (None antes de crear) |
| Condición inicial inválida | No INSERT P en casos acreditados. No extender esa afirmación a todo error posible después de comenzar escrituras |
| Falla posterior, I o commit | UoW única revierte todo. Tests de rollback/duplicados/concurrencia existentes se mantienen; no nuevas ejecuciones atribuidas |
| Idempotencia | P única por convocatoria/asignación/matrícula; I activo único. Inicio repetido no crea otro; puede rechazar con conflicto. No llamar idempotente al mismo veredicto HTTP si devuelve 409 |
| Cuatro operaciones de intentos existentes | main mantiene escenario, progreso, primera respuesta inmutable y cierre, con Identity y autorización persistente; no se cambian |
| Fuente/proveedores productivos | Faltan; None conserva el cierre. No promover FuenteConsentimientoLaboratorio, IngresoLaboratorio ni políticas P01–P16 |

Para registrar inicio en main faltan: documento aprobado y fuente publicada,
evidencia de aceptación + enlace P, admisión individual aprobada/persistida,
proveedores productivos de vinculación/estado inicial e inicio/cupos/fechas,
composición segura por solicitud y aceptación HTTP sobre main con esas dependencias.
No confundir las dos decisiones prioritarias con garantía de que todo otro
proveedor ya está listo. Permisos excepcionales siguen cerrados si no se aprueban;
no son motivo para otorgar una repetición automáticamente.

Pruebas futuras imprescindibles: upgrade/downgrade aislados y legado sin backfill;
fuente ausente/manipulada/ambigua; presentación de versión obsoleta; prueba de
aceptación explícita persistida; FK/propiedad P-C-I; cambio de versión durante
publicación coordinada; espera vs habilitación en transacciones competidoras;
retiro antes/después de concesión; primer inicio vs retransmisión; rechazo de nuevos
tardíos; rollback y respuesta perdida después de commit; admisión de versión ajena;
no DML de validar-ingreso; no SQL de P antes de consentimiento; respuestas inmutables.
Distinguir unitarias/SQLite de locks y concurrencia PG17; luego general aislada.

## 6. Decisiones para aprobación y orden de implementación

| Decisión | Quién debe confirmarla | Sin confirmación |
|---|---|---|
| Texto exacto, responsables, formato, vigencia, ámbito y aprobación documental | Profesora/institución según sus competencias | No publicar documento/aceptación oficial |
| Evidencia técnica nueva, referencia P-C, unicidad vigente y adaptación de guards | Usuario/equipo y revisión académica de desviaciones del ER | No crear ORM ni migraciones |
| Espera significa solicitud registrada, no presencia online; congelarla al habilitar | Responsable funcional | No implementar sala/cohorte |
| Primer inicio demorado frente a recuperación de una operación admitida | Responsable funcional | No abrir ese primer inicio como supuesto reintento |
| Condiciones de horario/fecha y contratos de vinculación/inicio | Responsable funcional sobre reglas pendientes | No inferir permiso de empezar desde una concesión o consentimiento |

**Siguiente incremento recomendado, tras aprobar el diseño físico:** evidencia
explícita de consentimiento y vínculo inmutable P-C, con migración aditiva en
PG17 desechable y adaptación de ServicioConsentimientoSQLAlchemy/ServicioVinculacion.
Se puede probar con datos LAB sin publicar documento ni rutas. Criterios: legado
intacto/no autorizado por defecto, nuevas P sin enlace rechazadas, mismo titular,
contenido/hash verificables, guard no revocación con I EN_CURSO, carreras de inicio
y rollback y conservación de los cuatro endpoints existentes.

Archivos previstos: Identity academic_base_models.py y consent.py, Participation
models.py/provision.py/start.py, guards de una NUEVA revisión Alembic, tests de
consentimiento/inicio/persistencia; sin editar revisiones ya ejecutadas. Fuente
oficial y admisión se implementan después de sus confirmaciones, sin crear otro
motor Participation ni un sistema paralelo de notificaciones.

La matriz de 27 RF no cambia: no hay funcionalidad implementada nueva ni pruebas
nuevas que acrediten avance de categoría. RF-12/RF-22 siguen PARCIAL; se conserva
13 IMPLEMENTADO, 9 PARCIAL y 5 BLOQUEADO. Este documento no certifica cumplimiento
legal ni aprobación institucional y no autoriza ninguna migración o despliegue.

## 7. Checkpoint y preservación

Inventario completo de modificados/no rastreados desde HEAD: en la evidencia de
esta revisión, separado por tipo, tamaño y SHA-256. Contiene también temporales,
respaldos y ajenos como inventario de preservación, **no selección de commit**.
Manifiesto apto para revisión: `CHECKPOINT_BACKEND_CONTRATOS_20261105.json`, con
código/pruebas/documentación separados y huellas actuales; excluye .env, secretos,
respaldos, ZIP, Word, evidencias temporales, cachés y script QA ajeno. Se conserva
el manifiesto anterior sin sobrescribir sus huellas históricas.

No se ejecutó staging/commit/push/merge/PR/cambio de rama/restauración de stash.
La propuesta de checkpoint no equivale a autorización de sus commits. Deben
repetirse huellas/diffs del índice y selección explícita tras la revisión humana.

La selección actual contiene **51 archivos pendientes**: 18 de código, 16 de
pruebas y 17 de documentación, más el propio manifiesto documental sin
autorreferencia de hash. Un archivo del manifiesto histórico,
`backend/app/modules/scheduling/domain/ingress_policy.py`, ya coincide con HEAD
tras retirar la anticipación: no se cuenta como cambio pendiente ni fue eliminado.
El SHA-256 completo del manifiesto se conserva externamente en la evidencia.
No queda Python modificado/nuevo de app/tests fuera de la selección; el script
QA previo y artefactos ajenos continúan separados, sin eliminarse.


### Actualización posterior: señal de admisión implementada

La sala de espera ya fue aprobada por el equipo e implementada en Scheduling;
la propuesta anterior sobre esa señal queda sustituida por
SALA_ESPERA_ADMISION_DISENO.md (32 aceptaciones; general 2158/38, sin fallos).
La falta de fuente oficial de consentimiento permanece. No se aprueba ni publica
el borrador, no se abren rutas de creación/inicio de Participation. RF-22 figura
implementado en su alcance de admisión; RF-12 sigue parcial. No confundir ambos.
