# BD2-01 — Organización académica y consentimiento implementados

**Cierre de la unidad autorizada · 2026-11-01.** Rama feature/integracion-backend; sin commit, push, merge ni PR. Se conserva el objetivo oficial de 28 tablas y toda la implementación anterior, incluida 8A.

## 1. Resultado y alcance

Se implementaron exclusivamente grupo_academico, grupo_estudiante y consentimiento: **14 columnas, 3 PK, 4 FK y 1 UNIQUE**. El registro productivo declara ahora 22 tablas, no un ER ampliado: son las 19 anteriores más estas tres oficiales. Las diez estructuras existentes que requieren reconciliación siguen intactas.

No se habilitaron servicios, repositorios académicos, endpoints ni datos de producción; no se registró el router de Participation. No se modificaron Cases, Scheduling, Participation, Evaluation, autenticación, políticas o los siete patrones.

**Separación de estados:**
- ORM y migraciones disponibles: 22 tablas integradas.
- PostgreSQL de laboratorio: upgrade/downgrade efectivamente comprobados sobre contenedores nuevos.
- Bases existentes del equipo/desarrollo/producción: no conectadas, inspeccionadas ni migradas. No se afirma su esquema aplicado.

## 2. Modelos y fidelidad al ER

Archivo nuevo: [academic_base_models.py](../../app/modules/identity/infrastructure/academic_base_models.py).

| Clase / tabla | Columnas originales |
|---|---|
| GrupoAcademicoORM / grupo_academico | id_grupo INTEGER PK autoincremental, id_profesor INTEGER NN, nombre VARCHAR(120) NN, periodo VARCHAR(30) NN |
| GrupoEstudianteORM / grupo_estudiante | id_grupo_estudiante INTEGER PK autoincremental, id_grupo INTEGER NN, id_estudiante INTEGER NN, fecha_ingreso TIMESTAMP sin zona NN, activo BOOLEAN NN DEFAULT true |
| ConsentimientoORM / consentimiento | id_consentimiento INTEGER PK autoincremental, id_estudiante INTEGER NN, version_texto VARCHAR(30) NN, fecha_aceptacion TIMESTAMP sin zona NN, fecha_revocacion TIMESTAMP sin zona nullable |

FK: grupo.profesor→usuario; membresía.grupo→grupo; membresía.estudiante→usuario; consentimiento.estudiante→usuario. UNIQUE: (grupo_estudiante.id_grupo,id_estudiante).

**Diferencias estructurales respecto de esos tres bloques del original: ninguna.** Se asignan nombres técnicos a FK/UQ para mantener ORM/DDL consistentes; no se agregan CHECK, índices explícitos, columnas, cascadas, UUID ni defaults académicos adicionales.

El [ER original](../../app/modules/identity/reference/sps.dbml) sigue con 28 tablas y SHA-256 fb6ab07cfdfee38ba59e1acc879335ec0b377150acc3474b4a817a9eece229d7; el [objetivo aprobado](ER_OBJETIVO_APROBADO_28_TABLAS.dbml) no se alteró.

Las clases comparten Base y solo se importan desde registrar_modelos_integrados. permiso_intento_extra y retroalimentacion_docente continúan en academic_metadata separado con sus dependencias pendientes; no se registran placeholders ni se duplica usuario.

## 3. Revisión Alembic

Archivo nuevo: [20261101_er28_base_academica.py](../../alembic/versions/20261101_er28_base_academica.py).

- revision: 20261101_er28_base_academica.
- down_revision: 20261031_academic_identity.
- Grafo local: siete revisiones, sin padres faltantes y una única cabeza nueva. Se conservan intactas las seis anteriores, incluidas las dos raíces y merges.
- La revisión predecesora existe en el árbol de trabajo y sigue sin seguimiento Git. Eso no impidió comprobar su cadena local; ninguna revisión se considera desplegada en bases del equipo.

upgrade crea grupo_academico → grupo_estudiante → consentimiento. No hay INSERT, backfill, ALTER, DROP ni cambio de identificadores anteriores. Una prueba inspecciona el AST para exigir la lista cerrada de tres CREATE TABLE; las pruebas de reflexión y datos verifican su efecto real.

downgrade comprueba las tres tablas vacías antes de cualquier DROP; PostgreSQL usa LOCK TABLE ... ACCESS EXCLUSIVE durante la comprobación. Si hay datos, rechaza la reversión. Si están vacías, retira únicamente consentimiento, grupo_estudiante y grupo_academico, sin CASCADE. Se comprobaron el rechazo sin ningún DROP y la preservación del esquema/datos. No se ejecutó sobre datos de valor.

## 4. Archivos de esta etapa

