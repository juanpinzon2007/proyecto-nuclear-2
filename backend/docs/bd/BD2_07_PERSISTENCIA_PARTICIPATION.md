# BD2-07 — Persistencia autorizada D1–D4

Actualización 2026-11-02 · Rama `feature/integracion-backend`.
La autorización expresa posterior D1–D4 sustituye el bloqueo de diseño del informe
previo, que se conserva al final como antecedente histórico.

## 1. Resultado implementado

Se integran **participacion, intento y permiso_intento_extra**, todas entidades
originales del ER28. La tercera es la dependencia obligatoria de la FK original
nullable de intento; se reutiliza la clase de Identity, sin duplicarla ni incorporar
automáticamente la retroalimentación pendiente. No se conceden permisos al migrar.

| Decisión autorizada | Implementación |
|---|---|
| D1 | UNIQUE(participacion.convocatoria_id); reintentos permanecen bajo la misma participación; UQ(participación,número) en intento |
| D2 | FK real de convocatoria, PK/FK/UQ originales; guards de titularidad, grupo/sesión y contexto histórico recíproco |
| D3 | `intento.duracion_concedida_segundos NUMERIC(20,6) NOT NULL CHECK (>0)`; inicio/duración inmutables; fuente de lectura histórica explícita |
| D4 | Índice UNIQUE parcial por participación WHERE estado='EN_CURSO'; serialización de altas por participación y rechazo de estados inventados |

El esquema queda preparado, **no el inicio productivo**. No hay repositorio de
escritura que omita controles, endpoint nuevo, router habilitado, nota oficial ni
política RF-22 artificial. `obtener_facade` sigue cerrado con 503.

## 2. Esquema y Alembic

Nueva revisión **`20261102_participation_history`**, padre real verificado
**`20261102_assignment_bridge`**. Previo a los cambios se comprobaron rama, estado
Git, 23 tablas integradas y una cabeza. No se modifica ninguna revisión anterior.
Se conservan los UUID y el DBML original. El incremento no hace backfills.

Tablas y atributos:

- `participacion`: cinco columnas originales más `convocatoria_id UUID NOT NULL`;
  PK INTEGER autogenerada; FK a asignación, matrícula y convocatoria; UNIQUE de
  convocatoria y UNIQUE(asignación,matrícula). Estado conserva el default literal
  `pendiente`; no se inventa una máquina de estados de participación.
- `permiso_intento_extra`: las seis columnas originales, sin adaptaciones. Se integra
  **solo** `PermisoIntentoExtraORM` en Base.metadata; `RetroalimentacionDocenteORM`
  continúa en metadata separado. No se presuponen cantidad ni concesión efectiva.
- `intento`: ocho columnas originales más duración concedida. PK INTEGER; tres FK
  originales; UNIQUE(participación,número); número positivo; duración positiva;
  estados exactamente `EN_CURSO`, `FINALIZADO`, `VENCIDO`; activo sin fin y cerrado
  con fin no anterior al inicio. `INCOMPLETA` no es un estado de ejecución.

NUMERIC(20,6) conserva los microsegundos de `timedelta`; elegir INTEGER segundos
habría truncado duraciones válidas del dominio. No hay DEFAULT de duración ni se
deduce su valor de Scheduling. No se interpreta la duración sintética de los tests
como regla académica aprobada. Las fechas conservan TIMESTAMP sin zona del ER;
su conversión requiere la zona explícita de `FechasPersistencia`, todavía pendiente.
Los checks de cierre operan sobre esos timestamps sin zona: antes de un escritor
real debe acordarse su interpretación (por ejemplo UTC), incluida la conservación
del tiempo transcurrido si se pretende guardar hora local con cambios DST. Las
fixtures no aprueban esa política ni justifican una conversión implícita.

El metadata pasa a **26 tablas integradas**. Esto no significa «26 de las 28
oficiales completas»: se conservan las estructuras técnicas ya existentes y las
diferencias conocidas con Cases. No se eliminan tablas para ajustar un conteo.
El esquema SQLite tiene FK/CHECK/UNIQUE/índice parcial, pero **no** los guards
PostgreSQL ni una garantía simulada de concurrencia.

## 3. Garantías PostgreSQL y alcance

Se instalan cinco funciones `bd207_*`, con SECURITY INVOKER, search_path acotado y
tablas public explícitas; nueve triggers nuevos. No se reemplazan las funciones ni
los 18 triggers de BD2-04 o el trigger de asignación BD2-05: total **28 triggers**.

