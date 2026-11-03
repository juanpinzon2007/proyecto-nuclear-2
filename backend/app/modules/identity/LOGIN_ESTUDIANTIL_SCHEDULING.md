# Login estudiantil con convocatorias reales

Actualización de fase 7: se eliminó tolerancia_minutos del HTTP y se preparó el
contrato temporal sin una regla académica por defecto. Estado y pruebas actuales:
[POLITICA_TEMPORAL_INGRESO.md](../scheduling/POLITICA_TEMPORAL_INGRESO.md).
Las referencias al stub 503 de este informe describen la fase del login: ahora
una sesión no iniciada se rechaza con 403 y EN_CURSO sin política sigue cerrada.

Rama feature/integracion-backend, base ee025d2. Se conservaron las modificaciones
acumuladas y la carpeta evidencias preexistente. No se modificó .env ni se usaron
bases del equipo. No hay migración nueva: head único 20261031_academic_identity,
19 tablas integradas. Participation continúa fuera del alcance.

## Diagnóstico y decisiones

El login público existente recibe correo institucional y código de convocatoria;
no recibe contraseña, id_usuario ni UUID académico como prueba de identidad.
ServicioAutenticacion ya valida dominio, la pareja correo/código y después cuenta,
actividad, rol ESTUDIANTE y correo antes de emitir el JWT. Faltaba implementar su
ValidadorConvocatoria y la búsqueda de cuenta por correo.

Se revisaron ADR_IDENTIDAD_ACADEMICA.md, CONTRATO_IDENTIDAD_ACADEMICA.md,
SEGURIDAD_ESTUDIANTIL.md, PERSISTENCIA_IDENTIDAD_ACADEMICA.md, el diff acumulado,
los modelos, el código de convocatoria y la migración de asociaciones. Los
documentos anteriores describen fases históricas; este informe actualiza el login.

La credencial estudiantil sigue siendo **correo + código**, conforme al flujo
existente; no se reemplazó una contraseña por un código. El hasheador pwdlib, los
hashes de contraseña y la administración de cuentas permanecen intactos. Una prueba
de regresión confirma que siguen verificándose contraseñas correctas/incorrectas.
No se creó otro sistema JWT ni un login docente alternativo.

## Implementación

1. **ConsultaCuentaPorCorreo**: puerto nuevo y método obtener_por_correo en el
   repositorio SQLAlchemy de usuarios. Solo busca cuentas existentes. Usa la misma
   normalización strip/casefold que el dominio y rechaza con integración pendiente
   dos correos que normalizan igual. No crea cuentas ni mapeos por correo.
2. **ValidadorConvocatoriaScheduling**: adaptador en infraestructura Identity que
   consulta los modelos de Scheduling sin introducirlos en el dominio Identity.
   Resuelve cuenta → UUID SCHEDULING mediante el resolver persistente; busca la
   convocatoria de ese UUID con el hash del código, exige una única coincidencia,
   estado ACTIVA y existencia/estado reconocido de la sesión. Nunca elige la primera
   fila de un conjunto ambiguo ni consulta solo por código sin titularidad.
3. **Código compartido**: Scheduling usa hash_codigo/coincide_codigo para generar,
   comprobar ingreso y autenticar convocatoria. Se conserva SHA-256 sobre el código
   aleatorio existente y comparación constante; no se alteraron hashes almacenados.
4. **Composición real**: obtener_fabrica_autenticacion crea una Session de la fábrica
   compartida, repositorios y validador reales; comparten Session durante el login.
   Dominios/JWT deben estar configurados antes de abrir Session. La sesión se cierra
   y revierte la lectura al terminar la petición; no hay commits o escrituras en login.
5. **Contexto académico**: ValidadorContextoConvocatoria y exigir_contexto_convocatoria
   comprueban el UUID canónico del claim, igualdad con la convocatoria solicitada,
   mapeo actual, propietario y estado ACTIVA. Se compone en la ruta de ingreso
   **después** del límite cerrado de política temporal; no lo sustituye.

Los fallos de SQL/configuración devuelven 503 sin detalles privados; errores de
credenciales o ausencia de cuenta/vínculo devuelven 401 sin token. Ambigüedad de
correo/mapeo/convocatoria produce 503, sin hacer una elección implícita. Errores
inesperados se propagan para diagnóstico y no conceden acceso.

### Alcance y contenido del JWT

La respuesta de login contiene un token del emisor existente TokensJWT:

- sub = cadena de la PK INTEGER de la cuenta persistida.
- convocatoria_id = representación UUID canónica de convocatoria.id obtenida en BD.
- iss, aud, iat, nbf, exp, jti y token_type conservan la validación existente.
- No contiene código, hash del código, contraseña, correo ni claves privadas.

