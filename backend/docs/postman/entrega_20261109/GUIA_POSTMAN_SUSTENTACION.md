# Postman Desktop para Windows — sustentación

## Preparar e importar

Desde PowerShell, situado en la raíz del repositorio original:

```powershell
.\preparar-postman.ps1
```

Elija 1 (recorrido principal), 2 (publicación y reportes) o 3 (Worker). También puede ejecutar ` .\preparar-postman.ps1 -Opcion 1` (o 2/3). Requiere Docker Engine activo, imagen postgres:17 y el entorno Python del proyecto; no requiere Newman ni Postman CLI.
Si faltara el entorno Python, prepárelo una sola vez desde la raíz: `py -m venv .venv` y `.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"`. Si falta únicamente la imagen, use `docker pull postgres:17`. El lanzador comprueba estos requisitos y falla sin reutilizar bases existentes.
Si Windows bloquea el script por su política de ejecución, puede usar una excepción solo para ese proceso: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\preparar-postman.ps1`. No cambie la política global.

Mantenga abierta esa consola. El preparador crea exclusivamente PostgreSQL desechable, servidores locales en puertos libres y credenciales sintéticas nuevas. No usa .env ni bases permanentes. La preparación de casos, asociaciones, admisión y documentos es administrativa de LAB: no demuestra un flujo docente completo por API.

La consola muestra dos rutas exactas dentro de una carpeta temporal privada: la colección seleccionada y `Environment_ACTIVO.postman_environment.json`. Pulse `i` para abrirla. En Postman Desktop use Import para esos dos archivos. No importe el environment vacío de la carpeta del repositorio como entorno activo.
**Seleccione expresamente en el desplegable Environment el nombre único que imprime la consola**, `NUCLEAR LAB — … — <identificador>`. Importar un JSON no selecciona automáticamente el entorno ni actualiza otro entorno ya activo. Si Postman pregunta cómo resolver una colección antigua, importe como copia o seleccione la colección recién importada; use el nombre NUCLEAR DESKTOP correspondiente al modo.

No copie UUID, contraseñas o JWT. El environment temporal contiene los datos sintéticos completos; cada login captura su token con pm.environment.set. Las solicitudes guardan los identificadores reales para el siguiente Send. Las variables sobreviven entre solicitudes independientes, sin Runner.
El archivo temporal contiene secretos sintéticos en texto; el tipo secret solo los oculta visualmente. No exporte, comparta ni sincronice esos valores. Use valores locales de Desktop y un entorno de laboratorio. Las capturas nunca deben incluir Authorization, variables secretas, códigos ni el cuerpo de respuesta del login.

## Ejecutar sin improvisación

Abra la primera solicitud de la colección indicada y pulse Send. Continúe en el orden numérico siguiente únicamente si todas las aserciones de Test Results están verdes. Los 401/403/404/409 de las negativas son éxitos esperados. No ejecute las tres colecciones sobre un mismo entorno.
Las guardas impiden enviar con un modo equivocado o saltando pasos. No sustituyen autorización del servidor. Si una prueba queda roja, conserve la respuesta y deténgase; prepare un laboratorio nuevo para repetir. No repita comandos de escritura fuera de sus pruebas de idempotencia. Si expira un JWT, vuelva a enviar el login de ese actor y reanude, sin copiar el token.
En reportes use Send and Download (o Save Response después de Send) para guardar XLSX/PDF y abrirlos. Compare las cabeceras de publicación y la nota 33.33. Las negativas deben devolver JSON, nunca un archivo.
En Worker envíe las dos primeras solicitudes, escriba `w` en la consola, envíe la tercera, escriba `w` otra vez y envíe la cuarta. Se ejecuta el Worker real --once: primero cierra 1 sesión y después 0. La fecha de la fixture está más de 24 horas vencida; no se modifica la política del Worker ni se calculan notas.

## Cerrar y cambiar de laboratorio

Escriba `q` en la consola: detiene solo los servidores y PostgreSQL creados por esa ejecución y elimina sus dos archivos temporales de importación. No elimina capturas o descargas que haya añadido. En el menú elija otro modo; importe sus nuevos archivos y seleccione su nuevo Environment. Con -Opcion, q termina el lanzador.
La copia importada en Postman no se borra automáticamente: elimínela manualmente al terminar la demostración. No reutilice sus tokens o URLs después de q. No cierre Docker Desktop para limpiar: podría afectar recursos de otros compañeros.

## Alcance y evidencia

MAIN significa ruta registrada en app.main; LAB significa composición aislada, no una ruta productiva habilitada. El recorrido principal calcula 100.00 como resultado técnico NO oficial. La colección de reportes usa otra fixture y una publicación explícita exclusivamente de laboratorio. No implica aprobación institucional de las políticas.
Para cada captura muestre nombre de solicitud, método/URL sin secretos, estado HTTP y Test Results. En operaciones no login puede mostrar Response con datos sintéticos. Para archivos capture también el documento abierto y sus cabeceras de publicación. Guarde las imágenes fuera del índice Git.

## NUCLEAR DESKTOP — 1 Recorrido principal (MAIN + LAB)

Archivo: `Proyecto_Nuclear_entrega_20261109.postman_collection.json`. Environment: el único generado para **principal**.

### 01. MAIN — login admin

- RF: RF-02/RF-03. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/personal`. HTTP esperado: **200**.
- Dependencia: Preparar/importar y seleccionar este Environment.
- Response esperada: access_token, token_type y vigencia; token capturado automáticamente.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: El administrador entra con credenciales sintéticas reales de Identity; no mostrar el JWT.
- Captura: `principal_01.png`; solo estado y Test Results; ocultar Response del login.

