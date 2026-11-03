# BD2-02C — Compatibilidad funcional de Cases con ER28

Fecha: 2026-11-02. Rama: `feature/integracion-backend`.

**Respuesta:** el ER28 permite leer un caso y navegar sus relaciones INTEGER,
pero no sustituye al Cases versionado actual sin perder semántica. No se puede
conservar directamente la referencia a versión asignada, sus UUID públicos ni
la valoración independiente opción×criterio. Cambiar nombres o convertir tipos
no resuelve esas pérdidas.

## 1. Experimento ejecutado

Se reutilizó el SQL exacto y el ciclo seguro del laboratorio BD2-02B, sin cambios.
Se creó el esquema completo en PostgreSQL 17.11 y se verificaron sus 28 tablas,
144 columnas, 28 PK, 40 FK, 19 UNIQUE y 47 índices de soporte. No hubo ORM,
Alembic, tablas auxiliares ni ejecución del backend contra el esquema experimental.

El [fixture](datos_sinteticos.sql) representa 1 caso, 3 escenas, 3 decisiones,
6 opciones, 1 rúbrica, 2 criterios, 4 niveles, 1 objetivo, 1 personaje en 2 escenas,
1 pista, 2 asignaciones y sus padres sintéticos: roles, usuarios, grupo y matrícula.
No se crearon intentos, respuestas, evaluaciones ni resultados oficiales. Fechas,
estados, límites y porcentajes del fixture son datos de ensayo, no políticas.

La [consulta](leer_caso.sql) recupera el grafo por asignación con agregados
independientes, sin duplicar decisiones por combinaciones de criterios/personajes.
Ordena escenas, decisiones y opciones por `orden`, aun cuando se insertaron fuera
de orden. No deduce la primera escena a partir de ese orden.

Lecturas y rutas observadas:

| Elemento | Resultado ejecutado |
|---|---|
| Asignación 401 | Caso INTEGER 10, rúbrica 20 |
| Escenas | 101, 102, 103; decisiones 201, 202, 203 |
| Opciones | 301/302, 303/304, 305/306 |
| Referencias a criterios | Decisión 201→21; decisiones 202/203→22; ambos criterios de rúbrica 20 |
| Secuencia explícita A | Opciones 301,303,305: escenas 101→102→103, después sin arco |
| Secuencia explícita B | Opciones 302,305: escenas 101→103, después sin arco |
| Opción de otra escena / selección posterior a NULL | Rechazadas por el verificador experimental |
| Asignación inexistente | JSON `null`, sin elegir otro caso |

Son lecturas internas de autoría con corrección/justificación sintéticas: no
respuestas HTTP estudiantiles. No se calcula progreso, se aplica Strategy ni se
interpreta ausencia de arco como cierre académico. No se demuestra publicación,
autenticación, ingreso temporal o titularidad de estudiante.

## 2. Resultado y reproducibilidad

El [ejecutor](run_cases_experiment.py) terminó dos ejecuciones independientes
con **37/37 comprobaciones**, cero fallidas en cada ejecución final. No son
pruebas pytest del backend ni se suman como 74 casos distintos. No hubo SQLite.

| Grupo | Comprobaciones |
|---|---:|
| Base vacía, catálogo inicial y catálogo final idéntico | 3 |
| Lectura del grafo, orden, relaciones y asignación inexistente | 8 |
| Secuencias explícitas y entradas inválidas | 5 |
| Rechazos del esquema Pydantic actual de Cases | 3 |
| FK/UNIQUE con errores PostgreSQL esperados | 4 |
| Campos/tablas sin representación directa, errores esperados | 6 |
| Versión no fijada, restauración y dos asignaciones | 3 |
| Cruces entre casos admitidos por ER y rechazados por lector | 4 |
| Rollback de todos los ensayos, lectura original conservada | 1 |
| Total | 37 |

Evidencia de intentos, incluidos fallos sin ocultarlos:

| Evidencia | Resultado | Limpieza |
|---|---|---|
| [b90d0b54](resultado_b90d0b54fbf94df19b18f45641626520.json) | Sin motor Docker; 0 comprobaciones. No había conexión al daemon, no se creó contenedor. | `not_created` |
| [2c52e203](resultado_2c52e203480b40ecae19c9da8a73889d.json) | 9 comprobaciones satisfechas y aborto: ausencia de asignación salía como NULL SQL vacío en psql; `json.loads` no podía interpretarlo. | `removed_verified` |
| [c13ddbee](resultado_c13ddbeecf4d4dac92e8cf472d5fdac6.json) | Lector corregido con COALESCE a JSON null; 37/37. | `removed_verified` |
| [7619a2c7](resultado_7619a2c727074a59b00553d124461295.json) | Repetición independiente del mismo código/SQL: 37/37. | `removed_verified` |

