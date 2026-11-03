# BD2-02A — Transición de Cases hacia el ER oficial

**Recomendación: alternativa 3 como primer incremento de validación**, en PostgreSQL nuevo y desechable, sin cambiar el backend vigente. Después, elegir una transición productiva gradual solo con evidencia y decisiones aprobadas. No convertir claves ni añadir columnas ahora.

Rama comprobada: feature/integracion-backend. Alcance: documento, lectura de código y búsquedas estáticas. Sin pytest, Docker, conexiones o migraciones. La línea base 1114 aprobadas/38 omitidas es histórica, no una ejecución nueva.

## 1. Referencias reales e identidad que transportan

El UUID de caso lógico **no es** el UUID de versión ni el del docente. No se pueden reemplazar todos los parámetros llamados id con un INTEGER.

| Capa / evidencia | Referencia comprobada |
|---|---|
| models/caso.py: CasoModel y VersionCasoModel | Caso.id UUID, creador UUID. FK directa version_caso.caso_id→caso.id; UNIQUE(caso_id,numero) |
| models/caso.py y models/rubrica.py | escenario y rubrica apuntan a versión UUID; pregunta→escenario; opción→pregunta; criterio→rúbrica; valoración→opción/criterio |
| domain/entities/caso.py; builders/constructor_caso.py | VersionCaso y ResumenVersion transportan caso_id y versión UUID; IDs UUID de contenido generados por uuid4. Builder resuelve nombres de criterios a sus UUID |
| domain/repositories.py; infrastructure/repositories/caso_repository.py | ICasoRepository/CasoRepository reciben version_id UUID y docente UUID; obtener_version filtra dueño; listar devuelve ambos IDs; _a_dominio/_mapear reconstruyen el grafo |
| application/services/caso_service.py | CasoService.crear_borrador/obtener/actualizar/publicar/archivar. actualizar conserva id de versión, caso_id y numero; no cambia identidad por reconstruir el payload |
| api/router.py y api/schemas/caso_responses.py | Rutas /api/v1/cases/{version_id} y publish/archive validan UUID de **versión**. Detalle/lista/respuesta exponen caso_id y versión; no aceptar INTEGER en esas rutas sin revisar contrato |
| scheduling/api/schemas.py, application/programar_sesion.py, infrastructure/models.py | Entrada version_caso_id UUID; db.get de versión; valida PUBLICADO y máximo<=estimado. FK sesion_programada.version_caso_id→version_caso.id. No FK directa de sesión a caso.id |
| cases/application/published_version.py; participation/infrastructure/integration.py | Consulta de versión exacta y su rúbrica; devuelve también caso_id lógico. 8A conserva ambos UUID, rúbrica y version_regla |
| participation/application/integration_ports.py vs ports.py/evaluation_ports.py/domain/evaluation.py | 8A usa UUID; los ports previos de participación/evaluación usan id_caso INTEGER. Esa divergencia sigue sin adaptación productiva; no es una conversión existente |
| identity/domain/entities.py | ResumenCaso/DetalleParticipacion usan id_caso str opaco, no demuestran UUID. Fixtures/reporting del ER emplean INTEGER; no confundirlos con contrato Cases |
| Pruebas y revisiones | Fixtures construyen Caso/Version/Session con UUID; pruebas HTTP exigen UUID/identidades; 8A prueba dos versiones/rúbricas distintas; revisiones iniciales crean esas FK |

En el ORM vigente, la FK directa hacia caso.id es la de version_caso.caso_id. Scheduling consume esa identidad **indirectamente por versión**. Cambiar solo caso deja también pendientes todas las FK de contenido, el filtrado por docente y las respuestas HTTP.

El anexo enumera las 44 fuentes Python con coincidencias de caso_id/version_id y equivalentes en app, tests y revisiones. No implica que cada coincidencia sea UUID: incluye explícitamente los contratos INTEGER/str y fixtures de laboratorio. Los archivos de schemas/builders indicados arriba completan los contratos tipados de UUID de contenido.

## 2. Diferencias de atributos y cardinalidad