### 02. MAIN — login docente

- RF: RF-02. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/personal`. HTTP esperado: **200**.
- Dependencia: Paso 1 aprobado.
- Response esperada: access_token del docente; captura automática.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: El rol y cuenta se validan en PostgreSQL, no en una cabecera de identidad.
- Captura: `principal_02.png`; solo estado y Test Results; ocultar Response del login.

### 03. MAIN — listar docentes

- RF: RF-03. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/docentes`. HTTP esperado: **200**.
- Dependencia: Paso 2 aprobado.
- Response esperada: Página de docentes con campos públicos, sin hashes ni contraseñas.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: La consulta requiere administrador; no concede permisos adicionales.
- Captura: `principal_03.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 04. MAIN — login estudiante

- RF: RF-01. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/estudiantes`. HTTP esperado: **200**.
- Dependencia: Paso 3 aprobado.
- Response esperada: access_token estudiantil asociado a su convocatoria.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: El correo y código pertenecen al titular; login no inicia el intento.
- Captura: `principal_04.png`; solo estado y Test Results; ocultar Response del login.

### 05. MAIN — login ajeno

- RF: RF-01. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/estudiantes`. HTTP esperado: **200**.
- Dependencia: Paso 4 aprobado.
- Response esperada: Token de otro estudiante sintético, reservado para negativas.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Se utiliza una identidad real distinta, no un token inventado.
- Captura: `principal_05.png`; solo estado y Test Results; ocultar Response del login.

### 06. MAIN — identidad privada

- RF: RF-01/RF-02. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/me`. HTTP esperado: **200**.
- Dependencia: Paso 5 aprobado.
- Response esperada: Identidad del estudiante y roles vigentes.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: La API recupera la cuenta persistente del JWT; no confía en datos de identidad enviados por el cliente.
- Captura: `principal_06.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 07. MAIN — admisión persistida en preparación LAB

- RF: RF-22. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/convocatorias/{{convocatoria_id}}/admision`. HTTP esperado: **200**.
- Dependencia: Paso 6 aprobado.
- Response esperada: admitida=true y concesión propia persistida.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Concesión vigente. Todas deben aprobar.
- Explicación: La admisión fue preparada administrativamente en LAB; esta consulta no concede ingreso ni crea participación.
- Captura: `principal_07.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 08. MAIN — validar ingreso sin crear P/I

- RF: RF-22. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/validar-ingreso`. HTTP esperado: **200**.
- Dependencia: Paso 7 aprobado.
- Response esperada: Validación autorizada de ingreso, sin crear participación ni intento.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Validar ingreso se distingue de iniciar la simulación.
- Captura: `principal_08.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 09. LAB AISLADA — documento sintético versionado

- RF: RF-12. Superficie: LAB aislada.
- Operación: `GET {{base_url_laboratorio}}/api/v1/identity/convocatorias/{{convocatoria_id}}/asignaciones/{{id_asignacion}}/consentimiento`. HTTP esperado: **200**.
- Dependencia: Paso 8 aprobado.
- Response esperada: Documento sintético, versión, referencia y huella; captura automática.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Esta ruta solo existe en la aplicación LAB; no constituye consentimiento institucional aprobado.
- Captura: `principal_09.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 10. LAB AISLADA — aceptación explícita LAB

