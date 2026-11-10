# RF-10: contrato de navegación para Angular

## Alcance y aceptación antes de validar

Reutilizar main, Facade, SQL y grafo existentes. Demostrar dos ramas soportadas, recarga sin estado de cliente, primera selección inmutable, progreso, FIN y cierre; reusar negativas/concurrencia/rollback ya existentes. Los GET no persisten el vencimiento; un POST vencido sí puede confirmarlo y responder 409. No se modifica ese comportamiento. El único cambio productivo previsto es declarar en OpenAPI los errores que el router ya emite.

RF-10 original permite modificar; la aclaración posterior de la profesora prohíbe modificar tras responder (FASE_8B_RESPUESTAS_INMUTABLES.md). La inmutabilidad está confirmada, no se solicita reabrirla. Falta conciliación del requisito escrito y definición de varias preguntas por escena, ciclos y revisitas. **RF-10 sigue BLOQUEADO integralmente**. Este contrato cubre una pregunta por escena y grafos sin ciclos alcanzables; no prohíbe esos casos para siempre como regla académica. RF-12/23/25 mantienen sus bloqueos.

## Operaciones reales de app.main

| Método y ruta | Éxito | Cuerpo / respuesta |
|---|---|---|
| POST /api/v1/identity/auth/estudiantes | 200 | correo y codigo_convocatoria; access_token y token_type. No registrar estos valores |
| GET /api/v1/attempts/{attempt_id}/current-scenario | 200 | EscenarioActualRespuesta. Sin query params; extras devuelven 422 |
| POST /api/v1/attempts/{attempt_id}/decisions/{decision_id} | 201 | {id_opcion, reflexion_estudiante?}; devuelve IntentoRespuesta, NO confirma la opción en el cuerpo |
| GET /api/v1/attempts/{attempt_id}/progress | 200 | ProgresoRespuesta; consulta privada sin DML/flush/commit |
| POST /api/v1/attempts/{attempt_id}/finish | 200 | Sin cuerpo; IntentoRespuesta. Repetir cierre autorizado es idempotente |

JWT Bearer real, cuenta activa/rol y titularidad persistentes. Nunca enviar id_estudiante o rol como prueba de identidad. No hay PUT, PATCH o DELETE de decisiones en main; el método no admitido produce 405, no una edición. La ruta general heredada con PUT no se monta. No se añade ninguna ruta nueva en este incremento.

## Identificadores y DTO

Intento, participación y número de intento son INTEGER positivos representados como number. decision_id de la URL es UUID y corresponde a pregunta.id de current-scenario; no es el identificador de una selección almacenada. El grafo SQL devuelve UUID reales de escenas, preguntas y opciones. No convertir ni fabricar UUID desde INTEGER.

El DTO compartido SeleccionSolicitud y las selecciones de progreso conservan UUID | INTEGER por compatibilidad con consumidores históricos. El adaptador SQL real exige pertenencia al grafo UUID; que el esquema acepte INTEGER no concede una referencia válida. Angular de este recorrido debe enviar exactamente los UUID recibidos en GET. No se estrecha silenciosamente el DTO global.

```ts
type EstadoIntento = 'EN_CURSO' | 'FINALIZADO' | 'VENCIDO';
interface Intento {
 id_intento:number; id_participacion:number; numero_intento:number;
 estado:EstadoIntento; inicio:string; fin:string|null; vence_en:string;
}
interface EscenarioActual {
 id_escenario:string|null; contexto:string|null;
 pregunta:{id:string; enunciado:string; opciones:{id:string;texto:string}[]}|null;
 recorrido_finalizado:boolean; respondidas:number;
}
interface Progreso {
 intento:Intento;
 decisiones_aplicables:(string|number)[]|null;
 selecciones:{id_decision:string|number;id_opcion:string|number}[];
 pendientes:(string|number)[]|null; total_aplicable:number|null; respondidas:number;
}
interface Seleccion {id_opcion:string; reflexion_estudiante?:string|null;}
interface ErrorParticipacion {detail:{codigo:string;mensaje:string;campos?:string[]};}
```

Son contratos de transporte, no nuevas entidades Angular del repositorio. Las fechas son ISO-8601 con offset del servidor; no reinterpretar timestamps históricos sin zona ni inventar UTC en el backend. PARTICIPATION_TIMESTAMP_ZONE es obligatoria y explícita en el servidor. No hay campos de calificación, criterio, correctas, justificación o rúbrica en estos DTO. FIN devuelve id_escenario/contexto/pregunta=null, respondidas=N y recorrido_finalizado=true. El intento aún puede estar EN_CURSO: FIN no sustituye POST finish. Después del cierre, consultar progress; current-scenario devuelve 409.

## Secuencia y errores

