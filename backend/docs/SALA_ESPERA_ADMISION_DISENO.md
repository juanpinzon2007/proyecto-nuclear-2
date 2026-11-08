# Sala de espera y admisión: diseño e implementación autorizados

Decisión funcional explícita del equipo, 5 de noviembre de 2026. No aprueba el
consentimiento institucional. No permite crear P/I ni notas oficiales.

Se reutiliza convocatoria, única por sesión/estudiante. Diseño físico aditivo:
espera_registrada_en TIMESTAMPTZ NULL, espera_version_caso_id UUID NULL y
admision_evento_id UUID NULL. La tercera columna es necesaria para conservar la
versión exacta pedida, incluso antes de P/I: solo fecha y evento no la conservan.
No se añaden tablas. Legado NULL no se convierte automáticamente en admitido.

FK compuesta sesión/versión a la sesión; FK evento/sesión a la auditoría con
UNIQUE parental; CHECK pareja fecha/versión y admisión implica espera. Triggers
protegen irreversibilidad de solicitud/concesión, significado del evento docente
SIN_INICIAR->EN_CURSO, referencias y causa histórica. Downgrade rechaza pérdida
de datos si ya hay solicitudes/admisiones. Solo se prueba en PG17 desechable.

Registro: sesión y convocatoria con locks NOWAIT, identidad/ámbito revalidados;
solo SIN_INICIAR crea espera. Repetición de espera válida devuelve el mismo
registro; tras habilitar solo una concesión ya otorgada se recupera, no se crea.
No se usa timestamp para decidir el corte. No es presencia online ni heartbeat.

Habilitación: coordinador RF-19 mantiene su lock/refresco S y auditoría; antes de
avisos/commit bloquea candidatos C con NOWAIT, valida elegibilidad y concede con
esa auditoría. Orden nuevo S->C. NOWAIT evita esperar C cuando un escritor legado
posee C y espera S: se revierte toda habilitación y devuelve 409 reintentable,
sin alterar el contrato de transición inválida ni inventar tolerancia temporal.
El cierre worker no congela ni modifica admisiones. No hay entrega postcommit.

Validar ingreso/consultar admisión son lecturas privadas. Espera sí escribe.
Ingreso requiere EN_CURSO + concesión de esa sesión/versión, y condiciones vigentes
de cuenta, convocatoria, matrícula, código/horario. Se conservan límites exteriores
de programación y reloj consciente de zona ya existentes, sin margen nuevo. La
misma validación se prepara para composición futura de Participation; inicio
productivo permanece cerrado por consentimiento y contratos restantes.

No se cambian el DBML académico original ni identidad INTEGER/UUID. La revisión
Alembic dependerá de la cabeza única comprobada 20261104_teacher_spaces.


## Contrato HTTP registrado en app.main

No se cambia main.py: se amplía exclusivamente el router Scheduling ya registrado.
Autenticación JWT real y contexto de convocatoria, cuentas/roles y resolver SQL
vigentes; no hay cabeceras alternativas ni identificadores de alumno elegidos.

| Operación | Efecto | Respuesta |
|---|---|---|
| POST `/scheduling/convocatorias/{id}/espera`, cuerpo `codigo_acceso` | Primera solicitud propia ACTIVA, matrícula y versión inequívocas, S SIN_INICIAR. Es escritura con commit | 201 primera, 200 repetida/recuperación de concesión previa, 403 no autorizada o nueva tardía, 409 conflicto de lock reintentable, 503 dependencia, 422 cuerpo inválido |
| GET `/scheduling/convocatorias/{id}/admision` | Comprobante privado sin DML, flush ni commit | 200 con ids convocatoria/sesión/versión, solicitada, admitida y estado_sesion; 401/403/503 según identidad/dependencias |
| POST `/scheduling/sesiones/{id}/estado`, acción iniciar | Transición docente, auditoría, concesiones y avisos internos atómicos | 200; transición repetida 409 sin duplicados; conflicto con C bloqueada 409 con rollback; fallo SQL 503 |
| POST `/scheduling/validar-ingreso` | Revalida JWT, código, convocatoria, matrícula, versión, EN_CURSO y concesión causal. Solo lectura | 200 autorizado; 403 no admitido/retirado/cerrado/fuera de horario, 503 inconsistencia/configuración temporal, 401/422 habituales |

