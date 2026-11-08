# RF-16: reportes oficiales Excel y PDF — corte vigente 8/11/2026

## Contrato acreditable y fuente

RF-16 (fuente académica central, p. 4) exige descargar resultados académicos,
parciales y ausencias. UC-07 (p. 12) exige seleccionar sesión/estudiantes,
aplicar alcance docente en backend y emitir encabezados/mensaje explícito sin datos.
RN-18 restringe exportación al ámbito docente. La solicitud vigente exige XLSX/PDF.
No se crea un estado APROBADO ni una fórmula en el exportador.

Se reutiliza el GET de Identity y el Proxy. El lector oficial comparte con
`CicloAcademicoSQL` la autorización sesión/caso/grupos y la verificación del
snapshot canónico publicado (`publicacion_evaluacion` + `resultado_participacion`).
La selección del máximo, ausencia confirmada, exclusión de retiradas y autorización
de publicación ya fueron resueltas por ese servicio. El reporte copia el resultado;
no invoca estrategias, consolidación ni publicación. Una rectificación sin nueva
publicación conserva la última versión oficial. Puede descargarse una versión previa.

## HTTP registrado en app.main

`GET /api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte`

| Parámetro | Contrato |
|---|---|
| formato | `xlsx` o `pdf`; sin él, el antiguo CSV conserva su 503 |
| version_publicacion | Entero positivo; omitido selecciona última publicación oficial |
| id_grupo | Entero positivo presente en la publicación autorizada |
| id_estudiante | Entero positivo repetible; selección de estudiantes de la publicación |
| estado | COMPLETA, PARCIAL o AUSENTE; sin inventar aprobación académica |
| agrupar_por | grupo (predeterminado de presentación) o estudiante; orden estable por nombre/ID |

200 binario con Content-Disposition, MIME específico, Cache-Control:no-store,
X-Content-Type-Options:nosniff, X-Publicacion-Id/Version/SHA256. 401 sin autenticación,
JWT inválido o cuenta inactiva; 403 rol/ámbito/selección ajenos; 404 sin publicación
o versión inexistente; 422 parámetros inválidos; 503 configuración histórica ausente,
fuente inconsistente o fallo de exportador. No devuelve detalles internos de error.
Docente administrador no recibe privilegios implícitos. Cliente no aporta identidad.

La lectura usa una Session propia, snapshot REPEATABLE READ, READ ONLY y
no_autoflush; termina mediante rollback al cerrar, nunca flush ni commit. El archivo
se genera en memoria una vez cerrada la transacción de lectura. No hay DML, archivos
temporales con datos estudiantiles ni llamadas de red externas en el serializador.

## Contenido y privacidad

XLSX real: Publicacion, Resultados, Intentos y Antecedentes. Nota oficial numérica
con dos decimales; fechas de intentos son valores datetime UTC con etiqueta explícita;
ID y conteos enteros. Texto siempre literal, nunca fórmula/hipervínculo; cabeceras,
ancho/alto de filas, filtros, panel inmovilizado y configuración de impresión.
PDF real: título neutro sin logos/aprobaciones inventadas, versión/huella/fecha UTC,
resultados, intentos históricos, antecedentes y páginas con encabezados repetidos.
Fuentes Vera distribuidas por ReportLab para caracteres españoles. No se incluyen
correos, contraseñas, JWT, respuestas, rúbricas ni explicaciones.

Fechas/duraciones reales se leen solo de los intentos cerrados incluidos por ID en
la publicación, comprobando participación/número/estado. No se agregan duraciones
entre intentos para inventar otra medida. Las ausencias no fabrican intento o fecha.
El nombre histórico del caso proviene de su versión inmutable; alumno y grupo,
del snapshot. Las retiradas solo tienen UUID en la fuente: se conservan como
antecedentes RETIRADA sin nota ni nombre inventado. Esta limitación de metadatos
históricos no se oculta mediante un join al padrón actual.

## Dependencias y alcance de cambios

Producción: openpyxl 3.1.5 (MIT) y ReportLab 5.1.0 (BSD), compatibles con Python 3.13
del laboratorio. Rangos en pyproject. Pruebas: pypdf 6.x para lectura real de PDF.
Fuentes de licencia: https://pypi.org/project/openpyxl/ y https://pypi.org/project/reportlab/.
No se agregan modelos, tablas ni revisiones Alembic. El CSV de componente conserva
sus pruebas históricas y no se presenta como exportación oficial alternativa.

## Validación y evidencia

