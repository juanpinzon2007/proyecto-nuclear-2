# Resultado real de la preparación Postman

7 de noviembre de 2026, America/Bogota. HEAD
`8e1c03400b47d571eb903e40f0175c3d1c3f1008`, rama feature/backend-continuidad.

## Acreditado en este incremento

| Verificación | Resultado | Alcance |
|---|---|---|
| Inventario vs OpenAPI actual | 40 operaciones coincidentes | Más 4 rutas técnicas GET/HEAD; 48 combinaciones método/ruta |
| Catálogo importable 2.1 | 174 solicitudes preparadas | Positivas y negativas; NO 174 pruebas HTTP ejecutadas |
| Recorrido importable LAB | 30 solicitudes ordenadas | Main y servidor aislado claramente separados |
| Variables/JSON/estructura local | Correctos | Sin valores secretos en Environment ni respuestas guardadas |
| Sintaxis de scripts con Node | 206 scripts válidos | NO ejecución del sandbox pm.test |
| HTTP ASGI sin SQL | 6 comprobaciones correctas | health/OpenAPI 200 y cuatro rechazos 401 |
| HTTP TCP PostgreSQL17 | 30/30 pasos correctos | Python/httpx a Uvicorn, JWT/roles/relaciones SQL reales |
| Persistencia al terminar | FINALIZADO, 2 respuestas, 0 resultados oficiales | Otra Session SQL, sin sustitución de respuestas |
| Postman CLI / Newman | No disponibles | No instalados; ejecución e importación Desktop pendientes |

Dos ejecuciones independientes completaron el mismo recorrido de 30 pasos:
`resultado_http_20261107T180726Z.json` y
`resultado_http_20261107T181147Z.json`. **No sumar como 60 pruebas distintas**.
La última huella de colección coincide con la colección entregada. No se ejecutó
la suite general ni se trasladan sus cifras históricas a esta entrega.

La primera ejecución, `resultado_http_20261107T180624Z.json`, se conserva como
NO APROBADA: sus primeros 27 estados HTTP eran correctos, pero el verificador
presuponía cero commits para cualquier GET. La consulta existente de feedback
confirma una transacción lectora (`with s.begin()`), sin DML. El verificador fue
corregido para registrar ese hecho; no se alteró código productivo ni se ocultó el
resultado inicial. Los GET de intento/listado administrativo comprobados siguen
sin DML ni commits. El test de sintaxis inicial también corrigió un falso positivo
de su detector de llaves JSON; no fue un fallo HTTP del backend.

El HTTP TCP ejercitó login admin/docente/estudiantes, listado privado de docentes,
identidad, admisión persistida, validar ingreso, documento/aceptación LAB,
inicio LAB, duplicado rechazado, privacidad, escenario, respuestas inmutables,
progreso, cierre/idempotencia, feedback individual, acceso ajeno rechazado,
notificaciones internas y reporte oficial cerrado con 503.

## Preparación y limitaciones

Se reutiliza el fixture integral ya existente para datos administrativos sintéticos
y políticas explícitas. Solo el reloj de main se sustituye por el fijo del LAB;
JWT, repositorios, roles y autorización no se sustituyen. No se acredita la
provisión de grupos, matrículas, grants o asignaciones por endpoints inexistentes.

PostgreSQL se construyó desde las migraciones actuales en contenedores nuevos
`postgres:17`, con etiqueta `sps.identity.mapping.lab=true`, datos tmpfs, puerto
localhost efímero y base propia validada por la fixture. No se conectaron bases
existentes ni se ejecutaron migraciones permanentes. Al finalizar se verificó que
no quedaran contenedores de ese laboratorio.

La colección prueba datos/estado HTTP y privacidad; un cliente Postman no puede
probar por sí solo que no hubo SQL DML. Esa garantía se observó desde los hooks SQL
del verificador Python. No se anuncian garantías de concurrencia o rollback nuevas
por este recorrido secuencial; sus pruebas previas no se han vuelto a ejecutar aquí.

El archivo `VALIDACION.json` separa la revisión estructural y las seis solicitudes
sin SQL. Los JSON de recorrido no contienen claves, códigos, JWT, parámetros SQL,
correos reales ni cuerpos de respuesta. Las fechas de sus nombres son UTC.

## Pendiente manual

1. Importar las colecciones y el Environment en Postman Desktop.
2. Levantar un laboratorio nuevo con laboratorio_http.py, configurar valores
   locales privados y ejecutar los 30 pasos en Runner.
3. Verificar la ejecución real de los `pm.test` y conservar capturas sin secretos.
4. Validar el catálogo por carpetas sobre recursos con las precondiciones indicadas;
   no atribuirle cobertura de aceptación integral por existir sus solicitudes.

Consentimiento/provisión/inicio siguen solo en LAB. Repeticiones, reporte y avisos
de notas oficiales permanecen cerrados; Evaluation no tiene rutas registradas.
Ninguna aprobación académica se deriva de este laboratorio.