| Entidad | ER oficial | Implementación actual / consecuencia |
|---|---|---|
| caso | id_caso INTEGER; profesor usuario INTEGER; título, introducción, estado, creación/validación | Caso UUID contiene creador/creación; nombre, dos textos, tiempo estimado y estado se guardan en versión. No es un cambio de nombre de PK |
| version_caso | No figura entre las 28 | Caso 1:N versiones con número único; contenido propio por versión. Rúbrica 0..1 por versión; obligatoria para referencia de ingreso válida |
| escena/escenario | Escena INTEGER→caso; título/contexto/orden/tipo, orden único por caso | Escenario UUID→versión; orden/contexto, sin título/tipo. Importar texto no acredita los campos ausentes ni equivalencia del ámbito |
| decision/pregunta | Decisión INTEGER→escena y exactamente un criterio; orden único por escena | Pregunta UUID→escenario, sin criterio directo; opciones aportan a varios criterios mediante valoracion_opcion |
| criterio_rubrica | INTEGER→rúbrica, peso_porcentaje | UUID→rúbrica de versión, peso no certificado como porcentaje; preservación de niveles/puntajes/descriptor pendiente |
| opcion_respuesta | INTEGER→decisión, destino escena opcional, texto/correcta/justificación/orden y UQ compuesta | UUID→pregunta, sin destino; valoraciones multicriterio. Cambiar ruta/corregir criterio no es política ya resuelta |

Una fila oficial caso por cada edición podría conservar cada fotografía con su rúbrica, pero pierde la relación explícita de familia/versionado y el UUID lógico si no se acuerda cómo representarlos. No se fusionan dos ediciones ni se usan textos/JSON como tabla de correspondencias encubierta.

## 3. Comparación de alternativas

| Criterio | 1. Gradual INTEGER, UUID temporal | 2. Correspondencia en tablas existentes | 3. ER en laboratorio nuevo |
|---|---|---|---|
| Fidelidad a 28 | Meta posible tras reconciliación/corte; transición conserva más estructuras | Mantiene número si no agrega entidades, pero columnas alternativas/procedencia desvían atributos/PK del ER | Permite verificar literalmente las 28 sin colisión; no demuestra integración productiva |
| Backend | Adaptadores y convivencia explícita; corte complejo | API puede conservar UUID si cada alias tiene persistencia inequívoca | Backend actual no cambia; adaptación se diseña después |
| Pérdida de datos | Riesgo alto si se colapsan versiones o cambia FK in situ | Riesgo menor si mapeo preserva edición/ámbito; no resuelve faltantes | Menor riesgo inmediato: solo datos sintéticos, fuentes intactas |
| Python | ORM/repositorios y compatibilidad de DTO/servicios/API, lectores de Scheduling/8A | Modelos con claves alternativas y repositorios resolutores; servicios preservan significado | Primer paso solo infraestructura/pruebas de laboratorio; posteriormente adaptadores revisados |
| Alembic | Revisiones expand/backfill/validate/cutover, sin cambiar raíces | Revisiones de columnas/UQ/FK tras aprobación; backfill verificable | Ninguna revisión en cadena productiva inicial; DDL aislado desde definiciones oficiales |
| 1114 pruebas | Deben seguir pasando durante convivencia; cambios contractuales explícitos después | Mantenerlas más nuevas de alias/ambigüedad; no reemplazar UUID esperados por enteros para pasar | No ejecutadas aquí; futuro repetir regresión y agregar pruebas de fidelidad/viabilidad, sin contar omitidas como éxito |
| 8A/8B/8C | 8A conserva IDs mediante adaptador; 8B/8C esperan contexto persistido exacto | 8A necesita distinguir UUID de caso/versión; 8B/8C requieren referencia histórica reproducible | 8A intacta ahora; 8B/8C no se habilitan por una prueba de laboratorio |
| Autorización | Equipo para convivencia/corte; académico para semántica de versión y campos | Académico/equipo para desviaciones incluso sin tabla nueva | Autorización operativa del laboratorio; cambios de semántica se someten antes de importar o adaptar contratos |

### Por qué recomiendo 3 primero

