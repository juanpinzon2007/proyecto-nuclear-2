# Cierre confirmado y evaluación técnica explícita

## Protección y alcance

Checkpoint local `3aa1c160a02633722572f4e994ef38312c1a8b1f`, padre
`6fcbea054d0f141e3e245d0198ae5336273f824e`. Diecisiete rutas verificadas contra el
manifiesto anterior (11 modificadas y seis nuevas), hashes y resultados acreditados,
sin evidencias o secretos preparados. No hay otro commit ni publicación en esta etapa.

El incremento reutiliza PREGUNTAS_100_V1, estrategias COMPLETA/PARCIAL, calculador,
configuración del grafo, UoW, repositorio canónico y detalles exactos. No modifica
ORM, Alembic, puntuación, grafo, finish ni worker. No hay tareas automáticas nuevas.

## Contrato HTTP y autorización

POST `/scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico`
está en app.main por el router Scheduling. Sin cuerpo ni query: el cliente no puede
suministrar nota, rúbrica, estudiante, política o versión. Devuelve 200 tanto al
crear como al recuperar idempotentemente. Reutiliza la representación del GET:
Decimal y fracciones como cadenas, referencias históricas, fecha y hash,
`ambito=TECNICO`, `oficial=false`. Nunca una nota publicada.

401 JWT/cuenta; 403 rol o ámbito; 409 intento abierto, resultado existente de otro
motor o conflicto transaccional recuperable; 422 cuerpo/query/ruta inválidos;
503 configuración, motor o SQL no disponibles. Cache-Control:no-store. No se
expone la excepción SQL, credenciales, código de política ni información ajena.

JWT real y DOCENTE vigente en PostgreSQL. Reutiliza AmbitoFeedbackIndividual
solo para su autorización transaccional (no escribe feedback): participación,
cuenta/rol/vínculos, grupo/matrícula, convocatoria, asignación, sesión y creador.
No fabrica un ContextoAcceso del alumno para actuar como él. Comprueba el intento
y la sesión de la URL y reutiliza las verificaciones conservadoras de preparación.
Las referencias caso/versión se leen protegidas contra modificaciones concurrentes.
No concede atribuciones a ADMINISTRADOR ni DOCENTE ADMINISTRADOR por suposición.

## Secuencia y transacciones

1. El estudiante cierra mediante el finish existente y su commit independiente.
2. El docente invoca POST explícitamente. Se abre otra UoW READ COMMITTED nueva.
3. Se adquieren los locks del ámbito existente; repositorio de Participation
   mantiene P -> I y vuelve a leer el intento. Solo FINALIZADO/VENCIDO son elegibles.
4. Si existe un resultado TECNICO de la regla, se verifica y recupera, sin llamar
   al preparador de resultados nuevos. Un LAB anterior no se sustituye (409).
5. Si falta, la edición asignada proporciona grafo/puntajes/rúbrica. Se ejecutan
   estrategias y calculador existentes, y se guarda una sola cabecera con detalles.
6. Un commit confirma solo Evaluation. Otra Session READ ONLY recupera y valida el
   resultado para devolverlo mediante el mismo lector docente del GET.

No hay llamada automática desde finish, GET ni worker. Si falla antes del commit,
rollback elimina la escritura parcial de Evaluation; no puede deshacer el cierre
confirmado por otra transacción. Si el commit tuvo éxito pero la lectura/respuesta
falla, el resultado permanece: reintentar POST/GET devuelve el mismo ID, fecha y
hash. No se promete entrega de respuestas HTTP exactamente una vez.

P -> I, autorización bloqueada, UNIQUE(id_intento), guards y procedencia inmutable
conservan una cabecera. Dos POST concurrentes recuperan el mismo resultado. Un
conflicto 409 por deadlock/serialización exige reintentar la operación; no se repite
la transición de cierre. La comprobación histórica puede reproducir el cálculo
para validarlo, sin recalificar con otra edición ni escribir una nota nueva.

No se generan notificaciones de calificaciones. El worker conserva solo sus efectos
propios de estado/auditoría/aviso de sesión. La competencia worker/evaluación se
prueba con PostgreSQL real, sin convertir el worker en motor académico.

## Límites reales

Un FINALIZADO voluntario sin FIN puede existir por el contrato vigente de cierre.
El motor COMPLETA lo rechaza (503) conservando cierre y ausencia de resultado: no
lo reclasifica arbitrariamente ni inventa ceros o una rama futura. VENCIDO aplica
la estrategia PARCIAL autorizada y denominador inequívoco. Una edición sin
PREGUNTAS_100_V1/configuración completa sigue cerrada y requiere resolución de
configuración/contrato; repetir no hace válido un dato incompleto. No se reescribe
una edición publicada para superar ese bloqueo.

Los resultados históricos LAB siguen legibles mediante GET dentro de su contrato;
POST no los convierte ni reemplaza. No se recalifica historia automáticamente.
La autorización conservadora del GET revisa toda la sesión; una incoherencia en
otra fila puede impedir devolver un resultado confirmado hasta resolverla.

## Validación y evidencia

Aceptación corregida: 24 aprobadas, sin omisiones/fallos/errores, advertencia conocida
Starlette, 41.68 s. Se añadió después la comprobación de edición posterior; resultados
finales: **346 aprobadas** focalizadas/relacionadas, 0 omitidas/fallidas/errores,
una advertencia conocida, 283.29 s. Incluye las 25 nuevas. Laboratorio TCP: 13/13
solicitudes guardadas, estados [200,200,200,404,200,200,200,401,401,403,403,409,422],
una sola cabecera insertada, cierre preservado y cero escrituras en GET/reintento.
Validación estática: 43 operaciones, 256 scripts con sintaxis JS y nueve comprobaciones
HTTP sin SQL. NO ejecución de pm.test.

