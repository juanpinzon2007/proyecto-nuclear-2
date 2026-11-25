# Auditoría integral de SPS

24 de noviembre de 2026. Revisión local de `maicol` sobre `e7f1b75`. El árbol de trabajo estaba limpio al empezar. Las pruebas de auditoría utilizaron una copia con PostgreSQL 17 y datos sintéticos. Posteriormente se actualizó la instancia local principal y se activó Gmail. La migración conservó las 11 participaciones existentes. Los cambios quedaron locales, sin commits, push ni despliegue público.

## 1. Estado inicial y arquitectura

SPS es un monolito modular. Identity gestiona autenticación, roles, permisos, grupos y seguimiento. Cases gestiona versiones, escenarios, grafos y rúbricas. Scheduling gestiona sesiones, espacios, convocatorias y avisos. Participation registra intentos, decisiones, resultados y entrega. La interfaz Angular 21.2 usa Angular Material, CDK, SCSS y rutas cargadas bajo demanda. Nginx sirve la aplicación y proporciona un proxy del mismo origen para la API.

El backend usa FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy, Psycopg, PostgreSQL, Alembic, JWT con PyJWT y Argon2. El worker utiliza el mismo código y base de datos para el cierre de sesiones e intentos y el despacho de correo. Docker Compose ejecuta los cuatro servicios.

La versión inicial permitía los flujos académicos centrales. Ya tenía control de acceso por rol, versiones publicadas, trazabilidad y una cola de correo cifrada. Tenía desbordamientos en móvil, mensajes de texto plano, manejo irregular de fallos en notificaciones y varias verificaciones históricas de base de datos que habían quedado desfasadas.

## 2. Hallazgos y correcciones

| Gravedad | Hallazgo | Corrección y resultado |
|---|---|---|
| Alta | El flujo interactivo podía adjuntar o generar un consentimiento sin comprobación de aprobación institucional. | Fuera del laboratorio explícito, resuelve el documento vigente y verifica el atestado mediante el proveedor existente. Sin aprobación, devuelve 503. La prueba de PostgreSQL comprueba que ese rechazo deja cero documentos nuevos. |
| Alta | La lectura de permisos ignoraba cualquier error SQL y podía recuperar permisos del rol omitiendo revocaciones individuales. El punto de guardado también ejecutaba `flush` en consultas. | Lectura sin `autoflush` y fallo controlado en PostgreSQL. La compatibilidad histórica se limita a fixtures de SQLite que carecen de la tabla. |
| Alta | El inicio estudiantil podía tratar un error de la base de datos como verificación completada. | Se exige leer el estado para emitir un token. En cuentas históricas sin fila, se conserva el comportamiento de la migración existente. |
| Alta para mantenimiento | La versión instalada de `cryptography` (46.0.7) quedó en el rango de cuatro identificadores únicos de avisos de seguridad. | Se elevó el mínimo de la dependencia existente a 50.0.2 y se verificaron de nuevo el cifrado de la cola y las firmas de consentimiento. |
| Media | Las solicitudes repetidas de OTP podían sustituir de inmediato el código anterior y volver a enviar correo. | Pausa de un minuto por cuenta, conservando los 15 minutos de vigencia, el límite de cinco intentos por código y la invalidación tras verificar. La recuperación conserva una respuesta pública uniforme y serializa escrituras por usuario. |
| Media | Una configuración SMTP inválida podía fallar después de confirmar una operación que disparaba avisos de negocio. Los registros podían incluir el correo y el detalle del proveedor. | Manejo dentro de la tarea de notificación, registros por tipo de error y mensaje de resultado sin detalles privados. |
| Media | La plantilla de retiro usaba un identificador distinto al de la notificación registrada. | El retiro tiene asunto y texto propios en ambos formatos. Se verificó su envío al capturador sin incluir el código anterior. |
| Media | La cola podía volver a tomar errores SMTP antes de ofrecer turno a avisos nuevos. Un error al cerrar la conexión podía provocar un reintento posterior a la aceptación. | Pendientes nuevos primero, pausa de un minuto en los reintentos del worker y resultado basado en la respuesta SMTP a DATA. El identificador del mensaje durable se conserva al reintentar. |
| Media | La vista de trazabilidad de intentos combinaba tres relaciones uno a muchos y deduplicaba el producto al final. | Tres conteos independientes por intento sobre los índices existentes. Alembic conserva las columnas, tipos y datos. |
| Media | El editor y las convocatorias desbordaban el ancho del teléfono. Las convocatorias se mostraban en un único listado. | Campos adaptables, controles alineados, tabla acotada, búsqueda por estudiante, correo o estado y páginas de 10, 20 o 50 filas. |
| Media | La pantalla ofrecía emitir convocatorias a sesiones iniciadas, acción que la API rechaza. | El formulario se muestra para sesiones sin iniciar. Las demás presentan una explicación y permiten consultar su lista. |
| Media | SQLite no podía crear el esquema de pruebas por una restricción con `btrim`. Había inventarios obsoletos de tablas, revisiones y datos de demostración con fecha sin zona incorrecta. | El modelo usa `trim` equivalente, se actualizan las expectativas con el esquema vigente y la carga sintética usa la zona temporal configurada. |
| Baja | Había iconos de edición sin nombre accesible, notas partidas, fechas de estilo estadounidense y mensajes ambiguos de reenvío. | Etiquetas de acción, foco visible para controles nativos, nota en una línea, formato `es-CO` y mensajes que explican la pausa. |
| Baja | El punto de entrada Angular podía permanecer en caché al probar una versión nueva. | Nginx devuelve `Cache-Control: no-cache` en el HTML de entrada. Los recursos con hash de producción conservan sus nombres versionados. |

