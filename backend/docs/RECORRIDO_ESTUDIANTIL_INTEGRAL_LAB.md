# Checkpoints y recorrido estudiantil integral de laboratorio

6 de noviembre de 2026, America/Bogota. Carpeta original, rama
feature/backend-continuidad. No despliegue, push, merge ni PR.

## Checkpoints autorizados y verificados

Se comprobaron las 40 entradas del manifiesto CHECKPOINT_INICIO_ADMITIDO_20261106.json:
rutas, tamaño, SHA-256, contenido, clasificación, imports/sintaxis y coincidencia
del código Python con la general anterior. El manifiesto mismo es la ruta 41
(sin autohuella circular). Selecciones sin solapamiento; índice comprobado por
contenido normalizado y git diff --cached --check antes de cada commit.

| Bloque | Commit local | Archivos | Contenido |
|---|---|---:|---|
| C1 | 6463eecf817f476002f56546f9abc63dd3889731 | 30 | Persistencia y núcleo transaccional de consentimiento/admisión |
| C2 | 758f00e0e245c261fd26c93fb13bf3e320e0f343 | 11 | API privada, contratos, pruebas e inventarios; incluye manifiesto |

Las rutas completas de cada commit constan en el manifiesto y en
evidencias/recorrido_integral_20261106T165102Z/commits_verificados.json.
No se añadieron .env, respaldos, ZIP, Word, cachés ni evidencias temporales.
Fuera de selección había arrastres preservados, incluido el ejecutor documental
backend/scripts/run_unit_tests.py; no había código funcional app/tests/alembic
pendiente fuera de la selección. Se verificaron sus huellas previas.

Los dos commits son el único avance de referencias autorizado: la rama activa
pasó de 28be564 a 758f00e. Stash y las demás ramas/referencias se preservaron.
No se han creado más commits para las nuevas pruebas/documentación posteriores.

## Preparación y superficies reales

Nueva prueba: backend/tests/integration/test_lab_student_journey.py. Reutiliza
el laboratorio PostgreSQL 17 nuevo de pg_autoria y los contratos de publicación
documental, políticas explícitas LAB y escritura existentes; no otro motor.

Preparación administrativa SOLO LAB: administrador activo con contraseña aleatoria
hasheada/verificada por obtener_hasheador, catálogo de roles/permisos, estudiantes,
asociaciones académicas nuevas persistidas por repositorio, grupo/matrículas, grant
docente-espacio, puente de asignación y documento sintético. No se generan UUID
desde INTEGER ni se asignan identidades históricas. Los UUID de identidades nuevas
del laboratorio se registran explícitamente en su sistema. No es un alta académica
completa mediante frontend ni un proceso institucional de aprobación.

Todos los JWT se obtienen por los endpoints de login reales. No se llama a emitir
tokens desde el test ni se sustituyen las dependencias de autenticación, autorización,
repositorios o relaciones. main solamente sustituye sus dos relojes para una fecha
de laboratorio explícita; la app aislada no tiene overrides. Configuración DB/JWT
del proceso de pruebas apunta exclusivamente al contenedor recién creado; .env
no se modifica ni se usa para conectar a bases permanentes.

## Recorrido efectivamente observado

Los códigos siguientes corresponden a respuestas reales, extraídas del JUnit.
Hay 38 operaciones HTTP en el caso principal y 21 en el caso de error/recuperación.
Incluyen preparación y verificaciones negativas, no 59 requisitos adicionales.

