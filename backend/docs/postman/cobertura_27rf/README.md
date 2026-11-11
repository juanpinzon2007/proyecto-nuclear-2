# Candidato integrado del 11 de noviembre

21 RF APROBADOS y 6 BLOQUEADOS en el alcance de laboratorio. Nueva ejecución completa de Newman con 569 solicitudes y 2166 aserciones. Las secciones fechadas anteriores conservan sus resultados históricos. Véase ../../CANDIDATO_INTEGRADO_20261111.md para el contrato actual, las pruebas y las capturas.

# Cobertura verificable de los 27 RF — Postman

Resultado de la selección final Fase7: **17 RF APROBADOS integralmente, 10 BLOQUEADOS, 0 FALLIDOS y 0 NO EJECUTADOS** en el alcance funcional documentado de laboratorio. Los bloqueados tienen capacidades parciales ejecutadas; no equivalen a requisitos completos. Consulte [la matriz](MATRIZ_TRAZABILIDAD_27RF.md), [las brechas](BRECHAS_RF.md) y [los resultados JSON](RESULTADOS_27RF.json).

## Qué está preparado

- `Proyecto_Nuclear_27RF.postman_collection.json`: una colección 2.1 con exactamente 27 carpetas RF-01 a RF-27. Cada caso tiene código PM-RF, contrato, HTTP exacto y scripts pm.test.
- `Proyecto_Nuclear_27RF.postman_environment.json`: plantilla totalmente vacía, sin secretos. **No es el Environment listo para ejecutar**; use el preparador.
- `REQUISITOS_FUENTE.json`: texto central del PDF, páginas y SHA-256. La matriz distingue el contrato original de las aclaraciones posteriores.
- `INVENTARIO_PREVIO.json` y `openapi_main.json`: colecciones existentes, métodos pytest y rutas reales. El registro de ruta no acredita ejecución ni disponibilidad productiva.
- `matriz_trazabilidad_27rf.csv`: cada solicitud enlazada con sus aserciones, resultado, evidencia y pruebas complementarias verificadas.
- `RF-01.md` a `RF-27.md`: orden, superficies MAIN/LAB, resultados reales, verificaciones SQL y capturas pendientes.

## Preparar RF-07 y demostrarlo con Send

Desde la raíz **original** del repositorio, con Docker Engine activo, imagen postgres:17 y `.venv` disponible:

```powershell
.\preparar-27rf.ps1 -RF RF-07
```

