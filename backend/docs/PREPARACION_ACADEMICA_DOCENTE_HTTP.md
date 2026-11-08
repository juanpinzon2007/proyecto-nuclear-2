# Preparación académica docente privada — HTTP

7 de noviembre de 2026, America/Bogota. Base: feature/backend-continuidad,
HEAD `65e6583b8eff130f6e7e6eaffe45bc5b4f201c0f` más cambios locales sin commit.

## Contrato disponible en app.main

`GET /scheduling/sesiones/{sesion_id}/evaluacion/preparacion`

Sin body ni parámetros query. sesion_id es UUID. Bearer del login real
`POST /api/v1/identity/auth/personal`. Solo DOCENTE activo y vigente en SQL;
ADMINISTRADOR no hereda funciones docentes. Un rol DOCENTE ADMINISTRADOR desconocido
por Identity permanece cerrado, no se infieren permisos por su nombre.

Respuesta 200, `Cache-Control: no-store`:

- id_sesion, version_caso_id y estado_sesion históricos.
- convocatorias: id_convocatoria, id_estudiante INTEGER de Identity, estado,
  id_participacion nullable, intentos y pendientes. No hay correo ni nombre.
- intentos: id_intento, numero, estado persistido y resultado_tecnico_disponible.
  Este booleano no acredita una nota ni publicación oficial.
- pendientes de toda la sesión y **publicable=false**, siempre.

No devuelve rúbrica, rubrica_id, version_regla, niveles, puntajes, respuestas,
justificaciones, procedencia ni id_resultado_tecnico. No hay cálculos nuevos,
ausencias inferidas, consolidación, caducidad persistida o permisos de publicación.
La colección OpenAPI contiene el esquema exacto de esta proyección.

| HTTP | Condición |
|---|---|
| 401 | JWT ausente/inválido o cuenta inexistente/inactiva en la autenticación |
| 403 | Rol no docente; identidad académica ausente; sesión inexistente/ajena o creador del caso distinto |
| 422 | UUID inválido o cualquier parámetro query; no se acepta docente_id como filtro/autoridad |
| 503 | Asociación ambigua, grupo/asignación inconsistente, matrícula no inequívoca, zona o infraestructura no acreditadas |

Los mensajes se traducen mediante RutaIdentity, sin SQL interno ni informes
parciales. El recurso inexistente usa el mismo cierre que uno ajeno para no
confirmar su existencia. Si una cuenta pierde privilegios tras la autenticación,
la revalidación dentro de la instantánea también rechaza el acceso.

## Reutilización y frontera de privacidad

No se modifica `ConsultaPreparacionEvaluacionSQLAlchemy`, sus DTO internos ni
los repositorios. La dependencia HTTP aporta usuario autenticado, nueva Session
y FechasPersistencia con `PARTICIPATION_TIMESTAMP_ZONE` explícita. Zona ausente o
inválida: 503, sin UTC implícito. Identity revalida cuenta/roles desde SQL; el
lector los vuelve a comprobar dentro de su transacción y resuelve CASES y
SCHEDULING independientemente, sin conversiones INTEGER/UUID.

El lector existente exige sesión propia y creador del caso, versión/rúbrica
coherentes, todas las asignaciones y grupos del docente, y correspondencia entre
convocatorias, matrículas, participaciones e intentos. Reproduce referencias de
resultados técnicos si existen, sin devolver su nota. Una fila sin intentos solo
requiere revisión docente, nunca se convierte automáticamente en ausencia.

La lectura interna conserva el diagnóstico MATRÍCULA_NO_INEQUÍVOCA (código real
`MATRICULA_NO_INEQUIVOCA`) incluso sin poder vincular de forma cierta al alumno.
**La API rechaza el conjunto completo con 503** ante esa señal. No expone IDs de
alumnos sin ámbito demostrado ni elimina silenciosamente esas filas para presentar
un padrón aparentemente completo. Las convocatorias válidas sin participación sí
se devuelven, y las retiradas conservan TRATAMIENTO_RETIRO_PENDIENTE.

