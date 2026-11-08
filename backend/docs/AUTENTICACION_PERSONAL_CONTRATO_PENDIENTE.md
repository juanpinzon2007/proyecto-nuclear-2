# Autenticación del personal: contrato pendiente y límite de implementación

> Diagnóstico histórico, sustituido en cuanto a la elección del mecanismo por
> la decisión funcional posterior del equipo: correo y contraseña asignada por
> administrador. La implementación y sus límites institucionales pendientes están
> en [LOGIN_PERSONAL_CORREO_CLAVE.md](LOGIN_PERSONAL_CORREO_CLAVE.md).
> Las afirmaciones siguientes sobre ausencia de login describen la revisión previa.

5 de noviembre de 2026, America/Bogota. Repositorio original, rama
`feature/backend-continuidad`, base `33981c8`. RF-19 operativo se conserva sin commit.

**Resultado:** no hay evidencia suficiente para elegir contraseñas locales o SSO
para docentes/administradores. No se implementó un login, endpoint, proveedor,
puerto especulativo ni cuenta inicial. Las operaciones existentes conservan su
protección JWT; el ingreso público de personal continúa sin implementarse.

## 1. RF-03 y fuentes contrastadas

RF-03 exige que el administrador cree usuarios docentes y les asigne roles y
permisos. No equivale a un requisito de login ni autoriza por sí mismo un proveedor
de identidad. Autenticación de personal es una dependencia transversal de ese flujo.

