# Participation fase 1 — composición principal condicionada

## Contratos y decisión de alcance

RF-12 original: «Cada participación guarda inicio, fin, calificación final y retroalimentación por pregunta».
RF-23: «Al iniciar la participación, el sistema inicia el contador, aplica el límite máximo y conserva las respuestas para evaluación».
RF-25: «El sistema impide repetir una participación registrada, salvo autorización del docente creador del caso; tampoco permite participar en una sesión finalizada».
Fuente: PDF central, pp. 4–5, y REQUISITOS_FUENTE.json de la cobertura 27RF.

El equipo confirmó durante este incremento que **no hay evidencia oficial verificable de aprobación del consentimiento ni políticas productivas definitivas de inicio, provisión y repetición**. Esta respuesta prevalece sobre la intención de cerrar los RF: no se inventan decisiones para cumplir la meta.

Se reutiliza la infraestructura versionada existente: documento original/texto/huellas separadas, vigencia y selector por asignación; aceptación explícita con FK histórica, integridad SQL, protección de revocación durante ejecución; coordinador convocatoria→P→I con una UoW y locks. No se crean tablas, migraciones, repositorios o motores paralelos.

## Implementación independiente

Se registran cuatro operaciones en app.main, a través de las factorías existentes:

| Método | Ruta | Contrato |
|---|---|---|
| GET | /api/v1/identity/convocatorias/{convocatoria_id}/asignaciones/{id_asignacion}/consentimiento | Documento seleccionado por el servidor; no cliente/última etiqueta |
| GET | misma base + /aceptacion | Evidencia propia actual o aceptado=false |
| POST | misma base + /aceptacion | id_version_documento INTEGER, referencia, huella, acepta=true; idempotente 200 |
| POST | /api/v1/convocatorias/{convocatoria_id}/intentos | id_asignacion, codigo_acceso, id_consentimiento e id_permiso_extra opcional; 201 condicionado |

No se registra POST /convocatorias/{id}/participacion: la provisión independiente sigue en su aplicación opt-in. No hay API de publicación/aprobación documental ni revocación. No se monta el router general de Participation ni se habilita PUT de respuestas.

**Registrado no significa habilitado productivamente.** Las dependencias principales requieren tres puertos del servidor: aprobación documental, política de vinculación y política de inicio. Los proveedores productivos predeterminados rechazan; no retornan valores de LAB. None/objetos sin autorizar también rechazan. No hay flags HTTP ni variables .env de habilitación.

La fuente SQL conserva sus garantías criptográficas y de vigencia. En composición principal la política de aprobación debe autorizar el documento exacto dentro de la lectura transaccional, incluyendo la fuente usada por el inicio. Un hash/metadato/aceptación sintéticos no superan la ausencia del proveedor institucional. Los consumidores internos y las apps explícitas de LAB anteriores conservan compatibilidad; no representan fuentes oficiales.

Se exige JWT real, cuenta/rol actuales y relaciones persistentes. El coordinador ya revalida titularidad, matrícula, convocatoria activa/admitida, sesión EN_CURSO, asignación, UUID publicado exacto, rúbrica, consentimiento y permiso en la misma UoW. Se reutilizan advisory/row locks y el consumo por FK del permiso; no se invoca un start paralelo ni se concede ingreso por alcanzar la fecha programada.

La duración se captura del servidor y se conserva en el intento. GET progreso puede proyectar VENCIDO sin escribir; finish confirma el cierre. No se calculan ni publican notas automáticamente. Las selecciones permanecen inmutables.

## Errores y protección histórica

401: JWT ausente/inválido; 403: rol/ámbito/condición académica denegados; 409: intento activo/conflicto; 422: forma inválida. 503 por aprobación/políticas/configuración ausentes no constituye cumplimiento del RF. Las respuestas controladas conservan no-store.

Un SQL inesperado como 22012 (división por cero) conserva el **500** del contrato existente de RutaParticipacion y test_lab_student_journey; no se reclasifica como 503 para ocultarlo. La aceptación prueba rollback de P/I, respuesta sin SQL ni credenciales y reintento exitoso. Conflictos PostgreSQL conocidos conservan el mapeo existente a 409.

