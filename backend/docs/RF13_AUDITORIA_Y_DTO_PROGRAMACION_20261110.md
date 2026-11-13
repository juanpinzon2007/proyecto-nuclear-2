# Fase 6 — RF-13 y compatibilidad del DTO de programación

10 de noviembre de 2026, America/Bogota. Auditoría dirigida y ejecución real, sin cambios productivos ni nuevas reglas académicas.

## Estado inicial comprobado y preservación

Rama codex/participation-inicio-main-20261109; HEAD 8e1e8a67f6e4ba387b9d0650059e6fe654c704d9. Índice vacío; ocho modificaciones rastreadas: los siete cambios anteriores más los blancos de worker_runner.py. 3106 archivos sin seguimiento al comenzar. Cuatro worktrees existentes inventariados, ninguno cambiado ni creado. El checkpoint RF04 existe y no se altera.

Se verificaron los archivos del respaldo privado nuclear_rf04_20261110T224945Z y su delta Fase5; .env, stash, referencias y las huellas previas se conservan. PRESERVACION_INICIAL.json registra el estado sin incluir credenciales. El contrato RF04 propuesto permanece intacto. No hay commit, push, pull, merge, checkout, cambios de esquema ni conexión a bases permanentes en esta fase.

## Contrato académico exacto

Fuente original: _referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf, p.4:

> RF-13: El sistema calcula y almacena la calificación de cada intento a partir de las respuestas y de la rúbrica asociada.

RN17, p.7, exige la rúbrica de la versión del caso utilizada en la sesión. UC05, p.11, tiene como actor al estudiante con participación En curso o al servicio de cierre por tiempo. Describe cerrar → detalle por pregunta → calcular según política aprobada → notificar, con nota/estado/horas/feedback persistidos y rechazo de duplicación ante reintentos.

RF13 no equivale a publicar oficialmente ni exige por sí solo reportes, una selección de mejor intento, un umbral de aprobación o un proveedor de correo. No se convierten RF14/16/24/25/27 en condiciones artificiales para afirmar que el cálculo técnico funciona. Tampoco se deduce de las flechas de UC05 una única transacción HTTP o permiso para revertir un cierre previamente confirmado.

Entradas académicas: intento y respuestas persistidas, rúbrica/versionado de la sesión y política aplicable. Salidas: nota y detalle persistidos, reproducibles y no duplicados. El actor que dispara el cálculo es un punto de conciliación: el endpoint existente es una orden DOCENTE posterior al cierre; no se llama desde finish ni worker por decisiones técnicas posteriores expresas.

Las páginas originales y su SHA-256 están en evidencias/rf13_fase6_20261110/FUENTE_ACADEMICA.json. FUENTES_IMPLEMENTACION.json conserva huellas de los componentes y documentos inspeccionados.

## Decisiones posteriores: qué está resuelto

| Fuente / alcance | Regla efectivamente definida | Estado verificable |
|---|---|---|
| Respuestas de la profesora registradas en FASE_8C_EVALUATION_INTEGRACION.md | Una selección por pregunta; escala 0–100; criterios iguales; pendientes al vencer cero | No se limita el número de alternativas ni se infiere una fórmula de ausencia de una frase ambigua |
| Instrucción expresa del incremento RF13/RF24, registrada en RF13_RF24_MOTOR_PREGUNTAS.md | Puntaje docente explícito por alternativa/pregunta, igual peso, promedio simple, ramas inaccesibles excluidas, rutas uniformes, Decimal, ROUND_HALF_UP final | Implementada como PREGUNTAS_100_V1; no volver a preguntar el método de redondeo como si siguiera técnicamente indefinido |
| Misma instrucción y ConfiguracionPreguntas.validar | Correspondencias inequívocas; igualdad de perfiles por criterio; una pregunta no cuenta varias veces por tener varios criterios | Implementada, con errores explícitos ante configuración incompleta o incompatible |
| Persistencia exacta posterior | Una cabecera canónica y detalle por pregunta/criterio con fracciones exactas | Implementada; no existe hoy el impedimento histórico que obligaba a inventar niveles discretos |
| CIERRE_VOLUNTARIO_PARCIAL.md y descriptor de política versión 2 | Cierre voluntario incompleto: PARCIAL, denominador uniforme, pendientes por cantidad cero | Propuesta técnica del equipo implementada y versionada; no se atribuye aprobación institucional a la profesora |
| CIERRE_TECNICO_EVALUATION.md, seguido por CIERRE_VOLUNTARIO_PARCIAL.md | Cierre y cálculo explícito docente en transacciones distintas; reintento no repite cierre | Implementado. Las afirmaciones anteriores «sin persistencia», «sin endpoint» o «voluntario siempre rechazado» son históricas |