- RF: RF-12. Superficie: LAB aislada.
- Operación: `POST {{base_url_laboratorio}}/api/v1/identity/convocatorias/{{convocatoria_id}}/asignaciones/{{id_asignacion}}/consentimiento/aceptacion`. HTTP esperado: **200**.
- Dependencia: Paso 9 aprobado.
- Response esperada: Aceptación explícita con id_consentimiento.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Se acepta el documento del servidor y se conserva su versión; solo política LAB.
- Captura: `principal_10.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 11. LAB AISLADA — inicio transaccional LAB

- RF: RF-12. Superficie: LAB aislada.
- Operación: `POST {{base_url_laboratorio}}/api/v1/convocatorias/{{convocatoria_id}}/intentos`. HTTP esperado: **201**.
- Dependencia: Paso 10 aprobado.
- Response esperada: Intento EN_CURSO, id_intento e id_participacion capturados.
- Test Results: HTTP exacto 201; Sin credenciales privadas. Todas deben aprobar.
- Explicación: La creación usa convocatoria, admisión y consentimiento en una transacción de laboratorio.
- Captura: `principal_11.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 12. LAB AISLADA — inicio repetido sin duplicados

- RF: RF-12. Superficie: LAB aislada.
- Operación: `POST {{base_url_laboratorio}}/api/v1/convocatorias/{{convocatoria_id}}/intentos`. HTTP esperado: **409**.
- Dependencia: Paso 11 aprobado.
- Response esperada: Conflicto de inicio repetido; no otro intento válido.
- Test Results: HTTP exacto 409; Sin credenciales privadas; Error sin datos académicos. Todas deben aprobar.
- Explicación: 409 es el resultado esperado: la repetición no debe crear otro inicio.
- Captura: `principal_12.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 13. MAIN — progreso ajeno rechazado

- RF: RF-11/RF-12. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/progress`. HTTP esperado: **403**.
- Dependencia: Paso 12 aprobado.
- Response esperada: Error de acceso, sin progreso del titular.
- Test Results: HTTP exacto 403; Sin credenciales privadas; Sin notas ni correcciones; Error sin datos académicos. Todas deben aprobar.
- Explicación: Un estudiante autenticado distinto no puede consultar este intento.
- Captura: `principal_13.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 14. MAIN — progreso inicial

- RF: RF-11. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/progress`. HTTP esperado: **200**.
- Dependencia: Paso 13 aprobado.
- Response esperada: Progreso con respondidas=0 y el intento esperado.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Cero respuestas; Intento propio recuperado. Todas deben aprobar.
- Explicación: La consulta es privada y todavía no hay selecciones ni calificaciones.
- Captura: `principal_14.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 15. MAIN — escenario actual 1

- RF: RF-10/RF-11. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario`. HTTP esperado: **200**.
- Dependencia: Paso 14 aprobado.
- Response esperada: Primera pregunta autorizada y sus opciones; captura automática.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Pregunta habilitada; Otra alternativa real disponible. Todas deben aprobar.
- Explicación: Solo se muestra la escena actual; no respuestas correctas ni preguntas futuras.
- Captura: `principal_15.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 16. MAIN — primera selección 1

- RF: RF-10. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/attempts/{{id_intento}}/decisions/{{id_decision}}`. HTTP esperado: **201**.
- Dependencia: Paso 15 aprobado.
- Response esperada: Confirmación de primera selección; mismo intento.
- Test Results: HTTP exacto 201; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones. Todas deben aprobar.
- Explicación: La primera respuesta queda registrada e inmutable.
- Captura: `principal_16.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 17. MAIN — segunda selección rechazada

- RF: RF-10. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/attempts/{{id_intento}}/decisions/{{id_decision}}`. HTTP esperado: **409**.
- Dependencia: Paso 16 aprobado.
- Response esperada: 409 al intentar seleccionar otra alternativa para la misma pregunta.
- Test Results: HTTP exacto 409; Sin credenciales privadas; Sin notas ni correcciones; Error sin datos académicos. Todas deben aprobar.
- Explicación: La regla posterior de la profesora prohíbe modificar una respuesta ya registrada.
- Captura: `principal_17.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 18. MAIN — escenario actual 2

- RF: RF-10/RF-11. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario`. HTTP esperado: **200**.
- Dependencia: Paso 17 aprobado.
- Response esperada: Pregunta siguiente del grafo real; captura automática.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Pregunta habilitada. Todas deben aprobar.
- Explicación: La alternativa registrada determina la transición persistente de Cases.
- Captura: `principal_18.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 19. MAIN — primera selección 2

- RF: RF-10. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/attempts/{{id_intento}}/decisions/{{id_decision}}`. HTTP esperado: **201**.
- Dependencia: Paso 18 aprobado.
- Response esperada: Confirmación de la segunda selección; mismo intento.
- Test Results: HTTP exacto 201; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones. Todas deben aprobar.
- Explicación: Se responde una pregunta pendiente, sin sustituir la anterior.
- Captura: `principal_19.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 20. MAIN — ruta terminal

- RF: RF-10/RF-11. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario`. HTTP esperado: **200**.
- Dependencia: Paso 19 aprobado.
- Response esperada: recorrido_finalizado=true y pregunta=null.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Terminal sin pregunta futura. Todas deben aprobar.
- Explicación: FIN corresponde al grafo publicado; no se fabrica una escena adicional.
- Captura: `principal_20.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 21. MAIN — progreso completo privado

- RF: RF-11. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/progress`. HTTP esperado: **200**.
- Dependencia: Paso 20 aprobado.
- Response esperada: respondidas=2 y selección original conservada.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Dos respondidas; Intento propio recuperado; Selección original intacta. Todas deben aprobar.
- Explicación: El progreso recupera las decisiones reales y no revela calificaciones.
- Captura: `principal_21.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 22. MAIN — cierre ajeno rechazado

- RF: RF-12. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/attempts/{{id_intento}}/finish`. HTTP esperado: **403**.
- Dependencia: Paso 21 aprobado.
- Response esperada: 403 al cierre por estudiante ajeno.
- Test Results: HTTP exacto 403; Sin credenciales privadas; Sin notas ni correcciones; Error sin datos académicos. Todas deben aprobar.
- Explicación: Autenticarse no concede titularidad sobre cualquier intento.
- Captura: `principal_22.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 23. MAIN — cierre titular

- RF: RF-12/RF-23. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/attempts/{{id_intento}}/finish`. HTTP esperado: **200**.
- Dependencia: Paso 22 aprobado.
- Response esperada: estado=FINALIZADO y fecha de cierre.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Finalizado. Todas deben aprobar.
- Explicación: Cerrar no calcula ni publica una nota; el cálculo docente es posterior.
- Captura: `principal_23.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 24. MAIN — cierre idempotente

- RF: RF-12. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/attempts/{{id_intento}}/finish`. HTTP esperado: **200**.
- Dependencia: Paso 23 aprobado.
- Response esperada: Mismo cierre y fecha que la solicitud anterior.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Cierre íntegramente idempotente. Todas deben aprobar.
- Explicación: El cierre repetido es idempotente y no cambia su historia.
- Captura: `principal_24.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 25. MAIN — escenario cerrado

- RF: RF-10/RF-12. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario`. HTTP esperado: **409**.
- Dependencia: Paso 24 aprobado.
- Response esperada: 409: no continúa una simulación cerrada.
- Test Results: HTTP exacto 409; Contrato JSON; Sin credenciales privadas; Sin notas ni correcciones; Error sin datos académicos. Todas deben aprobar.
- Explicación: El cierre confirmado impide seguir respondiendo o navegar el intento.
- Captura: `principal_25.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 26. MAIN — login docente ajeno

- RF: RF-02. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/personal`. HTTP esperado: **200**.
- Dependencia: Paso 25 aprobado.
- Response esperada: Token de un docente distinto, capturado para la negativa.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: La prueba usa un docente real ajeno al ámbito académico.
- Captura: `principal_26.png`; solo estado y Test Results; ocultar Response del login.

