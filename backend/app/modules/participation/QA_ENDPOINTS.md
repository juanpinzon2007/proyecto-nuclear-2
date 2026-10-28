# Evidencia de QA funcional — Participación SPS

Reporte generado desde `tests/artifacts/qa.xml`, producido por la ejecución real de Pytest.
Los estados provienen de JUnit; los valores obtenidos se registran después de las aserciones.

**352 aprobadas, 0 fallidas y 3 omitidas; 355 pruebas recogidas.**

Entorno: aplicación FastAPI aislada, TestClient normal con excepciones visibles, fachada, servicios,
dominio, estrategias y calculador reales. Solo se sustituyen los ports externos y repositorios por fakes.
No hay políticas oficiales ni PostgreSQL académico verificados.

## Matriz ejecutada

| Endpoint | Escenario probado | Resultado esperado | Resultado obtenido | Estado | Archivo de prueba asociado |
| --- | --- | --- | --- | --- | --- |
| POST /api/v1/participations/20/attempts | valido | 201; JSON y persistencia coherentes | 201; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-inicio] |
| POST /api/v1/attempts/10/decisions/50 | valido | 201; JSON y persistencia coherentes | 201; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-registro] |
| PUT /api/v1/attempts/10/decisions/50 | valido | 200; JSON y persistencia coherentes | 200; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-modificacion] |
| GET /api/v1/attempts/10/progress | valido | 200; JSON y persistencia coherentes | 200; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-progreso] |
| POST /api/v1/attempts/10/finish | valido | 200; JSON y persistencia coherentes | 200; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | valido | 200; JSON y persistencia coherentes | 200; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-resultado] |
| GET /api/v1/participations/20/absence-result | valido | 200; JSON y persistencia coherentes | 200; esquema, agregado y repositorio verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[valido-ausencia] |
| POST /api/v1/participations/20/attempts | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-inicio] |
| POST /api/v1/attempts/10/decisions/50 | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-registro] |
| PUT /api/v1/attempts/10/decisions/50 | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-modificacion] |
| GET /api/v1/attempts/10/progress | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-progreso] |
| POST /api/v1/attempts/10/finish | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-resultado] |
| GET /api/v1/participations/20/absence-result | invalido | 422 sin cambios confirmados | 422; estado y repositorio intactos | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[invalido-ausencia] |
| POST /api/v1/participations/20/attempts | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-inicio] |
| POST /api/v1/attempts/10/decisions/50 | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-registro] |
| PUT /api/v1/attempts/10/decisions/50 | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-modificacion] |
| GET /api/v1/attempts/10/progress | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-progreso] |
| POST /api/v1/attempts/10/finish | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-resultado] |
| GET /api/v1/participations/20/absence-result | sin_autorizacion | 403; sin datos ni cambios | 403; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[sin_autorizacion-ausencia] |
| POST /api/v1/participations/20/attempts | repeticion | Primera 201; repetida 409; sin duplicados | 201/409; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-inicio] |
| POST /api/v1/attempts/10/decisions/50 | repeticion | Primera 201; repetida 422; sin duplicados | 201/422; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-registro] |
| PUT /api/v1/attempts/10/decisions/50 | repeticion | Primera 200; repetida 200; sin duplicados | 200/200; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-modificacion] |
| GET /api/v1/attempts/10/progress | repeticion | Primera 200; repetida 200; sin duplicados | 200/200; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-progreso] |
| POST /api/v1/attempts/10/finish | repeticion | Primera 200; repetida 200; sin duplicados | 200/200; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | repeticion | Primera 200; repetida 200; sin duplicados | 200/200; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-resultado] |
| GET /api/v1/participations/20/absence-result | repeticion | Primera 200; repetida 200; sin duplicados | 200/200; dominio y contadores verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[repeticion-ausencia] |
| POST /api/v1/participations/20/attempts | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-inicio] |
| POST /api/v1/attempts/10/decisions/50 | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-registro] |
| PUT /api/v1/attempts/10/decisions/50 | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-modificacion] |
| GET /api/v1/attempts/10/progress | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-progreso] |
| POST /api/v1/attempts/10/finish | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-resultado] |
| GET /api/v1/participations/20/absence-result | fallo_identidad | Excepción observable; HTTP 500 sin detalles ni cambios | RuntimeError propagado; 500 genérico; estado intacto | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[fallo_identidad-ausencia] |
| POST /api/v1/participations/20/attempts | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-inicio] |
| POST /api/v1/attempts/10/decisions/50 | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-registro] |
| PUT /api/v1/attempts/10/decisions/50 | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-modificacion] |
| GET /api/v1/attempts/10/progress | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-progreso] |
| POST /api/v1/attempts/10/finish | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-resultado] |
| GET /api/v1/participations/20/absence-result | cerrado_por_defecto | 503; sin datos ni cambios | 503; esquema y estado verificados | PASS | tests/test_http_functional.py::test_matriz_funcional_siete_endpoints[cerrado_por_defecto-ausencia] |
| POST /api/v1/participations/20/attempts | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[inicio] |
| POST /api/v1/attempts/10/decisions/50 | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[registro] |
| PUT /api/v1/attempts/10/decisions/50 | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[modificacion] |
| GET /api/v1/attempts/10/progress | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[progreso] |
| POST /api/v1/attempts/10/finish | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[finalizacion] |
| GET /api/v1/participations/20/attempts/10/result | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[resultado] |
| GET /api/v1/participations/20/absence-result | fallo_dependencia_especifica | Error observable, rollback; recuperación del cierre | Excepción y 500 sin detalles; estado anterior preservado | PASS | tests/test_http_functional.py::test_fallo_dependencia_especifica_no_corrompe_estado[ausencia] |
| GET /api/v1/participations/20/attempts/10/result | flujo_completo | Flujo HTTP con 2 selecciones, cierre único y nota ficticia 2.50 confirmada | Todas las etapas verificadas; dominio real; un resultado definitivo; 2.50 | PASS | tests/test_http_functional.py::test_flujo_funcional_completo_http_con_trazabilidad |
| GET /api/v1/participations/20/attempts/10/result | parcial_y_politica_explicita | Pendiente sin nota; con política de prueba: PARCIAL 3.00 | 200 PENDIENTE → 200 DEFINITIVA PARCIAL 3.00; una inserción | PASS | tests/test_http_functional.py::test_parcial_pendiente_y_politica_explicita_por_http |
| GET /api/v1/participations/20/absence-result | strategy_ausencia_real | Ceros internos sin intento; publicación pendiente por ER | Dos ceros de Strategy real; HTTP PENDIENTE; cero intentos y evaluaciones definitivas | PASS | tests/test_http_functional.py::test_ausencia_usa_strategy_real_sin_intento_y_no_publica_cero_ficticio |

