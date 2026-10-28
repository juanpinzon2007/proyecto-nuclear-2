# Quinto incremento: preparación de persistencia y propuesta para aprobación

## Estado verificado y alcance de lo implementado

La rama inspeccionada es `martin`. Existe una sola `Base` en `app/db/base.py`, un
motor/fábrica de sesiones compartidos en `app/db/session.py`, y Alembic apunta a
`Base.metadata`. Su historial está vacío: `versions/` solo contiene `.gitkeep`.
No se encontraron modelos ORM académicos ni migraciones de los otros módulos.
No hay DDL compartido definitivo ni constancia local de aprobación de todos los
detalles necesarios. El dibujo ER no basta para confirmar restricciones reales,
secuencias, interpretación temporal o estrategia de registro de claves foráneas.

Docker está instalado pero su motor no estaba disponible. La configuración
compartida tampoco tiene contraseña PostgreSQL. No se comprobó una base remota ni
se inspeccionó un esquema real. No se levantan servicios ni se generan credenciales.

| Componente | Implementado ahora | Límite |
| --- | --- | --- |
| `unit_of_work.py` | Sesión SQLAlchemy por operación, commit común, rollback y cierre | Requiere constructores de repositorios completos; no conecta adaptadores ficticios |
| `queries.py` | Lecturas parametrizadas de participación, intento y pasos; reconstrucción del dominio | Recibe tablas existentes y decisiones de mapeo explícitas; no escribe |
| `codecs.py` | Conversión temporal explícita y comprobación exacta NUMERIC(p,s) | No inventa zona, redondeo o tratamiento académico |
| `errors.py` | `MapeoPersistenciaPendiente`, compatible con `ReglaPendiente` | Bloquea reconstrucciones que perderían información |

No se crean clases ORM, tablas, otra Base, metadatos de producción, migraciones,
motor, sessionmaker ni configuración duplicada. Las únicas tablas descritas en
Python son fixtures aisladas en memoria para compilar SQL durante pruebas; nunca
se ejecuta DDL. No se usa `create_all()` ni SQLite.

## Qué puede hacer el adaptador de lectura

`TablasLecturaParticipacion` recibe objetos `Table` del futuro esquema compartido
o de una reflexión explícita acordada con el equipo. Exige nombres y columnas
del ER, con IDs enteros. No declara modelos de otros desarrolladores y no afirma
validar aprobación, claves foráneas, índices o semántica por comprobar esos nombres.

`LecturasParticipacionSQLAlchemy` implementa:

- `obtener_participacion`: devuelve la entidad con su asignación y membresía.
- `obtener_intento`: recupera el intento y sus pasos ordenados.
- `listar_intentos`: devuelve las ejecuciones de una participación; una lista vacía
  no fabrica un intento ni acredita por sí sola una ausencia.

No implementa el puerto completo `RepositorioParticipacion`: faltan generación de
IDs, inserción y actualización seguras. No debe pasarse como si fuera ese repositorio
a `ParticipacionFacade`. Tampoco existe un repositorio SQL de resultados completo:
el ER no permite reconstruir todavía el DTO definitivo con toda su referencia,
modalidad y política. No se presenta un `SELECT nota_final` como evaluación oficial.

Para reconstruir un intento hay que proporcionar:

1. Un mapeo explícito de strings persistidos a `EstadoIntento`. No se asume que
   los valores internos EN_CURSO/FINALIZADO/VENCIDO ya sean los estados de la BD.
2. `FechasPersistencia` con política acordada para columnas sin offset, o rechazo
   de esos timestamps si todavía no existe un acuerdo.
3. `duracion_historica(session, id_intento)` desde una fuente histórica real que
   use la misma transacción. No consultar la duración actual de Scheduling para
   reconstruir un intento anterior. Sin esa fuente se bloquea la operación.

La reconstrucción utiliza las entidades actuales, incluidas sus validaciones.
Si `tiempo_segundos` de datos existentes no significa segundos desde el inicio
hasta el último guardado, debe acordarse el mapeo; no se ajusta silenciosamente.
No hay carga de usuarios, casos, opciones o rúbricas mediante ORM duplicado.

## Unit of Work y conexión futura con Facade/Strategy

`UnidadTrabajoSQLAlchemy` implementa el ciclo de vida requerido por los puertos
existentes sin cambiar sus firmas. Recibe constructores de repositorios que
recibirán **la misma Session**. Si no se inyecta una fábrica de sesión de prueba,
usa `get_session_factory()` de la configuración compartida, al entrar al contexto.

