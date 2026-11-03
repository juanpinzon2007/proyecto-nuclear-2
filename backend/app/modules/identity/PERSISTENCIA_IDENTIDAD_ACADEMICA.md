# Resolver persistente: primer incremento

Actualización posterior: el login por convocatoria ya está implementado sobre este
resolver. Ver [LOGIN_ESTUDIANTIL_SCHEDULING.md](LOGIN_ESTUDIANTIL_SCHEDULING.md).
Las limitaciones de login descritas abajo corresponden a la fase del resolver.

Rama feature/integracion-backend, base ee025d2. Se conservan las fases previas
sin commit. Este incremento no aplica migraciones a bases existentes del equipo.

## Modelo y diferencia respecto del ADR

El ADR proponía PK(id_usuario,sistema), expresamente como cardinalidad pendiente.
La nueva instrucción evita imponerla: IdentidadAcademicaORM guarda **0..N vínculos
por cuenta/sistema**. No afirma que esos vínculos sean alias ni membresías; solo
almacena asociaciones externas verificadas. El resolver no recibe contexto para
elegir entre varios, por lo que más de uno produce 503 en lugar de elegir el primero.

Tabla identidad_academica:

- sistema VARCHAR(16), PK, NOT NULL, CASES/SCHEDULING por CHECK.
- id_academico UUID, PK, NOT NULL, CHECK distinto de UUID nulo, sin generador/default.
- id_usuario INTEGER NOT NULL, FK real a usuario.id_usuario, sin cascada.
- PK(sistema,id_academico) impide que ese UUID tenga dos propietarios en el sistema.
- Índice NO único (id_usuario,sistema) para recuperar todos sus vínculos.

No hay unicidad por cuenta/sistema, otro registro de personas ni equivalencias por
correo. Los UUID de distintos sistemas pueden coincidir sin implicar una misma
cuenta. No se asignaron vínculos históricos ni se generaron UUID personales en
producción. Los valores creados por las suites son exclusivamente fixtures de laboratorio.

## Repositorio y composición

`infrastructure/academic_identity_repository.py::RepositorioIdentidadAcademicaSQLAlchemy`
implementa ConsultaVinculosAcademicos y RegistroVinculosAcademicos:

- obtener valida la representación INTEGER propia de Identity y el sistema;
  consulta todas las filas, sin LIMIT 1, sin autoflush ni escrituras implícitas;
  devuelve VinculoAcademico inmutable. Datos corruptos o SQL indisponible cierran
  con IntegracionPendiente; un fallo inesperado se propaga.
- agregar_verificado es inserción interna explícita, sin generación, actualización
  ni upsert. Hace flush, no commit; IntegrityError se traduce a ConflictoIdentidad.
  El llamador debe hacer rollback o salir del contexto de Session al fallar.
  Una segunda asociación del mismo UUID no reasigna al propietario anterior.
- El método no verifica evidencia institucional ni otorga permiso administrativo.
  No existe endpoint para invocarlo: una futura importación necesita autorización,
  revisión y auditoría. Tampoco hay API para rectificar/eliminar asociaciones.

`api/academic_dependencies.py` compone ahora el resolver SQL con la fábrica de
Session compartida de app/db/session.py. La apertura es diferida: token y rol se
validan antes de crear la sesión del mapeo. ExitStack/Session cierran y revierten
las transacciones de lectura al terminar la petición. Se mantiene inyección de
fábricas para pruebas, sin una implementación falsa en producción.

Sin tabla migrada o infraestructura disponible: 503. Usuario sin vínculo: 403.
Más de uno, UUID nulo o incoherencia: 503. No existe fallback por cabecera ni un
UUID generado si falta correspondencia. No se crea esquema al importar/arrancar.

## Operaciones que se conservan cerradas

Antes el resolver ausente bloqueaba todas las rutas académicas. Al conectarlo,
una cuenta realmente vinculada podría llegar a reglas todavía pendientes del ADR.
Se añadieron por eso dos límites explícitos, sin inventar política:

- Cases POST /api/v1/cases: exigir_permiso_creacion_configurado devuelve 503 hasta
  integrar el permiso específico RF-02 del catálogo real. El rol docente y la
  correspondencia UUID no se presentan como ese permiso.