Filas de evidencia HTTP registradas: 52.

## Escenario completo y defectos

`test_flujo_funcional_completo_http_con_trazabilidad` materializa la participación en el fake,
inicia por HTTP, registra dos decisiones, consulta progreso, modifica la primera conservando dos pasos,
finaliza, rechaza edición, repite cierre sin escrituras y obtiene PENDIENTE antes de evaluar.
Después solicita explícitamente la evaluación backend mediante Facade (no existe un endpoint que la dispare),
confirma el cálculo real con política ficticia y lee DEFINITIVA 2.50 por HTTP. No se duplica al reintentar.

Los espías de trazabilidad invocan los métodos originales: no reemplazan el dominio ni el cálculo.
Secuencia registrada:

```text
Facade.iniciar → Servicio.iniciar → Dominio.iniciar → Repositorio.agregar → UoW.commit → Servicio.guardar → Dominio.registrar → Repositorio.guardar → UoW.commit → Servicio.guardar → Dominio.registrar → Repositorio.guardar → UoW.commit → Servicio.progreso → Servicio.guardar → Dominio.modificar → Repositorio.guardar → UoW.commit → Servicio.cierre → Dominio.finalizar → Repositorio.guardar → UoW.commit → Servicio.guardar → Servicio.cierre → Dominio.finalizar → Calculador.real → Resultados.insertar → UoW.commit
```

