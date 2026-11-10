# RF-03: auditoría y autorización de escrituras administrativas

## Contrato y fuentes

RF-03 original: «El administrador crea usuarios docentes y les asigna roles y permisos». Fuente: ProyectoNuclear-IngenieriaSoftwareII (1).pdf p.4, transcripción/huella en REQUISITOS_FUENTE.json. RN-02 p.7 exige autorización por rol y permiso; no basta ocultar operaciones en la interfaz. El análisis Entrega 1, p.3, exige centralizar administración/verificación; pp.16 y 34 reutilizan Proxy y Facade.

Agile Inception SPS p.6 delimita registro/asignación, excluye nómina/contratación; p.12 describe gestionar roles y configurar permisos. P.4 dice que una persona puede asumir más de una función institucional, pero se controla por rol y recurso. **No es una especificación suficiente de multirrol por cuenta, ni autoriza un nuevo perfil DOCENTE ADMINISTRADOR.** No se exigen esos extras como si fueran criterios expresos de RF-03. Extractos y SHA-256 verificables: evidencias/rf03_fase3_20261109/FUENTES_RF03.json.

El DBML físico aprobado mantiene usuario.id_rol y rol_permiso: un rol por cuenta y permisos compartidos por rol. La API admite un conjunto por compatibilidad, pero el repositorio exige un solo rol y la coincidencia exacta con sus permisos persistidos. No se modifica el catálogo global al dar de alta un docente. No hay contrato operativo aprobado que decida cómo asignar excepciones individuales o gestionar el catálogo global desde la API. Esa es la brecha de aceptación restante; la mera ausencia de multirrol NO constituye por sí misma incumplimiento del texto original.

## Disponible antes del incremento

- Bootstrap controlado del primer administrador, sin registro HTTP público.
- POST /api/v1/identity/auth/personal: correo/clave, hash Argon2, JWT con configuración explícita.
- POST /api/v1/identity/docentes: alta por ADMINISTRADOR, datos reales obligatorios, rol DOCENTE y permisos del catálogo.
- GET /api/v1/identity/docentes: consulta administrativa privada, paginada, de solo lectura; sin hashes ni asociaciones académicas.
- PUT /api/v1/identity/docentes/{id_docente}/autorizaciones: valida perfil/catálogo permitido; no concede multirrol ni permisos individuales ficticios.
- GET /api/v1/identity/me: identidad y permisos efectivos actuales desde PostgreSQL.

Se utilizan los routers de Identity registrados en app.main. El actor proviene del JWT y la cuenta SQL, no del cuerpo/cabeceras de identidad. Cambiar id_docente identifica el recurso objetivo, no al actor. ADMINISTRADOR no obtiene por ello titularidad de todos los recursos de Cases/Scheduling/Participation. Grupos, matrículas, convocatorias y vínculos UUID no se crean automáticamente en el alta; corresponden a RF-04 y sus módulos.

## Defecto reproducido y alcance elegido

El Proxy valida el ContextoAcceso recuperado al autenticar, pero ServicioAdministracionUsuarios abría otra UoW escritora sin releer al administrador. Una revocación ya confirmada entre ambas operaciones dejaba que el contexto anterior autorizara la escritura. Cuatro pruebas HTTP/JWT/PG17 lo reprodujeron: alta devuelve 201 y asignación 200 después de desactivar la cuenta o cambiarle el rol, cuando debían rechazarse. JUnit/log original: diagnostico_antes/. No se usa skip/xfail ni se cambia el esperado para conseguir verde.

## Corrección mínima

- Reutilizar ServicioAutorizacion.exigir_rol como comprobación pura estática: su uso existente mediante instancias conserva los mismos argumentos y reglas.
- Puerto RepositorioUsuarios.obtener_para_escritura: devuelve una identidad actual estabilizada hasta commit/rollback, no la del JWT ni un valor permisivo por defecto.
- Adaptador SQL: no_autoflush, FOR SHARE sobre cuenta y rol, populate_existing=True. Los bloqueos impiden modificar activo/id_rol o el nombre del rol durante la operación. Se mantienen el motor, la Session y UoW existentes.
- ServicioAdministracionUsuarios revalida antes de consultar permisos o mutar, en alta y asignación. Cuenta inexistente/inactiva: 401; rol revocado: 403. Puerto ausente, resultado incompatible o infraestructura no disponible fallan cerrados.
- El doble unitario existente implementa explícitamente el nuevo puerto a partir de sus identidades; no se sustituye la autorización real en las pruebas HTTP.

Sin nuevas tablas, ORM, migraciones, roles, permisos, JWT alternativos o endpoints. No se modifica RF-04 ni Participation/Evaluation. Los contratos públicos se conservan: el cambio corrige una autorización obsoleta, no concede privilegios. Los métodos de escritura no confirman nada por sí solos: la UoW conserva commit/rollback.

