# Incremento 8A: auditoría y límites de integración

Rama verificada: `feature/integracion-backend`. Se conservan los cambios previos
sin commit. Por instrucción del usuario no se ejecutan pytest, capturas, Docker,
conexiones a bases ni migraciones en esta etapa. La línea base 983 passed / 38
skipped es reportada, no una ejecución de esta entrega.

## Matriz previa a la implementación

| Módulo origen | Módulo destino | Información intercambiada | Contrato existente | Implementación disponible | Riesgo | Acción necesaria |
| --- | --- | --- | --- | --- | --- | --- |
| Identity | Participation HTTP | Cuenta activa y rol estudiante | `obtener_estudiante_actual` de Identity | JWT y repositorio SQL reales; Participation tenía stub 503 | Suplantación por IDs del cliente | Consumir la dependencia real; mantener cerrada la fachada |
| Identity | Participation HTTP | UUID académico Scheduling | `obtener_estudiante_scheduling` | Resolver SQL, 0..N vínculos, resolución exactamente uno | Confundir cuenta, UUID y membresía | Conservar cuenta INTEGER y UUID separados; rechazar ambigüedad |
| Identity | Scheduling | Contexto JWT y titularidad de convocatoria | `ValidadorConvocatoriaScheduling.validar_contexto` | Real SQL; no acredita ingreso temporal | Interpretar login como permiso de inicio | Reutilizar, sin sustituir RF-22 |
| Scheduling | Participation | Código, convocatoria, sesión, ventana y duración | `validar_ingreso(Session, ..., politica, reloj)` | Real; política por defecto no configurada | Saltarse RF-22 con otro endpoint | Consulta interna reutiliza el servicio; sin ruta alternativa |
| Scheduling | Cases | Versión exacta asignada | `sesion_programada.version_caso_id` | FK UUID real a `version_caso.id` | Elegir última versión o permitir elección estudiantil | Usar solo el UUID guardado por Scheduling |
| Cases | Participation | Referencia de versión publicada | `CasoService.obtener` es detalle docente, incluye respuestas | Falta consulta pública mínima para este consumidor | Filtrar corrección o usar detalle docente | Añadir lectura interna de metadatos, sin opciones ni contenido de rúbrica |
| Scheduling | Participation agregado | Asignación y membresía de una participación | `SchedulingPort` usa INTEGER del ER | Solo fakes; no hay `asignacion_caso` ni `grupo_estudiante` en las migraciones integradas | Inventar equivalencias con sesión/convocatoria UUID | Acordar vínculo y provisión antes de adaptar el puerto |
| Cases | Participation agregado | Caso, decisión, opción y recorrido | `CasesPort` usa INTEGER del ER | Solo fakes; Cases tiene caso/pregunta/opción UUID | Convertir UUID a INTEGER o asumir recorrido lineal | Aprobar contrato; conservar bloqueo, sin contar todas las preguntas |
| Participation | PostgreSQL | Agregado, pasos y límite histórico | `RepositorioParticipacion`, `UnidadTrabajo` | Lectores y UoW reales, escritor ausente | Duplicados, pérdida de duración y referencias falsas | Resolver esquema y FK antes de crear escritor/migración |
| Identity / Scheduling | Participation inicio | Consentimiento, cupos y autorización atómica | `IdentityPort.autorizar_inicio`, `SchedulingPort.autorizar_nuevo_intento` | Solo fakes; no reserva/consumo SQL integrado | Carrera comprobar–crear | Misma transacción y protocolo compartido, aún pendientes |
| Participation | Evaluation | Evidencias y resultados | `ServicioEvaluacion`, Strategy y puertos | Dominio real, persistencia académica simulada | Publicar nota sin política o commit | No componer motor oficial ni persistir notas en 8A |

## Diagnóstico verificable

- `domain/entities.py`: Participacion conserva asignación y membresía INTEGER;
  Intento conserva duración individual y devuelve objetos nuevos inmutables;
  PasoSimulacion conserva una selección por decisión. VENCIDO no es una
  clasificación académica. No se cambia el dominio ni la política de rutas.
- `application/services.py`: inicio supone una participación existente; decisiones
  y progreso dependen de Cases; cierre conserva respuestas. Los puertos Identity
  de titularidad/consentimiento aún no tienen adaptador para este agregado.