| Protección | Garantía |
|---|---|
| `bd207_participacion` | En alta exige matrícula activa, grupo de asignación, misma sesión de convocatoria ACTIVA y una sola identidad Scheduling del usuario que coincida con el UUID convocado |
| Contexto de participación | No permite cambiar PK, asignación, matrícula, convocatoria ni fecha de registro. No permite borrar participación histórica |
| `bd207_padre` sobre convocatoria/matrícula | Con participación existente impide reparentar estudiante, grupo, sesión o identificadores; las FK impiden huérfanos. Permite registrar retirada/inactividad sin cambiar identidad |
| `bd207_identidad` | Serializa por cuenta y bloquea cambios, eliminación o incorporación de otra identidad Scheduling cuando esa cuenta tiene una participación histórica; los vínculos Cases permanecen independientes |
| `bd207_intento` | Serializa alta por participación; consentimiento del mismo alumno y permiso, cuando se referencia, de esa participación. No cambia identidad/inicio/duración ni reabre/modifica un intento cerrado |
| Consentimiento/permiso usados | Congela propietario/versión/aceptación del consentimiento y el permiso referenciado; permite registrar revocación del consentimiento, sin decidir su efecto académico |
| Cierre del intento | FINALIZADO antes del vencimiento, VENCIDO exactamente en inicio+duración. No usa programación posterior para recalcular el fin |
| `bd207_no_truncar` | Rechaza TRUNCATE de participación e intento, incluso si se intenta eludir el historial por esa vía |

Los triggers sobre tablas anteriores solo protegen referencias nuevas usadas; no
añaden columnas ni cambian sus PK, tipos, estados o datos históricos. Son la parte
recíproca de D2: validar únicamente INSERT de participación permitiría romper la
asociación actualizando después convocatoria, matrícula o identidad.

No se verifica JWT dentro de PostgreSQL ni se acredita autorización de inicio con
una fila. Se permite persistir historia estructural coherente; la aplicabilidad del
consentimiento, rol del concedente, cantidad disponible de permisos, número de
intentos autorizado, RF-22 y duración concedida deben verificarse en Application.
El índice parcial no concede el segundo intento al cerrar el primero.

## 4. Bloqueos, concurrencia y rollback

Alta de participación: bloquea matrícula FOR SHARE, cuenta FOR UPDATE, convocatoria
FOR UPDATE y asignación FOR SHARE; verifica de nuevo pertenencia e identidad. La
cuenta es el árbitro para evitar un segundo vínculo Scheduling concurrente: no basta
con bloquear la identidad existente, porque otro vínculo sería una fila nueva.
El guard de identidad también bloquea las cuentas afectadas, ordenadas por PK.

Alta de intento: bloquea participación FOR UPDATE antes de verificar consentimiento
y permiso bajo FOR SHARE. El índice parcial y la UQ del número son árbitros de
concurrencia. Los guards recíprocos de los padres impiden que la validación quede
obsoleta por cambios posteriores de propiedad. Dos inserciones simultáneas no
producen dos activos, ni dos participaciones por la misma convocatoria.

Se verifican carreras reales en READ COMMITTED y, para intentos, SERIALIZABLE.
SERIALIZABLE puede abortar con 40001: es un resultado seguro, no acceso concedido.
**REPEATABLE READ se rechaza con 40001** en estos guards para evitar validaciones
sobre snapshots anteriores al commit del competidor. Es una limitación técnica
explícita; no se declara soporte para esa modalidad ni se reintenta automáticamente.

Los locks pertenecen a la transacción del llamador. Puede haber esperas, timeouts o
deadlocks con otros órdenes de adquisición: se requiere rollback completo y nueva
autorización, nunca omitir un guard. No se promete ausencia universal de deadlocks.
Las pruebas tienen límites de espera; comprueban tanto éxito único como rechazo
del competidor y rollback sin filas parciales.

## 5. Fuente de lectura y contrato futuro de inicio

`consultar_duracion_historica(Session, id_intento)` lee únicamente el NUMERIC
persistido y devuelve `timedelta` exacto. No usa Scheduling ni hace autoflush,
commit o cierre. Es una fuente explícita para el callback ya existente de
`LecturasParticipacionSQLAlchemy`; no cambia sus defaults ni presenta ese lector
como repositorio completo. `paso_simulacion` sigue pendiente de compatibilidad.

La futura UoW deberá componer **con su misma Session** los autorizadores Identity,
Scheduling y el repositorio, no solo agregar este ORM al repositorio actual.
`ServicioInicio` los recibe hoy desde fuera de la fábrica; eso no demuestra que
compartan la transacción. La consulta informativa BD2-06 permanece sin cambios.

