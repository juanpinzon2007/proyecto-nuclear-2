# PT-DCP-01 — Demostración paso a paso

Esta carpeta añade exclusivamente una demostración y su evidencia. No modifica el Plan de Pruebas, código productivo, DBML, ORM ni migraciones. No instala rutas en `main.py`.

## Ejecutar y tomar capturas

Abra PowerShell en una terminal interactiva, con Docker iniciado y la imagen PostgreSQL 17 ya instalada. No necesita iniciar el Compose del proyecto ni suministrar una URL de base de datos.

```powershell
Set-Location 'C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2'
& '.\backend\docs\demostracion_pt_dcp_01\ejecutar.ps1' -Pausar
```

Después de **cada operación real**, verá precondiciones, entrada, operación, esperado, obtenido y referencia al test fuente. Cuando aparezca `Capture este paso`, tome la captura y pulse ENTER. Se comprueba el resultado antes de pausar. Si falla una comprobación, pytest falla y el script comunica el error; no se convierte en una evidencia aprobada.

Para facilitar las capturas, también puede ejecutar por separado:

```powershell
& '.\backend\docs\demostracion_pt_dcp_01\ejecutar.ps1' -Escenario participation -Pausar
& '.\backend\docs\demostracion_pt_dcp_01\ejecutar.ps1' -Escenario evaluation -Pausar
& '.\backend\docs\demostracion_pt_dcp_01\ejecutar.ps1' -Escenario feedback -Pausar
```

Cada invocación crea su propio laboratorio y una carpeta nueva de salidas. Para ejecutar sin pausas, omita `-Pausar`. Termine todos los pasos para que el fixture elimine su contenedor; no cierre forzosamente la terminal. No hay comandos de limpieza global.

Las pausas fueron verificadas en una terminal interactiva real con el escenario de feedback. No requieren navegador, Postman ni Uvicorn. **TestClient ejecuta solicitudes ASGI dentro del proceso**, usando el router real: no es una prueba de red HTTP desplegada. PostgreSQL sí se utiliza mediante conexiones TCP reales.

## Datos y límites de la demostración

- El fixture existente crea estudiantes, docente, asociaciones académicas, matrícula, convocatoria, consentimiento, caso, versión publicada, rúbrica y un intento sintéticos. Las claves se generan normalmente y se muestran en la evidencia: no copie UUID de otra ejecución.
- El intento se prepara directamente mediante fixtures. **No demuestra inicio productivo de intentos ni login con contraseña.** El JWT es emitido por el componente real existente para una cuenta sintética; se verifican firma, roles y titularidad mediante dependencias reales. El token y los secretos no se imprimen.
- Participation usa el grafo SQL real con una pregunta por escena y ramas sin ciclos. El reloj controlado marca `2026-11-02T12:01:00Z`, dentro del horario autorizado. No se altera la hora del equipo ni se acepta una hora enviada por el estudiante.
- Evaluation y feedback son servicios internos, no endpoints públicos. Se utilizan otros intentos sintéticos cerrados para reutilizar exactamente las fixtures de evaluación existentes. **No se afirma que la evaluación mostrada corresponda al intento de la demostración HTTP.**
- El cálculo de dos criterios y la persistencia de un criterio son demostraciones distintas. No se almacena una nota de 60 fingiendo que procede de la rúbrica persistida de un criterio.
- La escala 0–100 y los pesos iguales están aprobados. La conversión del nivel `5` a `100` y la agregación de una pregunta se suministran explícitamente como convenciones de laboratorio existentes. No certifican el mapeo ni la agregación académicos pendientes.
- No se habilitan calificaciones oficiales, RF-22, inicio productivo ni rutas productivas de Participation. No se prueba un frontend.

## Secuencia y capturas sugeridas

No se asignan identificadores oficiales de casos PT-DCP-01 porque no se ha leído ni modificado ese documento. Relacione las siguientes etiquetas con sus casos ya definidos.