| Fuente | Evidencia y vigencia |
|---|---|
| `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, p. 4 | RF-01 define correo institucional/código para estudiantes; RF-02 rol y permiso específico; RF-03 administración docente. No define credenciales ni proveedor del personal. |
| Mismo PDF, pp. 5, 7 y 21 | RNF de protección de secretos; RN-01/02 y API propuesta de acceso estudiantil. No se encontró mandato de SSO ni autorización de login local del personal. Los RNF se titulan propuestos. |
| `_referencias_locales/Agile Inception SPS.pdf`, pp. 4 y 6 | Administrador gestiona docentes, roles y permisos. Autenticación correo/código expresamente estudiantil; no otro mecanismo de personal. |
| `_referencias_locales/Entrega 1 Proyecto Nuclear Análisis de sistemas (1).pdf` (nombre local con acentos Unicode) | Se revisaron referencias de actores/autenticación y búsqueda de credenciales/proveedores. No aporta un contrato de login del personal. |
| `identity/README.md`, Seguridad y bloqueo 3 | Advierte explícitamente que falta confirmar autenticación del administrador y docentes, pese al alta con hash Argon2. Su matriz y cifras corresponden a fases históricas. |
| `identity/CONTRATO_IDENTIDAD_ACADEMICA.md` | Resolver académico y autenticación son responsabilidades distintas. Sus propuestas de DDL antiguas no sustituyen el ORM persistente actual. |
| `identity/PERSISTENCIA_IDENTIDAD_ACADEMICA.md` y ORM actual | Registro por sistema/UUID con 0..N vínculos por usuario; resolución inequívoca. No es un proveedor de login ni se rellena automáticamente. |
| Matriz `AUDITORIA_COBERTURA_BACKEND_20261105.md` | RF-02/RF-03 parciales; emisión manual de JWT de personal en fixtures no acredita login. La instrucción actual condiciona implementar a evidencia del contrato, no aprueba uno nuevo. |

La existencia de `usuario.clave_hash` no demuestra que la universidad haya elegido
contraseñas locales. Tampoco la ausencia de un contrato local demuestra que exija
SSO. No se deduce ninguna de las dos opciones.

## 2. Código y disponibilidad real

Rutas de código relativas a `backend/app/modules/`.

| Componente | Implementación actual | Límite |
|---|---|---|
| Estudiantes | `identity/api/router.py::autenticar_estudiante` → `ServicioAutenticacion.autenticar_estudiante` → `ValidadorConvocatoriaScheduling.validar` | Único login HTTP. Correo/código, dominio explícito, usuario ESTUDIANTE activo, vínculo Scheduling y convocatoria propia ACTIVA; autenticar no aprueba ingreso temporal. |
| Credencial docente | `ServicioAdministracionUsuarios.crear_docente` → `obtener_hasheador().hash` → `RepositorioUsuariosSQLAlchemy.crear_docente` → `usuario.clave_hash` | Hash Argon2/pwdlib, nombre y hash obligatorios en el escritor real. Ningún servicio productivo verifica esa contraseña para emitir un token de personal. `verify` se usa en pruebas de hash, no en un login publicado. |
| Roles/permisos | `RepositorioUsuariosSQLAlchemy.obtener/_contexto/_permisos_rol` | Un `usuario.id_rol`, catálogo `rol`, permisos de `rol_permiso`/`permiso`; `obtener_usuario_actual` los recarga del servidor, sin aceptar roles del cliente. |
| JWT | `identity/infrastructure/security.py::TokensJWT` | HS256, secreto obligatorio de al menos 32 bytes, iss/aud/sub/iat/nbf/exp/jti/tipo. Emite identidad sin código, contraseña, roles o correo. Puede emitir sin convocatoria; eso no autoriza un emisor HTTP de personal. |
| Duración | `core/config.py::Settings.identity_jwt_minutes` y constructor TokensJWT | Configuración existente 1–60 minutos, predeterminado técnico 15. No es aprobación de la política de sesión del personal. Sin refresh token. |
| Invalidación | `obtener_usuario_actual`, ServicioAutorizacion | Cuenta eliminada/inactiva deja de acceder; cambios de rol/permisos se aplican al consultar el servidor. No hay denylist de jti, cierre de sesión, versión de credencial ni revocación selectiva de tokens. Cambiar el hash no invalida automáticamente un JWT firmado anterior. |
| Administración | POST `/api/v1/identity/docentes`, PUT `/api/v1/identity/docentes/{id_docente}/autorizaciones` | Registradas en main; ProxyAdministracionUsuarios exige ADMINISTRADOR y delega en repositorio/UoW reales. No hay bootstrap público de administrador ni login para obtener su token. |
| Alcance RF-03 | `_rol_confirmado` y `AutorizacionesDocente` | El ORM admite un rol y permisos por rol. Se rechaza multirrol o conjunto individual diferente; no se cambia `rol_permiso` para simular una excepción que afectaría a todos. No hay concesión individual arbitraria ni CRUD público de catálogos. Resolver solo el login no completa RF-03. |

Los errores existentes de Identity usan mensajes sanitizados, 401/403/422/503
según caso y `Cache-Control: no-store`. No se aprueba por analogía una política
de intentos fallidos, MFA, recuperación de claves o bloqueo temporal del personal.

### Dependencias académicas conservadas

- Cases: `obtener_docente_actual` exige DOCENTE; `obtener_docente_cases` resuelve
  vínculo CASES persistente; autoría exige CREAR_CASOS y propiedad del caso.
- Scheduling: `obtener_docente_scheduling` resuelve su vínculo propio; programación
  valida titularidad y asignación explícita al espacio. Un ADMINISTRADOR no
  obtiene automáticamente esas facultades docentes.
- Seguimiento/feedback de Participation: autorización docente y propiedad por
  relaciones SQL (`identity/infrastructure/followup.py` y
  `participation/infrastructure/individual_feedback.py`). No se alteran.
- El permiso excepcional de inicio sigue verificando creador/identidad CASES en
  `participation/infrastructure/start.py`. Un login no aprueba repetición ni RF-22.

Los UUID académicos se recuperan de asociaciones verificadas; no se generan al
autenticar ni se derivan de INTEGER. No se usa `X-Docente-Id` como identidad.

## 3. Decisiones indispensables y responsables

| Decisión | Qué está confirmado / qué falta aprobar | Responsable de acuerdo |
|---|---|---|
| Mecanismo por tipo de personal | Elegir local, SSO institucional u otra solución explícita; no hay elección vigente encontrada | Responsable institucional/TIC y equipo; validación del responsable académico del alcance |
| Población y bootstrap | Quién habilita personal, quién crea el primer ADMINISTRADOR y cómo entrega/recupera credenciales. No crear una semilla universal ni autovincular cuentas | Propietario institucional de cuentas y seguridad |
| Credenciales y errores | Si local: identificador, reglas de contraseña, recuperación, intentos/rate limit/MFA si aplican. Si SSO: proveedor, issuer, audiencia, flujo, claves y asociación estable de sujeto. Mantener errores públicos no enumerables | TIC/seguridad y equipo |
| Sesión e invalidación | Confirmar duración, renovación y efecto de baja/cambio de contraseña/cierre de sesión; decidir si basta la revocación efectiva actual por estado/rol | TIC/seguridad; aceptación de producto |
| Granularidad RF-03 | ¿Permisos comunes del rol o excepciones por docente? ¿Multirrol? El ER actual no representa esas excepciones. No ampliar esquema por suposición | Profesora/responsable académico y equipo de datos |

La pregunta funcional concreta para la profesora es la granularidad de roles y
permisos del docente. El mecanismo institucional y el bootstrap deben acordarse
con quien tenga autoridad sobre cuentas/seguridad, sin exigirle inventar esos
detalles técnicos ni convertirlos en fórmulas académicas.

## 4. Integración mínima condicionada, no implementada

Si se autoriza autenticación local: ampliar el servicio existente con una operación
de personal; consulta privada de credenciales por correo (el puerto actual retorna
contexto público, no hash), `pwdlib.verify`, estado activo y rol DOCENTE o
ADMINISTRADOR recargado desde SQL. Reutilizar TokensJWT sin convocatoria ficticia,
algoritmo alternativo ni roles del cliente. Endpoint y esquema SecretStr solo tras
aprobar ese contrato. No devolver el hash ni crear vínculos académicos al ingresar.
Aplicar la política acordada de errores/rate limit y revalidar autorización en
cada recurso después del login. No se fija ahora una ruta pública provisional.

Si se exige SSO: obtener primero contrato/registro del proveedor, validar identidad
externa y definir su asociación verificada a `usuario.id_usuario`. Un sujeto SSO
no es un UUID de Cases/Scheduling; no reutilizar esa asociación como si fueran
el mismo concepto ni convertir el identificador. No reemplazar SSO por contraseña.

Archivos candidatos, SOLO después de aprobar la alternativa local: servicio de
autenticación y ports existentes, repositorio de credenciales interno, schemas,
router y composición Identity; pruebas de Identity y aceptación HTTP PG17. La
alternativa SSO exige concretar antes el adaptador y el contrato del proveedor.
No se crean clases/puertos sin consumidor para aparentar avance.

Tras aprobar: aceptación con contraseña/identidad válida e inválida, cuenta ausente
e inactiva, ADMINISTRADOR frente a DOCENTE/ESTUDIANTE, roles vigentes en SQL,
token expirado/manipulado, acceso ajeno, ausencia de enumeración o secretos y
concurrencia/rollback del alta. Nuevas pruebas con PG17 propio, regresión relacionada
y general si cambia autenticación compartida. No sustituir relaciones críticas por mocks.

## 5. Verificaciones actuales y preservación

Paquete: `evidencias/autenticacion_personal_20261105T201553Z/`.

- OpenAPI de `app.main.app` generado en proceso aislado, sin lectura de `.env`
  ni conexión PostgreSQL: el único `/auth/` de Identity es `/auth/estudiantes`;
  las dos operaciones administrativas anteriores sí están registradas.
- Búsqueda de referencias a proveedores/contraseñas en los tres PDF y contraste
  con módulos actuales. `fuentes_academicas.json` conserva páginas/huellas.
- No se ejecutó pytest, laboratorio, migración o flujo de login de personal:
  la condición de implementación no está satisfecha y no cambió código productivo.
  No se atribuyen resultados nuevos a pruebas históricas.
- Las 2023/38 de general y las 162 relacionadas de RF-19 son ejecuciones previas;
  no prueban login de personal. Las fixtures docentes emiten TokensJWT directamente
  con cuentas/vínculos sintéticos; prueban autorización, no autenticación desde credenciales.
- Solo se añade este documento y se precisa la matriz de cobertura (RF-02/RF-03
  permanecen PARCIAL; conteos 12/9/6 sin cambios). RF-19, RF-27, código Identity,
  Participation, Evaluation, stash y los tres checkpoints se preservan.
- No commits/push/merge, cambios de rama, ORM/migraciones, `.env` ni bases permanentes.

**Siguiente acción concreta:** obtener elección institucional de mecanismo y
bootstrap, y confirmar la granularidad RF-03. Hasta entonces no hay un endpoint
de ingreso del personal que pueda implementarse o acreditarse sin inventar contrato.