Abre una transacción, deja a los repositorios consultar/modificar sin commits
propios y confirma solo en `commit()`. Salir sin commit o por excepción revierte
la transacción y cierra la sesión. Una unidad terminada no se reutiliza; una
operación posterior requiere otra unidad y sesión. Una sesión ya activa se rechaza
sin confirmar ni revertir su transacción ajena. Fallar al construir un repositorio
cierra la sesión nueva que pertenecía a la unidad.

SQLSTATE 23505 (unicidad), 40001 (serialización) y 40P01 (deadlock) se traducen a
`ConflictoActualizacion` tras rollback. No se reintenta automáticamente ni se
suprime un error de FK 23503 como si fuera una carrera transitoria. No se publican
mensajes SQL privados como texto del conflicto.

Cuando existan repositorios de escritura aprobados, la fábrica que consume Facade
construirá una nueva unidad con esos constructores. Strategy seguirá preparando
evidencias y CalculadorRubrica calculando; el repositorio conservará el resultado
íntegro, no repetirá cálculos ni seleccionará una política por su cuenta.
Sin `crear_resultados`, acceder a ese repositorio falla con mapeo pendiente.
No se conecta esta unidad a los endpoints ni se sustituyen sus dependencias cerradas.

**Cierre y evaluación conjunta:** el flujo actual confirma el cierre y después
solicita evaluación en otra operación. Este incremento no cambia esa semántica:
NO ofrece todavía atomicidad conjunta del cierre académico y su resultado.
La unidad puede agrupar escrituras de ambos repositorios en una sesión, pero
eso no demuestra que los servicios actuales ejecuten ambas en una transacción.

Propuesta para aprobación: mantener los endpoints/casos de uso existentes y, cuando
haya rúbrica, política y esquema completos, añadir una operación Application
explícita que cierre, prepare los datos, calcule e inserte el resultado dentro de una sola
unidad. Debe decidirse qué ocurre si la política está pendiente: el cierre actual
no puede quedar rehén de una regla aún no aprobada. Esa ampliación necesitaría
pruebas nuevas de ambos resultados y rollback; no se cambia ahora el contrato ni
se afirma que las pruebas de dos repositorios sin BD demuestren esa atomicidad.

## Modelo ER frente a propuestas de los PDF

Se consultaron los cuatro archivos de `_referencias_locales/`, especialmente:

- Agile Inception, p. 9: parcial, ausencia y redondeo tienen precisiones pendientes.
- Análisis de Sistemas, p. 32: ausencia sin intento y resultados asociados al
  contexto académico; el UUID descrito allí no reemplaza los IDs enteros del ER.
- Ingeniería de Software II, pp. 25, 27–28: VERSION_CASO, CONVOCATORIA,
  RESPUESTA_PARTICIPACION, RESULTADO_EVALUACION y DETALLE_EVALUACION son propuestas
  diferentes. No se crean tablas equivalentes con esos nombres en este incremento.
- Imagen ER: separa participacion, intento, paso_simulacion, resultado_intento,
  resultado_criterio y resultado_participacion. Es la referencia de esta propuesta.

## Claves foráneas que deben coordinarse

| Tabla/columna de Participación | Destino representado en el ER | Coordinación |
| --- | --- | --- |
| participacion.id_asignacion | asignacion_caso.id_asignacion | Maicol |
| participacion.id_grupo_estudiante | grupo_estudiante.id_grupo_estudiante | Maicol y contrato de identidad de Alejandro |
| intento.id_participacion | participacion.id_participacion | Martín |
| intento.id_consentimiento | consentimiento.id_consentimiento | Alejandro |
| intento.id_permiso_extra, nullable | permiso_intento_extra.id_permiso_extra | Alejandro |
| paso_simulacion.id_intento | intento.id_intento | Martín |
| paso_simulacion.id_decision | decision.id_decision | Juan Andrés |
| paso_simulacion.(id_opcion, id_decision) | opcion_respuesta.(id_opcion, id_decision) | Juan Andrés; confirmar clave compuesta referenciable |
| resultado_intento.id_intento | intento.id_intento | Martín; confirmar unicidad real |
| resultado_criterio.id_resultado | resultado_intento.id_resultado | Martín |
| resultado_criterio.id_criterio | criterio_rubrica.id_criterio | Juan Andrés |
| resultado_criterio.(id_nivel, id_criterio) | nivel_criterio.(id_nivel, id_criterio) | Juan Andrés; confirmar clave compuesta |
| resultado_participacion.id_participacion | participacion.id_participacion | Martín; resumen/consolidación aparte del intento |