| Evidencia | Precondiciones / entrada | Operación observada | Resultado esperado y comprobado | Test automatizado fuente |
|---|---|---|---|---|
| P-01, paso 1 | Titular autenticado, intento EN_CURSO, primera pregunta de escena inicial y opción propia | `POST /api/v1/attempts/{id}/decisions/{questionUUID}` con `id_opcion` | HTTP **201**, intento EN_CURSO | `test_scheduling_participation.py::test_http_real_jwt_sql_respuesta_progreso_put_y_cierre` |
| P-02, pasos 2–3 | Respuesta anterior confirmada; otra alternativa de la misma pregunta | `PUT` sobre la misma ruta; después lectura SQL | HTTP **409**, `RESPUESTA_INMUTABLE`; PostgreSQL conserva exactamente la opción original | Test HTTP anterior y `test_immutable_answers.py::test_put_logico_rechazado_conserva_original` |
| P-03, pasos 4–6 | Una respuesta; JWT del titular y luego JWT válido de otro alumno | `GET /api/v1/attempts/{id}/progress` | Titular: **200**, `respondidas=1`, selección propia, sin corrección ni puntajes. Ajeno: **403**, `ACCESO_DENEGADO`, sin selecciones | Test HTTP anterior y `test_scheduling_participation.py::test_intento_ajeno_no_se_consulta_ni_responde` (este último prueba el servicio; la demo añade HTTP) |
| P-04, pasos 7–10 | Siguiente pregunta autorizada por el grafo; luego recorrido respondido | POST de segunda respuesta; `POST /api/v1/attempts/{id}/finish` dos veces | **201**; **200**, FINALIZADO; segunda finalización idéntica | Test HTTP anterior |
| E-01, paso 1 | Logros conocidos 20 y 100; pesos efectivos 1/2 y 1/2 | Calculador existente, `(20 + 100) / 2` | **60 exacto**. Pesos históricos 60/40 conservados, no utilizados como pesos efectivos | `test_academic_policy.py::test_igual_peso_no_reescribe_pesos_historicos` |
| E-02, pasos 2–3 | Otro intento cerrado; una pregunta, un criterio; nivel de fixture 5 y mapeo LAB `5×20` | Motor existente → repositorio → consulta con nueva Session SQL | **100**, `oficial=false`; detalle SQL `100.00`; misma versión, rúbrica y huella; resultado recuperado idéntico | `test_academic_policy.py::test_100_se_persiste_y_recupera_sin_nota_oficial`; `test_evaluation_result_storage.py::test_evaluar_guardar_y_recuperar_otra_session` |
| F-01, pasos 1–2 | Otra participación sintética cerrada; docente propietario y estudiante titular | Registrar valoración individual y consultar; repetir lectura como otro estudiante | Texto recuperado para el titular; **AccesoDenegado** para el ajeno. Es una excepción interna, no un HTTP inventado | `test_academic_policy.py::test_feedback_individual_editable_y_privado` |

Todos los tests fuente están en `backend/tests/integration/`. La demostración ejecutable es `test_demostracion.py`, en esta carpeta. Reutiliza sus fixtures y helpers; no sustituye permisos, rutas, repositorios ni el calculador productivos por nuevos motores simulados.

En progreso, `total_aplicable=null` mientras no se ha terminado el recorrido es correcto: no se inventa un total contando preguntas de ramas no elegidas.

## Qué anexar al Plan de Pruebas

Por cada captura incluya: identificador del caso de su Plan, etiqueta anterior, número de paso, fecha de ejecución propia, entrada, resultado esperado, resultado obtenido y archivo JSON de respaldo. Capture la operación y el cuerpo de respuesta, no únicamente `PASSED`.

El script imprime la ruta de su carpeta `salidas/<ejecución>/`. Contiene:

- `consola.txt`: transcripción completa, incluyendo resumen de pytest.
- `test_01_participation_http.json`: diez pasos, cuerpos HTTP completos y conservación SQL.
- `test_02_evaluation_interna.json`: tres pasos de cálculo y persistencia técnica.
- `test_03_feedback_individual.json`: dos pasos de titularidad y rechazo.
- `laboratorio.json`: base aislada, versión PostgreSQL, puerto local y revisión Alembic realmente consultados.

Para releer una evidencia sin volver a crear una base:

```powershell
$carpeta = '.\backend\docs\demostracion_pt_dcp_01\salidas\20261102_235350_593_dbff9f2f'
$evidencia = Get-Content -LiteralPath "$carpeta\test_01_participation_http.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$evidencia.pasos[1] | ConvertTo-Json -Depth 15
```

Ese ejemplo muestra el PUT rechazado de la ejecución comprobada. Para sus capturas nuevas, sustituya `$carpeta` por la ruta impresa por su ejecución. Los JSON son observaciones guardadas, no respuestas que deban devolver siempre los mismos UUID.

## Ejecuciones comprobadas

1. Preparación inicial: **3 passed**, 0 skipped, 0 failed, 0 errors, una advertencia conocida; 9.90 s. La consola inicial tenía problemas de tildes; sus JSON UTF-8 se conservaron. No se recomienda esa consola para las capturas.
2. Versión final, con rechazo HTTP de progreso ajeno y UTF-8: **3 passed**, 0 skipped, 0 failed, 0 errors, una advertencia conocida; **9.61 s**. Quince pasos comprobados. Evidencias completas en `salidas/20261102_235350_593_dbff9f2f/`.
3. Verificación interactiva de `-Escenario feedback -Pausar`: **1 passed, 2 deselected**, 0 skipped, 0 failed, 0 errors, una advertencia conocida; 15.51 s, incluidas las pausas. Evidencias en `salidas/20261102_235431_822_ed49a563/`.

La advertencia es `StarletteDeprecationWarning` por el uso actual de httpx con TestClient. No se instalaron dependencias. Los escenarios no seleccionados no son pruebas aprobadas ni omitidas por configuración. **No se ejecutó la suite general** ni se actualiza su línea base con estas cifras.

## Aislamiento y conservación

El runner solo ejecuta este archivo. Rechaza otra ejecución pytest activa y una rama diferente; no cambia de rama. Temporalmente configura variables del proceso para el opt-in del laboratorio y retira URLs de laboratorios externos; restaura los valores al terminar. No edita `.env`.

Se reutiliza `motor_postgresql_desechable`: crea un contenedor nuevo identificado por ID completo y etiqueta `sps.identity.mapping.lab=true`, PGDATA en tmpfs, sin volúmenes persistentes; conecta por TCP a un puerto efímero de `127.0.0.1`, comprueba la base nueva vacía y aplica las migraciones existentes **solo allí**. Su `finally` elimina exclusivamente su contenedor. No se añadieron, editaron ni ejecutaron migraciones sobre bases del equipo.

En la ejecución final se consultó PostgreSQL **17.11**, base `sps_identity_test_resolver`, puerto **54601**, revisión **20261102_immutable_answers**. El puerto cambiará en cada ejecución. Tras ambas ejecuciones finales no quedaron contenedores con la etiqueta del laboratorio; se verificó mediante consulta de solo lectura:

```powershell
docker ps -a --filter label=sps.identity.mapping.lab=true --format '{{.ID}} {{.Names}}'
git diff --check
```

La consulta Docker no borra nada. Si hay otros laboratorios simultáneos, la presencia de un contenedor ajeno no autoriza eliminarlo.

Se compararon huellas SHA-256 de todos los `.py` y `.dbml` bajo `backend/app/` y `backend/alembic/` antes y después: **sin cambios**. Rama conservada `feature/integracion-backend`, HEAD `ee025d2` con cambios previos locales preservados. `git diff --check` sin errores; permanece el aviso previo de conversión LF/CRLF de `caso_repository.py`. No se realizaron commits, pushes ni merges.
