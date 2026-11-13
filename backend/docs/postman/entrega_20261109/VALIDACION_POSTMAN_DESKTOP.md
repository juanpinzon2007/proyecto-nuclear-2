# Validación de Postman Desktop — 8 noviembre 2026

Versión base: `0fa76b04126a700125a252dc4291d3bf74a04542`; rama `feature/backend-continuidad`. Automatización y colecciones locales sin commit. No se modificó código productivo, migraciones ni bases permanentes.

## Ejecución real

Se arrancó el script PowerShell real con -Opcion 1/2/3. Cada modo creó PostgreSQL 17 nuevo y servidores de laboratorio. Newman 6.2.3 ejecutó los scripts pm.test con **un runtime nuevo por solicitud**: solo el Environment resultante se transfirió al siguiente Send. No se reutilizaron variables locales de una ejecución anterior.

Esto acredita HTTP y scripts reales compatibles con Send independiente; **no se abrió/importó ni pulsó Send en la interfaz gráfica de Postman Desktop**. Su ejecución manual y las capturas siguen a cargo del presentador. Newman fue instalado en una carpeta temporal privada únicamente para QA; no es un requisito del lanzador ni de la demostración.

| Modo | Solicitudes HTTP | pm.test aprobadas | Fallos | Guardas sin HTTP |
|---|---:|---:|---:|---:|
| principal | 32 | 141 | 0 | 2 |
| reportes | 15 | 52 | 0 | 2 |
| worker | 4 | 14 | 0 | 2 |

**Resultado: 51 solicitudes, 207 aserciones pm.test aprobadas y 0 fallos.** Las seis guardas de modo/orden son verificaciones adicionales sin HTTP, no se suman como pm.test. No se sumaron las primeras ejecuciones _01 a las repeticiones _02. No se ejecutó pytest ni se atribuyen cifras históricas a esta entrega.

## Evidencia PostgreSQL y archivos

- Principal: antes P=0/I=0/respuestas=0/resultados=0/publicaciones=0; después P=1/I=1/respuestas=2/resultados=1/publicaciones=0. Resultado técnico 100.00 NO oficial. Rechazo 409 de otra alternativa y conservación de selección original; cierre y evaluación idempotentes.
- Reportes: publicación explícita de laboratorio 33.33; XLSX y PDF reales descargados, leídos con openpyxl/pypdf y correspondientes al mismo identificador, versión y huella de publicación.
- Worker: Worker real --once, primera ejecución 1 cierre y segunda 0; sesión FINALIZADO, una auditoría y un aviso, sin resultados técnicos. Fixture vencida hace más de 24 horas.

Los detalles nominales de cada solicitud y aserción están en `evidencias/postman_desktop_20261108/{principal,reportes,worker}_02/resultado.json`; los dos binarios sintéticos están en reportes_02. No contienen Environment, JWT, contraseñas ni cuerpos de login. Son evidencias locales; no se prepararon commits.

## Repetir la validación opcional

La demostración normal usa exclusivamente `.\preparar-postman.ps1` y Postman Desktop. Para QA automatizada se dispone de `verificar_desktop.py --modo principal|reportes|worker --newman <carpeta_node_modules/newman> --evidencias <carpeta_nueva>`. Ejecutarlo con `.venv\Scripts\python.exe -B`; requiere Node y Newman opcionales. El destino de evidencias debe ser nuevo. Esta herramienta lanza el script PowerShell y comprueba limpieza al salir.

Newman se instaló de forma aislada con npm --prefix en TEMP y sin scripts de instalación. npm informó dependencias obsoletas transitivas; se limita al ejecutor opcional, no forma parte de las dependencias productivas ni se exige al presentador.

## Aislamiento y preservación

Todos los recursos PostgreSQL propios de las seis ejecuciones fueron eliminados por q. Los servidores propios finalizaron y los archivos privados temporales de importación se eliminaron. Se conservaron los contenedores anteriores, incluido el laboratorio que ya estaba activo. Se usan puertos asignados por el sistema: no se cierra un servidor por ocupar 8765/8766.

La verificación `preservacion_despues.json` comprobó 2415 originales sin seguimiento por SHA-256: cero alterados; .env, stash, referencias y HEAD preservados; índice vacío y ningún contenedor nuevo restante. Cinco archivos rastreados de automatización/colecciones modificados; archivos nuevos de preparación y documentación sin preparar. No hubo commit, push, merge ni cambios de rama.

## Uso y límites

Siga `GUIA_POSTMAN_SUSTENTACION.md`: contiene las 51 solicitudes, dependencias, HTTP esperado, respuesta, aserciones, RF y capturas. Los entornos temporales son completos y únicos, pero deben importarse y **seleccionarse** expresamente; no se presupone sincronización automática.

El documento de consentimiento, admisión, asignaciones y datos académicos son sintéticos y de laboratorio. El inicio LAB no se declara disponible en app.main. No se modificaron políticas ni se habilitaron rutas productivas. Los resultados principales siguen siendo técnicos; la colección de reportes demuestra una publicación explícita exclusivamente sobre datos desechables.
