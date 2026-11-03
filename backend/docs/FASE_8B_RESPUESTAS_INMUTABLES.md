# 8B — Respuestas inmutables: política académica confirmada

2026-11-02 · `feature/integracion-backend`.

La profesora Diana Ma Valencia confirmó: «No puede modificar nada si responde una
vez ya» y «No puede modificar». Esta aclaración sustituye los contratos anteriores
que permitían editar antes del cierre y deja resuelta la prohibición de cambiar
de camino modificando una respuesta. Los informes y requisitos originales se
conservan como antecedentes; **ya no se considera pendiente esta decisión**.

## Protecciones implementadas

| Componente | Comportamiento vigente |
|---|---|
| `domain/entities.py` | `Intento.registrar_decision` rechaza una pregunta repetida, incluso con la misma opción. `modificar_decision` conserva su firma para rechazar clientes antiguos y siempre impide modificar. No existe operación de eliminación. |
| `domain/errors.py` | `RespuestaInmutable`, subtipo de `IntentoNoEditable`, distingue la prohibición académica del cierre/vencimiento. No cambia el estado de un intento activo a cerrado. |
| `application/services.py` | Después de cargar y autorizar al propietario y comprobar tiempo/cierre, rechaza PUT y selección repetida antes de consultar permisos de edición o Cases. Nuevas preguntas mantienen todos los controles de Scheduling y recorrido. |
| `application/facade.py` (sin cambios) | Sus entradas existentes delegan en el servicio protegido; no se crea otra fachada ni se acepta una dependencia permisiva como autorización para modificar. |
| `infrastructure/repository.py` | Contrasta snapshot actual bajo locks; rechaza quitar o cambiar cualquier paso existente antes de insertar nuevos. Se elimina completamente el UPDATE de pasos. Solo inserta respuestas nuevas o actualiza la cabecera para cerrar/vencer. |
| `infrastructure/cases_route.py` | El proveedor SQL real también rechaza modificar una respuesta: dejó de ser una política pendiente. No se rehace el grafo ni se cambian reglas de avance. |
| `api/errors.py`, `api/router.py` | PUT se conserva obsoleto y protegido. Para intento activo autorizado devuelve 409 `RESPUESTA_INMUTABLE`; no es upsert ni modifica reflexión. Cierre/vencimiento conserva 409 `INTENTO_NO_EDITABLE`. JWT, titularidad, validación 422 y dependencias cerradas siguen vigentes. |

Una respuesta comprende todos los campos de `paso_simulacion`, incluida reflexión,
tiempos, opción e identidad. La inmutabilidad no impide contestar la siguiente
pregunta autorizada por el grafo. No afecta la valoración docente individual
editable, que pertenece a otro flujo, ni reescribe resultados históricos de 8C.

## Migración y concurrencia

`20261102_immutable_answers` depende de `20261102_cases_graph`: instala únicamente
una función SECURITY INVOKER y un trigger BEFORE UPDATE OR DELETE en
`paso_simulacion`. Rechaza incluso UPDATE sin cambios, ORM flush y la rama UPDATE
de un UPSERT. No añade tablas, columnas, claves ni reescribe una fila. La revisión
anterior del grafo y todos los guards anteriores se conservan literalmente.

TRUNCATE/DELETE ya tenían protección; se mantienen. Los UNIQUE de pregunta por
intento, número de paso y PK impiden insertar duplicados. La aplicación/repo usan
los locks existentes de participación/intento: dos POST concurrentes se serializan,
uno confirma y el otro encuentra la selección ya registrada y recibe rechazo.
No hay actualización silenciosa. SQL directo concurrente también queda sujeto
a UNIQUE y triggers, sin depender del autorizador de la aplicación.

Upgrade bloquea escrituras mientras instala el guard. Downgrade elimina solo
su trigger y función, sin tocar respuestas ni resultados; **retira la protección
SQL adicional**, por lo que no debe confundirse con conservar esa garantía.
Se prueba exclusivamente en PostgreSQL nuevo/destruible, con filas existentes.
La garantía SQL requiere instalar la nueva revisión: no se aplicó a bases persistentes.

## Contratos de pruebas sustituidos explícitamente

No se eliminaron pruebas ni se usaron skip/xfail para la nueva política.