| Operación | Superficie ejecutada | Resultado observado |
|---|---|---|
| Bootstrap de administrador | Preparación SQL interna LAB | Cuenta activa, hash real verificado; no registro público abierto |
| Login administrador | main POST /api/v1/identity/auth/personal | 200 |
| Alta docente con permiso del catálogo | main POST /api/v1/identity/docentes | 201 |
| Login docente | main POST /api/v1/identity/auth/personal | 200 |
| Crear caso, consultar edición, configurar grafo, publicar | main /api/v1/cases y /{version_id}/graph, /publish | 201, 200, 200, 200 |
| Crear espacio y programar sesión | main POST /scheduling/espacios y /sesiones | 201 y 201, después del grant interno explícito |
| Crear convocatoria individual de dos estudiantes | main POST /scheduling/sesiones/{id}/convocatorias | 201 por titular; códigos no registrados en evidencias |
| Login estudiantil con correo/código propio | main POST /api/v1/identity/auth/estudiantes | 200 para cada estudiante |
| Espera y repetición autorizada | main POST /scheduling/convocatorias/{id}/espera | 201 y 200, mismo registro |
| Habilitación y consulta de concesión | main POST /scheduling/sesiones/{id}/estado; GET /convocatorias/{id}/admision | 200 y 200; evento DOCENTE, sesión y versión exactas comprobados en otra Session |
| Publicación/selección documental | Repositorio interno, SOLO LAB | Documento sintético persistido y seleccionado; ninguna aprobación institucional |
| Consultar y aceptar consentimiento | App aislada bajo /api/v1/identity/convocatorias/{id}/asignaciones/{id}/consentimiento | GET 200, POST /aceptacion 200; repetición conserva PK y fecha |
| Inicio del estudiante no admitido | App aislada POST /api/v1/convocatorias/{id}/intentos | 403, aunque tiene matrícula y consentimiento propio; cero INSERT P/I |
| Inicio del titular admitido | Misma ruta aislada | 201; los INSERT P/I comparten txid_current(), conexión y un commit |
| Repetir inicio y recuperar participación | Aislada POST /intentos y /participacion | 409 y 200; una P y un I, sin recuperación de intento inventada |
| Escenario/progreso ajenos | main GET /api/v1/attempts/{id}/current-scenario y /progress | 403 |
| Consultar escenarios y registrar decisiones | main GET current-scenario, POST decisions/{decision_id} | 200/201; segunda selección 409, preserva primera |
| Consultar progreso | main GET /api/v1/attempts/{id}/progress | 200, dos respuestas, sin pendientes ni correcciones/notas |
| Finalizar y repetir cierre | main POST /api/v1/attempts/{id}/finish | 200/200, misma respuesta, FINALIZADO persistido |
| Publicación automática de notas | Consulta SQL independiente del resultado | Cero resultado_intento para el intento; no se llama al motor oficial |

No es una ejecución íntegra de app.main: consentimiento y provisión/inicio se
montan solo en otra aplicación FastAPI dentro del test. Es HTTP ASGI/TestClient,
JWT y PostgreSQL reales; no acredita navegador, TLS ni un servidor desplegado.
Los grafos sí se construyen y publican por API, no mediante INSERT de transiciones.

## Negativos, integridad y recuperación

El caso integral verifica estudiante ajeno, estudiante sin concesión pese a
consentimiento propio, repetición de intento, selección inmutable y privacidad.
Reutiliza además las 11 aceptaciones de test_admitted_start.py: no admitido,
retirada después de consulta positiva, matrícula inválida, consentimiento ausente,
obsoleto o ajeno, concurrencia, P histórica sin concesión, rollback, cambio documental
concurrente e historial. No se crean pruebas redundantes para incrementar estadísticas.

El segundo caso nuevo provoca SELECT 1/0 en PostgreSQL después del INSERT I,
únicamente mediante un hook del engine de laboratorio. El servidor produce SQLSTATE
22012 y HTTP 500 esperado; la UoW revierte P e I. Desde otra Session ambos conteos
son cero y la aceptación previamente confirmada permanece. Se retira el hook y
el reintento responde 201, con una P y un I. No se simula un error positivo de
autorización ni se modifica el comportamiento HTTP del backend.

Para el inicio exitoso se observaron dos INSERT con el mismo ID de transacción
PostgreSQL, la misma conexión y un commit. La comprobación de rechazo sin concesión
observó cero INSERT antes de la respuesta. Después se verifican FK de aceptación,
versión de asignación y cierre en sesiones distintas. La garantía cubre servicios
y UoW existentes, no impide todo SQL privilegiado que eluda reglas de aplicación.

## Resultados actuales, versiones y evidencia

| Ejecución NUEVA | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Aceptación: 2 E2E nuevos + 11 previos | 13 | 0 | 0 | 0 | 1 |
| Regresión relacionada mixta | 682 | 0 | 0 | 0 | 1 |

Duraciones: 44.54 s y 358.70 s. Advertencia conocida de Starlette/httpx.
No sumar ejecuciones solapadas. No nueva general: no hubo modificaciones a
componentes compartidos ni defectos que exigieran corregirlos. Las 2224 aprobadas
y 38 omitidas de la general anterior son HISTÓRICAS, no una corrida de esta entrega.
No se infiere un nuevo total general a partir de añadir dos tests.

El 401 histórico no reapareció. Se conservaron diagnóstico y causa no demostrada;
no se modificaron JWT, leeway o permisos. La instrumentación observacional registra
tipos de errores JWT esperados en negativos y estabilidad temporal, sin secretos.