Antes de INSERT deben revalidarse cuenta/rol, identidad, matrícula/grupo, contexto
JWT y convocatoria/código/estado/sesión, asignación y versión/rúbrica exactas,
consentimiento aplicable y permisos/cupos. La política confiable y el reloj del
servidor determinan ingreso y duración, que se captura una sola vez en el intento.
No usar este DTO ni otro resultado previo como permiso reutilizable.

Se debe acordar un orden de locks común con retiro/reprogramación/revocación y
estos guards. Los locks del inicio deben tomarse antes de revalidar datos ORM
cacheados. Una sola confirmación guarda el agregado; 23505/40001/40P01 o fallo de
política/infraestructura descarta todo y obliga a comenzar otra UoW y reautorizar.

## 6. Upgrade, downgrade y datos anteriores

Upgrade aditivo: crea las tres tablas nuevas, constraints, índice parcial y guards.
No asigna convocatorias a históricos ni crea usuarios, consentimientos o permisos.
No existe un backfill automático ni se modifican filas previas.

Downgrade bloquea las tres tablas nuevas y **rechaza cualquier dato en cualquiera
de ellas**, incluso un permiso sin intento. Solo sobre estado vacío elimina sus
propios triggers/funciones y tablas, preservando BD2-04/05. No borra historial para
facilitar la reversión. Requiere una ventana sin escritores por sus locks DDL.
Se verifican upgrade/downgrade/reupgrade en PostgreSQL nuevo.

## 7. Pruebas ejecutadas en esta implementación

- Prevalidación de regresiones sin Docker: **55 passed, 41 skipped, 1 warning**,
  7,89 s; las omitidas requerían el laboratorio, no se cuentan como aprobadas.
- Grupo nuevo: **55 passed, 0 skipped, 0 failed/errors**, 17,46 s.
- Grupo ampliado: **234 passed, 0 skipped, 0 failed/errors, 1 warning**, 65,04 s.
  Repite las nuevas pruebas y valida puente, BD2-06, metadata, Identity y BD2-01.
- Primera suite general: **1299 passed, 38 skipped, 0 failed/errors, 1 warning**,
  159,05 s. Después se agregó una regresión de precisión, por lo que este resultado
  no se presenta como validación del estado final.
- La frontera numérica adicional reprodujo **1 failed, 55 deselected**, 6,45 s:
  PostgreSQL resolvía `interval * numeric` mediante float8 y perdía un microsegundo
  en una duración amplia representable por el dominio. Se corrigió el guard para
  sumar días enteros y segundos restantes mediante intervalos textuales, evitando
  esa conversión. El valor amplio es una prueba técnica, no una política académica.
- Grupo nuevo final: **56 passed, 0 skipped, 0 failed/errors**, 16,49 s:
  **16 SQLite y 40 PostgreSQL**. Incluye la regresión de precisión corregida.
- Suite general final: **1300 passed, 38 skipped, 0 failed, 0 errors,
  1 warning**, **158,85 s**. Repite todas las regresiones después de la corrección
  de precisión. Son 56 aprobadas nuevas respecto de la línea base de 1244.
  Las 38 omitidas no se cuentan como aprobadas: 29 requieren URL externa Identity,
  tres conexiones Participation están deshabilitadas y seis requieren otra URL de
  persistencia. Se mantienen cerradas para no utilizar bases del equipo.
  La advertencia es la deprecación conocida Starlette/TestClient/httpx.

Comando de suite, con el entorno de aislamiento descrito abajo:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Las nuevas pruebas usan SQLite para DDL/PK/FK/CHECK/unicidad/rollback/lectura de
duración y PostgreSQL real para guards, contexto histórico, relaciones ajenas,
reprogramación, microsegundos, concurrencia, modo de aislamiento y ciclo Alembic.
Las fixtures crean datos sintéticos explícitos y versiones con el repositorio
real de Cases; nunca desactivan sus triggers. La presencia de un permiso sintético
no demuestra autorización académica real ni una política aprobada de reintentos.

## 8. Aislamiento y compatibilidad

Solo SQLite en memoria y PostgreSQL 17 en contenedores **nuevos**, con ID/nombre/
etiqueta propios, tmpfs sin bind/volumen persistente, puerto efímero 127.0.0.1,
base inicialmente vacía y readiness por conexión TCP real/current_database().
El finally elimina exclusivamente el contenedor creado por el fixture.

El subproceso retira TEST_DATABASE_URL, SPS_IDENTITY_TEST_URL y
SPS_PERSISTENCE_LAB_URL; fija SPS_TEST_POSTGRESQL=0 y habilita solo
SPS_TEST_IDENTITY_MAPPING_DOCKER=1. El test HTTP PostgreSQL anidado usa exclusivamente
su base creada dentro de un contenedor propio. No se utiliza `.env` como conexión
ni se modifica. No hay migraciones sobre bases persistentes o contenedores ajenos.

