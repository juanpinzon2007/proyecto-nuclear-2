# Consulta docente privada del resultado técnico

## Checkpoint y contrato

Persistencia protegida en `6fcbea054d0f141e3e245d0198ae5336273f824e`, padre
`2a79dc7d2e8937129932e9f8f10c962c2c042cd9`. Solo las 23 rutas del manifiesto
verificado, sin secretos ni evidencias generadas. El incremento HTTP es posterior,
sin commit. No cambia ORM, Alembic, puntajes, motor ni resultados históricos.

GET `/scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico`
está en app.main a través del router Scheduling. No monta el router general de
Participation. Solo DOCENTE vigente, JWT real, cuenta activa y vínculos CASES y
SCHEDULING inequívocos; titular de sesión/caso y grupos de las asignaciones,
matrícula de la participación e intento en la misma sesión. ADMINISTRADOR,
estudiante o docente ajeno no reciben acceso. No se concede DOCENTE ADMINISTRADOR.

Respuestas: 200 resultado existente; 401 autenticación/cuenta; 403 ámbito o intento
inaccesibles, incluso ID inexistente; 404 intento autorizado sin resultado; 422
parámetros o ruta inválidos; 503 configuración o integridad no acreditadas. Los
parámetros query no están admitidos. Cache-Control: no-store, también en errores.

La representación contiene referencias históricas, modalidad, ámbito, fecha,
`oficial=false`, nota técnica, hash de procedencia y detalles autorizados. Decimal
se serializa como cadena; las fracciones también usan cadenas de enteros para
evitar pérdida de precisión JavaScript. No devuelve fuentes de código, documento
de política, credenciales, correos, respuestas correctas ni explicaciones. Solo
las preguntas efectivamente seleccionadas; los pendientes son un conteo, no
selecciones ficticias o una ruta futura elegida arbitrariamente.

El formato TECNICO expone sumas, cantidades y numerador/denominador exactos.
LABORATORIO anterior conserva sus niveles reales, sin conversión al motor nuevo.
Su restricción preexistente de lectura en base de laboratorio se conserva: no se
presenta como una nota productiva. La nota técnica no es una publicación oficial.

## Reutilización y aceptación

La consulta extiende el lector de preparación existente. Se extrajeron únicamente
el límite transaccional de lectura y la construcción del repositorio ya utilizados.
Autoriza primero la sesión completa y después la pertenencia del intento. Esto
es conservador: una incoherencia en otra fila del padrón puede cerrar la consulta
con 503; no se omiten estudiantes para obtener un informe parcial aparentemente válido.

Una Session nueva, REPEATABLE READ / READ ONLY y no_autoflush cubren autorización,
lectura y validación del resultado. Cierre con rollback, nunca commit. Se reutiliza
el repositorio canónico y su verificación histórica: puede reproducir el cálculo
para contrastar un resultado almacenado, pero no crea un resultado nuevo en GET.

Criterios de aceptación: 200 completo/vencido; 404 sin resultado y con intento
activo sin vencerlo; privacidad de ámbito y roles; fracciones exactas; misma versión
ante edición posterior; lectura concurrente sin efectos; error SQL sin filtración;
compatibilidad legacy; cero DML/flush/commit en consultas. Preparación administrativa
sintética identificada en las fixtures; JWT y relaciones críticos son reales PG17.

## Cálculo después del cierre

No se altera `ServicioCierre`, Facade, finish ni su respuesta. El cierre actual no
calcula/publica nota. El punto reutilizable es `persistir_resultado_preguntas` con
identidad titular y contexto explícitos, DESPUÉS de comprobar cierre persistido,
en su UoW de cálculo/escritura. Reintento concurrente recupera la misma cabecera.

No se añade un cálculo automático posterior al commit: si falla, el intento ya
estaría cerrado y una respuesta de error no podría presentarse como rollback del
cierre. Tampoco se fuerza atomicidad conjunta que impida cerrar por configuración
de rúbrica incompleta. Falta acordar quién invoca el comando explícito de cálculo
y cómo se recupera su fallo en la composición del producto. No se crea una ruta
POST de cálculo fuera del alcance de esta consulta. El GET nunca sustituye ese
comando ni lo dispara. Este tramo de composición no se declara implementado.

## Resultados

