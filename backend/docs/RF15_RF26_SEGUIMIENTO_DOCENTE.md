# RF-15 y RF-26 — Seguimiento y valoración docente

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