### 27. MAIN — cerrado sin resultado [GET 404]

- RF: RF-13/RF-24. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/intentos/{{id_intento}}/resultado-tecnico`. HTTP esperado: **404**.
- Dependencia: Paso 26 aprobado.
- Response esperada: 404: todavía no existe resultado técnico.
- Test Results: HTTP exacto 404; Sin credenciales privadas; Error sin datos académicos. Todas deben aprobar.
- Explicación: La consulta no calcula: el cierre dejó el intento sin calificación automática.
- Captura: `principal_27.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 28. MAIN — evaluar cerrado [POST 200]

- RF: RF-13/RF-24. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/intentos/{{id_intento}}/resultado-tecnico`. HTTP esperado: **200**.
- Dependencia: Paso 27 aprobado.
- Response esperada: Resultado técnico 100.00, oficial=false, versión histórica.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Técnico, no oficial; Versión histórica; Nota decimal como cadena; Sin código ni credenciales; Sin caché; Fracciones exactas como cadenas; Resultado conocido LAB, no oficial; Mismo intento y resultado NO oficial. Todas deben aprobar.
- Explicación: POST explícito del docente calcula las dos respuestas correctas de esta fixture; no es nota oficial.
- Captura: `principal_28.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 29. MAIN — reintento idempotente [POST 200]

