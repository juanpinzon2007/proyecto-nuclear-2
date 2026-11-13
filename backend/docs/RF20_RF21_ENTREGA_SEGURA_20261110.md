# Fase 10 — Checkpoint RF24 y contrato de entrega RF20/RF21

10 de noviembre de 2026, America/Bogota. Los registros UTC del laboratorio corresponden al 11/11. Auditoría dirigida, pruebas nuevas y propuesta condicionada; no nuevo transporte de correo.

## Preservación y checkpoint

Inicio verificado: rama `codex/participation-inicio-main-20261109`, HEAD `a62868d6e57db7efbc0f7fa14c097898f78dc145`, índice vacío, ocho modificaciones previas de código y 3378 archivos sin seguimiento. Los ocho documentos de `evidencias/rf24_fase9_20261110/MANIFIESTO_RF24.json` coincidían en tamaño y SHA-256. Las pruebas originales de RF24 y las huellas de sus fuentes se contrastaron sin reejecutarlas para el commit.

Respaldo privado: `C:/SPS/respaldos/nuclear_rf24_fase10_20261111T010005Z`. Se copiaron las ocho rutas conservando estructura, se verificó cada SHA y se restauraron en otro directorio de prueba. Bundle de referencias verificado, ACL restringida al usuario y SYSTEM. No se sobrescribió el repositorio ni otro respaldo.

Commit local autorizado: **`578f86385c9118813f0c1a51104e00be5927be29`**, `docs(evaluation): acreditar controles y bloqueo de RF24`. Contiene exclusivamente:

1. `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`
2. `backend/docs/RF24_CIERRE_CONTROLADO_20261110.md`
3. `backend/docs/postman/cobertura_27rf/BRECHAS_RF.md`
4. `backend/docs/postman/cobertura_27rf/MATRIZ_TRAZABILIDAD_27RF.md`
5. `backend/docs/postman/cobertura_27rf/README.md`
6. `backend/docs/postman/cobertura_27rf/RESULTADOS_27RF.json`
7. `backend/docs/postman/cobertura_27rf/RF-24.md`
8. `backend/docs/postman/cobertura_27rf/matriz_trazabilidad_27rf.csv`

Se utilizaron rutas explícitas, revisión del diff y `git diff --cached --check`. El diff íntegro preparado está en `evidencias/rf20_rf21_fase10_20261110/checkpoint_rf24.diff`. No se incluyeron código previo, .env, evidencias masivas, credenciales o respaldos. La advertencia LF/CRLF fue de normalización Git, no un cambio funcional. No hay push, pull, merge, checkout, clean o reset.

## Fuentes y separación de responsabilidades