Código probado: HEAD 758f00e más la nueva prueba local identificada por SHA-256.
Cada ejecución guarda comando, cwd, HEAD, estado Git, hashes, log, JUnit y estabilidad
de fuentes. Los pasos observados se extraen del XML, no de respuestas fabricadas:

- evidencias/recorrido_integral_20261106T165102Z/pruebas_casos_20261106T165903Z/
- evidencias/recorrido_integral_20261106T165102Z/pruebas_focal_20261106T170045Z/
- pasos_http_observados.json y .csv: superficie, método, ruta, esperado/observado.
- commits_verificados.json: rutas exactas de los dos checkpoints.
- estado_rf_27.csv: copia trazable de los 27 estados vigentes.

Reproducción PowerShell desde la carpeta original:

```powershell
.\.venv\Scripts\python.exe evidencias\recorrido_integral_20261106T165102Z\ejecutar_validacion.py casos
Get-Content evidencias\recorrido_integral_20261106T165102Z\pasos_http_observados.json -Encoding UTF8
```

Cambiar casos por focal reproduce la selección relacionada. El ejecutor desactiva
.env/URLs externas y usa los fixtures Docker propios. Nunca editar fuentes durante
pytest. No se incluyen tokens, códigos individuales, contraseñas, correos personales
ni URLs con credenciales en los pasos exportados.

## Disponibilidad para frontend y bloqueos concretos

Registrado y probado en main de laboratorio: login personal/estudiantil, alta docente,
Cases y grafo protegido, programación/convocatorias, espera/admisión/validar-ingreso
y cuatro operaciones del intento existente. Requieren configuración real segura,
datos y migraciones; no se certifica aquí una instancia productiva desplegada.

Solo aislado: consulta/aceptación de consentimiento, provisión e inicio. No añadir
estas rutas a main hasta contar con documento institucional aprobado, proceso
controlado de publicación/selección y políticas obligatorias de inicio/provisión
autorizadas. Las implementaciones LAB nunca serán sus defaults productivos.

Solo interno/preparación: bootstrap de administrador/catálogos, verificación y
registro de identidades académicas, organización/matrículas, grants de espacio,
puente de asignación y publicación documental. Falta definir u operar su proceso
administrativo autorizado; no atribuir estas preparaciones a una UI inexistente.

Dependencias fuera del recorrido acreditado: entrega segura del código por correo
(aquí se traslada la respuesta docente en memoria del LAB, no se demuestra SMTP),
políticas de Evaluation para notas/consolidación/reportes oficiales, repetición
excepcional y recorridos multipregunta/cíclicos/revisitas todavía no autorizados.
No se publica una nota para aparentar que el MVP académico está completo.

## Estado funcional y Git al cerrar

Sin reclasificaciones por cantidad de pruebas: 14 IMPLEMENTADO, 8 PARCIAL y
5 BLOQUEADO, conforme a las 27 filas de la matriz. Se corrige su párrafo numérico
obsoleto 13/9/5 y referencias de login personal ya acreditado. RF-12 sigue PARCIAL.

- IMPLEMENTADO: RF-01, 02, 05, 06, 07, 08, 09, 11, 15, 17, 18, 19, 22, 26.
- PARCIAL: RF-03, 04, 10, 12, 20, 21, 23, 27.
- BLOQUEADO: RF-13, 14, 16, 24, 25.

No se reauditan ni se atribuyen nuevas aceptaciones a los demás RF/RNF. La matriz
vigente conserva sus archivos, endpoints, pruebas y dependencias individuales.
Nuevo trabajo posterior a checkpoints, sin commit adicional: nueva prueba E2E,
este informe y la actualización de matriz. Los ocho componentes Python del
incremento previo no se reescriben; no hay cambios productivos en esta etapa.

Una cabeza Alembic 20261106_consent_versions y 33 tablas de metadata, sin nuevas
migraciones/modelos o cambios al DBML. Solo PostgreSQL 17 nuevo y desechable;
no acceso a bases permanentes. Stash, demás referencias, .env, respaldos y arrastres
preservados. Revisión final de índice/diff y limpieza en verificacion_final.json.

Prioridad recomendada: cerrar documento/proceso institucional y políticas de
inicio, además del proceso administrativo que proporciona vínculos/matrículas/
grants/asignación. Después revisar el montaje mínimo en main. En paralelo, resolver
los contratos académicos que bloquean Evaluation/reportes y la entrega real de
convocatorias. No iniciar esa implementación ni el frontend automáticamente.