Evidencia local: `evidencias/rf16_reportes_20261108/` (no versionar).
21 casos focalizados aprobados con el código estabilizado; 450 pruebas relacionadas
aprobadas en la ejecución previa de integración (sin sumar suites solapadas). Quedan
registrados JUnit, consola y archivos descargados. Configuración temporal ausente o
inválida y error SQL de lectura también se rechazan sin escrituras, con recuperación posterior. Las ejecuciones iniciales fallidas
se conservan: guard CSV antiguo todavía cerrado en Proxy, un dato de ruta inválido
en la fixture y conteos de pruebas sin restringir a la sesión. Se corrigieron el
encaminamiento al lector oficial y las aserciones/fixture sin debilitar autorización.

Resultados definitivos de esta ejecución, sobre base fee07cb + incremento local:

| Validación | Aprobadas | Omitidas | Fallos/errores |
|---|---:|---:|---:|
| Focalizada final RF-16 | 21 | 0 | 0 / 0 |
| Relacionada, ejecución anterior al último ajuste de presentación y tres casos defensivos | 450 | 0 | 0 / 0 |
| General final: 115 módulos, cuatro particiones disjuntas | 2457 | 38 | 0 / 0 |

No sumar las filas: se solapan. General = 2495 casos nominales, incluye las 21
aceptaciones RF-16 finales. Particiones: 654/0, 567/3, 736/29, 500/6
(aprobadas/omitidas). Un tipo de advertencia conocido de Starlette/httpx se repite
por proceso. Las 38 omisiones corresponden a pruebas opcionales que requieren
URLs/activación PostgreSQL externas; no son aprobaciones. Las pruebas PG17 de
RF-16 y sus integraciones sí ejecutaron contenedores propios nuevos.

JUnit consolidado y sin duplicados: `general_junit.xml`; resultados/omisiones,
logs y huellas por partición, en la carpeta local de evidencia. Fuentes invariables
durante cada ejecución. Una prueba histórica BD2 generó su JSON de evidencia con
nombre UUID, conservado sin versionar; ningún archivo preexistente cambió por pytest.
Tras las pruebas no quedan contenedores propios: los ajenos detenidos se conservaron.
No se aplicaron cambios sobre bases permanentes ni se alteró .env.

15 solicitudes HTTP TCP ejecutadas con httpx siguiendo la colección de entrega:
login real, consolidación/publicación explícitas, replay y lectura; ambas descargas
pertenecen a la misma publicación v1 (PARCIAL 33.33) y tres rechazos adicionales.
`demostracion_http.json` identifica PostgreSQL 17.11 y las respuestas reales,
sin tokens. XLSX leído con openpyxl y cuatro hojas renderizadas; PDF leído con
pypdf y páginas renderizadas/inspeccionadas (incluida tabla multipágina).
Node compiló 243 scripts de catálogo/entrega sin errores. Postman CLI y Newman
no están instalados: **no se ejecutó pm.test ni Postman Runner**; la evidencia
HTTP Python y las comprobaciones binarias no se presentan como Runner.

RF-16 queda IMPLEMENTADO en app.main para publicaciones oficiales existentes.
Sin fuente oficial se devuelve 404; sin formato, CSV legado 503. El incremento
no permite calificar cierres voluntarios sin FIN, ni habilita inicio productivo,
ni resuelve por suposición los once RF que siguen PARCIAL. La matriz cambia solo
RF-16: 16 IMPLEMENTADO y 11 PARCIAL, no una declaración de backend terminado.
Guía de demostración: `postman/entrega_20261109/RF16_REPORTES.md`.

## Archivos del incremento (23 rutas explícitas)

- `backend/app/modules/identity/api/dependencies.py`
- `backend/app/modules/identity/api/router.py`
- `backend/app/modules/identity/application/ports.py`
- `backend/app/modules/identity/application/proxy_seguimiento.py`
- `backend/app/modules/identity/application/services.py`
- `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`
- `backend/docs/RF16_REPORTE_Y_BLOQUEOS.md`
- `backend/docs/postman/INVENTARIO.md`
- `backend/docs/postman/Proyecto_Nuclear_laboratorio.postman_environment.json`
- `backend/docs/postman/Proyecto_Nuclear_main.postman_collection.json`
- `backend/docs/postman/entrega_20261109/Proyecto_Nuclear_entrega_20261109.postman_collection.json`
- `backend/docs/postman/entrega_20261109/Proyecto_Nuclear_entrega_20261109.postman_environment.json`
- `backend/docs/postman/entrega_20261109/generar.py`
- `backend/docs/postman/generar_colecciones.py`
- `backend/docs/postman/inventario_endpoints.json`
- `backend/docs/postman/openapi_main.json`
- `backend/pyproject.toml`
- `backend/app/modules/identity/application/official_reports.py`
- `backend/app/modules/identity/infrastructure/official_reports.py`
- `backend/app/modules/identity/infrastructure/report_exporters.py`
- `backend/tests/integration/test_official_reports_http.py`
- `backend/docs/postman/entrega_20261109/Proyecto_Nuclear_reportes_oficiales.postman_collection.json`
- `backend/docs/postman/entrega_20261109/RF16_REPORTES.md`