- RF: RF-13/RF-24. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/intentos/{{id_intento}}/resultado-tecnico`. HTTP esperado: **200**.
- Dependencia: Paso 28 aprobado.
- Response esperada: Mismo id_resultado, huella y fecha de cálculo.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Técnico, no oficial; Versión histórica; Nota decimal como cadena; Sin código ni credenciales; Sin caché; Fracciones exactas como cadenas; Mismo resultado y fecha; Mismo intento y resultado NO oficial. Todas deben aprobar.
- Explicación: Reintentar el comando no duplica ni recalifica el resultado.
- Captura: `principal_29.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 30. MAIN — recuperar resultado técnico persistido

- RF: RF-13/RF-24. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/intentos/{{id_intento}}/resultado-tecnico`. HTTP esperado: **200**.
- Dependencia: Paso 29 aprobado.
- Response esperada: Mismo resultado persistido, recuperado por GET.
- Test Results: HTTP exacto 200; Contrato JSON; Sin credenciales privadas; Técnico, no oficial; Versión histórica; Nota decimal como cadena; Sin código ni credenciales; Sin caché; Fracciones exactas como cadenas; Mismo intento y resultado NO oficial; Resultado persistido idéntico. Todas deben aprobar.
- Explicación: Una solicitud SQL independiente recupera el resultado sin generarlo de nuevo.
- Captura: `principal_30.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 31. MAIN — rechazar evaluación por estudiante

- RF: RF-02/RF-13. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/intentos/{{id_intento}}/resultado-tecnico`. HTTP esperado: **403**.
- Dependencia: Paso 30 aprobado.
- Response esperada: 403: un estudiante no puede ejecutar evaluación docente.
- Test Results: HTTP exacto 403; Sin credenciales privadas; Error sin datos académicos. Todas deben aprobar.
- Explicación: El permiso se comprueba en el servidor, no se deduce del conocimiento de un UUID.
- Captura: `principal_31.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 32. MAIN — rechazar evaluación por docente ajeno

- RF: RF-13/RF-15. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/intentos/{{id_intento}}/resultado-tecnico`. HTTP esperado: **403**.
- Dependencia: Paso 31 aprobado.
- Response esperada: 403: docente fuera del ámbito de sesión/caso/grupo.
- Test Results: HTTP exacto 403; Sin credenciales privadas; Error sin datos académicos. Todas deben aprobar.
- Explicación: El rol docente no concede acceso a recursos ajenos.
- Captura: `principal_32.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

## NUCLEAR DESKTOP — 2 Publicación y reportes RF-16

Archivo: `Proyecto_Nuclear_reportes_oficiales.postman_collection.json`. Environment: el único generado para **reportes**.

### 01. MAIN — login docente

- RF: RF-02. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/personal`. HTTP esperado: **200**.
- Dependencia: Preparar/importar y seleccionar este Environment.
- Response esperada: JWT docente capturado.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Login real; no capturar el token en la evidencia.
- Captura: `reportes_01.png`; solo estado y Test Results; ocultar Response del login.

### 02. MAIN — login estudiante

- RF: RF-01. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/estudiantes`. HTTP esperado: **200**.
- Dependencia: Paso 1 aprobado.
- Response esperada: JWT del estudiante titular capturado.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Esta identidad comprobará la consulta privada y la negativa de exportación.
- Captura: `reportes_02.png`; solo estado y Test Results; ocultar Response del login.

### 03. MAIN — login docente ajeno

