# BD2-06 — Vinculación de lectura para Participation

2026-11-02 · Rama `feature/integracion-backend`.

## Resultado y alcance

Se implementa una consulta interna verificable sobre el esquema autorizado:
**usuario → vínculo Scheduling → convocatoria → sesión → asignación → caso/versión/
rúbrica**, más **usuario → matrícula activa → grupo de esa asignación**.

No se crea participación ni intento. No se añade ningún endpoint, tabla, atributo
ORM, migración o política académica. La fotografía obtenida no autoriza una futura
escritura ni reemplaza las comprobaciones transaccionales de inicio.

## Componentes implementados

| Componente | Responsabilidad |
|---|---|
| `ContextoVinculadoParticipacion` | DTO inmutable: conserva el contexto UUID de 8A y las PK INTEGER reales de usuario, matrícula, grupo, asignación y caso académico |
| `ConsultaVinculacionParticipacion` | Puerto interno adicional de lectura; exige una asignación explícita y conserva sin cambios la firma del puerto 8A anterior |
| `ConsultaVinculacionSQLAlchemy` | Compone la consulta 8A existente y acredita las relaciones mediante una consulta SQL parametrizada sobre la misma Session prestada |

Composición interna del servidor, sin HTTP nuevo:

```python
consulta = ConsultaVinculacionSQLAlchemy(
    sesion, politica=politica_del_servidor, reloj=reloj_del_servidor,
    consulta_version=consulta_publicada_de_cases,
)
contexto = consulta.consultar(
    usuario=contexto_autenticado_por_identity,
    convocatoria_id=convocatoria_solicitada,
    codigo_acceso=codigo_individual,
    id_asignacion=asignacion_explicita,
)
```

Las dependencias son del servidor. No se proporciona una política productiva
nueva ni una fábrica que cambie el bloqueo actual. `obtener_facade` sigue
respondiendo 503; la consulta no se registra en `main.py`.

## Reutilización y verificaciones

1. `ConsultaIngresoSQLAlchemy` relee cuenta activa/rol desde Identity, usa el
   resolver persistente por sistema y exige el contexto de convocatoria del JWT.
   No se toman usuario, rol o UUID académico de una cabecera arbitraria.
2. `ValidadorConvocatoriaScheduling` conserva titularidad/estado de convocatoria.
   `validar_ingreso` conserva código individual, sesión EN_CURSO, fechas,
   reloj inyectado y política temporal confiable. Sin RF-22 configurado la consulta
   falla antes de pedir la versión y antes de consultar matrícula/asignación.
3. La consulta publicada inyectable de Cases entrega únicamente la versión exacta
   de Scheduling, número, familia, rúbrica propia y `version_regla`; nunca la última.
4. El adaptador nuevo enlaza la asignación explícita con su grupo/matrícula, el
   INTEGER alternativo del caso y la misma familia UUID. Comprueba en SQL la pareja
   sesión–versión, convocatoria propia ACTIVA, sesión EN_CURSO, versión PUBLICADO,
   número y referencias de rúbrica/regla coincidentes con el contexto anterior.
5. Se exige una sola fila. Inexistencia, relación ajena o inconsistente no devuelve
   contexto y comparte un error genérico; multiplicidad inesperada se cierra como
   integración pendiente. La unicidad existente de matrícula por (grupo,estudiante),
   PK y rúbrica por versión impide multiplicidades normales.

`id_entero` de Identity adapta la cadena decimal de la **misma PK usuario** a
INTEGER. El UUID de Scheduling procede del vínculo persistente inequívoco; nunca
se calcula a partir de esa PK. `caso.id_caso` y `caso.id UUID` se leen de la misma
fila real, preservando P1. No se generan vínculos ni se concilian casos legados.

La matrícula exige un registro del usuario en el grupo exacto con `activo=True`.
Esto reconoce el indicador explícito del esquema y rechaza la matrícula desactivada;
**no certifica una política de vigencia temporal**. No interpreta `periodo` ni
`fecha_ingreso`, inventa fecha de retiro, episodios de reingreso o membresías.
Un usuario en varios grupos debe indicar una asignación concreta; no se elige la
primera matrícula ni una asignación por posesión del código.

