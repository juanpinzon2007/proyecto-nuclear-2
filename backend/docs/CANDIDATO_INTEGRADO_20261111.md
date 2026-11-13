# Candidato integrado del backend

11 de noviembre de 2026, America/Bogota.

## Versión y preservación

Candidato en `C:/SPS/nuclear-acelerado-candidato`, rama `codex/acelerado-candidato-20261110`. Código final validado en `b30f98dc6d792c4ff4c287ee95e3643d70e79da2`. Newman ejecutó el código productivo de `b3bfad0591c3fa5a926b16ae5fc03cb186696833`; las dos revisiones posteriores adaptan exclusivamente pruebas de migración. Las fuentes productivas y la colección ejecutada coinciden entre ambos puntos.

Repositorio original preservado en su rama `codex/participation-inicio-main-20261109`, HEAD `2479b32d28f19e95e410b87b95e6572730d0d979`. Se reverificaron los 3447 archivos del respaldo privado y sus SHA-256, incluidos los ocho cambios anteriores y .env. Se recuperaron dos muestras en una carpeta privada independiente. Se conservaron los 3438 archivos originales sin seguimiento, stash y referencias previas. La única referencia remota local actualizada por el fetch autorizado fue origin/develop.

Base de integración `c0c6d0187ffd5e6de51f9eb7d2c3de006d6b6da7`, verificada mediante fetch específico el 11/11 a las 04:10 UTC. El merge local `bfe92fd` reconcilió esa referencia en el candidato. Los commits de este incremento son locales. La creación gestionada de worktree quedó sin respuesta y se utilizaron worktrees nativos de Git autorizados, con inventario verificado.

Evidencias y comandos completos en `C:/SPS/acelerado_nuclear_20261110`. El checkpoint documental final y el bundle se identifican en `ESTADO_FINAL.json` de esa carpeta.

## Checkpoints y worktrees

| Frente | Worktree bajo C:/SPS | Commit de origen | Commit incorporado al candidato |
|---|---|---|---|
| Docker | nuclear-acelerado-docker | 628240c | beba436 |
| Procedencia | nuclear-acelerado-procedencia | 28e336e y fa4f453 | bd5f44b y 8891dcd |
| Permisos | nuclear-acelerado-identidad | 79c1e67 | be976fe |
| Correo | nuclear-acelerado-correo | e441e77 | 7181130 |
| Asignación | nuclear-acelerado-asignacion | 8a9d0e5 | b72d3eb |
| Auxiliares Postman | nuclear-acelerado-correo | 8d5ff76 | 982aa9f |
| Composición final | nuclear-acelerado-candidato | b3bfad0 | b3bfad0 |
| Compatibilidad de pruebas | nuclear-acelerado-correo | 1a852d5 y e3e3df3 | f981aec y b30f98d |
| Simulación existente | nuclear-acelerado-simulacion | bd5f44b | Sin incremento adicional |

Los worktrees utilizan ramas independientes codex/acelerado. Los JSON de evidencia conservan hashes completos, comandos y versión. Los archivos generados por la prueba BD2 permanecen locales y excluidos de commits.

## Funcionalidades integradas

| Frente | Resultado verificable |
|---|---|
| RF-03 | ADMINISTRADOR activo consulta y configura permisos globales DOCENTE mediante GET/PUT `/api/v1/identity/roles/docente/permisos`. Reutiliza rol_permiso, UoW y revalidación SQL. Los tokens existentes reciben el perfil vigente. Las actualizaciones concurrentes se serializan. |
| RF-04 | POST `/scheduling/sesiones` crea sesión, asignación y convocatorias en una transacción cuando recibe grupo propio, estudiantes matriculados y fecha límite explícita. Respeta versión publicada exacta, grants y titularidad. |
| RF-13/RF-24 | Lectura y reproducción de los dos snapshots de procedencia reconocidos del motor, con calificaciones, rúbrica, fracciones y huellas históricas preservadas. Se conservan las Strategies y el calculador. |
| RF-20/RF-21 | Despacho cifrado durable asociado a la notificación existente. SMTP configurable, captura TCP real, destinatario SQL, código individual, mensaje, URL, cancelación, concurrencia, rollback y recuperación acreditados. |
| RF-10/RF-12/RF-23/RF-25 | Nueva ejecución de 162 aceptaciones y regresiones existentes. Las políticas productivas obligatorias conservan sus puertos cerrados cuando falta aprobación. |
| Docker | PARTICIPATION_TIMESTAMP_ZONE explícita y passthrough de correo opcional. Imagen productiva reconstruida y verificada mediante HTTP, JWT real y PostgreSQL 17. |