Resuelve la duda técnica de si las FK oficiales funcionan juntas sin exponer datos actuales a una transformación aún indefinida. Su resultado debe ser un prototipo verificable y un reporte de correspondencias/pérdidas, no otra arquitectura aprobada ni un despliegue paralelo.

No garantiza que todas las funcionalidades actuales quepan sin pérdida en los atributos originales: tiempo estimado, UUID históricos, familia de versiones, descriptores/valoraciones y otros datos pueden no tener destino fiel. Si se exige simultáneamente ER exacto, todos los contratos actuales intactos y retirada de soporte, hay una contradicción que el ensayo debe demostrar, no esconder.

La alternativa 1 es el mecanismo posterior de despliegue preferible si el ensayo y las decisiones lo permiten. La 2 puede ayudar, pero **no** propongo añadir id_caso INTEGER o uuid_origen a la tabla actual sin aprobación: una clave alternativa no se convierte por sí sola en la PK oficial ni resuelve versiones.

## 4. Primer incremento que puede autorizarse

**Ensayo de fidelidad del esquema, sin adaptación productiva ni datos históricos.**

Archivos futuros propuestos, ninguno creado ahora:
- backend/tests/er28_cases/schema_support.py: metadata SQLAlchemy Core privado derivado de los bloques oficiales (tipos, PK, UQ, defaults, FK simples y las dos compuestas). No importar estos objetos a Base.metadata ni añadir entidades.
- backend/tests/er28_cases/test_schema_cases.py: prueba del esquema completo de 28 en un laboratorio nuevo y de la cadena caso→rúbrica/criterio→escena/decisión/opción, más objetivo/personaje/personaje_escena/pista.
- Reutilizar el laboratorio desechable existente y su validación TCP/ID/label/base vacía, con conexión explícita. No modificar .env ni usar URL heredada.
- Un reporte de viabilidad posterior; no modificar las revisiones de backend/alembic/versions ni registrar modelos en producción.

La fábrica de schema debe reconocer declaraciones de tipos y excluir bloques indexes (144 columnas reales, no el conteo documental antiguo de 156). Debe aplicar exactamente el original, no la propuesta de 40. El helper actual tablas_academicas_prueba solo cubre un subconjunto y no sustituye esa verificación completa.

Condiciones de aceptación futuras:
1. Exactamente 28 tablas académicas/144 columnas/40 FK y PK/UQ/defaults originales en el laboratorio; ningún placeholder. Sin Alembic en este primer ensayo no aparece alembic_version.
2. Todas las FK resueltas; registros sintéticos válidos y huérfanos/duplicados rechazados donde el original sí lo exige.
3. Separar integridad del ER de reglas adicionales: sus FK simples no impiden todos los cruces entre casos; informar esos casos, no añadir restricciones ocultas.
4. Dos ediciones fuente sintéticas con distinta rúbrica: no fusionarlas. Probar propuestas de correspondencia **solo como experimento**, conservando ambos UUID y declarando qué no puede persistir el destino. El manifiesto de prueba no es un resolver productivo.
5. Ninguna entrada a fuentes existentes, cambios en Base/cadena ni rutas. Después, regresión aislada de los 1114 casos previos más los nuevos; informar omitidos por separado.
6. Entorno efímero identificado y eliminado solo por ID propio; no datos del equipo. No declarar éxito de compatibilidad si únicamente pasó CREATE TABLE.

**Aprobación previa mínima:** autorizar ese ensayo aislado y su alcance de pruebas, sin tratarlo como autorización de modificar código funcional o importar datos. Para un incremento productivo, el equipo/académico debe decidir primero: una edición como caso independiente o representación alternativa; ámbito caso/versión de objetivos/personajes; criterio por decisión frente a multicriterio; campos de procedencia y compatibilidad de los UUID públicos. No se inventa ninguna de esas respuestas en el ensayo.

## 5. Soporte existente y viabilidad de 28 físicas

Los tres equivalentes parciales escenario/pregunta/nivel_rubrica necesitan reconciliación, no duplicados permanentes. version_caso/valoracion_opcion requieren destino semántico; espacio_academico/sesion_programada/convocatoria sostienen Scheduling/login; identidad_academica y evento_auditoria sostienen identidad/trazabilidad. Todos siguen intactos ahora.