La corrección afectó solo la consulta nueva del laboratorio; no el ER ni la
expectativa de devolver ausencia. La primera evidencia hereda un mensaje genérico
de imagen no disponible; `docker version` identificó el motor apagado y la imagen
local se confirmó después de iniciarlo. No hubo pull ni Compose.

La suite productiva no se ejecutó. **1114 aprobadas y 38 omitidas es antecedente
histórico**, no una verificación nueva. Los 198 probes de BD2-02B son otra prueba.

## 3. Qué impide la compatibilidad

### Versión asignada: prueba negativa reproducible

1. Se lee asignación 401→caso 10 con título original, decisión original y rúbrica original.
2. En una transacción se cambian el título/introducción del caso 10, el enunciado
   de decisión 201 y el nombre de rúbrica 20.
3. Se vuelve a leer la misma asignación: su registro es idéntico, pero los tres
   elementos del contenido son diferentes. No existe referencia a una edición anterior.
4. Se revierte la transacción y la lectura completa vuelve a ser idéntica a la inicial.

El JSON conserva ambas lecturas. Además, PostgreSQL devuelve `42P01` al consultar
`version_caso` y `42703` para `asignacion_caso.version_caso_id`. Las dos asignaciones
401 y 402 obtienen el mismo contenido actual.

Esto demuestra que **las restricciones ER por sí mismas no fijan una versión**.
No demuestra que el servicio actual permita editar versiones publicadas: su
dominio sí restringe edición a BORRADOR. Una política futura de inmutabilidad por
caso podría proteger una sola edición, pero no añade al ER actual la familia de
versiones, número, UUID o procedencia de múltiples ediciones existentes.

### Matriz contra contratos reales

| Capacidad/contrato | ER28 observado | Backend actual y evidencia | Diagnóstico / adaptación necesaria |
|---|---|---|---|
| Identidad de caso/contenido | INTEGER autoincremental; cada hijo referencia su padre INTEGER | [CasoDetalleResponse](../../../app/modules/cases/api/schemas/caso_responses.py), líneas 16–70: UUID para caso, escenario, pregunta, opción, rúbrica, criterio y nivel | Pydantic real rechaza `caso_id` y IDs anidados (`uuid_type`). No convertir ni generar UUID; conservar contratos y resolver procedencias verificadas antes de mover datos. |
| Recuperación de escenas/preguntas | Escena→decisión→opción, ordenadas y con FKs | [EscenarioModel/PreguntaModel](../../../app/modules/cases/infrastructure/models/caso.py): dependen de versión y escenario UUID | Estructura de lectura anidada equivalente en parte; cambia raíz, identidad y atributos. `escena` tiene título/tipo y `decision` criterio obligatorio que no aparecen en la pregunta actual. |
| Referencia exacta publicada | `asignacion_caso.id_caso`; sin edición ni número | [ReferenciaVersionPublicada/consultar_version_publicada](../../../app/modules/cases/application/published_version.py), líneas 20–47: UUID caso/versión/rúbrica, número, `version_regla`; busca versión exacta PUBLICADO | Bloqueo central. No elegir última versión, reutilizar caso como versión ni inventar número 1. Aprobar representación de edición inmutable y procedencia dentro del límite de 28 antes de adaptar. |
| Rúbrica asignada | Única por caso; decisiones con un criterio obligatorio | [RubricaModel](../../../app/modules/cases/infrastructure/models/rubrica.py): única por versión, con `version_regla` | La referencia INTEGER existe y se lee, pero no representa por sí sola la rúbrica de una versión histórica. `version_regla` ausente confirmado (`42703`). |
| Valoración de opciones | Booleano correcto/incorrecto; una FK de criterio por decisión; niveles con logro porcentual | [ValoracionOpcionModel](../../../app/modules/cases/infrastructure/models/rubrica.py), línea 63: puntaje por par opción/criterio; [ValidadorMapeoOpciones](../../../app/modules/cases/domain/validators/eslabones.py), línea 76: cada opción debe valorar cada criterio | Falta `valoracion_opcion` (`42P01`) y el contrato exige `valoraciones`. Con 6 opciones/2 criterios se necesitarían 12 valores independientes, no representados por los 6 booleanos ni por pesos globales. No derivarlos sin política. |
| Nivel de criterio | Nombre y `logro_porcentaje` | [NivelRubrica/NivelResponse](../../../app/modules/cases/domain/entities/caso.py): `puntaje` y `descriptor` | No se acredita equivalencia entre porcentaje y puntaje; descriptor no existe (`42703`). |
| Datos del caso | Título e introducción teórica | [VersionCaso](../../../app/modules/cases/domain/entities/caso.py), línea 89: nombre, desarrollo situacional, contexto/historia y tiempo estimado | Título→nombre es una proyección simple; una introducción no sustituye sin aprobación dos textos separados. Tiempo estimado no existe (`42703`); duración de asignación no es su sustituto. |
| Estados y fechas | VARCHAR sin CHECK; default borrador, timestamps sin zona | EstadoCaso y fechas ORM con zona; [programar_sesion](../../../app/modules/scheduling/application/programar_sesion.py) comprueba PUBLICADO y fechas conscientes de zona | El rechazo Pydantic incluye enum para `borrador`. Requiere mapeo explícito de estados y política de zona para datos históricos; no se los da por equivalentes. |
| Objetivos, personajes, pistas y destinos | Se recuperan fielmente, con arcos opcionales por opción | El agregado Cases actual no contiene todos estos campos ni una política de ramificación completa | El destino también necesita conservar información adicional del ER. El ensayo verifica arcos; no define reglas de navegación académica ni invalidación. |