---

# Historial conservado: diagnóstico del 5 de noviembre (ya no describe el corte vigente)

# RF-16: reporte académico y validación del exportador existente

5 de noviembre de 2026. Rama `feature/backend-continuidad`, base `33981c8`.
Se preservan los incrementos locales RF-19, autenticación y RF-15.

## Diagnóstico y alcance seleccionado antes de implementar

RF-16 exige descargar resultados académicos, avances parciales y ausencias para
registrar notas. No autoriza calcular una nota ni inferir AUSENCIA de una fila
faltante. RF-13/24 y el contrato de consolidación son dependencias, no decisiones
del serializador.

- GET `/api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte` está registrado
  en main, pero ProxySeguimiento llama al ámbito de sesión que responde 503.
  Además, ServicioSeguimiento tiene `reportes=None`; no hay LecturaReportes real
  compuesto. Un token de docente no habilita un reporte por sí solo.
- `ConsultaResultadosReporteSQLAlchemy` parte de P → matrícula → usuario y hace
  LEFT JOIN a resultado_participacion, restringido por asignación y participaciones
  autorizadas recibidas. No descubre convocados sin P ni verifica él solo el docente.
- Scheduling sí almacena convocatorias y retiros; falta fijar el padrón académico
  del reporte, su corte y tratamiento de retiros. Una sesión puede tener asignaciones
  a varios grupos. No duplicar un convocado por joins ni equiparar retiro y ausencia.
- `resultado_participacion` no está integrado en metadata/migraciones vigentes.
  `resultado_intento`/detalle sí existen, con CHECK `ambito='LABORATORIO'`.
  No son fuente alternativa de calificaciones oficiales ni permiten consolidar
  intentos eligiendo mayor/última nota por iniciativa del reporte.
- `EstadoReporte` contiene COMPLETA/PARCIAL/AUSENCIA, contrato técnico del DTO.
  No es un cálculo académico ni sinónimo de APROBADA. FilaReporte permite nota
  nula; vacío se conserva, nunca se rellena con cero.
- CSV actual: `id_estudiante,id_participacion,estado,nota`. Es el contrato técnico
  existente del exportador, no evidencia de una plantilla institucional aprobada.
  Los RF no fijan por sí solos esas columnas/orden. No se añaden campos, formatos
  ni estados nuevos en esta iteración.

**Incremento viable:** validar integridad de la entrada del serializador existente:
una fila por estudiante de la sesión, una participación no asociada a dos filas,
notas presentes dentro del 0–100 ya confirmado. Si llegan varias filas/estados
incompatibles, rechazar el conjunto; nunca deduplicar eligiendo un intento o nota.
La unicidad actual convocatoria(sesión, estudiante), participación(convocatoria)
y participación(asignación, matrícula) respalda este control técnico del reporte
por sesión; no resuelve la regla de consolidación de intentos.

Criterios de aceptación:

1. Conservar cabeceras, precisión Decimal, neutralización de fórmulas y vacíos.
2. Rechazar duplicados/contradicciones y notas fuera de escala, sin producir un
   archivo parcial ni alterar filas para que el resultado parezca consistente.
3. Acreditar solo el componente CSV con datos sintéticos identificados como LAB;
   no presentar ese archivo como exportación oficial obtenida desde PostgreSQL.
4. Con PostgreSQL17 desechable y JWT real, comprobar que padrón incompleto para
   la consulta P y resultados inexistentes no abren el endpoint; cero DML/commits,
   sin revelar datos a ajenos/no docentes ni crear estados de ausencia.
5. Mantener cerrado el endpoint productivo. No implementar Evaluation ni una
   tabla ficticia de resultados consolidados para superar el bloqueo.

No se considera completamente bloqueado el trabajo técnico del componente CSV;
sí lo está la entrega del reporte oficial. No se cambia a otro RF para aparentar
que se ha terminado RF-16.

## Implementación y evidencia actual

Único cambio productivo: `identity/application/services.py::ServicioReportes.descargar`.
Materializa las filas del puerto una vez y valida unicidad de estudiante y de
participación no nula, y escala de nota presente 0–100 antes de serializar. Datos
duplicados/contradictorios o fuera de escala producen IntegracionPendiente, no una
elección silenciosa de fila. No agrega, redondea, reclasifica ni cambia el CSV válido.
Los identificadores siguen escapándose contra fórmulas y None sigue vacío.

El serializador **no certifica la procedencia oficial** ni autorización de sus
filas: eso compete al proveedor LecturaReportes/Proxy, todavía sin composición
productiva. Ninguna nota LAB se convierte en oficial por pasar estas validaciones.