El contrato propuesto de Evaluation del 7 de noviembre conserva cuestiones que después resolvieron instrucciones expresas de implementación. Su mera existencia no permite declarar que todas sigan pendientes. A la inversa, que una implementación exista no acredita por sí sola la adopción académica institucional de esa política.

## Implementación reutilizable y persistencia

| Componente real | Responsabilidad |
|---|---|
| application/evaluation_service.py::seleccionar_estrategia y Strategies existentes | COMPLETA/PARCIAL/AUSENCIA; el flujo por preguntas reutiliza las estrategias, sin motor paralelo |
| domain/calculador_rubrica.py::CalculadorRubrica.calcular_preguntas | Suma Decimal y denominador completo; redondea solo la nota final |
| cases/application/scoring.py::ConfiguracionPreguntas; infrastructure/scoring.py | Lee el grafo y valoraciones de la versión histórica; valida rutas, criterios y puntajes; no interpreta otra regla como PREGUNTAS_100_V1 |
| question_evaluation.py::preparar_calculo_historico | Clasificación, parámetros efectivos y procedencia/hash reproducibles, incluyendo versión 2 para voluntario incompleto |
| teacher_evaluation.py::EvaluadorTecnicoDocente | Revalida ámbito SQL, estado cerrado e identidad en UoW; calcula/persiste o recupera idempotentemente |
| result_repository.py y question_result_repository.py | Cabecera canónica resultado_intento; validación histórica y detalle exacto, sin sustituir resultados de otro motor |
| teacher_result.py y technical_results.py | Lectura docente privada y serialización Decimal/fracciones como cadenas |

Tablas: resultado_intento, resultado_calculo_preguntas, resultado_pregunta y resultado_criterio_exacto; resultado_criterio histórico continúa legible. Se conserva caso/versión/rúbrica/política y sus huellas; los pendientes se cuentan sin filas ficticias de respuesta. UNIQUE(id_intento), FK, checks y triggers mantienen referencias y aritmética histórica. La autorización del actor es una garantía de aplicación/UoW; no se presenta como una ACL de PostgreSQL para SQL arbitrario.

La escritura usa PostgreSQL READ COMMITTED, locks de ámbito y P→I, y una sola cabecera. El cierre previo no se deshace si el cálculo posterior falla. Un commit confirmado seguido por una lectura/respuesta fallida se recupera mediante POST/GET; no se promete entrega HTTP exactamente una vez. No se recalifican ediciones históricas ni se actualiza una nota oficial al calcular.

## HTTP realmente registrado en app.main

El router principal incluye Scheduling; este incluye technical_results. Ruta base:

`/scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico`

- POST: 200 al calcular o recuperar el mismo resultado; sin body ni query. UUID de sesión e INTEGER positivo de intento. El cliente no suministra nota, rúbrica ni política.
- GET: 200 para resultado existente; 404 si todavía no existe. No calcula ni cierra el intento y conserva lectura sin DML.
- JWT real, cuenta activa, DOCENTE vigente, identidad académica y ámbito sobre sesión/caso/grupo/matrícula/convocatoria/participación/intento. No se conceden privilegios nuevos a ADMINISTRADOR o DOCENTE ADMINISTRADOR.
- 401 autenticación/cuenta; 403 ámbito/rol; 409 intento abierto/conflicto o resultado incompatible; 422 entrada; 503 configuración/persistencia no acreditadas. Cache-Control:no-store.
- Salida: id_resultado y referencias históricas, modalidad, cantidades, nota Decimal, preguntas y detalle exacto, fecha/hash, ambito TECNICO o LABORATORIO histórico, oficial=false. No implica publicación.

## Aceptación nueva y brechas exactas

