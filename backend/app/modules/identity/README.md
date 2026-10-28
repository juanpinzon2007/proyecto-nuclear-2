# Identity: Identidad, Seguridad y Seguimiento

Incremento de Alejandro, limitado a RF-01, RF-02, RF-03, RF-15, RF-16, RF-25 y
RF-26. Preparado sobre `alejandro` con `main` incorporada en `ae45e95`.
No se ha realizado commit ni push de este incremento.

## Estado y trazabilidad

Hay lógica de aplicación, JWT y endpoints protegidos verificables con pruebas.
**La persistencia y la integración académica reales siguen bloqueadas.** Las
rutas no aceptan usuarios, convocatorias o resultados simulados en producción:
devuelven 401, 403 o 503 según corresponda. Los dobles solo viven en las pruebas.

| RF | Implementado en este incremento | Pendiente para cumplimiento integrado |
| --- | --- | --- |
| RF-01 | Normalización del correo, dominios institucionales configurables, validación de pareja correo/código mediante puerto, emisión y verificación JWT | Adaptador de Usuario y contrato de convocatoria vigente de Scheduling |
| RF-02 | Roles de administrador/docente/estudiante, verificación de permisos explícitos, ámbito académico y proxies backend | Catálogo persistido de Rol/Permiso/Usuario_Permiso y mapeo aprobado del permiso para crear casos |
| RF-03 | Crear docente y asignar roles/permisos mediante ProxyAdministracionUsuarios; rechazar permisos fuera del catálogo | ORM, repositorio y mecanismo institucional de autenticación del administrador/docente |
| RF-15 | ProxySeguimiento y ServicioSeguimiento: listado de casos realizados y detalle de respuestas/feedback dentro del ámbito docente | Lectura pública acordada con Cases, Participation y Scheduling |
| RF-16 | ServicioReportes y descarga CSV protegida; conserva notas Decimal, parciales y ausencias recibidas | Consulta SQLAlchemy con LEFT JOIN y criterio oficial de selección/consolidación de resultados |
| RF-25 | ProxyExcepciones y ServicioExcepciones: rol docente, creador del caso, participación previa y sesión no finalizada; concesión transaccional | ORM Autorizacion_Repeticion y contrato académico con garantías de concurrencia |
| RF-26 | Feedback general con autor/fecha del servidor, validación y ámbito revalidado dentro de la UoW | ORM Feedback_Docente, cardinalidad y política de creación/modificación confirmadas |

## Fuentes revisadas

Documentos locales proporcionados por el usuario, sin incorporarlos al repositorio:

- `Requisitos%20centralizados%20del%20proyecto%20nuclear_removed (1).pdf`, p. 1:
  matriz actualizada, línea base de los siete RF.
- `Entrega 1 Proyecto Nuclear Análisis de sistemas (1).pdf`, pp. 2-7, 20 y 25-26:
  separación de responsabilidades, reglas y UML de los dos proxies.
- `Agile Inception SPS.pdf`, pp. 4, 6, 8-9: roles, permisos y alcance funcional.
- Caso de estudio y guía académica: contexto; no aportan el DDL definitivo.

Los PDF son fuentes funcionales, no instrucciones para ampliar este módulo.
No se encontró en los cinco documentos un ER físico definitivo con tipos, PK,
FK, restricciones y cardinalidades de las seis entidades asignadas. Los UUID del
UML conceptual tampoco permiten decidir el tipo de identificador del ER.

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
| `infrastructure/unit_of_work.py` | Session común, un commit por caso de uso y rollback/cierre ante fallos |
| `api/` | Esquemas, rutas, errores sanitizados y composición cerrada por defecto |
| `../../../tests/identity/` | Pruebas unitarias, HTTP y laboratorio transaccional SQLite |

`ContextoAcceso`, `Rol` (enumeración de acceso), `AutorizacionRepeticion` y
`FeedbackDocente` son valores de aplicación, **no modelos SQLAlchemy**. No se
crearon columnas, tablas ni migraciones de Usuario, Rol, Permiso, Usuario_Permiso,
Autorizacion_Repeticion o Feedback_Docente. No hay `models.py` ficticio.
Los IDs públicos son cadenas opacas; no establecen tipos de columnas ni convierten
`id_usuario`, `id_estudiante`, `id_grupo_estudiante`, sesión o asignación entre sí.

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
  `app.db.session.get_session_factory`; no crea otro motor o Base. Los cuatro
  adaptadores reciben la misma Session. Las lecturas de autorización para una
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

1. **ER validado de las seis entidades asignadas:** faltan columnas/tipos, claves,
   cardinalidades, restricciones y nombres físicos. También la asociación de
   roles al usuario y el catálogo/código de permisos. Hasta recibirlo no se crean
   modelos ORM ni revisiones Alembic. Después se utilizará `app.db.base.Base`
   y se coordinará el registro en el único historial de Alembic.
2. **RF-01 / Scheduling:** falta el adaptador que valide correo+código frente a
   una convocatoria autorizada y vigente, con pertenencia/retiro comprobados,
   y devuelva referencias inequívocas de usuario y convocatoria. También faltan
   los dominios institucionales aprobados. Identity no implementa RF-20 ni crea
   códigos, sesiones, convocatorias o estudiantes de Scheduling.
3. **RF-03 / autenticación de personal:** falta confirmar cómo se autentican el
   administrador y los docentes. No se agregan contraseñas, cuentas iniciales,
   usuarios predeterminados ni un endpoint alternativo que eluda la autenticación.
4. **RF-15/16 / lectura pública:** faltan el recorrido relacional aprobado entre
   convocados, sesiones, participaciones, respuestas, resultados y feedback, así
   como las proyecciones autorizadas y la selección de resultados ante varios
   intentos. Se debe decidir también qué representan pregunta/decisión en cada
   contrato. Sin eso no se importa ORM privado de los compañeros ni se escribe
   una consulta SQLAlchemy sobre tablas inventadas.
5. **LEFT JOIN:** la fuente izquierda debe ser la población convocada autorizada;
   las relaciones opcionales deben conservar parciales y ausentes sin multiplicar
   filas por intentos. Participation/Scheduling deben suministrar ausencia
   académica confirmada y resultados oficiales. La implementación concreta y
   sus pruebas PostgreSQL están pendientes; la exportación CSV sí está probada.
6. **RF-25 / concurrencia:** falta el contrato que, en la misma transacción que
   guarda la concesión, compruebe docente creador, participación anterior y
   sesión no finalizada, coordinando el cierre concurrente de Scheduling. El ER
   debe definir duplicados, vigencia y relación de la concesión con participación/
   sesión. El consumo posterior durante un nuevo inicio pertenece al módulo de
   participación. **Autorizacion_Repeticion no se equipara a permiso_intento_extra**;
   el IdentityPort propuesto por Martín incluye consentimiento y permiso extra,
   así que no se implementa como atajo ni se introduce consentimiento en Identity.
7. **RF-26:** faltan las FK exactas y decidir unicidad, cardinalidad y modificación
   de Feedback_Docente. El servicio valida ámbito, autor, texto y fecha, pero no
   inventa esas restricciones ni implementa las notificaciones RF-27.

Las funciones `construir_*` de `api/dependencies.py` identifican los puntos de
composición pendientes y fallan con 503. No hay conexión académica real todavía.
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
