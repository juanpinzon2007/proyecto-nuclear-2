# Demostración RF-10: solo solicitudes de app.main

Contrato Angular: `backend/docs/RF10_CONTRATO_ANGULAR.md`. RF-10 continúa BLOQUEADO integralmente por conciliación documental y reglas no definidas de multipregunta/ciclos/revisitas.

## Preparar

Desde la raíz del repositorio, con Docker Engine abierto y postgres:17 disponible:

```powershell
$anterior = $env:PYTHONIOENCODING
try {
  $env:PYTHONIOENCODING = 'utf-8'
  & .\.venv\Scripts\python.exe -B -u backend/docs/postman/rf10_main/preparar.py
} finally { $env:PYTHONIOENCODING = $anterior }
```

Importe los dos archivos temporales impresos, seleccione el Environment cuyo nombre empieza RF10 MAIN — INTENTO PREVIO LAB, y ejecute únicamente RF-10 — MAIN en orden. Use q en la terminal para eliminar los archivos privados/servidores/contenedor propios. No reutilice un entorno de otra ejecución.

El preparador reutiliza las fixtures/laboratorios existentes. Crea un caso publicado/grafo, sesión, convocatoria/admisión, aceptación e intento con políticas SOLO LAB. Es preparación previa identificada, no una API productiva de inicio. Después, las 21 peticiones de la colección llaman únicamente app.main; no sustituyen Identity, SQL, Scheduling o Cases. No se aprueban RF-12/23/25. El reloj de laboratorio existente está controlado; las pruebas automatizadas cubren por separado el vencimiento.

La plantilla incluida está vacía, sin contraseñas, códigos, JWT ni UUID inventados. El entorno temporal contiene secretos sintéticos necesarios para login: no exportarlo, compartirlo o sincronizarlo. El módulo privado de Newman es opcional y no está incluido. La interfaz gráfica Postman no ha sido ejecutada por esta preparación.

## Orden y captura

No continúe si una aserción falla. En login o respuestas con tokens, oculte Body/Response, Authorization y Environment. Para los demás pasos muestre nombre, método/URL, HTTP y Test Results. No se entregan capturas fabricadas.

| Solicitud | Método | HTTP esperado | Evidencia manual |
|---|---|---:|---|
| RF10-MAIN-01 — Login titular real | POST | 200 | Ocultar credenciales/JWT; acreditar solo estado y tests |
| RF10-MAIN-02 — Rechazar anónimo | GET | 401 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-03 — Login otro estudiante | POST | 200 | Ocultar credenciales/JWT; acreditar solo estado y tests |
| RF10-MAIN-04 — Rechazar acceso ajeno | GET | 403 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-05 — Escenario actual privado | GET | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-06 — Recargar misma pregunta sin escribir | GET | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-07 — Rechazar pregunta futura | POST | 403 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-08 — Primera selección | POST | 201 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-09 — Reenvío idéntico no es upsert | POST | 409 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-10 — Rechazar cambio de alternativa | POST | 409 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-11 — PUT no registrado | PUT | 405 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-12 — PATCH no registrado | PATCH | 405 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-13 — Reconciliar selección desde progreso | GET | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-14 — Siguiente escenario real | GET | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-15 — Respuesta siguiente autorizada | POST | 201 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-16 — FIN sin contenido futuro | GET | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-17 — FIN no cierra automáticamente | GET | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-18 — Cierre explícito | POST | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-19 — Repetir cierre conserva datos | POST | 200 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-20 — Contenido activo cerrado | GET | 409 | Capturar respuesta sintética y Test Results |
| RF10-MAIN-21 — Progreso histórico privado | GET | 200 | Capturar respuesta sintética y Test Results |

Los UUID de pregunta futura usados para un rechazo provienen de la preparación LAB; el endpoint público no revela preguntas futuras. El navegador no debe fabricar ni obtenerlas por un camino alternativo.

## Automatización reproducible

```powershell
$runtime = Get-Content evidencias/postman_desktop_20261108/newman_runtime.json -Raw | ConvertFrom-Json
& .\.venv\Scripts\python.exe -B backend/docs/postman/rf10_main/preparar.py --ejecutar --newman (Join-Path $runtime.ruta "node_modules/newman") --evidencias evidencias/RF10_NUEVA_EJECUCION
```

La ruta JSON anterior es un registro local privado de la instalación Newman 6.2.3, no una dependencia versionada. En otro equipo instale Newman y pase su ruta local node_modules/newman. Use siempre un destino de evidencia NUEVO. El ejecutor guarda inicio/resultado, JUnit y salida sanitaria de pm.test; comprueba SQL independiente, ausencia de notas/publicaciones y limpieza. No publica en Postman ni GitHub.

No ejecutar toda la colección maestra 27RF contra esta base: sus carpetas exigen laboratorios distintos. La colección maestra RF-10 mantiene sus pasos MAIN/LAB identificados; esta colección es un complemento que separa la preparación y el recorrido público.

## Resultado comprobado

Newman 6.2.3 ejecutó 21 solicitudes / 76 aserciones aprobadas sobre app.main, con lectura SQL independiente y limpieza. Evidencia seleccionada: evidencias/rf10_contrato_20261109/newman_main_2/. No se abrió Postman Desktop ni se tomó una captura; las capturas de la tabla son tareas manuales. Focal: 124 aprobadas; relacionada: 775/9 omitidas; general nueva: 2502/38, sin fallos/errores. No sumar ejecuciones solapadas. RF-10 sigue BLOQUEADO integralmente.