Los permisos globales DOCENTE y los valores de asignación fueron confirmados por el responsable funcional durante este incremento. Son decisiones del proyecto. Su documentación conserva esa procedencia.

La corrección de procedencia compara metadata histórica congelada y AST ejecutable equivalente. Las pruebas cruzadas escriben y leen PostgreSQL con el motor vigente y las dos capturas históricas verificadas. Los documentos de BD se validan mediante hashes exactos. Ningún código recibido de BD se ejecuta.

## Contratos para clientes

RF-03 recibe `{"permisos":["CREAR_CASOS"]}` o una lista vacía explícita. La respuesta contiene rol, catálogo, perfil, cantidad de cuentas afectadas y `alcance=GLOBAL_ROL`. Exige ADMINISTRADOR activo. Los códigos deben existir en el catálogo. GET utiliza REPEATABLE READ / READ ONLY.

RF-04 extiende el cuerpo existente con `grupo_id` INTEGER positivo, `estudiantes_ids` UUID Scheduling distintos y `fecha_limite_ingreso` con offset dentro del intervalo inclusivo de la sesión. Los tres campos se suministran juntos. El servidor utiliza `intentos_base=1` y `estado=programada`. Esta asignación conserva separada la admisión por habilitación.

El POST con selección devuelve 201 y añade `id_asignacion` y `convocatorias`, con los códigos de una sola entrega y Cache-Control no-store. Los GET mantienen la privacidad de esos códigos. El POST sin selección conserva el contrato anterior de programación. Cada POST de creación válido representa un recurso nuevo. Las solicitudes idénticas pueden crear sesiones distintas.

Errores acreditados 401 por autenticación, 403 por ámbito, 422 por selección inválida y 503 por configuración o persistencia. Los clientes pueden discriminar la respuesta extendida por `id_asignacion`. OpenAPI y las colecciones contienen los DTO completos.

## Persistencia y configuración

Una cabeza Alembic `20261110_durable_mail` y 40 tablas físicas. La tabla técnica nueva `despacho_correo` usa `id_notificacion` UUID como PK/FK a la notificación canónica, payload BYTEA cifrado, estado, intentos, error sanitizado y fechas con zona. CHECKs verifican estados, contador, payload y aceptación. La migración conserva las tablas históricas y el downgrade protege el historial existente. Las pruebas ejecutaron subida, bajada y comparación completa ORM en PostgreSQL 17 desechable.

El ER conceptual y su DBML se preservan. Las contribuciones y calificaciones históricas conservan su representación exacta.

Correo deshabilitado por defecto. Al habilitarlo se exigen host, puerto, TLS, remitente, URL y clave Fernet. Las credenciales son externas al código. STARTTLS y SSL utilizan el contexto TLS del sistema. LAB_LOOPBACK se restringe al capturador local. El dispatcher operativo se invoca mediante `python -m app.modules.scheduling.infrastructure.mail_delivery --limit 20` en un entorno configurado.

La cola se genera para avisos nuevos con correo habilitado. Las convocatorias históricas conservan sus hashes. La captura acredita aceptación SMTP local. La entrega a destinatarios institucionales requiere configurar y validar el proveedor externo. Una caída entre la aceptación SMTP y el commit puede causar un reenvío. El Message-ID estable permite correlacionarlo. La operación requiere custodiar la clave y supervisar el despacho.

