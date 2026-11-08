> Actualización posterior: se implementó la mecánica interna con fuente LAB y la
> validación de consentimiento/política antes del INSERT P. La fuente oficial y
> el inicio productivo siguen bloqueados. Ver `CONSENTIMIENTO_E_INICIO_INTERNO.md`.
> El diagnóstico y propuesta de commits siguientes son históricos; no se ejecutan
> ni se usan sus huellas antiguas para incluir automáticamente los cambios nuevos.

# Checkpoint pendiente y contrato de consentimiento

5 de noviembre de 2026, America/Bogota. Solo verificación y documentación.
Repositorio original; rama `feature/backend-continuidad`; HEAD completo
`33981c8da00996e4091d9dde9c0288bbac50c5ab`. No se ejecutan commits ni migraciones.

## 1. Verificación del manifiesto y contenido

Se verificaron **34/34 rutas únicas, tamaños y SHA-256**, sin solapamientos,
contra `CHECKPOINT_LOCAL_PROPUESTO_20261105.json`, que se conserva sin modificar.
Ningún archivo Python modificado/nuevo de `backend/app/` o `backend/tests/` queda
fuera de esas 34 rutas. Se revisaron contenido y diffs de los incrementos. El
escaneo no identificó claves privadas, URLs PostgreSQL con contraseña ni JWT
literales; no constituye certificación exhaustiva. Las credenciales explícitas
sintéticas de fixtures son exclusivamente de laboratorio, no cuentas productivas.

**Discrepancia de clasificación:** `backend/tests/identity/test_report_integrity.py`
aparece en login_personal, pero verifica ServicioReportes y pertenece a RF-16.
No hay alteración de contenido ni diferencia de huella; la propuesta siguiente
corrige la agrupación, conservando el manifiesto original como evidencia.

Fuera del manifiesto: el propio JSON (excluye autorreferencia), este nuevo informe
y `backend/scripts/run_unit_tests.py`. Los dos documentos se proponen en un commit
separado. El script es un artefacto QA previo, sin cambios, ajeno a estos incrementos,
y continúa excluido; no se presume parte del código aprobado. Se conservan todos
los otros no rastreados, respaldos, evidencias, ZIP, Word, cachés y `.env`, sin
proponerlos para staging. Inventario completo en la evidencia, no en los commits.

## 2. Propuesta exacta de commits locales, NO ejecutada

Orden: RF-19 es independiente; RF-15 aporta el helper de observación SQL usado
por pruebas posteriores de RF-16/login/RF-22. Login y RF-22 reutilizan Identity.
La matriz compartida se incorpora al último bloque funcional porque refleja
el conjunto completo, no solo un incremento. La evidencia general acredita el
árbol combinado; no se afirma haber ejecutado cada estado intermedio de commit.
Seis commits propuestos, 34 archivos funcionales sin duplicación más 2 documentos.

### Propuesta 1: RF19 (4 archivos)

`feat(scheduling): habilitar ejecucion operativa del worker RF-19`

- `backend/app/modules/scheduling/infrastructure/worker_runner.py`
- `backend/docs/RF19_WORKER_OPERATIVO.md`
- `backend/tests/integration/test_worker_process.py`
- `backend/tests/unit/scheduling/test_worker_runner.py`

### Propuesta 2: RF15 (3 archivos)

`fix(identity): asegurar seguimiento docente de solo lectura`

- `backend/app/modules/identity/infrastructure/followup.py`
- `backend/docs/RF15_RF26_SEGUIMIENTO_DOCENTE.md`
- `backend/tests/integration/test_main_teacher_followup.py`

### Propuesta 3: RF16 (4 archivos)

`fix(identity): validar integridad del exportador sin abrir reportes oficiales`

- `backend/app/modules/identity/application/services.py`
- `backend/docs/RF16_REPORTE_Y_BLOQUEOS.md`
- `backend/tests/identity/test_report_integrity.py`
- `backend/tests/integration/test_main_report_closed.py`

### Propuesta 4: login_personal (10 archivos)

`feat(identity): autenticar personal con correo y clave asignada`

- `backend/app/modules/identity/README.md`
- `backend/app/modules/identity/api/dependencies.py`
- `backend/app/modules/identity/api/router.py`
- `backend/app/modules/identity/api/schemas.py`
- `backend/app/modules/identity/application/authentication.py`
- `backend/app/modules/identity/application/ports.py`
- `backend/app/modules/identity/infrastructure/credentials.py`
- `backend/docs/AUTENTICACION_PERSONAL_CONTRATO_PENDIENTE.md`
- `backend/docs/LOGIN_PERSONAL_CORREO_CLAVE.md`
- `backend/tests/integration/test_main_staff_login.py`