General final: **2416 aprobadas, 38 omitidas, 0 fallidas, 0 errores**, una advertencia
conocida Starlette, 1411.03 s; 2454 casos JUnit. Incluye las 25 nuevas. Las 38
omisiones conservadas requieren configuración externa (29 Identity, 3 conexión y
6 laboratorio independiente); ninguna aceptación nueva omitida. No sumar suites
solapadas. Fuentes sin cambios durante pytest; solo se generó el JSON BD2-04 previsto.
No quedaron contenedores propios activos ni detenidos bajo la etiqueta de laboratorio.
Las cifras 2391/38 pertenecen al incremento anterior, no a esta ejecución.
Evidencia local: `evidencias/cierre_tecnico_evaluation_20261107/`.
Focal: `pruebas_focal_20261108T021240Z/`; general:
`pruebas_total_20261108T022052Z/`. Fin general UTC 2026-11-08 02:44:41,
fecha local Bogotá 7 de noviembre de 2026. Logs completos, JUnit nominal,
fuentes/HEAD, aceptación TCP y validaciones estáticas en carpetas separadas.
Inventario final con rutas, tamaños y SHA-256: `MANIFIESTO_INCREMENTO.json`.

Se conservan fallos iniciales: referencia errónea id_sesion en el handler nuevo,
corregida a sesion_id. Las inyecciones SQL se adaptaron para pasar por SQLAlchemy
con el mismo SELECT 1/0 real, en lugar de lanzar la excepción cruda desde un cursor
en un hook; mantienen las aserciones de 503, rollback y estado cerrado sin cambios.
No hay skip/xfail nuevo ni relajación de condiciones de negocio.

## Postman y sustentación

Colección nueva: `postman/Proyecto_Nuclear_evaluacion_tecnica.postman_collection.json`.
Trece solicitudes, junto al Environment existente sin secretos. Node comprueba
sintaxis y la estructura se contrasta con OpenAPI; eso NO es ejecutar pm.test.
No se atribuyen aprobaciones del Runner si no se ejecutó realmente.

PowerShell interactivo desde la raíz:

```powershell
.\.venv\Scripts\python.exe -B backend\docs\postman\laboratorio_resultados_tecnicos.py --puerto 8765 --sin-evaluar
```

Solo PostgreSQL17 NUEVO. Ingrese clave/código sintéticos en la entrada oculta.
El cierre VENCIDO de la demostración se prepara mediante fixtures administrativas;
las pruebas Python acreditan aparte finish HTTP real y respuestas por ambas ramas.
No se presenta la preparación SQL como un inicio docente productivo.

Importe colección/Environment y copie las referencias sintéticas impresas a valores
locales; complete clave_docente y codigo_estudiante. Establezca
laboratorio_confirmado=true y permitir_escrituras_laboratorio=true SOLO para este
laboratorio. Los tokens se obtienen por login real en el Runner; no exporte el
entorno usado ni capture respuestas de login o Authorization. Para repetir toda la
secuencia desde GET404, cierre y reinicie el laboratorio propio; no borre resultados.

Capturas y explicación:
- Tras login, GET al intento cerrado: 404. «Cerrar no calcula automáticamente».
- POST sin cuerpo: 200, nota_final="33.33", modalidad=PARCIAL, oficial=false,
  versión histórica y aportes 50/3 + 50/3. «Promedio uniforme, sin redondeo intermedio».
- Repetir POST: 200, mismos id_resultado/fecha_calculo/procedencia_sha256.
  «Recupera un resultado confirmado, no crea otro».
- GET posterior: 200 con el mismo resultado. «Persistencia y consulta separadas».
- POST para intento_sin_resultado_id (activo): 409. «No se evalúa un intento abierto».
- Estudiante/docente ajeno: 403; sin JWT/JWT inválido:401; cuerpo con nota:422.
  «El cliente no decide la nota ni el ámbito».
- Capture Test Results solo después del Runner real. Ocultar cabeceras/tokens.

Enter en la consola detiene servidor y elimina únicamente su contenedor. El caso
sintético adicional con permiso de repetición es preparación LAB ya existente,
no habilitación productiva de RF-25. No se toca el recorrido LAB anterior.

## Cobertura y estabilización

RF-13/RF-24 siguen PARCIAL a nivel de requisito completo: el tramo técnico explícito
es invocable por HTTP, pero no consolida/publica, no confirma/rectifica ausencias
ni resuelve el cierre voluntario incompleto por una regla nueva. RF-14, RF-16 y
RF-25 conservan sus dependencias de visibilidad, publicación/consolidación y
agrupación/autorización de repeticiones. Ninguna calificación oficial habilitada.

Para el lunes: congelar este contrato técnico tras revisión, ensayar la colección
en un laboratorio nuevo y conservar logs/JUnit/manifest; mantener cerrada la
publicación oficial y obtener las decisiones académicas restantes por separado.
No ampliar algoritmos ni alterar el cierre para ocultar escenarios no evaluables.


## Estado Git y preservación

Rama feature/backend-continuidad; HEAD 3aa1c160a02633722572f4e994ef38312c1a8b1f,
único checkpoint local autorizado. Implementación posterior SIN COMMIT, índice
vacío. Ningún push, merge ni PR. `git diff --check` aprobado. .env, stash, otras
ramas, respaldos y archivos históricos conservados. No cambió ninguna migración,
modelo, calculador, finish ni worker. No se tocaron bases permanentes. La API está
registrada en el candidato local y acreditada en laboratorio; no constituye un
despliegue en GitHub ni en la base persistente del equipo.
