# Segunda auditoría integral del Simulador de Psicología Social

- **Fecha de trabajo** · 24 de noviembre de 2026, Colombia
- **Rama de trabajo** · `maicol`, revisión base `e7f1b75`, con las correcciones locales de la primera auditoría
- **Entorno** · PostgreSQL 17.11, Angular 21, FastAPI y Nginx en Docker, con 5.004 cuentas sintéticas
- **Versión evaluada** · cambios locales de esta segunda auditoría

## 1. Resumen ejecutivo

Se corrigieron la multiplicación de consultas del directorio, el recorrido periódico de intentos activos, el desbordamiento a 320 px y el foco al cambiar de formulario. Se reforzaron las respuestas de error, la caché de recursos versionados, el acceso por Nginx y el procesamiento del correo. La aplicación conserva los módulos y los flujos académicos existentes.

Con 5.000 resultados y 12 solicitudes simultáneas, el p95 del directorio pasó de 7.620,47 a 953,99 ms en la repetición final. El comprobante SMTP en PostgreSQL confirma el comportamiento del flujo en laboratorio. La cuenta Gmail existente negoció TLS 1.3 y rechazó la autenticación con SMTP 534 (5.7.9). La entrega nueva al buzón oficial queda pendiente de la aceptación de Gmail.

- [Primera auditoría y configuración documentada](AUDITORIA_INTEGRAL_20261124.md)
- [Definiciones de los 115 disparadores y las nueve vistas](SEGUNDA_AUDITORIA_POSTGRES_20261124.md)
- [Galería de 15 correos con HTML y texto plano](SEGUNDA_AUDITORIA_CORREOS_20261124.html)

## 2. Diagnóstico, gravedad y causa

| Gravedad | Hallazgo | Causa | Corrección y evidencia |
|---|---|---|---|
| Alta | Latencia creciente del directorio | Cada fila repetía consultas de permisos, identidad y primer ingreso | Cuatro lecturas agrupadas para los detalles. La prueba HTTP compara 1 y 50 usuarios y comprueba el mismo total de consultas. |
| Alta | Trabajo periódico proporcional al total de intentos activos | El worker leía todos y filtraba sus fechas en Python | PostgreSQL selecciona los vencidos con un índice parcial por vencimiento. |
| Alta | Gmail rechazó la autenticación existente | La cuenta presentó SMTP 534 después de negociar TLS y validar el certificado. La causa dentro de la cuenta quedó sin determinar. | Registro operativo diferenciado para rechazo de autenticación y certificado. El servicio conserva la configuración y los avisos pendientes. |
| Alta | Avisos críticos en herramientas de desarrollo | La instalación inicial resolvió Vitest y su cobertura en versiones afectadas | Compatibilidad probada en la rama 4.1 con versiones fijadas. El segundo escaneo npm informó cero avisos críticos. |
| Alta | Nginx mantenía una IP anterior tras recrear la API | El nombre del servicio Docker se resolvía al iniciar Nginx | Resolución periódica en el DNS interno. Al cambiar la IP de la API, Nginx volvió a entregar HTTP 200 desde el mismo contenedor. |
| Alta | Datos de validación reenviados al cliente por defecto | El serializador de errores de FastAPI incluye el valor inválido y puede incluir contexto | Respuesta con ubicación, tipo y mensaje de interfaz. Prueba HTTP con un valor sintético. |
| Media | Control de acceso HTTP y de caché incompleto | Proxy genérico para toda la aplicación | Límite en POST de autenticación, CSP para el frontend, HTML revalidable y caché inmutable para archivos con huella. |
| Media | Desbordamiento horizontal a 320 px y foco difícil de seguir | Ancho mínimo rígido con barra de desplazamiento, encabezados inflexibles y pasos del formulario que reemplazan el control activo | Ajustes del tamaño base, cabecera, botones y foco. Barrido del navegador y prueba Angular. |
| Media | Un diálogo del simulador quedaba abierto tras expirar la sesión | La navegación al login podía destruir la vista sin cerrar el diálogo global | Cierre de diálogos al volver al login y prueba de la navegación con parámetros. |
| Media | Una respuesta HTTP tardía podía cerrar una sesión recién iniciada | El interceptor comparaba el estado HTTP con el token de la solicitud sin comprobar qué sesión seguía activa | Solo un rechazo del token vigente cierra la sesión. Pruebas con respuestas de ambas sesiones. |
| Media | Reintentos de correo con intervalo fijo y una conexión por mensaje | El envío abría y cerraba la sesión SMTP en cada operación | Intervalos de 1, 2, 4, 8, 16, 32 y hasta 60 minutos. Reutilización del canal dentro de cada lote, con nueva conexión tras un fallo. |
| Media | Los mensajes de correo tenían una presentación uniforme | El HTML tenía el mismo orden y estilo para datos con funciones distintas | Categoría, previsualización de bandeja, fechas formateadas, datos operativos destacados y códigos con jerarquía propia. |
| Baja | Mensajes de red difíciles de interpretar | Los estados HTTP llegaban a la interfaz con texto de infraestructura o duplicado | Instrucción para recuperar la conexión y aviso único cuando hay demasiados intentos. |

