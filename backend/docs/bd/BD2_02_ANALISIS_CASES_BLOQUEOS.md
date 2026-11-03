# BD2-02 — Selección de entidades de Cases y bloqueo de dependencias

**Resultado: análisis concluido; no hay un subconjunto no vacío de las seis entidades que pueda implementarse fielmente al ER mediante una migración aditiva con dependencias resueltas.** Se aplica la instrucción del usuario de detenerse antes de modificar código ante incompatibilidades de diseño.

Fecha: 2026-11-01. Rama verificada: feature/integracion-backend. No se inicia BD2-03.

## 1. Estado comprobado

- ER oficial: [sps.dbml](../../app/modules/identity/reference/sps.dbml), 28 tablas. No modificado.
- Base.metadata: **22 tablas**, incluidas las tres de BD2-01. No se incorporó ningún modelo nuevo.
- Cabeza Alembic única: **20261101_er28_base_academica**. Siete revisiones y ningún padre faltante, según lectura AST, sin ejecutar migraciones.
- No se verificó esquema aplicado en PostgreSQL ni se abrió ninguna conexión.
- Se preservan los cambios locales previos y todos los archivos no rastreados.

La inspección de modelos se realizó en memoria con creación de motores/conexiones bloqueadas. Los tipos Uuid de SQLAlchemy tienen representación genérica CHAR(32) al imprimirlos sin dialecto; los modelos declaran UUID y en PostgreSQL se compilan como UUID. Esa impresión no es una inspección física de PostgreSQL.

## 2. Entidades analizadas y dependencias oficiales

| Entidad oficial | PK y FK oficiales | Implementación cercana actual | Bloqueo concreto |
|---|---|---|---|
| objetivo_aprendizaje | id_objetivo INTEGER PK; id_caso INTEGER → caso.id_caso; UNIQUE(caso,orden) | No tiene ORM | caso.id_caso no existe; caso.id actual es UUID. No se puede elegir caso lógico o versión sin decisión |
| escena | id_escena INTEGER PK; id_caso INTEGER → caso.id_caso; UNIQUE(caso,orden) | escenario: UUID, FK version_caso_id UUID, orden/contexto | Ya existe equivalente parcial; no tiene título/tipo originales. Otra tabla escena dejaría dos autoridades sin correspondencia definida |
| personaje | id_personaje INTEGER PK; id_caso INTEGER → caso.id_caso | No tiene ORM | Mismo padre INTEGER ausente; hay que decidir si personaje es compartido por caso o pertenece a cada versión |
| personaje_escena | PK compuesta y FK INTEGER a personaje.id_personaje y escena.id_escena | No tiene ORM | Ambos padres oficiales están ausentes/bloqueados; escenario UUID no sustituye escena INTEGER |
| decision | id_decision INTEGER PK; id_escena INTEGER → escena.id_escena; id_criterio INTEGER → criterio_rubrica.id_criterio; UNIQUE(escena,orden) | pregunta UUID por escenario; valoracion_opcion une opción/criterio | Escena INTEGER ausente; criterio_rubrica.id_criterio tampoco existe: el actual usa id UUID. Además, un criterio obligatorio por decisión no equivale a varios aportes por opción |
| pista | id_pista INTEGER PK; id_decision INTEGER → decision.id_decision | No tiene ORM | Decisión oficial ausente/bloqueada. Apuntar a pregunta.id UUID cambiaría tipo/relación aprobados |

Los campos de texto no bastan para seleccionar una tabla «independiente»: las FK son obligatorias. Crear solo personaje_escena/pista tampoco evita esos padres. No se propone hacer nullable una FK, retirarla o apuntarla a una tabla ficticia para poder crear la tabla vacía.

## 3. Prueba técnica del bloqueo raíz

Fuentes actuales:
- [CasoModel, VersionCasoModel, EscenarioModel y PreguntaModel](../../app/modules/cases/infrastructure/models/caso.py).
- [Rúbrica, criterios y valoraciones](../../app/modules/cases/infrastructure/models/rubrica.py).
- [Registro compartido](../../app/db/models.py).

El original define caso.id_caso INTEGER. CasoModel define id: Mapped[uuid.UUID] y docente_creador_id UUID; contenido/estado/número están en VersionCasoModel. Por ello:
1. Una FK oficial a caso.id_caso no encuentra la columna en metadata.
2. Cambiar únicamente su destino a caso.id deja un INTEGER apuntando a UUID, incompatible para una FK PostgreSQL.
3. Declarar id_caso UUID permitiría una relación técnica, pero cambia el atributo oficial y no decide si el contenido sigue al caso o a una edición.
4. Apuntar a version_caso.id resuelve la identidad de edición, pero cambia también el padre y la cardinalidad respecto del ER aprobado.

Esto es distinto de generar una PK INTEGER nueva para un objetivo o personaje: esas PK propias serían legítimas. El bloqueo está en las referencias a padres reales y en su significado, no en que INTEGER y UUID no puedan coexistir en una aplicación.

La dependencia de las seis entidades termina en ese padre incompatible:
- caso oficial → objetivo_aprendizaje / escena / personaje;
- escena + personaje → personaje_escena;
- escena + criterio oficial → decision;
- decision → pista.

Implementar todas las seis juntas no resolvería el padre caso ni el criterio de rúbrica. Crear un segundo caso homónimo en la misma metadata tampoco es posible sin conflicto; otro schema o puente constituiría una estrategia de coexistencia que requiere aprobación expresa.

## 4. Versionamiento y contratos que se protegen