El comprobante no contiene código, nota, rúbrica, respuestas ni contenido. Su
booleano admitida describe la concesión histórica: no reemplaza validar-ingreso
ni acredita permiso vigente cuando la sesión finalizó o cambió la matrícula.
Recuperar mediante GET no crea otra solicitud; POST repetido no duplica la existente.
Los límites exteriores programados [fecha_inicio, fecha_fin) se conservan, con
fechas conscientes de zona y reloj servidor inyectable, sin minutos extra. La
espera no tiene TTL ni requisito de conexión continua. Ningún timestamp decide
quién llegó primero: decide el lock y el commit.

## Congelación y concurrencia

El coordinador existente conserva el lock exclusivo S y populate_existing de
RF-19. Solo iniciar con origen DOCENTE ejecuta congelar_admisiones. La espera
adquiere S y luego C; NOWAIT devuelve 409 cuando ya está habilitando. Al congelar,
C se bloquea NOWAIT para no esperar un escritor anterior que posea C y espere S.
Se verifica nuevamente cuenta activa/rol, propietario académico inequívoco,
matrícula/asignación y versión. Las solicitudes inválidas no reciben concesión;
corregirlas después no permite una admisión tardía. Un fallo revierte estado,
auditoría, avisos y todas las concesiones. Una segunda habilitación la rechaza
State; el worker finaliza sin congelar nuevamente. No se promete entrega externa
ni efectos exactamente una vez fuera de PostgreSQL.

Los triggers resguardan historial y referencias; la elegibilidad y el conjunto
completo se conceden por el coordinador autorizado, no por un permiso de SQL
arbitrario. Superusuarios/propietarios capaces de deshabilitar triggers quedan
fuera de esa garantía. Los antiguos fixtures de políticas sintéticas desactivan
solo en su aplicación de prueba el puerto nuevo; NO acreditan admisión. La suite
nueva usa main y admisión SQL real sin override de autenticación/autorización.

## Persistencia y reversión

Revisión `20261105_waiting_admission`, depende de `20261104_teacher_spaces`.
Tres columnas nullable sin backfill en convocatoria; UNIQUE parental en auditoría,
dos FK compuestas, dos CHECK, dos funciones y tres triggers. No crea tablas ni
convierte INTEGER/UUID; metadata sigue en 31 tablas. No se toca DBML académico.
La revisión anterior y los guards históricos se conservan. Upgrade/downgrade/
upgrade probado en PG17 vacío desechable; downgrade con evidencia de solicitudes
se rechaza antes de eliminar datos. Para un despliegue real futuro se requiere
respaldo y revisión operativa; NO se aplicó a una base permanente.

## Separación respecto a Participation y consentimiento

Cinco conceptos distintos: solicitud de espera → concesión congelada → ingreso
validado → participación creada → intento iniciado. Los tres primeros NO crean
los dos últimos. ConsultaIngresoSQLAlchemy admite inyectar el mismo puerto
AutorizacionAdmision/AdmisionSQLAlchemy; no hay segundo autorizador ni política
productiva de laboratorio. Su compatibilidad histórica se conserva cuando una
composición aislada proporciona explícitamente su política LAB.

Main conserva únicamente las cuatro operaciones acreditadas de intentos existentes;
no registra provisión, inicio, aceptación sintética, resultados ni notas oficiales.
El consentimiento sigue sin documento oficial publicado. La fuente productiva
continúa ausente. No se cambia la comprobación previa al INSERT de P ni su UoW.
La referencia persistente P→aceptación está pendiente: propuesta mínima, columna
nullable id_consentimiento FK a consentimiento.id_consentimiento, verificando mismo
estudiante y evidencia histórica inequívoca antes de hacerla obligatoria; no
backfill inventado. Requiere revisión/aprobación y migración propia, NO implementada.
Repetición y demás políticas de inicio no se resuelven mediante una admisión.

## Evidencia actual y reproducibilidad

Carpeta: `evidencias/sala_espera_20261106T021313Z/`. Incluye HEAD, refs, stash,
huellas iniciales, comandos/entorno aislado, logs, JUnit y resultados con fuentes
estables durante cada ejecución. El runner desactiva lectura de .env y elimina
URLs externas en el proceso hijo; solo habilita creación de laboratorios propios.