Fuente original: `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, p.5:

- **RF20:** «El sistema asocia un código de autorización al estudiante convocado e incluye el código en la notificación de programación».
- **RF21:** «El correo informa caso, mensaje personalizado, URL y código. El docente puede agregar o retirar estudiantes y cada afectado debe ser notificado».

RN01/RN08, p.7, vinculan correo+código a estudiante/convocatoria/sesión y exigen revalidar el estado; autenticación no sustituye admisión. RN09 exige aviso por alta/retiro. UC02, p.11, programa/asocia estudiantes/genera códigos/guarda/notifica; no confirma una convocatoria no persistida y exige registrar errores de envío para reintentarlos. RNF01 protege secretos; RNF02/03 exigen autorización backend y privacidad académica. Páginas y SHA del PDF: `FUENTES_ACADEMICAS.json` de esta fase.

RF20 cubre credencial, asociación, validación y su inclusión en la notificación. RF21 añade contenido y entrega del correo, altas/retiros y recuperación de errores. No son dos emisores distintos. No se atribuye al PDF una caducidad numérica, consumo por login, rotación automática, cuota de reenvíos o recepción garantizada por SMTP. Las decisiones posteriores de admisión/sala de espera y respuestas inmutables se conservan; no se reabren.

## Recorrido real y garantías verificadas

| Etapa | Código y comportamiento actual | Evidencia y límite |
|---|---|---|
| Solicitud autorizada | `convocation_management._autorizar`: JWT/cuenta activa/DOCENTE, vínculos explícitos, titularidad de sesión/caso, grupo y matrícula. Revalidación en transacción escritora | HTTP/PG rechaza estudiante, anónimo, docente ajeno, matrícula/caso/grupo/vínculo incompatibles; ninguna cabecera convierte INTEGER en UUID |
| Generación | `crear_convocatoria`: `secrets.token_urlsafe(32)` para una convocatoria individual, alta solo SIN_INICIAR; sesión/estudiante únicos | Generación y duplicados probados. No se regenera un código ante un alta repetida |
| Protección | `hash_codigo`: SHA-256 del secreto aleatorio; comparación `hmac.compare_digest`. Solo hash persistido | No se confunde token aleatorio con contraseña de baja entropía. Prueba PG comprueba hash distinto del código y ausencia del código en los mensajes |
| Respuesta del alta | `POST /scheduling/sesiones/{s}/convocatorias`: 201 con `convocatoria_id` y `codigo_acceso`, solo al docente autorizado, `Cache-Control:no-store` | La respuesta en claro es la entrega al invocador autorizado, **no evidencia de correo al estudiante**. Listados excluyen código/hash |
| Aviso interno | `convocar_con_aviso` crea `CONVOCATORIA/INTERNA/PENDIENTE`, destinatario persistido, caso/horario/mensaje personalizado | Comparte Session/commit con convocatoria. No guarda código en `mensaje`; no configura URL ni correo ficticios |
| Autenticación del titular | `ValidadorConvocatoriaScheduling`, login estudiantil real correo+código, JWT con contexto de convocatoria | Login del nuevo convocado y rechazo del retirado demostrados en main. JWT no contiene código ni permite acceder a otra convocatoria |
| Uso y vigencia | Estado ACTIVA y correspondencias persistentes; ingreso exige habilitación EN_CURSO, horario y admisión vigentes | **No hay consumo del código por el primer login ni un TTL propio de credencial definido.** Expiración del JWT, ventana de sesión y retiro son controles distintos. No se inventa un código de un solo uso |
| Retiro | DELETE lógico a RETIRADA, advisory lock compartido con provisión, historial intacto; aviso INTERNA | Repetir retiro no duplica aviso. JWT anterior sigue acreditando identidad, pero no concede ingreso/escritura sobre la convocatoria retirada |
| Reintentos/concurrencia SQL | Locks y UNIQUE(sesión, estudiante); fallo de aviso revierte alta/retiro; reintento posterior recupera | Alta repetida:422; retirada repetida:200. Una solicitud concurrente no crea otra convocatoria ni aviso indebido. No equivale a reintento de envío externo |
| Envío y recepción | **No existe transporte ejecutable** | No hay aceptación del proveedor ni entrega acreditada; no se suman esas etapas a las pruebas aprobadas |

Rutas existentes en main: POST/GET `/scheduling/sesiones/{s}/convocatorias`, DELETE `/scheduling/sesiones/{s}/convocatorias/{c}`, GET `/scheduling/notificaciones?destinatario_id={uuid}`, POST `/api/v1/identity/auth/estudiantes`, POST `/scheduling/validar-ingreso`. La consulta de notificaciones exige el UUID resuelto del propio JWT. No se añade otra ruta de consulta o reenvío del secreto.

El validador de autenticación distingue los estados conocidos de sesión e incluye FINALIZADO: autenticarse para consultar datos propios no equivale a ingresar/iniciar. No se declara que finalizar la sesión consuma o caduque por sí solo el código. El retiro sí invalida la convocatoria para ese login. Se conserva la consulta histórica privada de RF14, sin inventar una expiración de credencial que la cierre.

## Infraestructura y brecha reproducible

Se inspeccionaron Scheduling, Identity, configuración y dependencias Python. No se encontró SMTP/API de correo, cliente, adaptador emisor, capturador conectado al backend, envío asíncrono ni interfaz de transporte operativa. `crear_notificacion` acepta el canal CORREO, pero **solo inserta una fila**: no envía. El modelo tiene estado genérico PENDIENTE; no conserva intentos de entrega, id de proveedor ni evidencia de recepción. Las búsquedas y huellas se conservan en el inventario técnico de esta fase. No se leyó ni modificó configuración secreta para intentar un envío.

La credencial original existe en memoria hasta responder el POST; después solo queda su hash. Si el commit fue exitoso pero se perdió la respuesta, otra alta devuelve422 y no puede reconstruir ese secreto. Esto es una limitación real de recuperación, no autorización para regenerarlo o mostrar hashes. No se exige que el POST actual sea idempotente con recuperación de secreto cuando su contrato no lo establece.

La coordinación transaccional interna RF19/Observer ya resuelta conserva cambio/auditoría/avisos internos en una transacción PostgreSQL. **No coordina dos recursos externos**. `Gestor.publicar` ni una fila PENDIENTE demuestran envío de correo. No se altera ese mecanismo ni se reutiliza la auditoría histórica como cola mutable sin diseño aprobado.

## Decisión arquitectónica condicionada

| Alternativa | Atomicidad/recuperación | Decisión |
|---|---|---|
| Enviar antes del commit | El correo puede salir y después revertirse la convocatoria; retiene locks durante red | Insuficiente para UC02; no implementar |
| Enviar después del commit usando solo memoria | Evita anunciar un rollback previo, pero una caída pierde el código y el envío; SMTP exitoso con ACK perdido sigue siendo ambiguo | No acredita recuperación; no declarar RF completo |
| Despacho durable a partir de `notificacion`, con material secreto cifrado y referencia causal | Commit de convocatoria/aviso/material protegido, luego envío recuperable; reintentos sin repetir alta | **Propuesta recomendada**, no implementada. Reutilizar notificaciones y añadir solo persistencia técnica indispensable si se aprueba; no crear otro sistema paralelo |

Antes de implementar la tercera opción se requieren decisiones/configuración concretas:

1. Canal/proveedor autorizado (SMTP/API), remitente y URL pública confiable; secretos suministrados al servidor fuera de Git. Destinatario resuelto desde relaciones académicas, nunca un correo arbitrario del cliente.
2. Aprobar conservar temporalmente el código **cifrado** para despacho/reintento, dónde custodiar la clave y cuándo retirar ese material. No almacenar el código en claro en `mensaje`, auditoría o errores. Alternativamente, aprobar otro mecanismo seguro; rotarlo no es una solución implícita.
3. Definir el contrato de reintento/reenvío: reutilizar el mismo envío causal frente a crear uno nuevo, tratamiento de una aceptación de proveedor cuyo ACK se perdió y efecto de un retiro sobre un envío pendiente. No inventar vigencias, cuotas o tolerancias.
4. Distinguir registro de intento, aceptación por proveedor y entrega efectiva. Solo registrar ENTREGADO si existe evidencia autenticada suficiente del proveedor; un SMTP250 no confirma recepción/lectura. Si no hay confirmación, conservar estado de aceptación o desconocido, sin prometer exactamente una vez.

Contrato técnico mínimo propuesto: evento/notificación con identidad estable, destinatario y contenido resueltos por servidor, payload secreto protegido sin exposición por las DTO públicas, acuse sanitizado con id del proveedor cuando exista y registro de cada intento sin cuerpo secreto. El worker tomaría pendientes con exclusión concurrente y revalidaría retiro/estado conforme a la regla aprobada. Reintentar el despacho no volvería a crear convocatorias. Los nombres de estados, campos de persistencia, retención y protocolo de ACK se cerrarían con el proveedor elegido antes de cualquier ORM/migración. No se imponen ahora tablas nuevas ni un algoritmo de reenvío.

No se implementa un mock de correo para obtener un requisito APROBADO. Una futura aceptación usará un capturador local y fallos controlados del transporte; acreditará el emisor y el correo capturado en laboratorio, **no entrega institucional productiva**. En esta fase no se emitió correo real ni se levantó un capturador sin emisor que probar.

## Pruebas nuevas y límites

| Ejecución actual | Resultado |
|---|---|
| Focal, cuatro archivos unitarios Scheduling | **25 aprobadas**, 0 omitidas/fallos/errores |
| Relacionada, gestión de convocatorias, login SQL y errores de acceso | **74 aprobadas**, 0 omitidas/fallos/errores |
| Newman RF20 maestra sobre main | **16 solicitudes / 53 aserciones**, cero fallos técnicos; estado integral BLOQUEADO |
| Newman RF21 maestra sobre main | **16 solicitudes / 53 aserciones**, cero fallos técnicos; estado integral BLOQUEADO |

Los unitarios utilizan dobles explícitos; la relacionada combina PostgreSQL17 desechable y SQLite aislado. Su ensamblaje HTTP de fixtures no se confunde con main: Newman sí ejecuta las rutas reales de main con JWT reales y PostgreSQL **17.11**. Cuentas, matrícula, grants/asignación y sesión de convocatoria son preparación administrativa LAB; no acreditan la creación productiva del puente RF04. El nuevo código del POST se usa para login real y luego el retiro lo rechaza. SQL independiente de generación/avisos/hash y rollback se acredita en las pruebas PG; los conteos genéricos del ejecutor Newman no sustituyen esos asserts específicos.

Se conserva una advertencia Starlette/httpx en cada ejecución pytest. No se suman suites como estadísticas adicionales ni se atribuye a la simulación de un fallo SQL la simulación de SMTP. **Fallo de transporte/aceptación/entrega: NO EJECUTADOS**, porque no existe emisor configurado; no son tests omitidos convertidos en aprobados.

Evidencia: `evidencias/rf20_rf21_fase10_20261110/`, con focal/relacionada (comando, fuentes SHA, consola, JUnit y resultado), `newman_RF-20/`, `newman_RF-21/` y logs nominales. No se ejecutó Desktop ni se fabricaron capturas. No cambió código productivo ni de pruebas: no se repitió la general. La regresión de los17 RF (314HTTP/1145aserciones, Fase9) y la general2538/38 son **históricas cotejadas contra las mismas fuentes**, no ejecuciones nuevas de esta fase.

Comandos ejecutados desde la raíz; usar destinos nuevos para repetir:

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf20_rf21_fase10_20261110/run.py --modo focal --evidencias evidencias/rf20_rf21_fase10_20261110/focal
.\.venv\Scripts\python.exe -B evidencias/rf20_rf21_fase10_20261110/run.py --modo relacionada --evidencias evidencias/rf20_rf21_fase10_20261110/relacionada
$runtimeCorreo10 = Get-Content evidencias/postman_desktop_20261108/newman_runtime.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-20 --newman (Join-Path $runtimeCorreo10.ruta 'node_modules/newman') --evidencias evidencias/rf20_rf21_fase10_20261110/newman_RF-20
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-21 --newman (Join-Path $runtimeCorreo10.ruta 'node_modules/newman') --evidencias evidencias/rf20_rf21_fase10_20261110/newman_RF-21
```