### Propuesta 5: RF22 (13 archivos)

`feat(scheduling): validar ingreso anticipado con matricula persistente`

- `backend/app/modules/scheduling/POLITICA_TEMPORAL_INGRESO.md`
- `backend/app/modules/scheduling/api/router.py`
- `backend/app/modules/scheduling/application/validar_ingreso.py`
- `backend/app/modules/scheduling/domain/ingress_policy.py`
- `backend/app/modules/scheduling/infrastructure/ingress_access.py`
- `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`
- `backend/docs/RF22_INGRESO_ANTICIPADO.md`
- `backend/tests/identity/test_ingress_temporal_sql.py`
- `backend/tests/identity/test_student_login_scheduling.py`
- `backend/tests/integration/test_main_early_ingress.py`
- `backend/tests/integration/test_student_identity_security.py`
- `backend/tests/unit/scheduling/test_api_endpoints.py`
- `backend/tests/unit/scheduling/test_ingress_policy.py`

### Propuesta 6: documentacion_conciliacion (2 archivos)

`docs: registrar checkpoint y contrato pendiente de consentimiento`

- `backend/docs/CHECKPOINT_LOCAL_PROPUESTO_20261105.json`
- `backend/docs/CONSENTIMIENTO_CONTRATO_Y_CHECKPOINT_20261105.md`

No se ejecutó `git add`, commit, push, merge, PR, cambio de rama ni operación de
stash. Antes de un commit autorizado se debe repetir SHA-256, `git diff --cached
--check`, nombres y contenido del índice de **cada selección explícita**. El JSON
del plan en la carpeta de evidencia permite revisar rutas sin usar `git add .`.
No se ejecutan esos comandos de preparación en esta revisión.

## 3. Consentimiento: qué existe y qué no está definido

Decisiones funcionales comunicadas por el equipo, que se conservan como tales:
**aceptación antes de crear participación** y **no revocación mientras se ejecuta
la simulación**. No se vuelve a pedir aprobar esos principios ni se inventa una
aceptación, un texto, una versión vigente o un endpoint de revocación.

| Aspecto | Evidencia concreta actual | Límite |
|---|---|---|
| Persistencia de aceptación | Identity `infrastructure/academic_base_models.py::ConsentimientoORM`; migración `20261101_er28_base_academica` | id, estudiante INTEGER con FK a usuario, version_texto VARCHAR(30), fecha_aceptacion y fecha_revocacion; no contiene texto, huella del documento ni regla de vigencia |
| Fuente oficial y versión vigente | No se identificó un archivo de consentimiento aprobado, catálogo, configuración o proveedor de selección en las fuentes accesibles inspeccionadas | Los requisitos/informes y el ER describen el concepto; una cadena version_texto o la versión de una fixture no acreditan el documento vigente |
| Estudiante que acepta | FK identifica una cuenta; Identity ya autentica estudiante y contexto de convocatoria | No hay servicio/endpoint de aceptación que obtenga ese actor del JWT y registre su voluntad explícita |
| Momento | fecha_aceptacion persistida como timestamp sin zona; FechasPersistencia exige convención de zona explícita | No hay escritor productivo de aceptación con reloj de servidor. No interpretar registros legados como UTC por defecto |
| Validación para iniciar | `participation/infrastructure/start.py::IdentityInicioSQLAlchemy.autorizar_inicio` | Relee/bloquea consentimiento, exige mismo estudiante y fecha_revocacion NULL. Vigencia/aplicabilidad se delega a PoliticaInicioIntento, sin proveedor productivo |
| Datos de política | `application/start_policy.py::CondicionesInicioIntento` incluye version_consentimiento y aceptado_en | Recibir esos campos no prueba que exista documento o versión oficial; políticas positivas siguen siendo LAB |
| Antes de crear P | `infrastructure/provision.py::_obtener_o_crear` no recibe ni valida consentimiento; `CondicionesVinculacion` tampoco lo contiene | Provisión independiente LAB puede confirmar P sin aceptación. No está montada en main y no cumple aún la nueva condición |
| Flujo combinado P + I | `iniciar_desde_convocatoria` llama primero _obtener_o_crear, luego preparar_inicio_en_uow y finalmente commit | Un rechazo revierte P/I nuevos, pero P puede haberse insertado/flush antes de validar. Atomicidad final NO demuestra aceptación anterior a crear P |
| Integridad histórica | `20261102_participation_history.py::bd207_padre`, rama consentimiento | Impide cambiar/eliminar id, estudiante, versión y fecha de aceptación cuando están usados por intento. NO incluye fecha_revocacion en la comparación protegida |
| No revocación durante ejecución | No existe una ruta productiva de revocación; start toma un lock compartido mientras dura su transacción | Ese lock no dura toda la simulación y el guard no bloquea específicamente revocación con intento EN_CURSO. No afirmar que la nueva regla está garantizada en PostgreSQL |

