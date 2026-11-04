# 8B — Autorización real de respuestas y composición HTTP

Actualización 2026-11-03: se implementó el inicio transaccional sobre participación
existente mediante `crear_facade_inicio_8b`, probado con políticas explícitas de
laboratorio. Véase [inicio transaccional](FASE_8B_INICIO_TRANSACCIONAL.md).
Las afirmaciones posteriores sobre métodos de inicio cerrados corresponden a la
composición anterior `crear_facade_8b`, que conserva ese bloqueo deliberadamente;
no describen la nueva composición opt-in. No se habilitó el router principal.

2026-11-02 · `feature/integracion-backend`. Backend y 8B aún no completos.
El trabajo no modifica archivos del Plan de Pruebas PT-DCP-01.

## Funcionalidad operativa

El usuario confirmó expresamente para un intento ya iniciado válidamente:
**EN_CURSO y fecha_inicio ≤ hora del servidor < fecha_fin, además de tiempo
individual disponible; fin exclusivo, sin prórroga. Esto no autoriza inicio/RF-22.**

`scheduling/application/attempt_operations.py::autorizar_respuesta_sesion`
implementa esa regla sobre fechas conscientes normalizadas a UTC. No acepta una
tolerancia ni fecha del cliente. Datos temporales desconocidos/incoherentes
cierran la operación. `consultar_operacion_sesion` conserva su contrato factual
y bloquea sesión/convocatoria en la Session del escritor.

`participation/infrastructure/composition.py` incorpora
`AutorizacionRespuestaScheduling` como proveedor real predeterminado de
`crear_facade_8b`. La política es pura y sin estado; no es un fake de laboratorio.
Un `None` explícito sigue rechazándose como dependencia ausente, conservando
los contratos de pruebas negativas anteriores.

La Facade reutiliza la UoW y repos existentes: acredita cuenta/rol, identidad UUID
persistente, matrícula activa, contexto JWT, convocatoria ACTIVA, asignación,
sesión, versión exacta, estado del intento y duración histórica. Cases determina
la escena/pregunta actual mediante el grafo SQL. No cuenta todas las preguntas.
Solo registra una primera selección válida; la inmutabilidad sigue protegida en
dominio, aplicación, repositorio y PostgreSQL. Se permiten las siguientes
preguntas de la rama autorizada y el cierre idempotente que conserva respuestas.

## Frontera temporal corregida y contrato mínimo ampliado

Se reprodujo un fallo: autorizar justo antes del fin y registrar justo en el fin
podía eludir el horario. `SchedulingPort` añade **validar_instante_registro(instante)**:
`ServicioDecisiones` lo llama con el timestamp creado por el dominio, antes de
guardar. El adaptador vuelve a aplicar la misma política sobre las fechas/estado
ya bloqueados, sin otra Session ni otra fórmula. La autorización se vincula al
objeto de transacción y no puede reutilizarse después de commit/rollback.
El doble `SchedulingFalso` se adapta únicamente en las pruebas.

No se congela una hora antigua ni se amplía el plazo. La duración individual
no se reconstruye desde el tiempo máximo actual de Scheduling. El fin de sesión
impide responder, pero no cambia por iniciativa propia el vencimiento histórico
del intento ni genera una clasificación/nota académica nueva.

## Endpoints y contratos

`api/dependencies.py::crear_dependencia_facade_8b` prepara composición explícita
del servidor con Session, reloj y zona histórica de timestamps configurados.
Reutiliza Identity/JWT y vuelve a acreditar titularidad dentro de la escritura.
No consulta `.env` para elegir conexiones ni acepta estudiante/política/horas
en el cuerpo. No se instala en `main.py` ni sustituye la dependencia global 503.

| Operación sobre intento existente | Evidencia / estado |
|---|---|
| POST `/api/v1/attempts/{attempt_id}/decisions/{decision_id}` | Funciona con JWT, roles/repos SQL, horario real y grafo SQL en app aislada. 201; duplicado o PUT 409; ajeno 403; fuera de horario 403; recorrido no disponible 503. |
| GET `/api/v1/attempts/{attempt_id}/progress` | Lectura propia y progreso real, sin corrección/puntajes. Puede conservar vencimiento individual como ya estaba implementado. |
| POST `/api/v1/attempts/{attempt_id}/finish` | Cierre propio idempotente, conservando respuestas; no publica nota ni concede permiso para responder. |
| PUT decisión | Obsoleto, 409 por inmutabilidad cuando la identidad/estado permiten llegar a la regla. No se reabre edición. |
| POST `/participations/{participation_id}/attempts` | **Cerrado 503**: falta composición de autorización de inicio. La nueva dependencia rechaza la ruta sin alcance de intento existente. |
| GET resultados oficiales / ausencia | **Cerrados** en esta composición; la persistencia técnica de 8C no se publica como nota aprobada. |