Se adaptan expectativas de metadata/cabeza en regresiones; las revisiones históricas
se siguen probando en sus destinos originales. Para comparar todo el ORM actual
se sube explícitamente al head nuevo, sin atribuirle estructuras a revisiones viejas.
Los tests de Cases conservan SQL BD2-04 literal y controlan ahora los 28 triggers
de la cabeza completa en la prueba HTTP. No se desactiva ninguna restricción.

## 9. Archivos y siguiente límite

Nuevos: `participation/infrastructure/models.py`, revisión
`alembic/versions/20261102_participation_history.py` y
`tests/integration/test_participation_persistence.py`.

Modificados: `app/db/models.py`,
`identity/infrastructure/academic_models.py` (solo integración del permiso y texto
explicativo), `participation/infrastructure/queries.py` (fuente de duración),
este informe y cinco regresiones: `test_schema_integration.py`,
`test_er28_academic_base.py`, `test_assignment_bridge.py`,
`test_cases_guard_migration.py`, `identity/test_academic_identity_repository.py`.

Estado final verificado: **26 tablas de negocio integradas, diez revisiones y
una cabeza `20261102_participation_history`**, padre `20261102_assignment_bridge`.
Las tablas adicionales siguen siendo entidades oficiales; las estructuras
técnicas preexistentes no se borran. No se certifica el esquema físico de una base
persistente, pues ninguna fue consultada ni migrada.

Comparación SHA-256 con el inventario inicial: solo se modifican los nueve
archivos previos enumerados arriba (tres productivos, el informe y cinco tests),
sin eliminar ninguno. Se conservan los bytes de ER original, revisiones anteriores,
SQL BD2-04/05, Cases, Scheduling, 8A/BD2-06, dominio, Facade, API y patrones.
Además de los tres archivos nuevos, la regresión BD2-04 generó las evidencias
`evidencia_c09bb5e33d22417189afe79ead48d4ed.json` y
`evidencia_ef822d9d373b44e2b4bacb080f525eb1.json` en su laboratorio documental,
sin sobrescribir las anteriores.

`git diff --check`: salida 0, sin errores de espacios; Git advierte sobre futura
normalización LF/CRLF de un archivo previo del repositorio de Cases que esta fase
no modificó. Los nuevos archivos también se verifican por separado. El inventario
final de contenedores con etiqueta `sps.identity.mapping.lab=true` queda vacío.
La rama se conserva y todos los cambios permanecen sin commit. No hubo push,
merge, limpieza global, cambio de rama ni aplicación a una base persistente.

Para preparar 8B faltan políticas de consentimiento, ingreso RF-22, duración
autorizada/cupos/reintentos y zona histórica; después, composición transaccional
de puertos y un repositorio de escritura completo con pruebas end-to-end.
No se abre ingreso productivo, Evaluation ni API. No se modifican los siete
patrones. No se inicia BD2-08 ni se hace commit, push, merge o cambio de rama.

---

<details>
<summary>Antecedente anterior a la autorización D1–D4 (conservado, conclusiones de bloqueo superadas)</summary>

# BD2-07 — Límite de persistencia y autorización concreta pendiente

2026-11-02 · Rama verificada: `feature/integracion-backend`.

## 1. Resultado de esta etapa

**No se incorporan modelos, tablas, columnas, migraciones ni escritores nuevos.**
Se conserva BD2-06 y se prepara el contrato de implementación descrito abajo.
No se declara operativo el inicio persistente ni la simulación completa.

La solicitud autoriza estructuras independientes fieles al ER, pero exige detenerse
antes de modificar claves, columnas, relaciones o cardinalidades indispensables no
aprobadas. BD2-05 autorizó expresamente P1–P3; su informe excluye P4–P6 de esquema.
BD2-06 documentó las decisiones pendientes, sin aprobarlas. Esta nueva solicitud
mantiene ese límite y no elige ninguna cardinalidad ni fuente de duración.

La tabla literal `participacion` **sí es construible en DDL**: sus dos FK ya tienen
destino. No se presenta como un impedimento de PostgreSQL. Sin embargo, crearla
vacía no implementaría el vínculo histórico obligatorio con convocatoria; crear un
escritor que lo omita tampoco es un incremento funcional íntegro de lo solicitado.
Por esa razón se pospone su esquema de escritura hasta resolver la relación exacta.
No se introduce una tabla provisional ni un repositorio que descarte contexto.