Primera aceptación HTTP: 22 aprobadas, sin omisiones/fallos/errores, una advertencia
conocida Starlette, 34.23 s. Focalizada relacionada: 293 aprobadas, sin omisiones,
fallos ni errores, una advertencia conocida, 207.90 s. La aceptación se amplió
posteriormente con un intento ajeno REAL persistido, acreditado en la general.
Laboratorio TCP: 9/9 solicitudes guardadas con HTTP real y sin escrituras en GET,
registrado en aceptacion_tcp.json. No ejecuta pm.test. General final: **2391 aprobadas,
38 omitidas, 0 fallidas, 0 errores**, una advertencia conocida Starlette, 1385.91 s;
2429 casos JUnit. Incluye las 24 nuevas aceptaciones. No se suman ejecuciones solapadas.
Las omisiones conservadas son 29 Identity por URL externa ausente, 3 de conexión
externa y 6 de laboratorio independiente no configurado; ninguna aceptación nueva
fue omitida. Las cifras
2367/38 del incremento anterior son históricas, no resultados de esta ejecución.
Evidencia local: `evidencias/consulta_resultados_tecnicos_20261107/`.
Focal: `pruebas_focal_20261108T012204Z/`; general:
`pruebas_total_20261108T012731Z/`. Fecha UTC de fin 2026-11-08 01:50:52,
fecha local Bogotá 7 de noviembre. Las fuentes preexistentes no cambiaron durante
pytest; solo se generó el JSON sintético BD2-04 previsto. Se comprobaron contenedores
propios restantes: ninguno. Validación estática final: 42 operaciones, 235 scripts
JavaScript con sintaxis válida y ocho comprobaciones HTTP sin SQL; NO ejecución pm.test.
Archivos, tamaños y SHA-256: `MANIFIESTO_INCREMENTO.json` en esa carpeta de evidencia.

## Postman y capturas

Importar `postman/Proyecto_Nuclear_resultados_tecnicos.postman_collection.json` y
`postman/Proyecto_Nuclear_laboratorio.postman_environment.json`.
La colección tiene nueve solicitudes: login docente/estudiante/docente ajeno,
GET 200, anónimo 401, JWT inválido 401, estudiante 403, docente ajeno 403 y resultado
no disponible 404. pm.test verifica contrato, ámbito no oficial, versión histórica,
cadenas decimales/fracciones, no caché y ausencia de credenciales/fuentes.

Desde la raíz, en PowerShell interactivo:

```powershell
.\.venv\Scripts\python.exe -B backend\docs\postman\laboratorio_resultados_tecnicos.py --puerto 8765
```

El operador elige clave/código sintéticos mediante entrada oculta. El script usa
solo fixtures administrativas y PostgreSQL17 NUEVO; prepara un resultado vencido
33.33 y otro intento sin resultado dentro del mismo ámbito. El permiso de repetición
para preparar ese segundo intento es exclusivamente LAB, no evidencia de un flujo
productivo aprobado. No cambia políticas ni conecta el inicio en main.

Copiar las referencias sintéticas impresas a valores locales del Environment:
base_url, sesion_id, version_id, id_intento, intento_sin_resultado_id y correos
sintéticos. Completar localmente clave_docente/codigo_estudiante elegidos y
laboratorio_confirmado=true. No exportar el entorno usado ni respuestas de login.
La preparación puede requerir Docker Engine disponible y descargar postgres:17.

Capturas: (1) GET autorizado, URL y HTTP200 con oficial=false/33.33; (2) detalle de
criterios 50/3 + 50/3 y versión histórica; (3) docente ajeno/estudiante HTTP403 sin
nota; (4) intento_sin_resultado_id HTTP404 sin nota; (5) Test Results de pm.test,
solo después de ejecutarlo realmente. Ocultar pestañas/cabeceras Authorization y
respuestas de login. Enter en la consola detiene servidor y limpia solo su contenedor.

Validación estática de artefactos y HTTP Python no equivalen a ejecutar Postman.
CLI/Newman no disponibles en la revisión inicial; no se atribuyen aprobaciones de
pm.test. El recorrido integral anterior permanece separado.

## Cobertura y límites

RF-13/RF-24 permanecen PARCIAL: se incorpora una lectura docente técnica real,
no publicación/consolidación ni ausencias automáticas. RF-14 no se habilita para
estudiantes; RF-16 depende de resultados oficiales/padrón/consolidación; RF-25
mantiene pendientes identidad de evaluación y selección de repeticiones.
Siguiente decisión técnica: composición explícita y recuperable del comando de
cálculo tras cierre; revisión posterior de publicación/ausencias según contratos.


## Estado Git al cierre

Rama feature/backend-continuidad; HEAD 6fcbea054d0f141e3e245d0198ae5336273f824e.
Un solo commit autorizado en esta iteración, sin push/merge/PR. El índice quedó
vacío; implementación HTTP, pruebas, informe/matriz y Postman siguen sin commit.
No se aplicaron cambios en .env, stash, respaldos ni bases permanentes. No se
modificó ninguna migración después del checkpoint. `git diff --check` aprobado.
Se mantienen intactos el contrato propuesto de Evaluation y las evidencias históricas.
