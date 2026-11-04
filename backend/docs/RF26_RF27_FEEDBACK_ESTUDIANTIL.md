# RF-26/RF-27 — consulta privada y aviso interno de feedback

Fecha: 4 de noviembre de 2026, America/Bogota. Candidato sin commit en
`C:\SPS\consolidacion`, rama `codex/consolidacion-backend`, HEAD
`3e09defb608b3162b728f8b73b50dc772dd43693`.

## Operaciones conectadas

| Operación | Contrato y alcance |
|---|---|
| `GET /api/v1/identity/seguimiento/participaciones/{id_participacion}/feedback` | Nueva composición HTTP de `consultar_feedback_individual`. Solo ESTUDIANTE vigente, matrícula propia y convocatoria del JWT validada mediante resolver SQL. Devuelve `id_participacion`, `id_docente`, `texto`, `fecha`; `Cache-Control: no-store`. |
| `POST` sobre la misma ruta | Autoría docente existente RF-15/26; mantiene una valoración editable. Ahora registra también el aviso interno ante un cambio efectivo de texto. No cambia su respuesta 201. |
| `GET /scheduling/notificaciones?destinatario_id=<UUID académico>` | Bandeja existente. El servidor resuelve el UUID del estudiante autenticado y rechaza un filtro de destinatario distinto. No se creó otra bandeja. |

Identity y Scheduling ya están registrados en `app.main`. Estas operaciones
quedan compuestas en la aplicación principal sin modificar `main.py`. Su
ejecución está demostrada con TestClient, JWT real y PostgreSQL 17 desechable;
no se certificó despliegue ni configuración de una base permanente.
Participation sigue sin registro global; no se habilitaron sus inicios ni notas.

## Visibilidad y relaciones

Se conserva el contrato de lectura existente: debe existir al menos un intento
y todos deben estar cerrados (`FINALIZADO` o `VENCIDO`). No se transforma
vencimiento en ausencia ni se crean intentos. Una convocatoria retirada, un
contexto JWT ausente/ajeno o una participación ajena impiden la lectura.
No se exige que la sesión ya haya finalizado ni se añade una política de ingreso
para leer un comentario histórico. Se comprueba la correspondencia persistida
matrícula–asignación–convocatoria–sesión–versión exacta del caso.

Se reutiliza el lock de participación, compartido con inicio y escritura docente;
se revalida la cuenta/rol y se bloquean los vínculos de identidad consultados.
El SELECT no actualiza feedback, intentos ni avisos. Un fallo SQL se traduce a
503 sin detalles internos. Se conservó el 503 preexistente cuando todavía no hay
valoración; distinguir esa ausencia con otro estado HTTP queda como mejora del
contrato, no como un dato o comentario inventado.

## Aviso RF-27 y límite de deduplicación

El creador genérico de Scheduling admite ahora el tipo aditivo
`RETROALIMENTACION`, sobre el mismo `VARCHAR` y la misma tabla. No se reutiliza
`notificar_calificacion`: exige UUID de participación y anuncia una nota, lo que
no corresponde a este flujo. No se convierte el INTEGER de participación en UUID.

El repositorio existente toma el UUID del estudiante de la convocatoria,
verificado mediante matrícula y resolver académico. `crear_notificacion`
recomprueba destinatario/convocatoria. Feedback y aviso `INTERNA/PENDIENTE`
se guardan con la misma Session y el mismo commit. Si falla cualquiera, ambos
se revierten; un reintento puede confirmar ambos. No hay publicación externa
antes del commit ni un segundo sistema de eventos/notificaciones.

Solo una primera valoración o un cambio efectivo de texto genera aviso. El
lock de participación serializa escrituras concurrentes: dos escrituras del
mismo texto y su repetición consecutiva producen un aviso, no dos. Un cambio
posterior produce otro aviso. Esto no es un protocolo universal de exactamente
una vez: no se añadió clave de idempotencia de solicitud ni revisión histórica
del texto. No se notifican retrospectivamente escrituras antiguas.

El mensaje anuncia únicamente el registro/actualización y remite a consultar
su disponibilidad: no contiene el comentario, respuestas, justificaciones,
códigos, nota ni una promesa de acceso inmediato. Puede aparecer mientras un
intento está activo; recibirlo no habilita la lectura del comentario.
Se acredita aviso interno persistente y consultable; no correo, despacho externo,
acuse de lectura, publicación oficial ni notificación de calificaciones.