`consentimiento`, la estructura independiente que ya coincide con el ER, **ya está
integrada** desde BD2-01. No se duplica. El permiso adicional depende de participación
y no se importa automáticamente desde el metadata pendiente. `intento` agrega el
bloqueo de duración histórica; no se crea una versión que pierda ese dato.

## 2. Evidencia específica y definiciones originales

Se consultaron `identity/reference/sps.dbml` y el objetivo oficial de 28 entidades,
la matriz `A_CONCILIACION_ER_ORM.md`, BD2-05/06, modelos reales, puertos y servicios
de Participation, unidad de trabajo, lecturas SQL, integración 8A y cadena Alembic.
La matriz de BD-1.2 es histórica: sus recuentos de 19 tablas no sustituyen los 23
modelos integrados verificados ahora. No se utiliza el DBML alternativo de 40 tablas.

| Entidad | Definición original relevante | Implementación actual / límite |
|---|---|---|
| `participacion` | `id_participacion INTEGER PK`; `id_asignacion INTEGER FK NOT NULL`; `id_grupo_estudiante INTEGER FK NOT NULL`; `estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'`; `fecha_registro TIMESTAMP NOT NULL`; UNIQUE(asignación,matrícula) | Dominio `Participacion` con los cinco atributos; no modelo integrado. Sin referencia a convocatoria |
| `consentimiento` | PK INTEGER; estudiante FK usuario; versión de texto VARCHAR(30); aceptación TIMESTAMP; revocación TIMESTAMP nullable | `ConsentimientoORM`, integrado. La tabla no decide aplicabilidad ni versión exigida |
| `permiso_intento_extra` | PK INTEGER; participación y profesor FK; cantidad INTEGER DEFAULT 1; justificación TEXT; autorización TIMESTAMP | `PermisoIntentoExtraORM`, fuera del metadata integrado. No duplicar ni eliminar su FK pendiente; su repositorio no consume cupos |
| `intento` | PK INTEGER; participación y consentimiento FK NOT NULL; permiso adicional FK nullable; número INTEGER; estado VARCHAR(20); inicio TIMESTAMP; fin TIMESTAMP nullable; UNIQUE(participación,número) | Dominio `Intento` requiere además `tiempo_maximo`. No existe ORM integrado ni escritor productivo |

Referencias verificables:

- `participation/domain/entities.py`: `Participacion`, `Intento`, `vence_en`.
- `participation/application/services.py`: `ServicioInicio.iniciar` presupone que
  participación existe; comprueba único activo y consulta autorización de cupos.
- `participation/application/ports.py`: `IdentityPort`, `SchedulingPort`,
  `RepositorioParticipacion` y sus garantías de bloqueo/actualización esperada.
- `participation/infrastructure/queries.py`: `_reconstruir` rechaza la lectura de
  intento si no se inyecta una fuente de duración histórica; no la infiere de sesión.
- `participation/infrastructure/unit_of_work.py`: comparte Session con repositorio/
  resultados; no compone por sí sola los puertos Identity y Scheduling del inicio.
- `participation/infrastructure/academic_context.py`: verifica relaciones actuales
  sin locks ni escrituras; su DTO no es autorización transaccional.
- `scheduling/infrastructure/assignment_models.py`: versión/sesión exactas y
  UNIQUE(sesión,grupo), que **no** es UNIQUE(sesión).
- `scheduling/infrastructure/models.py`: UNIQUE(sesión,estudiante) de convocatoria;
  no relaciona una convocatoria con una matrícula elegida.
- `identity/infrastructure/academic_base_models.py`: UNIQUE(grupo,estudiante),
  que permite a un usuario pertenecer a más de un grupo.

## 3. Bloqueos demostrables

### B1. Cardinalidad de convocatoria–participación

El esquema permite una sesión con dos grupos y un estudiante matriculado en ambos.
Existe una convocatoria por (sesión,estudiante), pero pueden existir dos pares
(asignación,matrícula). La UQ original de participación permite ambas participaciones.
Imponer UNIQUE(convocatoria) reduciría ese conjunto; no es una corrección puramente
técnica demostrada por el ER. Elegir la primera matrícula sería una política ficticia.

BD2-06 exige asignación explícita para leer correctamente ese escenario. Persistir
solo sus cinco atributos originales perdería la referencia a la convocatoria
seleccionada. Derivarla otra vez de vínculos actuales no conserva su origen ante
cambios de convocatoria o identidad académica.

### B2. El ER no conserva la duración individual del intento

