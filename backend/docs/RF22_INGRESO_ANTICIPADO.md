> Actualización vigente: sala de espera y admisión aprobadas por el equipo.
> Se registran solicitudes propias antes de habilitar y se congela el conjunto
> elegible en la transacción docente SIN_INICIAR → EN_CURSO. EN_CURSO sin concesión
> individual rechaza con 403. No hay tolerancia anticipada ni tardía ni presencia
> online inferida. Las afirmaciones anteriores sobre falta de señal de admisión
> quedan como historia; se conserva el cierre del inicio por consentimiento oficial.
> Contrato, migración y evidencia: `SALA_ESPERA_ADMISION_DISENO.md` (backend/docs).

---

> Definición definitiva posterior: no existe tolerancia anticipada NI tardía.
> EN_CURSO es necesario, pero no demuestra oportunidad de la solicitud. Al faltar
> señal de admisión/contrato objetivo, la composición productiva sigue en 503.
> No se implementa igualdad exacta con un timestamp ni una ventana implícita.
> La señal de admisión propuesta y el avance interno de consentimiento/inicio se
> detallan en `CONSENTIMIENTO_E_INICIO_INTERNO.md`. La general actual es 2126/38,
> sin fallos/errores; los 2102/38 siguientes corresponden al incremento anterior.
> El cuerpo siguiente describe aquella entrega de RF-22. El incremento actual
> sí adapta los contratos internos de Participation; sus archivos y límites están
> en el informe de consentimiento/inicio citado, sin habilitar rutas productivas.

# RF-22 vigente: habilitación efectiva, sin ingreso anticipado

Corrección del responsable funcional comunicada el 5 de noviembre de 2026
(America/Bogota). Rama `feature/backend-continuidad`, base `33981c8` más cambios
locales. **Los diez minutos anticipados quedan DESCARTADOS por corrección del
requisito, no por un defecto de programación de aquella interpretación.**
Se conserva el nombre de este archivo y el contenido anterior como trazabilidad;
las reglas del antecedente al final NO son el contrato vigente.

## Contrato vigente y habilitación comprobada

Ruta efectiva en main: **POST `/scheduling/validar-ingreso`**; cuerpo sin cambios:
convocatoria_id, estudiante_id y codigo_acceso. No hay alias `/api/v1/scheduling`.

Habilitar es ejecutar la operación docente protegida POST
`/scheduling/sesiones/{sesion_id}/estado` con acción `iniciar`.
State (`EstadoSinIniciar.iniciar`) produce EN_CURSO. `cambiar_estado_sesion`
bloquea/refresca la fila y registra CAMBIO_ESTADO; `cambiar_estado_y_publicar`
confirma estado, auditoría y avisos SQL atómicamente. La fecha_inicio programada
no produce esta transición. SesionProgramadaModel no tiene un inicio_real dedicado;
la auditoría registra su creado_en. No se usa esa fecha para inventar un umbral.

| Condición | Antes | Ahora, composición productiva |
|---|---|---|
| SIN_INICIAR, inicio - 10 minutos | Permitido con los demás controles | 403 |
| SIN_INICIAR, inicio - 1 segundo | Permitido con los demás controles | 403 |
| SIN_INICIAR, hora programada alcanzada o posterior | 403 | 403; la hora no habilita |
| EN_CURSO habilitada, falta política temporal | 503 | 503; no se inventa tolerancia |
| FINALIZADO (nombre real del estado) | 403 | 403 |
| Retirada, identidad ajena o código incorrecto | Rechazo | Rechazo conservado |
| EN_CURSO y ventana explícita LAB, matrícula/referencias válidas | Solo laboratorio | 200 solo en prueba, NO política productiva |

EN_CURSO es una condición necesaria y verificable; no es autorización suficiente.
El proveedor `PoliticaIngresoNoConfigurada` continúa cerrado. La nueva decisión no
define una ventana completa de ingreso, límite posterior ni sus fronteras. Por
eso RF-22 permanece PARCIAL y no hay un positivo productivo aprobado. No se supone
que la programación equivale a habilitación ni se activa ingreso tardío.

