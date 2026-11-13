# Fase 7 — cierre de la consulta estudiantil RF-14

10 de noviembre de 2026, America/Bogota. **RF-14 APROBADO en el alcance funcional vigente de consulta de resultados existentes.** Aceptación sobre app.main/PostgreSQL17 de laboratorio; no acredita despliegue permanente, aprobación institucional de las fórmulas RF13 ni el inicio productivo RF12/23/25.

## Preservación y checkpoint RF13

Estado inicial: rama codex/participation-inicio-main-20261109, HEAD 8e1e8a67f6e4ba387b9d0650059e6fe654c704d9, índice vacío. Se verificaron las cuatro rutas/SHA-256 de MANIFIESTO_FASE6.json, los ocho cambios previos y los archivos no rastreados.

Checkpoint local **48b0bfb61839684e5b3e9fbfdfc88b0bcd204972**, `docs(evaluation): preservar auditoria RF13 y compatibilidad DTO`, contiene exclusivamente RF13_AUDITORIA_Y_DTO_PROGRAMACION_20261110.md, AUDITORIA_COBERTURA_BACKEND_20261105.md, cobertura_27rf/BRECHAS_RF.md y RF-13.md. Sin código productivo, .env, evidencias ni cambios anteriores preparados. Respaldo privado de esos documentos y bundle verificado: C:/SPS/respaldos/nuclear_rf13_20261110T233054Z. Los respaldos previos se conservan.

RF13 continúa BLOQUEADO integralmente: la consulta RF14 no aprueba otras rúbricas ni cambia UC05. No se modificó ProgramarSesionRequest ni se activó extra='forbid'. No hubo push, pull, merge, checkout, clean, nuevas ramas/worktrees ni operaciones sobre bases permanentes.

## Contrato académico y decisiones aplicables

Fuente original: _referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf, p.4, RF14: «Al terminar, el sistema presenta aciertos, errores, sus explicaciones y nota final; no anticipa justificaciones durante la resolución». UC05, p.11, sitúa la consulta después del cierre/evaluación; RN17 conserva rúbrica/versionado y RN18 el ámbito. Páginas y SHA-256: evidencias/rf14_fase7_20261110/FUENTE_ACADEMICA.json.

La confirmación funcional posterior del usuario como responsable del equipo (8/11), «Provisional configurable, sin correctas durante sesión activa», está recogida en EVALUATION_CICLO_ACADEMICO.md. Es la fuente de la configuración docente y de la prohibición de correcciones durante sesión activa; no se inventa una fecha de publicación. No se atribuye una aprobación institucional de fórmulas a esa confirmación.

El actor de esta consulta es el **estudiante titular**. El docente autoriza visibilidad provisional o una publicación mediante operaciones separadas, con rol/ámbito SQL. RF14 no exige publicar una nota al cerrar ni que el GET calcule una nota faltante. El original exige identificar acierto/error de la selección y su explicación: se comprueban es_correcta y justificacion de cada selección real. No se convierte una propuesta más amplia de revelar todas las alternativas correctas, niveles o ponderaciones en obligación académica aprobada.

No se amplía el recorrido soportado ni se exige resolver RF10 para leer una participación ya válida: varias preguntas/ciclos/revisitas conservan sus límites propios. Tampoco se exige implementar RF04 o el inicio desde convocatoria para demostrar este consumidor con datos académicos preexistentes. Las fixtures de esas dependencias están declaradas como preparación LAB.

## Estados que no son equivalentes

| Estado | Significado |
|---|---|
| Calculado | El motor obtuvo un valor; puede no existir todavía una escritura confirmada |
| Persistido | Hay una cabecera canónica y detalle verificable de RF13 |
| Consultable provisionalmente | Titular autorizado, configuración docente habilitada, todos sus intentos cerrados y resultados técnicos disponibles; oficial=false |
| Publicado oficialmente | POST docente con revisión íntegra autorizó un snapshot versionado; GET devuelve solo la fila propia de la última publicación. Las publicaciones de prueba son datos sintéticos, no notas universitarias reales |

Sin publicación y sin habilitación provisional, 404. Si hay un intento abierto, 409 cuando la consulta provisional está habilitada. Si el resultado aún no existe, 404 sin calcular. Una ausencia confirmada sin publicación no se inventa como intento o nota provisional: después de publicación expresa se consulta AUSENTE/0.00 con participación/intento ausentes. Los vencidos y voluntarios parciales muestran selecciones reales y el resultado persistido, sin crear feedback de preguntas pendientes.

## Brecha funcional demostrada y corrección mínima

Un intento cerrado, autorizado, con visibilidad provisional habilitada pero sin resultado devolvía **503**. RepositorioResultadosTecnicosSQLAlchemy.obtener_tecnico lanzaba RecursoNoDisponible de Participation; CicloAcademicoSQL.estudiante lo capturaba como ErrorAplicacionParticipacion genérico y lo transformaba en IntegracionPendiente.