Alejandro también coordina la autorización extraordinaria que referencia una
participación y al docente creador. No se declara su ORM aquí para satisfacer
una FK faltante. Antes de Alembic debe acordarse cómo registrar las tablas de
todos los módulos en la misma metadata y el orden de sus revisiones. Las
referencias ORM podrán resolverse por nombre una vez exista ese registro común.

## Propuesta concreta de mapeo y pendientes indispensables

| Elemento | Mapeo propuesto sin crear tablas | Decisión pendiente antes de escribir |
| --- | --- | --- |
| Participacion | IDs enteros y campos del ER de participacion | Responsable de materializar convocados, unicidad asignación/membresía y estados |
| Intento | IDs/referencias, número, inicio/fin, estado en intento | Mapeo de estados e instantánea del límite individual |
| PasoSimulacion | Campos homónimos de paso_simulacion | Selección actual frente a historial/revisitas y significado de tiempo_segundos |
| Calificación de intento | nota_final/fecha_calculo de resultado_intento | Guardar modalidad, referencia histórica y política suficiente para reproducir |
| Criterios | resultado_criterio con criterio y nivel reales | Escala de aportes, FK compuesta y niveles válidos para faltantes |
| Resumen/ausencia | resultado_participacion, sin intento inventado | Consolidación y evidencia de ceros por decisión no representada en el ER |

**Límite individual:** el dominio conserva `tiempo_maximo`, pero el ER de intento
solo muestra inicio y fin. Recomendación para revisar: una columna histórica
`vence_en TIMESTAMPTZ NOT NULL` en intento; permitiría reconstruir la duración
como vence_en − inicio. No se añade. Una alternativa acordada es una instantánea
inmutable existente, si el equipo demuestra dónde se conserva. Nunca usar una
asignación mutable actual ni inferir el límite a partir de fin.

**Resultados:** el ER no muestra modalidad de intento, versión de rúbrica ni
identificador de política de cálculo. Hay que aprobar dónde se conservan esas
referencias, por ejemplo modalidad en resultado_intento y referencias inmutables
reales de rúbrica/política. No se decide unilateralmente la estructura de Cases
ni se introduce un JSON que simule un esquema académico alternativo.

**Ausencia:** puede tener resumen en resultado_participacion, pero resultado_criterio
depende de resultado_intento. No existe el detalle por decisión ausente que propone
el PDF. Sigue bloqueada la persistencia definitiva de ese DTO hasta acordar el
mapeo; no se fabrican intentos ni se reutiliza otra tabla con distinto significado.

**Decimales:** nota_final/nota_definitiva aparecen como NUMERIC(4,2) y
puntaje_obtenido como NUMERIC(5,2). `decimal_exacto` rechaza, por ejemplo,
0.333333 en escala 2 o 100 en NUMERIC(4,2). No redondea ni trunca para hacer que
un resultado quepa. Los aportes del calculador pueden necesitar más precisión;
su representación debe acordarse antes de escribirlos.

**Tiempo:** el ER usa timestamp sin especificar una convención de zona. La zona
del usuario/equipo no constituye política de BD. Se debe acordar UTC explícito
para esos valores o adoptar columnas con zona mediante migración aprobada.
El codec rechaza horas locales ambiguas/inexistentes y no genera fechas con
el reloj local. La fecha de cálculo de una escritura futura deberá proceder
del reloj del servidor inyectado y conservarse ante reintentos.

## Restricciones propuestas para revisión, no migraciones ejecutadas

- Unicidad de participación por (id_asignacion, id_grupo_estudiante), si se confirma
  que esa fila representa la convocatoria individual del ER.
- UNIQUE(id_participacion, numero_intento) y un índice único parcial que impida
  dos intentos activos, usando el valor de estado aprobado. Confirmar origen
  SERIAL/IDENTITY/secuencia para IDs; no usar MAX(id)+1.
- Para la selección actual: UNIQUE(id_intento, id_decision) y
  UNIQUE(id_intento, numero_paso). Si se necesita historial o revisitas con
  varias filas, acordar primero su representación y no aplicar estas reglas a ciegas.