Se mantienen JWT real, convocatoria ACTIVA/titular, código, matrícula activa,
asignación y versión UUID exacta. El cliente no puede sustituir la versión ni
aportar tiempo/tolerancias. Timestamps conscientes de zona y reloj del servidor;
sin cambios en PARTICIPATION_TIMESTAMP_ZONE. La validación no crea P/I, no concede
permiso de inicio, no hace DML/flush/commit y no modifica auditoría al repetirse.

## Implementación y pruebas actuales

Cambios productivos mínimos en Scheduling: se retiran constante, clase y factory
de anticipación; se elimina el parámetro politica_anticipada y su rama de
SIN_INICIAR. El servicio exige EN_CURSO antes de consultar cualquier ventana.
Se conserva el adaptador SQL de matrícula y los headers no-store, sin cambios.
No se modifican Participation, Evaluation, Identity productivo, Worker, ORM,
migraciones ni DBML. El router y su registro en main no cambian.

`tests/integration/test_main_early_ingress.py` se conserva por trazabilidad,
actualizado al requisito vigente. La sesión que se evalúa se crea NUEVA desde
HTTP con JWT docente real y queda SIN_INICIAR; no se reescribe la auditoría de
una sesión anterior. La asignación y credencial inicial son preparación explícita
LAB. Habilitar/finalizar usa HTTP real y se comprueba estado/auditoría desde otra
Session PostgreSQL. JWT estudiantil sale del login correo/código real en main.

30 aceptaciones HTTP PG17: rechazos a -601, -600, -300, -1, 0 y +1 segundos sin
habilitación; habilitación efectiva; finalización; política faltante; retirada,
ajeno, matrícula inválida/ambigua, código, referencia de versión manipulada,
zonas, fallos SQL y repetición/concurrencia sin escrituras. Los positivos de las
otras condiciones inyectan EXPLÍCITAMENTE IngresoLaboratorio; se prueba aparte el
503 por defecto, también concurrente. No se presentan esos 200 como autorización
académica productiva. No se sustituye autenticación, autorización ni repositorios.

Los cuatro casos unitarios del proveedor anticipado fueron retirados porque ese
puerto ya no existe; se conservan en el respaldo y en los logs anteriores. Los
rechazos de estado previos permanecen, y la aceptación HTTP sustituye la semántica
anticipada con el rechazo exigido. No hay skip/xfail nuevos ni borrado de archivos.
Se restaura en la prueba compartida de login la expectativa «La sesión no está en
curso». El total de pruebas puede coincidir con el anterior; no son los mismos
contratos ni se suman ejecuciones solapadas.

| Ejecución actual | Aprobadas | Omitidas | Fallidas/errores | Advertencias |
|---|---:|---:|---:|---:|
| Reproducción ANTES de corregir: permitía -10 y -5 min | 2 | 0 | 0 | 1 |
| Aceptación corregida main/PG17 | 30 | 0 | 0 | 1 |
| Relacionada | 558 | 0 | 0 | 1 |
| General | 2102 | 38 | 0 | 1 |

Focalizada `pruebas_casos_20261106T002750Z`: 64.60 s. Relacionada
`pruebas_focal_20261106T002906Z`: 184.53 s. General
`pruebas_total_20261106T003253Z`: 926.08 s, terminó el 5 de noviembre a las
19:48:32 America/Bogota (2026-11-06T00:48:32Z). Advertencia conocida Starlette/httpx.
Las 38 omisiones son 29 antiguas Identity y 9 Participation condicionadas a
URL/configuración; no se dan por aprobadas. Todas las fuentes estuvieron estables
durante pytest; solo se generó el artefacto experimental BD2-04 esperado.

Evidencia, JUnit, consola, comandos, huellas y respaldo previo:
`evidencias/rf22_habilitacion_20261106T002442Z/`.
Ejecutor aislado: `C:\Python313\python.exe -B evidencias/rf22_habilitacion_20261106T002442Z/ejecutar_validacion.py casos`
(o `focal` / `total`). La reproducción diagnostico corresponde al código anterior
respaldado, no a los nodeids corregidos. No carga .env ni usa URLs permanentes;
PostgreSQL 17 se crea con tmpfs/puerto local efímero y se elimina por su propio id.

## Pendientes y preservación

Sin política temporal completa no se habilita ingreso productivo, aun con EN_CURSO.
Consentimiento, provisión, repetición e inicio desde convocatoria conservan sus
bloqueos; no se toca su implementación ni se publican notas. No se inicia otra fase.

