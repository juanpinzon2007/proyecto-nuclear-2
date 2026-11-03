# BD2-04 — Integridad histórica de Cases en PostgreSQL

> Informe del experimento previo. La integración posteriormente autorizada de
> esta misma protección se documenta en
> [BD2_04_INTEGRACION_AUTORIZADA.md](../BD2_04_INTEGRACION_AUTORIZADA.md).

2026-11-02 · `feature/integracion-backend` · Solo experimento y propuesta de migración.

**Resultado: solución viable en el alcance probado sin nuevas tablas/columnas,
mediante triggers sobre las estructuras actuales. Dos ejecuciones finales con
109/109 comprobaciones. No instalada en el backend ni en bases del equipo.**

## 1. Vulnerabilidades reproducidas

Se construyó PostgreSQL 17.11 desde el head actual de Alembic, con datos sintéticos.
Antes de instalar guardas se ejecutaron y revirtieron dos bypass:

- UPDATE del nombre de versión PUBLICADO: aceptado, SQLSTATE 00000.
- UPDATE de valoración hacia un criterio existente de otra versión: aceptado,
  SQLSTATE 00000. Ambas FK eran válidas por separado.

Después de instalar las guardas, esos caminos y sus variantes se rechazan.
No se repitió el ER alternativo U1 ni se sustituyó version_caso.

Restricciones originales útiles: PK UUID de cada entidad, FK de la jerarquía,
UNIQUE(caso_id,numero), orden por padre, una rúbrica por versión y PK compuesta
opción/criterio. Ninguna de ellas congelaba contenido o comprobaba la edición común.
En Python ya estaban `asegurar_editable`, Chain, controles de dueño y relectura
bloqueada de BD2-03B; el experimento coloca una barrera también ante DML directo.

## 2. Solución experimentada y límites de esquema

[protecciones.sql](protecciones.sql) contiene seis funciones y 18 triggers.
No añade columnas, índices, CHECK, UQ o FK ni modifica identificadores.

- Raíz: admite creación BORRADOR y transiciones existentes a PUBLICADO/ARCHIVADO;
  congela el resto del contenido e impide volver a BORRADOR o eliminar historia.
- Hijos: BEFORE INSERT/UPDATE/DELETE resuelve la raíz y bloquea su fila FOR UPDATE;
  si está PUBLICADO/ARCHIVADO, rechaza. Se cubren escenario, pregunta, opción,
  rúbrica, criterio, nivel y valoración.
- Identidad/pertenencia: PK y padres no se cambian mediante UPDATE, tampoco en
  borradores; correcciones de estructura usan el reemplazo DELETE/INSERT actual.
  Los metadatos de la familia caso son estables. Esto es más estricto que solo
  congelar publicados y debe aprobarse explícitamente para una futura revisión.
- Valoraciones: antes de INSERT/UPDATE exige que opción y criterio lleguen a la
  misma versión. El reparentado posterior de cualquiera de sus ancestros queda
  prohibido, evitando invalidar una relación previamente aceptada.
- Familia: borrar solo familias con ediciones BORRADOR, bloqueadas; coordinación
  con creación/publicación mediante bloqueo de clave de la familia. Cascadas de
  borradores se permiten sin dejar huérfanos. No se permite TRUNCATE en las nueve
  tablas, para no eludir triggers por fila.
- Instalación: bloqueo de tablas y auditoría atómicos; discrepancias anteriores
  hacen abortar, sin reparación automática ni instalación parcial.

**No se usa CHECK entre tablas.** Una FK compuesta sería preferible si ambas
ramas almacenaran una clave común de versión. Hoy opción llega por pregunta/
escenario y criterio por rúbrica; valoracion_opcion tampoco tiene version_id.
Un UNIQUE adicional no permite una FK a un JOIN. La alternativa declarativa
exigiría columnas de versión propagadas y claves compuestas nuevas: cambios
estructurales no autorizados ni necesarios para este ensayo. Se descartó aquí.

No se necesitan más atributos académicos para el alcance de congelación y
pertenencia probado. Sí requieren otra autorización cualquier transferencia de
propietario/reparentado, reconstrucción de historia perdida, representación ER28
alternativa o nuevas relaciones de evaluación. No se implementó ninguna.

## 3. Resultados reales