La app de pruebas registra el router y configura la nueva dependencia; la app
principal permanece sin router Participation. Para habilitarla se requiere
configurar y revisar ese despliegue explícitamente, migraciones instaladas en su
entorno y zona histórica acreditada. Ninguna prueba demuestra un endpoint público
productivo ya desplegado.

## Pruebas y aislamiento

Nuevo `tests/integration/test_scheduling_participation.py`: **36 pruebas**.
No simula Identity, permisos Scheduling, Cases, repositorio ni UoW en los positivos.
Configura claves JWT/Session de laboratorio y reloj controlado. Los intentos se
provisionan como **datos sintéticos**: no representan un inicio productivo aprobado.
Se prueban estado, horario y fronteras, zonas equivalentes, cuenta/rol/matrícula/
convocatoria/contexto, intento ajeno, primera selección, segunda selección,
duración histórica, ramas reales y rutas no soportadas, fallo después de insertar
con rollback, carreras y autorización no reutilizable. HTTP usa JWT y resolver
SQL reales, con configuración de laboratorio, no usuarios autenticados falsos.

Prueba de frontera antes de la corrección: falló con DID NOT RAISE (reproducción
real). Después de corregirla, regresión focalizada de aplicación/API, Scheduling,
grafo y respuestas inmutables: **198 aprobadas, 1 advertencia conocida, 60,58 s**.
Incluía 35 pruebas nuevas; la prueba adicional de no reutilización se añade antes
de ejecutar la suite general final. No se borra ni debilita ninguna prueba previa.

Suite general final: **1665 aprobadas, 38 omitidas, 0 fallos, 0 errores,
1 advertencia conocida de Starlette; 350,54 s**. Se conservan las 1629 pruebas
anteriores y se agregan 36. Las omitidas requieren conexiones externas que no se
habilitaron: 29 Identity, tres Participation y seis de otro laboratorio por URL;
no se consideran aprobadas. La regresión incluye Evaluation, persistencia y guards.

Se retiran URLs
externas del subproceso y se habilita exclusivamente PostgreSQL Docker nuevo
con etiqueta propia/tmpfs; SQLite solo donde el historial ya utiliza aislamiento.
Se comprueba ausencia de pytest activo antes de cada lote de edición; no se
modifican archivos durante las ejecuciones focalizadas ni durante la general.

Verificación final: no hay pytest activo ni contenedores con etiqueta
`sps.identity.mapping.lab=true`; `git diff --check` termina con código 0, con el
aviso LF/CRLF preexistente de `caso_repository.py`. Rama sin cambios, 30 tablas ORM,
15 revisiones y cabeza única `20261102_immutable_answers`. No se crean ni modifican
modelos/migraciones/DBML, ni el motor/persistencia de Evaluation, ni `main.py`.
La suite genera automáticamente la evidencia BD2-04
`bd/laboratorio_bd2_04/evidencia_0c3c6d7e3b834afaa8b1df9d4c4e7d40.json`;
no se sobrescriben las anteriores. No se accede a bases permanentes.

La regla temporal es una autorización de aplicación dentro de la UoW, no un
nuevo trigger de horario ni un sustituto de Identity. Los guards SQL anteriores
siguen protegiendo inmutabilidad y referencias; no se atribuye autenticación JWT
a una conexión administrativa SQL directa.

## Pendientes concretos y siguiente prioridad

1. **Inicio real autorizado:** los métodos `IdentityIntentoSQLAlchemy.autorizar_inicio`,
   `SchedulingIntentoSQLAlchemy.obtener_condiciones/autorizar_nuevo_intento` siguen
   cerrados. No se declara una prueba positiva SQL de inicio: solo el inicio
   independiente ya cubierto con dobles y el rechazo real de esta composición.
   Falta cerrar RF-22/ventana de ingreso y la composición atómica de consentimiento,
   provisión de participación y cupos/repetición. No se deducen del permiso de responder.
2. **Cases:** múltiples preguntas, salidas contradictorias y ciclos/revisitas
   siguen pendientes de definición. Se conservan y rechazan los recorridos afectados.
3. **Evaluation:** la regresión no habilita mapeos/agregación/redondeo no aprobados
   ni decide preguntas futuras de una rama no elegida. No hay notas oficiales.
4. **Despliegue:** no se aplica una migración ni se utiliza una base permanente.
   La revisión actual sigue siendo `20261102_immutable_answers`; no se crea esquema.

Siguiente implementación prioritaria: autorización/provisión transaccional del
primer intento con contratos académicos de ingreso explícitos. Hasta resolverlos
no existe el recorrido productivo completo desde cero ni puede certificarse el
Backend como entregable completo. Sin commit/push/merge, cambio de rama ni fase 9.