1. Autenticar y obtener un intento ya existente autorizado. Su preparación en la demostración es LAB, no inicio productivo.
2. GET progress después de recargar. Si FINALIZADO/VENCIDO, representar el estado y selecciones sin abrir una edición.
3. Con EN_CURSO, GET current-scenario; mostrar únicamente pregunta y alternativas recibidas. No derivar próximas escenas del orden editorial.
4. Confirmar una opción y hacer POST. Deshabilitar doble clic en UI, pero la integridad corresponde al servidor.
5. Tras 201, consultar progress y current-scenario. La respuesta queda inmutable, incluso si la misma selección se vuelve a enviar.
6. Al recibir FIN, ofrecer cierre explícito. El cierre voluntario anterior a FIN conserva su contrato existente; este incremento no lo restringe ni calcula notas.

| HTTP | Interpretación para este recorrido | Acción cliente |
|---|---|---|
| 401 | JWT ausente, inválido o expirado | Flujo de autenticación; no suplantación por cabeceras |
| 403 ACCESO_DENEGADO | Titularidad/matrícula/convocatoria/sesión/pregunta/opción fuera de autorización | No reintentar como otro usuario; no revelar contenido |
| 404 RECURSO_NO_DISPONIBLE | Recurso no disponible según contrato | No fabricar identificadores |
| 409 RESPUESTA_INMUTABLE | Ya existe una selección, incluso idéntica | Consultar progress; no upsert |
| 409 INTENTO_NO_EDITABLE | Cierre o tiempo agotado | Consultar progress; el POST puede haber confirmado VENCIDO |
| 409 CONFLICTO_ACTUALIZACION | Conflicto transaccional | Releer estado antes de cualquier siguiente acción autorizada |
| 422 | Cuerpo/parámetros inválidos | Corregir la solicitud, no cambiar la política |
| 503 | Configuración/integración/regla pendiente | Mostrar indisponibilidad; nunca tratarlo como cumplimiento o permiso |
| 500 | Fallo inesperado | No asumir que una solicitud anterior se confirmó o falló; releer progreso |

No aplicar retry automático de POST de selección ante pérdida de respuesta. Consultar progress: si aparece la opción original, mostrarla como registrada; si hay otra, no sustituirla. La segunda selección devuelve 409; el POST no es idempotente en su respuesta HTTP. GET progress solo proyecta vencimiento; POST puede persistirlo antes de rechazar la selección. El mensaje HTTP 405 de método no registrado pertenece a FastAPI y no usa necesariamente ErrorParticipacion; el cliente debe comprobar la forma de detail.

## Preparación de evidencia

Reutilizar test_main_decisions (14 casos), test_main_current_scenario (11), test_immutable_answers (21) y test_cases_graph (51). Nuevos casos cubren exclusivamente contrato OpenAPI, recarga/rama/FIN/cierre y diferencia GET/POST al vencer. No sustituir relaciones críticas por mocks.

La colección complementaria RF-10 ejecutará únicamente URLs de app.main. PostgreSQL17, relaciones académicas y el intento previo se preparan con los mecanismos LAB existentes. Esa preparación separada no habilita consentimiento ni inicio productivos. Las peticiones de la colección no invocan URLs LAB ni resultados oficiales. Los resultados se agregarán después de ejecutar, sin reutilizar cifras históricas.


## Integración práctica del cliente

`total_aplicable=null` o `pendientes=null` significa que el conjunto completo aún no está acreditado, no cero. No calcular un porcentaje inventando preguntas futuras. Tras FIN, la lista del recorrido puede completarse sin incluir ramas inaccesibles.

Usar HttpClient con URLs relativas al origen autorizado. No hay CORSMiddleware configurado en app.main: una prueba Postman no acredita CORS en navegador. En desarrollo se puede usar el proxy de Angular hacia el backend de laboratorio para conservar el mismo origen; no se añade allow_origins=* ni se decide una política de despliegue en este incremento. Los orígenes de producción y el almacenamiento del token requieren la configuración de seguridad del equipo.

```ts
// Fragmento orientativo, sin crear un frontend ni otro backend.
const base = `/api/v1/attempts/${attemptId}`;
// El interceptor de autenticación existente agrega Bearer; no registrar el token.
http.get<Progreso>(`${base}/progress`);
http.get<EscenarioActual>(`${base}/current-scenario`);
http.post<Intento>(`${base}/decisions/${pregunta.id}`, { id_opcion: opcion.id });
http.post<Intento>(`${base}/finish`, null);
```

No obtener un UUID a partir de un INTEGER ni enviar id_estudiante/rol. Las referencias de este flujo se reciben del servidor. No ejecutar current-scenario si progress ya confirma FINALIZADO/VENCIDO. No mostrar evaluación o explicaciones a partir de estos DTO. Un endpoint registrado de inicio que devuelve 503 no es un paso aprobado del cliente.