## 3. Base de datos, disparadores y vistas

La copia migrada a `20261124_decision_counts` tiene **47 tablas**, **9 vistas**, **115 disparadores no internos**, **47 claves primarias**, **93 foráneas**, **39 restricciones CHECK** y **116 índices**. PostgreSQL reportó **0 restricciones sin validar**. Las tablas incluyen el registro de Alembic y la auditoría gestionada por migración. El ORM registra 45 tablas. Los 115 disparadores cubren 67 eventos INSERT, 68 DELETE, 76 UPDATE y 28 TRUNCATE. Un mismo disparador puede cubrir varios eventos.

Se verificaron las vistas de catálogo de casos, resumen de sesiones, seguimiento, primer ingreso, trazabilidad global, trazabilidad del estudiante, correo y notificaciones, decisiones y permisos. Los escenarios de prueba comprobaron conteos y relación de entidades, selección del resultado oficial más reciente, permisos efectivos, auditoría sin hashes ni material cifrado y reglas de integridad e inmutabilidad con escrituras reales. También se verificaron las funciones `sps_*` con `SECURITY INVOKER` y `search_path` fijo.

Se probó la migración limpia y la sustitución reversible de la vista con datos sintéticos existentes. Se mantuvieron las claves, relaciones, restricciones y registros históricos. La información versionada de casos, consentimiento e intentos representa versiones de negocio. La auditoría conserva copias de eventos para trazabilidad. Se mantuvo esa separación.

En la consulta de muestra, 10 mediciones con `EXPLAIN (ANALYZE, BUFFERS)` tuvieron una mediana de **0,582 ms** antes y **0,508 ms** después. Ambos planes devolvieron la misma fila. La muestra mide un caso en caliente y permite comprobar la eliminación de la agregación por producto de las tres relaciones. La capacidad con volumen institucional queda pendiente de una carga representativa.

## 4. Correo electrónico y plantillas