- UNIQUE(resultado_intento.id_intento), UNIQUE(id_resultado,id_criterio) en
  resultado_criterio y UNIQUE(resultado_participacion.id_participacion).
- Claves compuestas de opción/decisión y nivel/criterio, con sus UNIQUE de origen.
- Coherencia asignación/grupo/estudiante y criterio/rúbrica/caso: una FK simple
  no garantiza por sí sola toda esa pertenencia; debe acordarse la estrategia
  relacional y validarse en Application dentro de la transacción.
- CHECK de porcentajes/rangos/tiempos acordados y política que conserve evidencia
  académica: evitar borrados en cascada de intentos, pasos y resultados históricos.

## Concurrencia: implementado, propuesto y no verificado

El modo `bloquear=True` del adaptador prepara `SELECT ... FOR UPDATE` y ordena
bloqueos por participación y después intento. La lectura inicial del intento,
sin bloquear, solo descubre el padre; se revalida su pertenencia al bloquearlo.
Los pasos se leen bajo el bloqueo de su agregado. Los futuros escritores deben
seguir el mismo orden; código externo que escriba sin ese protocolo rompe la garantía.

La compilación PostgreSQL se prueba, pero **no se ejecutó un bloqueo real**.
Sin escritura aprobada no se demuestran ediciones simultáneas, doble finalización,
unicidad real, ausencia frente a un inicio, ni preservación de cambios bajo carga.
Las validaciones Python, las compilaciones y los fakes anteriores no sustituyen
restricciones de BD, aislamiento y pruebas con dos conexiones PostgreSQL.

La futura implementación de guardar debe bloquear, reconstruir el agregado y
comparar con `esperado` antes de modificarlo. No debe borrar/reinsertar todos los
pasos ni hacer upsert de calificaciones. Una calificación existente se recupera
sin recalcular con la rúbrica actual. Los repositorios no hacen commits individuales.

## Pruebas y cómo ejecutarlas

| Grupo | Qué comprueba | Qué no demuestra |
| --- | --- | --- |
| 245 pruebas anteriores | Dominio, Application, Strategy y HTTP con fakes | Persistencia o autenticación reales |
| test_persistence_codecs.py | Exactitud Decimal y política temporal | Almacenamiento de columnas reales |
| test_sqlalchemy_queries.py | Mapeo y SQL PostgreSQL compilado, Session doble | Ejecución SQL ni bloqueos reales |
| test_sqlalchemy_uow.py | Session SQLAlchemy real en memoria, sin conexión | Commit de filas académicas |
| test_postgresql_connection.py | Opt-in de conexión, rollback tras error y tipos del driver | DDL, repositorios académicos o concurrencia |

Comando habitual desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests backend/tests -c backend/pyproject.toml -q
```

Para las tres pruebas PostgreSQL, usar la configuración compartida con una BD de
prueba accesible y habilitar explícitamente:

```powershell
$env:SPS_TEST_POSTGRESQL = "1"
.\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests/test_postgresql_connection.py -q
Remove-Item Env:SPS_TEST_POSTGRESQL
```

Estas pruebas solo usan SELECT; no crean ni modifican tablas. Sin habilitación
se omiten. Si se solicitan explícitamente y falta conexión/configuración, fallan
en vez de declarar una integración exitosa. Este incremento no ejecutó esas
pruebas reales ni agregó SQLite como sustituto.

## Acuerdos necesarios con cada compañero

- **Juan Andrés:** tipos/claves de decision, opcion_respuesta, criterio y nivel;
  UNIQUE compuestos y referencia histórica de contenido/rúbrica/políticas.
- **Alejandro:** consentimiento y permiso extraordinario, su identidad/FK y
  consumo concurrente del cupo, sin duplicar sus entidades ORM.
- **Maicol:** asignación, membresía y materialización de participaciones; duración
  histórica, cambios de programación y protocolo de cierre/ausencias frente a inicio.
- **Equipo:** aprobar DDL, estados, timestamps, secuencias, restricciones, precisión,
  versionado, consolidación y orden de migraciones. Después implementar escritores
  y resultados e integrar pruebas PostgreSQL de dos conexiones antes de habilitar HTTP.

Referencias técnicas: [sesiones SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[reflexión](https://docs.sqlalchemy.org/en/20/core/reflection.html) y
[dialecto PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html).