- `infrastructure/queries.py`: solo lectura de tablas del ER recibidas por
  parámetro; requiere duración histórica y estados/zonas explícitos.
  `unit_of_work.py` comparte Session, confirma o revierte, pero no crea escritores.
- `api/router.py`: siete rutas provisionales, con IDs INTEGER.
  `app/main.py` no importa ni registra ese router.
- `identity/application/academic_identity.py`: los únicos sistemas reconocidos
  son CASES y SCHEDULING; no se añade PARTICIPATION ni se genera una identidad.
- `scheduling/infrastructure/models.py`: convocatoria → sesión → versión tiene
  FK UUID reales. `programar_sesion.py` exige PUBLICADO y duración permitida.
  `validar_ingreso.py` comprueba código, titularidad, estado EN_CURSO y ventana.
- `cases/application/services/caso_service.py`: la versión publicada no admite
  edición por su flujo normal, pero puede archivarse. Su API docente no es una
  API de contenido estudiantil y no debe reutilizarse exponiendo el detalle entero.
- Las migraciones integradas contienen usuario, casos/versiones/preguntas/opciones,
  sesiones/convocatorias y asociaciones académicas. No contienen participacion,
  intento, paso_simulacion, asignacion_caso, grupo_estudiante ni consentimiento.

`infrastructure/PERSISTENCIA.md` y `PLAN_INTEGRACION_POSTGRESQL.md` describen fases
anteriores en martin, con Alembic entonces vacío. Ese estado histórico ya no es
el actual. Siguen vigentes sus límites del agregado: falta de escritor, duración
histórica, consentimiento, mapeo de resultados, ramificación y consumo concurrente.

## Implementación y validación

### Qué se conecta realmente

1. `api/dependencies.py` consume `obtener_estudiante_actual` y
   `obtener_estudiante_scheduling` de Identity: Bearer, JWT, cuenta activa, roles
   actuales y vínculo persistente inequívoco. No lee cabeceras de identidad ni IDs
   de cliente. La adaptación cadena decimal → INTEGER representa la **misma PK
   usuario.id_usuario**, no una conversión INTEGER/UUID ni una membresía.
2. `EstudianteAutenticado` conserva su campo interno `id_estudiante` por
   compatibilidad y añade `id_estudiante_scheduling` UUID y el contexto de
   convocatoria del JWT. Los campos adicionales son opcionales para conservar los
   dobles antiguos; la dependencia real siempre entrega el UUID resuelto. Ninguno
   se recibe como solicitud HTTP. No se cambia la firma pública de Facade.
3. `application/integration_ports.py` describe una consulta nueva de contexto UUID,
   **separada** de los puertos INTEGER antiguos. Su resultado inmutable conserva
   estudiante Scheduling, convocatoria, sesión, caso, versión exacta, número y
   duración. La ampliación descrita al final conserva también el UUID de rúbrica
   y su version_regla. No contiene corrección, criterios, niveles, nota ni código
   de acceso.
4. `infrastructure/integration.py::ConsultaIngresoSQLAlchemy` usa una Session
   proporcionada por el llamador. Relee cuenta/rol; reutiliza el resolver y
   `ValidadorConvocatoriaScheduling.validar_contexto`, luego `validar_ingreso` de
   Scheduling. No replica sus reglas de horario o estado. Solo después lee la
   versión asignada mediante el nuevo contrato de Cases.
5. `cases/application/published_version.py` es una consulta pública **interna** de
   metadatos, sin HTTP ni acceso docente privilegiado. Exige la versión exacta
   PUBLICADO y la existencia de su caso; no elige la versión más reciente. Es el
   único archivo añadido fuera de Participation/pruebas: necesario porque el
   servicio existente de Cases expone detalle docente con corrección y requiere
   propiedad del docente. No se modificó ninguna regla de publicación o edición.

La consulta no hace commit ni rollback propio, no crea Session/motor/tablas y
desactiva autoflush para no escribir cambios ajenos al leer. El llamador debe
revertir y cerrar su Session ante errores. SQLAlchemy parametriza los filtros.
Errores de titularidad/código/estado se traducen a AccesoDenegado; versión no
disponible a RecursoNoDisponible; política/infraestructura a ReglaPendiente, sin
publicar SQL ni credenciales. Errores inesperados no se ocultan.