Actualmente:
- Caso → VersionCaso mediante caso_id UUID y UNIQUE(caso,numero).
- Versión → escenarios y rúbrica.
- Escenario → preguntas → opciones.
- Opción → valoracion_opcion → criterios, con puntajes por opción/criterio.
- Scheduling referencia la versión exacta.
- [consultar_version_publicada](../../app/modules/cases/application/published_version.py) recupera esa versión y su rúbrica; no selecciona la última.
- [ContextoIngresoParticipacion](../../app/modules/participation/application/integration_ports.py) conserva caso_id, version_caso_id y rubrica_id UUID.

Añadir objetivos/personajes directamente al caso lógico haría que distintas versiones compartieran esos datos. Eso podría ser una decisión válida de negocio, pero no está demostrado ni debe imponerse. Añadirlos a la versión preservaría la edición como ámbito, pero requiere aprobar esa diferencia frente al ER.

Duplicar escena/decision al lado de escenario/pregunta exigiría resolver qué estructura publica Builder/Chain, cuál consulta el estudiante y cómo se conserva el contenido de cada sesión. Una sincronización implícita o copiar textos una vez no garantiza integridad histórica.

No se modificó ninguno de esos contratos, patrones, puertos o servicios. Tampoco se tocó 8A ni grupo_academico/grupo_estudiante/consentimiento.

## 5. Alternativas para aprobación

| Alternativa | Alcance y ventaja | Decisión/coste antes de codificar |
|---|---|---|
| A. Mantener el ER literal de 28 y reconciliar primero los padres | Preparar identidad oficial INTEGER de caso/criterio, preservando cada edición y sus referencias antes de crear hijos | **Dirección recomendada para el objetivo oficial.** Requiere aprobar representación de versiones y estrategia de compatibilidad/coexistencia; no autoriza cambiar PK ni contratos actuales en esta fase |
| B. Autorizar ajustes dentro de las mismas 28 entidades | Podría conservar PK INTEGER propias y FK UUID explícitas al caso o a versión para objetivos/personajes; no implica necesariamente entidad nueva | Cambia tipos/relaciones del ER. El equipo y responsable académico deben elegir el ámbito y aprobar el ajuste antes de migrar. No aplicado aquí |
| C. Aceptar escenario/pregunta como equivalentes oficiales y evolucionarlos | Evita duplicar escena/decision; permite estudiar campos faltantes y mantener el grafo actual | Requiere reconciliar nombres/tipos/criterio y decidir qué se considera cumplimiento del ER. Agregar título/tipo por sí solo no resuelve todo ni aprueba esa equivalencia |

No hay recomendación de volver al modelo de 40. No se utiliza una clave INTEGER alternativa, cast, hash o manifiesto como sustituto silencioso de una relación aprobada. Cualquier puente productivo, columna de procedencia o schema de transición debe evaluarse y aprobarse primero.

### Preguntas mínimas a resolver

1. ¿Debe cada edición usada conservarse como un caso oficial INTEGER independiente, o se autoriza otra representación de versiones dentro de las 28?
2. ¿Objetivos y personajes pertenecen al caso lógico o a la versión concreta?
3. ¿Escena/decisión se reconciliarán con escenario/pregunta, o se autoriza una coexistencia temporal con correspondencia explícita y salida definida?
4. ¿Se mantiene un criterio por decisión del ER o cómo se preserva la valoración multicriterio actual?
5. ¿Qué mecanismo conservará los UUID externos/referencias de sesiones y 8A sin alterar sus contratos durante la transición?

No hace falta aprobar fórmulas de evaluación para decidir una FK, pero sí su ámbito y el significado del criterio. RF-22 u otras políticas pendientes no se usan para resolver estos bloqueos estructurales.

## 6. Entrega y estado final de BD2-02

| Punto solicitado | Resultado |
|---|---|
| Entidades analizadas | Las seis de la matriz, contrastadas con caso/version_caso/escenario/pregunta/rúbrica/criterio/valoración actuales |
| Subconjunto seleccionado | **Ninguno implementable sin una decisión adicional**; las seis dependen directa o transitivamente de padres incompatibles |
| Modelos / migración nuevos | Ninguno; no se registró metadata parcial ni tablas duplicadas |
| Comparación con ER | Relaciones INTEGER originales preservadas como referencia, no sustituidas por UUID de forma unilateral |
| Pruebas | No ejecutadas: no hubo cambio de código; solo inspección estática y de metadata sin conexión |
| Línea base | 1114 aprobadas/38 omitidas/0 fallos y errores de BD2-01 siguen siendo antecedentes; no nueva ejecución ni omitidos contados como aprobados |
| Metadata final | 22 tablas; BD2-01 intacta |
| Alembic final | 20261101_er28_base_academica, cabeza única sin revisiones nuevas |
| Único archivo nuevo | backend/docs/bd/BD2_02_ANALISIS_CASES_BLOQUEOS.md, este informe |
| Próximo incremento recomendado | Decisión acotada de reconciliación de caso/versiones y criterio; después seleccionar primero objetivos/personajes si sus padres quedan realmente resueltos |

No se ejecutaron pytest, Docker, migraciones o conexiones a PostgreSQL. No se modificó .env, código, ER ni documentos previos. Sin commit/push/merge/cambio de rama y sin operaciones destructivas.

El cierre comprueba hashes de archivos preexistentes, enlaces del informe y git diff --check. **BD2-02 se detiene en el límite solicitado: la implementación requiere una alternativa aprobada. No se inicia BD2-03.**