| Criterio | Evidencia nueva | Conclusión |
|---|---|---|
| Escala, igualdad de peso, tercios y redondeo | test_question_scoring.py, incl. test_decimal_peso_unico_sin_redondeo_intermedio | Acreditado para la configuración explícita soportada |
| Ramas excluidas, pendientes y versión histórica | test_question_scoring.py y test_teacher_technical_evaluation.py | Acreditado; no inventa ruta futura ni selecciona la última edición |
| Escritura y lectura desde otra Session, integridad y compatibilidad | test_question_result_storage.py y test_main_technical_results.py | Acreditado, sin niveles ficticios |
| Idempotencia, concurrencia, SQL fallido y reintento | test_teacher_technical_evaluation.py; test_voluntary_partial_http.py | Acreditado; cierre conservado, una cabecera y ninguna publicación automática |
| Actor y privacidad HTTP | mismas pruebas + Newman RF13 | Acreditado para el comando docente y titularidad persistente |
| Cálculo para una rúbrica histórica distinta | test_configuracion_historica_no_se_reinterpreta[...False] | 503 sin resultado; con resultado de motor previo, 409 para no sustituirlo. No hay un mapeo académico general autorizado para convertir esas rúbricas |
| Flujo académico UC05 frente al disparador actual | Fuentes y código: finish/worker no invocan al evaluador | Necesita conciliación expresa: mantener el comando docente o autorizar otra orquestación. No se activa automáticamente por deducción |
| Alcance completo de rúbricas/grafos | La configuración nueva es opt-in; una pregunta por escena, sin ciclos alcanzables, rutas uniformes | Definir el alcance académico admitido o las reglas necesarias para ampliarlo. No se exige unilateralmente soportar ciclos no aprobados |

**Veredicto: RF13 técnico demostrado en el alcance PREGUNTAS_100_V1; RF13 integral permanece BLOQUEADO.** El motivo no es simplemente «no hay un acta firmada» ni que falte publicar notas. Falta cerrar la aplicabilidad académica y cobertura de rúbricas válidas fuera del opt-in, así como conciliar el flujo UC05 con el comando posterior autorizado. No se cambian reglas ni se fuerza otra fórmula para obtener APROBADO.

No se implementó código productivo: no apareció un defecto que pudiera corregirse sin cambiar esos contratos. Rechazar una configuración incompleta/legada es una protección, no un fallo que deba convertirse en un puntaje inventado. Tampoco se impone retroactivamente la nueva regla a versiones inmutables.

## Auditoría independiente del DTO de programación

ProgramarSesionRequest declara siete campos: espacio_academico_id, version_caso_id, fecha_inicio, fecha_fin, tiempo_maximo_minutos, lugar y mensaje_personalizado. No configura extra='forbid'; Pydantic ignora las claves no declaradas. Se reproduce mediante HTTP/main/JWT/PG17, no solo model_validate.

Seis casos observados: asignacion_academica mal formada; estudiantes_ids inválidos; docente_id ajeno; estado e intentos_base; fecha_limite_ingreso e id_grupo; campo_desconocido=null. **Todos devuelven 201 y crean solo S**, sin crear A ni C. La identidad persistida sigue siendo el docente JWT y S permanece SIN_INICIAR: no se demostró escalamiento de privilegios. El riesgo es que un cliente atribuya efectos al bloque ignorado; la respuesta actual solo acredita programación, no asociación.

Dos controles adicionales: tiempo_maximo_minutos=0 → 422; petición estudiantil → 403. Ambos antes de DML/commit y sin variar conteos. **No existe un rechazo 422 actual por extras**; no se declara que ese comportamiento ya esté implementado ni aprobado.

Inventario: 12 colecciones versionadas, 25 solicitudes POST de programación (en Proyecto_Nuclear_main y la maestra 27RF); todas contienen únicamente claves declaradas, sin bodies variables pendientes de resolver. CONSUMIDORES_DTO.json conserva las rutas y claves, sin secretos. Se localizaron también 25 archivos Python/JS candidatos en CONSUMIDORES_PYTHON.json. No hay cliente TypeScript versionado en este checkout; no se certifican consumidores externos ni ramas de compañeros.

En las fuentes revisadas no se encontró una orden específica de rechazar todo campo adicional. El OpenAPI/DTO vigente tampoco lo declara. La validación de fechas, duración, caso publicado y permisos no equivale a un contrato extra='forbid'.

Propuesta para el responsable de API: aprobar explícitamente endurecer este DTO con ConfigDict(extra='forbid'), documentar el 422 y comprobar los clientes antes de desplegar. Las 25 solicitudes conocidas no necesitan extras, pero eso no garantiza compatibilidad universal. Otra opción es introducir DTO estricto solo en una composición nueva expresamente versionada. **Ambas quedan sin implementar.** Ninguna permite introducir asignaciones RF04 mediante campos ignorados.

## Ejecuciones nuevas y límites de la evidencia