- Primera aceptación: 23 aprobadas y 1 fallo de sincronización del test. Un
  endpoint async con SQL síncrono bloqueaba el mismo portal TestClient. Se
  corrigió la prueba para usar portales independientes; no se rebajó el lock.
- Regresión focalizada: 606 aprobadas, cero fallos/errores/omisiones, una advertencia
  conocida, 233.96 s, `pruebas_focal_20261106T022236Z`.
- Aceptación ampliada final: 32 aprobadas, cero fallos/errores/omisiones, una
  advertencia conocida, 61.61 s, `pruebas_casos_20261106T022726Z`.
- Las ejecuciones se solapan; NO sumar sus aprobaciones. La general se registra
  al finalizar, no se atribuye a esta entrega el histórico 2126/38.

Comandos PowerShell desde la raíz del repositorio (runner local preservado):

```powershell
C:\Python313\python.exe -B evidencias/sala_espera_20261106T021313Z/ejecutar_validacion.py casos
C:\Python313\python.exe -B evidencias/sala_espera_20261106T021313Z/ejecutar_validacion.py focal
C:\Python313\python.exe -B evidencias/sala_espera_20261106T021313Z/ejecutar_validacion.py total
```

El runner usa .venv del proyecto. Requiere Docker Engine Linux y postgres:17;
crea solamente sps-resolver-lab-* con etiqueta, puerto TCP efímero y tmpfs, y
elimina sus contenedores propios al salir. No sustituye una configuración segura
de despliegue ni instala dependencias.


### Ajustes de compatibilidad de pruebas históricos

La primera general (`pruebas_total_20261106T023004Z`) registró 2031 aprobadas,
38 omitidas, 23 fallos y 104 errores. Se preservan todos sus logs/JUnit. Causas:
asserts de la cabeza anterior/conteo de triggers, comparación DDL SQLite incompleta
y fixtures que usaban el ORM actual con una revisión antigua sin columnas nuevas.
No fueron fallos de la aceptación HTTP nueva; sí eran incompatibilidades reales
que impedían acreditar la regresión.

Se actualizan referencias de cabeza y conteo solo cuando el esquema es head.
Las fixtures de ejecución de asignación, pasos y resultados migran a head. Las
pruebas puras de revisiones antiguas mantienen sus padres y contadores históricos;
su DDL auxiliar añade solo las tres columnas nullable necesarias para preparar datos
con ORM actual, sin estampar la nueva revisión ni atribuirle triggers/garantías.
La comparación de aquella revisión excluye únicamente las restricciones futuras
nominalmente identificadas; la de head sigue siendo completa. SQLite construye
FK/UNIQUE/CHECK reales mediante DDL propio, sin fingir bloqueos/guards PostgreSQL.
No se borra ningún test ni se agregan skip/xfail. Regresión de los 13 archivos
afectados completa: 333 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia,
194.44 s; `pruebas_diagnostico_20261106T024743Z`. No sumar con otras suites.


## Cierre de validación

General final: **2158 aprobadas, 38 omitidas, 0 fallidas, 0 errores y 1 advertencia
Starlette conocida**, 948.13 s. `pruebas_total_20261106T025335Z`, final UTC
2026-11-06 03:09:36 (2026-11-05 22:09:36 America/Bogota). Las 38 omisiones son
29 Identity y 9 Participation antiguas condicionadas a URL: NO se cuentan como
aprobadas. Los laboratorios nuevos sí se ejecutaron. Fuentes estables durante
pytest; solo se generó el artefacto BD2-04 permitido y preservado.

La aceptación final ampliada mantiene 32/0/0/0, 63.27 s,
`pruebas_casos_20261106T025215Z`, y verifica el mismo autorizador en la consulta
histórica existente de Participation. Las 606 focalizadas y 333 relacionadas se
solapan con la general: sus cifras no se suman.

RF-22 queda IMPLEMENTADO para la admisión aprobada/acreditada, no desplegado sobre
una base permanente ni equivalente a inicio de simulación. La matriz conserva
RF-12 PARCIAL; consentimiento oficial, referencia P→aceptación y contratos restantes
de inicio siguen cerrados. No se altera Evaluation ni se publican notas.

