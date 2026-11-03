# Seguridad estudiantil y límite de persistencia

Este documento registra una fase anterior. La persistencia y el login avanzaron
posteriormente; ver [LOGIN_ESTUDIANTIL_SCHEDULING.md](LOGIN_ESTUDIANTIL_SCHEDULING.md)
para el estado actual y la distinción entre identidad de cuenta y convocatoria.

Fecha: 31 de octubre de 2026. Rama `feature/integracion-backend`, base ee025d2.
Se revisaron y conservaron los cambios sin commit anteriores: dependencia docente,
resolver por sistema, cierre de Cases/Scheduling, sus pruebas y documentos.

## Auditoría del modelo y decisión sobre el esquema

Se inspeccionaron modelos y repositorios de Identity/Cases, modelos y servicios
de Scheduling, migraciones, dependencias JWT y pruebas. Identity mantiene usuario
INTEGER y lo expone como cadena. Cases persiste UUID docente sin FK a usuario.
Scheduling persiste UUID docente, estudiante y destinatario sin registro personal
ni FK a usuario. Convocatoria tiene su propia PK UUID y un estudiante_id separado;
la pertenencia a la sesión está en convocatoria.sesion_id. Las notificaciones de
convocatoria copian su estudiante_id y verifican esa igualdad cuando se crean.

Por tanto, los nombres y usos apuntan a referencias personales; no hay evidencia
de que estudiante_id sea la PK de convocatoria. Tampoco hay evidencia suficiente
de su relación con usuario ni de si un UUID histórico identifica una persona o
un perfil/membresía externa. Los generadores uuid_pk crean entidades académicas,
no asociaciones de personas. No se infiere significado de compartir tipo UUID.

La hipótesis id_usuario+sistema → UUID no contradice los tipos físicos actuales,
pero **no está confirmada su cardinalidad semántica**:

- No hay catálogo de identidades ni contrato del proveedor de UUID personales.
- No se ha verificado que una cuenta tenga un único UUID en Scheduling, tanto
  como docente como estudiante, ni que cambios de perfil conserven ese UUID.
- No hay inventario autorizado de asociaciones históricas o alias; las fixtures
  no demuestran que varias referencias pertenezcan a la misma persona.
- UNIQUE(sistema,id_academico) impediría compartir un UUID entre cuentas, pero
  no verifica que la titularidad importada sea correcta.

**Decisión de esta etapa:** no crear modelo ORM, repositorio SQL ni migración.
La solicitud exige no crear una migración arbitraria si hay ambigüedad. Construir
solo una tabla vacía no resolvería el significado de sus restricciones. No se
introdujo una segunda metadata ni una tabla auxiliar para simular aprobación.

Alembic conserva el único head `6867083574f6` y las 18 tablas integradas. Se
comprobó leyendo ScriptDirectory/metadata, sin ejecutar migraciones. No se accedió
a producción ni a bases del equipo, no se modificó .env ni se borraron registros.

La propuesta sigue siendo aditiva, pendiente de confirmar con los responsables:
id_usuario INTEGER FK usuario, sistema CASES/SCHEDULING, id_academico UUID no nulo,
PK(id_usuario,sistema), UNIQUE(sistema,id_academico). Antes de implementarla hay
que confirmar identidad personal estable frente a perfil/membresía y el tratamiento
de alias. Si hay varios perfiles por sistema, debe redefinirse el contrato, no
elegir un UUID al azar ni esconder varios vínculos detrás de una consulta LIMIT 1.

El plan de inventario, reconciliación, alta estable autorizada y migración está en
[CONTRATO_IDENTIDAD_ACADEMICA.md](CONTRATO_IDENTIDAD_ACADEMICA.md). La activación
del adaptador debe seguir denegada mientras falten esquema y asociaciones verificadas.
No hay altas públicas o implícitas por nombre, correo o login.

## Problemas de las rutas anteriores

- GET /scheduling/notificaciones consultaba por cualquier destinatario_id enviado
  en query, sin autenticación ni comprobación de titularidad. Conocer un UUID
  permitía pedir las notificaciones de otra persona.