| Archivo | Cambio propio de BD2-01 |
|---|---|
| backend/app/modules/identity/infrastructure/academic_base_models.py | Nuevo: tres modelos exactos del ER |
| backend/app/db/models.py | Una importación adicional de los nuevos modelos; conservar registro y validación anteriores |
| backend/alembic/versions/20261101_er28_base_academica.py | Nueva revisión aditiva con downgrade protegido |
| backend/tests/integration/test_er28_academic_base.py | Nuevo: 53 pruebas de modelos/estructura/integridad/migración y preservación |
| backend/tests/integration/test_schema_integration.py | Inventario exacto 22, importación por subprocess y nueva cabeza/ancestría; mantener pendientes fuera |
| backend/tests/identity/test_academic_identity_repository.py | Verificar nueva cabeza hija de la histórica y regresar a head al terminar el ciclo aditivo |
| backend/docs/bd/BD2_01_IMPLEMENTACION_BASE_ACADEMICA.md | Este informe |

La prueba anterior de ciclo vuelve ahora a head, en vez de dejar el laboratorio en REVISION histórica: el downgrade también retira las tres tablas nuevas vacías, y volver solo a la revisión antigua no las restauraría. Se mantiene la comparación completa de filas anteriores y se comprueba el padre histórico; no se excluyen tablas para esconder el cambio.

Los archivos ya modificados/sin seguimiento antes de esta tarea se conservan. El git diff contra HEAD incluye fases previas: no debe atribuirse todo ese diff a esta unidad.

## 5. Resultados reales de las pruebas

El usuario autorizó explícitamente la suite mixta: SQLite aislado, pruebas sin BD y PostgreSQL temporal. Se usaron los argumentos de pytest siguientes mediante un lanzador de seguridad en un proceso efímero; no se aplicó el CLI Alembic contra la configuración del proyecto.

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Primera versión del archivo nuevo, antes de ampliar PK duplicada | 47 | 0 | 0 | 0 | 0 |
| Nuevas + metadata + repositorio afectado, primera pasada | 94 | 0 | 2 | 0 | 1 |
| Mismo grupo después de corregir la cadena de subprocess | 96 | 0 | 0 | 0 | 1 |
| Suite completa final | **1114** | **38** | **0** | **0** | **1** |

Los dos fallos intermedios eran KeyError de .format al insertar un literal de conjunto sin escapar llaves en la cadena del test de importación. Se corrigió a llaves escapadas; no se alteró la regla ni se retiró la aserción. La repetición completa del grupo pasó en 24,41 s; la suite final, en 95,20 s.

Grupos ejecutados:
- backend/tests/integration/test_er28_academic_base.py.
- backend/tests/integration/test_schema_integration.py.
- backend/tests/identity/test_academic_identity_repository.py.
- Después: backend/tests y backend/app/modules/participation/tests con -c backend/pyproject.toml -q -rs --tb=short.

**Las 53 pruebas nuevas**, medidas por nodo/fixture en la ejecución final:
- 4 sin BD: contrato de columnas/tipos/PK/FK/UQ/defaults, límites del incremento y cabeza/AST.
- 21 con SQLite en memoria: FK activadas, nulabilidad, PK autogenerada/duplicada, UNIQUE, valores/defaults y ciclo con preservación.
- 28 con PostgreSQL nuevo: los mismos casos de persistencia, más longitudes reales, fallo DDL y downgrade poblado con rechazo antes de borrar.

Se sembró exclusivamente historia sintética de laboratorio en cada una de las 19 tablas anteriores para comparar filas y estructura antes/después del upgrade y downgrade. La comparación verificó columnas, tipos/defaults, PK, FK, UQ, CHECK e índices. La inspección estática independiente también encontró **cero diferencias** en las definiciones previas.

### Omitidas y comparación con la línea base

La única advertencia final es la conocida StarletteDeprecationWarning relacionada con httpx. No se instalaron paquetes ni se cambió esa integración.

Las 38 omitidas continúan sin ejecutarse:
- 29 de Identity que requieren SPS_IDENTITY_TEST_URL.
- 3 de conexión PostgreSQL de Participation que requieren SPS_TEST_POSTGRESQL/configuración explícita.
- 6 de persistencia aislada de Participation que requieren SPS_PERSISTENCE_LAB_URL.

No se tomaron URLs existentes del entorno para habilitarlas y no se cambió su código/skip. Esas configuraciones no acreditaban un laboratorio nuevo autorizado. No se cuentan como aprobadas.

Línea base histórica del usuario: 1061 aprobadas, 38 omitidas, 0 fallos/errores y una advertencia. Resultado actual: **1061 + 53 = 1114 aprobadas**, las mismas 38 omitidas y una advertencia. No se afirma que una política académica o la persistencia restante de Participation esté integrada por ese resultado. Los 199 casos históricos específicos de 8A no se suman de nuevo; sus pruebas existentes formaron parte de la suite de regresión sin modificaciones.

## 6. Evidencia de PostgreSQL aislado y protección del entorno

Se reutilizó motor_postgresql_desechable de tests/identity/academic_identity_support.py. Cada instancia:
1. Creó un contenedor nuevo con ID completo, nombre sps-resolver-lab-... y label sps.identity.mapping.lab=true, desde la imagen local postgres:17, sin pull.
2. Usó tmpfs para datos y ningún bind/volumen persistente; puerto TCP efímero publicado solo en 127.0.0.1.
3. Verificó ID/nombre/label/montajes/puerto y la base sps_identity_test_resolver con rol de laboratorio, credencial generada solo para esa instancia.
4. Esperó TCP/autenticación/SELECT current_database() y confirmó que no hubiera tablas antes de migrar.
5. Eliminó exclusivamente su propio ID en finally, incluso ante errores. Sin prune ni limpieza global.