La ausencia de fuente aquí significa **no identificada en el repositorio,
configuración y documentación accesibles inspeccionados**, no prueba que la
institución carezca de un documento fuera de estas fuentes. No se consultaron
bases permanentes para buscar aceptaciones ni se tomaron registros LAB como fuente.

La inspección pura de `app.main.app.openapi()` confirmó: ninguna ruta de
consentimiento ni de provisión/inicio desde convocatoria. Sigue registrado
POST `/scheduling/validar-ingreso`. No se conectó nada adicional a main.

## 4. Bloqueo y propuesta mínima para resolverlo

**No se implementa código funcional en esta revisión.** Falta la fuente oficial
versionada y su ámbito de aplicabilidad. Registrar una aceptación de una versión
inventada o elegir el mayor version_texto sería una asociación sin respaldo.
El inicio productivo y la provisión pública permanecen cerrados.

Antes del siguiente incremento, proporcionar/confirmar:

1. Documento exacto aprobado, responsable que autoriza su publicación, identificador
   de versión estable (compatible con 30 caracteres, sin truncar huellas), y fecha
   de vigencia explícita. No se asigna un identificador en este informe.
2. Alcance: global, por caso/version, asignación u otro criterio; mecanismo del
   servidor que selecciona inequívocamente qué documento corresponde a esa
   convocatoria. Una fecha o una etiqueta sola no determina ese alcance.
3. Efecto de publicar otra versión sobre aceptaciones/participaciones existentes.
   No reutilizar automáticamente la última aceptación ni reescribir las anteriores.
4. Tratamiento de aceptaciones repetidas e historial. La tabla permite varias
   por usuario/version y no tiene UNIQUE de ese par; no imponer una cardinalidad
   nueva ni prometer idempotencia persistente sin un contrato y restricciones.

Propuesta a aprobar, sin implementarla: una fuente de documentos de servidor
versionada e inmutable (puede ser un registro de artefactos, sin tabla nueva), que
mantenga bytes históricos, identificador estable, SHA-256 completo y ámbito/vigencia
aprobados. Un puerto de Identity resolvería la definición aplicable y recuperaría
cada definición histórica. No usar un archivo mutable que conserve el mismo id;
no truncar el hash de 64 caracteres a version_texto. El hash acredita contenido,
no por sí mismo aprobación académica. El despliegue debe verificar ambos.

Luego un servicio de aceptación reutilizaría Identity, su Session, reloj del
servidor y conversión temporal explícita. La voluntad tendría que ser explícita;
actor, fecha y versión aplicable se resuelven en servidor. El cliente podría
confirmar la versión/huella presentada para detectar un documento obsoleto, pero
no elegir arbitrariamente una versión ni atribuir la aceptación a otro estudiante.
Solo se persiste después de verificar esas condiciones. No se crea P ni I al
consultar/presentar o aceptar un documento.

La autorización de consentimiento debe compartirse con el iniciador existente,
no duplicar motores. En la UoW de provisión/inicio: resolver actor/convocatoria,
matrícula, sesión, asignación y referencias exactas con los locks existentes;
validar y bloquear aceptación aplicable **antes de agregar P**; después registrar
P/I y un solo commit, o rollback completo. Revisar el orden global de locks de
start.py y provision.py antes de mover lecturas; probar competencia real con
revocación y solicitudes duplicadas. Validar anticipadamente no reemplaza esta UoW.