La consulta no usa `asignacion.estado`, cupos o fechas de asignación como una nueva
política de ingreso: su semántica y coordinación con Scheduling siguen pendientes.
El control temporal efectivo sigue siendo exclusivamente el ya existente.

## Seguridad, ausencia de escrituras y límites

La composición usa `no_autoflush`, SELECT parametrizados y proyecciones de columnas.
No hace INSERT/UPDATE/DELETE, flush, commit, rollback, cierre de Session ni bloqueo
de filas. La Session pertenece al llamador, que debe cerrarla/revertirla.

Los resultados contienen solo referencias internas necesarias y duración informativa
de Scheduling. No devuelven correo, códigos, hashes, contenido docente, respuestas
correctas, justificaciones, criterios, niveles, puntajes o notas. Los errores SQL
se traducen a `ReglaPendiente` con mensaje público genérico, sin detalles del driver.

Los SELECT sucesivos no constituyen una fotografía atómica frente a todas las
mutaciones concurrentes. Su resultado puede quedar obsoleto. La duración consultada
no se convierte en duración histórica concedida. No se retienen locks ni se crea
un token de permiso. Revalidar inmediatamente antes de escribir, en otra Session,
tampoco resolvería esa carrera: se necesita una transacción única con bloqueo.

La prueba positiva usa **política y reloj sintéticos de laboratorio**. No demuestra
que RF-22 esté aprobado ni habilitado. La fábrica productiva sigue cerrada y no se
han integrado los puertos de mutación de `ParticipacionFacade`.

## Preparación P6: datos y decisiones pendientes

| Tema | Evidencia actual | Necesidad antes de persistir |
|---|---|---|
| Participación | Dominio INTEGER y `ServicioInicio` requieren participación previamente existente. El ER tiene UQ(asignación,matrícula) y estado inicial `pendiente`; no está en metadata integrado | Aprobar provisión, estado y vínculo histórico con convocatoria; implementar la entidad oficial, no confundirla con invitación |
| Convocatoria | UUID con FK a sesión y estudiante UUID; no FK hacia participación/matrícula | Persistir la referencia elegida e impedir que cambios posteriores alteren su titularidad/grupo/sesión histórica |
| Consentimiento | Tabla existente por usuario INTEGER, versión de texto, aceptación y revocación. Intento/dominio lo exigen | Acordar aplicabilidad, texto/versión y efecto de revocación; comprobar titularidad dentro de la transacción. No inferir consentimiento de una matrícula |
| Permisos | `PermisoIntentoExtraORM` pertenece a metadata pendiente y su repositorio no consume cupos | Incorporar entidad oficial solo con su dependencia participación; acreditar docente, participación, cantidad y consumo sin carreras |
| Intentos | Dominio usa inicio UTC y duración positiva; un único activo se comprueba en Application. El ER solo tiene inicio/fin y UQ(participación,número) | Conservar duración histórica concedida; proteger número y único activo también ante escritores concurrentes |
| Tiempo | Scheduling tiene tiempos con zona; asignación/ER usan timestamps sin zona, cupos y fecha límite propios | Aprobar fuente autoritativa, coordinación y zona histórica; no reconstruir duración desde una sesión editable ni permitir tolerancia del cliente |
| Versiones | Asignación fija versión exacta; rúbrica única y regla congeladas por BD2-04/05 | Preservar toda la cadena participación→asignación→versión y evitar cambios históricos de convocatoria/matrícula |
| Respuestas | Puertos de Cases de Participation usan decisiones/opciones INTEGER; Cases actual utiliza UUID | Resolver explícitamente esa compatibilidad antes de guardar respuestas; este incremento no la resuelve |

### Cambios exactos que necesitan autorización posterior

No se implementa ninguno de los siguientes:

1. Crear `participacion` oficial manteniendo UQ(asignación,matrícula) y sus FK.
   Propuesta histórica P4: agregar **`convocatoria_id UUID NOT NULL` FK a
   `convocatoria.id`**, con protección recíproca de titularidad/sesión/grupo.
   **UNIQUE(convocatoria_id) necesita decisión explícita**: una convocatoria de una
   sesión con varios grupos no demuestra por sí sola cardinalidad 0..1 de participación.
   Si se permiten participaciones distintas por asignación, evaluar unicidad por
   (convocatoria,asignación); no escoger esa alternativa automáticamente.
