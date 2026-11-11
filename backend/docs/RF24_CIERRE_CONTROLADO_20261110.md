# Fase 9 — Cierre condicionado de RF-24

10 de noviembre de 2026, America/Bogota. Ejecuciones nuevas; los timestamps UTC de los laboratorios cruzan al 11 de noviembre. No se modifica la política académica.

## Preservación y alcance

Rama verificada: `codex/participation-inicio-main-20261109`. HEAD inicial/final: `a62868d6e57db7efbc0f7fa14c097898f78dc145`, checkpoint RF14 presente. Índice vacío al comenzar. Ocho modificaciones anteriores y 3291 archivos sin seguimiento iniciales, incluido el informe Fase8, inventariados y preservados. No hay cambios de worktree ni rama, commit, push, pull, merge, reset, clean o checkout.

`evidencias/rf24_fase9_20261110/PRESERVACION_INICIAL.json` conserva referencias, huellas de .env/código/tests, stash e inventario de archivos. No contiene sus secretos. Las ocho huellas coinciden con la preservación anterior. Las pruebas se ejecutan sobre **HEAD más esos cambios locales previos**; no se atribuyen a un checkout limpio del commit. No se modificó código productivo, pruebas, ORM, migraciones, .env ni bases permanentes en esta fase.

## Contrato original y decisiones vigentes