**Esta consulta es una fotografía, no una autorización transferible.** No hay
endpoint nuevo ni composición que permita usarla para iniciar. No se conecta a
SchedulingPort como si sus UUID fueran INTEGER. Tampoco permite seleccionar una
versión desde el cliente. Una versión archivada impide esta preparación para un
nuevo ingreso; no se cambia el tratamiento de intentos históricos, aún pendiente.

### Qué permanece bloqueado y por qué

- `obtener_facade` conserva 503 INTEGRACION_NO_CONFIGURADA después de autenticar;
  `main.py` conserva el router sin registrar. Por ello no hay lectura/escritura de
  intentos reales, propios o ajenos, ni una alternativa para eludir RF-22.
- Sin una política autorizada, `validar_ingreso` lanza
  PoliticaTemporalNoDisponible y la consulta falla cerrada. No se creó una fórmula
  de tolerancia ni se adoptaron valores de fixtures como política productiva.
- No se crean modelos ni migraciones. Falta aprobar si Participation conserva el
  ER INTEGER con relaciones reales demostrables o adapta sus contratos a las
  entidades UUID ya implementadas. No existen tablas de correspondencia ni datos
  que permitan asumir asignación=sesión, membresía=convocatoria o decisión=pregunta.
- Faltan provisión idempotente de participaciones, consentimiento y permisos
  extraordinarios reales, relación con convocatoria, duración histórica del intento
  y contrato de recorrido. No se persisten calificaciones ni se incorpora Evaluation.

### Atomicidad y concurrencia: límite que no se cruza

El ServicioInicio actual abre su UoW pero sus puertos externos no reciben esa
transacción ni reservan cupos. La nueva consulta **no** resuelve esa atomicidad.
No se implementó comprobar en una Session y crear un intento en otra.

Contrato transaccional que debe acordarse antes del escritor:

1. Una Session/UoW para autorización vigente, cupo/permiso y creación. Ningún
   adaptador intermedio puede confirmar por su cuenta.
2. Bloquear la sesión y convocatoria, revalidar pertenencia y contexto, y después
   participación/intento en un orden global aprobado. Scheduling ya bloquea sesión
   en `cambiar_estado_sesion`; retiro de convocatorias, Worker, permisos y nuevos
   escritores deben respetar el mismo protocolo. No basta añadir FOR UPDATE a una
   consulta aislada que devuelve un DTO después de liberar su transacción.
3. Revalidar versión/publicación y política bajo ese límite. Coordinar con Cases
   archivado y estabilidad de versión; su repositorio actual confirma sus propias
   escrituras y no debe llamarse para escribir dentro de la UoW de Participation.
4. Usar un instante del servidor coherente para autorizar y registrar inicio,
   después de adquirir bloqueos; acordar el evento temporal exacto que representa
   ingreso. Conservar límite individual histórico, sin reconstruirlo desde duración
   mutable. El simple paso del tiempo tampoco se resuelve con un bloqueo de filas.
5. Complementar con unicidad de número/participación e intento activo, guardado con
   estado esperado y FK completas, una vez aprobado el DDL. Probar dos conexiones
   PostgreSQL: doble inicio, cierre/retiro simultáneo, revocación/cupo y rollback.

Las pruebas existentes de fakes y el bloqueo real del lector no demuestran un
escritor concurrente de intentos. No se añadió un escritor ficticio para declarar
esa cobertura. Sigue pendiente la prueba de asociación participación–intento–caso
con las FK definitivas, porque ese esquema no existe.

### Pruebas preparadas, NO ejecutadas

`backend/tests/integration/test_participation_8a.py` reutiliza las fixtures de
login y el laboratorio PostgreSQL corregido. Parametriza SQLite/PostgreSQL e
inyecta exclusivamente configuración JWT de prueba, Session y reloj/ventana
sintéticos cuando la prueba lo requiere. Las rutas de sonda solo existen en la
app de pruebas. Cubre:

- Login/JWT y resolución SQL reales hasta la dependencia HTTP de Participation;
  ausencia, invalidez, expiración, manipulación, cuenta inexistente/inactiva y rol.
- Cuenta sin asociación, asociación ambigua y cabeceras/query de suplantación.
- Fachada cerrada para inicio, lectura, escritura y resultados aunque haya JWT
  válido y se cambien IDs de URL; esto demuestra cierre, no titularidad SQL del
  agregado pendiente.
- Convocatoria ajena/inexistente/retirada, contexto ausente, código incorrecto y
  estados de sesión no permitidos, reutilizando las reglas existentes.