El cliente solo envía correo/código; el schema extra=forbid rechaza un intento de
añadir id_convocatoria. Para cambiar de convocatoria se autentica con el código de
esa convocatoria. Un token válido de A no autoriza B, aunque ambas sean del mismo
estudiante. Al retirar la convocatoria, la validación de contexto rechaza el token
anterior para esa operación académica. No se presenta la firma como prueba de
vigencia permanente del recurso.

El verificador JWT general sigue admitiendo contextos opacos antiguos como cadenas:
no rompe por ello los tokens de cuenta existentes. La nueva frontera académica
rechaza contextos ausentes, no canónicos o diferentes; no convierte un contexto
histórico en UUID por suposición. Tokens emitidos por el login integrado sí llevan
siempre la PK de Scheduling obtenida del servidor.

### Identidad fuera de una sesión

Se retiró de obtener_usuario_actual la condición global que rechazaba a cualquier
ESTUDIANTE sin id_convocatoria. Esa condición impedía /me y avisos propios a una
cuenta con JWT válido, mezclando autenticación y autorización académica.

Ahora /me exige firma vigente y cuenta activa; notificaciones exige además rol
estudiantil y UUID propio resuelto. No exige sesión EN_CURSO ni una convocatoria
ACTIVA para consultar los avisos de esa cuenta. La operación académica sí exige
su contexto verificado; un token sin contexto no autoriza esa operación.

La autenticación por código exige convocatoria ACTIVA y una sesión existente en
un estado conocido. No impone hora ni estado EN_CURSO para **identificar la cuenta**:
permite autenticar para consultar avisos antes del inicio o tras finalizar. Esto no
permite empezar participación ni leer casos académicos ajenos. La prohibición de
ingresar en sesión finalizada sigue siendo responsabilidad del servicio de ingreso.
No hay fecha de caducidad del código en el modelo: no se inventa una expiración,
reutilización o consumo único. Si se aprueba caducidad adicional, necesita contrato
y persistencia propios. Un código de convocatoria RETIRADA ya no autentica.

## Estado real de las rutas

| Ruta | Estado en este incremento |
| --- | --- |
| POST /api/v1/identity/auth/estudiantes | Login funcional con repositorios y convocatoria reales si configuración/esquema/vínculos existen |
| GET /api/v1/identity/me | JWT + cuenta activa, sin exigir sesión académica |
| GET /scheduling/notificaciones | JWT + rol + UUID propio; no acepta destinatario ajeno |
| POST /scheduling/validar-ingreso | Sigue 503 por política temporal pendiente; ningún parámetro del cliente levanta ese bloqueo |
| POST /api/v1/cases | Sigue cerrado por permiso específico pendiente; un estudiante recibe 403 por rol |
| Participation | Sin integración |

La sonda /sonda-contexto que aparece en pruebas es exclusiva de su aplicación
de laboratorio; NO se añadió a app/main.py ni es un endpoint público del producto.
Permite verificar la autorización contextual independientemente del ingreso temporal
que debe seguir cerrado. Las fixtures antiguas que aíslan el servicio de ingreso
sustituyen explícitamente esa frontera; no se describen como autenticación integrada.

## Pruebas y evidencia

`tests/identity/test_student_login_scheduling.py` crea usuarios/asociaciones solo
de laboratorio y usa crear_convocatoria real para generar los códigos y persistir
sus hashes. Las pruebas usan routers Identity/Scheduling, ServicioAutenticacion,
repositorio de usuarios, resolver/mapeo SQL, validador y TokensJWT reales. Solo se
inyectan configuración JWT/domino y fábricas de Session del laboratorio.

La suite comprueba login correcto, cuenta/código incorrectos, convocatoria ajena,
inactivo/rol ajeno/retirada, código sin convocatoria, mapeo ausente/ambiguo, correos
normalizados ambiguos y Unicode, códigos duplicados en sesiones diferentes, alcance
entre convocatorias del mismo usuario, retiro después de emitir token, tokens
expirados/manipulados/firma inválida, falta de configuración y excepciones de Session.

`test_scheduling_access_errors.py` usa mocks identificados para fallos SQL de la
consulta de convocatoria y del repositorio real de cuentas, y errores inesperados.
No se atribuye persistencia a esas pruebas.

| Ejecución | Aprobadas | Fallidas | Omitidas | Advertencias |
| --- | ---: | ---: | ---: | ---: |
| Específicas: login nuevo, errores, HTTP Identity y seguridad estudiantil anterior | 130 | 0 | 0 | 1 |
| Suite completa con laboratorios PostgreSQL habilitados | 887 | 0 | 38 | 1 |