La primera focal nueva tuvo tres fallos de preparación: conteo no acotado a estudiante en un módulo que conserva historia, observador SQL instalado en otro Engine y docente seleccionado de otro escenario. La segunda reprodujo 500 donde la prueba había supuesto 503 sin respaldo contractual. Se conservaron ambas ejecuciones; las correcciones no cambian reglas académicas ni alteran el backend para aceptar operaciones inválidas.

## Demostración Postman

Desde la raíz del repositorio:

```powershell
.\preparar-participation-fase1.ps1
```

Por defecto prepara **CONTROL**, con documento/aceptación sintéticos auténticamente persistidos como precondición LAB. Importar los dos JSON temporales impresos, seleccionar su Environment único y ejecutar la carpeta CONTROL. Login 200 y tres bloqueos 503. Es prueba de cierre seguro, nunca aprobación funcional.

Para los recorridos positivos EXCLUSIVAMENTE de laboratorio:

```powershell
.\preparar-participation-fase1.ps1 -RF RF-12
.\preparar-participation-fase1.ps1 -RF RF-23
.\preparar-participation-fase1.ps1 -RF RF-25
```

Una ejecución a la vez; q cierra solo sus recursos. Importar y seleccionar el Environment nuevo en cada cambio. La colección tiene carpetas RF-12, RF-23, RF-25 y CONTROL; no ejecutar todas con un único entorno. No copiar UUID, credenciales o tokens. Los valores temporales son sintéticos y secretos: no exportarlos/sincronizarlos ni capturarlos en pantalla.

Las rutas positivas son app.main real con puertos de política **LAB inyectados por el preparador**, no aprobación productiva. Los proveedores se importan de tests solo en el script de laboratorio; nunca en app.main ni en código productivo. La preparación siempre crea PostgreSQL17 nuevo, no admite una URL externa y desactiva .env dentro de su proceso.

RF-12 empieza por F1-RF-12-01 (login administrador), sigue en orden: documento/aceptación main, inicio, respuesta inmutable, progreso y cierre idempotente. RF-23 usa el mismo flujo hasta la primera selección: antes de «RELOJ LAB» escribir t en la consola. Solo se adelanta el reloj inyectado después del límite histórico; no se modifican timestamps SQL ni se afirma esperar 30 minutos reales. Luego progreso VENCIDO y finish persisten el vencimiento sin notas. RF-25 cierra el primero, el creador autoriza un permiso nativo, el segundo inicia y el permiso no puede reutilizarse tras cierre. Las negativas esperadas son verdes sin significar habilitación productiva.

i abre la carpeta temporal; q detiene servidores/contenedor propio y elimina los archivos de importación. Los entornos ya importados en Postman se retiran manualmente; importar otro JSON no selecciona automáticamente el nuevo. Mostrar nombre, URL, HTTP y Test Results; ocultar Authorization y cuerpos de login/código. Capturas manuales pendientes: no se usó la interfaz gráfica.

El ejecutor preparar.py --rf ... --ejecutar --newman <modulo> --evidencias <carpeta nueva> ejecuta los pm.test mediante Newman por solicitud independiente, automatiza el avance LAB de RF-23 y verifica desde otra Session SQL duración, estados, referencias, ausencia de notas y limpieza. JUnit y JSON son nominales; no exporta Environment ni tokens.

## Información indispensable para desbloquear producción

1. Documento institucional definitivo: contenido original y representación aceptada, identificador/referencia/versionado, vigencia/ámbito y autoridad/evidencia auténtica de aprobación. El borrador NO APROBADO no sirve.
2. Proceso autorizado para verificar aprobación, publicar y seleccionar la versión por asignación; quién es responsable y cómo se acredita. Un ADMINISTRADOR técnico no obtiene automáticamente autoridad institucional.
3. Política definitiva de provisión/inicio: momento de crear P, su estado inicial, cupos base y relación exacta entre admisión, apertura/cierre y límite de ingreso. No se eligen «pendiente», un cupo o una tolerancia de LAB por defecto.
4. Repetición: condiciones/cantidad/ámbito de la autorización, reglas sobre misma evaluación y caso diferente y su compatibilidad con ventanas de sesión. La infraestructura de un uso y creador persistente no aprueba todas esas políticas.
5. Proveedores de esos puertos revisados y desplegados sin configuraciones sintéticas; nueva aceptación de los recorridos sin sustituciones de política LAB.