- RF: RF-02. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/personal`. HTTP esperado: **200**.
- Dependencia: Paso 2 aprobado.
- Response esperada: JWT de un docente ajeno capturado.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: No concede ámbito sobre la sesión del laboratorio.
- Captura: `reportes_03.png`; solo estado y Test Results; ocultar Response del login.

### 04. 1 — revisar cohorte y capturar hash

- RF: RF-13/RF-24. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/consolidacion`. HTTP esperado: **200**.
- Dependencia: Paso 3 aprobado.
- Response esperada: Cohorte publicable y nota técnica 33.33; captura de revisión_sha256.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Todas resueltas. Todas deben aprobar.
- Explicación: La fixture tiene un intento VENCIDO con una respuesta de tres; aún no está publicado.
- Captura: `reportes_04.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 05. 2 — autorizar publicación completa

- RF: RF-13/RF-24/RF-27. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/publicaciones`. HTTP esperado: **200**.
- Dependencia: Paso 4 aprobado.
- Response esperada: oficial=true, publicación v1 y hash de revisión autorizado.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Oficial por autorización explícita; Sin duplicados. Todas deben aprobar.
- Explicación: El docente publica expresamente toda la cohorte; es un POST que escribe publicación y aviso internos.
- Captura: `reportes_05.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 06. 3 — reintento de misma publicación

- RF: RF-13/RF-27. Superficie: app.main.
- Operación: `POST {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/publicaciones`. HTTP esperado: **200**.
- Dependencia: Paso 5 aprobado.
- Response esperada: Mismo id de publicación.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Misma publicación. Todas deben aprobar.
- Explicación: Repetir la misma autorización no duplica publicación ni avisos.
- Captura: `reportes_06.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 07. 4 — lectura oficial docente

- RF: RF-13/RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/publicaciones`. HTTP esperado: **200**.
- Dependencia: Paso 6 aprobado.
- Response esperada: Publicación oficial exacta; captura id, versión y huella.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Publicación autorizada. Todas deben aprobar.
- Explicación: Esta fuente inmutable es la que deben usar los dos archivos.
- Captura: `reportes_07.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 08. 5 — consulta privada titular

- RF: RF-14. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/convocatorias/{{convocatoria_id}}/resultado`. HTTP esperado: **200**.
- Dependencia: Paso 7 aprobado.
- Response esperada: Resultado propio oficial 33.33.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Oficial y decimal. Todas deben aprobar.
- Explicación: Solo el estudiante titular consulta su fila, sin acceso a las de otros.
- Captura: `reportes_08.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 09. 6 — docente ajeno rechazado

- RF: RF-15/RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/publicaciones`. HTTP esperado: **403**.
- Dependencia: Paso 8 aprobado.
- Response esperada: 403 para docente ajeno.
- Test Results: HTTP exacto 403; Sin credenciales privadas; Error sin datos académicos. Todas deben aprobar.
- Explicación: La publicación no es un recurso público por conocer el identificador.
- Captura: `reportes_09.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 10. 7 — sin autenticación

- RF: RF-02/RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{sesion_id}}/evaluacion/publicaciones`. HTTP esperado: **401**.
- Dependencia: Paso 9 aprobado.
- Response esperada: 401 sin autenticación.
- Test Results: HTTP exacto 401; Sin credenciales privadas; Error sin datos académicos. Todas deben aprobar.
- Explicación: Este rechazo es una prueba aprobada, no un fallo de la demostración.
- Captura: `reportes_10.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 11. RF16 — descargar XLSX

- RF: RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/seguimiento/sesiones/{{sesion_id}}/reporte?formato=xlsx`. HTTP esperado: **200**.
- Dependencia: Paso 10 aprobado.
- Response esperada: Binario XLSX no vacío y cabeceras de la publicación capturada.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Binario no vacío; MIME correcto; Descarga adjunta; Publicación exacta; Privado. Todas deben aprobar.
- Explicación: Guardar con Send and Download y abrir Resultados: PARCIAL 33.33, misma publicación.
- Captura: `reportes_11.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 12. RF16 — descargar PDF

- RF: RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/seguimiento/sesiones/{{sesion_id}}/reporte?formato=pdf`. HTTP esperado: **200**.
- Dependencia: Paso 11 aprobado.
- Response esperada: PDF no vacío y cabeceras de la misma publicación.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Binario no vacío; MIME correcto; Descarga adjunta; Publicación exacta; Privado. Todas deben aprobar.
- Explicación: Abrir el PDF y comparar id/versión/nota con Excel; no recalcula calificaciones.
- Captura: `reportes_12.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 13. RF16 — rechazo sin JWT

