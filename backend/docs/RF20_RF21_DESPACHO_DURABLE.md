# RF-20 y RF-21 — despacho de correo recuperable

## Alcance del incremento

Las altas y retiros conservan los servicios y avisos internos existentes. Con correo habilitado, la transacción escritora añade un despacho cifrado asociado por FK y PK a la misma notificación. No se incorpora otra bandeja de notificaciones ni una ruta de reenvío de credenciales.

La tabla técnica `despacho_correo` conserva el payload cifrado, estado, contador operativo de intentos, fechas y un código de error sin contenido del proveedor. La migración `20261110_durable_mail` depende de `20261108_voluntary_partial`. Añade una tabla física, pasando de 39 a 40. El modelo académico original se conserva. El downgrade de una tabla con historial se rechaza para impedir pérdida accidental. El ciclo reversible sin datos se acredita en PostgreSQL 17 desechable.

El código aleatorio existente continúa almacenado como hash en `convocatoria`. El material necesario para entregar el correo se cifra mediante Fernet con clave obligatoria del servidor. El mensaje interno y la auditoría de despacho excluyen el código, las credenciales SMTP y el ciphertext. La respuesta original del POST de alta conserva la entrega única de `codigo_acceso` al docente autorizado y `Cache-Control: no-store`, conforme al contrato anterior. Esta es la exposición autorizada ya existente.

## Configuración obligatoria

`SCHEDULING_MAIL_ENABLED` vale `false` por defecto. En ese estado las operaciones mantienen sus avisos internos y no generan despachos de correo. Los códigos antiguos conservados únicamente como hash no se reconstruyen ni se rellenan retroactivamente.

Al habilitar correo se exigen `SCHEDULING_MAIL_HOST`, `SCHEDULING_MAIL_PORT`, `SCHEDULING_MAIL_TLS`, `SCHEDULING_MAIL_FROM`, `SCHEDULING_MAIL_ENCRYPTION_KEY` y `SCHEDULING_MAIL_PUBLIC_URL`. El puerto vacío se trata como ausente, sin elegir un puerto implícito. La clave debe ser una clave Fernet válida suministrada fuera del repositorio. `SCHEDULING_MAIL_USERNAME` y `SCHEDULING_MAIL_PASSWORD` son opcionales conjuntamente. El proveedor puede autorizar por infraestructura o exigir autenticación.

Los modos de transporte `STARTTLS` y `SSL` utilizan el almacén de confianza del sistema y validación de certificados. La URL pública debe ser HTTPS. `LAB_LOOPBACK` es una excepción explícita para captura local, restringida a una IP literal loopback. Solo en ese modo se admite una URL HTTP loopback. No se proporciona contraseña, clave criptográfica ni servidor SMTP predeterminado.

La ausencia o invalidez de configuración requerida devuelve cierre seguro antes del commit del alta o retiro cuando el correo está habilitado. No se declara enviado un correo por insertar una notificación interna.

## Despacho y recuperación

Desde el directorio `backend`, con el intérprete y las variables del laboratorio o despliegue configuradas, ejecutar un lote operativo mediante el siguiente comando.

```powershell
python -m app.modules.scheduling.infrastructure.mail_delivery --limit 20
```

El comando se ejecuta después de confirmar la transacción académica. Cada fila elegible se procesa una vez por invocación, usando una transacción propia y `FOR UPDATE SKIP LOCKED`. Un fallo SMTP conserva `REINTENTAR`, y otra invocación recupera el despacho sin recrear la convocatoria, la transición ni la notificación. Una aceptación SMTP persistida conserva `ACEPTADO_PROVEEDOR` y se omite en posteriores lotes. La auditoría usa `evento_auditoria` con identidad causal de notificación y resultado operativo.

Antes del envío se revalidan la convocatoria, el destinatario SQL, la cuenta activa, su correo y la correspondencia del código con el hash vigente. Una invitación retirada o credencial cambiada se cancela. El aviso de retiro puede enviarse sin incluir código ni reactivar el permiso. Las actualizaciones concurrentes de convocatoria y cuenta se coordinan mediante bloqueos de fila.

La aceptación por SMTP no acredita recepción en el buzón. Una caída después de que SMTP acepte y antes de confirmar el registro puede ocasionar repetición al recuperar. Se utiliza un `Message-ID` estable, pero el destinatario o proveedor podría recibir duplicados en esa ventana. No existe garantía de entrega exactamente una vez. La recuperación efectiva depende del proveedor, conectividad, operación del despachador y conservación de la clave de cifrado. La rotación o pérdida de clave requiere un procedimiento controlado adicional. Este incremento no inventa caducidades, cuotas, regeneración de códigos ni una política de reenvío al estudiante.

## Evidencia de aceptación

`tests/integration/test_durable_mail.py` ejecuta HTTP sobre `app.main.app`, login real del personal, JWT, PostgreSQL 17 y un capturador SMTP TCP real local mediante `aiosmtpd`. Las asignaciones académicas y credenciales son preparación sintética de laboratorio. Las dependencias SQL del servidor apuntan exclusivamente al laboratorio desechable.

Se comprueban destinatario real persistido, caso, mensaje personalizado, URL y código individual, recuperación desde otra sesión SQL, fallo SMTP y reintento, concurrencia de despachadores, ausencia de efectos sin autorización, cifrado autenticado alterado, retiro, rollback SQL, configuración incompleta, FK, PK y CHECK, upgrade/downgrade y rechazo de downgrade con historial. Los logs, JUnit y comandos originales se guardan fuera del repositorio en `C:\SPS\acelerado_nuclear_20261110\correo`.

Este incremento acredita transporte configurable y aceptación SMTP en captura local. La entrega externa real requiere configuración segura del proveedor y comprobación operativa posterior. No se enviaron correos a cuentas reales y no se publicaron calificaciones.

## Resultados verificados del 11 de noviembre

La aceptación final `focal_reanudado` aprobó 18 pruebas, sin omisiones, fallos ni errores. La regresión de esquema `esquema_final` aprobó 292, omitió 29 por ausencia de una URL externa opcional y terminó sin fallos ni errores. Ambas conservaron la advertencia conocida de Starlette/httpx. Los 137 casos de `relacionada` corresponden a la ejecución anterior del mismo frente. Estas suites se solapan y sus cantidades se informan por separado.

El intento `focal_final` coincidió con la indisponibilidad de Docker Engine y conserva un fallo y 16 errores de preparación de PostgreSQL, junto con una prueba aprobada de configuración. La ejecución posterior se realizó después de comprobar la reanudación del motor. Los diagnósticos anteriores del esquema se preservan. Se corrigieron las expectativas del esquema físico actual y la retirada exclusiva de DDL auxiliar vacío en SQLite en memoria. Las expectativas de revisiones históricas y el DBML académico permanecen vigentes.

No se ejecutó una suite general en este worktree. La validación general corresponde al candidato integrado. La aceptación SMTP local sigue sujeta a la configuración y comprobación del proveedor real antes del despliegue.
