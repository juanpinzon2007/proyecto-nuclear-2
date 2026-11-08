# RF-15 y RF-26 — Seguimiento y valoración docente

> Continuidad del 5 de noviembre de 2026 en el repositorio original, rama
> `feature/backend-continuidad`: ver sección final. Los resultados siguientes
> corresponden al incremento histórico, no a una nueva ejecución.

3 de noviembre de 2026, Bogotá. Worktree `C:\SPS\consolidacion`, rama
`codex/consolidacion-backend`, base `3e09def`, cambios locales sin commit.

## Alcance implementado

Se reutilizan ProxySeguimiento, ServicioSeguimiento, ServicioFeedbackDocente,
AmbitoFeedbackIndividual, RepositorioFeedbackIndividual y la UoW de Identity.
ConsultaSeguimientoSQLAlchemy conecta los puertos de lectura/ámbito con las
tablas existentes. No se duplica el escritor de feedback ni el motor Evaluation.

| Ruta bajo `/api/v1/identity` | Comportamiento |
|---|---|
| GET `/seguimiento/casos` | Casos con participación registrada dentro del ámbito. Se distingue su versión exacta; no se infiere que todas estén terminadas. |
| GET `/seguimiento/casos/{id_caso}/participaciones` | Nueva enumeración de participaciones propias, con estudiante, convocatoria, sesión, versión y estado almacenado. |
| GET `/seguimiento/participaciones/{id_participacion}` | Respuestas e intentos separados, avance por respuestas registradas y feedback general. No consolida intentos ni inventa porcentajes. |
| POST `/seguimiento/participaciones/{id_participacion}/feedback` | Ruta existente: crea o edita una sola valoración. Conserva el contrato 201 para ambas operaciones, PK, autor y destinatario. |

Identity ya está registrado en main: estas rutas tienen composición real sin
modificar main.py ni registrar todo Participation. La configuración real de
JWT/conexión y las asociaciones académicas verificadas siguen siendo necesarias.
Las pruebas acreditan ASGI/TestClient con PostgreSQL desechable, no un despliegue
público ni acceso a una base permanente.

## Seguridad e integridad

- JWT real; cuenta activa y rol/permisos obtenidos del servidor. No se inventa un
  permiso nuevo: el contrato vigente exige DOCENTE y ámbito académico verificable.
- Se comprueban las asociaciones CASES/SCHEDULING del docente y las referencias
  grupo–matrícula–participación–asignación–sesión–versión–caso.
- El ámbito existente se refuerza con convocatoria de esa sesión y asociación
  Scheduling del alumno coincidente. No se confunde UUID con PK INTEGER.
- El Proxy comprueba acceso antes de delegar. Lectura y escritura revalidan de
  nuevo dentro de su transacción; una comprobación previa no autoriza el commit.
- Lecturas históricas no excluyen automáticamente una matrícula o convocatoria
  retirada; no se confunde autorización docente de consulta con permiso de ingreso.
- Los estudiantes no acceden a las rutas docentes. Durante un intento activo no
  se devuelve justificación en el detalle. En cerrados se reutiliza la consulta
  histórica de Cases; no hay nota oficial ni resultado técnico LAB presentado como tal.
- El escritor ya existente usa UPSERT protegido, UNIQUE por participación, FK y
  triggers previos. Se preservan autor/destinatario; rollback conserva el comentario
  previo. Las solicitudes concurrentes dejan una sola fila vigente.
- La trazabilidad disponible es PK, referencias, autor y fecha de la valoración
  vigente. No existe un historial de textos anteriores: se mantiene la decisión
  aprobada de una valoración editable, sin añadir tablas.
- Las fechas de intento se muestran como están persistidas, sin reinterpretar su
  zona histórica, calcular plazos ni cambiar estados al consultar.

RF-16 y excepciones siguen cerrados: no se integra un reporte/ausencia/consolidación
oficial mediante estos puertos. No se conectan notificaciones, RF-22, consentimiento,
repetición ni notas. No hay cambios de ORM, migraciones o DBML.

## Pruebas reales

Nuevo `backend/tests/integration/test_teacher_followup_http.py`: 20 casos HTTP,
con JWT real y PostgreSQL nuevo. Reutiliza la preparación integral 8B: caso/grafo
por API, login estudiantil real y servicio transaccional de inicio con políticas
explícitas SOLO LAB. Los JWT docentes usan el emisor real con clave sintética;
no se implementa ni se acredita un nuevo login público de docentes.