Fuente: `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, p.5:

> RF-24: El sistema calcula la nota parcial de quien no termina y asigna cero a cada pregunta de quien no participa, aplicando las reglas de la rúbrica.

La p.7, RN14, exige conservar respuestas y evaluación parcial al agotarse el tiempo; RN15 contempla AUSENTE y ceros conforme a la rúbrica; RN17 exige la rúbrica histórica de la sesión. UC05, p.11, describe cerrar → detalle → cálculo según política aprobada → notificar, con estudiante/servicio de tiempo como actor. El documento `Entrega 1 Proyecto Nuclear Análisis de sistemas (1).pdf` (ruta real y huella en el inventario), p.6 y p.24/32, diferencia completa/parcial/ausencia y propone Strategy con calculador compartido, sin exigir un intento ficticio para quien no participó.

Estas fuentes y sus páginas exactas están en `FUENTES_ACADEMICAS.json` de esta fase. **RF24 no exige por sí solo Excel/PDF**: RF16 es la dependencia de exportación; verificar sus descargas no sustituye evaluar un intento parcial.

Decisiones posteriores documentadas:

- `FASE_8C_EVALUATION_INTEGRACION.md`, §1–2: respuestas de Diana Ma Valencia trasladadas por el usuario; preguntas pendientes al vencer con cero, escala 0–100, criterios iguales. La frase histórica sobre ausencia no autoriza copiar una nota previa.
- `RF13_RF24_MOTOR_PREGUNTAS.md`: regla posterior explícita por pregunta, puntajes docentes, rutas uniformes, ramas inaccesibles excluidas, Decimal y ROUND_HALF_UP únicamente al final. Parámetros técnicos definidos; no se vuelven a preguntar como si faltaran.
- `CIERRE_VOLUNTARIO_PARCIAL.md`: un FINALIZADO antes de FIN puede producir PARCIAL con denominador común; política versión 2, identificada como **propuesta técnica del equipo**.
- `EVALUATION_CICLO_ACADEMICO.md`: ausencia confirmada expresamente por docente, cero, sin intento ficticio; rectificación append-only; convocatoria retirada excluida de notas y conservada como antecedente. Publicación docente explícita e independiente.

La implementación de estas decisiones no constituye por sí misma una nueva aprobación académica del universo de rúbricas o del disparador de UC05. No se pide reconfirmar el cero o la confirmación docente ya establecidos funcionalmente.

## Actores, datos y contrato HTTP real

El cálculo lo ejecuta el servicio técnico, mediante orden explícita del DOCENTE autorizado sobre un intento existente FINALIZADO/VENCIDO. El estudiante registra sus respuestas y cierra; la autenticación no concede autoridad para calcular/publicar. La ausencia la confirma el DOCENTE con ámbito sobre sesión/caso/grupo/matrícula/convocatoria. Cuenta activa, rol vigente e identidades académicas se verifican desde PostgreSQL, no desde cabeceras de suplantación. No se conceden atribuciones adicionales a ADMINISTRADOR o DOCENTE ADMINISTRADOR.

Todos los siguientes endpoints están registrados en **app.main**, bajo `/scheduling`:

| Operación | Entrada y resultado real |
|---|---|
| POST `/sesiones/{s}/evaluacion/intentos/{i}/resultado-tecnico` | Sesión UUID e intento INTEGER positivo; sin body/query. 200 calcula o recupera idempotentemente un resultado técnico existente; nota Decimal como cadena, modalidad, versión/rúbrica, detalle exacto, `oficial=false`. No cierra ni publica |
| GET misma ruta | 200 resultado persistido, 404 si falta. No calcula ni escribe |
| POST `/sesiones/{s}/evaluacion/convocatorias/{c}/ausencia` | UUIDs y `{motivo}` no vacío (máximo 4000). 200 con id/revisión/confirmada/fecha/motivo, `nota="0.00"`, `oficial=false`. Exige sesión FINALIZADO, convocatoria ACTIVA del ámbito y ningún intento iniciado |
| POST misma base + `/ausencia/rectificacion` | `{id_confirmacion:UUID,motivo}`. Nueva revisión, no borra historia ni sustituye una publicación vigente |
| GET `/sesiones/{s}/evaluacion/consolidacion` | Pendientes, filas, retiradas y hash; no crea resultados ni confirma ausencias automáticamente |
| POST `/sesiones/{s}/evaluacion/publicaciones` | `{revision_sha256}` vigente; solo publica si toda la cohorte activa está resuelta y el docente autoriza. Operación separada |
| GET `/convocatorias/{c}/resultado` | Titular autenticado; visibilidad autorizada, sin explicaciones durante sesión activa. La lectura no calcula ni publica |

Errores reutilizados: 401 autenticación/cuenta, 403 rol o ámbito, 404 resultado inexistente, 409 intento activo/ausencia con intento/revisión o estado incompatible, 422 entrada inválida, 503 configuración o integración no acreditable. No se debilitan esos estados para obtener aserciones verdes.

Datos previos necesarios: cuenta/rol activo, vínculos INTEGER/UUID explícitos, grupo/matrícula/asignación, sesión/versionado/rúbrica, convocatoria propia y, para un parcial, intento y respuestas persistidos. La ausencia conserva convocatoria/estudiante/versión/docente/fecha/motivo/revisión; no inventa participación, consentimiento, intento, selección ni ruta futura.

## Brechas clasificadas antes de implementar

| Clase | Hallazgo | Decisión |
|---|---|---|
| Técnica solucionable | No se reprodujo un defecto funcional independiente de las decisiones pendientes. Las garantías existentes de cálculo, guardado, lectura, autorización, idempotencia y rollback pasan las pruebas nuevas de esta fase | Reutilizar, sin otra Strategy, endpoint o tabla |
| Cobertura de demostración | La carpeta Newman RF24 confirma ausencia/publicación, pero su resultado parcial está preparado antes del primer Send | No atribuir a esa carpeta la ejecución del cálculo. Acreditarlo con pytest HTTP/main y declarar exactamente la preparación LAB |
| Académica compartida con RF13 | El escritor nuevo requiere PREGUNTAS_100_V1; no hay política general explícita para interpretar otras rúbricas históricas válidas | Confirmar alcance evaluable o aportar el mapeo/agregación de las otras reglas. No convertir niveles ni recalificar historia |
| Académica compartida con UC05 | El cálculo parcial ocurre por orden docente posterior; UC05 vincula el recorrido al cierre estudiantil/servicio de tiempo | Conciliar ese disparador, sin deducir una obligación de transacción HTTP única ni automatizar finish/worker |
| Académica de incompletos voluntarios | Política v2 está identificada como propuesta técnica del equipo | Confirmar su adopción académica para aceptación integral; no atribuir aprobación a la profesora |
| Externa | RF24 no necesita correo para calcular/persistir. El envío externo de RF20/21 es otro contrato | No bloquear artificialmente el cálculo por SMTP ni presentar avisos internos como correo |

## Matriz de aceptación y código reutilizado

| Criterio | Implementación/prueba existente ejecutada ahora | Resultado y límite |
|---|---|---|
| Parcial vencido y respuestas conservadas | `EvaluacionParcialStrategy`, `preparar_calculo_historico`, `CalculadorRubrica.calcular_preguntas`; `test_question_scoring.py::test_postgresql_vencido_denominador_completo_sin_respuestas_ficticias` | 0 respuestas → 0.00; 1/2 con 100 → 50.00; sin INSERT de selecciones pendientes |
| Cierre HTTP y cálculo posterior | `test_teacher_technical_evaluation.py::test_finish_http_independiente_seguido_calculo_docente[0-True-activo]` | JWT real/main: registra respuesta, reloj de laboratorio alcanza vencimiento, finish devuelve VENCIDO sin resultado; POST docente devuelve PARCIAL 33.33, GET/reintento mismo resultado. No publicación automática |
| Ramas, denominador y precisión | `ConfiguracionPreguntas`; `test_question_scoring.py::test_ramas_excluidas_no_penalizan_y_no_se_eligen_al_vencer`; `test_question_result_storage.py::test_tercio_exacto_vencido_sin_redondear_contribucion` | Denominador común validado, ninguna ruta futura inventada; fracciones exactas, redondeo solo final |
| Voluntario incompleto | `test_voluntary_partial_http.py` y clasificador versionado | PARCIAL, pendiente por cantidad cero; original cerrado inmutable. Técnico acreditado; adopción académica de propuesta pendiente |
| Ausencia expresa | `CicloAcademicoSQL.ausencia`; `test_academic_cycle_http.py::test_ausencia_explicita_sin_participacion_ni_intento_rectificacion_historica` | 200/0.00/no oficial, replay mismo id, no nuevas P/I, rectificación revisión 2, última publicación no se borra |
| Ceros por decisiones sin intento | `EvaluacionAusenciaStrategy`; `test_evaluation_domain.py::test_ausencia_genera_ceros_por_decision_sin_intento_ficticio` | Prueba de dominio: cero por decisión aplicable, sin selección. La API de ausencia conserva cero agregado y referencia histórica; no afirmar que Newman haya creado detalle de preguntas de una ruta no recorrida |
| Ausencia no inferida y conflicto con intento | `test_academic_cycle_http.py::test_ausencia_concurrente_y_negativa_con_intento` | Dos confirmaciones concurrentes: mismo id/una fila; con intento existente:409. Cohorte sin confirmar impide publicar |
| Autorización, historia, lectura y rollback | `test_teacher_technical_evaluation.py`, `test_question_result_storage.py`, `test_main_technical_results.py`, `test_academic_cycle_http.py` | Rechazos de ajenos, versión histórica, SQL independiente, rollback, idempotencia, no DML en GET. No se afirma que Newman inyecte esos fallos SQL |
| RF14 preservado | `test_rf14_student_results.py`, 13 casos de la relacionada | Privacidad y feedback histórico; GET sin resultado404 sin calcular; sesión activa sin divulgación anticipada |
| Alcance integral | Documentación Fase8 y guard de `cases/infrastructure/scoring.py` | Sigue pendiente la aplicabilidad de otras rúbricas y el disparador académico. Los controles 503/409 no equivalen a aceptación integral |

La matriz nominal complementaria está en `evidencias/rf24_fase9_20261110/MATRIZ_CRITERIOS_RF24.csv`, con IDs pytest y evidencias originales.

## Ejecuciones nuevas y evidencia SQL

| Ejecución de esta fase | Resultado |
|---|---|
| Focal: ciclo académico, scoring, voluntario parcial y dominio Evaluation | **116 aprobadas**, 0 omitidas/fallos/errores; 142.31 s |
| Relacionada: siete archivos de integración, incluido RF14 | **180 aprobadas**, 0 omitidas/fallos/errores; 349.24 s |
| Newman RF24 maestra | **18 solicitudes / 62 aserciones**, cero fallos técnicos; RF sigue BLOQUEADO |
| Newman de las 17 carpetas acreditadas | **314 solicitudes / 1145 aserciones**, cero fallos; las 17 conservan APROBADO en el alcance documentado |

Las suites pytest se solapan: **no sumar 116+180**. Tampoco son una nueva general. La general 2538/38 es histórica. En cada ejecución pytest aparece la advertencia conocida Starlette/httpx; no se oculta. Las carpetas Newman tienen laboratorio nuevo individual, JWT reales y verificaciones SQL. Ninguna ejecución usa .env ni URL permanente.

Newman RF24 usa únicamente URLs de **app.main**. Su preparación administrativa y el intento parcial/resultado previo son **fixtures LAB**, no una demostración de alta/inicio productivo ni de cálculo por el primer Send. SQL independiente:

- Antes: 1 participación, 1 intento, 1 respuesta, 1 resultado técnico, 0 publicaciones.
- Después: mismos P/I/respuesta/resultado; **1 ausencia confirmada y 1 publicación explícita**, PostgreSQL **17.11**. No se crearon intentos ficticios.
- XLSX/PDF descargados y verificados por el ejecutor existente; son evidencia auxiliar de publicación autorizada en LAB, no una aprobación nueva de RF16.

Archivos originales: `focal/` y `relacionada/` (comando, huellas, consola.log, JUnit, resultado.json); `newman_rf24/` (resultado.json, junit.xml, descargas), `newman_rf24_consola.log`; `regresion_17/RF-xx/` y logs individuales. `RESUMEN_EJECUCION.json` concilia resultados. No se ejecutó Postman Desktop ni se fabricaron capturas. La regresión nueva cubre los 17 acreditados; los otros nueve bloqueados distintos de RF24 **no se reejecutaron** ni se reclasificaron.

Comandos ejecutados desde la raíz; al repetir, utilizar destinos de evidencia nuevos:

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf24_fase9_20261110/run.py --modo focal --evidencias evidencias/rf24_fase9_20261110/focal
.\.venv\Scripts\python.exe -B evidencias/rf24_fase9_20261110/run.py --modo relacionada --evidencias evidencias/rf24_fase9_20261110/relacionada
$runtimeRf24 = Get-Content evidencias/postman_desktop_20261108/newman_runtime.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-24 --newman (Join-Path $runtimeRf24.ruta 'node_modules/newman') --evidencias evidencias/rf24_fase9_20261110/newman_rf24
```