## Pruebas actuales

| Ejecución | Resultado |
|---|---|
| Procedencia focal / relacionada | 9 / 150 aprobadas |
| Docker inicial focal / relacionada | 5 / 20 aprobadas |
| Identity relacionada | 401 aprobadas, 29 omitidas |
| RF-04 focal / relacionada final | 27 / 207 aprobadas |
| Correo focal / esquema | 18 aprobadas / 292 aprobadas y 29 omitidas |
| Composición asignación-correo e imagen final | 7 aprobadas |
| Simulación existente | 162 aprobadas |
| General final completa | 2611 aprobadas, 38 omitidas, cero fallos y errores, 130 archivos en cuatro particiones disjuntas |
| Newman completo | 27 carpetas, 569 solicitudes, 2166 aserciones, cero fallos técnicos |

Las ejecuciones se solapan y se presentan por separado. Los 38 skips corresponden a conexiones PostgreSQL externas opcionales. La aceptación crítica utilizó contenedores propios de PostgreSQL 17. La advertencia conocida de Starlette/httpx está conservada. Los JUnit y logs registran nominalmente resultados y omisiones.

La primera general terminó con 2608 aprobadas, 38 omitidas y tres fallos de expectativas de migración. Se preservó íntegra. Se actualizó el inventario de la cabeza actual y la lista explícita de objetos posteriores para comparaciones históricas. La cabeza actual sigue comparándose sin filtros. Después se ejecutaron nuevamente las cuatro particiones completas.

También se preservan el diagnóstico de procedencia, el spy obsoleto, el fallo inicial de preparación RF-04, el rol ORM precargado y la interrupción de Docker. El defecto real del rol precargado se corrigió reutilizando obtener_para_escritura. Las pruebas actuales verifican su rechazo antes del INSERT.

## Cobertura de los 27 RF

APROBADO corresponde al alcance funcional acreditado sobre datos de laboratorio y componentes reales. Las preparaciones administrativas y las operaciones LAB se identifican en cada carpeta. La ejecución de las 27 carpetas conserva seis bloqueos académicos y de composición.

| RF | Estado | HTTP | Aserciones |
|---|---|---:|---:|
| RF-01 | APROBADO | 6 | 18 |
| RF-02 | APROBADO | 15 | 49 |
| RF-03 | APROBADO | 26 | 85 |
| RF-04 | APROBADO | 14 | 46 |
| RF-05 | APROBADO | 15 | 49 |
| RF-06 | APROBADO | 15 | 49 |
| RF-07 | APROBADO | 15 | 49 |
| RF-08 | APROBADO | 15 | 49 |
| RF-09 | APROBADO | 16 | 53 |
| RF-10 | BLOQUEADO | 32 | 141 |
| RF-11 | APROBADO | 32 | 141 |
| RF-12 | BLOQUEADO | 32 | 141 |
| RF-13 | BLOQUEADO | 32 | 141 |
| RF-14 | APROBADO | 19 | 68 |
| RF-15 | APROBADO | 42 | 174 |
| RF-16 | APROBADO | 15 | 52 |
| RF-17 | APROBADO | 15 | 49 |
| RF-18 | APROBADO | 12 | 39 |
| RF-19 | APROBADO | 17 | 54 |
| RF-20 | APROBADO | 17 | 57 |
| RF-21 | APROBADO | 17 | 57 |
| RF-22 | APROBADO | 6 | 18 |
| RF-23 | BLOQUEADO | 32 | 141 |
| RF-24 | BLOQUEADO | 18 | 62 |
| RF-25 | BLOQUEADO | 35 | 150 |
| RF-26 | APROBADO | 38 | 161 |
| RF-27 | APROBADO | 21 | 73 |

La matriz nominal y el CSV enlazan cada solicitud, sus aserciones y pruebas pytest aprobadas. Los 17 RF anteriores conservaron su aceptación. RF-03, RF-04, RF-20 y RF-21 avanzan con evidencia nueva. El proveedor externo de correo sigue siendo una dependencia de despliegue.