- POST /scheduling/validar-ingreso comprobaba convocatoria activa, estudiante_id,
  código y horario; no verificaba que ese estudiante fuese el solicitante. No era
  un ingreso sin código, pero el UUID del cuerpo y la posesión de ese código no
  constituían una identidad de usuario recuperada desde el servidor.
- El servicio no realiza una mutación ni emite JWT en ese endpoint: devuelve una
  sesión tras validar. El problema era autorizar esa consulta/validación bajo una
  identidad elegida por el cliente. No se afirmó una escritura inexistente.

## Cambios independientes del esquema

`identity/api/dependencies.py` agrega obtener_estudiante_actual. La frontera HTTP
común _obtener_usuario_con_rol reutiliza obtener_usuario_actual y ServicioAutorizacion
para docente y estudiante; no duplica JWT ni cambia su verificador. Exige usuario
activo, rol ESTUDIANTE vigente del repositorio y el contexto de convocatoria que
Identity ya requiere en tokens estudiantiles. Un docente sin ese rol recibe 403.
Los roles de claims/cabeceras no conceden autorización.

`identity/api/academic_dependencies.py` agrega obtener_estudiante_scheduling:
resuelve el usuario autenticado para SistemaAcademico.SCHEDULING usando el contrato
existente. La fábrica productiva sigue cerrada; solo los tests inyectan asociaciones.

`scheduling/api/router.py` protege ambas rutas antes de obtener la Session académica:

1. Exige Bearer/JWT y rol estudiantil del servidor.
2. Obtiene el UUID de Scheduling mediante el resolver verificado.
3. Conserva los parámetros estudiante_id/destinatario_id por compatibilidad, pero
   los compara con el UUID resuelto y rechaza diferencias con 403.
4. Pasa únicamente el ID resuelto al servicio de ingreso o al filtro SQL de
   notificaciones. Ningún identificador del cliente sustituye al resuelto.
5. En ingreso, el servicio existente vuelve a comprobar propietario de convocatoria,
   código, estado y horario. No se cambiaron esas reglas.
6. Las respuestas exitosas de las dos rutas incluyen Cache-Control: no-store.

Sin token: 401. Inactivo/inexistente: 401. Rol ajeno: 403. Constructor del resolver
no disponible: 503. Asociación inexistente: 403. Asociación inconsistente/duplicada
o fallo declarado: 503. Error inesperado: se propaga, y ASGI produce 500 genérico
con debug desactivado; no se abre acceso ni se expone un detalle SQL como mensaje.

## Público frente a autenticado

El endpoint público de autenticación estudiantil sigue siendo el existente
POST /api/v1/identity/auth/estudiantes: correo institucional/código → validación
de convocatoria → usuario Identity → emisión JWT. No requiere un JWT previo.
Su ValidadorConvocatoria todavía está pendiente; devuelve 503 sin adaptador real.
No se creó un login alternativo ni se liberó esa integración para facilitar pruebas.

POST /scheduling/validar-ingreso es ahora una operación protegida posterior a la
autenticación, no un segundo endpoint de login. GET /scheduling/notificaciones
también requiere autenticación y titularidad. /health permanece público; las
rutas docentes conservan su protección de la fase anterior.

Se necesita coordinar el arranque real del flujo: el adaptador de login de Identity
deberá resolver correo/cuenta y validar el código con contratos internos, sin
llamar por HTTP a una ruta que ya exige JWT ni introducir un ciclo de autenticación.
No se ha demostrado correspondencia entre el id_convocatoria opaco del JWT de
Identity y la PK UUID de Scheduling. No se convierten ni comparan como si fueran
la misma entidad. En esta fase la titularidad se verifica por el UUID estudiantil
resuelto y por convocatoria.estudiante_id; no se inventa un alcance adicional del
token a una sola convocatoria. Esa semántica requiere un acuerdo explícito.

Si el equipo exige que el antiguo endpoint Scheduling sea el acceso inicial público,
debe aprobar un contrato de autenticación distinto y su responsabilidad. No se
conservará como público aceptando identidad arbitraria para mantener compatibilidad.

## Pruebas