El manifiesto histórico de 34 archivos y el informe de consentimiento se preservan
sin cambios, además de un respaldo verificado de 36 archivos antes de implementar.
Sus huellas anteriores NO deben usarse para commitear automáticamente el contenido
corregido: `delta_autorizado.json` identifica los cambios nuevos y sus SHA-256.
Git se conserva en la misma rama/HEAD, sin staging ni commits; refs, stash y .env
se verifican al cierre. No hay migraciones nuevas ni conexiones a bases permanentes.

---

## Antecedente DESCARTADO: decisión anterior, resultados y propuesta histórica

Todo el contenido siguiente documenta la interpretación previa. No habilita
anticipación ni sustituye el contrato vigente explicado arriba.

# RF-22: validación anticipada de ingreso, sin inicio de simulación

5 de noviembre de 2026, America/Bogota. Base `33981c8` más modificaciones
locales en `feature/backend-continuidad`. No es un nuevo commit ni despliegue.

## Contrato y aceptación

Decisión funcional comunicada por el equipo en este incremento: se permite
validar ingreso desde diez minutos antes del inicio programado, inclusive.
No es aprobación institucional de políticas complementarias ni autoriza iniciar
una simulación. No se reutiliza la propuesta histórica de quince minutos.

Ruta efectiva existente en main: **POST `/scheduling/validar-ingreso`**.
No existe el alias `/api/v1/scheduling/validar-ingreso` y no se añade uno.
Se conserva el cuerpo `convocatoria_id`, `estudiante_id`, `codigo_acceso`, con
campos adicionales prohibidos. El estudiante del cuerpo debe coincidir con la
identidad resuelta del JWT; no constituye una credencial por sí mismo.

Criterios de aceptación del incremento:

- Sesión SIN_INICIAR: ventana `[inicio - 10 minutos, inicio)`; el extremo inferior
  es inclusivo. En inicio exacto esta autorización anticipada termina; el estado
  SIN_INICIAR continúa sin autorizar el ingreso desde ese instante.
- Sesión EN_CURSO: se conserva el proveedor existente de política posterior,
  todavía no configurado (503). No se inventa ingreso tardío ni su frontera.
- Sesión FINALIZADO: 403, sin reapertura ni modificación del estado.
- JWT real, cuenta activa, rol ESTUDIANTE, resolver académico inequívoco, contexto
  de convocatoria y titularidad, convocatoria ACTIVA, código válido y matrícula
  activa en una asignación de la misma sesión y versión exacta.
- Ninguna creación de participación o intento; sin DML, flush o commit.
- Fechas y reloj conscientes de zona, normalizados a UTC. No se adopta zona local
  ni se interpreta una fecha naive. La política no recibe horas del cliente.

| Caso | Respuesta de esta composición |
|---|---|
| Inicio - 10 minutos - 1 segundo | 403 |
| Inicio - 10 minutos exactos / inicio - 5 minutos, SIN_INICIAR | 200, SesionResponse existente |
| Inicio exacto o posterior, SIN_INICIAR | 403 |
| Inicio exacto o posterior, EN_CURSO sin política suficiente | 503 |
| FINALIZADO, convocatoria retirada, identidad ajena, matrícula inactiva | 403 |
| Sin JWT o token inválido | 401 |
| Matrícula aplicable ambigua o asignación inexistente | 503, sin elegir ni crear asociación |
| Fecha/reloj sin zona, proveedor incoherente o fallo SQL | 503 |
| Parámetros de tiempo/tolerancia/zona enviados por HTTP | 422 |

La respuesta positiva no es reserva, pase persistido ni permiso reutilizable.
Puede invalidarse por retiro, cierre o cambios posteriores; iniciar requiere
su propia autorización transaccional. Solicitudes repetidas y concurrentes
solo leen. La composición de inicio de laboratorio sigue rechazando una sesión
SIN_INICIAR, incluso después de una validación anticipada positiva.

## Reutilización y cambios exactos

- `scheduling/domain/ingress_policy.py`: PoliticaIngresoAnticipadoDiezMinutos usa
  el puerto PoliticaIngreso y VentanaIngreso existentes; constante única de diez
  minutos. No añade columnas, tolerancia configurable ni fórmula posterior.