| RF bloqueado | Decisión o contrato pendiente | Responsable |
|---|---|---|
| RF-10 | Conciliación del documento que describía edición con la inmutabilidad vigente. Semántica de varias preguntas, ciclos y revisitas. | Equipo funcional y profesora |
| RF-12 | Documento de consentimiento oficialmente publicado y vigente, evidencia de aprobación y políticas explícitas de inicio/provisión, incluido estado inicial de Participation. | Institución y equipo funcional |
| RF-13 | Alcance académico de PREGUNTAS_100_V1 frente a otras rúbricas y conciliación de UC05 con el comando docente posterior al cierre. | Equipo funcional y profesora |
| RF-23 | Composición productiva del inicio que activa el tiempo individual, dependiente de RF-12. | Equipo funcional y backend |
| RF-24 | Alcance de rúbricas y orquestación UC05 compartidos con RF-13, incluida adopción del parcial voluntario propuesto. | Equipo funcional y profesora |
| RF-25 | Inicio productivo autorizado y vinculación explícita entre evaluaciones de casos distintos. | Equipo funcional y backend |

La escala, igualdad de pesos, ceros autorizados, Decimal y ROUND_HALF_UP de PREGUNTAS_100_V1 ya tienen implementación técnica. Las siguientes precisiones se concentran en aplicabilidad y orquestación.

## Reproducción y sustentación

Desde PowerShell, con Docker Engine abierto y las dependencias declaradas instaladas.

```powershell
Set-Location C:\SPS\nuclear-acelerado-candidato
$python = 'C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2\.venv\Scripts\python.exe'
$env:PYTHONPATH = "$PWD\backend;C:\SPS\acelerado_nuclear_20261110\correo\vendor"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
& $python -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-04 --preparar
```

El preparador imprime dos rutas privadas para importar la colección y el Environment activo. Cada carpeta se ejecuta desde su primera solicitud, con su propio laboratorio. RF-03 muestra alta y permisos globales. RF-04 demuestra la misma sesión, asignación y convocatorias. Para RF-20 o RF-21, preparar la carpeta correspondiente y usar `m` en la consola antes de los pasos CORREO 1 y CORREO 2. La consola verifica el SMTP real local y devuelve únicamente conteos y comprobaciones seguras. Finalizar con `q` libera los recursos propios.

Capturas manuales pendientes de Postman Desktop. Guardar estado HTTP y Test Results de permisos globales, revocación efectiva, programación 201 y consulta de sus convocatorias, rechazo ajeno 403, selección inválida 422 y las dos comprobaciones SMTP. Mantener ocultos Authorization, los cuerpos de login y los códigos. La ejecución automatizada acreditada corresponde a Newman.

Para repetir la validación completa con destinos nuevos.

```powershell
$marca = Get-Date -Format yyyyMMddTHHmmss
& $python -B -u C:\SPS\acelerado_nuclear_20261110\qa_candidato.py --general --evidencias "C:\SPS\acelerado_nuclear_20261110\repeticion_$marca"
& $python -B -u C:\SPS\acelerado_nuclear_20261110\newman_candidato.py --evidencias "C:\SPS\acelerado_nuclear_20261110\newman_$marca"
```

Los runners desactivan .env y URLs heredadas, utilizan bases nuevas y conservan consola, JUnit, versión y huellas de fuentes. El despliegue real requiere aplicar la migración aprobada y configurar secretos, zona histórica, proveedor y supervisión en su entorno controlado.

## Continuidad

El candidato queda preparado para revisión del equipo. El siguiente incremento de mayor impacto es cerrar el consentimiento oficial y el contrato de inicio/provisión con los puertos existentes. Esto permite avanzar coordinadamente RF-12, RF-23 y RF-25. En paralelo funcional, concretar aplicabilidad de rúbricas y UC05 para RF-13/RF-24. El backend conserva esos seis requisitos pendientes.