La misma última orden se ejecutó para RF01/02/05/06/07/08/09/11/14/15/16/17/18/19/22/26/27, con destino `regresion_17/RF-xx` y log individual. Son las carpetas cuyo contrato no tiene bloqueo, no una selección posterior para ocultar fallos. Se comprobó limpieza de los laboratorios y ausencia de contenedores activos al finalizar.

## RF20/RF21 como alternativas y decisión final

Se evaluaron sus fuentes originales y `crear_convocatoria.py`, `convocation_management.py`, `crear_notificacion.py` y contratos Postman:

| Candidato | Disponible | Dependencia concreta |
|---|---|---|
| RF20, código individual | Código aleatorio por convocatoria, solo hash persistido, entrega en claro una sola vez al invocador autorizado, validación real y revocación por retiro | La entrega segura al estudiante no está completada. No se puede reconstruir el código desde su hash para un envío posterior |
| RF21, convocatoria y cambios | Alta/retiro autorizados, avisos INTERNA y rollback; el mensaje incluye caso/horario/mensaje personalizado | El requisito exige correo con URL/código. No hay adaptador/proveedor/remitente/URL institucional y contrato de recuperación del envío configurados. Un aviso INTERNA no satisface ese correo |

No se implementan estos otros requisitos ahora. Siguiente alternativa priorizada: **cerrar el contrato de entrega RF20/RF21**, indicando canal/proveedor/remitente/URL autorizados y cómo recuperar un fallo de envío sin guardar el código en claro ni invalidarlo implícitamente. Con esa decisión se podrá integrar un recorrido verificable reutilizando convocatorias y notificaciones; no se afirma que sea un incremento actualmente libre de dependencias.

Preguntas de cierre RF24: ¿se acepta el comando docente posterior de RF13/UC05? ¿Se limita la evaluación a nuevas versiones PREGUNTAS_100_V1 con conservación del legado, o qué otras rúbricas válidas deben calcularse? ¿Se adopta académicamente la política v2 para el voluntario incompleto? No crear otra fórmula ni automatizar el cierre para resolverlas por código.

**RF24: BLOQUEADO integralmente, capacidades técnicas verificadas.** Matriz de aceptación: **17 APROBADOS / 10 BLOQUEADOS**; RF03/04/10/12/13/23/25 conservan su estado. No hay nueva corrección productiva ni nuevas pruebas artificiales. Se actualiza únicamente la documentación/trazabilidad de RF24, con propuesta de checkpoint documental explícita; no se crea un commit adicional. Se detiene la implementación dependiente de las decisiones pendientes.