Base de laboratorio: **22 tablas de dominio actuales + alembic_version = 23
tablas físicas**, 107 columnas. Es el esquema existente migrado, no el ER28 literal.
Tras instalar: mismas tablas/columnas/PK/FK/UQ/índices; 18 triggers de usuario nuevos.
No se creó una tabla académica/auxiliar adicional para el experimento.

| Grupo de comprobaciones finales | Cantidad | Resultado |
|---|---:|---|
| Aislamiento, bypass previo, preflight/atomicidad, catálogo e instalación | 7 | Correcto; los bypass previos se documentan como vulnerabilidades |
| Matriz PUBLICADO/ARCHIVADO: UPDATE/DELETE de raíz/familia/hijos, INSERT hijos, reversión y rollback | 54 | Rechazo o conservación esperados |
| Estado inicial, referencias entre versiones, reparentado, identidades, transiciones y huérfanos | 14 | Rechazo esperado |
| TRUNCATE en las nueve tablas | 9 | Rechazo, sin pérdida de datos |
| Escritores reales, referencia exacta, dos ediciones familiares, Scheduling y cascada borrador | 8 | Operaciones legítimas conservadas |
| Concurrencia en tres escenarios | 10 | Orden y rechazo esperados |
| Rol no propietario | 3 | No desactiva barrera; DML histórico rechazado |
| Catálogo final y reversión con filas preservadas | 4 | Correcto; downgrade reabre bypass como se advierte |
| Total | **109** | **109 satisfechas, ninguna fallida en las dos corridas finales** |

Concurrencia observada por pg_blocking_pids, con conexiones distintas:

1. Publicador primero, READ COMMITTED: editor espera y recibe 23514 tras commit.
2. Publicador primero, REPEATABLE READ: editor espera y recibe 40001; no escribe
   usando una fotografía obsoleta. Requiere rollback/reintento del caso completo.
3. Editor primero: la publicación espera su bloqueo de raíz, el editor confirma
   antes de congelar y publicación termina; una edición posterior se rechaza.

Dos ediciones comparten familia UUID pero conservan UUID de versión/rúbrica
distintos. Publicar la posterior no sustituye la referencia exacta de la anterior.
La sesión conserva su version_caso_id, incluso después de archivar esa versión.
Se usaron CasoRepository, Chain y programar_sesion reales, no escritores falsos.

Esta conservación se comprobó con las operaciones legítimas del ensayo, no como
una prohibición SQL de reasignar sesiones. **No se añadió un trigger a
sesion_programada**: su FK sigue admitiendo otra versión existente. Bloquear un
UPDATE directo de esa referencia necesita una protección y alcance aprobados
por separado; las nueve tablas de esta propuesta no cierran ese camino.

La consulta de ingreso 8A sigue requiriendo PUBLICADO; no se altera para permitir
ingreso a ARCHIVADO. Sus referencias y políticas permanecen intactas. El experimento
no crea intentos productivos ni evalúa calificaciones, RF-22 o JWT.

### Ejecuciones y fallos conservados

| Evidencia | Resultado |
|---|---|
| [998908dd](evidencia_998908dd2f814164b5c520869a19b630.json) | Dos bypass previos comprobados; el preflight del ejecutor falla antes de alcanzar PostgreSQL por interpretación de porcentajes como placeholders |
| [1131e7cf](evidencia_1131e7cfbd2e495e8084f41afa0b79cd.json) | Mismo problema; diagnóstico ampliado: sqlstate NULL y mensaje del driver. No era un rechazo de integridad válido |
| [cee4616f](evidencia_cee4616f6c2947dda90020964c81a351.json) | Tras usar ejecución sin parámetros para DDL literal: 99/99 |
| [6585b02d](evidencia_6585b02df54945dabcd867bd903f5be9.json) | Añadidas comprobaciones de montaje, estado inicial y misma familia/Scheduling: 104/104 |
| [5ef9153f](evidencia_5ef9153f1a4e4fe397c3539c1f1c5b9a.json) | Código final, concurrencia inversa y filas tras downgrade: 109/109 |
| [d88a3a24](evidencia_d88a3a2475bf4912be52f87735042ad2.json) | Repetición independiente del mismo código y SQL: 109/109 |

No hubo skip/xfail, cambio de expectativas para aceptar vulneraciones ni reparación
de datos para instalar. Los errores iniciales se corrigieron en el transporte DDL
del ejecutor experimental, sin cambiar producción. No se suman ejecuciones repetidas
ni se añaden estos probes a la línea base de pytest.

## 4. Seguridad y limpieza verificadas

