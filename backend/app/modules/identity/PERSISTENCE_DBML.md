# Persistencia de Identity sobre el DBML recibido

Base de trabajo: `351169b`, rama `alejandro`. El commit y las 109 pruebas
originales se conservan sin alteraciones. No se hizo commit, push ni Pull Request.

## Fuente y comparación

Se conserva la copia literal entregada por el usuario en
[reference/sps.dbml](reference/sps.dbml), SHA-256:
`fb6ab07cfdfee38ba59e1acc879335ec0b377150acc3474b4a817a9eece229d7`.
La comparación de bytes contra el adjunto fue idéntica.

| Nombre conceptual anterior | Tabla real DBML | Resultado |
| --- | --- | --- |
| Usuario | usuario | Modelo y repositorio implementados |
| Rol | rol | Modelo; leído como un solo rol por usuario |
| Permiso | permiso | Modelo y consulta del catálogo existente |
| Usuario_Permiso | rol_permiso | Modelo de PK compuesta; los permisos pertenecen al rol, no al usuario |
| Autorizacion_Repeticion | permiso_intento_extra | Mapeo físico y repositorio nativo; no equivalencia automática con el DTO antiguo |
| Feedback_Docente | retroalimentacion_docente | Modelo fiel al ER; incompatible con feedback individual |

No se añadieron nombres alternativos ni tablas auxiliares para ocultar las
incompatibilidades. Todos los modelos usan `app.db.base.Base`. Los repositorios
usan Session síncrona y dejan commit/rollback a la UoW existente.

## Acceso: implementado y conectado

`infrastructure/models.py` reproduce las cuatro tablas de acceso con sus tipos,
longitudes, PK, FK, NOT NULL, UNIQUE y valor por defecto de activo. No añade
cascadas, estados ni restricciones inexistentes en el DBML.

`RepositorioUsuariosSQLAlchemy` carga la identidad vigente desde usuario, su rol
mediante usuario.id_rol y los códigos de permisos mediante rol_permiso/permiso.
Los IDs públicos siguen siendo cadenas; el adaptador acepta únicamente la
representación canónica de INTEGER positivo del modelo. No equipara esos IDs
con membresías o asignaciones.

La fábrica HTTP abre la Session común de forma diferida y la cierra al terminar
la petición. Por eso una solicitud sin Bearer devuelve 401 sin necesitar BD.
Una BD, configuración o esquema no disponible devuelve 503 sanitizado.

La administración usa el servicio y ProxyAdministracionUsuarios existentes.
Solo se extendió el alta con los datos NOT NULL confirmados: nombre y clave.
La clave llega como SecretStr y se almacena exclusivamente como hash Argon2;
no se expone en respuestas. No se creó un login nuevo para personal.

El cuerpo de alta real incluye correo, nombre, clave, roles y permisos. La forma
anterior sin nombre/clave conserva compatibilidad con los servicios y pruebas,
pero el repositorio real la rechaza con 422: no fabrica nombre ni hash.

### Límite real del contrato de autorizaciones

El servicio antiguo representa roles/permisos por usuario. El DBML solo permite
un rol por usuario y permisos compartidos por rol. El adaptador:

- Acepta un único rol y exige que los permisos solicitados coincidan exactamente
  con los del rol persistido.
- Rechaza multirrol o concesiones individuales incompatibles con 422.
- No modifica rol_permiso al crear o modificar un docente, evitando cambiar las
  autorizaciones de todos sus compañeros por una solicitud individual.
- No siembra roles/permisos ni adivina códigos. Reconoce los nombres de los tres
  roles funcionales sin distinguir mayúsculas; un nombre desconocido falla con 503.

La administración de concesiones individuales del contrato anterior no puede
declararse completa bajo este ER. Cambiar explícitamente el catálogo global de
permisos por rol requiere acordar esa operación y su política; no se añadió un
endpoint global para resolverlo unilateralmente.

## Migración

`20261028_identity_access` crea solo las cuatro tablas de acceso. Las pruebas
ejecutan upgrade y downgrade reales en SQLite y PostgreSQL aislados.
`alembic/env.py` registra esos modelos y acepta una conexión explícita para las
pruebas. No se ejecutó la migración en la BD del proyecto.

Antes de aplicarla, revisar la cadena de revisiones y el estado de las tablas
del equipo. No hacer stamp ni borrar tablas existentes para forzar su aplicación.
Los modelos académicos están en un archivo separado y no se registran por
defecto en Alembic: sus FK requieren las tablas propiedad de los compañeros.

## RF-25: permiso_intento_extra

El modelo reproduce:

- id_permiso_extra: INTEGER autoincremental, PK.
- id_participacion: INTEGER NOT NULL, FK a participacion.
- id_profesor: INTEGER NOT NULL, FK a usuario.
- cantidad_autorizada: INTEGER NOT NULL, default 1.
- justificacion: TEXT NOT NULL.
- fecha_autorizacion: TIMESTAMP sin zona NOT NULL.

El repositorio nativo `RepositorioPermisosExtraSQLAlchemy.agregar` persiste esos
datos y devuelve el ID generado sin commit propio. No crea intentos ni consume
cupos. No implementa guardar(AutorizacionRepeticion) como una equivalencia falsa.

La integración del endpoint sigue en 503 porque faltan:

1. Resolver sesión/estudiante del DTO anterior a una participación inequívoca,
   usando un contrato de Scheduling/Participation.
2. Proveer cantidad autorizada y justificación; el servicio anterior no entrega
   esta última. No se fabrica un texto ni se decide la cantidad por suposición.
3. Verificar creador del caso y sesión no finalizada bajo la misma transacción,
   coordinada con cierre y consumo por los compañeros.
4. Acordar representación temporal: el servicio entrega UTC con zona y el DBML
   usa timestamp sin zona. El repositorio nativo exige datetime sin zona; no
   descarta tzinfo automáticamente ni asume el huso de esos valores.

La FK id_profesor no demuestra por sí sola que sea el docente creador. Esa regla
sigue en el servicio/proxy y requiere la consulta académica real.

## RF-26: incompatibilidad que no se modificó

retroalimentacion_docente tiene id_asignacion NOT NULL y UNIQUE, FK a
asignacion_caso. Por tanto permite un feedback para la asignación completa.
No existe una columna de participación o estudiante destinatario.

El modelo está definido exactamente así. No se implementó un escritor que use
feedback general de asignación como si fuera individual, ni se creó feedback_docente
como tabla alternativa. La ruta individual continúa devolviendo 503.

El equipo debe resolver la contradicción entre RF-26 y el ER antes de escribir
el adaptador. Esa decisión también afecta al detalle de seguimiento de RF-15.

## RF-16: LEFT OUTER JOIN probado, conexión pendiente

`ConsultaResultadosReporteSQLAlchemy` recibe explícitamente las tablas públicas
externas; no declara ORM de módulos ajenos. La consulta usa estas FK del DBML:

- participacion.id_grupo_estudiante → grupo_estudiante.id_grupo_estudiante.
- grupo_estudiante.id_estudiante → usuario.id_usuario.
- resultado_participacion.id_participacion → participacion.id_participacion.

La relación con resultado_participacion es LEFT OUTER JOIN, conservando filas
sin resultado. Filtra por id_asignacion y por IDs de participaciones previamente
autorizadas por el servidor, nunca tomados como autorización del navegador.

Se consulta el resultado consolidado único; no se unen todos los intentos ni se
recalcula una nota. situacion y nota_definitiva se devuelven sin reclasificar.
Cuando no hay resultado, ambos son None: no se inventa AUSENCIA ni cero.

Faltan dos contratos para implementar LecturaReportes y conectar el endpoint:

1. Que Scheduling confirme si participacion contiene una fila por cada convocado,
   incluso quien nunca inicia. grupo_estudiante solo acredita pertenencia al
   grupo; no demuestra convocatoria a una asignación específica.
2. Que Participation confirme los valores oficiales de situacion y el estado
   de los resultados consolidados publicables. Las cadenas completa/parcial/
   ausencia usadas en fixtures no constituyen aprobación del catálogo.

Hasta entonces la consulta prueba el JOIN real del subconjunto confirmado, pero
no acredita un reporte completo de todos los convocados. La ruta permanece 503.

## Integraciones que siguen pendientes

| Funcionalidad | Estado |
| --- | --- |
| /me y lectura de identidad | Repositorio SQLAlchemy real conectado; requiere configuración, esquema y datos reales |
| Alta/validación de autorizaciones docentes compatibles | Servicio, proxy, UoW y repositorio reales conectados |
| Login estudiante RF-01 | 503: falta ValidadorConvocatoria de Scheduling y dominios aprobados |
| Login personal | No definido ni añadido; requiere el mecanismo institucional acordado |
| Seguimiento RF-15 | 503: faltan adaptadores públicos de ámbito y lectura; feedback individual incompatible |
| Reporte RF-16 | 503: falta confirmar padrón y correspondencia oficial de resultados |
| Repetición RF-25 | 503: falta adaptación completa y transaccional al registro real |
| Feedback RF-26 | 503: falta resolución del conflicto ER/requisito |

Las siete operaciones protegidas conservan sus proxies backend. No se modificó
cases, participation, scheduling, frontend, Worker, Base o fábrica común de sesiones.

Referencias técnicas consultadas: [mapeo declarativo SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)
y [hash de credenciales con pwdlib/Argon2 en FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