| Ejecución | Aprobadas | Omitidas | Fallos | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Focal `pruebas_casos_20261105T204245Z` | 13 | 0 | 0 | 0 | 1 |
| Relacionada `pruebas_focal_20261105T204324Z` | 140 | 0 | 0 | 0 | 1 |
| General `pruebas_total_20261105T204545Z` | 2053 | 38 | 0 | 0 | 1 |

Tiempos: 14.45 s, 71.52 s y 857.04 s. No se suman suites solapadas. La general
incluye los incrementos pendientes RF-19 y RF-15; no se atribuyen sus pruebas solo
a RF-16. La advertencia conocida es Starlette/TestClient/httpx. Las 38 omisiones
mantienen sus causas de configuración de laboratorios alternativos en consola/JUnit.

- `tests/identity/test_report_integrity.py`: seis pruebas de componente con doble
  explícito del lector. Verifican duplicados, contradicción de propiedad, límites,
  vacíos y CSV; no prueban notas oficiales o lecturas PostgreSQL.
- `tests/integration/test_main_report_closed.py`: siete casos con main/JWT/PG17
  reales. Un docente válido (propio o ajeno) recibe 503 porque no se compuso el
  ámbito/reporte; no se presenta ese 503 como autorización de propiedad completa.
  Estudiante 403; anonimato/token inválido 401. Sin archivo, datos académicos,
  DML, flush ni commits. Reintentos concurrentes conservan el cierre seguro.
- El laboratorio prepara dos convocados con identidad/matrícula explícitas y
  solo una participación, sin resultados; no asigna AUSENCIA a la fila faltante.
  Se comprueba que no hay resultado_participacion físico en esa base aislada y
  que el descriptor del consolidado rechaza sustituirlo por resultado_intento.
  El segundo convocado es preparación administrativa de datos históricos, no
  prueba de que la API autorice agregar estudiantes a una sesión EN_CURSO.

Paquete: `evidencias/rf16_integridad_20261105T203847Z/`. Incluye consola, JUnit,
comandos, hashes, aislamiento y `SERIALIZADOR_LAB_NO_OFICIAL.csv`. Este archivo es
la salida real de la prueba **unitaria** registrada en JUnit, reabierta y validada
como CSV UTF-8 con cuatro filas sintéticas y las cuatro cabeceras actuales. Su
SHA-256 y origen están en `archivo_csv.json`; no es una descarga HTTP ni un reporte
de estudiantes reales. No se presenta como evidencia de exportación oficial PG.

## Bloqueos exactos y orden para completar RF-16

1. Scheduling/academia: padrón autorizado de referencia, fecha de corte y reglas
   para retirados/matrículas/grupos superpuestos. La consulta basada solo en P
   pierde convocados; no añadirlos como ausentes automáticamente.
2. Evaluation: definición oficial de niveles/logro, agregación de preguntas y
   precisión/redondeo cuando aplique; confirmación de ausencia y consolidación
   de múltiples intentos. No basta escoger última/mayor nota o FINALIZADO.
3. Persistencia y procedencia oficial: integrar resultado_participacion bajo
   contrato aprobado. El DBML original tiene id_participacion obligatorio y
   nota_definitiva DECIMAL(4,2): no permite 100.00 ni un resultado sin P. Deben
   resolverse ambas relaciones físicas sin crear intentos/participaciones ficticias.
   La adaptación previa de resultado_intento no autoriza por analogía este DDL.
4. Formato institucional y mapeo de estados/columnas: aprobar lo requerido antes
   de añadir nombres/correos/versiones o interpretar situacion libre como estado
   oficial. COMPLETA no significa APROBADA y no se introduce umbral de aprobación.
5. Componer consulta autorizada que reutilice versión exacta y evidencias oficiales,
   y solo entonces activar el CSV existente con pruebas HTTP de archivo descargado,
   integridad, casos sin resultado y no duplicación. Login del personal sigue
   siendo una dependencia transversal, no se sustituye con el token de fixture.

RF-16 conserva BLOQUEADO para entrega oficial; este es un incremento técnico
limitado de integridad. No hay otro parcial de la matriz listo para completarse
sin contratos pendientes: RF-02/03/04 dependen de autenticación/proceso académico,
RF-20/21 de entrega segura por correo y RF-10/12/23/27 de inicio o evaluación.
No se escoge uno de esos para inventar reglas. Siguiente dependencia recomendada:
RF-13, concretar el contrato académico de resultados y su relación con RF-24;
sin él RF-16 no puede exportar notas confiables.

No se modificaron main, SQLAlchemy, migraciones, Evaluation, login, RF-19 ni RF-15.
La general generó únicamente un JSON de evidencia BD2-04, conservado y excluido
de commits. No hubo edición de fuentes mientras pytest estaba activo. Rama/HEAD,
stash, `.env` y archivos anteriores se verifican en `CIERRE.json`, sin commits ni
publicaciones y sin bases permanentes. Laboratorios propios eliminados.