- `scheduling/application/validar_ingreso.py`: parámetro opcional
  `politica_anticipada=None`. Solo el nuevo proveedor explícito permite evaluar
  SIN_INICIAR antes del inicio. Los consumidores existentes que no lo pasan
  conservan su semántica EN_CURSO. Las fuentes no pueden ampliar los límites.
- `scheduling/infrastructure/ingress_access.py`: comprueba matrícula/asignación
  mediante las claves reales INTEGER y la versión UUID de sesión. No convierte
  identificadores ni infiere matrícula desde el espacio. Ausencia o ambigüedad
  conserva el cierre. No utiliza Participation como padrón.
- `scheduling/api/router.py`: compone la anticipación y matrícula sobre la misma
  Session de lectura, con no_autoflush. Conserva el proveedor posterior cerrado.
  Corrige la pérdida de Cache-Control: no-store en errores de ingreso.
- No se modifican main, ORM, migraciones, Worker, Identity productivo,
  Participation productivo, Evaluation ni DBML.

Pruebas: `tests/integration/test_main_early_ingress.py` (26 casos HTTP main, JWT
real y PostgreSQL 17 desechable); cuatro casos nuevos de proveedor incoherente en
`tests/unit/scheduling/test_ingress_policy.py`. La fixture temporal de
`test_ingress_temporal_sql.py` prepara grupo, matrícula y asignación reales, sin
añadirlos a la fixture compartida de login. Las fixtures con dobles de router se identifican como tales y no acreditan
integridad PostgreSQL. SQLite restaura solamente el UTC escrito por su fixture;
producción sigue rechazando fechas naive.

Se conserva la configuración de zonas de Participation sin usarla para interpretar
las fechas conscientes de zona de Scheduling. No se añade un valor predeterminado
ni se cambia PARTICIPATION_TIMESTAMP_ZONE. Un offset equivalente produce el mismo
resultado; un reloj sin zona falla cerrado y una zona aportada por HTTP se rechaza.

## Resultados y alcance de evidencia

Evidencia en `evidencias/rf22_anticipado_20261105T231718Z/`: comandos, huellas,
JUnit XML, consola, resultado y manifiesto previo. El ejecutor desactiva la lectura
de `.env`, elimina URLs externas y habilita solamente contenedores propios
postgres:17 con tmpfs, puerto local efímero y eliminación por identificador.

| Ejecución | Aprobadas | Fallidas | Omitidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Comprobación adicional del login previo, sin cambios | 19 | 0 | 0 | 0 | 1 |
| Primera aceptación nueva | 23 | 4 | 0 | 0 | 1 |
| Primera relacionada | 375 | 19 | 0 | 0 | 1 |
| Segunda relacionada | 393 | 1 | 0 | 0 | 1 |
| Primera relacionada verde `pruebas_focal_20261105T232733Z` | 398 | 0 | 0 | 0 | 1 |
| Primera general `pruebas_total_20261105T233046Z` | 2063 | 12 | 38 | 27 | 1 |
| Relacionada ampliada FINAL `pruebas_focal_20261105T234704Z` | 558 | 0 | 0 | 0 | 1 |
| General FINAL `pruebas_total_20261105T235005Z` | 2102 | 0 | 38 | 0 | 1 |

No se suman ejecuciones solapadas. Se conservan los fallos: tres errores de
cabecera corregidos; un dato de prueba con estado imposible se retiró de la matriz
HTTP porque el CHECK PostgreSQL ya lo rechaza (el rechazo de estado desconocido
continúa probado en unidad). La regresión detectó fixtures sin matrícula y mocks
sin contexto no_autoflush, que se completaron explícitamente. Una expectativa
histórica de SIN_INICIAR cambió al rechazo fuera de la ventana anticipada, sin
cambiar su 403. El último fallo era un doble de matrícula reutilizado como
notificación; se separó. No se introdujeron skip, xfail ni excepciones permisivas.
Advertencia conocida: Starlette/TestClient-httpx.