Se demuestra lectura autorizada, separación de ámbito, feedback editable persistido
desde otra Session, rechazo de estudiante/ajeno/anonimato/token inválido, campos
inválidos, revocación de cuenta/rol/asociaciones, ambigüedad, rollback y concurrencia.
La explicación de una versión archivada conserva su referencia histórica.

| Ejecución | Resultado |
|---|---|
| Primera focal | 45 aprobadas, 1 fallida, 0 omitidas: campo opcional nulo alteraba el listado antiguo; se corrigió serialización sin modificar esa prueba. |
| Segunda focal | 114 aprobadas, 21 omitidas, 1 fallida: expectativa 503 de adaptador pendiente; ahora el docente sin asociación recibe 403. Se conserva la denegación y la prueba de excepciones 503. |
| Focal final | 201 aprobadas, 29 omitidas, 0 fallos/errores, 1 advertencia; 104.23 s. |
| General final | 1875 aprobadas, 38 omitidas, 0 fallos/errores, 53 advertencias; 525.38 s. |

La general contiene la focal: no se suman. Son 20 pruebas nuevas de este incremento;
la general también incluye las 21 de composición HTTP de la entrega anterior.
Las omisiones son conexiones externas no habilitadas, no aprobaciones. No se
instalaron dependencias ni se ocultaron advertencias o resultados intermedios.

Respaldo verificado, manifiestos, comandos, logs y JUnit:
`C:\SPSBackups\rf15-rf26-20261104T030916Z`.
No se modificaron fuentes durante pytest; la general produjo un JSON propio de
evidencia BD2-04. Los laboratorios fueron eliminados y diff --check terminó en 0.

## Límites y continuidad

La consulta y edición docente solicitadas están implementadas. El RF-15 académico
más amplio todavía no puede mostrar una nota oficial mientras 8C carezca de las
políticas aprobadas de cálculo/consolidación. No se declara cerrado todo el backend.
Paginación/rendimiento de grandes listados y entrega/notificación al estudiante
no se acreditan por estas pruebas. No se añaden permisos de delegación entre
docentes ni se suplen asociaciones históricas ausentes con UUID inventados.

Siguiente incremento recomendado, sujeto a revisión: conectar la lectura privada
estudiantil del feedback general para intentos cerrados, reutilizando la consulta
existente, manteniendo las notas y la ausencia oficial bloqueadas.

## Continuidad: recorrido de lectura en app.main (5 de noviembre de 2026)

RF-15 exige navegar casos realizados y consultar por estudiante sus respuestas,
retroalimentación por respuesta y valoración general docente. No es RF-16
(exportación/notas oficiales) ni autorización para inventar un login de personal.
La matriz ya lo clasifica IMPLEMENTADO para el ámbito existente; no se crea otro
servicio ni una ruta duplicada.

Incremento seleccionado: caso → participaciones → detalle histórico mediante los
tres GET existentes en `app.main.app`. La consulta SQL actual entra en `s.begin()`
y confirma al terminar; se acreditará y sustituirá esa frontera por lectura sin
autoflush ni commit, conservando la autorización y sus locks. Solo Identity cambia;
el escritor RF-26 y Participation no se refactorizan.

Criterios definidos antes de la corrección:

- JWT real y roles/identidades persistidos; autenticación del personal preparada
  solo en laboratorio, sin endpoint provisional ni cabecera de identidad.
- Misma versión asignada, incluso tras publicar otra y archivar la anterior.
- Datos propios, referencias exactas, respuestas registradas y valoración
  existente; sin notas oficiales, rúbricas ni respuestas futuras. Explicaciones
  conservan su regla actual: solo para intentos cerrados.
- Repetición y concurrencia de los GET sin DML, flush ni commit y sin cambios en
  participación, intento, respuestas o valoración. Los locks de ámbito se conservan;
  no se afirma compatibilidad con una transacción PostgreSQL READ ONLY o réplica.
- Rechazo de ajenos/no docentes y vínculos ausentes/ambiguos; fallo SQL saneado.
- Reutilizar el contrato HTTP, Proxy, servicios y consultas; mantener RF-16 y el
  inicio/calificaciones oficiales cerrados.

El inicio de la fixture utiliza políticas explícitas LAB y la nueva edición se
prepara administrativamente con el helper existente; ninguna de esas preparaciones
acredita ingreso productivo ni una API nueva de versionamiento.

### Corrección y aceptación actual