## 3. Arquitectura, backend y mantenibilidad

El monolito modular conserva los dominios de casos, identidad, programación y participación. El directorio compone un resultado de lectura en un solo módulo y reutiliza la lógica de permisos efectivos para listar, crear y editar usuarios. Agrupa las consultas por ID y selecciona las columnas del directorio. La paginación administrativa conserva la búsqueda, el orden, el tamaño máximo de 50, los totales, los permisos individuales y la compatibilidad con la ruta histórica.

Se diferenció `/health`, que comprueba el proceso HTTP, de `/ready`, que comprueba una conexión a PostgreSQL. Docker Compose comprueba `/ready`. Al detener PostgreSQL en la prueba, `/health` mantuvo HTTP 200 y `/ready` devolvió HTTP 503 con el mensaje genérico. Al levantar la base, `/ready` volvió a HTTP 200. El proxy conserva las rutas existentes y actualiza la IP del servicio. Los errores de persistencia enviados al navegador usan un texto genérico y el registro recoge la clase del error sin imprimir parámetros SQL.

| Área | Archivos intervenidos en esta ronda |
|---|---|
| Identidad y directorio | `backend/app/modules/identity/api/users_management_router.py`, `backend/app/modules/identity/infrastructure/user_catalog.py` |
| Aplicación y conexiones | `backend/app/main.py`, `backend/app/db/session.py`, `docker-compose.yml` |
| Vencimiento de intentos | `backend/app/modules/scheduling/infrastructure/worker_runner.py`, `backend/alembic/versions/20261124_index_attempt_deadline.py` |
| Correo | `backend/app/modules/scheduling/infrastructure/mail_delivery.py`, `backend/app/modules/scheduling/infrastructure/mail_templates.py` |
| Frontend y proxy | `frontend/nginx.conf`, `frontend/angular.json`, `frontend/src/styles.scss`, `frontend/src/app/app.ts`, `frontend/src/app/layout/shell.component.scss`, `frontend/src/app/core/{api-error,auth.interceptor}.ts`, `frontend/src/app/pages/login/login.component.{ts,html}` |
| Pruebas | `backend/tests/integration/test_admin_teacher_directory.py`, `backend/tests/integration/test_durable_mail.py`, pruebas de migración, transporte y dependencias de Vitest en `frontend/package.json` y `frontend/package-lock.json`, `frontend/tsconfig.spec.json`, `frontend/vitest.config.ts` y cinco archivos `*.spec.ts` |

## 4. PostgreSQL, disparadores y vistas

El índice parcial `ix_intento_activo_vencimiento` cubre los intentos `EN_CURSO` por instante de vencimiento e ID. El cálculo mantiene los microsegundos y utiliza la zona que el sistema aplica al persistir fechas. Se restauró una copia de laboratorio en una base nueva y se comprobaron la revisión de Alembic, 5.004 usuarios y una participación.