2. Crear `intento` y conectar el permiso excepcional oficial. Propuesta histórica
   P5: **`duracion_concedida_segundos INTEGER NOT NULL CHECK (>0)`** en intento.
   Necesita aprobar la duración/fuente y su captura histórica. El ER literal no
   permite reconstruirla de forma estable después de cambiar Scheduling.
3. Conservar UQ(participación,número) y aprobar un índice UNIQUE parcial por
   participación para el estado activo, con estados exactos acordados. Añadir
   integridad de consentimiento/permiso propios; FK separadas no prueban pertenencia.
4. Aprobar protecciones de contexto histórico de convocatoria/matrícula y el estado
   inicial/condiciones académicas de participación. No imponer nuevas columnas,
   triggers ni cardinalidades por esta documentación.

Una derivación temporal convocatoria→sesión→asignación/matrícula puede leerse con
el esquema actual (implementado aquí), pero no registra qué convocatoria originó
una participación ni conserva su relación ante reasignaciones futuras. La falta de
esa FK y de duración histórica son bloqueos concretos, no permiso para omitirlas.
No se añaden entidades fuera de las 28 ni se elimina soporte técnico actual.

### Límite transaccional requerido para el inicio futuro

`UnidadTrabajoSQLAlchemy` ya dispone de una Session nueva compartida y un commit.
Hoy solo compone repositorio/resultados inyectados; los `IdentityPort` y
`SchedulingPort` de `ServicioInicio` se reciben por separado. Su mera existencia no
demuestra que las autorizaciones compartan la transacción.

La futura composición debe inyectar todos los adaptadores desde esa misma Session:

1. Establecer un orden común de locks para cuenta/vínculo, convocatoria/sesión,
   asignación/matrícula, participación, consentimiento y permiso. Revisar ese orden
   con los locks de versión BD2-04/05 antes de fijarlo; no prometer ausencia de deadlocks.
2. Releer identidad/rol y relaciones, estado y código individual, RF-22/fechas,
   matrícula, consentimiento y cupos bajo esos locks. Detectar cambios mientras
   se espera; las otras operaciones de retiro/revocación deben cooperar.
3. Materializar o recuperar la participación según cardinalidad aprobada, bloquearla
   y comprobar intentos previos. Resolver versión/rúbrica exactas; nunca «última».
4. Calcular número/cupo con las reglas aprobadas, capturar una vez el reloj del
   servidor y duración histórica y registrar el intento sin publicar notas.
5. Confirmar una sola vez. Ante SQLSTATE 23505/40001/40P01, rollback completo y
   nueva autorización antes del reintento; no reutilizar este DTO como permiso.

No se afirma que esa transacción esté implementada ni demostrada en BD2-06.

## Pruebas ejecutadas y entorno

Los nuevos tests reutilizan login TestClient/JWT real, repositorios SQL y resolver
persistente. Usan SQLite en memoria y PostgreSQL 17 nuevo creado por
`motor_postgresql_desechable`, con ID/nombre/etiqueta propios, puerto efímero
127.0.0.1, tmpfs sin volúmenes persistentes, base inicialmente vacía y readiness TCP
con `SELECT current_database()`. El `finally` verifica y elimina solo el contenedor
propio. Se ejecutan las migraciones existentes únicamente dentro de ese laboratorio.

Se retiran del subproceso las variables `TEST_DATABASE_URL`, `SPS_IDENTITY_TEST_URL`
y `SPS_PERSISTENCE_LAB_URL`; `SPS_TEST_POSTGRESQL=0` evita conexiones externas y
`SPS_TEST_IDENTITY_MAPPING_DOCKER=1` habilita solo contenedores nuevos. `.env` no se
modifica ni se utiliza como conexión de pruebas. No se usan bases del equipo.

SQLite recibe una clave de caso sintética explícita en la fila de fixture, pues
no dispone del generador PostgreSQL; no se aplica a históricos reales. Se corrigen
zonas UTC solo en las fixtures SQLite existentes. Los casos de referencias erróneas
de Cases usan una función inyectada solo en tests para devolver otra rúbrica/versión;
los demás vínculos se leen realmente de SQL. No se desactivan FK/triggers.