La prohibición de revocar durante ejecución es una regla confirmada, pero su
protección necesita un contrato de escritura y bloqueo común con inicio/cierre.
No se propone abrir un endpoint nuevo de revocación. Debe precisarse cómo se
representa ejecución frente a vencimiento efectivo todavía no persistido, y qué
ocurre fuera de ejecución; no inventar efectos retrospectivos. Si se exige impedir
SQL directo, hace falta una revisión explícita del guard de fecha_revocacion y
su concurrencia; ninguna migración se crea ni se atribuye esa garantía hoy.

Archivos que probablemente afectaría el siguiente incremento **tras resolver la
fuente**: Identity application/ports y servicio de consentimiento, adaptador de
fuente/aceptaciones, schemas/dependencies/router solo si se aprueba su contrato;
Participation provision_policy.py, provision.py y la validación compartida con
start.py; tests específicos de consentimiento y provisión. ORM/Alembic solo si
la cardinalidad/integridad aprobada lo exige, con autorización y laboratorio.

## 5. RF-22 y pruebas necesarias

Se conserva sin cambios la regla acreditada `[inicio - 10 minutos, inicio)` para
SIN_INICIAR. EN_CURSO continúa sin política de ingreso posterior (503); sesiones
finalizadas rechazan. No se infiere ingreso tardío ni permiso de comenzar antes.
Aun con consentimiento correcto seguiría pendiente esa política posterior y las
condiciones de repetición/provisión. No se habilitan notas oficiales.

Aceptación futura indispensable, sin ejecutarla ni fabricar resultados:

- Documento y versión recuperados del servidor; fuente ausente/ambigua o huella
  inválida falla cerrada. No usar parámetros LAB como configuración productiva.
- Aceptación explícita de JWT titular, cuenta activa y convocatoria propia;
  otro estudiante, versión obsoleta/manipulada y aceptación no explícita rechazados.
- Momento del servidor persistido/recuperado desde otra Session SQL, con zona
  explícita; datos históricos inmutables y reglas de repetición aprobadas.
- Sin consentimiento válido, **ningún INSERT de participación**, no solo ausencia
  tras rollback. Después, autorización completa en la misma UoW y un solo commit.
- Concurrencia/rollback de aceptación y P/I; no duplicación según contrato aprobado.
- Rechazo de revocación durante ejecución, competencia con inicio/cierre y guard
  PostgreSQL si se aprueba; no introducir una operación de revocación alternativa.

Pruebas existentes relevantes, revisadas pero NO ejecutadas ahora:
`test_attempt_start.py::test_consentimiento_ajeno_no_inicia`,
`test_controles_reales_del_inicio`, `test_falta_politica_cierra`,
`test_rollback_tras_insert`; `test_participation_provision.py::
test_consentimiento_ajeno_revierte_participacion_nueva`,
`test_rollback_atomico_de_ambas_entidades` y
`test_dos_inicios_concurrentes_un_vinculo_y_un_intento`.
Sus positivos usan políticas explícitas LAB; no prueban una fuente oficial.

No se ejecutó pytest, PostgreSQL ni Docker en esta revisión documental, ni se
aplicaron migraciones. Se leyó el JUnit previo y se cotejaron las huellas runtime
+tests con la general de RF-22: **2102 aprobadas, 38 omitidas, 0 fallidas/errores,
1 advertencia**, ejecución `pruebas_total_20261105T235005Z`. Es un resultado previo,
no una aprobación nueva; las omisiones no se contabilizan como aprobadas.

## 6. Matriz, preservación y siguiente paso

No se altera la matriz de 27 RF ni sus estados: no hay implementación nueva que
justifique avanzar cumplimiento. RF-12 sigue PARCIAL, RF-22 sigue PARCIAL. Las dos
decisiones del equipo se documentan, pero no acreditan aceptación ni revocación.

Se conserva íntegramente el manifiesto de 34 archivos, stash, referencias, .env,
evidencias y no rastreados. Índice vacío, sin commits ni publicaciones. La única
nueva documentación de producto es este informe; el soporte de verificación queda
en la carpeta de evidencia indicada abajo, fuera de cualquier commit.

**Siguiente incremento recomendado:** recibir el documento aprobado y definir su
resolución versionada por servidor; entonces implementar aceptación explícita y
su control previo a P sobre la UoW existente. No abrir inicio productivo hasta
resolver también la política de ingreso desde el inicio programado.

Evidencia de esta revisión: `evidencias/contrato_consentimiento_20261106T001412Z/` (verificación de 34 huellas,
inventario, propuesta de commits, correspondencia con regresión y cierre).