La corrección en infrastructure/academic_cycle.py importa esa excepción con alias y la traduce específicamente a RecursoNoDisponible de Identity (**404**), igual que la ausencia del resultado en la lectura técnica docente. La captura queda antes del manejo genérico de configuración/integridad, que conserva 503. No se suprime una excepción SQL, no se crea resultado, no se devuelve cero ni se altera visibilidad o publicación.

**Único cambio productivo: cinco líneas en academic_cycle.py.** No hay otra ruta, servicio, repositorio, DTO, tabla ni migración. El cálculo, puntajes, versiones históricas, fin de intento y reglas de publicación existentes permanecen intactos.

## Componentes y ruta existentes

GET **/scheduling/convocatorias/{convocatoria_id}/resultado**, registrado en main → Scheduling → academic_results.router. Dependencia estudiantil real de Identity y CicloAcademicoSQL.estudiante. Relación servidor: JWT/cuenta activa → identidad Scheduling → convocatoria propia/claim → sesión → participación/intentos → resultado o snapshot propio.

La Session lectora usa REPEATABLE READ / READ ONLY, no_autoflush y cierre con rollback. No hay commit, publicación o nuevo cálculo persistido. El repositorio puede reproducir la procedencia para verificar integridad sin recalificar ni escribir. Para feedback se reutiliza Cases.consultar_explicaciones_seleccionadas con la versión exacta y las selecciones inmutables, no la última edición.

La fuente oficial es Pub/ResultadoParticipacionModel verificada por hash; la fuente provisional son resultados TECNICO de la participación. LABORATORIO no se convierte en una nota consultable. No se expone al estudiante la revisión completa de cohorte, documentos del motor/política, credenciales, alternativas no seleccionadas ni datos de otro alumno. El ámbito/visibilidad son controles de aplicación; PostgreSQL impone además READ ONLY e integridad histórica, no una ACL académica autónoma para SQL arbitrario.

Contrato HTTP, unión de DTO, nulabilidad, campos visibles, recarga y errores para Angular: **RF14_CONTRATO_ANGULAR.md**. La ruta actual devuelve diccionarios sin response_model explícito; no se afirma que un cliente generado de OpenAPI ya conozca toda esa unión. No se ejecutó navegador/Angular.

## Criterios de aceptación y evidencia

| Criterio | Evidencia concreta | Veredicto |
|---|---|---|
| Titular JWT/cuenta/convocatoria | Nuevos tests privados: anónimo, token inválido, docente/admin, estudiante ajeno y cuenta inactiva; login real | APROBADO; ningún error contiene nota/detalle/explicaciones |
| Aciertos/errores y explicaciones | Dos recorridos reales con 100.00 y 0.00; comparación exacta de IDs, texto, flag y justificación contra las selecciones históricas | APROBADO |
| Versión histórica | Se crea una edición posterior; GET conserva la versión y explicaciones del intento original | APROBADO |
| Vencido e incompleto voluntario | Dos parciales con 33.33, una respuesta y un feedback; no se añaden pasos/preguntas ficticios | APROBADO |
| Visibilidad y sesión activa | test_provisional_configurable_sin_correctas_durante_sesion_activa y test_provisional_no_revela_resultados_con_intento_activo existentes, reejecutados | APROBADO; nota provisional solo habilitada, explicaciones=[] mientras S activa; intento activo no revela nota |
| Resultado pendiente | Nuevo test cerrado sin cálculo: 404, sin cabecera ni escritura | APROBADO después del fix; 503 original preservado |
| Ausencia y autorización de publicación | Confirmación docente, GET previo sin nota, publicación explícita y GET titular 0.00/AUSENTE, sin nuevas P/I | APROBADO para consumir el estado ya resuelto, no para aprobar la política productora RF24 |
| Solo lectura/recarga/concurrencia | Tres GET concurrentes idénticos; RR/READ ONLY; ausencia de DML/DDL/flush/commit y cabecera/nota/fecha/hash inalterados | APROBADO |
| No publicar al consultar | Pruebas del ciclo, estado SQL y el límite lector conservados; publicación solo por POST docente | APROBADO |
| Compatibilidad RF13 y demás RF | 180 relacionadas, general completa nueva y selección Newman de las 27 carpetas | APROBADO técnicamente; no cambia la clasificación de los otros 26 |

**Conclusión:** el bloqueo previo de RF14 por cobertura de explicaciones/privacidad se cierra con evidencia positiva. RF14 pasa a IMPLEMENTADO en la matriz de implementación y APROBADO en aceptación funcional de laboratorio. RF13 permanece PARCIAL/BLOQUEADO; este cierre no certifica fórmulas académicas fuera de su alcance ni abre inicio, repetición o divulgación adicional.

## Pruebas nuevas y diagnósticos conservados

Evidencia: evidencias/rf14_fase7_20261110/, con comandos, HEAD, huellas, consola, JUnit y eventos originales. No se suman focal, relacionada, general y Newman.