`PreparacionSesionRespuesta.desde_lectura` solo proyecta DTOs y aplica ese cierre;
no incorpora otra consulta SQL. El router pequeño de Scheduling se incluye bajo
el router ya montado en main, sin habilitar Participation general ni rutas de
resultados. Las cuatro operaciones estudiantiles existentes se conservan.

## Consistencia de lectura

Se conserva REPEATABLE READ y SET TRANSACTION READ ONLY del lector. Session nueva
por operación, no_autoflush y cierre con rollback lector, nunca commit. No se
actualiza vencimiento ni se elige la mejor nota/último intento. La instantánea
no es un permiso durable de publicación ni promete observar una revocación que
se confirme después de iniciada esa instantánea.

Pruebas HTTP instrumentan los dos engines propios (preparación y app.main),
before_flush, SQL DML/DDL y commit. SHOW transaction_read_only confirma on y el
nivel REPEATABLE READ en la consulta real; lecturas concurrentes producen el mismo
documento y no escriben. Se conservan las 13 pruebas PostgreSQL del lector interno.

## Pruebas y evidencias

Nuevo archivo `backend/tests/integration/test_main_evaluation_readiness.py`:
19 escenarios PG17/main/JWT reales. Login de personal y estudiantil por las APIs
existentes; sin overrides de autenticación/autorización. Preparación académica y
puntajes de un resultado, cuando se usan, son explícitamente LAB.

Primera aceptación: **19 aprobadas, 0 omitidas/fallidas/errores, 1 advertencia
Starlette**, 24.31 s. Relacionada: **84 aprobadas, 0 omitidas/fallidas/errores,
1 advertencia**, 146.13 s; incluye las 19 nuevas, las 13 internas y las consultas
docentes/administrativas, login, reporte cerrado y recorrido estudiantil previos.
General final nueva: **2284 aprobadas, 38 omitidas, 0 fallidas, 0 errores,
1 advertencia**, 1294.14 s. JUnit contiene 2322 casos. Las 38 omisiones son las
pruebas históricas condicionadas a URLs/configuración externas que no se habilitan
para evitar conexiones permanentes; ninguna aceptación nueva se omitió. Fuentes
estables durante las tres ejecuciones. No sumar selecciones solapadas ni atribuir
las 2265 aprobaciones anteriores a esta ejecución. La simulación de fallo HTTP
inyecta OperationalError; las relaciones y
autorizaciones críticas son SQL reales y la suite interna conserva su fallo SQL real.

Evidencia local: `evidencias/preparacion_docente_http_20261107T184605Z/`, con comandos,
HEAD, inventario SHA-256, consola y JUnit. El ejecutor desactiva .env únicamente
dentro de pytest, retira URLs heredadas y habilita el fixture Docker que crea su
PG17 tmpfs y verifica SELECT current_database() contra su base nueva. Ninguna
migración se ejecuta en bases permanentes.

Carpetas de evidencia: `pruebas_casos_20261107T185013Z` (19),
`pruebas_focal_20261107T185613Z` (84) y `pruebas_total_20261107T190002Z` (2284/38).
La general creó una evidencia BD2-04 nueva, conservada, sin modificar fuentes
preexistentes. El manifiesto local final registra los archivos y sus SHA-256.
La validación de Postman registra 219 scripts con sintaxis válida y siete
comprobaciones ASGI sin SQL; no ejecuta pm.test ni sustituye los 19 escenarios PG.

## Postman y sustentación en vivo

Colección nueva:
`backend/docs/postman/Proyecto_Nuclear_preparacion_docente.postman_collection.json`.
Siete solicitudes: login docente, login estudiante, GET autorizado, sin JWT,
JWT inválido, rol estudiante y query docente_id rechazado. Las tres últimas son
pruebas negativas; el catálogo principal añade esas cinco variantes de GET.

pm.test comprueba estado exacto, esquema JSON, publicable=false, versión esperada,
ausencia de rúbricas/notas/respuestas/IDs técnicos y no-store. Postman no puede
probar por sí solo ausencia de DML; esa garantía se acredita con los hooks PG de
las pruebas HTTP. No se declara ejecución del sandbox: CLI/Newman siguen ausentes.

