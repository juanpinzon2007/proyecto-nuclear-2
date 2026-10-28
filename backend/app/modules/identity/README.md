# Identity: Identidad, Seguridad y Seguimiento

Incremento de Alejandro, limitado a RF-01, RF-02, RF-03, RF-15, RF-16, RF-25 y
RF-26. Base conservada: commit `351169b`, rama `alejandro`.
El incremento de persistencia está sin commit, push ni Pull Request.

## Estado y trazabilidad

Se conservan los servicios, proxies y las 109 pruebas originales. Se incorporan
modelos SQLAlchemy exactos, repositorios de acceso, alta docente con hash Argon2,
persistencia nativa de permiso extra y un LEFT OUTER JOIN verificado sobre el
subconjunto de relaciones confirmado. Suite ampliada: 174 pruebas aprobadas,
incluidas SQLite y PostgreSQL 18.4 aislado. **Esto no completa las integraciones
académicas**: las fábricas pendientes siguen respondiendo 503.

| RF | Implementado en este incremento | Pendiente para cumplimiento integrado |
| --- | --- | --- |
| RF-01 | JWT y repositorio real de usuario con roles/permisos cargados del servidor | Validador de convocatoria de Scheduling y dominios aprobados |
| RF-02 | usuario/rol/permiso/rol_permiso; un rol por usuario y permisos derivados del rol; proxies conservados | Catálogo real y publicación del contrato de permiso para crear casos |
| RF-03 | Alta con nombre, correo y hash Argon2; asignación compatible con rol_permiso; repositorio y UoW reales conectados | Autenticación del personal; decisiones sobre administración global del catálogo frente a permisos individuales no representados |
| RF-15 | ProxySeguimiento y ServicioSeguimiento: listado de casos realizados y detalle de respuestas/feedback dentro del ámbito docente | Lectura pública acordada con Cases, Participation y Scheduling |
| RF-16 | Exportación conservada y LEFT OUTER JOIN real entre participación, membresía, usuario y resultado consolidado | Padrón completo confirmado y correspondencia oficial de situacion; consulta todavía no conectada al endpoint |
| RF-25 | Proxy/servicio conservados; modelo permiso_intento_extra y repositorio nativo verificados | Resolver participación, cantidad/justificación, semántica temporal y garantías transaccionales antes de adaptar la concesión actual |
| RF-26 | Proxy/servicio conservados; modelo retroalimentacion_docente fiel al DBML | Incompatibilidad: el ER vincula un feedback único a la asignación, no a la participación individual |

## Fuentes revisadas

Documentos locales proporcionados por el usuario, sin incorporarlos al repositorio:

- `Requisitos%20centralizados%20del%20proyecto%20nuclear_removed (1).pdf`, p. 1:
  matriz actualizada, línea base de los siete RF.
- `Entrega 1 Proyecto Nuclear Análisis de sistemas (1).pdf`, pp. 2-7, 20 y 25-26:
  separación de responsabilidades, reglas y UML de los dos proxies.
- `Agile Inception SPS.pdf`, pp. 4, 6, 8-9: roles, permisos y alcance funcional.
- Caso de estudio y guía académica: contexto; no aportan el DDL definitivo.

Los PDF son fuentes funcionales, no instrucciones para ampliar este módulo.
El DBML entregado posteriormente está conservado sin alteraciones en
[reference/sps.dbml](reference/sps.dbml). Este define los nombres físicos,
INTEGER, PK, FK, unicidad, longitudes y timestamps sin zona. Sus diferencias con
los valores de aplicación y los bloqueos están en [PERSISTENCE_DBML.md](PERSISTENCE_DBML.md).