| Grupo previo | Adaptación y cobertura conservada |
|---|---|
| `test_domain.py::test_modificar_reemplaza_seleccion_sin_duplicar` | Ahora exige `RespuestaInmutable` y conserva opción inicial. La antigua sustitución dejó de estar permitida. |
| `test_application.py` | Modificar/cambiar rama exige rechazo definitivo. Los fallos de dependencias y guardado se provocan registrando otra pregunta válida para conservar rollback y no simular una edición permitida. |
| `test_api.py`, `test_http_functional.py` | PUT 200 y POST repetido 422 se sustituyen por 409; se conservan todos los casos de autenticación, validación, errores y privacidad. El flujo completo evalúa la opción original: cambia la nota de laboratorio esperada de 2.50 a 4.00 sin cambiar el calculador. |
| `test_steps_uuid.py` | Se conserva registro, recuperación, cierre y carrera con cierre; la modificación siempre pierde y la selección original permanece. |
| `test_cases_scheduling_operations.py` | Dos escrituras exitosas ahora son dos preguntas distintas, ambas RESPONDER; siguen verificándose la Session compartida y la carrera con vencimiento. |
| `test_route_change_guards.py` | La rama se elige en la primera respuesta. Su cambio posterior se rechaza incluso si no excluiría otras respuestas; no se vuelve a consultar Cases para intentar editar. |
| `test_cases_graph.py` | La expectativa de modificación pasa de regla pendiente a prohibición confirmada; las pruebas de grafo/ramas/ciclos no se eliminan ni rediseñan. |
| `test_academic_policy.py` | Mantiene tres alternativas disponibles, una selección y la opción original ante el PUT rechazado. No limita arbitrariamente las alternativas. |
| Pruebas de cabeza/metadata/guards | Se actualiza la cabeza y el inventario actual a 44 triggers. Los ensayos de revisiones históricas conservan sus recuentos propios. |

## Validación

- Dominio/aplicación/HTTP: **227 aprobadas**, 1 advertencia conocida de Starlette,
  12,46 s; sin fallos. Autorizaciones y repositorios son dobles de pruebas aisladas.
- Integración PostgreSQL, grafo, conservación de rutas, casos de uso y políticas
  existentes: **156 aprobadas**, 1 advertencia conocida, 119,94 s; sin fallos.
- `test_immutable_answers.py`: **21 casos nuevos**, usando PostgreSQL desechable,
  Facade/repo SQL y grafo real. Solo la autorización temporal positiva de Scheduling
  sigue siendo fixture. Cubren segunda selección igual/distinta, PUT activo/cerrado/
  vencido, agregado manipulado, SQL directo/ORM/UPSERT/DELETE/TRUNCATE, rollback de
  otra inserción y solicitudes concurrentes desde Facade y SQL. Se verifica
  upgrade/downgrade/reupgrade sin pérdida de respuestas ni cambio de tablas.
- Suite general final: **1629 aprobadas, 38 omitidas, 0 fallos, 0 errores,
  1 advertencia conocida de Starlette; 349,02 s**. Son exactamente 21 aprobadas
  adicionales sobre la línea base de 1608, conservando los casos anteriores.
  Las 38 omitidas son conexiones externas no habilitadas (29 Identity, tres
  Participation y seis de otro laboratorio por URL), no pruebas aprobadas.

Se retiran del subproceso TEST_DATABASE_URL, SPS_IDENTITY_TEST_URL y
SPS_PERSISTENCE_LAB_URL; SPS_TEST_POSTGRESQL=0 evita conexiones externas y
SPS_TEST_IDENTITY_MAPPING_DOCKER=1 habilita solo contenedores nuevos propios.
SQLite sigue limitado a pruebas aisladas sin atribuirle los triggers PostgreSQL.

Verificación final: una cabeza `20261102_immutable_answers`, 15 revisiones y 30
tablas ORM, sin nuevas tablas ni columnas. `git diff --check` termina con código
0 (aviso previo LF/CRLF de `caso_repository.py`). El inventario de contenedores
con etiqueta `sps.identity.mapping.lab=true` está vacío. No quedan laboratorios.
La comparación SHA-256 conserva literalmente las migraciones anteriores, todo
el código de Cases/grafo, el calculador/Strategy y persistencia de Evaluation y
los DBML. La única prueba de política 8C adaptada exige conservar la tercera
alternativa inicial frente a un PUT rechazado; no cambia la fórmula académica.
Los cambios locales anteriores siguen sin commit y la rama no cambia.

La regresión genera adicionalmente la evidencia automática BD2-04
`bd/laboratorio_bd2_04/evidencia_0d612754bf0445eab04daf5e882a5542.json`;
no sobrescribe las evidencias anteriores. Ninguna migración se aplicó a una base
persistente ni se alteraron resultados académicos existentes del equipo.

## Bloqueos que quedan para 8B

1. Avance en escenas con varias preguntas y posibles destinos contradictorios.
2. Ciclos/revisitas y su correspondencia con una selección inmutable por pregunta
   e intento. No se prohíben permanentemente en el esquema ni se crean selecciones
   adicionales para disimular la decisión pendiente.
3. Autorización temporal productiva de Scheduling para responder e inicio;
   consentimiento/cupos/condiciones pendientes de su composición. RF-22 sigue cerrado.
4. La evaluación no adivina preguntas futuras de una rama todavía no elegida ni
   mapeos/agregación/redondeo académicos que sigan pendientes en 8C.

No se habilitan endpoints productivos ni notas oficiales. No se cambia de rama,
no se hace commit/push/merge y no se inicia fase 9. **8B sigue abierta**, aunque
la política de inmutabilidad ya está implementada y no necesita otra aprobación.