Para demostrarlo desde la raíz original, con Docker e imagen postgres:17 locales:

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -B backend\docs\postman\laboratorio_http.py --puerto 8765 --puerto-lab 8766
```

1. Elegir las cuatro entradas sintéticas que solicita sin eco. No usar datos reales.
2. Importar Environment sin secretos y la nueva colección docente. Completar valores
   **locales privados** de correo/clave docente, correo/código estudiante, sesion_id,
   version_id y ambas confirmaciones LAB=true con los recursos de la consola.
3. Ejecutar sus siete solicitudes en Runner, en orden. Captura E-PREP-01: resumen
   de login/Tests, con token oculto. E-PREP-02: GET 200 y body mostrando versión,
   convocatorias sin intento, pendientes y publicable=false. E-PREP-03: Tests de
   401/403/422. No capturar Authorization, códigos ni cuerpos de login.
4. La sesión académica puede seguir EN_CURSO: esta consulta no inicia ni finaliza
   intentos. Si se desea mostrar un intento cerrado, ejecutar primero el recorrido
   integral LAB existente, sin modificarlo; volver a consultar con login docente.
5. Para mostrar una retirada, después del recorrido, listar convocatorias con la
   API docente existente y retirar únicamente la del estudiante ajeno sintético
   sin intento, con su UUID real. Usar una solicitud de retiro sobre ese UUID sin
   sustituir el contexto titular del Environment. Reconsultar la preparación y
   capturar RETIRADA/TRATAMIENTO_RETIRO_PENDIENTE. Esto cambia el fixture: recrear
   el laboratorio antes de repetir el recorrido integral.
6. Múltiples intentos, grupos inconsistentes y fallo SQL están acreditados por las
   pruebas automatizadas; no se habilita una repetición productiva para una captura.
7. Enter en la consola cierra servidores y elimina únicamente el contenedor propio.

El lanzador usa el fixture académico existente y reloj fijo solo LAB; no convierte
sus políticas en productivas. El recorrido de 30 solicitudes y sus artefactos
históricos permanecen sin cambios. Las evidencias previas de Postman no se
sobrescriben: el validador admite --salida nueva y usa creación exclusiva.

## Archivos y estado funcional

- `scheduling/api/evaluation_readiness.py`: esquemas, proyección, dependencia y GET.
- `scheduling/api/router.py`: inclusión de este router lector.
- `tests/integration/test_main_evaluation_readiness.py`: aceptación nueva.
- Artefactos reproducibles Postman: generador, catálogo, OpenAPI/inventarios,
  validador, README y colección docente específica; no cambia Environment ni
  recorrido integral si no cambia su contenido.
- Este informe y trazabilidad en la matriz, sin reclasificación de RF.

RF-13, RF-14, RF-16, RF-24 y RF-25 siguen BLOQUEADO para las operaciones académicas
oficiales. Totales: 14 IMPLEMENTADO, 8 PARCIAL, 5 BLOQUEADO. Esta consulta cierra
una integración lectora, no la fórmula ni la publicación. El contrato propuesto
`CONTRATO_FUNCIONAL_EVALUATION_PROPUESTO_20261107.md` permanece intacto como
antecedente de las decisiones pendientes.

Siguiente incremento propuesto sin inventar calificaciones: consulta docente
privada del historial de permisos de intento extra ya persistidos (autor, fecha,
cantidad concedida y usos registrados), verificando creador/ámbito; sin conceder
ni consumir autorizaciones y sin clasificar su vigencia con reglas pendientes.
Revisar primero su alcance RF-25 y reutilizar tablas/consultas existentes, sin otro
motor. Para avanzar al cálculo, obtener las decisiones de matriz, universo
evaluable y redondeo; exponer readiness no las resuelve. La aceptación manual en
Postman del lector actual es una tarea QA inmediata que tampoco necesita esas reglas.