## Resultados reales — 9 noviembre 2026, Bogotá

Versión: HEAD `84f05d55446acea22c2402f403156c200a927338` más los cambios RF-10 locales identificados por SHA-256. Se conservan los siete cambios de código anteriores sin incluirlos en los checkpoints de este incremento. Evidencia: `evidencias/rf10_contrato_20261109/`; los timestamps de logs son UTC (10 noviembre), correspondientes a la noche del 9 en Bogotá.

| Ejecución nueva | Aprobadas | Omitidas | Fallidas/errores |
|---|---:|---:|---:|
| Contrato unitario | 5 | 0 | 0 |
| Nuevos casos, unidad + HTTP/PG17 | 8 | 0 | 0 |
| Focal ampliada | 124 | 0 | 0 |
| Relacionada | 775 | 9 | 0 |
| General nueva, cuatro particiones disjuntas | 2502 | 38 | 0 |

La general cubre los 120 archivos, 2540 casos únicos, con fuentes estables. Es una ejecución nueva completa, no la conciliación anterior de 2494/38. No sumar las suites solapadas. Se conserva una categoría de advertencia Starlette/httpx y las omisiones históricas por opt-in/URLs externas no configuradas; ninguna prueba nueva se omitió. JUnit agregado: junit_general.xml; logs originales: general_g0..general_g3/consola.log.

Newman 6.2.3: complemento **21 solicitudes / 76 aserciones**, todas aprobadas; maestra RF-10 **32 / 141**, todas aprobadas técnicamente y RF BLOQUEADO. No sumar ambas colecciones ni las repeticiones. `newman_main_2` es la ejecución seleccionada, con SHA-256 de colección/preparador y consulta SQL independiente: un intento FINALIZADO, dos respuestas, cero resultados/publicaciones. `newman_main_1` se conserva como ejecución previa; no añade cobertura. La nueva generación inicial encontró un import local de re fuera de orden; se corrigió el generador antes de ejecutar los scripts actuales. No se cambió ningún HTTP esperado para conseguir aprobación.

No se ejecutaron los otros 26 RF nuevamente en Postman ni Postman Desktop/Angular en navegador. Sus estados previos permanecen intactos, con 16 APROBADOS/11 BLOQUEADOS en la matriz global. La regresión backend sí se ejecutó completa.

Los errores controlados se documentan como ErrorHTTP; un 405 o un 500 del framework puede no usar ese esquema o incluso ser texto. Comprobar la forma y Content-Type antes de acceder a detail.codigo. La corrección productiva se limita a metadatos OpenAPI: antes decisiones y cierre omitían 401/403/404/409/503 y anunciaban HTTPValidationError para 422; ahora declaran ErrorHTTP, que es lo que traduce RutaParticipacion. Evidencia comparativa: DIAGNOSTICO_OPENAPI.json.

## Comandos ejecutados y continuidad

Desde la raíz, el runner de evidencia deshabilita .env dentro de su proceso, elimina URLs heredadas, activa únicamente las fixtures Docker propias y registra comando, HEAD, huellas, fecha, JUnit y consola:

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf10_contrato_20261109/run.py --modo focal --evidencias evidencias/rf10_contrato_20261109/focal
.\.venv\Scripts\python.exe -B evidencias/rf10_contrato_20261109/run.py --modo relacionada --evidencias evidencias/rf10_contrato_20261109/relacionada
# También se ejecutaron --modo g0, g1, g2, g3, cada uno en su destino general_gN.
.\.venv\Scripts\python.exe -B evidencias/rf10_contrato_20261109/agrupar_general.py
```

Esos destinos ya existen: para repetir, usar nombres NUEVOS. Los comandos exactos de todas las pruebas están en ejecucion.json. Para Newman, ver backend/docs/postman/rf10_main/README.md; no se incluyen binarios ni módulos privados de instalación.

Fase A protegida mediante respaldo local privado recuperable fuera del repositorio y dos commits locales: cf09ab9692c5329934568c559d91622cef5c3a74 y 84f05d55446acea22c2402f403156c200a927338. Las 2822 copias y 25 referencias se verificaron; el bundle se recuperó en un repositorio bare de comprobación sin sobrescribir el original. La guía generada recibió únicamente normalización de una línea vacía EOF para superar diff --check, con original/huellas conservados. Los cinco artefactos anteriores de Postman no se sobrescribieron.

No hay nuevas rutas, modelos, tablas, migraciones, motores ni políticas. No se habilitan PUT/PATCH ni inicio productivo. RF-10 queda sin commit para revisión; no se hizo push/merge. El siguiente paso es revisar este contrato con el cliente Angular y conciliar documentalmente RF-10 sin revertir la política confirmada de inmutabilidad. Multipregunta/ciclos/revisitas requieren definición académica adicional antes de implementarse.