- Scheduling POST /scheduling/validar-ingreso: exigir_politica_ingreso_configurada
  devuelve 503, sin consultar el servicio académico, hasta usar un límite confiable
  del servidor. No se abre ingreso con tolerancia_minutos del cliente.

Las fixtures antiguas de esas operaciones sustituyen únicamente ese límite para
seguir verificando el negocio existente. La suite SQL nueva NO lo sustituye y
demuestra 503 con usuario/vínculo reales de laboratorio. No son pruebas de un
permiso o una política académica definitiva.

Login estudiantil, alcance vigente del claim convocatoria_id y política temporal
no se implementaron en este incremento. Los GET autorizados de casos/sesiones y
notificaciones propias sí pueden ejecutar repositorios/consultas reales con un
JWT válido y un vínculo unívoco persistido.

## Migración y seguridad de los datos

Nueva revisión: `20261031_academic_identity`, down_revision `6867083574f6`.
Es la única cabeza. Registra la tabla propia mediante la Base compartida y
app/db/models.py. El conjunto integrado pasa de 18 a 19 tablas; las pruebas de
esquema fueron ampliadas conservando FK, comparación metadata e historial anterior.

Upgrade: solo CREATE TABLE/INDEX de identidad_academica con FK/PK/CHECK.
No altera cuentas, roles, casos, sesiones, convocatorias ni notificaciones; no
inserta asociaciones. Downgrade elimina exclusivamente índice/tabla de esa revisión
en el laboratorio. No debe ejecutarse sobre vínculos reales: perdería ese registro;
para desactivar en un despliegue se debe cerrar la composición, conservando datos.

Ninguna migración se ejecutó sobre sps, sps-identity-pg-test ni otras bases del equipo.
No se tocó .env, no se cambiaron tipos existentes y no se integró Participation.

## Laboratorios y evidencia

`tests/identity/academic_identity_support.py` crea SQLite en memoria y, con opt-in,
un contenedor NUEVO PostgreSQL 17 por módulo de pruebas. Los contenedores llevan
nombre sps-resolver-lab-*, etiqueta sps.identity.mapping.lab=true, puerto aleatorio
limitado a loopback, contraseña aleatoria no impresa y datos en tmpfs, sin volúmenes
del equipo. El runner valida etiqueta, mounts, puerto y current_database(), exige
la BD nueva vacía y aplica Alembic con conexión inyectada. Al terminar cierra engines
y destruye solo su contenedor por el ID creado en ese runner. No usa DROP SCHEMA.

Se ejecutaron tanto las pruebas específicas como la suite completa con PostgreSQL
habilitado para estas suites. Todos los contenedores propios fueron eliminados;
los dos contenedores que estaban antes permanecen intactos.

| Prueba | Qué se ejecutó realmente |
| --- | --- |
| test_academic_identity_repository.py | Alembic, Session y repositorio reales sobre SQLite y PostgreSQL: resolución, ausencia, varios UUID conservados, propietario único, FK/NULL/CHECK, rollback y ciclos de migración |
| test_academic_identity_http_sql.py | TestClient ASGI, JWT, roles y usuarios SQL, resolver SQL, CasoService/CasoRepository y consultas Scheduling reales; solo clave JWT y fábricas de Session pertenecen a las fixtures |
| test_academic_identity_postgresql.py | PostgreSQL exclusivamente: terminar el backend propio para verificar pérdida de conexión/recuperación; dos conexiones compiten por el mismo UUID y solo un propietario se confirma |

El ciclo de migración siembra cuentas, caso, versión, espacio y sesión de prueba,
captura todas las tablas previas y comprueba que sus filas permanecen iguales tras
downgrade/upgrade de la revisión nueva. También compara metadata y comprueba la
ausencia de UNIQUE(id_usuario,sistema).