El candidato enviado al **esquema Pydantic productivo real** solo renombra datos
con correspondencia simple. Deja visibles todos los campos ausentes. El resultado
negativo completo está en `rechazo_contrato_CasoDetalleResponse`. No se presentó
ese candidato como DTO válido ni se construyeron entidades versionadas incompletas.

### Integridad de pertenencia

Se observaron rechazos `23503` para opción con decisión inexistente y asignación
con caso inexistente; `23505` para orden de decisión duplicado y segunda rúbrica
del mismo caso. Las referencias INTEGER necesarias sí funcionan.

En cambio, un destino de opción que existe en **otro caso**, y un criterio que
existe en **otra rúbrica/caso**, se aceptan (`00000`). El lector experimental los
rechaza por pertenencia, sin modificar FKs ni añadir triggers. No debe consumirse
la consulta sin estas guardas y una autorización real. Los ensayos se revierten.

## 4. Primer cambio productivo seguro propuesto — no implementado

**Separar la consulta de versión publicada de su invocación concreta en 8A,
preservando exactamente su contrato UUID y comportamiento.** Es un paso preparatorio,
no la solución del esquema ni una autorización para integrar ER28.

Alcance mínimo de una próxima iteración, si se autoriza:

1. En `cases/application/published_version.py`, declarar un contrato callable
   `ConsultaVersionPublicada` con la firma de `consultar_version_publicada`:
   Session del llamador y `version_id: UUID`, devolución `ReferenciaVersionPublicada`.
   La función SQL existente sigue siendo su implementación real y predeterminada.
2. En `participation/infrastructure/integration.py`, permitir inyectar esa consulta
   en `ConsultaIngresoSQLAlchemy` y usarla en lugar de la invocación fija de línea 61.
   Conservar `no_autoflush`, transacción del llamador, autorizaciones, política/reloj
   y traducción de errores. Nunca añadir fallback ER28, última versión o UUID inventado.
3. En pruebas de integración aisladas, comprobar igualdad de referencias con el
   camino anterior, versión inexistente/no publicada/sin rúbrica, fallo de consulta,
   ausencia de commits/escrituras y rechazo sin autorización. Dobles solo en pruebas.

No cambia DB, endpoints ni los siete patrones: mantiene las validaciones y Chain
de Cases, Facade/Strategy de Participation y sus reglas. La dependencia cruza módulos
como hoy, pero su punto de sustitución queda explícito. No se introduce un adaptador
productivo a este SQL porque no puede devolver honestamente la referencia completa.

**Cambio mínimo semántico indispensable para poder sustituir Cases:** aprobar la
representación persistente de una edición asignable e inmutable y su correspondencia
con los UUID existentes. Una posibilidad a evaluar dentro de las mismas 28 tablas
es un registro `caso` por edición y atributos explícitos de familia/número/procedencia,
incluida procedencia de hijos. Esto modifica atributos/significado del ER, requiere
aprobación y aún no resuelve la valoración multicriterio ni todos los campos ausentes.
No está demostrado que ER literal sin cambios preserve todos los contratos actuales.
Relajar UUID a INTEGER, hacer opcionales campos obligatorios o reemplazar versión
por caso no es una solución compatible.

## 5. Riesgos concretos para Scheduling y 8A