- Primera focal: 10 aprobadas/3 fallidas. Una fue el 503 funcional. Las otras fueron preparación: elección incorrecta de rama y un INSERT ambiguo que el guard BD207 rechazó. Se corrigió la rama sin cambiar la nota esperada; se comprobó SQLSTATE 23514 como protección y se mantuvo el guard, sin forzar corrupción histórica.
- Focal final: **13 aprobadas**, cero omisiones/fallos/errores, en test_rf14_student_results.py.
- Relacionada final: **180 aprobadas**, cero omisiones/fallos/errores. Incluye RF13, almacenamiento, publicación y consulta.
- General NUEVA COMPLETA: **2538 aprobadas, 38 omitidas, cero fallos/errores**; 2576 casos únicos, 124 archivos, cuatro particiones disjuntas y fuentes app/tests estables. No es conciliación de la histórica 2525/38. Se mantiene un tipo de advertencia Starlette/httpx; las omisiones externas no equivalen a aprobaciones.
- Primera Newman de las 27 carpetas: solo RF14 falló por redeclaración de una variable j en el script añadido; backend 200 no se contó como aprobación. El diagnóstico completo se conserva. Se aisló el bloque JS y se verificaron 1120 scripts por sintaxis; no se cambiaron los HTTP esperados ni se quitaron aserciones para ocultar un fallo.
- Repetición RF14: **19 solicitudes/68 aserciones**, cero fallos. Además de lo anterior, la unicidad de preguntas se comprueba por intento, no globalmente entre repeticiones.
- Selección final reemplaza únicamente RF14: **560 solicitudes/2134 aserciones**, cero fallos técnicos, **17 APROBADOS/10 BLOQUEADOS**. No sumar los ocho pasos del diagnóstico y los 19 definitivos. Los contratos de los otros 26 RF son idénticos.

Newman RF14 usó PostgreSQL **17.11**, una participación, un intento, una respuesta, un resultado y una publicación de laboratorio autorizada explícitamente. El GET repetido conserva la misma respuesta. Los XLSX/PDF de la colección reutilizada se verificaron, pero no se presentan como trabajo nuevo de RF16. No se ejecutó Postman Desktop; sí los pm.test reales mediante Newman 6.2.3.

## Demostración y comandos

Desde la raíz, usar preparar-27rf.ps1 -RF RF-14, importar colección maestra y Environment privado de ese laboratorio, seleccionar SOLO RF14 y ejecutar sus 19 solicitudes en orden. Cuentas/grupos/matrículas/asignación/resultados iniciales son preparación administrativa LAB; publicación y consulta usan API real/main con JWT. No se demuestra con ello provisión productiva RF04 ni aprobación del consentimiento.

Capturas manuales pendientes: PM-RF-14-04 revisión; -05 autorización docente; -08 resultado titular con nota, aciertos y explicaciones; -16 recarga idéntica; -17/-18 rechazos por rol/autenticación; -19 query inválida. Mostrar URL, HTTP y Test Results. Ocultar Authorization, cuerpos de login, claves y códigos. Para provisional durante sesión activa, usar el test de integración y su laboratorio específico; la carpeta RF14 publica sobre sesión finalizada y no se inventa una captura de sesión activa.

```powershell
.\.venv\Scripts\python.exe -B evidencias/rf14_fase7_20261110/run.py --modo focal --evidencias evidencias/rf14_fase7_20261110/focal_final
.\.venv\Scripts\python.exe -B evidencias/rf14_fase7_20261110/run.py --modo relacionada --evidencias evidencias/rf14_fase7_20261110/relacionada_final
# General: g0, g1, g2, g3 en destinos general_gN, después agrupar_general.py.
$runtime = Get-Content evidencias/postman_desktop_20261108/newman_runtime.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf todos --newman (Join-Path $runtime.ruta 'node_modules/newman') --evidencias evidencias/rf14_fase7_20261110/newman_27
# Tras el fix del script se repitió exclusivamente RF14 en newman_rf14_final.
```

Los destinos ya existen: usar otros nombres al repetir. La selección de evidencia final está en seleccion_final/SELECCION_RESULTADOS.json, el JUnit general en junit_general.xml y los hashes/rutas del incremento en MANIFIESTO_RF14.json. Los diagnósticos no se borran ni se preparan en Git.

## Límites y siguiente requisito

No hay aprobación nueva del catálogo de rúbricas RF13, de UC05, varias preguntas/ciclos RF10, asignación RF04 ni políticas de inicio/consentimiento/repetición. Esas son dependencias del producto completo, no razones para crear otro endpoint de consulta o mostrar resultados sin permiso. Tampoco se promete visibilidad de todas las alternativas correctas o un desglose adicional no aprobado. No se certifica integración Angular sin pruebas de navegador.

Siguiente requisito recomendado: **RF13**, conciliar su política aplicable y disparador UC05 con el equipo académico usando la evidencia técnica existente. No implementar otra fórmula ni automatizar finish/worker para forzar el cierre. Esta fase termina aquí, sin iniciar otro requisito.