## Veredicto y continuidad

**RF20 BLOQUEADO:** generación, asociación, hash y validación acreditados; falta incluir y entregar el código al estudiante en la notificación exigida. **RF21 BLOQUEADO:** altas/retiros, destinatarios, avisos internos y rollback acreditados; faltan envío externo con contenido completo y recuperación durable. No falta únicamente cargar una contraseña SMTP: hay un contrato de seguridad/recuperación por cerrar. La matriz conserva **17 APROBADOS y 10 BLOQUEADOS**, sin cambiar RF03/04/10/12/13/23/24/25.

Siguiente candidato independiente de correo y Evaluation: **RF03, cierre del contrato de administración de roles/permisos**. Sus operaciones de alta/consulta ya existen; la matriz pide precisar permisos globales por rol frente a excepciones por docente. Es independiente de este transporte, pero tampoco está libre de decisiones: aprobar ese alcance antes de habilitar nuevas asignaciones. No se recomienda reconstruirlo ni declarar otro pendiente implementable sin comprobar ese contrato. Ninguno de los diez bloqueos actuales queda automáticamente resuelto por los resultados de esta fase.

No hubo nuevas rutas, servicios, tablas, migraciones, proveedor, credenciales, correos reales o políticas académicas. Las modificaciones posteriores al checkpoint son únicamente documentación y trazabilidad de RF20/RF21; permanecen sin commit. Se conserva todo el trabajo previo y se detiene el incremento dependiente del contrato externo.