Nuevo archivo `backend/tests/integration/test_student_identity_security.py`: 42
casos. Incluye token ausente/inválido/vencido, usuario inexistente/inactivo, rol
docente, falta de contexto de convocatoria, falta del adaptador, asociación ausente,
duplicada/inconsistente, manipulación de IDs HTTP, filtro SQL por UUID resuelto,
ingreso correcto, cabeceras ignoradas y rechazo de convocatoria ajena/inactiva,
código incorrecto, sesión cerrada y horario no permitido.

El JWT, ServicioAutorizacion, resolver y validar_ingreso son reales. Los usuarios,
la consulta de vínculos y Session son mocks. Una prueba usa el repositorio Identity
real con una Session que lanza SQLAlchemyError, comprobando 503 sin acceso académico.
Otras verifican propagación de errores inesperados y HTTP 500 sin detalles privados.
Se trata de HTTP ASGI en proceso, no tráfico de red ni PostgreSQL real.

Las tres pruebas unitarias antiguas de rutas estudiantiles ahora usan una fixture
estudiantil explícita que sustituye la dependencia; son pruebas de router/servicio,
no de autenticación. La prueba funcional de Scheduling incorpora JWT y resolver
reales con una cuenta y asociación en memoria; conserva persistencia académica
SQLite, validación del código incorrecto y ciclo de vida de la sesión. No se
eliminaron pruebas ni se debilitaron sus expectativas de negocio.

| Ejecución | Aprobadas | Fallidas | Omitidas | Advertencias |
| --- | ---: | ---: | ---: | ---: |
| Específica: Identity, seguridad y Scheduling | 351 | 0 | 29 | 1 |
| Completa: backend/tests + participation/tests | 776 | 0 | 38 | 1 |

Las omitidas no se consideran aprobadas. Advertencia conocida Starlette/httpx.
No se instalaron dependencias ni se habilitaron variables de PostgreSQL.

Comando específico:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/integration/test_student_identity_security.py backend/tests/identity backend/tests/unit/scheduling backend/tests/integration/scheduling backend/tests/integration/test_docente_identity.py backend/tests/integration/test_academic_identity_security.py -q -rs --tb=short
```

Comando completo:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

**Persistencia/unicidad en BD aislada:** bloqueadas, no ejecutadas ni acreditadas.
No existe todavía el esquema aprobado de asociaciones ni su adaptador SQL. No
se añadieron tests sintéticos que validen una tabla hipotética como si verificaran
la integración. Su futura suite debe probar FK, unicidad en ambos sentidos,
persistencia estable, rollback y concurrencia en PostgreSQL independiente.

## Riesgos y próximo incremento

- Confirmar cardinalidad personal/perfil, titularidad histórica y dueño del mapeo.
- Implementar esquema/adaptador solo tras resolver lo anterior; nunca poblar UUID
  históricos por inferencia. La ausencia de mapeo mantiene las rutas cerradas.
- Coordinar login público y contexto de convocatoria para evitar un ciclo JWT.
- El servicio existente recibe tolerancia_minutos del cuerpo HTTP. Esta fase conserva
  su regla de validación y no decide una política académica nueva; el origen autorizado
  de esa tolerancia sigue pendiente antes de habilitar el ingreso real.
- Los permisos docentes específicos y el ámbito para convocar/notificar estudiantes
  siguen pendientes; un rol no autoriza cualquier operación sobre cualquier recurso.
- Participation permanece fuera. No reutilizar por semejanza sus IDs enteros como
  UUID de Scheduling ni declarar integradas sus referencias.

## Diff de esta etapa

Producción: identity/api/dependencies.py (rol estudiantil y frontera HTTP compartida),
identity/api/academic_dependencies.py (resolución estudiantil), scheduling/api/router.py
(titularidad y respuestas sin caché).
Pruebas: nuevo test_student_identity_security.py, fixture y test funcional de
Scheduling, fixture y tres tests unitarios estudiantiles.
Documentación: este archivo y enlace desde CONTRATO_IDENTIDAD_ACADEMICA.md.
Los cambios docentes anteriores se conservan; no forman parte de una persistencia
nueva. Sin cambios a modelos, repositorios SQL, migraciones, main.py, frontend,
.env o Participation. Sin commit, push, merge, PR ni cambio de rama.