Cada corrida crea su propio contenedor postgres:17, con etiqueta y nombre aleatorios,
datos tmpfs, sin bind/volúmenes persistentes y puerto efímero solo en 127.0.0.1.
El fixture espera conexión TCP real y confirma base vacía/identidad; el ejecutor
verifica el montaje real. Base: sps_identity_test_resolver; no sps ni bases del equipo.
El rol bd204_writer se crea solo en el contenedor del ensayo y no es propietario
ni superusuario. No puede desactivar triggers ni poner replication_role=replica.

Los seis contenedores creados fueron eliminados por ID propio en finally y su
ausencia se verificó mediante inspect. Las evidencias registran sus IDs completos;
las dos finales son `8cf79ac56dc07c8f1eb4cf7591102aa5e7c97b2012f6c69c041911c8dbc6d838`
y `1c25f4f51d867b754d23f7ffc206b656fbfd1a9ea74882463a82ae7faa628a17`.
No se usaron credenciales externas, `.env`, Compose ni limpieza global.

La barrera no puede proteger frente al propietario/superusuario que la elimine.
Separar propietario/migrador de rol de aplicación es condición de adopción, no
algo verificado sobre roles reales del equipo. No se inspeccionaron esas bases.
Autorización docente/estudiante y validación académica completa siguen en Python;
los triggers no convierten una publicación SQL en una validación de la Chain.

## 5. Primera migración recomendada y pendientes

Preparar, **solo después de aprobación**, `20261102_cases_history_guard` sobre
el head `20261101_er28_base_academica`. La especificación de objetos, DDL exacto,
hashes, preflight, dialectos y reversión está en
[ESPECIFICACION_MIGRACION.md](ESPECIFICACION_MIGRACION.md).

Recomiendo aprobar el diseño para esa integración condicionada, no aplicarlo ahora:

- No hay fallo pendiente en las 109 comprobaciones finales; quedan por ejecutar
  la regresión general con revisión integrada y los cambios legítimos de fixtures.
- Las pruebas anteriores que insertan PUBLICADO y luego agregan rúbrica, o limpian
  historia mediante DELETE, no son compatibles con una barrera real de inmutabilidad.
  Deben preparar BORRADOR/cargar/publicar y aislar mediante rollback o destruir su
  laboratorio. No habilitar variables de sesión para saltar los triggers.
- La prueba de BD2-03B que afirmaba el bypass SQL debe pasar a exigir rechazo con
  la nueva revisión. No se modificó aquí porque todo cambio se limitó a docs/bd.
- El protocolo probado serializa una raíz. En transacciones multirraíz puede haber
  deadlocks; 40P01/40001 exigen rollback y reintento controlado. No se demuestra
  ausencia universal de deadlocks ni se introduce retry automático en los servicios.
- Se prohíbe reparentado incluso entre borradores, cambios de metadatos de familia,
  creación inicial PUBLICADO y TRUNCATE; son condiciones expresas por aprobar.
  Los escritores productivos existentes probados no necesitan esas operaciones.
- Las bases con inconsistencias previas deben corregirse mediante un proceso
  autorizado aparte. La migración no puede certificar ni reconstruir notas históricas
  cuyo contexto se hubiera perdido antes de instalarla.

No se ejecutó la suite general en esta fase; **1157 aprobadas/38 omitidas/1
advertencia** sigue siendo resultado histórico, no validación con estos triggers.
No se incorporó revisión Alembic, modificó ORM/8A/patrones/DBML ni se cambió rama.
Los archivos nuevos están exclusivamente en esta carpeta. No se inicia BD2-05.

Cierre verificado: 282 archivos preexistentes conservan sus hashes y hay solo
12 archivos nuevos en la carpeta autorizada. Los hashes de todos los artefactos
registrados coinciden con ambas evidencias finales. Análisis sintáctico del
ejecutor, enlaces y whitespace de los archivos nuevos correctos. `git diff --check`
no informa errores; Git emite un aviso de conversión LF/CRLF de un archivo previo
sin que se haya modificado su contenido en esta fase.

**Solicitud de aprobación:** ¿autorizas integrar la revisión especificada, junto
con las adaptaciones de fixtures y regresión aislada, manteniendo prohibida su
aplicación a bases persistentes sin autorización de despliegue separada? Se pide
porque añade objetos/reglas de esquema que todavía solo están autorizados para
el laboratorio. La propuesta es concreta y está probada; no se ejecutará sola.