El remitente configurado es **adminsps8@gmail.com**. Gmail SMTP utiliza `smtp.gmail.com`, puerto `587` y `STARTTLS`. Se exige que la cuenta autenticada coincida con el remitente y tenga una contraseña de aplicación de 16 caracteres. El TLS valida el certificado del servidor. El servicio centralizado genera correo `multipart/alternative`, con HTML y texto plano. [Configuración SMTP oficial de Google](https://developers.google.com/workspace/gmail/imap/imap-smtp)

| Flujo existente | Contenido adaptado |
|---|---|
| Registro de cuenta | Saludo, rol, acceso a SPS e indicaciones del tipo de cuenta. |
| Primer ingreso estudiantil | Código de verificación destacado, 15 minutos e indicación de seguridad. |
| Recuperación de contraseña | Código destacado, 15 minutos e instrucciones para restablecer. |
| Matrícula en grupo | Nombre del grupo y datos disponibles de la matrícula. |
| Creación de caso | Caso y contexto de la actividad de autoría. |
| Asignación de rúbrica | Caso y datos disponibles de la rúbrica. |
| Publicación de caso | Nombre y versión publicada. |
| Convocatoria | Saludo por nombre, caso, horario y código individual con instrucciones de ingreso. |
| Retiro de convocatoria | Contexto de la sesión y aviso de retiro. |
| Cambio de sesión | Programación actualizada y mensaje docente. |
| Calificación | Aviso de resultados oficiales y acceso al portal. |
| Retroalimentación | Aviso de la respuesta del docente y acceso al portal. |

El diseño usa fondo claro, cabecera oscura y acento cian, con jerarquía de títulos, bloques de código y botón de acceso. Usa tablas de presentación, estilos en línea y un ancho máximo de 600 px. El logotipo se obtiene de la URL pública HTTPS de SPS. El nombre institucional permanece visible cuando el cliente bloquea imágenes. Los datos dinámicos se escapan antes de insertarlos en HTML. El transporte SMTP de laboratorio verificó destinatario, texto, HTML, retiro, recuperación tras un fallo temporal y que la cola no reenvía un registro ya confirmado. El usuario confirmó la recepción del primer mensaje de prueba en Gmail. Después de activar el correo automático en la instancia de `4200`, se verificó la autenticación SMTP del worker mediante TLS y Gmail aceptó un segundo mensaje al remitente. Quedan pendientes las pruebas de presentación en diferentes clientes de correo.

### Activar y probar Gmail

1. Entra en la cuenta **adminsps8@gmail.com** y habilita la verificación en dos pasos. [Configuración de verificación en dos pasos](https://support.google.com/accounts/answer/185839?hl=es)
2. Abre la herramienta de Google, crea una contraseña con el nombre «SPS SMTP» y copia los 16 caracteres. La opción depende de la política y protección de la cuenta. [Contraseñas de aplicación](https://myaccount.google.com/apppasswords) · [Ayuda de Google](https://support.google.com/accounts/answer/185833?hl=es)
3. Guarda la contraseña de aplicación en `SCHEDULING_MAIL_PASSWORD` dentro del archivo `.env` de la raíz del proyecto. Conserva la clave Fernet ya configurada.
4. Conserva `SCHEDULING_MAIL_ENABLED=false` para la primera prueba. Desde la raíz del repositorio ejecuta este comando. Usa una instancia de la API sin arrancar dependencias y envía un solo mensaje a la misma cuenta remitente.

   ```powershell
   docker compose -p sps-maicol-local run --rm --no-deps --build -e SCHEDULING_MAIL_ENABLED=true api python -m app.modules.scheduling.infrastructure.mail_delivery --test-to-sender
   ```

5. Busca «Prueba de correo de SPS» en el buzón y en spam. Comprueba el remitente, el cuerpo y el botón. Una aceptación SMTP confirma recepción por el servidor, mientras que ver el mensaje en el buzón confirma la prueba de entrega.
6. Para comunicaciones académicas reales, configura `SCHEDULING_MAIL_PUBLIC_URL` con la dirección HTTPS institucional, activa `SCHEDULING_MAIL_ENABLED=true` y recrea API y worker en el entorno autorizado. El enlace local `127.0.0.1` sirve para una prueba en este equipo. La recreación vuelve a leer el archivo de entorno sin reiniciar PostgreSQL.

   ```powershell
   docker compose -p sps-maicol-local up -d --build --force-recreate --no-deps api worker
   ```

`.env` está ignorado, no figura en el índice de Git ni apareció en el historial de las referencias locales consultadas. `.env.example` contiene el host, la cuenta pública, los nombres de variables y los campos secretos vacíos. Las operaciones que requieren correo durable devuelven 503 si se activa SMTP con configuración incompleta. El correo automático está activo en la instancia local principal. Los mensajes de prueba reales se enviaron únicamente a la cuenta remitente.

## 5. Frontend, usabilidad y accesibilidad

- **Docencia.** Los controles de autoría comparten alineación y tienen nombre accesible. Los campos largos en el editor respetan el ancho de la columna. Convocatorias permite buscar y paginar con el componente de listas que usa el resto de la interfaz. Se verifica el estado de aprobación en Seguimiento con el umbral existente de 60 sobre 100.
- **Administración.** Se recorrieron las tres pestañas del rol, el registro de cuentas, la lista, los permisos y los espacios. Se verificó el ancho adaptable con los controles existentes.
- **Estudiantes.** Se recorrieron portal, guía, simulador y resultado. Se usó el Joker y se jugaron dos cartas por teclado. El texto de confirmación quedó en mayúscula inicial. La localización de fechas y números coincide con el entorno colombiano.
- **Acceso.** Se verificaron formulario, acceso por rol, cierre de sesión y pantalla de recuperación. Las confirmaciones de correo explican cuándo volver a solicitar un código.
- **Accesibilidad.** Se revisaron etiquetas, orden y foco de controles en los recorridos, nombres de acciones de icono, mensajes de error y región desplazable de convocatorias. El contraste, el foco y la adaptación se trataron con WCAG 2.2 AA como referencia. Queda pendiente una auditoría con lectores de pantalla y revisión completa de contraste sobre todas las escenas. [Foco visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html) · [Reflujo de contenido](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)

Sobre los colores planos definidos por el tema, el texto principal sobre el panel da **15,62:1**, el texto secundario **9,96:1** y el anillo de foco **13,73:1**. En el correo, el texto sobre blanco da **14,51:1** y el texto del botón **10,94:1**. Estas mediciones corresponden a los colores indicados, sin transparencias ni imágenes de fondo.

En 19 pantallas o estados se midió el ancho del documento en **360, 390, 768, 1024, 1280, 1440 y 1920 px**. La versión corregida registró **0 px de desbordamiento horizontal del documento** en las 133 combinaciones. En móvil, el carril de cartas y las tablas con varias columnas conservan su desplazamiento interno. Antes, Convocatorias superaba el ancho útil de 360 y 390 px por 94 y 64 px respectivamente. El editor superaba el ancho útil de 390 px por 42 px.

En una sesión de prueba con 15 convocatorias, el paginador mostró 10 y 5 filas. El buscador devolvió la coincidencia esperada y mostró un mensaje cuando el filtro quedó vacío. Con Tab, la tabla recibió el foco con un contorno visible. Una sesión en curso mostró su lista y explicó la restricción de emisión.

## 6. Backend, seguridad y escalabilidad

Se revisaron los routers principales, validaciones, dependencias de autorización, contraseñas, sesiones JWT, decisiones y evaluación. Las pruebas ejercitan respuestas 401, 403, 409, 422 y 503, permisos efectivos, cuentas inactivas, titularidad de convocatorias, pérdida de conexión o dependencias e historial. Las consultas del código revisado usan ORM o parámetros. El frontend usa el proxy de mismo origen y autorización Bearer. Las operaciones académicas verifican permisos en backend. El análisis de dependencias de producción de Angular con `npm audit --omit=dev` reportó cero avisos para el lockfile consultado.

`pip-audit` detectó cuatro identificadores únicos para `cryptography` 46.0.7. El límite anterior impedía instalar las versiones corregidas. La imagen final usa 50.0.2, pasó `pip check` y el nuevo escaneo reportó cero avisos conocidos. Una prueba independiente descifró con 50.0.2 un mensaje Fernet generado con 46.0.7 y la misma clave sintética. [Historial de versiones de pyca/cryptography](https://cryptography.io/en/latest/changelog/) · [Aviso de seguridad del proveedor](https://github.com/pyca/cryptography/security/advisories/GHSA-537c-gmf6-5ccf)

La paginación reduce filas en pantalla. Las API de convocatorias y algunas otras listas aún entregan su colección completa. La búsqueda de cuentas por correo conserva la normalización histórica y recorre el catálogo. La paginación del servidor y la reconciliación de correos históricos para indexar su forma canónica quedan pendientes para un volumen institucional. La entrega SMTP y el registro de aceptación son pasos distintos. Si el proceso cae entre ambos, existe posibilidad residual de reenvío, aun con el identificador estable. Quedan por medir límites reales de Gmail y concurrencia representativa. El backend usa rangos de versiones sin un bloqueo completo de dependencias transitivas.

## 7. Pruebas y evidencias

| Estado | Verificación | Evidencia |
|---|---|---|
| Inicial | Suite amplia sobre el código de partida | 679 aprobadas, 21 fallidas, 280 errores de preparación y 1.404 omitidas. SQLite fallaba al preparar el modelo con `btrim`. |
| Inicial | Selección PostgreSQL y SMTP sobre el código de partida | 21 aprobadas y una expectativa desfasada en la prueba de migración del correo durable. |
| Corregida y verificada | Regresión amplia del backend | 976 aprobadas, sin fallos. 1.409 omitidas por requisitos del entorno o por configuración opcional. Las suites PostgreSQL se contabilizan por separado y se solapan parcialmente. |
| Corregida y verificada | PostgreSQL, vistas, disparadores, correo durable, identidad y flujo académico | 36 aprobadas. Incluye alta de roles, creación y programación del caso, matrícula, convocatoria, consentimiento, decisiones, evaluación, publicación, informes, entrega SMTP y rechazos autorizativos. |
| Corregida y verificada | PostgreSQL ampliado | 62 aprobadas en consentimiento firmado, permisos administrativos, espacios académicos, autoría de grafos e informes oficiales. La primera ejecución completó las aserciones y falló en el cierre de una conexión de prueba. La repetición con la conexión de mantenimiento independiente terminó limpia. |
| Corregida y verificada | Compilación y ejecución en contenedores | Angular compiló en producción. El paquete inicial quedó en 762 kB y la estimación de transferencia comprimida fue 186 kB. Nginx, API, base de datos y worker arrancaron en la copia aislada. `/login` respondió 200 con `no-cache`. `/health` respondió `ok`. |
| Corregida y verificada | Configuración temporal | Compose rechazó la zona vacía, aceptó `America/Bogota` y la imagen convirtió las 07:00 locales del caso de prueba a las 12:00 UTC. |
| Exitosa | Navegador en siete anchos | Capturas antes y después durante la auditoría. Flujo estudiantil completado con 2 de 2 respuestas y resultado de prueba de 100 sobre 100. Sin errores de consola capturados en el recorrido final. |
| Corregida y verificada | Dependencias y compatibilidad de claves | `npm audit --omit=dev` y el segundo `pip-audit` reportaron cero avisos conocidos. La imagen corrigió el rango fijado en `cryptography` y pudo leer un mensaje Fernet antiguo. |
| Exitosa | Entrega por Gmail y activación local | El usuario confirmó la recepción del primer mensaje. El worker local se autenticó con Gmail mediante TLS y el proveedor aceptó un segundo mensaje de prueba. Se verificó el acceso de administrador, docente y estudiante. |
| Pendiente | Presentación en clientes de correo | Falta comprobar las plantillas en distintas aplicaciones y dispositivos. |
| Pendiente | Accesibilidad integral, carga y operación real | Faltan lectores de pantalla, prueba de carga con datos representativos y validación en el despliegue institucional. |
| Limitación del entorno | Suites opcionales de Docker y navegador | Se verificó temporalidad en el host y el flujo en Chromium. Las pruebas que exigen Docker desde el proceso Python y los clientes de correo nativos conservan sus requisitos propios. Angular no tiene configurado el destino `test` para ejecutar pruebas unitarias con `npm test`. |

Las dos selecciones de PostgreSQL se volvieron a ejecutar juntas con `cryptography` 50.0.2 y pasaron las **98 pruebas**. El cliente de pruebas de Starlette emite una advertencia de deprecación por HTTPX.

Los registros locales de ejecución se conservan en `.venv/sps-auditoria-base`. La suite utiliza bases temporales. El recorrido web integra Angular, Nginx, FastAPI y PostgreSQL. La prueba académica automatizada usa la aplicación HTTP real con PostgreSQL. La vista previa de correo generada para esta auditoría lleva datos ficticios y el logotipo incluido en el HTML para abrirlo sin conexión.

## 8. Archivos modificados

| Archivo | Motivo |
|---|---|
| `.env` y `.env.example` | Preparar Gmail, el remitente, TLS y las variables privadas. El archivo local conserva sus variables ajenas al correo. |
| `backend/alembic/versions/20261124_traceability_decision_counts.py` | Sustituir y restaurar la vista de conteos sin alterar tablas. |
| `backend/app/modules/scheduling/infrastructure/mail_templates.py` | Renderizar el HTML centralizado. |
| `backend/app/modules/scheduling/infrastructure/mail_delivery.py` | Validar Gmail, enviar las dos partes MIME, ordenar la cola y probar el remitente. |
| `backend/app/modules/scheduling/infrastructure/worker_runner.py` | Aplicar la pausa de reintento y registrar fallos seguros. |
| `backend/app/modules/identity/api/router.py` | Exigir estado de verificación y mantener una respuesta pública de recuperación uniforme. |
| `backend/app/modules/identity/infrastructure/onboarding.py` | Limitar reenvíos, aplicar plantilla OTP y sanear registros. |
| `backend/app/modules/identity/infrastructure/password_recovery.py` | Serializar por cuenta, aplicar pausa y plantilla de recuperación. |
| `backend/app/modules/identity/infrastructure/business_notifications.py` | Aislar fallos de correo posteriores al commit. |
| `backend/app/modules/identity/infrastructure/repositories.py` | Aplicar revocaciones sin escrituras implícitas y fallar ante errores de consulta. |
| `backend/app/modules/participation/api/interactive_router.py` | Exigir aprobación institucional fuera de laboratorio. |
| `backend/app/modules/participation/infrastructure/result_models.py` | Usar una restricción de textos compatible con el entorno de pruebas. |
| `backend/pyproject.toml` | Admitir la versión corregida de la dependencia criptográfica existente. |
| `frontend/nginx.conf` y `frontend/src/app/app.config.ts` | Revalidar el HTML de entrada y localizar fechas y números. |
| `frontend/src/styles.scss` | Foco visible en controles nativos y campos Material contraíbles. |
| `frontend/src/app/pages/casos/caso-editor.component.ts` | Alineación, nombres accesibles y etiquetas más breves. |
| `frontend/src/app/pages/programacion/convocatorias.component.ts` | Tabla adaptable, búsqueda, paginación, estados y copy de emisión. |
| `frontend/src/app/pages/seguimiento/seguimiento.component.ts` | Mantener cada nota en una línea. |
| `frontend/src/app/pages/estudiante/simulador.component.ts` | Corregir mayúsculas de la confirmación de entrega. |
| `frontend/src/app/pages/login/login.component.html` y `login.component.ts` | Mostrar el resultado real de la petición de recuperación o reenvío. |
| `scripts/seed_demo_data.py` | Generar fechas sintéticas con la convención del entorno. |
| `backend/tests/identity/academic_identity_support.py` y `test_academic_identity_repository.py` | Limpiar únicamente el DDL vacío del fixture y verificar la revisión actual. |
| `backend/tests/identity/test_persistence.py` | Conservar la comparación DBML de columnas y relaciones originales con el inventario integrado actual. |
| `backend/tests/integration/test_assignment_bridge.py`, `test_cases_guard_migration.py`, `test_er28_academic_base.py`, `test_evaluation_result_storage.py`, `test_participation_persistence.py`, `test_schema_integration.py` y `test_steps_uuid.py` | Actualizar inventarios y referencias de migración al estado del esquema comprobado. |
| `backend/tests/integration/test_assignment_mail_composition.py` y `test_durable_mail.py` | Comprobar las dos partes del correo, el reintento y el cambio histórico de la migración de correo. |
| `backend/tests/integration/test_db_views_and_triggers_traceability.py` | Verificar que el resultado de la vista se conserva al revertir y reaplicar con datos. |
| `backend/tests/integration/test_e2e_27rf_flow.py` | Ejercitar el límite entre consentimiento institucional y laboratorio. |
| `backend/tests/integration/test_student_identity_security.py` | Modelar el contexto sin autoflush en la prueba de fallo de SQL. |
| `backend/tests/integration/test_docker_timestamp_zone.py` | Identificar correctamente una ejecución sin CLI de Docker. |
| `backend/tests/unit/identity/test_business_notifications.py`, `test_first_login_otp.py` y `test_password_recovery.py` | Probar HTML escapado, código destacado y límites de reenvío. |
| `README.md` y este informe | Documentar la composición actual, ejecución y evidencia. |

## 9. Ejecutar SPS

La instancia local actualizada está disponible en [SPS local](http://127.0.0.1:4200/login) en modo de demostración y con el correo automático activo. Sus enlaces apuntan al equipo local. La copia aislada de auditoría se ejecutó en el puerto 4202 con la API en el 8002 y PostgreSQL en la red interna de Docker.

Para una instalación nueva en desarrollo, copia `.env.example` a `.env` si todavía no existe. Configura PostgreSQL, una clave JWT aleatoria, dominios institucionales y la zona temporal de esa base. Para ejecutar los datos sintéticos, establece `ACADEMIC_RUNTIME_SCOPE=LABORATORIO` y mantén el correo desactivado. Después, desde la raíz del repositorio:

```powershell
docker compose config --quiet
docker compose up -d --wait db
docker compose build api frontend worker
docker compose run --rm --no-deps api alembic upgrade head
docker compose up -d --wait frontend worker
docker compose ps
```

Abre [SPS local](http://127.0.0.1:4200/login). El flujo académico en producción requiere el documento institucional y su atestado configurados según el proceso del proyecto. Para usar una base existente se requiere aplicar la migración en el entorno autorizado tras validar el respaldo. Compose conserva el volumen de datos al detener el proyecto.

## 10. Evaluación inicial y final

Escala de 1 a 5. El promedio asigna el mismo peso a cada criterio. Un 5 requiere evidencia completa para el criterio. El cierre incorpora la recepción confirmada en Gmail y la verificación de los tres roles en la instancia local actualizada.

| Criterio | Inicial | Final | Justificación y límite |
|---|---:|---:|---|
| Arquitectura de software | 4,1 | 4,1 | Monolito modular apropiado. Persisten accesos directos a algunos modelos entre módulos. |
| Base de datos | 4,0 | 4,3 | Claves y restricciones verificadas en PostgreSQL. Falta revisar el volumen institucional. |
| Disparadores | 4,1 | 4,3 | Evidencia de integridad e historial para eventos reales. Falta carga con escrituras concurrentes sostenidas. |
| Vistas | 3,8 | 4,3 | Nueve vistas comprobadas y conteos de intento independientes. La medición de rendimiento usa una muestra pequeña. |
| Backend | 3,6 | 4,1 | Permisos, OTP y fallos SMTP más previsibles. Quedan distintos mecanismos de entrega de notificaciones. |
| Frontend | 3,8 | 4,2 | Compilación y recorrido real por rol. Falta automatizar la regresión visual. |
| Diseño visual | 4,0 | 4,2 | Se conserva la identidad gráfica y se mejora la lectura en formularios. Falta validación con usuarios. |
| Alineación de componentes | 3,6 | 4,3 | Botones y tablas verificados en las pantallas que desbordaban. |
| Consistencia visual | 3,8 | 4,2 | Selectores y botones coherentes con Material y formatos en español. Algunos estilos locales siguen siendo específicos de cada flujo. |
| Usabilidad | 3,7 | 4,2 | Búsqueda, paginación y estados más claros. La selección inicial de estudiantes aún carga la lista completa. |
| Experiencia del usuario | 3,7 | 4,2 | Guía, decisiones y entrega verificadas de extremo a extremo. Falta observación con usuarios nuevos. |
| Accesibilidad | 3,0 | 3,7 | Etiquetas, foco, teclado y mensajes revisados. Falta verificación completa con lectores de pantalla y contraste. |
| Diseño responsive | 3,4 | 4,2 | Siete anchos en Chromium. Falta validación en motores y dispositivos físicos adicionales. |
| Seguridad | 3,2 | 3,9 | Bloqueo de permisos y consentimiento ante fallos, OTP acotado y correo con TLS. Falta revisar operación real y límites globales de solicitudes. |
| Escalabilidad | 3,1 | 3,6 | Vista de conteos, búsqueda, paginación visual y mejor orden de la cola. Falta paginación de servidor y carga representativa. |
| Mantenibilidad | 3,6 | 4,1 | Reutilización de configuración, plantilla, controles y pruebas del proyecto. Persiste documentación histórica por módulo. |
| Servicio de correo electrónico | 2,8 | 4,3 | Recepción real confirmada en Gmail y autenticación TLS del worker activo. Falta medir entregabilidad a escala y a distintos dominios. |
| Diseño de correos electrónicos | 2,0 | 4,1 | Doce tipos con HTML y texto. Faltan resultados de renderizado nativo en varios clientes. |
| Rendimiento | 3,4 | 3,8 | Mejora local medible en una consulta. Faltan tiempos con carga y métricas percentiles. |
| Calidad del código | 3,5 | 4,1 | Menos escrituras implícitas y rutas de error más claras. Quedan archivos de gran tamaño en frontend y API. |
| Pruebas de software | 3,0 | 4,0 | Se recuperaron pruebas y se ejecutaron escenarios reales. Hay suites opcionales y entornos pendientes. |
| Funcionamiento general | 3,6 | 4,2 | Flujo académico, tres roles y correo verificados en local. Falta validar la operación institucional. |
| **Calificación definitiva** | **3,49** | **4,11** | **Promedio de los 22 criterios.** |

El objetivo de 4,8 requiere evidencia adicional de entregabilidad a escala, compatibilidad de correo, accesibilidad, rendimiento bajo carga y operación institucional.