Defecto reproducido: la captura `except Exception` del router ocultaba RuntimeError al TestClient normal.
La prueba nueva falló inicialmente con `DID NOT RAISE RuntimeError`. Se retiró esa captura;
el error inesperado se propaga y ASGI sin debug devuelve HTTP 500 genérico, sin credenciales ni datos académicos.
Se conserva la prueba anterior de privacidad usando `raise_server_exceptions=False` solo para observar ese límite HTTP.
Cambio explícito del contrato provisional: el 500 inesperado deja de prometer el JSON ERROR_INTERNO;
los errores esperados mantienen sus códigos JSON. No se borraron tests ni se cambiaron reglas académicas.

## Comprobaciones adicionales y bloqueos

| Alcance | Resultado / limitación | Estado | Evidencia |
| --- | --- | --- | --- |
| API anterior, dominio y Application | Se incluyen sus pruebas en esta ejecución | PASS | tests/test_api.py y demás suites |
| Infraestructura sin BD | Compilación SQL, codecs y ciclo Session; no prueba transacciones de filas | PASS | tests/test_sqlalchemy_queries.py, tests/test_sqlalchemy_uow.py, tests/test_persistence_codecs.py |
| PostgreSQL real | PostgreSQL real no habilitado: falta SPS_TEST_POSTGRESQL=1 y configuración de conexión. | BLOCKED | test_postgresql_conexion_y_commit_sin_ddl |
| PostgreSQL real | PostgreSQL real no habilitado: falta SPS_TEST_POSTGRESQL=1 y configuración de conexión. | BLOCKED | test_postgresql_recuperacion_despues_de_error |
| PostgreSQL real | PostgreSQL real no habilitado: falta SPS_TEST_POSTGRESQL=1 y configuración de conexión. | BLOCKED | test_postgresql_decimal_y_timestamp_del_driver |
| Habilitación integrada de los siete endpoints | Router no registrado en main.py; identidad y adaptadores reales pendientes | BLOCKED | tests/test_api.py::test_router_no_registrado_en_aplicacion_principal |
| Resultado definitivo de ausencia | Se prueban ceros internos sin intento y HTTP PENDIENTE; falta mapeo ER aprobado | BLOCKED | test_ausencia_usa_strategy_real_sin_intento_y_no_publica_cero_ficticio |

La repetición de GET no calcula ni crea resultados. El test parcial pasa de PENDIENTE a PARCIAL 3.00
solo después de habilitar una política de fixture explícita. La ausencia permanece pendiente; no se publica un cero ficticio.

## Dependencias para la integración real

- Alejandro: identidad verificada, consentimiento, propiedad y permisos reales.
- Juan Andrés: contenido y recorrido autorizados, rúbrica histórica y mapeo académico a niveles.
- Maicol: convocatorias/participaciones, ventanas, duración histórica y confirmación de ausencias.
- Equipo: DDL aprobado, escritores SQL, unicidad/concurrencia PostgreSQL, precisión y políticas de evaluación/consolidación.

No se modificó main.py, no se crearon tablas/migraciones ni se conectó una autenticación ficticia.
No se verifican persistencia académica ni concurrencia real PostgreSQL. No se utiliza SQLite como sustituto.

## Repetir la ejecución

Desde la raíz del repositorio oficial, con el extra dev instalado:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests backend/tests -c backend/pyproject.toml -q -rs --junitxml=backend/app/modules/participation/tests/artifacts/qa.xml -o junit_family=xunit1
.\.venv\Scripts\python.exe -m app.modules.participation.tests.generate_qa_report --junit backend/app/modules/participation/tests/artifacts/qa.xml --output backend/app/modules/participation/QA_ENDPOINTS.md
```

`tests/artifacts/` está ignorado localmente. El Markdown es evidencia regenerable para revisión,
no una certificación de despliegue ni de políticas oficiales. No habilitar PostgreSQL real con la bandera
SPS_TEST_POSTGRESQL hasta configurar deliberadamente la conexión compartida al entorno de prueba.

## Recomendación de Git

Revisar el diff y versionar como QA del módulo en martin si la ejecución no tiene fallos.
Conservar los bloqueos de integración. El push a martin es apropiado tras revisión y pruebas en el entorno del equipo,
sin habilitar producción. Esta ejecución no hace commit, push ni abre Pull Request.
Los archivos pendientes del quinto incremento ya existían al iniciar esta tarea; revisar el alcance del commit.
