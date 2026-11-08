# Fase 9: consulta privada del escenario actual

Actualización posterior: el montaje limitado en `app.main`, su configuración y
sus pruebas están en [FASE_9_APLICACION_PRINCIPAL.md](FASE_9_APLICACION_PRINCIPAL.md).
Este documento conserva la evidencia histórica de la aplicación aislada.

Fecha local: 4 de noviembre de 2026 (America/Bogota).
Base: `origin/develop`, `4ade83a64ffef3347dba2c649b8461c75fb11741` (merge PR #7).
Validación actual: `C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2`,
rama `feature/backend-continuidad`. Los 11 archivos trasladados están presentes
y sus SHA-256 coincidieron con el manifiesto del incremento anterior.
No se copiaron nuevamente ni se sobrescribieron. No se crearon worktrees ni commits.
La preparación anterior en `C:\SPS\fase9-escenario` se conserva como antecedente.

## Contrato

`GET /api/v1/attempts/{attempt_id}/current-scenario`, Bearer JWT estudiantil.
No admite parámetros query para escoger pregunta, escenario, versión o estudiante.
La dependencia productiva permanece cerrada por defecto. El servidor puede componer
la consulta con `crear_dependencia_escenario_8b(crear_sesion, fechas, reloj)`.
No se registra el router general de Participation en `app.main`.

Respuesta 200: `id_escenario`, `contexto`, `pregunta` (id, enunciado, opciones con
id/texto), `recorrido_finalizado` y `respondidas`. No se serializan modelos ORM,
transiciones, destinos, rúbrica, valoraciones, justificaciones o corrección.
Si se llegó a FIN, escenario/contexto/pregunta son null y el indicador es true;
esto NO cierra automáticamente el intento. `Cache-Control: no-store`.

401: JWT ausente/inválido o cuenta inactiva; 403: titularidad/convocatoria/matrícula
o sesión/horario no autorizados; 404: intento inexistente; 409: cerrado o vencido;
422: parámetros de consulta no admitidos; 503: composición, infraestructura o
recorrido no disponibles. El error no incluye el contenido privado.

## Reutilización e integridad

- DTOs inmutables de aplicación; esquemas HTTP con lista blanca.
- `ConsultaEscenarioActualSQLAlchemy` compone UoW, repositorio de Participation,
  `_cargar_autorizado`, `IdentityIntentoSQLAlchemy` y `SchedulingIntentoSQLAlchemy`.
- Revalida cuenta, roles, matrícula, contexto JWT, convocatoria activa, sesión y
  edición exacta. Usa la ventana de RESPONDER ya confirmada; no autoriza inicio
  ni aplica una tolerancia nueva. El reloj inyectado se comprueba después de
  adquirir los locks para no conservar una hora anterior a una espera concurrente.
- `RecorridoCasesSQLAlchemy.obtener_actual` amplía el adaptador existente y usa
  `RepositorioGrafoSQLAlchemy.leer` / `GrafoVersion.recorrer`, sin otro repositorio
  ni algoritmo de navegación. Lee únicamente la versión asignada; permite su
  conservación histórica ARCHIVADA conforme al lector existente.
- El grafo mantiene bloqueados ciclos, múltiples preguntas por escena y
  transiciones incompletas. Ninguna selección se crea, elimina o modifica.
- Los locks siguen el orden de los escritores existentes; no hay commit, flush
  explícito, asignación de IDs ni guardado del agregado. La UoW sale con rollback
  y libera los locks. La verificación de tiempo NO persiste VENCIDO desde GET.
- Progreso y cierre conservan sus contratos; Evaluation y las migraciones no
  se modifican.

## Pruebas y evidencia

`test_current_scenario_http.py` contiene aceptación ejecutada con PostgreSQL17
propio, JWT real y las relaciones SQL existentes: contenido y whitelist, consultas
repetidas sin DML, consulta futura rechazada, JWT/ajeno/retiro/matrícula/inactividad,
sesión fuera de condiciones, vencido/cerrado, falta de composición, rama alternativa
y FIN, edición 2 del mismo caso con archivo de la anterior, y fallos de dependencia.
Solo estos últimos fallos se inyectan; no se simula la autoridad de los positivos.

Preparar una edición 2 aún requiere fixture administrativa con el mapeador actual,
como en RF18; no se afirma que haya un endpoint de creación de ediciones. El grafo
de esa edición y la publicación/archivo sí se realizan mediante API.

`test_student_vertical_journey.py` ahora obtiene la primera pregunta y la siguiente
por GET, en lugar de `h.escenas`. Comprueba FIN sin preguntas y rechazo del contenido
tras cerrar. Conserva login correo/código y el enlace interno 8C del mismo intento.
`test_api.py` conserva los controles previos de OpenAPI y añade inventario de siete
rutas, Bearer y whitelist de la nueva respuesta.

Evidencia histórica: `C:\SPSBackups\fase9-escenario-20261105T015054Z`.
Incluye respaldo de 374 archivos originales con SHA-256, fuentes de cada ejecución,
comandos, logs, JUnit XML y resultados nominales. El nombre del directorio usa UTC;
la fecha local corresponde al 4 de noviembre.

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores |
| --- | ---: | ---: | ---: | ---: |
| Focal inicial PostgreSQL | 0 | 0 | 0 | 15 |
| Regresión Participation inicial sin motor | 354 | 9 | 1 | 0 |
| Regresión Participation corregida sin motor | 355 | 9 | 0 | 0 |

Los 15 errores fueron de preparación: `docker image inspect postgres:17` agotó
40 segundos, sin crear un laboratorio. Docker Desktop informó `paused` y la UI
mostró `Engine stopped`. No acreditan fallos ni éxitos funcionales del endpoint.
El fallo unitario fue el inventario OpenAPI anterior (seis rutas, ahora siete);
se actualizó junto con comprobaciones de privacidad y autenticación.
Advertencia conocida en las tres ejecuciones: Starlette/TestClient-httpx.
Las nueve omisiones antiguas requieren conexiones externas expresamente
deshabilitadas; no se consideran aprobadas.

Lo anterior describe exclusivamente los intentos históricos, cuando Docker estaba
pausado. No se reemplazaron por mocks ni se atribuyeron aprobaciones a esos errores.

### Validación actual en feature/backend-continuidad

Docker Engine respondió con versión 27.4.0. Se utilizó la imagen local
`docker.io/library/postgres:17`, ID
`sha256:3b0cda93be7c8dba2ed484d19393d93845dc3dafb88973e248ba8e6d99d784e1`,
con `PG_MAJOR=17` y `PG_VERSION=17.11-1.pgdg13+2`.

| Ejecución actual | Aprobadas | Omitidas | Fallidas | Errores | Advertencias pytest |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aceptación HTTP y vertical, 48.33 s | **17** | **0** | **0** | **0** | 1 |
| Regresión relacionada, 258.38 s | **761** | **9** | **0** | **0** | 1 |

Las 17 son 16 escenarios de `test_current_scenario_http.py` y la prueba vertical
actualizada. La regresión incluye esas mismas pruebas: no se suman los resultados.
Las nueve omisiones corresponden a tres pruebas antiguas con conexión externa y
seis dependientes de `SPS_PERSISTENCE_LAB_URL`, deshabilitadas deliberadamente.
No impidieron ejecutar las pruebas PostgreSQL desechables. La advertencia pytest
es la conocida de Starlette/TestClient-httpx.

Git también emitió un aviso `Filename too long` al recorrer una carpeta preexistente
de evidencias antiguas. Es independiente de pytest; no se renombró ni eliminó
ningún archivo para suprimirlo. Los 11 archivos de este incremento sí se
verificaron individualmente y fueron accesibles.

Evidencia actual, relativa al repositorio:
`evidencias/fase9_validacion_20261105T025639Z/`:

- `estado_inicial.json`: rama, HEAD, Git y comprobación nominal de los 11 archivos.
- `pruebas_focal_20261105T025659Z/`: comando, consola, JUnit, fuentes y resultado.
- `pruebas_general_20261105T025811Z/`: mismos artefactos para la regresión relacionada.
- `aceptacion_nominal.json`: los 17 tests con sus resultados individuales.
- `respuesta_publica.json`: respuesta real capturada por la aceptación HTTP.
- `recorrido_vertical.json`: pasos HTTP y frontera interna 8C del mismo intento.
- `CIERRE.json`: preservación, huellas, limpieza y estado final de la validación.

El ejecutor conserva la selección de pruebas anterior, adaptando exclusivamente
ruta y rama. Como este repositorio tiene `.env`, deshabilita su lectura mediante
`Settings.model_config['env_file']=None` SOLO en el proceso hijo de pytest, antes
de importar las pruebas. El archivo no se modifica. Además elimina del entorno
hijo las credenciales y URLs externas, fuerza los flags de aislamiento y verifica
que las fuentes no cambien durante cada ejecución. No modifica la autenticación
ni reemplaza los repositorios SQL reales.

No se encontraron defectos funcionales que requirieran cambiar el código trasladado.
Esta continuidad modifica únicamente este informe y genera su ejecutor/evidencias
locales. No modifica políticas, DBML, modelos, migraciones ni `main.py`.

### Respuesta real observada

HTTP 200, con `Cache-Control: no-store`, para el titular autenticado en el laboratorio:

```json
{
  "id_escenario": "2cc84010-22da-4ac2-a5c3-5a990a786cc6",
  "contexto": "Escenario uno.",
  "pregunta": {
    "id": "f2eb7f59-5a25-40d4-b7e9-6dc28628eb4d",
    "enunciado": "¿Qué haría?",
    "opciones": [
      {"id": "d32de303-d4fe-4a0f-bc80-54102d67915b", "texto": "Opción 1"},
      {"id": "bbbf357b-f943-47ec-b09d-b56fece94551", "texto": "Opción 2"}
    ]
  },
  "recorrido_finalizado": false,
  "respondidas": 0
}
```

Son identificadores generados por los servicios reales en datos sintéticos. No
son recursos permanentes. El test compara contexto, enunciado y alternativas con
la edición de Cases, verifica ausencia de preguntas futuras/corrección/notas,
rechaza parámetros para elegir preguntas y observa cero instrucciones DML en los
GET repetidos. Las sesiones SQL independientes confirman que los datos no cambian.

Reproducción mediante el ejecutor aislado conservado:

```powershell
# Ejecutar desde la carpeta actual autorizada:
Set-Location 'C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2'
docker version --format '{{.Server.Version}}'
& C:\Python313\python.exe -B .\evidencias\fase9_validacion_20261105T025639Z\ejecutar_validacion.py focal
& C:\Python313\python.exe -B .\evidencias\fase9_validacion_20261105T025639Z\ejecutar_validacion.py general
# Solo visualizar evidencia existente, sin volver a ejecutar pruebas:
Get-Content .\evidencias\fase9_validacion_20261105T025639Z\respuesta_publica.json -Encoding UTF8
```

`general` es la regresión RELACIONADA seleccionada en ese script, no la suite global.
El ejecutor excluye la lectura de .env y conexiones externas, redacta secretos, habilita únicamente
el fixture que crea contenedores propios y verifica que las fuentes no cambien
durante pytest. Cada ejecución conserva por separado sus resultados solapados.

## Disponibilidad y continuidad

**Acreditado en aplicación ASGI aislada con TestClient, JWT real y PostgreSQL17
desechable.** No es una prueba contra un servidor HTTP desplegado. La preparación
administrativa y las políticas de inicio/provisión/ingreso siguen siendo de
laboratorio; no se presentan como flujo docente productivo ni aprobación académica.
La consulta no está habilitada en la aplicación principal ni desplegada.

8B: continúan pendientes las aprobaciones productivas de ingreso RF-22,
consentimiento/revocación, provisión y repetición. No se habilitan ciclos ni
configuraciones multipregunta. 8C: mapeo/agregación/redondeo y publicación oficial
siguen bloqueados; su persistencia técnica no equivale a notas aprobadas.
9: se acredita el recorrido vertical actualizado: login, ingreso sin escritura,
inicio transaccional, lectura del escenario, respuesta inmutable, siguiente pregunta,
FIN, progreso privado, cierre idempotente y lectura interna histórica de 8C. La
previsualización sin mapeo aprobado se rechaza y no genera una nota oficial.

Siguiente paso recomendado, sin ejecutarlo: revisar una composición limitada de
rutas cuya autorización esté completa, conservando cerrados inicio y provisión
hasta aprobar sus políticas. No se habilita globalmente Participation ni se
continúa otro módulo en esta validación.