- Bloqueo sin política; positivo con política **sintética** que conserva versión
  exacta aunque exista otra posterior; rechazo de versiones no publicadas.
- Versión inexistente; FK reales que impiden convocatoria sin sesión y sesión sin
  versión, con rollback que conserva las relaciones originales.
- Fallos SQL/resolver sin conceder acceso y ausencia de flush/commit de cambios
  pendientes de una Session prestada.

Los errores de infraestructura se inyectan con mocks. SQLite usa el restaurador
UTC exclusivo de fixtures existente porque pierde offsets; no se introdujo esa
conversión en producción. Los positivos SQL no aprueban RF-22 ni persistencia del
agregado. Las pruebas anteriores de duplicados, propiedad, rollback y lectores
permanecen; las de concurrencia del futuro escritor siguen pendientes.

Se actualizaron aserciones de `participation/tests/test_api.py` y
`test_http_functional.py`: sin JWT ahora corresponde **401 NO_AUTENTICADO** en
lugar del antiguo stub 503 SEGURIDAD_NO_CONFIGURADA. Se conservan las aserciones
de repositorio intacto y se exige WWW-Authenticate. El caso de token inventado
inyecta un verificador JWT real de prueba para comprobar 401 sin depender de
configuración local. No se debilitó una aserción ni se omitió un caso.

### Archivos de esta entrega

- Modificados: `api/dependencies.py`, `README.md`, `api/HTTP.md`,
  `tests/test_api.py`, `tests/test_http_functional.py` de Participation.
- Nuevos: este informe, `application/integration_ports.py`,
  `infrastructure/integration.py`, `cases/application/published_version.py` y
  `backend/tests/integration/test_participation_8a.py`.
- No se cambia main.py, configuración global, migraciones, modelos, dominio,
  Facade ni servicios académicos existentes. No se consultaron datos del equipo.

### Orden de la próxima integración y decisiones del equipo

1. Maicol y Martín: aprobar vínculo persistente de participación con convocatoria,
   origen de asignación/membresía, responsable de provisión y cardinalidad. La FK
   sesión→versión ya existe; no es un bloqueo por ausencia de esa relación.
2. Juan Andrés y Martín: aprobar contrato de preguntas/decisiones y opciones UUID,
   recorrido ramificado y referencia histórica. Elegir evolución de contratos y
   compatibilidad HTTP, sin convertir identificadores ni generar aliases arbitrarios.
3. Alejandro: consentimiento/permiso y titularidad del agregado desde esos vínculos;
   confirmar transacción para revocación y consumo, sin inventar datos históricos.
4. Responsable académico y Maicol: definir RF-22, fuente autorizada, límites e
   inclusión de extremos. Cualquier cambio desde HTTP debe seguir rechazándose.
5. Equipo: aprobar DDL y duración histórica, migración aditiva coordinada desde la
   única cabeza actual; implementar escritor/UoW y protocolo de bloqueos. Solo
   entonces preparar/ejecutar migración en laboratorio vacío, verificar ida/vuelta,
   concurrencia y rollbacks; nunca aplicar automáticamente a una base compartida.
6. Conectar Facade, probar todos los adaptadores juntos y recién considerar su
   registro HTTP. Los criterios de evaluación y notas oficiales quedan para otra fase.

### Comandos para ejecución del usuario

Desde la raíz de `proyecto-nuclear-2`, sin editar .env. No necesitan una URL externa:

```powershell
# SQLite y comprobaciones HTTP previas, en un PowerShell dedicado sin el opt-in:
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/integration/test_participation_8a.py backend/app/modules/participation/tests/test_api.py backend/app/modules/participation/tests/test_http_functional.py -q -rs --tb=short

# En otro PowerShell dedicado, con Docker y la imagen local postgres:17 disponibles:
$env:SPS_TEST_IDENTITY_MAPPING_DOCKER='1'
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/integration/test_participation_8a.py -q -rs --tb=short
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

El fixture crea y elimina exclusivamente contenedores nuevos; no habilitar URLs de
bases del equipo para sustituirlo. Sin opt-in, PostgreSQL se omite explícitamente;
esas omisiones no cuentan como aprobadas. No se predice un número de pruebas
aprobadas: queda pendiente la ejecución local y revisión de sus resultados.

### Comprobaciones estáticas realizadas

- AST y compilación en memoria de los siete Python creados/modificados: sintaxis
  válida, sin importar ni ejecutar esos módulos. Esto no demuestra recolección de
  pytest, inyección FastAPI ni comportamiento SQL en ejecución.
- Grafo de revisiones leído mediante AST: única cabeza
  `20261031_academic_identity`. No se invocó upgrade/downgrade ni se modificó Alembic.
- `git diff --check`: sin errores; también se verificó whitespace de los cinco
  archivos nuevos, que el diff normal no incluye por no estar rastreados.
- Diff de este incremento: cinco archivos existentes modificados y cinco nuevos;
  se preservaron los cambios locales de fases previas. Sin commits ni cambios de
  rama. No se ejecutaron pytest, Docker, capturas ni conexiones a bases.

## Ampliación 8A tras la auditoría de patrones

Esta sección distingue el trabajo que ya estaba preparado del añadido en la
continuación. La línea base 983 aprobadas / 38 omitidas sigue siendo un resultado
anterior reportado, no una ejecución del código 8A actual. No se ejecuta pytest.

### Matriz al iniciar esta continuación

| Origen | Destino | Información / contrato | Estado encontrado | Riesgo | Acción de esta continuación |
| --- | --- | --- | --- | --- | --- |
| Identity | Participation HTTP | JWT, rol y UUID: dependencias públicas de Identity | Código SQL real ya conectado en la dependencia, aún pendiente de pruebas 8A | Confundir autenticación con titularidad de participación | Conservar; no reinterpretar cuenta INTEGER como UUID o membresía |
| Scheduling | Participation | Convocatoria, sesión y ventana: validar_ingreso | Consulta interna existente; RF-22 cerrado por defecto | Usar una lectura como reserva de autorización | Conservar; sin escritor ni endpoint alternativo |
| Cases | Participation | Versión publicada exacta: consultar_version_publicada | Consulta de versión real; su proyección no incluía referencia de rúbrica | Asociar después una rúbrica de otra versión o usar la más reciente | Añadir solo referencia real desde la FK de la versión |
| Participation | PostgreSQL | Agregado / RepositorioParticipacion / UoW | Lectores y UoW; ningún escritor ni tablas del agregado integradas | Duplicidad, FK inventadas, autorización fuera de transacción | No implementar escritura hasta aprobar las relaciones faltantes |

### Implementación añadida y contrato ampliado

La revisión funcional conserva estos límites de los requisitos centralizados:

| Requisito | Código disponible | Límite para la integración real |
| --- | --- | --- |
| RF-10 / RF-11 | ServicioDecisiones, ServicioProgreso y entidades inmutables | Falta escritor y contrato UUID de recorrido/decisiones |
| RF-12 | Inicio/fin y asociación del intento en el dominio | Falta esquema integrado del agregado y trazabilidad histórica persistida |
| RF-13 / RF-14 | ServicioEvaluacion, Strategy, calculador y lectura autorizada de resultados | Sin políticas definitivas ni repositorio de resultados conectado; no se publican notas |
| RF-22 | validar_ingreso con política del servidor | Sin política aprobada sigue cerrado |
| RF-23 | Reloj inyectado y vencimiento individual con conservación de selecciones | Falta persistir el límite histórico; no se reconstruye desde programación mutable |
| RF-24 | Estrategias parcial/ausencia y pendientes explícitos | Sin criterio académico completo ni mapeo definitivo de ausencia; no se inventan intentos o ceros oficiales |
| RF-25 | Puertos de autorización de repetición y rechazo de intento activo | Falta consumo/reserva de permiso y cupo en la transacción del inicio |

Se verificó `RubricaModel.version_caso_id`: FK a `version_caso.id`, NOT NULL y
UNIQUE. Es una relación existente; no se inventa una asociación nueva. Además,
`ValidadorRubrica` ya exige rúbrica al publicar por la cadena de Cases (RF-09 y
RF-17). No se cambió esa validación.

- `cases/application/published_version.py`: SELECT de metadatos con join por
  `rubrica.version_caso_id = version_caso.id`. Conserva el filtro PUBLICADO y el
  ID exacto de Scheduling. `ReferenciaVersionPublicada` añade `rubrica_id: UUID`
  y `version_regla: str`; si falta la rúbrica propia no devuelve referencia.
- `participation/application/integration_ports.py`: la proyección interna
  `ContextoIngresoParticipacion` conserva esos dos campos adicionales.
- `participation/infrastructure/integration.py`: transfiere las referencias por
  nombre de campo, después de superar la validación de Scheduling. No calcula,
  no interpreta version_regla como política oficial y no carga criterios,
  niveles ni valoraciones de opciones.

Es una ampliación del nuevo contrato interno 8A, todavía no publicado por HTTP;
no cambia Facade, sus puertos INTEGER anteriores ni esquemas HTTP. Los consumidores
localizados son la propia consulta integrada y sus pruebas. No se adapta este DTO
a ReferenciaAcademica de Evaluation, que todavía usa INTEGER: esa incompatibilidad
sigue pendiente. El UUID y version_regla son referencias observadas, no una
instantánea histórica persistida ni garantía de inmutabilidad transaccional.

La consulta tampoco reemplaza una validación completa de publicación por la
cadena de Cases: lee su estado y comprueba el vínculo necesario. No vuelve a
publicar ni repara datos históricos inconsistentes. No se modificó ningún ORM,
migración ni base de datos.

### Escritura y concurrencia: resultado de la revisión

No hay una operación SQL nueva de escritura del agregado que pueda conectarse
con seguridad al contrato actual. Faltan asignación/membresía INTEGER y su vínculo
con convocatoria UUID, consentimiento y permisos, mapeo de decisiones a preguntas,
provisión de participaciones y límite individual histórico. Las tablas integradas
no materializan esas dependencias. Una tabla local de equivalencias sin evidencia
no resolvería su significado ni legitimaría datos históricos.

Se conserva la UoW y los tests de duplicados/rollback previos; no se presenta esa
conservación como escritor implementado. La consulta es de solo lectura y no reserva
ingreso. Las lecturas pueden quedar desactualizadas respecto de transacciones
concurrentes o del identity map de una Session prestada. No debe emplearse su
resultado para autorizar una inserción posterior; sigue siendo necesario el
protocolo transaccional compartido descrito arriba antes de habilitar un inicio.

RF-22 continúa cerrado con PoliticaIngresoNoConfigurada. No se introducen valores
de tolerancia. La fachada sigue respondiendo 503 tras autenticar y su router no se
registra en main.py. La protección real actual frente a acceso cruzado al agregado
es mantenerlo inaccesible; no se afirma una titularidad SQL que todavía no existe.

### Pruebas ampliadas, pendientes de ejecución local

Se conserva la matriz 8A de SQLite/PostgreSQL y sus controles JWT/roles/titularidad.
La fixture nueva añade únicamente en el laboratorio una referencia de rúbrica con
version_regla sintética, sin declarar una fórmula aprobada. Se amplía el positivo
para crear otra versión publicada con otra rúbrica y exigir que la consulta
conserve ambas referencias originales, sin tomar las más recientes.

Se agregan regresiones para:

1. Una sesión que referencia una versión sin rúbrica propia: se rechaza aunque
   otra versión del mismo caso sí tenga rúbrica. El dato inconsistente se crea
   únicamente en la fixture negativa; no se eliminan datos del equipo.
2. Ausencia de RF-22: no se llega a consultar versión/rúbrica.
3. Fallo SQL inyectado en política o consulta Cases: no se obtiene contexto ni se
   publican detalles privados. Estas fallas son simuladas, no cortes reales de red.
4. FK de rúbrica a versión existente y UNIQUE de rúbrica por versión: una
   escritura inválida de laboratorio falla y su rollback conserva las referencias
   originales. Se comprueba la restricción vigente, no se crea otra en esta fase.

Ninguno de estos positivos sintéticos demuestra un ingreso productivo ni una
calificación oficial. Persistencia del agregado, doble inicio y concurrencia con
cierre/retiro siguen pendientes de implementar y verificar con dos conexiones
PostgreSQL. Las FK y rollbacks ya preparados solo cubren el esquema vigente y
las fixtures indicadas en sus pruebas.

### Patrones conservados

| Patrón | Componentes revisados | Cambio en esta continuación |
| --- | --- | --- |
| Proxy | ProxySeguimiento, ProxyExcepciones, ProxyAdministracionUsuarios | Ninguno |
| Facade | ParticipacionFacade y servicios delegados | Ninguno |
| Builder | IConstructorCaso y ConstructorCaso | Ninguno |
| Chain of Responsibility | ValidadorCaso, eslabones y construir_cadena_publicacion | Ninguno |
| State | EstadoSesion, estados concretos y transicionar | Ninguno |
| Observer | GestorEventosAcademicos, ObservadorNotificaciones y registro | Ninguno |
| Strategy | IEstrategiaEvaluacion, estrategias y ServicioEvaluacion | Ninguno |

No se modifican documentos ni capturas del informe de patrones. La consulta
adicional de referencias no cambia las responsabilidades ni los contratos de esos
patrones; no se agrega ningún patrón para justificar este incremento.

### Archivos intervenidos únicamente en esta continuación

1. `backend/app/modules/cases/application/published_version.py`: lectura de la
   referencia real de rúbrica junto a la versión asignada.
2. `backend/app/modules/participation/application/integration_ports.py`: campos
   de referencia, sin equivalencia con los INTEGER de Evaluation.
3. `backend/app/modules/participation/infrastructure/integration.py`: conserva
   esas referencias en la proyección, sin escritura.
4. `backend/tests/integration/test_participation_8a.py`: fixture y regresiones.
5. `backend/app/modules/participation/README.md`: resumen del alcance actual.
6. Este informe: matriz inicial, diferencias, límites y pasos de verificación.

No se recrearon archivos ni se sobrescribieron las fases previas; estos seis
archivos ya existían al comenzar esta continuación. Los diez archivos de la
preparación inicial siguen distinguidos en el apartado histórico anterior.

Comprobaciones efectivamente realizadas en esta continuación:

- AST y compilación en memoria de los cuatro Python modificados: correctos, sin
  ejecutar sus módulos ni pruebas. Inyección HTTP y comportamiento SQL siguen
  pendientes de la ejecución del usuario.
- Comparación de 14 archivos centrales de los siete patrones contra ee025d2:
  idénticos al normalizar finales de línea. Incluye proxies, fachada, estrategias,
  servicio de evaluación, Builder, servicio de Cases, cadena, State y Observer.
- Lectura estática del grafo Alembic: única cabeza declarada
  `20261031_academic_identity`. No se comprueba su aplicación a ninguna base.
- `git diff --check`: correcto. También se revisó whitespace de estos seis
  archivos, incluyendo los no rastreados, respetando los finales CRLF existentes.
- Sin pytest, Docker, acceso a BD, migraciones, commits ni cambios de rama.

Los comandos PowerShell anteriores continúan siendo los recomendados: específicos
primero, suite completa después, con el laboratorio Docker propio cuando se
habilite su opt-in. La fase 8 no se declara terminada; 8A queda preparada para
esa verificación y conserva los bloqueos explícitos del inicio real.

## Ajuste controlado posterior a BD2-02C — 2026-11-02

La inspección encontró una invocación fija a `consultar_version_publicada` en
`ConsultaIngresoSQLAlchemy._consultar`. El puerto `ConsultaIngresoParticipacion`
permite sustituir toda la consulta de ingreso, pero no permite inyectar esa
dependencia interna conservando los controles de la implementación SQL. Las
dependencias HTTP tampoco ofrecían ese punto de composición.

Se añadió exclusivamente:

- `ConsultaVersionPublicada`, protocolo callable en
  `cases/application/published_version.py`, con la firma y retorno existentes:
  Session del llamador, `version_id: UUID` y `ReferenciaVersionPublicada`.
- Un parámetro interno opcional y keyword-only `consulta_version` en el
  constructor de `ConsultaIngresoSQLAlchemy`. Si es `None`, selecciona la función
  SQL real existente al construir el objeto. Si se proporciona, conserva esa
  dependencia explícita. No es una opción HTTP ni una configuración del cliente.
- Regresiones en `tests/integration/test_participation_8a.py`: delegación SQL
  real frente al comportamiento predeterminado, versión asignada frente a una
  posterior, ausencia de flush/commit, rechazo de versiones no publicadas o sin
  rúbrica, errores de dependencia sin fallback ni detalles privados y orden de
  autorización anterior a la consulta de Cases. Son 14 casos parametrizados
  adicionales por motor (28 al ejecutar ambos), sin retirar pruebas anteriores.

El contrato obliga al proveedor a leer solo la versión publicada solicitada y
su rúbrica propia, sin escribir, autoflush, commit ni cerrar la Session. El
proveedor predeterminado no cambió. La inyección es una dependencia confiable
compuesta por el servidor; no autentica por sí sola ni sustituye las comprobaciones
anteriores. No se añadió ningún proveedor ER28 ni retorno parcial de prueba a
producción.

Se conservan sin cambios el DTO `ContextoIngresoParticipacion`, los puertos
existentes, las dependencias HTTP y la fachada que devuelve 503. Identity relee
cuenta activa/rol, el resolver verifica asociación, el validador comprueba contexto
y titularidad de convocatoria y Scheduling mantiene código, estado, reloj y
política. RF-22 sin política sigue bloqueando antes de Cases. Luego se pasa
exactamente `sesion.version_caso_id` y se conservan `rubrica_id`/`version_regla`.
Las mismas excepciones se traducen a acceso denegado, recurso no disponible o
regla pendiente. No hay alternativa que elija otra versión al fallar la consulta.

El ensayo con dos versiones y el delegado usa SQL real de laboratorio; las
pruebas de errores y orden usan callables controlados solo en pruebas. Las rutas
HTTP existentes se prueban mediante TestClient/ASGI con JWT de laboratorio; no
es una prueba de red pública ni de autorización académica definitiva. Las
ventanas positivas son sintéticas y no aprueban RF-22.

La compatibilidad ER28 continúa pendiente: faltan representación de versión
asignada, correspondencias verificadas INTEGER/UUID, versión de regla y valores
por opción/criterio. Preparar este punto de inyección no resuelve esos datos ni
autoriza el inicio productivo de intentos. No se alteraron ORM, ER, migraciones,
los siete patrones, datos persistentes ni PostgreSQL del equipo; no se inicia
BD2-03.

### Validación ejecutada de este ajuste

Se ejecutó primero `backend/tests/integration/test_participation_8a.py` y después
la suite completa:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Para aislar la ejecución, únicamente en el proceso hijo se retiraron
`TEST_DATABASE_URL`, `SPS_IDENTITY_TEST_URL` y `SPS_PERSISTENCE_LAB_URL`; se fijaron
`SPS_TEST_POSTGRESQL=0`, `SPS_TEST_IDENTITY_MAPPING_DOCKER=1` y
`PYTHONDONTWRITEBYTECODE=1`. `.env` y el entorno persistente no cambiaron. Cases y
Scheduling usaron SQLite aislado; el fixture opt-in de Identity/8A creó sus propios
contenedores PostgreSQL 17 con nombres aleatorios, etiquetas, tmpfs y puertos
dinámicos de localhost. Las migraciones de las pruebas solo se aplicaron allí o
en SQLite en memoria, no a una base persistente.

Resultado general: **1142 passed, 38 skipped, 0 failed, 0 errors, 1 warning**, en
104.01 segundos. La advertencia es `StarletteDeprecationWarning` sobre TestClient
y httpx; no se instalaron dependencias para modificarla. Las 38 omisiones son
29 de persistencia Identity sin URL independiente, 3 de conexión PostgreSQL de
Participation deshabilitadas y 6 de su laboratorio sin URL. No se consideran
aprobadas. El incremento frente a 1114/38 es de 28 aprobaciones parametrizadas.

Se conservan en el reporte los dos intentos específicos iniciales que no pudieron
preparar PostgreSQL: ambos tuvieron 53 aprobadas SQLite, 53 errores de setup, 0
fallidas y 1 advertencia. Primero Docker no pudo inspeccionar `postgres:17`;
después la preparación recibió una lista de puertos vacía (`IndexError` en el
fixture existente). No se cambiaron fixtures, se omitieron casos para ocultarlo
ni se afirmó que esos errores fueran aprobaciones. Una vez disponible la
infraestructura, la suite general completa sí ejecutó y aprobó los casos de 8A
en ambos motores. La causa de esos fallos transitorios de Docker no queda
diagnosticada definitivamente en este ajuste acotado.

Repetición específica final, sin cambios adicionales de código: **106 passed,
0 skipped, 0 failed, 0 errors, 1 warning**, en 22.55 segundos. Son 53 casos
SQLite y 53 PostgreSQL, incluidos los 14 nuevos por motor. La repetición confirma
el resultado de 8A dentro de la suite general, sin certificar estabilidad global
de Docker frente a los dos fallos transitorios anteriores.

El cierre por hashes identifica cambios únicamente en los dos archivos de código
citados, el archivo de pruebas 8A y este documento; sin archivos nuevos ni pérdida
de los demás avances locales. `git diff --check`, análisis sintáctico de los tres
Python y comprobación de whitespace de los cuatro archivos: correctos.
