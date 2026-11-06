# Login local del personal: decisión del equipo y alcance técnico

5 de noviembre de 2026. Repositorio original, `feature/backend-continuidad`,
base `33981c8`, conservando RF-19, RF-15, RF-16 y documentación sin commit.

## Decisión recibida

El usuario comunica como decisión funcional del equipo: ingreso de docentes y
administradores mediante correo y contraseña asignada por el administrador.
Esto sustituye el bloqueo de elección local/SSO del diagnóstico anterior para
este incremento. No es aprobación institucional de políticas complementarias.
No se implementa SSO, autoprovisión, multirrol ni permisos individuales.

## Contrato implementado

`POST /api/v1/identity/auth/personal` en el router Identity ya montado en main.
Entrada JSON `correo` y `clave` (SecretStr); campos adicionales rechazados.
Se normaliza correo con la función existente; contraseña se verifica exacta,
sin recortar espacios. Límites técnicos compatibles con el alta actual; no se
inventa complejidad, caducidad ni un dominio institucional específico del personal.

Solo cuenta existente/activa y rol DOCENTE o ADMINISTRADOR persistido puede emitir
token. Estudiante, contraseña incorrecta, cuenta ausente/inactiva o hash inválido
reciben el mismo 401 genérico. Identidad ambigua o infraestructura/configuración
no disponible falla cerrada con 503; validación de solicitud usa 422 saneado.
Se conserva `Cache-Control: no-store`. Nunca se devuelve hash ni contraseña.

Se reutiliza ServicioAutenticacion, con operación `autenticar_personal`, y el
nuevo puerto acotado ValidadorCredencialesPersonal. El adaptador SQL usa la misma
Session del login, el repositorio existente y `pwdlib.verify`; nunca hace commit
ni entrega el hash a Application. Cuenta/hash/rol se leen con refresco y locks
compartidos durante la solicitud. Se conserva la detección de correos ambiguos
tras casefold; no se elige uno de ellos ni se migra su unicidad por suposición.

La verificación de cuentas inexistentes usa un hash de descarte generado en el
proceso y no persistido. No es usuario, clave predeterminada ni cuenta inicial;
reduce diferencias triviales de trabajo de hash, sin prometer tiempo constante
o protección completa contra enumeración/fuerza bruta.

TokensJWT permanece sin cambios: HS256 y claims existentes, configuración segura
obligatoria, duración técnica configurable actual (1–60 minutos, predeterminado
15). Token de personal sin convocatoria, correo, contraseña ni roles/permisos.
Cada petición vuelve a consultar estado/roles/permisos del servidor. Login no
crea vínculos CASES/SCHEDULING ni deriva UUID de usuario INTEGER.

El administrador puede usar las operaciones administrativas existentes; DOCENTE
no obtiene esa facultad. ADMINISTRADOR no se convierte en docente creador ni
adquiere acceso automático a Cases, Scheduling o participaciones. Continúan las
verificaciones de permiso, identidad académica y propiedad de cada recurso.

## Provisión y políticas todavía pendientes

- El primer administrador se prepara solo en la fixture. No hay seed, clave
  predeterminada ni endpoint público de creación/autovinculación de administrador.
  El procedimiento institucional de bootstrap y reconciliación de cuentas viejas
  sigue pendiente. El hash histórico no acredita quién asignó originalmente la clave.
- El alta docente administrativa existente asigna y almacena la clave con Argon2;
  no se añade recuperación, entrega de secretos por correo ni cambio de clave.
- Duración institucional, renovación, MFA, controles de intentos/rate limit,
  bloqueo temporal y recuperación deben validarse con los responsables. No se
  inventan números. Antes de exposición pública se requieren HTTPS, gestión de
  secretos y protección operativa contra abuso; esta aceptación no los certifica.
- No hay denylist ni revocación individual de jti/logout/versión de credencial.
  Cuenta inactiva/rol/permisos revocados afectan solicitudes posteriores, pero
  cambiar un hash no revoca por sí solo JWT ya emitidos. Esa política no se altera.
- RF-03 no queda completo solo por login: se mantiene la limitación de un rol
  por usuario/permisos por rol y la decisión pendiente sobre granularidad.
- Inicio desde convocatoria, repetición, RF-22, notas y reporte oficial RF-16
  siguen bloqueados. No se modifica Evaluation ni se exportan resultados LAB.

La ruta se compone realmente en main; su disponibilidad exige configuración JWT,
PostgreSQL migrado y cuentas autorizadas con hashes válidos. No se ha desplegado
contra una base permanente ni se afirma aprobación institucional del mecanismo.


## Aceptación y resultados actuales

Las 19 pruebas de `backend/tests/integration/test_main_staff_login.py` usan
`app.main.app`, PostgreSQL 17 temporal, JWT y hashes reales, sin overrides de
credenciales, autenticación, autorización o repositorios. El primer administrador
es una preparación explícita de laboratorio; el docente del flujo principal se
crea desde HTTP administrativo y su hash se comprueba desde otra Session SQL.
Se prueban alta y asignación, login docente, separación de roles, propiedad de
casos, revocación persistida de permisos/rol/estado, fallos SQL/configuración,
credenciales inválidas, correo ambiguo, tokens expirados/manipulados, campos extra
y concurrencia. Login no hace DML, flush ni commit ni crea identidad académica.

| Ejecución | Resultado | Duración |
|---|---|---|
| Primera focalizada | 18 aprobadas, 1 fallida, 0 omitidas/errores, 1 advertencia | 12.58 s |
| Focalizada corregida | 19 aprobadas, 0 fallidas/omitidas/errores, 1 advertencia | 10.89 s |
| Regresión relacionada final | 421 aprobadas, 29 omitidas, 0 fallidas/errores, 1 advertencia | 101.54 s |
| Regresión general final | 2072 aprobadas, 38 omitidas, 0 fallidas/errores, 1 advertencia | 885.54 s |

Las ejecuciones se solapan y no se suman. Se conserva la primera falla: el test
usaba `id` donde Cases devuelve `version_id`. Se corrigió solo el test; no el
contrato productivo. Dos aserciones administrativas posteriores también quedaron
validadas por las regresiones finales. Omisiones: 29 pruebas antiguas Identity
condicionadas a URL y 9 de Participation condicionadas a configuración/URL;
ninguna se interpreta como aprobada. Advertencia conocida Starlette/TestClient.

Evidencia verificable: `evidencias/login_personal_20261105T211338Z/`:
`pruebas_casos_20261105T211634Z`, `pruebas_casos_20261105T211847Z`,
`pruebas_focal_20261105T212027Z` y `pruebas_total_20261105T212350Z` contienen
consola, JUnit XML, metadatos y huellas del árbol probado. Ejecutor reproducible:
`C:\Python313\python.exe -B evidencias/login_personal_20261105T211338Z/ejecutar_validacion.py focal`
(o `total`). No carga `.env` ni reutiliza URLs externas; requiere Docker Engine.
Base probada `33981c8` más cambios locales, no un nuevo commit. La general conservó
las fuentes y generó únicamente un artefacto experimental BD2-04 adicional.

Archivos de este incremento: Identity `application/ports.py`,
`application/authentication.py`, `infrastructure/credentials.py`,
`api/schemas.py`, `api/dependencies.py`, `api/router.py`; prueba
`tests/integration/test_main_staff_login.py`; este informe, README Identity,
nota de sustitución en el diagnóstico de autenticación y matriz de cobertura.
No se modifican esquema, migraciones ni fórmulas de Evaluation.