## Archivos del incremento

- `identity/api/dependencies.py`: composición de la lectura existente con Identity real.
- `identity/api/router.py`: GET privado, sin reglas de dominio en el router.
- `participation/infrastructure/individual_feedback.py`: lectura reforzada y aviso atómico en el escritor existente.
- `scheduling/application/crear_notificacion.py`: tipo técnico `RETROALIMENTACION`.
- `tests/integration/test_student_general_feedback_http.py`: 20 escenarios HTTP nuevos.
- Este informe. La regresión generó además un JSON de evidencia del laboratorio BD2-04, conservado sin editar.

## Validación real

Evidencias, JUnit XML, logs, comandos y SHA-256 están en
`C:\SPSBackups\rf26-rf27-20261104T183124Z`.

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Focal inicial, 18:34 UTC | 11 | 0 | 1 | 0 | 1 |
| Focal de consulta, 18:35 UTC | 229 | 29 | 0 | 0 | 1 |
| Focal con avisos, 18:39 UTC | 9 | 0 | 1 | 0 | 1 |
| Focal final, 18:40 UTC | 232 | 29 | 0 | 0 | 1 |
| General final, 18:43 UTC | 1895 | 38 | 0 | 0 | 53 |

Las suites se solapan: no sumar sus resultados. La primera prueba fallida
intentaba borrar un vínculo histórico que BD2-07 impide alterar. Se corrigió la
preparación para probar cambios permitidos de convocatoria, actividad y rol,
sin desactivar guards ni añadir corrupción ficticia. El segundo fallo fue una
aserción de estado activo colocada por error después del cierre en otro escenario;
se devolvió a su prueba de intento activo. Se preservaron ambos registros.

Los 20 escenarios nuevos usan PostgreSQL real y relaciones persistentes. Reutilizan
el login estudiantil y las APIs de Cases/Scheduling/Participation del laboratorio
8B; sus políticas de inicio siguen siendo explícitamente de laboratorio. Los JWT
docentes usan el emisor real con cuentas/clave sintéticas. No se sustituyen las
relaciones críticas ni la autorización por mocks. Solo las pruebas excepcionales
inyectan un error de conexión o un fallo después del flush real para acreditar
denegación y rollback. Los tests unitarios existentes de notificaciones con Mock
no se presentan como prueba de persistencia.

Las 38 omisiones corresponden a configuraciones externas no habilitadas:
29 `SPS_IDENTITY_TEST_URL`, 3 pruebas antiguas `SPS_TEST_POSTGRESQL` y
6 `SPS_PERSISTENCE_LAB_URL`. No se consideran aprobadas. Las advertencias incluyen
Starlette y uso de `record_property` con JUnit xunit2.

## Preservación y continuidad

Antes de editar se copiaron y verificaron 354 archivos con tamaño/SHA-256 y un
bundle Git verificado. De esos originales, solo cambiaron los cuatro archivos
productivos enumerados; los otros 350 se preservaron. Las referencias de
`martin`, `feature/integracion-backend`, HEAD y el stash original no cambiaron.
No hubo commit, merge, push ni consumo del stash.

No se alteraron ORM, DBML, migraciones, Evaluation ni políticas 8B. Se mantienen
30 tablas de metadata y una cabeza Alembic `20261102_immutable_answers`.
No se conectaron bases permanentes: el ejecutor elimina URLs externas del entorno
del proceso, activa contenedores nuevos etiquetados con almacenamiento tmpfs y
puertos locales efímeros; el fixture comprueba su identidad y los elimina por ID.
Los archivos preexistentes no cambiaron durante pytest. No quedaron contenedores
de laboratorio y `git diff --check` pasó.

RF-26 queda acreditado para comentario individual existente con las condiciones
descritas. RF-27 queda acreditado para ese aviso interno, no para avisar notas
oficiales. Permanecen cerradas la consulta sin intentos, las convocatorias no
vigentes y la publicación académica pendiente de Evaluation. No hay historial
de versiones del comentario ni confirmación de lectura de avisos.

Siguiente incremento recomendado, sujeto a revisión: integrar la consulta y la
bandeja existentes con la pantalla estudiantil y sus pruebas de aceptación,
sin ampliar visibilidad ni publicar notas. No se inició otro incremento.