Se confirmó el alcance aprobado en la matriz: RF-15 es consulta por caso/estudiante
de respuestas y retroalimentación, no cálculo de notas oficiales ni exportación.
Las rutas y servicios ya existían; no se creó otra implementación.

Cambio productivo único: `identity/infrastructure/followup.py::_operar` sustituye
`s.begin()` por `s.no_autoflush`. La Session se cierra y descarta su transacción
de lectura, liberando locks, sin commit. No se elimina la comprobación del Proxy
ni la revalidación dentro de la consulta. AmbitoFeedbackIndividual y la UoW del
escritor RF-26 permanecen intactos.

| Ejecución actual | Resultado |
|---|---|
| Reproducción `pruebas_seguridad_20261105T202708Z` | 2 fallidas, 0 aprobadas/omitidas/errores, 1 advertencia; 13.83 s. Se observaron seis COMMIT por recorrido (cuatro GET), tanto activo como cerrado; no DML. |
| Aceptación `pruebas_casos_20261105T202801Z` | 11 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 33.35 s. |
| Relacionada `pruebas_focal_20261105T202910Z` | 129 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 139.05 s. |

No se suman suites solapadas ni se ocultan los fallos iniciales. La advertencia
es Starlette/TestClient/httpx. No se repitió la general: no cambian puertos,
DTOs, firmas públicas, router, autenticación ni contratos HTTP compartidos.
2023/38 sigue siendo la general histórica, no el resultado de este incremento.

Los once casos de `tests/integration/test_main_teacher_followup.py` acreditan:

- Recorrido caso/listado/detalle repetido, activo y cerrado, con filas reales
  PostgreSQL17 y aplicación principal. Cero DML, flush y commits; snapshots intactos.
- Edición histórica exacta después de crear otra y archivar la asignada; explicación
  y valoración confirmadas, sin notas ni rúbricas. En activo no se devuelven explicaciones.
- Rechazo de anonimato, token inválido, estudiante, administrador sin rol docente,
  docente ajeno con vínculos válidos, vínculo ausente y vínculo ambiguo. Cabecera
  `X-Docente-Id` y parámetro `id_docente` no sustituyen el JWT.
- Dos lecturas concurrentes con igual respuesta y sin escrituras; fallo SQL
  controlado devuelve 503 saneado, sin marcador privado ni modificación de datos.

La falla SQL se inyecta en la ejecución de una consulta real; no se presenta como
caída física del servidor. Los demás controles no se sustituyen por mocks.
La relacionada reutiliza pruebas de Proxy/HTTP Identity, seguimiento/feedback,
consulta estudiantil de feedback, progreso y bloqueo seguro de notas RF-27.

### Disponibilidad y evidencia

Los tres GET están efectivamente registrados en main; la aceptación usa sus
fábricas reales y JWT real. Solo el reloj de preparación estudiantil se sustituye
en laboratorio. El token del docente se emite en la fixture con configuración
sintética explícita: **no acredita login del personal ni integración productiva
de extremo a extremo**. No se añadió una nueva ruta ni un emisor provisional.
Las consultas históricas autorizadas siguen disponibles para un JWT legítimo,
configuración válida y vínculos persistentes; usuarios sin esa autorización
siguen rechazados. RF-16 devuelve 503 con su integración pendiente, y notas,
repetición/inicio productivo y RF-22 conservan sus barreras.

Paquete `evidencias/rf15_lectura_20261105T202511Z/`: inventario inicial, comandos,
consolas, JUnit con detalles LAB activos/cerrados, aislamiento Docker y cierre.
Para repetir únicamente aceptación y relacionada en laboratorios nuevos:

```powershell
& C:\Python313\python.exe -B .\evidencias\rf15_lectura_20261105T202511Z\ejecutar_validacion.py casos
& C:\Python313\python.exe -B .\evidencias\rf15_lectura_20261105T202511Z\ejecutar_validacion.py focal
```

El ejecutor desactiva `.env` y URLs externas solo en el proceso de pruebas;
reutiliza el creador de PG17 desechable. No conecta bases del equipo ni cambia
credenciales permanentes. No se crea infraestructura, ORM ni migración.

RF-15 conserva su clasificación IMPLEMENTADO para el alcance acreditado; se
amplía la evidencia y pureza transaccional, no se incrementa el conteo de RF.
El siguiente requisito de mayor impacto es RF-03, después de acordar el contrato
de autenticación de personal y la granularidad administrativa. No se implementa
ese siguiente requisito ni un login, multirrol o permiso individual aquí.