La primera general reprodujo un efecto de la preparación: la matrícula/asignación
se había añadido a la fixture compartida de login, que también usan pruebas de
sesiones aún no asignadas y cambios de versión. Sus FK impidieron esas operaciones.
Se movió esa preparación a `ingreso_sql`, exclusivamente temporal, sin cambiar las
12 pruebas ni las 27 preparaciones históricas afectadas, sin eliminar FK y sin
cambiar producción. La regresión ampliada incluye esas dos suites (8A y contexto
académico) y las conserva verdes. La general final tardó 938.51 s; las 558
relacionadas, 149.94 s. Sus fuentes permanecieron estables durante pytest.

Las 26 aceptaciones nuevas de main pasaron en la regresión final, y las cuatro
pruebas unitarias nuevas acreditan el rechazo de proveedores que amplían la
ventana. Las 38 omisiones son 29 pruebas antiguas de Identity y 9 de Participation
condicionadas a URL/configuración externa; no acreditan ejecución PostgreSQL.
La aceptación nueva usa PostgreSQL 17 propio y no omitió casos.

Fecha local de cierre de la general: 5 de noviembre de 2026, 19:05:56
(America/Bogota); el metadato UTC registra 2026-11-06T00:05:56Z.
Se conserva el artefacto BD2-04 generado por cada general, fuera del checkpoint.

Comando reproducible del ejecutor aislado:

```powershell
C:\Python313\python.exe -B evidencias/rf22_anticipado_20261105T231718Z/ejecutar_validacion.py focal
# 'casos': solo la aceptación HTTP nueva; 'total': suite general aislada.
```

## Siguiente dependencia: consentimiento e inicio desde convocatoria

Se registra la decisión comunicada: consentimiento antes de crear participación
y no revocable mientras se ejecuta la simulación. No se implementa ese siguiente
incremento aquí. Detalles todavía indispensables:

1. Fuente autorizada del texto y versión vigente, aplicabilidad y prueba de cuál
   versión corresponde al caso/sesión; version_texto persistido no prueba vigencia.
2. Qué hacer con aceptaciones anteriores cuando cambia esa versión; no se elige
   automáticamente la más reciente ni se inventa una fecha de expiración.
3. Inicio/fin del intervalo de no revocación y comportamiento fuera de ejecución,
   incluidas participaciones con intentos cerrados; no existe flujo productivo de
   revocación que pueda afirmarse protegido solo por este cambio.
4. Comprobar el consentimiento antes de la creación de P y el inicio en la misma
   UoW. La provisión independiente de laboratorio no acredita todavía ese contrato;
   permanece fuera de main, junto al inicio desde convocatoria.
5. Política de ingreso desde el inicio programado, provisión/estado inicial y
   repetición excepcional siguen pendientes. Diez minutos ANTES no define RF-22
   tardío ni cupos. Debe revalidarse todo en el instante de escritura.

RF-22 avanza de BLOQUEADO a PARCIAL: la anticipación está implementada y acreditada,
pero no se declara terminada la política de ingreso completa ni el inicio productivo.
El siguiente incremento natural es precisar la fuente versionada de consentimiento
y la política desde el inicio; después reutilizar la composición transaccional 8B.

## Preservación y checkpoint propuesto

Se conserva el manifiesto previo (22 archivos) en la carpeta de evidencia.
La selección actualizada, con rutas, tamaños, clasificación por incremento y
SHA-256, está en `backend/docs/CHECKPOINT_LOCAL_PROPUESTO_20261105.json`.
No es staging ni autorización para ejecutar commits. Se excluyen `.env`, evidencias,
ZIP, respaldos y documentos universitarios ajenos; el manifiesto no se autorreferencia.

Comprobaciones finales: rama `feature/backend-continuidad`, HEAD `33981c8`, índice
vacío, stash y referencias sin cambios; archivos anteriores preservados por huella
salvo las modificaciones autorizadas de este incremento. `git diff --check` correcto.
Alembic conserva la única cabeza `20261104_teacher_spaces`, metadata conserva 31
tablas físicas; no se añadieron tablas, columnas, revisiones ni cambios al ER28.
Contenedores de laboratorio eliminados, sin procesos pytest pendientes. No se
aplicó ninguna migración a una base persistente ni se modificó `.env`.
Estado detallado y verificaciones: `CIERRE.json` y `status_final.txt` en la carpeta
de evidencia. Los cambios permanecen locales; no hubo commit, push, merge ni PR.