Los **115 disparadores de aplicación** aparecen habilitados en el catálogo. PostgreSQL reportó también **372 disparadores internos** de integridad. La suite PostgreSQL verificó migración de ida y vuelta, trazabilidad, inmutabilidad, precedencia de permisos, relaciones y condiciones negativas de conjuntos representativos. La inspección individual del catálogo cubre 115 declaraciones. La verificación DML individual de cada disparador y cada combinación de evento sigue pendiente.

| Vista | Filas en la lectura de laboratorio | Evidencia funcional adicional |
|---|---:|---|
| `vw_auditoria_primer_ingreso` | 5.004 | Regresión de primer ingreso y verificación. |
| `vw_catalogo_casos` | 2 | Estados, versiones y casos de prueba. |
| `vw_matriz_permisos_usuarios` | 5.004 | Permisos heredados y precedencia de excepciones individuales. |
| `vw_resumen_sesiones` | 1 | Relaciones con caso, espacio y sesión. |
| `vw_seguimiento_participacion` | 2 | Estado académico y relaciones de participación. |
| `vw_trazabilidad_correos_y_notificaciones` | 0 | Alta y envío con registros poblados en la suite SMTP desechable. |
| `vw_trazabilidad_estudiante_360` | 5.002 | Matrícula y trazabilidad con datos sintéticos. |
| `vw_trazabilidad_global` | 5.050 | Eventos con relaciones y mutaciones de prueba. |
| `vw_trazabilidad_intentos_decisiones` | 2 | Conteo independiente de borradores, cambios y pasos. |

Las cifras de esta tabla corresponden a una lectura posterior al recorrido visual. Las pruebas de comportamiento están en `test_db_views_and_triggers_traceability.py` y los escenarios de integración relacionados. Los planes de coste de todas las vistas bajo volumen institucional son una medición pendiente.

## 5. Frontend, usabilidad, accesibilidad y respuesta al tamaño de pantalla

Se conservó la estética oscura con cian y la apariencia lúdica del simulador. La cabecera cede espacio al título mientras los botones mantienen su tamaño. En pantallas estrechas se permite que el subtítulo ocupe dos líneas. En horizontal con poca altura el encabezado se desplaza con el documento y el menú inferior ocupa menos espacio. El enlace para saltar al contenido muestra el foco y se ajustó el espacio de desplazamiento junto a ambas barras.

Se probaron **16 vistas** en cada uno de estos anchos en píxeles **320, 360, 375, 390, 414, 768, 1024, 1280, 1366, 1440, 1920 y 2560**. Se incluyeron login, recuperación, administración, permisos, espacios, casos, editor, detalle, grafo, sesiones, convocatorias, evaluación, grupos, seguimiento, portal del estudiante y simulador. En el barrido inicial, nueve vistas desbordaban 8 px a 320 px. En el barrido corregido, el documento presentó un desbordamiento de 0 px en los 192 pares de vista y ancho. Se comprobó también seguimiento a 844 × 390 px. El desbordamiento de carruseles y tablas dentro de sus propios contenedores es intencional.