Riesgos y condiciones operativas: al desplegar en el futuro se debe instalar esta
revisión antes de ejecutar el ORM nuevo. Las sesiones antiguas EN_CURSO sin
solicitud/concesión no reciben backfill. Habilitar con conjunto vacío no autoriza
altas posteriores. 409 de lock permite reintentar; no añade minutos de tolerancia.
Las escrituras SQL privilegiadas que eludan al coordinador no acreditan ámbito
académico; los triggers preservan referencias/historia, no sustituyen autorización.
No se afirma presencia online ni entrega externa exactamente una vez.

## Archivos del incremento (distintos del trabajo previo preservado)

- `backend/alembic/versions/20261105_waiting_admission.py`
- `backend/app/modules/participation/api/HTTP.md`
- `backend/app/modules/participation/infrastructure/integration.py`
- `backend/app/modules/scheduling/POLITICA_TEMPORAL_INGRESO.md`
- `backend/app/modules/scheduling/api/admission_router.py`
- `backend/app/modules/scheduling/api/dependencies.py`
- `backend/app/modules/scheduling/api/router.py`
- `backend/app/modules/scheduling/api/schemas.py`
- `backend/app/modules/scheduling/application/cambiar_estado_y_publicar.py`
- `backend/app/modules/scheduling/application/validar_ingreso.py`
- `backend/app/modules/scheduling/domain/ingress_policy.py`
- `backend/app/modules/scheduling/infrastructure/admission.py`
- `backend/app/modules/scheduling/infrastructure/models.py`
- `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`
- `backend/docs/CIERRE_CONTRATOS_INICIO_PRODUCTIVO_PROPUESTA.md`
- `backend/docs/CONSENTIMIENTO_E_INICIO_INTERNO.md`
- `backend/docs/DECISIONES_FUNCIONALES_RF22.md`
- `backend/docs/RF22_INGRESO_ANTICIPADO.md`
- `backend/docs/SALA_ESPERA_ADMISION_DISENO.md`
- `backend/tests/identity/academic_identity_support.py`
- `backend/tests/identity/test_academic_identity_repository.py`
- `backend/tests/identity/test_ingress_temporal_sql.py`
- `backend/tests/integration/scheduling/conftest.py`
- `backend/tests/integration/test_academic_policy.py`
- `backend/tests/integration/test_assignment_bridge.py`
- `backend/tests/integration/test_cases_guard_migration.py`
- `backend/tests/integration/test_er28_academic_base.py`
- `backend/tests/integration/test_evaluation_result_storage.py`
- `backend/tests/integration/test_immutable_answers.py`
- `backend/tests/integration/test_main_early_ingress.py`
- `backend/tests/integration/test_participation_http_composition.py`
- `backend/tests/integration/test_participation_persistence.py`
- `backend/tests/integration/test_schema_integration.py`
- `backend/tests/integration/test_steps_uuid.py`
- `backend/tests/integration/test_student_identity_security.py`
- `backend/tests/integration/test_teacher_space_migration.py`
- `backend/tests/integration/test_waiting_admission.py`
- `backend/tests/unit/scheduling/test_api_endpoints.py`
- `backend/tests/unit/scheduling/test_cambiar_estado_y_publicar.py`


El manifiesto nuevo `CHECKPOINT_SALA_ESPERA_ADMISION_20261105.json` incluye las
huellas actuales y clasifica el trabajo pendiente acumulado. No reescribe los dos
manifiestos históricos. Git conserva rama feature/backend-continuidad, HEAD
33981c8, índice vacío, ramas originales y stash. No se hicieron commits ni push,
no se tocó .env, el ER original ni bases permanentes. Los contenedores propios
fueron eliminados por sus fixtures. Evidencia completa en la carpeta citada.

Siguiente incremento recomendado: obtener el consentimiento oficial aprobado y
su fuente versionada verificable, acordar/aprobar el enlace histórico entre P y
aceptación y completar los contratos aún obligatorios de inicio; entonces integrar
el mismo autorizador en la transacción de provisión/inicio. No se inicia aquí.