Si la política de PowerShell impide ejecutar el archivo, la excepción puede limitarse a ese proceso:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\preparar-27rf.ps1 -RF RF-07
```

1. El preparador crea exclusivamente PostgreSQL17 nuevo y servidores locales en puertos libres. No utiliza .env ni conexiones permanentes. Mantenga la consola abierta.
2. Escriba `i` para abrir su carpeta temporal privada. Importe los **dos archivos cuyas rutas imprime**: `Proyecto_Nuclear_27RF.postman_collection.json` y `Environment_ACTIVO.postman_environment.json`.
3. Seleccione en el desplegable Environment el nombre **NUCLEAR 27RF — RF-07 — identificador único**. Importar JSON no selecciona ni actualiza automáticamente otro entorno.
4. Abra la colección **Proyecto Nuclear — cobertura verificable RF-01 a RF-27**, carpeta **RF-07 — Administrar preguntas y respuestas**.
5. Empiece por **PM-RF-07-01 | MAIN — login docente**. Pulse Send en orden hasta el último caso. Los tokens, identificadores y cuerpos docentes se preparan/capturan automáticamente; no copie UUID ni edite headers o bodies.
6. Todos los Test Results deben aprobar. Los 403/404/400/422 de las negativas son resultados esperados; un 503 nunca acredita el requisito.

RF-07 demuestra, sobre app.main y JWT reales: creación, edición, dos escenarios con una pregunta y tres alternativas cada uno, flags correctas/incorrectas, justificaciones, rúbrica, grafo, publicación válida, rechazo de edición publicada y rechazo de estructura inválida. Las consultas HTTP son solicitudes distintas; además el ejecutor confirmó por una Session SQL independiente los **2 escenarios, 2 preguntas y 6 opciones**, con sus textos/flags/justificaciones exactos.

La preparación administrativa contiene cuentas, matrícula, asociaciones y grants sintéticos. El caso RF-07 que se acredita se crea y se edita mediante API, no se inserta como fixture SQL. La composición productiva no cambia.

## Demostrar otro RF

Escriba `q` para cerrar únicamente ese laboratorio. Después ejecute, por ejemplo:

```powershell
.\preparar-27rf.ps1 -RF RF-16
```

Importe los nuevos archivos y seleccione su nuevo Environment. Ejecute únicamente esa carpeta desde su primera solicitud. Cada RF tiene precondiciones propias: **no ejecute el Runner de las 27 carpetas sobre una única base**. Para automatizar las 27, use el ejecutor que crea una base nueva por RF.

- **RF-16:** publique expresamente mediante sus solicitudes y descargue archivos reales con Send and Download (o Save Response). Compare X-Publicacion-Id/Version/SHA256 entre Excel y PDF. No se recalculan notas al exportar.
- **RF-19:** primero demuestra estados y rechazo de doble cierre docente. Antes de las solicitudes llamadas WORKER 2 y WORKER 3 escriba `w` en la consola. El proceso Worker real --once cierra 1 sesión y luego 0, sobre una fixture más de 24 horas vencida. No evalúa ni publica notas.
- **RF-10/12/13/23/25:** el flujo incluye un inicio solo LAB con consentimiento sintético. Se mantiene la etiqueta BLOQUEADO para el cumplimiento integral pendiente; no se habilitaron rutas en app.main.
- **RF-20/21:** avisos internos reales y retiro no equivalen a envío de correo. No hay proveedor SMTP ni códigos expuestos en evidencia.

Las guardas evitan mezclar carpetas y saltar pasos en runtimes compatibles con pm.execution.skipRequest. No son un mecanismo de autorización: el servidor siempre verifica JWT, rol, cuenta y ámbito persistentes. Si cualquier prueba queda roja, detenga ese recorrido y conserve su resultado. Para repetirlo desde cero prepare otro laboratorio; no cambie el esperado para obtener verde.

Los JWT pueden expirar; vuelva a ejecutar el login correspondiente, sin copiar tokens. No comparta ni sincronice los valores del Environment. El archivo temporal contiene secretos **sintéticos** en texto; el tipo secret solo los oculta visualmente, no los cifra.

`q` detiene servidores y elimina únicamente recursos propios y archivos temporales de importación. Conserva contenedores ajenos, capturas y descargas. La copia ya importada en Postman no se elimina automáticamente: retírela manualmente al terminar. No cierre Docker Desktop para limpiar.

## Ejecutar automáticamente los 27 RF

Newman no es necesario para Send en Desktop. Para QA se utilizó **Newman 6.2.3 como biblioteca**, con un runtime independiente por solicitud y persistiendo únicamente el Environment entre Send.

```powershell
.\validar-27rf.ps1
```

En este equipo detecta el módulo privado utilizado en la validación anterior. En otro equipo, si falta, puede instalar el ejecutor en una carpeta temporal separada y proporcionar su ruta (Node/npm son requisitos solo de esta opción):

```powershell
$runtime27 = Join-Path $env:TEMP ('NuclearNewman-' + [guid]::NewGuid().ToString('N'))
npm.cmd install --prefix $runtime27 --no-audit --no-fund --ignore-scripts newman@6.2.3
.\validar-27rf.ps1 -ModuloNewman (Join-Path $runtime27 'node_modules\newman')
```

No instala dependencias dentro del repositorio ni publica resultados en un workspace. Cada ejecución crea una carpeta nueva en evidencias con logs, respuestas sintéticas redactadas cuando se capturan, JUnit nominal, Worker, SQL y binarios. No versionar los Environment temporales ni esos artefactos masivamente. Los resultados anteriores no se sobrescriben.

`validar_regresion.py` permite repetir focal o relacionada, desactiva .env y conexiones heredadas dentro del proceso y habilita únicamente fixtures PostgreSQL desechables. La ejecución actual obtuvo **74 aprobadas focalizadas y 605 relacionadas**, cero omitidas/fallos/errores y una advertencia conocida Starlette/httpx. **No se suman** porque se solapan; tampoco se ejecutó nuevamente toda la regresión general histórica. No se modificó producción durante este incremento.

## Evidencia auténtica y capturas

Evidencias locales de esta entrega: `evidencias/cobertura_27rf_20261109T195945Z/`. `SELECCION_RESULTADOS.json` explica qué ejecución válida se usa para cada RF; `junit_postman_27rf.xml` contiene las aserciones reales conciliadas. Se preservan todos los fallos diagnósticos y sus logs. Se reutiliza una carpeta del primer ciclo solo cuando sus requests y scripts no cambiaron.

No se afirmó ejecución en la interfaz gráfica de Postman ni se fabricaron capturas. La ejecución comprobada fue HTTP real con scripts pm.test mediante Newman. Durante la sustentación tome capturas mostrando nombre PM-RF, método/URL, HTTP, Response sintética y Test Results. **En login o generación de código, oculte Body/Response y Authorization que contengan secretos.**

Para RF-07 priorice: editar 200, detalle 200 con flags y justificaciones, publicar 200, editar publicada 400, publicar inválida 400, y el registro SQL independiente. Guarde imágenes con el código de caso. Las fichas CP del Word no se modificaron ni se asignaron correspondencias inventadas: los casos nuevos usan PM-RF; la conciliación institucional individual con PT-DCP-01 sigue indicada en la matriz.

## Límites del veredicto

16/27 aprobados no significa backend desplegado ni cobertura académica del 100 %. Los 11 bloqueos están individualizados en BRECHAS_RF.md: catálogo/administración de asociaciones, contradicción documental de RF-10, consentimiento/inicio productivo, alcance de resultados/visibilidad/repeticiones y validación institucional de políticas propuestas, y correo externo. No se sustituyeron por políticas ficticias ni se presentaron fixtures como operaciones productivas.


## Continuación RF-12/RF-23/RF-25 — 9 de noviembre, composición main condicionada

Nueva evidencia de regresión: `evidencias/participation_fase1_20261109T215053Z/regresion_postman_27/`. Se volvieron a ejecutar los 27 RF con PostgreSQL17 nuevo y Newman: 545 HTTP / 2080 pm.test, sin errores; se conservan 16 APROBADOS y 11 BLOQUEADOS. Las cifras de la sección anterior describen la auditoría previa y no se suman con esta ejecución.

Consentimiento e inicio están ahora registrados en app.main, pero sus proveedores productivos obligatorios permanecen cerrados por falta de aprobación/documento y políticas. La provisión independiente no se publica. La colección complementaria `../participation_fase1/` demuestra los mecanismos main con puertos explícitos LAB, además del cierre sin esos proveedores: 79 solicitudes / 291 aserciones reales. No se suma con la colección maestra.

RF-12, RF-23 y RF-25 siguen BLOQUEADOS para aceptación integral. Su matriz complementaria nominal es `../participation_fase1/matriz_fase1.csv`. Guía, contratos, pruebas, diagnósticos preservados y decisiones que debe aportar el equipo: `backend/docs/PARTICIPATION_FASE1_MAIN_CONDICIONADO.md`. No se reutiliza como oficial el borrador NO APROBADO.


## Fase 3 — RF-03 y regresión vigente

Evidencia: evidencias/rf03_fase3_20261109/. Se ejecutaron las 27 carpetas originales con PostgreSQL17 y Newman (545 HTTP / 2080 pm.test). Después se amplió RF-03 de 9 a 17 solicitudes para cubrir PUT, login/lectura posterior, rechazo por estudiante, catálogo incompatible, rol combinado no soportado y permiso inexistente. La selección final sustituye solo RF-03: **553 solicitudes / 2107 aserciones**, 16 APROBADOS y 11 BLOQUEADOS, cero FALLIDOS/NO EJECUTADOS. No sumar 545 + 17: los primeros nueve se solapan. Los requests/scripts de los otros 26 RF son idénticos.

RF-03 ampliado: 17/54 aprobados técnicamente; sigue BLOQUEADO integralmente por definición operativa de configuración/asignación de permisos. No por presumir que RF-03 exija multirrol o DOCENTE ADMINISTRADOR. El catálogo LAB incluye CREAR_CASOS para DOCENTE; el PUT válido conserva ese perfil, no representa una concesión individual distinta ni una operación de edición global del catálogo.

Código corregido: revalidación del administrador SQL y bloqueos en la UoW de alta/asignación. Informe, fuentes y límites: backend/docs/RF03_AUTORIZACION_TRANSACCIONAL.md. General backend nueva: 2518 aprobadas/38 omitidas, cero fallos/errores. Los párrafos previos describen ejecuciones históricas y no se suman con esta fase. No se ejecutó Postman Desktop.


## Fase 4 — RF04: alcance vigente

Ejecución nueva: evidencias/rf04_fase4_20261109/newman_27/. 556 solicitudes / 2118 pm.test, cero fallos técnicos, 16 APROBADOS y 11 BLOQUEADOS. RF04: 16 solicitudes / 53 aserciones; sigue BLOQUEADO. GET /scheduling/espacios (main) limita el listado a grants explícitos; las nuevas solicitudes PM-RF-04-10/11/12 acreditan selección propia, exclusión del espacio ajeno y rechazo sin JWT.

No se afirma asociación integral: rf_sesion se crea por HTTP, pero las convocatorias se demuestran sobre rf_sesion_convocatoria, otra sesión preparada con asignación en LAB. Falta el contrato productivo de fecha_limite_ingreso, intentos_base y estado del puente académico; no se promueven defaults/fixtures a políticas. No hay nueva ruta ni migración. Informe: backend/docs/RF04_SELECCION_ACADEMICA_Y_BLOQUEOS.md. General final nueva:2525 aprobadas/38 omitidas/cero fallos o errores; primera general de dos fallos unitarios preservada y corregida sin relajar HTTP esperados. No sumar ejecuciones.


## Fase 7 — RF14 acreditado y evidencia vigente

Selección:evidencias/rf14_fase7_20261110/seleccion_final/.560 solicitudes/2134 aserciones,17 APROBADOS/10 BLOQUEADOS. Las cifras de Fases3/4 anteriores son históricas. RF14:19/68, incluye aciertos/explicaciones históricos, recarga idéntica y rechazos; el fallo inicial de sintaxis se conserva sin contar como aprobación ni sumarlo al definitivo. No se alteraron requests/scripts de los otros26RF.

Backend:solo academic_cycle.py traduce resultado ausente a404; no calcula ni publica desde GET. General nueva2538/38,cero fallos/errores;13 focales y180 relacionadas, sin sumar. Guía y capturas:backend/docs/RF14_CONTRATO_ANGULAR.md y RF14_CIERRE_CONTROLADO_20261110.md. No se verificó Angular en navegador ni Postman Desktop.


## Complemento nuevo RF24 Fase9

Se repitieron RF24 (18HTTP/62pm.test) y las17carpetas ya acreditadas (314HTTP/1145pm.test), sin fallos técnicos. No es una nueva ejecución de las27carpetas ni una general. RF24 sigue BLOQUEADO; total17APROBADOS/10BLOQUEADOS. La fila RF24 y su evidencia CSV se actualizaron; las demás filas conservan su selección histórica. Resultados actuales y preparación LAB: `backend/docs/RF24_CIERRE_CONTROLADO_20261110.md` y `evidencias/rf24_fase9_20261110/RESUMEN_EJECUCION.json`.


## Fase10 — RF20/RF21

RF20 yRF21 fueron reejecutados:16HTTP/53pm.test cada uno, sin fallos técnicos; ambos siguen BLOQUEADOS. No se ejecutó correo real ni un capturador sin emisor. Los otros25RF conservan sus estados/evidencias. Regresión17 de Fase9 y general2538/38 históricas, no reejecutadas. El checkpoint documental RF24 es578f86385c9118813f0c1a51104e00be5927be29. Véase `backend/docs/RF20_RF21_ENTREGA_SEGURA_20261110.md`.