- Scheduling conserva `SesionProgramadaModel.version_caso_id` UUID con FK a
  `version_caso.id` ([modelo](../../../app/modules/scheduling/infrastructure/models.py),
  línea 54). `programar_sesion` verifica versión PUBLICADO y compara duración contra
  tiempo estimado del caso (líneas 59–76). Una asignación ER no satisface ese contrato.
- Convocatoria/estudiante/sesión UUID y control de titularidad no se obtienen del
  grupo/asignación por coincidencia de IDs. Este laboratorio no los resuelve ni prueba.
- [ContextoIngresoParticipacion](../../../app/modules/participation/application/integration_ports.py)
  conserva caso, versión, número, rúbrica y `version_regla`; no admite reemplazo por
  un solo id INTEGER. [ConsultaIngresoSQLAlchemy](../../../app/modules/participation/infrastructure/integration.py)
  relee Identity, valida convocatoria/horario y luego consulta exactamente la versión.
- Los [puertos INTEGER de Participation](../../../app/modules/participation/application/ports.py)
  pueden parecer cercanos al ER, pero no quedan conectados automáticamente a 8A.
  Mantenerlos separados evita asociaciones ficticias e inicio de intentos sin garantías.
- Sin preservar contenido/rúbrica histórica, recalificar respuestas podría usar datos
  distintos a los asignados. Las ediciones no deben sobreescribirse durante transición.
- Este ensayo no ejecutó una migración, recuperación histórica, estrategia de evaluación
  ni validación de ingreso. No certifica estas capacidades por haber leído el grafo.

## 6. Decisiones que requieren aprobación

1. Representación de múltiples ediciones/familias sin añadir una tabla 29: ¿se permite
   un caso por edición y qué atributos de procedencia/número se aprueban? Si no se
   permiten cambios al ER literal, reconocer la incompatibilidad y no retirar soporte.
2. Conservación de UUID públicos e históricos mediante correspondencias persistentes
   verificadas, sin derivarlos de INTEGER ni crear asociaciones por orden de filas.
3. Destino de las valoraciones opción×criterio, descriptores, textos separados,
   tiempo estimado y versión de regla. Mantener la funcionalidad actual hasta resolverlos;
   no sustituirla por una política académica más simple de forma unilateral.
4. Equivalencia explícita de estados y tratamiento de zonas horarias. La política de
   navegación, fin y modificación de rutas continúa pendiente donde no esté definida.

No se propone ampliación a 40 ni tablas permanentes nuevas. Mantener el backend
intacto durante el ensayo no aprueba la coexistencia permanente de tablas de soporte.

## 7. Aislamiento, limpieza y alcance de cambios

Las evidencias registran imagen PostgreSQL 17.11, red `none`, puertos vacíos, tmpfs
configurado y comprobado en `/proc/self/mountinfo`, identidad de DB/usuario y base
vacía inicial. SQL solo mediante TCP interno al contenedor recién creado.

| Intento con contenedor | ID completo | Resultado de limpieza |
|---|---|---|
| Lector inicial | `db485b07c2c0f86f0257e5d46e2030cf181b9823a8a43208dfa37cb502b941e7` | rm=0, inspect posterior=1, removed_verified |
| Ejecución completa 1 | `b7ef260e88e189818a8637ea8a4d04ef05b8b836e0aaba54913283549d671f8d` | rm=0, inspect posterior=1, removed_verified |
| Ejecución completa 2 | `9b78db598d6a606725515543a66922d955e0aed8e98f41708a0f948d8ee5aac8` | rm=0, inspect posterior=1, removed_verified |

El primer intento no creó contenedor. No se usaron bases, contenedores, volúmenes,
credenciales o conexiones del equipo; no hubo limpieza global. El ejecutor heredado
solo elimina su ID después de comprobar nombre/etiqueta/propiedad, dentro de finally.

Todos los archivos nuevos están en esta carpeta. No se modificaron BD2-02B, ER,
ORM, código productivo, migraciones, BD2-01, 8A, patrones o `.env`. Sin commit,
push, merge, cambio de rama ni BD2-03.

Cierre verificado: los 265 archivos preexistentes registrados (incluidos cambios
locales anteriores y referencias ignoradas por Git) conservan sus hashes; solo
hay nueve archivos nuevos, todos en la carpeta autorizada. Los seis hashes de
artefactos ejecutados coinciden con ambas evidencias satisfactorias. Los enlaces
locales resuelven, el script pasa análisis sintáctico y `git diff --check` no
presenta incidencias. Se comprobaron también los nueve archivos nuevos mediante
`git diff --no-index --check`, reconociendo CRLF como fin de línea de Windows,
sin incidencias de espacios. La rama continúa en `feature/integracion-backend`.