Agregar las entidades oficiales sin retirar/reconciliar los diez nombres adicionales no termina en 28. Conservarlos definitivamente como tablas, aunque sea en otro schema, tampoco cumple un físico final estricto de 28. Retirarlos antes de adaptar consumidores rompe funcionalidades.

Llegar a 28 tablas de dominio es un destino condicionado, no demostrado aún para todos los datos/contratos. Con Alembic habrá además su tabla de control: explicitar ese criterio de conteo. No borrar control ni mover soporte para aparentar cumplimiento. Cualquier ampliación de atributos dentro de las mismas 28 requiere aprobación si altera el ER literal.

## 6. Cierre de esta fase

Único archivo creado: este documento. No se modificó código, ORM, migraciones, ER, BD2-01, 8A ni patrones. No se ejecutaron pruebas, Docker o PostgreSQL. Metadata/cabeza no se cambiaron; los últimos valores verificados son 22 y 20261101_er28_base_academica. La aceptación de este informe no inicia el ensayo ni BD2-03.

## Anexo: trazabilidad textual de referencias

Búsqueda completa sobre Python de app, tests y revisiones para caso_id, case_id, version_caso_id, version_id, id_caso y destinos caso.id/version_caso.id. Líneas del estado inspeccionado; las menciones en fixtures INTEGER y DTO str se distinguen en §1. No se atribuyen FK físicas a menciones en texto.