Si la revocación gana, se rechaza antes de escribir. Si la operación ya retuvo sus bloqueos, la revocación espera al commit/rollback; no se promete cancelar retroactivamente una escritura autorizada ya confirmada. La prueba concurrente observa pg_blocking_pids, no presume bloqueo por una pausa arbitraria. Las consultas READ ONLY no utilizan este nuevo puerto. No se presenta esto como RLS ni como defensa contra un propietario SQL que eluda servicios.

## Pruebas y aceptación delimitada

Nuevas: cuatro revocaciones HTTP reales; Session ORM precargada; competencia con revocación SQL; fallo SQL tras INSERT y recuperación; nueve casos unitarios de identidad vigente/adaptador ausente. La corrección inicial aprobó 16 casos, incluidos los cuatro diagnósticos ahora corregidos. La autorización, concurrencia y rollback se prueban en PG17 desechable. Las ejecuciones ampliadas y Newman se agregarán al finalizar; no se atribuyen como actuales las cifras previas de 2502/38.

## Estado funcional y RF-04

RF-03 permanece BLOQUEADO para aceptación integral y PARCIAL como implementación. Alta/consulta/login y la protección transaccional sí se pueden acreditar. Falta acordar la semántica operativa de asignación/configuración de permisos compatible con el ER: cambios globales por rol frente a excepciones individuales. No se habilita una tabla o permiso nuevo unilateralmente. Los otros 26 RF conservan sus estados.

Para RF-04, reutilizar sesiones, convocatorias y asociaciones persistidas. El requisito original pide que el docente asocie espacio y estudiantes al programar; no obliga a crear un CRUD académico global ni a integrar matrículas externas. Antes de publicar operaciones de mantenimiento de asociaciones, fijar quién puede concederlas y con qué ámbito. Proponer después un recorrido docente propio con vínculos existentes, permisos persistentes y rechazo de grupo/estudiante/espacio ajenos; no crear UUID a partir de INTEGER ni autoconceder vínculos durante RF-03.

## Checkpoint RF-10

Se verificaron las 16 rutas contra MANIFIESTO_RF10.json, los siete cambios anteriores y el respaldo privado sin modificarlo. Commit local c6beb6f2aefeca02fcc7a3d4d2c7bd9774b1f846, mensaje test(participation): estabilizar contrato HTTP RF-10 para Angular. Incluye metadatos HTTP, pruebas, contrato, colecciones y trazabilidad, sin evidencias masivas. RF-10 conserva BLOQUEADO integralmente. RF-03 queda sin commit para revisión; no hay push ni merge.


## Resultados finales verificables (Bogotá, 9 noviembre 2026)

HEAD probado c6beb6f2aefeca02fcc7a3d4d2c7bd9774b1f846 más las modificaciones locales RF-03 identificadas mediante SHA-256. Los logs usan UTC del 10 noviembre; corresponden a la noche del 9 en Bogotá.

| Ejecución | Aprobadas | Omitidas | Fallidas / errores |
|---|---:|---:|---:|
| Diagnóstico original | 0 | 0 | 4 / 0 |
| Nuevos casos después de corregir | 16 | 0 | 0 / 0 |
| Focal ampliada | 109 | 0 | 0 / 0 |
| Relacionada | 560 | 29 | 0 / 0 |
| General nueva completa | 2518 | 38 | 0 / 0 |

La general cubre 122 archivos y 2556 casos únicos en cuatro particiones disjuntas, sin reutilizar ni conciliar ejecuciones anteriores. Las fuentes app/tests fueron estables. Las omisiones son opt-in de pruebas históricas que no usan conexiones externas del equipo; ninguna de las nuevas se omite. Se conserva la advertencia conocida Starlette/httpx. No sumar ejecuciones solapadas. JUnit y logs: diagnostico_antes/, correccion_1/, focal/, relacionada/, general_g0..general_g3/; agregado junit_general.xml y general_resultado.json.

Postman/Newman 6.2.3: las 27 carpetas iniciales aprobaron técnicamente 545 solicitudes / 2080 aserciones. Se detectó falta de cobertura del PUT en RF-03: se añadieron ocho pasos sin cambiar los nueve anteriores. La nueva RF-03 aprobó **17 solicitudes / 54 aserciones**, incluyendo PUT conforme al perfil, login real del usuario creado, GET me en solicitudes separadas y rechazos de permisos/roles no soportados o solicitante estudiante. La lectura SQL posterior confirma el perfil persistido. El catálogo LAB asigna CREAR_CASOS al rol DOCENTE: esto no significa que todos los docentes de producción reciban ese permiso por defecto.

La selección final conserva las 26 carpetas sin alterar sus requests/scripts y sustituye SOLO RF-03 por su ejecución ampliada: **553 solicitudes / 2107 aserciones**, 16 APROBADOS, 11 BLOQUEADOS, cero FALLIDOS o NO EJECUTADOS. No sumar 545 + 17; nueve casos se repiten. SELECCION_RESULTADOS.json y JUSTIFICACION_SELECCION.json, en seleccion_final/, explican la procedencia. RF-03 permanece BLOQUEADO; los otros 26 no se reclasifican. No se ejecutó Postman Desktop ni se fabricaron capturas.