Contraejemplo ejecutado en memoria con el dominio actual, sin BD ni escrituras:
dos intentos EN_CURSO tienen idénticos ocho atributos del registro original y
comienzan el 2026-11-02 a las 12:00 UTC; uno tiene duración sintética de 30 minutos
y otro de 45. Su fila ER sería idéntica, pero sus vencimientos son **12:30 y 12:45 UTC**.
Los números son datos de demostración, no una duración académica aprobada.

Reproducción conceptual del código ejecutado:

```python
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from app.modules.participation.domain.entities import Intento
from app.modules.participation.infrastructure.queries import INTENTO

a = Intento(id_intento=1, id_participacion=1, id_consentimiento=1,
    numero_intento=1, inicio=datetime(2026, 11, 2, 12, tzinfo=timezone.utc),
    tiempo_maximo=timedelta(minutes=30))
b = replace(a, tiempo_maximo=timedelta(minutes=45))
assert tuple(getattr(a, n) for n in INTENTO) == tuple(getattr(b, n) for n in INTENTO)
assert a.vence_en != b.vence_en
```

`fin` no resuelve el problema: es NULL en un intento activo y al finalizar registra
el cierre real. No se reutiliza como vencimiento ni se calcula la duración histórica
desde una programación editable. Guardar solo la tabla literal perdería semántica.

### B3. FK válidas no bastan para pertenencia

Una FK a asignación y otra a matrícula no demuestran que compartan grupo. Una FK
a consentimiento no demuestra que pertenezca al usuario de esa matrícula, y una FK
a permiso no demuestra que corresponda a esa participación. Se requiere validación
atómica y protección de las referencias frente a mutaciones posteriores.

UNIQUE(participación,número) no impide dos intentos EN_CURSO de números distintos.
Dos procesos que lean el mismo historial necesitan serialización por participación
y una restricción concurrente complementaria. No basta reutilizar el DTO de BD2-06.

## 4. Solicitud mínima de autorización — NO implementada

| Decisión | Cambio exacto propuesto | Qué debe aprobarse |
|---|---|---|
| A07-1 | Crear `participacion` con sus cinco atributos, PK/FK/UQ originales y **agregar `convocatoria_id UUID NOT NULL REFERENCES convocatoria(id)`**, sin convertir UUID en INTEGER | La columna adicional y el vínculo histórico. Elegir A07-2 antes de definir su unicidad |
| A07-2 | Recomendación técnica conservadora: permitir solo una participación por convocatoria mediante **UNIQUE(convocatoria_id)**, con asignación/matrícula explícitas; conservar UQ(asignación,matrícula) | Esta cardinalidad es **propuesta**, no deducida del ER. Si el estudiante debe participar por cada grupo, alternativa: UNIQUE(convocatoria_id,id_asignacion), manteniendo la UQ original. No ejecutar ninguna sin elección |
| A07-3 | Crear `intento` original y **agregar `duracion_concedida_segundos INTEGER NOT NULL CHECK (>0)`** | Fuente de duración y precisión. Si la duración requiere fracciones de segundo, debe ajustarse tipo/contrato antes de migrar; no truncar |
| A07-4 | Mantener UQ(participación,número); proponer **UNIQUE parcial por id_participacion WHERE estado='EN_CURSO'** | Restricción adicional y mapeo de estados persistidos. No imponer todos los estados académicos en un CHECK sin acordarlos |
| A07-5 | Conservar FK originales y aprobar controles SQL de consistencia grupo–matrícula, convocatoria–estudiante/sesión y consentimiento/permiso propios; impedir reparentado histórico de participación | Revisar guards recíprocos y su interacción con actualización/retiro/revocación de tablas existentes. No basta un trigger solo al INSERT que deje modificar después sus padres |

A07-1/3 son las dos columnas adicionales mínimas propuestas, no prueba de que
solo esas columnas resuelvan toda la seguridad. A07-2/4/5 y las políticas siguientes
deben resolverse para fijar el esquema y sus escritores.

No se necesitan tablas de asociación nuevas ajenas al ER28. El permiso excepcional
reutilizaría la clase existente de Identity, migrada al metadata integrado solo
cuando exista su participación real, sin arrastrar `retroalimentacion_docente`.

Decisiones académicas separadas del diseño físico:

- Aplicabilidad del consentimiento, versión de texto exigida y efecto de revocación
  sobre una ejecución ya empezada. El NOT NULL original y el dominio actuales no
  equivalen a aprobación de obligatoriedad universal: no se relaja ni se impone.
- Condiciones de alta y estado inicial de participación. El literal original
  `pendiente` puede preservarse como default; no basta para decidir cuándo provisionar.