Las pruebas HTTP positivas verifican listado/detalle de casos propios, 404 de caso
ajeno, listado de sesiones propias, 403 de sesión ajena, notificaciones propias sin
avisos ajenos, rol estudiantil/docente, actividad y rechazo de cabeceras de identidad.
Otra prueba verifica rollback de lecturas y devolución de conexiones al pool.
No se sustituyen las dependencias de autenticación/rol/resolver en esos recorridos.
No se usó red HTTP/Uvicorn: es HTTP ASGI en proceso.

Resultados finales:

| Ejecución | Passed | Failed | Skipped | Warnings |
| --- | ---: | ---: | ---: | ---: |
| Específica nueva, PostgreSQL habilitado | 57 | 0 | 0 | 1 |
| Suite completa, PostgreSQL habilitado para el mapeo nuevo | 833 | 0 | 38 | 1 |

Las 38 omitidas anteriores siguen pendientes: no se habilitaron sus variables de
conexión ni se consideran aprobadas. La advertencia es la conocida de Starlette/httpx.
No se instalaron dependencias. Sin el opt-in del laboratorio nuevo, sus pruebas
PostgreSQL se omiten y deben reportarse como tales.

Desde la raíz, con Docker activo e imagen postgres:17 ya disponible:

```powershell
$env:SPS_TEST_IDENTITY_MAPPING_DOCKER = "1"
try {
    .\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_academic_identity_repository.py backend/tests/identity/test_academic_identity_http_sql.py backend/tests/identity/test_academic_identity_postgresql.py -q -rs --tb=short
    .\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
} finally {
    Remove-Item Env:SPS_TEST_IDENTITY_MAPPING_DOCKER
}
```

Este runner no recibe URL de una base del equipo ni llama a get_engine compartido
para migraciones. Si se solicita laboratorio y falla Docker o no existe la imagen,
la prueba falla: no cambia a otra base ni presenta un skip como integración exitosa.

## Archivos y límites del diff

Nuevos de producción: academic_identity_models.py, academic_identity_repository.py
y alembic/versions/20261031_academic_identity.py. Modificados: contrato y dependencias
académicas Identity, registro app/db/models.py y los dos límites API descritos.
Pruebas nuevas: soporte de laboratorio y las tres suites de este informe. Las
pruebas de esquema esperan el head nuevo/19 tablas sin borrar las verificaciones
del merge anterior. Las pruebas de indisponibilidad inyectan un fallo explícito de
Session en lugar de intentar conectarse a la BD del equipo al quitar un override.

Se actualizaron fixtures Cases/Scheduling y nombres de escenarios para distinguir
políticas simuladas e indisponibilidad SQL real. No se quitaron tests ni se rebajó
el aislamiento de recursos. El git diff acumulado también contiene las tres fases
previas, que no deben atribuirse todas a este incremento.

## Riesgos y siguiente fase ejecutable

1. Inventariar y acreditar propietarios históricos con datos autorizados; no se
   sabe cuántas cuentas tienen UUID múltiples o incompatibles. Guardar varios
   vínculos no resuelve sus contextos: el acceso sigue cerrado por ambigüedad.
2. Definir el proceso administrativo de importación/rectificación y auditoría.
   La tabla no prueba la verdad de una asociación introducida manualmente.
3. Implementar ConsultaCuentaPorCorreo y detectar normalizaciones ambiguas; no
   crear usuarios desde login ni inferir correspondencias por coincidencia de correo.
4. Implementar el adaptador ValidadorConvocatoriaScheduling usando cuenta existente,
   mapeo unívoco y código de convocatoria vigente. Fijar el significado y alcance
   de convocatoria_id en el JWT; revalidar retiro/titularidad en el acceso académico.
5. Aprobar política temporal confiable y retirar tolerancia del comando estudiantil;
   implementar ese puerto antes de sustituir el límite cerrado de ingreso.
6. Integrar permiso específico de creación y ámbito de convocatorias/calificaciones,
   sin deducirlos del rol. No habilitar Cases POST solo por resolver un UUID.
7. Ejecutar login real completo en PostgreSQL de laboratorio, incluida revocación,
   antes de considerar despliegue. Ninguna prueba actual acredita ese login.

No hubo commit, push, merge, PR ni cambio de rama. El resolver persistente funciona
en los laboratorios descritos; la integración académica completa no está terminada.