La suite nueva agrega 54 casos: 25 con SQLite, 25 con PostgreSQL real y cuatro sin
BD (tres de errores con mocks y uno del hasheador existente). HTTP es ASGI mediante
TestClient, no una prueba de red/Uvicorn. Los 38 skipped anteriores siguen sin
comprobarse. La advertencia es la conocida Starlette/httpx. No se instalaron paquetes.

Se reutiliza el runner seguro academic_identity_support.py: crea contenedores nuevos
sps-resolver-lab-* con tmpfs, puerto local dinámico y contraseña efímera no impresa;
aplica Alembic solo con conexión de laboratorio inyectada y los elimina al terminar.
No usa los contenedores sps-identity-pg-test ni proyecto-nuclear-2-db-1 ni URLs del equipo.

### Ejemplo reproducible sin credenciales reales

Desde la raíz, Docker activo e imagen postgres:17 local:

```powershell
$env:SPS_TEST_IDENTITY_MAPPING_DOCKER = "1"
try {
    .\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_student_login_scheduling.py -k test_flujo_login_autorizado_jwt_y_notificaciones_reales -q -rs --tb=short
} finally {
    Remove-Item Env:SPS_TEST_IDENTITY_MAPPING_DOCKER
}
```

Ese ejemplo construye fixtures aisladas, genera un código con Scheduling, hace
POST login, verifica sub/convocatoria y ausencia de secretos en claims, consulta
/me y avisos propios, verifica contexto autorizado/ajeno y comprueba que el ingreso
temporal sigue 503. Ejecuta una vez con SQLite y otra con PostgreSQL; no muestra
código, contraseña o token. No hay que crear datos en la BD del proyecto.

Comandos de validación completos usados, con el mismo opt-in:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_student_login_scheduling.py backend/tests/identity/test_scheduling_access_errors.py backend/tests/identity/test_http.py backend/tests/integration/test_student_identity_security.py -q -rs --tb=short
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

## Cambios y límites del diff

- Identity application/ports.py: búsqueda por correo y comprobación de contexto,
  sin alterar el contrato de autenticación por código existente.
- Identity infrastructure/repositories.py: lectura única de cuenta normalizada.
- Identity infrastructure/scheduling_access.py: adaptador nuevo, sin escrituras.
- Identity api/dependencies.py: composición real del login/contexto y separación
  entre usuario autenticado y convocatoria autorizada.
- Scheduling domain/access_codes.py y servicios crear_convocatoria/validar_ingreso:
  extracción del mismo algoritmo existente, sin cambiarlo.
- Scheduling api/dependencies.py y router.py: contexto académico después del bloqueo
  temporal. Se mantienen la comprobación de titularidad y el bloqueo del ingreso.
- Pruebas: dos archivos nuevos y ajustes de expectativas /me/sin contexto y fixtures
  de ingreso. No se quitaron escenarios; las expectativas distinguen cuenta y ámbito.
- Sin nueva migración, cambios de ORM ni modificaciones de Participation o frontend.

## Riesgos y siguiente integración

1. La búsqueda normalizada lee IDs/correos del directorio para aplicar casefold de
   Python consistentemente; evita elegir una cuenta equivocada por diferencias
   Unicode con LOWER SQL. Es O(N): antes de escalar, reconciliar correos y aprobar
   una columna/índice canónico en otra migración. No crear ese índice sobre datos
   históricos sin comprobar colisiones.
2. El código sigue siendo una credencial de portador por requisito; correo no es un
   segundo secreto. Se necesitan decisiones sobre vigencia/rotación/reutilización,
   protección contra fuerza bruta, rate limiting y entrega institucional. No se
   implementaron políticas no aprobadas ni se declara el login listo para producción.
3. Confirmar origen y política de altas estudiantiles y asociaciones históricas.
   El login no aprovisiona cuentas, membresías ni relaciones por nombre/correo.
4. Aprobar el límite temporal y su fuente confiable; sustituir el límite cerrado
   solo al retirar la tolerancia elegida por el estudiante y probar la regla.
5. Mantener la revalidación de contexto/retiro en futuras operaciones académicas,
   atómica con cualquier escritura de inicio. El login no confirma ni inicia nada.
6. Integrar el permiso específico docente y ámbitos de convocatoria/calificaciones
   antes de habilitar sus operaciones. No abrir Cases por el mero rol.

No se modificó .env, no hubo commit, push, merge, PR ni cambio de rama. El login
con persistencia y JWT funciona en los laboratorios descritos; el ingreso temporal,
las reglas pendientes y Participation no se presentan como integrados.