RF-12, RF-23 y RF-25 continúan **BLOQUEADOS para aprobación integral**. Los 16 RF anteriores no se reclasifican por estos cambios. Sus resultados de regresión y los generales se adjuntarán con fecha, HEAD base y huellas locales; no se reutilizan cifras históricas como nuevas ejecuciones.


## Trazabilidad individual de esta composición

Todos los métodos siguientes pertenecen a `backend/tests/integration/test_main_start_composition.py` y se ejecutan contra app.main con JWT real y PostgreSQL17 nuevo. Las políticas positivas son explícitamente LAB.

| RF / control | Método pytest | Aserción principal |
|---|---|---|
| RF-12 / bloqueo | test_default_proveedores_cerrados_sin_politicas_ni_doc_aprobado | Las cuatro operaciones devuelven 503/no-store; sin C/P/I nuevos |
| Identidad | test_auth_precede_politicas | Anónimo y token inválido 401; docente 403 |
| RF-12 / recorrido | test_recorrido_main_aceptacion_inicio_decisiones_cierre | Aceptación explícita/idempotente, inicio 201, duplicado 409, decisiones inmutables, cierre sin resultados |
| Puertos obligatorios | test_un_puerto_ausente_impide_insertar | Cada uno de los tres proveedores ausentes cierra sin INSERT |
| Aprobación | test_aprobacion_invalida_no_confirma_evidencia | Un retorno True no sustituye autorización documental |
| Ámbito | test_autorizacion_revalidada_en_main_antes_de_insertar | Matrícula inactiva, convocatoria retirada y aceptación ajena rechazan sin P/I |
| Transacciones | test_inicio_concurrente_y_rollback_real | SQL fallido revierte P/I; dos inicios concurrentes dan 201/409 con un único intento |
| RF-25 | test_repeticion_permiso_real_consumido_una_vez | Creador real autoriza; consumo concurrente único; permiso consumido no se reutiliza |
| RF-23 | test_vencimiento_y_respuestas_conservadas_main | Duración histórica, respuesta conservada, proyección VENCIDO y cierre persistido sin nota |

La fuente documental/versionada existente y su inmutabilidad, publicación/selector, aceptación concurrente, revocación durante ejecución y rollback se conservan en `test_consent_version_persistence.py`. No se reconstruyen. Los puertos sin valores implícitos y la zona explícita se acreditan en `tests/unit/identity/test_consent_composition.py`.

La aceptación focal final consta de **59 aprobadas, cero omitidas, fallidas o errores**: `evidencias/participation_fase1_20261109T215053Z/focal_final/{junit.xml,consola.log,resultado.json,ejecucion.json}`. La advertencia Starlette/httpx se conserva. Las primeras dos ejecuciones diagnósticas permanecen en focal_1 y focal_2; no se presentan como verdes.

Newman: **79 solicitudes / 291 pm.test**, todas aprobadas: CONTROL 4/12; RF-12 25/97; RF-23 18/61; RF-25 32/121. Evidencia JSON/JUnit y lectura independiente SQL en `newman_1/`. La limpieza de cada laboratorio consta en `resultado.json`. No se suman estos números con pytest, ni con la regresión maestra que reutiliza operaciones.


## Regresión y contratos históricos sustituidos

La regresión relacionada finalizó con **763 aprobadas, cero omitidas/fallidas/errores**, y la advertencia conocida Starlette/httpx. No se suma con la aceptación focal de 59. Evidencia: `pytest_relacionada/` bajo la carpeta de esta ejecución.

La primera general se ejecutó en cuatro particiones disjuntas que cubren los 118 archivos de pruebas: **2492 aprobadas, 38 omitidas, dos fallidas y cero errores**. Los JUnit y logs originales se conservan en `pytest_g0` a `pytest_g3`. Las omisiones corresponden a opt-in/conexiones externas históricas no habilitadas; no se atribuyen aprobaciones a ellas. Las pruebas nuevas usan PostgreSQL17 propio.

Los dos fallos fueron aserciones históricas de ausencia de rutas, sustituidas por el contrato nuevo de composición cerrada:

- `test_main_current_scenario.py::test_principal_conserva_version_archivada_y_no_expone_otras_operaciones` pasa a `test_principal_conserva_version_archivada_y_bloquea_inicio_sin_politicas`: conserva el grafo histórico y las cuatro operaciones previas, añade únicamente el inicio al inventario permitido, exige 503/no-store sin políticas y conserva 404 para el router general de resultados que sigue ausente.
- `test_main_early_ingress.py::test_rechazo_sin_habilitar_no_inicia_y_main_no_expone_inicio` pasa a `test_rechazo_sin_habilitar_no_inicia_y_main_bloquea_inicio_sin_politicas`: conserva 403 del ingreso y del inicio LAB sin habilitación, cero P/I, y exige 503/no-store en main en lugar de la antigua ausencia 404.

No se cambia un resultado esperado para encubrir un fallo funcional: la solicitud de integrar la composición en main sustituye expresamente el contrato «ruta inexistente» por «ruta registrada sin permisos implícitos». No se tocó código productivo para resolver estos dos fallos, no se borraron casos y no se introdujeron skips/xfail. Se ejecutan de nuevo ambos archivos completos en `contratos_main_actualizados/`. La conciliación general, cuando esta reverificación termine, sustituye todos los casos de esos archivos, conserva las demás particiones y verifica fuentes app idénticas, cobertura y ausencia de duplicados. No equivale a una segunda ejecución general completa.

La regresión maestra Newman se volvió a ejecutar íntegramente: **545 solicitudes, 2080 aserciones aprobadas; 16 RF APROBADOS, 11 BLOQUEADOS, cero FALLIDOS/NO EJECUTADOS**. Evidencia nueva: `regresion_postman_27/`. Los RF previamente aprobados son 01,02,05,06,07,08,09,11,15,16,17,18,19,22,26,27. No hay nuevos RF aprobados por esta composición. Las solicitudes y scripts actuales coinciden con el snapshot ejecutado; únicamente se precisó la descripción de RF-12 y sus referencias pytest. La equivalencia se registra en `equivalencia_coleccion.json`.

Las precondiciones académicas del laboratorio se preparan mediante las fixtures existentes: no se presentan como un flujo administrativo productivo ni como aprobación documental. El preparador PowerShell requiere terminal interactiva: la verificación con `q` terminó con código 0 y limpieza; se conserva también el intento inicial de automatización por pipeline que terminó en EOF. No se atribuye ejecución a Postman Desktop ni se generan capturas.


## Resultado final y preservación

La reverificación completa de los dos archivos afectados terminó con **41 aprobadas, cero omisiones/fallos/errores**. La general conciliada tiene **2494 aprobadas y 38 omitidas, cero fallos/errores pendientes**, conservando los dos fallos iniciales y sustituyendo íntegramente sus archivos por la reverificación. `general_resultado.json` y `general_conciliada.xml` prueban cobertura de 118 archivos, ausencia de casos duplicados y fuentes app idénticas en todas las ejecuciones; no se afirma una segunda ejecución general completa. La única categoría de advertencia conocida es Starlette/httpx.

No se suman 59 focalizadas, 763 relacionadas, 41 reverificadas ni las aserciones Newman. No se incluyen bases, entornos privados, credenciales ni tokens en los artefactos importables. No se cambian ORM, migraciones, Strategy, fórmulas, resultados ni tablas.

Rama aislada: `codex/participation-inicio-main-20261109`, HEAD base `0fa76b04126a700125a252dc4291d3bf74a04542`, sin commits, push, merge ni worktrees. Los cambios anteriores se preservan. El inventario exacto y las huellas del incremento están en `evidencias/participation_fase1_20261109T215053Z/MANIFIESTO_INCREMENTO.json`; `ESTADO_FINAL.json` documenta índice, stash, .env, referencias y recursos. El diff global conserva dos advertencias de espacios finales preexistentes en constructor_caso.py, que no se corrigen por ser trabajo ajeno.

Siguiente paso necesario del equipo: entregar el documento oficial vigente con evidencia verificable de aprobación y cerrar las políticas de provisión/inicio/repetición. Solo entonces se podrán implementar sus proveedores productivos y repetir aceptación sin sustituciones LAB. Este incremento termina con los mecanismos técnicos acreditados y **RF-12/RF-23/RF-25 aún BLOQUEADOS**.