- Número de intentos autorizado, autorización/consumo de permisos y situaciones
  en que se permite reintentar. No sumar cantidades o reutilizar permisos sin política.
- Fuente autoritativa y coordinación de duración/cierre entre asignación y sesión;
  zona de timestamps sin offset; RF-22 y fecha límite de ingreso. No inventar tolerancia.
- Vigencia temporal/reingreso de matrícula; `activo=True` de BD2-06 no decide fechas.

## 5. Contrato transaccional futuro, sin implementarlo

### Frontera y composición

Una sola unidad de trabajo debe crear una Session nueva y proporcionar **esa misma
Session** a repositorio de participación, autorización Identity, Scheduling y
consultas de Cases. Los puertos de lectura y la consulta 8A no se vuelven permisos.
No se añade Evaluation ni un commit propio en un adaptador.

`ServicioInicio` recibe hoy Identity/Scheduling fuera de la UoW. La futura fábrica
debe componerlos dentro del alcance de la UoW o adaptar el contexto interno del
servicio; no usar sesiones globales ni pasar una autorización cacheada entre llamadas.
El JWT identifica al solicitante; roles/propiedad se releen en el servidor.

### Serialización necesaria

1. Fijar un orden compatible de locks entre operaciones de inicio, retiro,
   reprogramación, matrícula, consentimiento, permisos y guards de Cases. Candidato:
   cuenta/vínculos → sesión → convocatoria → asignación → matrícula → participación
   → consentimiento → permiso → intento. Ordenar PK cuando haya varias filas.
   **Es un candidato, no una ausencia de deadlocks demostrada**: requiere revisar
   todos los escritores y la adquisición de locks de versión BD2-04/05.
2. Bloquear filas que puedan cambiar la autorización y releerlas tras la espera,
   descartando estado ORM cacheado. Validar estudiante activo, rol, vínculo inequívoco,
   convocatoria/contexto/código/estado y sesión, matrícula/grupo, asignación, versión
   exacta y rúbrica. No bloquear primero un intento y luego su participación.
3. Si participación no existe, no hay una fila que bloquear: usar el padre común
   elegido (p. ej. convocatoria para A07-2 de una sola participación) y la UQ como
   árbitro. Si otra operación la creó, recuperarla y volver a verificar todos sus
   vínculos; no hacer upsert que sobrescriba contexto histórico.
4. Bloquear participación antes de enumerar intentos. Comprobar número, único activo,
   consentimiento propio/válido y permiso de esa participación bajo la política
   aprobada. La FK, por sí sola, no consume ni acredita un permiso.
5. Capturar el reloj del servidor al decidir el inicio, validar ventana RF-22 y
   fecha límite, fijar duración histórica y registrar el intento. Mantener inmutables
   inicio/duración/contexto; el cierre conserva su fecha real, no reemplaza duración.
6. Un solo commit. SQLSTATE 23505/40001/40P01 implica rollback completo; cualquier
   reintento empieza una nueva UoW y reautoriza. Ante timeout, fallo de política o
   infraestructura, no persistir un intento parcialmente autorizado.

Los retiros/revocaciones no cooperativos o cambios directos por SQL exigen guards
recíprocos/constraints. Los locks tomados por un único escritor no garantizan la
integridad frente a todos los demás. No se declara demostrada esa atomicidad futura.

## 6. Primer incremento ejecutable después de aprobación

Recomendación: resolver primero A07-1/2 y estado/provisión de participación; luego
implementar **provisión interna de participación vinculada**, aún sin iniciar intento
ni abrir HTTP. Probar su integridad y ciclo Alembic antes de incorporar permisos e
intentos con A07-3/4/5 y políticas aprobadas. No ampliar todo el módulo de una vez.

Archivos candidatos, no creados ni modificados en esta etapa:

| Archivo | Trabajo siguiente |
|---|---|
| `participation/infrastructure/models.py` | Modelo oficial participación con vínculo aprobado; después intento con duración histórica |
| `app/db/models.py` | Registro explícito solo de modelos ya cerrados y migrados |
| `alembic/versions/<revision_participacion>.py` | Revisión aditiva cuyo padre será la cabeza real entonces verificada; no fijar una cabeza futura por suposición |
| `participation/infrastructure/repositories.py` | Provisión/lectura/guardado con contratos realmente implementables, sin simular métodos pendientes |
| `participation/infrastructure/unit_of_work.py` y `application/services.py` | Composición transaccional de autorizadores sobre la misma Session; mantener Facade |
| `identity/infrastructure/academic_models.py` y repositorio correspondiente | Integrar únicamente permiso cuando sus FK se resuelvan; no duplicar clases |
| `tests/integration/test_participation_persistence.py` | FK/UQ, pertenencia, contexto inmutable, alta concurrente, rollback y downgrade sobre laboratorio nuevo |