Referencias técnicas consultadas: [JWT en FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[API de PyJWT](https://pyjwt.readthedocs.io/en/stable/api.html) y
[sesiones SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

## Organización

| Archivos | Responsabilidad |
| --- | --- |
| `domain/entities.py`, `domain/errors.py` | Valores de acceso y proyecciones funcionales; errores sin HTTP/ORM |
| `application/ports.py` | Interfaces necesarias de Identity; no constituyen adaptadores compartidos ya aprobados |
| `application/authentication.py`, `authorization.py` | Validación de acceso y comprobaciones de roles/permisos/ámbito |
| `application/proxy_*.py` | Controles backend antes de obtener y delegar en los servicios reales |
| `application/services.py` | Seguimiento, exportación, feedback, concesión excepcional y administración |
| `infrastructure/security.py` | Emisión/verificación JWT con PyJWT |
| `infrastructure/models.py`, `repositories.py` | Cuatro tablas de acceso; repositorio real de usuarios y sus autorizaciones por rol |
| `infrastructure/academic_models.py`, `academic_repositories.py` | Mapeos académicos del DBML y repositorio nativo de permiso_intento_extra, sin adaptación automática |
| `infrastructure/reporting_queries.py` | LEFT OUTER JOIN crudo de resultados; no clasifica ausencias ni acredita padrón completo |
| `infrastructure/credentials.py` | Hash Argon2 de la clave recibida en el alta docente |
| `infrastructure/unit_of_work.py` | Session común, un commit por caso de uso y rollback/cierre ante fallos |
| `api/` | Esquemas, rutas, errores sanitizados y composición cerrada por defecto |
| `../../../tests/identity/` | Pruebas originales conservadas y nueva persistencia SQLite/PostgreSQL |

`ContextoAcceso`, `Rol` (enumeración de acceso), `AutorizacionRepeticion` y
`FeedbackDocente` siguen siendo valores de aplicación, **no modelos SQLAlchemy**.
Ahora existen los seis mapeos físicos usuario, rol, permiso, rol_permiso,
permiso_intento_extra y retroalimentacion_docente. No se crearon usuario_permiso,
autorizacion_repeticion ni feedback_docente como tablas alternativas.
Solo las cuatro tablas de acceso tienen migración; las otras dos requieren
integrar las tablas de sus propietarios antes de coordinar su DDL.

## Seguridad y composición

- JWT HS256 fijo; clave sin valor por defecto y mínimo 32 bytes. Validación de
  firma, emisor y audiencia exactos, expiración, fecha de emisión, inicio de
  validez, identificador de token y tipo `access`. Duración configurable de
  1 a 60 minutos; valor inicial 15. No hay refresh tokens ni nuevos métodos de
  login para docentes/administradores sin contrato institucional.
- El JWT identifica al usuario y, para acceso estudiantil, a la convocatoria.
  No contiene el código, correo, roles o permisos. Estos últimos se recuperan
  del repositorio en cada solicitud protegida; un usuario eliminado o inactivo no
  conserva acceso por llevar claims de rol antiguos.
- La autenticación estudiantil requiere una pareja correo/código validada por
  el adaptador real de convocatoria. Los dominios se comparan exactamente contra
  la lista aprobada; no se adivina el dominio institucional.
- El contexto HTTP no se recibe en cuerpos, query ni cabeceras de identidad.
  Identidad/roles del solicitante, autor del feedback y fechas los fija el servidor.
- ProxySeguimiento controla rol y ámbito antes de leer/exportar o registrar
  feedback. ProxyExcepciones exige rol docente antes de construir el servicio;
  este verifica creador, participación previa y sesión dentro de la transacción.
  El administrador no adquiere automáticamente funciones del docente creador.
- ProxyAdministracionUsuarios exige rol administrador. El permiso específico
  para crear casos se comprueba con `ServicioAutorizacion.exigir_permiso` contra
  el código persistido acordado; este incremento no modifica Cases.
- Los servicios y proxies comparten interfaces. Los servicios reales se crean
  de forma diferida para poder rechazar un estudiante con 403 antes de acceder
  a una integración todavía no configurada.
- No se hacen commits en repositorios. La UoW reutiliza
  `app.db.session.get_session_factory`; no crea otro motor o Base. Los
  adaptadores configurados reciben la misma Session. Los ausentes fallan con 503
  al solicitarse, lo que permite operar administración sin simular otros módulos.
  Las lecturas de autorización para una
  escritura deben usar esa transacción y la garantía de bloqueo acordada.
- Las respuestas esperadas incluyen `Cache-Control: no-store`. Los errores de
  validación no reflejan códigos, tokens ni valores rechazados. Un fallo
  inesperado no se convierte en una autorización ni en un éxito.

## Rutas

Prefijo `/api/v1/identity`. Contrato HTTP local del incremento, pendiente de
revisión antes de consumirlo desde otros módulos o frontend.

| Método | Ruta | Protección |
| --- | --- | --- |
| POST | `/auth/estudiantes` | Correo institucional y `codigo_convocatoria` verificados |
| GET | `/me` | Bearer JWT e identidad vigente |
| POST | `/docentes` | ProxyAdministracionUsuarios |
| PUT | `/docentes/{id_docente}/autorizaciones` | ProxyAdministracionUsuarios |
| GET | `/seguimiento/casos` | ProxySeguimiento; casos realizados del ámbito docente |
| GET | `/seguimiento/participaciones/{id_participacion}` | ProxySeguimiento |
| GET | `/seguimiento/sesiones/{id_sesion}/reporte` | ProxySeguimiento; archivo CSV |
| POST | `/seguimiento/participaciones/{id_participacion}/feedback` | ProxySeguimiento; autor autenticado |
| POST | `/excepciones/repeticiones` | ProxyExcepciones; cuerpo `id_sesion`, `id_estudiante` |

El CSV actual define `id_estudiante,id_participacion,estado,nota`. Los estados de
proyección son COMPLETA, PARCIAL y AUSENCIA; su correspondencia con datos oficiales
debe aprobarse en el adaptador. No se convierten automáticamente estados de
intento en estados académicos. Una nota no confirmada permanece vacía: Identity
no calcula notas, no consolida intentos y no transforma un LEFT JOIN vacío en cero.
Se neutralizan fórmulas en identificadores al exportar para hojas de cálculo.

## Bloqueos concretos

1. **Autorizaciones del ER:** usuario tiene un único id_rol; rol_permiso concede
   permisos al rol completo. El adaptador rechaza multirrol o permisos por usuario
   distintos de los del rol con 422. No modifica el rol global para simular una
   concesión individual. El catálogo no se inventa ni se siembra en producción.
2. **RF-01 / Scheduling:** falta el adaptador que valide correo+código frente a
   una convocatoria autorizada y vigente, con pertenencia/retiro comprobados,
   y devuelva referencias inequívocas de usuario y convocatoria. También faltan
   los dominios institucionales aprobados. Identity no implementa RF-20 ni crea
   códigos, sesiones, convocatorias o estudiantes de Scheduling.
3. **RF-03 / autenticación de personal:** falta confirmar cómo se autentican el
   administrador y los docentes. El alta real requiere nombre y clave, almacenada
   como hash Argon2 en clave_hash. No se crean cuentas iniciales ni un nuevo login
   de personal por suposición. Las solicitudes antiguas sin estos datos siguen
   siendo aceptadas por el contrato anterior, pero el repositorio real responde
   422 porque no puede fabricar columnas NOT NULL.
4. **RF-15 / lectura pública:** falta la composición real del ámbito y las
   consultas académicas. La tabla global de feedback no puede devolverse como
   valoración individual. No se importan repositorios privados de compañeros.
5. **LEFT JOIN:** la fuente izquierda debe ser la población convocada autorizada;
   las relaciones opcionales deben conservar parciales y ausentes sin multiplicar
   filas por intentos. Participation/Scheduling deben suministrar ausencia
   académica confirmada y resultados oficiales. El LEFT JOIN de participaciones
   existentes a resultado_participacion ya está probado en PostgreSQL y SQLite;
   conserva los resultados faltantes como NULL. No acredita que participacion
   contenga a todos los convocados. Tampoco decide valores oficiales de situacion,
   por lo que todavía no implementa LecturaReportes ni se conecta a la ruta.
6. **RF-25 / concurrencia:** falta el contrato que, en la misma transacción que
   guarda la concesión, compruebe docente creador, participación anterior y
   sesión no finalizada. El repositorio nativo requiere id_participacion,
   id_profesor, cantidad_autorizada, justificacion y fecha sin zona. El servicio
   antiguo recibe sesión/estudiante, no aporta justificación y genera UTC con
   zona. No se inventan esos datos ni se equiparan ambos objetos automáticamente.
   El consumo de cupos e intentos corresponde a Participation; no se agrega
   consentimiento ni gestión general de intentos a Identity.
7. **RF-26:** retroalimentacion_docente.id_asignacion es NOT NULL y UNIQUE. No hay
   FK a participación individual. El modelo es fiel al ER, pero el endpoint sigue
   bloqueado hasta una decisión del equipo; no se cambia el ER ni el significado
   del feedback para forzar una escritura.

Las fábricas de usuarios y administración de `api/dependencies.py` ya componen
adaptadores reales. Sin BD/configuración/esquema disponibles responden 503.
Las fábricas académicas y de convocatoria siguen pendientes y responden 503.
Estos bloqueos no se resuelven mediante código nuevo en cases, participation o
scheduling. Frontend y Worker permanecen fuera del incremento.

## Configuración y pruebas

Variables en `.env.example`: `IDENTITY_JWT_SECRET`, `IDENTITY_JWT_ISSUER`,
`IDENTITY_JWT_AUDIENCE`, `IDENTITY_JWT_MINUTES` y
`IDENTITY_INSTITUTIONAL_DOMAINS` (array JSON). Compose las pasa únicamente a API.
`/health` no necesita estos valores ni abre conexiones a la base.

Desde la raíz, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe -m pytest backend/tests -c backend/pyproject.toml -q
```

Resultados reales y límites: [TEST_RESULTS.md](TEST_RESULTS.md).

Para ejecutar también la nueva persistencia PostgreSQL, establecer explícitamente
`SPS_IDENTITY_TEST_URL` apuntando a una BD local aislada cuyo nombre empiece por
`sps_identity_test`. Las pruebas crean/eliminan esquemas aleatorios dentro de esa
BD; nunca utilizan automáticamente POSTGRES_* ni la base del proyecto.