- Primer desarrollo: **13 failed, 37 errors**, sin aprobadas. Fallos de las fixtures
  nuevas (parámetro temporal omitido y colisión de IDs con el contador compartido)
  y error de preflight Docker al inspeccionar `postgres:17`. Se corrigieron las
  fixtures y se verificó la imagen local con su nombre completo, sin instalar,
  descargar ni cambiar la infraestructura compartida de pruebas.
- Grupo inicial corregido: **50 passed, 0 skipped, 0 failed/errors, 1 warning**,
  12,92 s. SQLite y PostgreSQL, ejecución independiente.
- Grupo ampliado: **189 passed, 0 skipped, 0 failed/errors, 1 warning**, 47,69 s.
  Incluye 54 tests nuevos (27 SQLite y 27 PostgreSQL), 106 de 8A y 29 del puente.
- Suite general final: **1244 passed, 38 skipped, 0 failed, 0 errors,
  1 warning**, 171,91 s. Incluye de nuevo las 54 pruebas nuevas, con la adaptación
  final que reutiliza `id_entero` de Identity. Se conservan las 1190 aprobadas de
  la fase anterior. Las omitidas no se consideran aprobadas: 29 requieren la URL
  externa de Identity, tres conexiones Participation están deshabilitadas y seis
  requieren otra URL de persistencia. No se habilitan contra bases del equipo.
  La advertencia es la deprecación conocida de Starlette/TestClient/httpx.

Comando de la suite, ejecutado en un subproceso con el entorno aislado anterior:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Se comprueban matrícula propia/ausente/inactiva/ajena, otro grupo, convocatoria
ajena/retirada/inexistente, código incorrecto, asignación inexistente/ID inválido,
otra sesión/versión, referencia errónea de familia/rúbrica/número/regla, identidad
ambigua, error SQL sin detalles, RF-22 cerrado, publicación posterior sin sustitución,
ausencia de datos privados y ausencia de escrituras/autoflush/commit con objetos
pendientes. La regresión 8A conserva JWT/roles y fachada 503. No se afirma haber
probado inicio persistente, políticas definitivas, evaluación ni concurrencia de
intentos no implementados.

## Archivos y estado final

- Modificado: `backend/app/modules/participation/application/integration_ports.py`,
  ampliación aditiva; no altera el contrato previo de ingreso.
- Nuevo: `backend/app/modules/participation/infrastructure/academic_context.py`.
- Nuevo: `backend/tests/integration/test_participation_academic_context.py`.
- Nuevo: este documento.

No se modifican ORM, migraciones, APIs, Cases, Identity ni Scheduling. Las
protecciones BD2-04 y BD2-05 se mantienen. La cabeza Alembic y el metadata
siguen siendo `20261102_assignment_bridge` y 23 tablas integradas, respectivamente.
Se verifican una sola cabeza y nueve revisiones; no se crea otra revisión.

`git diff --check` pasa con salida 0. La advertencia LF/CRLF afecta a un archivo
de repositorio de Cases previo, que esta fase no modificó. Los nuevos archivos
tampoco tienen espacios finales. Se conserva la rama y todos los cambios locales
acumulados sin commit. Comparación SHA-256 respecto de la captura inicial:
únicamente se modifica `integration_ports.py`; no desaparece ningún archivo previo.
Los tres archivos nuevos están enumerados arriba. La regresión histórica genera
además `laboratorio_bd2_04/evidencia_0105cccca04e42cc8db410cc3c48c279.json`, con sus
comprobaciones y limpieza, sin sobrescribir evidencias previas ni modificar SQL.

El inventario final de contenedores con etiqueta `sps.identity.mapping.lab=true`
está vacío. Los recursos propios fueron eliminados por los fixtures. No se ejecutó
ninguna migración sobre una base persistente ni se alteraron recursos del equipo.

No se realizan commit/push/merge, cambio de rama ni operaciones destructivas.
Se detiene la tarea en BD2-06; BD2-07 no se inicia.