## Clases, métodos y contrato público

| Archivo | Cambio |
|---|---|
| identity/application/authorization.py | ServicioAutorizacion.exigir_rol conserva exactamente su regla; ahora puede reutilizarse como función estática |
| identity/application/ports.py | RepositorioUsuarios.obtener_para_escritura documenta identidad estable hasta finalizar UoW |
| identity/application/services.py | ServicioAdministracionUsuarios._exigir_administrador; invocación antes de alta y asignación |
| identity/infrastructure/repositories.py | RepositorioUsuariosSQLAlchemy.obtener_para_escritura: lecturas actuales y locks compartidos |
| tests/identity/conftest.py | El adaptador unitario devuelve identidades explícitas para el nuevo puerto |
| tests/unit/identity/test_admin_write_authorization.py | Nueve casos de servicio/adaptador, sin DB |
| tests/integration/test_admin_write_authorization.py | Siete casos reales PG17/JWT/main, incluidos cuatro diagnósticos corregidos |
| postman/cobertura_27rf/construir.py | Ocho requests de autorizaciones; precisión del bloqueo RF03 y referencias de pruebas |
| postman/cobertura_27rf/ejecutar_rf.py | Lectura SQL independiente del perfil creado, sin secretos |

No hay endpoints nuevos ni cuerpos nuevos. Los consumidores del puerto de escritura deben implementarlo explícitamente: no hay fallback que autorice mediante el contexto anterior. Los lectores existentes continúan usando obtener, y las consultas READ ONLY no adquieren estos locks. Los timeouts usados para diagnosticar concurrencia son exclusivamente LAB; no se introduce un timeout productivo arbitrario. No se declara ausencia absoluta de deadlocks ni se sustituyen controles de acceso PostgreSQL por esta validación de aplicación.

## Repetir y revisar evidencia

Desde la raíz del repositorio, se ejecutó el runner de esta evidencia, que deshabilita .env dentro del proceso y limpia URLs heredadas, sin modificar el archivo:

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf03_fase3_20261109/run.py --modo focal --evidencias evidencias/rf03_fase3_20261109/focal
.\.venv\Scripts\python.exe -B evidencias/rf03_fase3_20261109/run.py --modo relacionada --evidencias evidencias/rf03_fase3_20261109/relacionada
# También g0, g1, g2, g3 en destinos general_gN separados.
.\.venv\Scripts\python.exe -B evidencias/rf03_fase3_20261109/agrupar_general.py
```

Los destinos ya existen: usar otros nombres al repetir. Los comandos nominales completos, HEAD, fuente local y huellas están en ejecucion.json. Para Newman se ejecutó ejecutar_rf.py --rf todos y después --rf RF-03, con módulo privado Newman 6.2.3 y destinos nuevos. Selección/reporte mediante informar.py --evidencias evidencias/rf03_fase3_20261109/seleccion_final. No se incluyen binarios ni valores secretos de Environment.

Para demostrar en Postman: preparar-27rf.ps1 -RF RF-03, importar el entorno privado nuevo, seleccionar SOLO esa carpeta y seguir PM-RF-03-01 a 17. Capturar alta 201, perfil 200, acceso estudiantil 403 y permisos incompatibles 422, junto a Test Results. Ocultar Authorization y los cuerpos/respuestas de login. La asignación positiva valida el catálogo actual; no demuestra una concesión individual inexistente. El caso de revocación entre autorización y commit se acredita con el test PG, no mediante una captura manual inventada.

## Decisión necesaria antes de cerrar RF-03

Confirmar si configurar permisos debe operar sobre un rol global (y afectar a todos sus usuarios) o sobre un docente individual. En el segundo caso, concretar la relación de persistencia y aprobación del cambio de esquema antes de implementarlo; en el primero, concretar la operación autorizada sobre el catálogo y su alcance. No es una decisión sobre reabrir acceso a cuentas inactivas ni sobre la obligación de verificar roles, ya establecida por RF-02/RN-02. Tampoco se exige unilateralmente SSO, recuperación de contraseña, nuevos roles o mantenimiento de matrículas como condición del RF original.

Siguiente incremento recomendado RF-04: comprobar/reutilizar las consultas de recursos propios que necesita el docente para elegir espacio, grupo y estudiantes matriculados al programar. Mantener identificadores INTEGER y UUID separados mediante sus vínculos persistidos. No introducir un directorio global o autovinculación. Implementar después únicamente la asociación faltante del flujo de programación con autorización de recurso, rechazo de ajenos, rollback y prueba main; las concesiones administrativas nuevas requieren definir responsable y ámbito primero.