El teclado activó el salto al contenido, las pestañas de grupos y el diálogo «Antes de empezar». Se comprobó el foco en el título de recuperación de contraseña y en el encabezado del diálogo. Escape devolvió el foco al botón de inicio. Se seleccionó una carta con Espacio, se lanzó con Enter y se comprobó que la primera elección abrió la segunda escena. El Joker pasó de una ayuda disponible a cero y mostró la comparación. En el recorrido final se entregaron dos respuestas y la cuenta de laboratorio recibió 100/100. Las capturas de inicio de sesión, recuperación, administración, diálogo previo y correos se registraron en esta sesión de navegador. La verificación de contraste en todas las pantallas, la dictación y los lectores NVDA/VoiceOver requieren pruebas adicionales para una evaluación completa. [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

## 6. Seguridad y correo electrónico

El proxy aplica una política de contenido y limita por IP las solicitudes POST a la familia de autenticación, con una media de 60 por minuto y ráfaga de 24. La prueba con formularios vacíos obtuvo 25 respuestas de validación y después HTTP 429 con `Retry-After: 1` y `no-store`. El frontend presenta una instrucción de espera. Las cabeceras de API excluyen la caché de datos autenticados. Las hojas y los scripts con huella permanecen inmutables y un archivo con huella que no existe devuelve 404. La API local directa queda en loopback. En una futura publicación detrás de otro proxy, la IP de cliente se debe configurar únicamente desde proxies de confianza. [Módulo de límites de Nginx](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html) · [Resolución de servicios en Nginx](https://nginx.org/en/docs/http/ngx_http_upstream_module.html) · [OWASP Top 10](https://owasp.org/projects/top-ten/)

La revisión final de npm detectó **0 avisos de producción** y **16 avisos moderados** de desarrollo tras actualizar Vitest y su complemento de cobertura a 4.1.12. La propuesta automática de npm para varios avisos recomienda retroceder Angular CLI a una versión mayor anterior. Se conservó Angular 21 y se declaró explícitamente la dependencia de animaciones que requiere la aplicación. [Documentación de npm audit](https://docs.npmjs.com/cli/commands/npm-audit/) · [Avisos de Vitest](https://github.com/vitest-dev/vitest/security/advisories)

### Verificación de Gmail y protección de credenciales

| Comprobación | Resultado |
|---|---|
| Configuración activa | `smtp.gmail.com`, STARTTLS en 587, usuario y remitente `adminsps8@gmail.com`. Validación del certificado y hostname habilitada. |
| Coincidencia con el archivo privado | API y worker cargan la misma credencial configurada en `.env`. Comparación en memoria sin registrar la huella ni el valor. |
| Exclusión de Git | `.env` y `frontend/.env` ignorados. Cero rutas coincidentes rastreadas. |
| Ejemplo de entorno | Los campos de SMTP, cifrado de la cola y JWT están vacíos. |
| Historial local y GitHub | 2.933 objetos en la copia local y 2.933 en el clon espejo de las referencias publicadas. Cero coincidencias exactas con la credencial activa. Alcance limitado a los objetos disponibles en esas copias. |
| Frontend y registros | 157 archivos del frontend, 9.031.680 bytes del archivo de los recursos servidos y hasta 2.500 líneas por servicio de API y worker. Cero coincidencias exactas. |
| TLS real | TLS 1.3 con certificado validado. El servidor respondió a NOOP. |
| Autenticación real | Gmail rechazó AUTH LOGIN con SMTP 534 (5.7.9) usando la credencial actual. Un intento de enviar al mismo buzón oficial terminó con una desconexión y sin aceptación de DATA confirmada. |
| Recepción del nuevo mensaje | Pendiente. La primera auditoría documenta una entrega anterior confirmada por el usuario. |
| Estado de la contraseña | Se conservó el valor configurado. La verificación del rechazo de Gmail es una dependencia de la cuenta. |

Los códigos de primer ingreso y recuperación mantienen su vigencia de 15 minutos y el límite de intentos aplicado por el servidor. La convocatoria conserva la ventana de acceso de la sesión y el código individual asociado al destinatario. El laboratorio ejecutó generación, entrega por SMTP local, validación, expiración y reintento con cuentas sintéticas. La cola conserva el cifrado del contenido, el bloqueo por registro y la exclusión de avisos ya aceptados. La protección evita duplicados en el comportamiento probado. Existe una incertidumbre propia del transporte si el servidor acepta DATA y la confirmación se pierde antes de que SPS la reciba o la registre. [Códigos SMTP de Gmail](https://support.google.com/mail/answer/3726730?hl=es)

El capturador SMTP recibió dos mensajes en una misma conexión. Los fallos de autenticación o certificado tienen un código operativo distinto y los reintentos progresivos cubren fallos transitorios. Google documenta restricciones para las cuentas personales de Gmail, entre ellas un límite de 500 envíos diarios. La capacidad de correo para muchas cohortes depende del proveedor y queda fuera de la prueba de volumen. [Límites de Gmail](https://support.google.com/mail/answer/22839?hl=es) · [Contraseñas de aplicación](https://support.google.com/accounts/answer/185833?hl=es)

### Presentación de los correos

La [galería](SEGUNDA_AUDITORIA_CORREOS_20261124.html) contiene 15 ejemplos producidos por el código real. Incluye altas de los tres roles, primer ingreso, recuperación, matrícula, creación de casos, rúbrica, publicación, convocatoria, retiro, cambio de sesión, calificación, retroalimentación y prueba de diagnóstico.

El correo usa un encabezado oscuro con acento cian, una categoría visible, una previsualización de bandeja, saludo, título, bloques de datos con fechas y zona horaria, código destacado cuando corresponde, botón y enlace de respaldo. Conserva su alternativa en texto plano. El logotipo se carga cuando se configura una URL HTTPS y el texto institucional mantiene la identificación si el cliente bloquea imágenes. Los datos variables se escapan. Las 15 previsualizaciones se abrieron en el navegador con HTML generado por SPS. La presentación nativa en Gmail, Outlook y dispositivos físicos sigue pendiente para la plantilla nueva.

## 7. Rendimiento y escalabilidad medidos

Cada celda se calculó sobre 24 solicitudes autenticadas de 50 elementos, después de una petición de calentamiento por grupo. Se usó PostgreSQL en Docker con 500 y 5.000 coincidencias y concurrencias de 1, 6 y 12. La ejecución mide el recorrido HTTP y la API en el entorno local. Los tiempos se expresan en milisegundos.

| Coincidencias | Concurrencia | Mediana antes → después | p95 antes → después | Solicitudes/s antes → después |
|---:|---:|---:|---:|---:|
| 500 | 1 | 417,98 → 58,06 | 552,71 → 77,41 | 2,28 → 16,22 |
| 500 | 6 | 3.425,41 → 297,81 | 3.889,82 → 442,71 | 1,72 → 19,26 |
| 500 | 12 | 6.993,88 → 606,57 | 7.281,99 → 721,83 | 1,70 → 18,12 |
| 5.000 | 1 | 445,49 → 60,67 | 644,67 → 70,06 | 2,12 → 16,32 |
| 5.000 | 6 | 3.288,03 → 334,85 | 3.415,12 → 379,21 | 1,81 → 17,95 |
| 5.000 | 12 | 7.207,49 → 743,81 | 7.620,47 → 953,99 | 1,65 → 14,35 |

La primera repetición coincidió con compilaciones del equipo y registró dos p95 de 3.740,14 y 1.771,38 ms en las últimas dos celdas de 5.000 coincidencias. La tabla usa la nueva repetición con las compilaciones terminadas, en la que mejoraron las seis medianas y los seis p95. Estos resultados describen lotes cortos en una estación de trabajo. Una evaluación de capacidad requiere intervalos largos, datos representativos y medición de CPU, memoria, conexiones y puestos concurrentes.

Para el worker, la misma forma de consulta sobre una tabla temporal de 100.000 intentos devolvía **50.000 candidatos** en **34,852 ms**. Con el filtro y el índice devolvió **100 vencidos** en **0,287 ms**. Son tiempos de ejecución de PostgreSQL recopilados con EXPLAIN ANALYZE. El entorno pequeño del simulador eligió un recorrido secuencial con una sola fila, una decisión esperable del planificador.

La compilación final de frontend produjo **762,85 kB iniciales** y **185,76 kB de transferencia estimada**. Los módulos de página se cargan bajo demanda. Las APIs, el HTML y los archivos versionados tienen políticas de caché distintas. Queda pendiente medir LCP, CLS, INP y Lighthouse bajo un perfil móvil reproducible y recopilar métricas reales de usuarios.

## 8. Matriz de trazabilidad y aceptación

| Requisito | Funcionalidad | Caso de prueba | Datos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|---|
| Paginación escalable | Directorio | Comparar páginas de 1 y 50 | 54 cuentas PG | Coste fijo, permisos exactos | Igual número de SELECT en ambos tamaños, permisos y UUID correctos | Verificado | `test_admin_teacher_directory.py` |
| Latencia bajo carga | Directorio | Progresión 1, 6, 12 | 500 y 5.000 coincidencias | Mejorar mediana y p95 | Mejoraron mediana y p95 en las seis celdas finales. | Verificado en laboratorio | Tabla de rendimiento |
| Expiración | Worker | Comparar plan con y sin filtro | 100.000 intentos temporales | Seleccionar solo vencidos y mantener precisión | 100 vencidos y precisión de microsegundos | Verificado | EXPLAIN y prueba de precisión |
| Restitución | Base de datos | Exportar y restaurar | 5.004 cuentas sintéticas | Migración y cantidades preservadas | Revisión y cantidades correctas | Verificado | Salida de `pg_restore` y consultas |
| Integridad y trazabilidad | Vistas y disparadores | Lectura, cambios de datos, integridad e inmutabilidad | PostgreSQL desechable | Definiciones habilitadas y registros coherentes | 9 vistas, 115 disparadores habilitados y escenarios de integración representativos | Parcial | Inventario y pruebas PostgreSQL |
| Privacidad | Validación HTTP | Enviar un tipo inválido | Texto ficticio | Respuesta clara sin valor reflejado | HTTP 422 con ubicación de campo | Verificado | `test_admin_teacher_directory.py` |
| Continuidad de sesión | Interceptor y diálogos | HTTP 401 tardío y regreso al login | Dos sesiones ficticias y un diálogo | Desconectar solo la sesión rechazada y cerrar los diálogos al salir | Una respuesta obsoleta conserva la nueva sesión y la navegación al login limpia los diálogos | Verificado | `auth.interceptor.spec.ts` y `app.spec.ts` |
| Carga y seguridad web | Nginx | Navegación SPA, archivo versionado, recurso ausente, tasa y cambio de IP | Angular compilado y API en Docker | CSP y caché coherentes, HTTP 404 y 429, recuperación de conexión | Cabeceras y estados esperados. Recuperación sin recrear Nginx. | Verificado | Nginx y comprobaciones HTTP |
| Teclado | Portal del estudiante | Abrir, cerrar y seleccionar | Convocatoria sintética | Foco dentro del diálogo y retorno al botón | Foco en título y retorno a inicio con Escape | Verificado | Navegador |
| Adaptación | UI de tres roles | 12 anchos y un perfil horizontal | 16 vistas | Cero desbordamiento de documento | Cero en 192 combinaciones | Verificado | Barrido DOM |
| Simulación | Escena, carta y Joker | Entrar, comparar, lanzar y entregar | Caso Asch sintético | Escena siguiente, progreso y resultado | 2 de 2 decisiones guardadas, entrega confirmada y 100/100 | Verificado | Navegador |
| Correo durable | Convocatoria y estado | Aceptación, fallo temporal y concurrencia | Capturador SMTP local | Destinatario correcto, HTML y texto, sin duplicado confirmado | Captura y estados coherentes | Verificado en laboratorio | `test_durable_mail.py` |
| Correo real | Gmail oficial | TLS y autenticación | Cuenta oficial existente | Autenticación aceptada y recepción | TLS 1.3, SMTP 534 | Bloqueado por Gmail | Diagnóstico del servidor |
| Presentación de correo | 15 ejemplos | Apertura de cada asunto | Datos sintéticos | HTML legible y alternativa plana | Las 15 plantillas abrieron en Chromium | Parcial | Galería, validación en clientes nativos pendiente |
| Cumplimiento AA | Accesibilidad | Reglas axe y recorrido de teclado | Formularios críticos y portales | Nombres, etiquetas, orden y contraste | Comprobación parcial de reglas y teclado | Parcial | Spec Angular, capturas y recorrido |

## 9. Reproducción y límites

| Conjunto ejecutado | Resultado |
|---|---|
| Suite amplia del backend con cobertura | 976 aprobadas y 1.413 omitidas por configuración o dependencias opt-in. Cobertura agregada de sentencias y ramas de `app` del 53 %. |
| Selección de integración PostgreSQL y SMTP | 81 aprobadas. Incluye directorio real, vistas, disparadores, identidad y correo. |
| Angular, Vitest y axe-core | 13 aprobadas. Cobertura global de líneas del 8,35 % y de ramas del 10,28 %. La automatización de frontend se concentra en acceso, errores, sesiones, diálogos y paginación. |
| Compilación y ejecución | Imagen de API, worker y frontend compilada. `nginx -t` correcto. Disponibilidad, 429 y recuperación tras cambio de IP verificados. |

Las 81 pruebas de integración complementan la ejecución amplia y parte de sus casos pertenece a la misma suite. Los resultados se presentan por ejecución. Starlette emitió una advertencia de deprecación de su cliente de pruebas.

Desde la raíz del repositorio, el procedimiento de la [primera auditoría](AUDITORIA_INTEGRAL_20261124.md) documenta Docker, Alembic y la configuración de laboratorio. Aplique las migraciones en una copia separada antes de usar el healthcheck actualizado. Para compilar y ejecutar pruebas de frontend con Node 22 y el lockfile del proyecto:

```powershell
cd frontend
npm ci
npm run build -- --configuration production
npm test -- --watch=false --coverage
```

La suite de backend usa `pytest`, con una base de pruebas desechable y la opción documentada para PostgreSQL. El ensayo de cobertura usa `coverage run --branch --source=app -m pytest`. La segunda auditoría utilizó el proyecto Docker `sps-segunda-auditoria`, la API 8003 y la interfaz 4203. La configuración de Gmail y la base local principal se conservaron durante el trabajo. El entorno aislado sirve para reproducir la prueba con estudiantes de demostración.

Para validar la publicación institucional quedan pendientes acreditación completa de WCAG, pruebas en navegadores y clientes de correo nativos, pruebas de carga sostenida en infraestructura representativa y revisión de políticas de cuenta Gmail. Las reglas de SMTP son operativas únicamente cuando el proveedor acepta la autenticación. El enlace de producción debe apuntar a la URL institucional HTTPS. Mantenga las credenciales en variables privadas.

## 10. Tabla de evaluación de 1 a 5

La nota final es la media aritmética simple de los 22 criterios, redondeada a dos decimales. El valor 4 representa operación comprobada con carencias relevantes. El valor 5 requiere evidencia reproducible y cierre de las brechas del criterio. Cada incremento corresponde a evidencia observada. Los resultados limitados al laboratorio conservan esa limitación en la nota. Se conserva la referencia global de 4,11 informada en la primera auditoría.

| Criterio | Primera auditoría | Segunda auditoría | Objetivo | Justificación y brecha |
|---|---:|---:|---:|---:|---|
| Arquitectura de software | 4,1 | 4,3 | 5,0 | Se agrupó la lectura del directorio y se separó la disponibilidad. Falta verificar operación de varias réplicas y sus límites. |
| Base de datos | 4,3 | 4,6 | 5,0 | Índice medido, revisión reversible y restauración satisfactoria. Falta recuperación con volúmenes y condiciones de producción. |
| Disparadores | 4,3 | 4,4 | 5,0 | Inventario de 115 y pruebas representativas. Falta DML individual por evento y tabla. |
| Vistas | 4,3 | 4,4 | 5,0 | Las nueve vistas ejecutan y tienen inventario y pruebas de trazabilidad. Falta un plan y coste por vista bajo volumen institucional. |
| Backend | 4,1 | 4,5 | 5,0 | Consultas agrupadas, errores privados y disponibilidad comprobada. Falta ensayar fallos distribuidos y más recorridos opt-in. |
| Frontend | 4,2 | 4,4 | 5,0 | Se mejoraron los tamaños, el foco y los mensajes de recuperación. Falta ampliar la batería a módulos académicos. |
| Diseño visual | 4,2 | 4,3 | 5,0 | Se refinaron la cabecera, la densidad y la apariencia móvil. Falta evaluación con usuarios y diferentes motores. |
| Alineación de componentes | 4,3 | 4,5 | 5,0 | Fecha, navegación y acciones conservaron flujo y tamaño en el barrido. Faltan más combinaciones de textos largos y traducciones. |
| Consistencia visual | 4,2 | 4,4 | 5,0 | Ajustes transversales de marco, foco, navegación y tipografía. Falta cobertura completa de variantes y estados vacíos. |
| Usabilidad | 4,2 | 4,4 | 5,0 | Se comprobó el inicio y la guía de cartas. Falta una prueba con usuarios novatos y tareas cronometradas. |
| Experiencia del usuario | 4,2 | 4,4 | 5,0 | Cambios de formulario explicativos y flujo de decisiones comprobado. Falta validar recuperación de sesiones largas y reconexión. |
| Accesibilidad | 3,7 | 4,2 | 5,0 | Foco, teclado, etiquetas y pruebas puntuales. Requiere auditoría AA completa con tecnología de asistencia. |
| Diseño responsive | 4,2 | 4,6 | 5,0 | 16 vistas y 12 anchos sin desbordamiento de documento. Faltan dispositivos físicos, zoom alto y otros motores. |
| Seguridad | 3,9 | 4,3 | 5,0 | CSP, límites, validación sin datos y revisión de credenciales. Quedan avisos moderados de desarrollo y validación operativa en un proxy real. |
| Escalabilidad | 3,6 | 4,3 | 5,0 | Mejora medida con 5.000 cuentas y 12 solicitudes, carga del worker reducida. Falta ensayo prolongado y aumento progresivo por encima del alcance local. |
| Mantenibilidad | 4,1 | 4,4 | 5,0 | Proyección común, módulo localizado de correo, compilación y nuevas pruebas. Falta descomponer componentes con alto acoplamiento. |
| Servicio de correo electrónico | 4,3 | 4,0 | 5,0 | SMTP de laboratorio, reintentos y deduplicación probados. Gmail rechazó la autenticación en esta ronda, lo que rebaja la evaluación operativa. |
| Diseño de correos electrónicos | 4,1 | 4,6 | 5,0 | Los 15 ejemplos se renderizan con jerarquía y alternativa plana. Falta revisar Gmail y Outlook nativos para la nueva versión. |
| Rendimiento | 3,8 | 4,4 | 5,0 | Mejora de directorio, worker y caché medible. Faltan series prolongadas, métricas de usuario y memoria/CPU bajo carga. |
| Calidad del código | 4,1 | 4,4 | 5,0 | Tipado en compilación, lógica de consulta reutilizada y cambios con regresiones. Queda deuda en módulos extensos. |
| Pruebas de software | 4,0 | 4,3 | 5,0 | Más regresiones HTTP, SMTP, migraciones, navegador y Angular. Falta cobertura funcional amplia de Angular y de escenarios opt-in. |
| Funcionamiento general | 4,2 | 4,4 | 5,0 | Roles, consultas principales, inicio y decisiones verificados. La entrega Gmail y las pruebas institucionales siguen pendientes. |
| **Calificación definitiva** | **4,11** | **4,39** | **4,90–5,00** | El objetivo queda pendiente de la evidencia y de los bloqueos indicados. |

## 11. Comprobación posterior de funcionamiento

| Componente | Resultado de la comprobación |
|---|---|
| Instancia principal en el puerto 4200 | El inicio de sesión respondió, la API devolvió HTTP 200 en `/health` y PostgreSQL respondió a una consulta de solo lectura. |
| Entorno de auditoría en el puerto 4203 | La interfaz y la API respondieron. Se restableció el acceso directo de laboratorio en el puerto 8003 y `/ready` devolvió HTTP 200 por ambas rutas. |
| Acceso por roles | Las cuentas sintéticas de administración, docencia y estudiante iniciaron sesión y recuperaron su perfil desde el entorno de auditoría. |
| Correo oficial | Gmail volvió a negociar TLS 1.3 y rechazó la autenticación con SMTP 534 (5.7.9). La entrega de correo real sigue pendiente. Se conservó la credencial existente. |

La comprobación ratifica las calificaciones de la segunda auditoría.