Criterios de aceptación de provisión: solo cuenta/convocatoria/matrícula/grupo/
asignación coincidentes; rechazo de referencias cruzadas por SQL y aplicación según
la garantía autorizada; dos altas simultáneas no crean duplicados ni cambian contexto;
una retirada/reasignación concurrente no produce una participación de otro alumno;
rollback no deja filas; downgrade rechaza datos que perdería; una cabeza Alembic;
regresión completa e ingreso HTTP todavía cerrado. La propuesta de intento requerirá
además probar duración conservada tras editar Scheduling, consentimiento y cupos.

## 7. Validación realizada en esta entrega

Comprobación estática ejecutada sin conexión: **23 tablas integradas**,
`consentimiento` existente con sus cinco columnas, ausencia de participación/intento/
permiso en metadata desplegable, una cabeza **`20261102_assignment_bridge`** y nueve
revisiones. El contraejemplo de pérdida de duración se ejecutó en memoria con éxito.

No hay nuevas estructuras para probar: **no se ejecutó un upgrade/downgrade BD2-07
ni se probaron escritores o concurrencia de intentos inexistentes**. Las pruebas de
las revisiones y flujos ya implementados se repiten en la suite general para
comprobar que siguen operativos sus contratos, sin atribuirles cobertura nueva.

Suite general **ejecutada nuevamente en esta entrega**: **1244 passed, 38 skipped,
0 failed, 0 errors, 1 warning**, en **150,90 s**. No hay pruebas nuevas de un
esquema BD2-07, pues no se creó. Las 38 omitidas no son aprobadas: 29 requieren
URL externa de Identity, tres conexiones Participation están deshabilitadas y seis
requieren otra URL de persistencia. La advertencia es la deprecación conocida de
Starlette/TestClient/httpx. No se modificaron pruebas ni dependencias.

Comando ejecutado con las variables de aislamiento descritas abajo:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Las pruebas de concurrencia/rollback/ciclo Alembic que pasaron son las del esquema
vigente, y las pruebas positivas de ingreso usan política sintética solo en sus
fixtures. No demuestran una política temporal real ni concurrencia de inicio
persistente de intentos. Se conserva esa distinción al presentar los resultados.

Se ejecuta exclusivamente SQLite aislado y PostgreSQL 17 nuevo/destructible de los
fixtures existentes. Se retiran TEST_DATABASE_URL, SPS_IDENTITY_TEST_URL y
SPS_PERSISTENCE_LAB_URL del subproceso; SPS_TEST_POSTGRESQL=0 deshabilita conexiones
externas y SPS_TEST_IDENTITY_MAPPING_DOCKER=1 permite solo contenedores nuevos.
El fixture verifica ID/etiqueta propios, tmpfs, puerto TCP efímero 127.0.0.1, base
vacía/readiness real y elimina exclusivamente su recurso en finally. No se modifican
`.env`, datos persistentes, contenedores del equipo ni SQL histórico autorizado.

## 8. Cambios y estado final

Único documento de entrega nuevo: `BD2_07_PERSISTENCIA_PARTICIPATION.md`.
El resultado real es una especificación y solicitud de autorización, **no un
incremento de persistencia implementado**. No se modifican tablas/columnas, ORM,
repositorios, puertos, Facade, API, migraciones ni los siete patrones.

La fachada permanece cerrada con 503; JWT, titularidad, controles de Scheduling,
RF-22 cerrado, BD2-04, BD2-05 y lectura BD2-06 se conservan. No se inicia BD2-08.
Verificación SHA-256 contra la captura inicial: **ningún archivo previo modificado
o eliminado**. Además de este informe nuevo, la regresión BD2-04 generó
`laboratorio_bd2_04/evidencia_dd8439b551614dcba58d89be90569ff0.json`, sin sobrescribir
evidencias anteriores. No hay cambios propios en código Python ni pruebas.

`git diff --check`: salida 0, sin errores de espacios. Se conserva una advertencia
de normalización LF/CRLF sobre el repositorio de Cases modificado en fases previas;
no se cambió ese archivo. Los cambios locales acumulados siguen sin commit. La
rama permanece `feature/integracion-backend`, la cabeza Alembic es la misma y
el metadata conserva 23 tablas. Inventario final de contenedores con etiqueta
`sps.identity.mapping.lab=true`: vacío. No se utilizó ninguna base persistente,
no se modificó `.env` y no hubo commit, push, merge ni cambio de rama.

</details>