- RF: RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/seguimiento/sesiones/{{sesion_id}}/reporte?formato=xlsx`. HTTP esperado: **401**.
- Dependencia: Paso 12 aprobado.
- Response esperada: 401 y JSON de error, sin archivo adjunto.
- Test Results: HTTP exacto 401; Sin credenciales privadas; No descarga datos; Error sin datos académicos. Todas deben aprobar.
- Explicación: La exportación requiere JWT válido.
- Captura: `reportes_13.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 14. RF16 — rechazo docente ajeno

- RF: RF-15/RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/seguimiento/sesiones/{{sesion_id}}/reporte?formato=xlsx`. HTTP esperado: **403**.
- Dependencia: Paso 13 aprobado.
- Response esperada: 403 y ningún archivo adjunto.
- Test Results: HTTP exacto 403; Sin credenciales privadas; No descarga datos; Error sin datos académicos. Todas deben aprobar.
- Explicación: Se rechaza al docente ajeno aunque esté autenticado.
- Captura: `reportes_14.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 15. RF16 — rechazo estudiante

- RF: RF-02/RF-16. Superficie: app.main.
- Operación: `GET {{base_url}}/api/v1/identity/seguimiento/sesiones/{{sesion_id}}/reporte?formato=xlsx`. HTTP esperado: **403**.
- Dependencia: Paso 14 aprobado.
- Response esperada: 403 y ningún archivo adjunto.
- Test Results: HTTP exacto 403; Sin credenciales privadas; No descarga datos; Error sin datos académicos. Todas deben aprobar.
- Explicación: El estudiante puede consultar su resultado, pero no exportar el reporte docente de la sesión.
- Captura: `reportes_15.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

## NUCLEAR DESKTOP — 3 Worker RF-19

Archivo: `Proyecto_Nuclear_worker_20261109.postman_collection.json`. Environment: el único generado para **worker**.

### 01. MAIN — login docente

- RF: RF-02. Superficie: app.main.
- Operación: `POST {{base_url}}/api/v1/identity/auth/personal`. HTTP esperado: **200**.
- Dependencia: Preparar/importar y seleccionar este Environment.
- Response esperada: JWT docente capturado.
- Test Results: HTTP exacto 200; Sin credenciales privadas. Todas deben aprobar.
- Explicación: Login real con credencial sintética generada por el preparador.
- Captura: `worker_01.png`; solo estado y Test Results; ocultar Response del login.

### 02. WORKER 1 — antes de ejecutar: EN_CURSO

- RF: RF-19. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{worker_sesion_id}}`. HTTP esperado: **200**.
- Dependencia: Paso 1 aprobado.
- Response esperada: Sesión EN_CURSO y versión exacta.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Estado esperado; Edición histórica. Todas deben aprobar.
- Explicación: Está vencida desde hace más de 24 horas; la fecha es preparación LAB para no esperar un día.
- Captura: `worker_02.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 03. WORKER 2 — después de w: FINALIZADO

- RF: RF-19. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{worker_sesion_id}}`. HTTP esperado: **200**.
- Dependencia: Paso 2 aprobado. Ejecutar w en la consola antes de Send.
- Response esperada: Sesión FINALIZADO tras ejecutar w en la consola.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Estado esperado; Edición histórica. Todas deben aprobar.
- Explicación: El Worker real persistió el cierre, auditoría y aviso; no evaluó intentos ni publicó notas.
- Captura: `worker_03.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.

### 04. WORKER 3 — después de segundo w: FINALIZADO

- RF: RF-19. Superficie: app.main.
- Operación: `GET {{base_url}}/scheduling/sesiones/{{worker_sesion_id}}`. HTTP esperado: **200**.
- Dependencia: Paso 3 aprobado. Ejecutar w en la consola antes de Send.
- Response esperada: FINALIZADO de nuevo tras ejecutar w por segunda vez.
- Test Results: HTTP exacto 200; Sin credenciales privadas; Estado esperado; Edición histórica. Todas deben aprobar.
- Explicación: La segunda ejecución cierra cero sesiones y mantiene un solo efecto histórico.
- Captura: `worker_04.png`; estado, Response sintética y Test Results; ocultar cabeceras de autorización.