| Archivo | Líneas |
|---|---|
| [app/modules/cases/api/router.py](../../app/modules/cases/api/router.py) | 49, 70, 72, 76, 81, 83, 87, 92, 94, 98, 103, 105, 109 |
| [app/modules/cases/api/schemas/caso_responses.py](../../app/modules/cases/api/schemas/caso_responses.py) | 62, 74, 75, 86, 87 |
| [app/modules/cases/application/published_version.py](../../app/modules/cases/application/published_version.py) | 3, 21, 22, 28, 36, 38, 39, 41, 46 |
| [app/modules/cases/application/services/caso_service.py](../../app/modules/cases/application/services/caso_service.py) | 37, 39, 42, 51, 55, 60, 67, 72, 79, 84, 85, 87 |
| [app/modules/cases/domain/entities/caso.py](../../app/modules/cases/domain/entities/caso.py) | 99, 143, 144 |
| [app/modules/cases/domain/repositories.py](../../app/modules/cases/domain/repositories.py) | 20 |
| [app/modules/cases/infrastructure/models/caso.py](../../app/modules/cases/infrastructure/models/caso.py) | 47, 50, 51, 78, 81, 82 |
| [app/modules/cases/infrastructure/models/rubrica.py](../../app/modules/cases/infrastructure/models/rubrica.py) | 18, 19 |
| [app/modules/cases/infrastructure/repositories/caso_repository.py](../../app/modules/cases/infrastructure/repositories/caso_repository.py) | 47, 49, 64, 65, 140, 181 |
| [app/modules/identity/domain/entities.py](../../app/modules/identity/domain/entities.py) | 89, 104 |
| [app/modules/identity/infrastructure/academic_models.py](../../app/modules/identity/infrastructure/academic_models.py) | 40 |
| [app/modules/participation/api/schemas.py](../../app/modules/participation/api/schemas.py) | 54 |
| [app/modules/participation/application/evaluation_ports.py](../../app/modules/participation/application/evaluation_ports.py) | 17 |
| [app/modules/participation/application/evaluation_service.py](../../app/modules/participation/application/evaluation_service.py) | 64, 67, 71 |
| [app/modules/participation/application/integration_ports.py](../../app/modules/participation/application/integration_ports.py) | 18, 19 |
| [app/modules/participation/application/ports.py](../../app/modules/participation/application/ports.py) | 16, 21, 29, 40 |
| [app/modules/participation/application/services.py](../../app/modules/participation/application/services.py) | 103, 105, 108, 144, 145 |
| [app/modules/participation/domain/evaluation.py](../../app/modules/participation/domain/evaluation.py) | 37, 42 |
| [app/modules/participation/infrastructure/integration.py](../../app/modules/participation/infrastructure/integration.py) | 61, 64 |
| [app/modules/participation/tests/evaluation_fakes.py](../../app/modules/participation/tests/evaluation_fakes.py) | 43, 46, 47 |
| [app/modules/participation/tests/fakes.py](../../app/modules/participation/tests/fakes.py) | 160, 192, 195, 200, 210, 215, 219 |
| [app/modules/participation/tests/test_evaluation_application.py](../../app/modules/participation/tests/test_evaluation_application.py) | 216 |
| [app/modules/scheduling/api/schemas.py](../../app/modules/scheduling/api/schemas.py) | 12, 53 |
| [app/modules/scheduling/application/programar_sesion.py](../../app/modules/scheduling/application/programar_sesion.py) | 23, 59, 84 |
| [app/modules/scheduling/infrastructure/models.py](../../app/modules/scheduling/infrastructure/models.py) | 54, 55 |
| [tests/identity/test_academic_identity_http_sql.py](../../tests/identity/test_academic_identity_http_sql.py) | 51, 58, 90 |
| [tests/identity/test_academic_identity_repository.py](../../tests/identity/test_academic_identity_repository.py) | 142, 148 |
| [tests/identity/test_http.py](../../tests/identity/test_http.py) | 195 |
| [tests/identity/test_persistence.py](../../tests/identity/test_persistence.py) | 87, 310, 311 |
| [tests/identity/test_student_login_scheduling.py](../../tests/identity/test_student_login_scheduling.py) | 57, 61, 187, 248 |
| [tests/integration/cases/test_lifecycle_endpoints.py](../../tests/integration/cases/test_lifecycle_endpoints.py) | 25, 28, 29, 37, 39, 58, 61, 62, 80, 82, 86, 100, 103, 116, 124, 128, 129, 132, 144, 149, 150, 161, 166, 168, 182, 183, 185, 189, 193, 195, 204, 207, 220, 221, 223, 227, 236, 238, 242, 248, 249, 250, 252, 258, 259, 260, 262, 269, 270, 273 |
| [tests/integration/cases/test_publish_endpoint.py](../../tests/integration/cases/test_publish_endpoint.py) | 31, 32, 42, 44, 64, 89, 124, 126, 130, 142, 144, 150, 156, 157, 159, 178, 181, 182, 219 |
| [tests/integration/scheduling/test_scheduling_endpoints.py](../../tests/integration/scheduling/test_scheduling_endpoints.py) | 28, 65 |
| [tests/integration/scheduling/test_worker_integration.py](../../tests/integration/scheduling/test_worker_integration.py) | 45, 59, 82 |
| [tests/integration/test_er28_academic_base.py](../../tests/integration/test_er28_academic_base.py) | 315, 317, 321, 327 |
| [tests/integration/test_participation_8a.py](../../tests/integration/test_participation_8a.py) | 59, 60, 62, 72, 197, 202, 210, 220, 225, 301, 311, 313, 319, 326 |
| [tests/integration/test_schema_integration.py](../../tests/integration/test_schema_integration.py) | 133, 264, 278, 305, 306 |
| [tests/integration/test_student_identity_security.py](../../tests/integration/test_student_identity_security.py) | 58 |
| [tests/unit/scheduling/test_api_endpoints.py](../../tests/unit/scheduling/test_api_endpoints.py) | 128, 205 |
| [tests/unit/scheduling/test_api_security.py](../../tests/unit/scheduling/test_api_security.py) | 19 |
| [tests/unit/scheduling/test_models.py](../../tests/unit/scheduling/test_models.py) | 47 |
| [tests/unit/scheduling/test_programar_sesion.py](../../tests/unit/scheduling/test_programar_sesion.py) | 25 |
| [alembic/versions/36b9e0790539_add_scheduling_tables.py](../../alembic/versions/36b9e0790539_add_scheduling_tables.py) | 29, 42, 47 |
| [alembic/versions/c27a750108db_feat_esquema_inicial_casos_y_rubricas.py](../../alembic/versions/c27a750108db_feat_esquema_inicial_casos_y_rubricas.py) | 30, 37, 39, 41, 45, 48, 50, 52, 55, 58, 60 |
