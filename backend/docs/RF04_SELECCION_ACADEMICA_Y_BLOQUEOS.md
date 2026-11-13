# RF-04 — selección académica y límites de la asociación

## Checkpoint previo

RF-03 protegido mediante c2cad50c444175de04fb803badeaf91f3befdf0f, `fix(identity): revalidar administracion en transaccion`. Se verificaron las 48 rutas del MANIFIESTO_RF03.json, sus SHA-256 y el índice. Los siete cambios anteriores quedaron fuera. Los cuatro diagnósticos RF-03 corregidos y sus resultados anteriores se conservaron; no se presentan como una ejecución nueva. No se modificó el respaldo privado, stash, .env ni otra rama.

## Contrato académico y criterios

Fuente: `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, p.4, RF-04: «Al agendar un caso, el docente asocia el nombre del espacio académico y uno o varios estudiantes autorizados». RN-05, p.7, exige docente, caso publicado, espacio, horario, tiempo máximo y lista de estudiantes autorizados. La fuente y sus páginas se preservan con SHA-256 en `evidencias/rf04_fase4_20261109/FUENTE_RF04.json`.

No se deduce de ese enunciado un permiso para administrar globalmente grupos, crear matrículas, concederse espacios o convertir identificadores. Las asociaciones explícitas docente/espacio ya fueron autorizadas y persisten en docente_espacio_academico. Los grupos y matrículas del ER tienen que existir previamente.

| Criterio | Comportamiento existente o acreditable | Límite |
|---|---|---|
| Actor | JWT real; cuenta activa y rol DOCENTE consultados en Identity; vínculo SCHEDULING persistente | No se amplían privilegios de otros roles |
| Espacio | FK y grant explícito docente INTEGER / espacio UUID | Crear el espacio no concede su uso |
| Caso | Versión PUBLICADO exacta, autoría CASES, sin equiparar UUID de módulos | No se sustituye por la versión más reciente |
| Estudiantes | Convocatoria individual persistida y validación de grupo propio/matrícula activa | Requiere asignación académica previa |
| Grupo | grupo_academico.id_profesor y grupo_estudiante INTEGER | No existe relación grupo/espacio que pueda inventarse |
| Vigencia | Cuenta y matrícula tienen activo; sesión tiene estados | Grupo y espacio no tienen activo; no se simula ese atributo |
| Asociación completa al agendar | Sesión y convocatorias tienen endpoints reales | No hay composición productiva que cree asignacion_caso con políticas aprobadas |

## Brecha demostrada y corrección mínima

Antes del cambio, GET /scheduling/espacios devolvía TODOS los espacios a cualquier docente con vínculo académico. Tres escenarios fallaron en PostgreSQL 17 sobre app.main: exposición del espacio de otro docente, recursos sin concesión y consulta concurrente que incluía recursos fuera de ámbito. Se conservan los fallos en diagnostico_antes/; no se cambian sus resultados esperados.

Se reutiliza el endpoint y la Session existentes. listar_espacios une espacio_academico con docente_espacio_academico y filtra por el INTEGER de Identity del docente autenticado. El UUID de Scheduling continúa resolviéndose por su dependencia real; no se usa como INTEGER ni como prueba de propiedad. La PK compuesta de grants evita duplicación por join. Orden determinista por nombre e id, formato id/nombre conservado, sin información estudiantil.

La consulta usa no_autoflush, no hace escrituras ni commits. Los errores SQL se traducen a 503 sin exponer detalles. Son controles de aplicación; no se afirma que se haya añadido una transacción PostgreSQL READ ONLY ni una nueva restricción de autorización en la base.

No hay ORM, migración, tabla, servicio ni ruta nuevos. No cambian las reglas de inicio, inmutabilidad, consentimiento, repetición ni evaluación.

## Contrato HTTP

GET /scheduling/espacios (app.main): JWT y rol docente vigentes + identidad académica. 200 devuelve exclusivamente los espacios con concesión explícita, o [] si no existen. 401 sin JWT válido/cuenta inactiva; 403 por rol o vínculo no autorizado; 503 por integración/configuración o consulta SQL no disponible. No se expone nombre de docentes, estudiantes, hashes ni permisos de otros usuarios.

POST /scheduling/sesiones y POST/GET /scheduling/sesiones/{id}/convocatorias se reutilizan sin modificaciones. Programar una sesión NO crea un grupo, una matrícula ni una asignación. Las convocatorias siguen rechazando el acceso cuando falta su vínculo académico persistente.

## Bloqueo que permanece

RF-04 sigue BLOQUEADO para aceptación integral y PARCIAL en la matriz de implementación. asignacion_caso exige fecha_limite_ingreso, intentos_base y estado, además de grupo, caso y versión/sesión. La confirmación funcional vigente declara pendientes las políticas productivas de provisión/inicio/repetición. No se copia el límite temporal o cupo de una fixture ni se considera el DEFAULT del esquema una aprobación académica. La sala de espera tampoco define por sí sola ese timestamp obligatorio.

Para desbloquear: concretar el contrato autorizado de creación de asignación (quién, grupo propio, campos temporales/estado/cupo y su relación con admisión), o aprobar la adaptación mínima que permita expresar el contrato sin valores ficticios. Definir quién mantiene los grants y matrículas existentes si se exige ese mantenimiento desde la API; RF-04 no concede autovinculación. No se necesita inventar una entidad grupo/espacio por semejanza de nombres.

La demostración Newman positiva crea sesión y convocatorias con main/JWT/SQL reales, pero la asignación, grants, grupos y matrículas se preparan administrativamente SOLO LAB. Esto no acredita una asociación completa creada exclusivamente por API. En concreto, la sesión nueva `rf_sesion` y la sesión `rf_sesion_convocatoria` sobre la que se convocan estudiantes son distintas: esta última se prepara previamente con su asignación en LAB. No se presenta esa secuencia como un recorrido integral de asociación sobre la sesión recién creada.

## Pruebas y evidencia

Evidencia de esta ejecución: `evidencias/rf04_fase4_20261109/`. Cada ejecución guarda consola.log, JUnit y resultado.json; los runners deshabilitan .env y URLs heredadas, usan PostgreSQL 17 nuevo y eliminan exclusivamente su laboratorio al terminar. No se suman focal, relacionada, general y Newman.

Resultados finales, ejecutados en esta fase (no sumar suites solapadas):

- Focal final: **18 aprobadas**, cero omisiones/fallos/errores: 11 unitarias existentes y siete integraciones nuevas.
- Relacionada final: **139 aprobadas**, cero omisiones/fallos/errores.
- General final **nueva completa**: **2525 aprobadas, 38 omitidas, cero fallos/errores**; 2563 casos únicos, 123 archivos, cuatro particiones disjuntas y huellas app/tests estables. Se repitieron las cuatro particiones tras corregir el fixture, no se concilió solamente el resultado anterior.
- Advertencia conocida Starlette/httpx conservada (un tipo, repetido en distintos procesos). Las 38 omisiones por conexiones PostgreSQL externas no configuradas se conservan en JUnit/consola; no equivalen a aprobaciones. La aceptación específica sí utilizó PostgreSQL17 desechable.
- Newman nuevo de las 27 carpetas: **556 HTTP / 2118 aserciones**, cero fallos técnicos; 16 APROBADOS y 11 BLOQUEADOS. RF04: **16 HTTP / 53 aserciones**, BLOQUEADO integralmente. Los requests/scripts de los otros 26 RF y todos sus veredictos permanecen intactos.
- Diagnóstico antes del filtro: tres fallos y tres aprobadas. Primera general: 2523 aprobadas, 38 omitidas y dos fallos unitarios (401 por fixture sin contexto Identity). Se conservan los logs/JUnit originales. El fixture se adapta al contexto explícito y no_autoflush; se añaden aserciones del filtro y ausencia de commit/flush. No se relajan los HTTP esperados.
- Los cuatro diagnósticos corregidos de RF03 volvieron a ejecutarse y aprobaron en la general final; referencias nominales en RF03_REVERIFICACION.json.

Evidencias: focal_final/, relacionada_final/, general_final_g0..3/, general_resultado.json, junit_general.xml y newman_27/. Los comandos completos, fechas, HEAD y huellas del código local están en ejecucion.json. La versión probada es c2cad50 más cambios locales RF04, no se atribuyen esos cambios a un commit inexistente.


Comandos desde la raíz del proyecto (usar destinos nuevos para repetir):

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf04_fase4_20261109/run.py --modo relacionada --evidencias evidencias/rf04_fase4_20261109/relacionada_final
# General: --modo g0, g1, g2, g3; destino general_final_gN; luego agrupar_general.py.
$runtime = Get-Content evidencias/postman_desktop_20261108/newman_runtime.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf todos --newman (Join-Path $runtime.ruta 'node_modules/newman') --evidencias evidencias/rf04_fase4_20261109/newman_27
```