Evidencia: evidencias/rf13_fase6_20261110/. Cada ejecución conserva consola.log, JUnit y resultado.json; comandos/HEAD/huellas en ejecucion.json. Runners deshabilitan .env y URLs externas, crean PostgreSQL17 nuevo y limpian solamente sus contenedores. No se usó Postman Desktop; Newman ejecutó los scripts reales de la colección.

| Ejecución | Resultado nuevo |
|---|---|
| Focal RF13: test_question_scoring.py, pruebas puras y PostgreSQL | 39 aprobadas, cero omisiones/fallos/errores |
| Relacionada: almacenamiento, HTTP docente, lectura privada y cierre parcial | 108 aprobadas, cero omisiones/fallos/errores |
| Diagnóstico DTO HTTP: test_dto_probe.py, fuera de la suite productiva | 8 observaciones verificadas, cero omisiones/fallos/errores; no son aprobación de ignorar extras |
| Newman RF13 de la maestra | 32 solicitudes / 141 aserciones, cero fallos técnicos; 28 main y cuatro LAB |

SQL independiente de Newman: PostgreSQL17.11, una participación, un intento, dos respuestas, **un resultado y cero publicaciones**. Cuentas/asignaciones/matrículas son preparación LAB; consentimiento/inicio positivos usan su aplicación LAB. El POST y GET de resultado técnico sí se ejecutan sobre main. Un 503 no se contó como aceptación integral.

Se conserva un tipo de advertencia conocido Starlette/httpx. No sumar ejecuciones solapadas. La general 2525/38 es histórica comprobada, no nueva. No se repitieron la general ni las otras 26 carpetas: no hubo cambios productivos o de contratos compartidos que lo exigieran. No se afirma una regresión nueva de los 16 RF por estas ejecuciones focales.

Comandos ejecutados desde la raíz (usar destinos nuevos al repetir):

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf13_fase6_20261110/run.py --modo focal --evidencias evidencias/rf13_fase6_20261110/focal
.\.venv\Scripts\python.exe -B evidencias/rf13_fase6_20261110/run.py --modo relacionada --evidencias evidencias/rf13_fase6_20261110/relacionada
.\.venv\Scripts\python.exe -B evidencias/rf13_fase6_20261110/run.py --modo contratos_actualizados --evidencias evidencias/rf13_fase6_20261110/dto_http
$runtime = Get-Content evidencias/postman_desktop_20261108/newman_runtime.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-13 --newman (Join-Path $runtime.ruta 'node_modules/newman') --evidencias evidencias/rf13_fase6_20261110/newman_rf13
```

## Decisiones y continuidad RF14

1. Confirmar qué rúbricas/reglas se admiten académicamente para RF13: adoptar el alcance explícito PREGUNTAS_100_V1 o aprobar el mapeo/agregación de las demás. No volver a inventar ni a presentar como pendientes técnicos la escala, pesos y ROUND_HALF_UP ya definidos para esa regla.
2. Conciliar UC05 con el disparador docente explícito y sus transacciones separadas. No automatizar finish/worker ni sustituir un cierre confirmado sin autorización.
3. Confirmar el alcance de recorridos y el tratamiento académico del voluntario incompleto, que conserva su procedencia de propuesta técnica. Las decisiones de varias preguntas/ciclos siguen siendo compartidas con RF10; no se resuelven aquí.
4. Por separado, el responsable de API debe decidir la compatibilidad de rechazo de extras; no es una fórmula académica que deba inventar el backend.

RF14 ya tiene GET /scheduling/convocatorias/{convocatoria_id}/resultado, visibilidad configurable y condiciones de privacidad en CicloAcademicoSQL.estudiante. El siguiente incremento debe verificar ese flujo existente, no crear otro: titular frente a ajeno, visibilidad apagada, intento activo, resultado provisional no oficial, sesión activa sin explicaciones y sesión finalizada con feedback permitido. Contrastar aciertos/errores/explicaciones con el RF14 original y la restricción posterior de no divulgar correctas durante sesión activa. No confundir aprobar RF13 técnico con aprobar toda esa divulgación.

Estado de los 27 RF: se conservan las 16 aprobaciones y 11 bloqueos de la matriz de aceptación previa. No se reclasifica ninguno por escribir este informe. RF03/RF04/RF10 y RF12/RF23/RF25 conservan sus límites. No hay nuevas rutas ni cambios a la colección, puntuación, ORM, migraciones, .env o bases permanentes.