Adicionalmente, el lanzador temporal interceptó las operaciones Docker reales, registró solo IDs creados por ese proceso y rechazó operar IDs ajenos. Protegió Engine.connect/raw_connection: PostgreSQL solo podía conectar al puerto de un ID creado/verificado activo con la identidad de laboratorio; SQLite solo a memoria o ruta temporal. Esa instrumentación de ejecución no cambió código de la aplicación ni pruebas para hacerlas pasar.

En ese proceso se retiraron las variables de URL externa SPS_IDENTITY_TEST_URL, SPS_PERSISTENCE_LAB_URL y TEST_DATABASE_URL y el opt-in ajeno SPS_TEST_POSTGRESQL; se activó SPS_TEST_IDENTITY_MAPPING_DOCKER=1. No se modificó .env ni el entorno persistente. Esto explica las omisiones, no las oculta.

**Contenedores de la suite completa final:** todos verificados y retirados con resultado Docker satisfactorio. No son contenedores existentes del equipo.

| ID completo propio | Puerto local | Verificado | Eliminado |
|---|---:|---|---|
| 01ed91784a518bf9244367bc8adb48a8253212e7ab4d996e814e0f4c7abd50df | 53279 | Sí | Sí |
| 1c69442a527832828770e12597458a7f9f139c83e8e199169f69ef22d868ae05 | 51269 | Sí | Sí |
| 2ed3171ec44423921dfe622fea84a2e4d4b5092c0c43391c5ca7fa6297c71c0a | 50116 | Sí | Sí |
| 39639554ea9f6658af1ee6eb4ffb89f22892fd69b215ff89b02632e89bbb646f | 51766 | Sí | Sí |
| 3c0ce56bc192cfdedcd60d50876064cc0c6fbcce1f6fe07f017f4aec32b84703 | 58834 | Sí | Sí |
| 5cdad5305851bb8410ed3a9180b393153ab261fe059891f34c5253ace01a90fc | 49714 | Sí | Sí |
| 9a5b04f5ac2287bc5870716fc80f06dd761aaf1e96a8521d601a5af555a14604 | 49757 | Sí | Sí |

Las ejecuciones específicas también crearon y retiraron sus propios laboratorios independientes. No se usó sps, ninguna base compartida ni contenedores anteriores. El estado de una base del equipo permanece sin verificar porque no se accedió a ella.

## 7. Límites y decisiones pendientes

- UNIQUE(grupo,estudiante) conserva el ER y no modela varios episodios históricos de matrícula. No se agregó fecha_retiro ni se aprobó reingreso.
- Consentimiento no se crea al iniciar sesión y no tiene texto/aceptación por defecto. Su aplicabilidad, vigencia y revocación de negocio siguen pendientes de decisiones académicas.
- Las fechas son sin zona por fidelidad al ER. No se ha convertido ningún timestamp legado ni se implementó un contrato nuevo de interpretación temporal.
- Los FK validan existencia, no rol/activo/permiso. No hay nuevos servicios que permitan escribir matrícula o consentimiento desde HTTP.
- RF-22, escala/fórmula, parcial/ausencia y consolidación no quedan aprobados; no se abrieron ingreso temporal ni calificación oficial.
- El vínculo entre convocatoria UUID y participación/asignación INTEGER sigue pendiente, igual que reconciliar versiones, valores de rúbrica, programación y feedback individual dentro de las 28.
- La concurrencia de inicio/cupo/retiro de Participation no se implementa ni certifica en esta unidad. Las pruebas actuales cubren restricciones y transacciones del incremento autorizado.
- El inventario declarado de 22 es transición, no una ampliación aprobada del ER ni un esquema final de 28. Las diez tablas actuales adicionales no se eliminaron.
- No se cambió ni desplegó ninguna política de los siete patrones; 8A conserva su contrato informativo y referencias exactas.

## 8. Estado Git y cierre

La rama sigue siendo feature/integracion-backend. Ningún commit, push, merge, PR, reset o clean. La revisión nueva y los demás archivos nuevos quedan sin seguimiento, al igual que archivos que ya estaban así. No se sobreescribe el trabajo previo.

El cambio propio comprende tres archivos preexistentes modificados, tres nuevos de código/pruebas/migración y este informe. Los otros **245 archivos preexistentes inventariados** conservan SHA-256 idéntico; no hay archivos eliminados. Los ER original/objetivo, nueve documentos previos y fuentes de los siete patrones/8A quedan intactos.

git diff --check: correcto, salida 0. Los siete archivos del incremento también se comprobaron individualmente contra origen vacío, incluidos los no rastreados, admitiendo los CRLF originales de Windows: sin incidencias de whitespace ni enlaces locales rotos. No se normalizaron los finales de línea previos ni se amplía/repite la suite después de modificar solo este informe.

**BD2-01 termina aquí. No se inicia BD2-02 y no se aplica la revisión a ninguna base existente.**