## Sustentación y continuidad

Preparar SOLO la carpeta RF-04 con preparar-27rf.ps1. Ejecutar sus solicitudes en orden. Capturar selección autorizada, exclusión del espacio ajeno, rechazo 401, sesión 201 con versión exacta y convocatorias persistidas. Mostrar URL, HTTP y Test Results, ocultando Authorization y cuerpos/códigos de login. Las capturas manuales no están fabricadas ni se afirma ejecución en Postman Desktop: la ejecución automatizada es Newman.

Siguiente incremento: cerrar primero el contrato de asignación académica requerido por RF-04. En paralelo documental, resolver para RF-03 si los permisos son globales por rol o individuales. No agregar una API de permisos/grants ni promover políticas LAB antes de esa precisión.

## Archivos y estado de entrega

Único archivo productivo: app/modules/scheduling/api/router.py, función listar_espacios. Prueba nueva: tests/integration/test_authorized_academic_spaces.py; adaptación del fixture y aserciones de tests/unit/scheduling/test_api_endpoints.py. Documentación: este informe, matriz global, inventario/OpenAPI, construir.py, informar.py y artefactos reproducibles de cobertura_27rf (colección, contratos, matrices, resultados y fichas nominales actualizadas). informar.py puede enlazar también el JUnit general, deduplicando las variantes por identificador; no suma sus conteos a Newman.

MANIFIESTO_RF04.json contiene las rutas, tamaños y SHA-256; ESTADO_FINAL.json registra el árbol de trabajo y la preservación. RF04 permanece sin commit. No se publica nada ni se habilita ningún otro requisito.
