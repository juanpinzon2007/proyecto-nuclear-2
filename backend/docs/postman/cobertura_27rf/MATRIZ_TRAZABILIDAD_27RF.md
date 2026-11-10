# Matriz de trazabilidad RF-01 a RF-27

Fuente literal: `REQUISITOS_FUENTE.json`, PDF central pp. 4–5 con SHA-256. Se conservan las decisiones posteriores y sus discrepancias; no se declara aprobación institucional por una implementación o fixture.

APROBADO significa aceptación funcional del RF en el alcance académico vigente documentado, mediante backend real y PG17 de laboratorio. No acredita despliegue permanente. BLOQUEADO puede contener operaciones técnicas aprobadas: no representa cumplimiento integral. FALLIDO conserva un defecto observado; NO EJECUTADO no tiene veredicto.

Cada carpeta se prepara en una base nueva. Las precondiciones repetidas por RF son solicitudes reales, pero no se contabilizan como funcionalidades distintas. Un HTTP negativo esperado es aceptación de seguridad; 503 no es un caso positivo de funcionalidad.

| RF | Requisito | Veredicto integral | HTTP ejecutadas | pm.test | Evidencia / detalle |
|---|---|---|---:|---:|---|
| RF-01 | Autenticar estudiantes | **APROBADO** | 6 | 18 | [RF-01](RF-01.md) |
| RF-02 | Controlar acceso por rol | **APROBADO** | 15 | 49 | [RF-02](RF-02.md) |
| RF-03 | Administrar docentes, roles y permisos | **BLOQUEADO** | 17 | 54 | [RF-03](RF-03.md) |
| RF-04 | Asociar espacio académico y estudiantes | **BLOQUEADO** | 16 | 53 | [RF-04](RF-04.md) |
| RF-05 | Registrar estructura académica del caso | **APROBADO** | 15 | 49 | [RF-05](RF-05.md) |
| RF-06 | Registrar contextos y preguntas por escenario | **APROBADO** | 15 | 49 | [RF-06](RF-06.md) |
| RF-07 | Administrar preguntas y respuestas | **APROBADO** | 15 | 49 | [RF-07](RF-07.md) |
| RF-08 | Justificar respuestas correctas e incorrectas | **APROBADO** | 15 | 49 | [RF-08](RF-08.md) |
| RF-09 | Validar estructura y rúbrica del caso | **APROBADO** | 16 | 53 | [RF-09](RF-09.md) |
| RF-10 | Responder y modificar respuestas | **BLOQUEADO** | 32 | 141 | [RF-10](RF-10.md) |
| RF-11 | Registrar respuestas y mostrar progreso | **APROBADO** | 32 | 141 | [RF-11](RF-11.md) |
| RF-12 | Registrar inicio y fin de participación | **BLOQUEADO** | 32 | 141 | [RF-12](RF-12.md) |
| RF-13 | Calcular nota con rúbrica | **BLOQUEADO** | 32 | 141 | [RF-13](RF-13.md) |
| RF-14 | Mostrar resultado y feedback final | **BLOQUEADO** | 15 | 52 | [RF-14](RF-14.md) |
| RF-15 | Consultar participaciones de estudiantes | **APROBADO** | 42 | 174 | [RF-15](RF-15.md) |
| RF-16 | Descargar reporte de participación | **APROBADO** | 15 | 52 | [RF-16](RF-16.md) |
| RF-17 | Registrar y asociar la rúbrica | **APROBADO** | 15 | 49 | [RF-17](RF-17.md) |
| RF-18 | Agendar fecha, horario y condiciones | **APROBADO** | 12 | 39 | [RF-18](RF-18.md) |
| RF-19 | Administrar estados de sesiones | **APROBADO** | 17 | 54 | [RF-19](RF-19.md) |
| RF-20 | Asignar y validar código de autorización | **BLOQUEADO** | 16 | 53 | [RF-20](RF-20.md) |
| RF-21 | Notificar convocatoria y cambios | **BLOQUEADO** | 16 | 53 | [RF-21](RF-21.md) |
| RF-22 | Restringir ingreso tardío | **APROBADO** | 6 | 18 | [RF-22](RF-22.md) |
| RF-23 | Controlar tiempo máximo | **BLOQUEADO** | 32 | 141 | [RF-23](RF-23.md) |
| RF-24 | Evaluar incompletos y ausencias | **BLOQUEADO** | 18 | 62 | [RF-24](RF-24.md) |
| RF-25 | Autorizar repetición excepcional | **BLOQUEADO** | 35 | 150 | [RF-25](RF-25.md) |
| RF-26 | Registrar feedback general docente | **APROBADO** | 38 | 161 | [RF-26](RF-26.md) |
| RF-27 | Notificar calificaciones y feedback | **APROBADO** | 21 | 73 | [RF-27](RF-27.md) |

**Total: 16 APROBADOS, 11 BLOQUEADOS, 0 FALLIDOS y 0 NO EJECUTADOS.** 556 solicitudes ejecutadas y 2118 aserciones pm.test; no significa 27 RF aprobados.

La matriz CSV contiene una fila por caso, método, endpoint, aserciones reales, veredicto, evidencia nominal y referencias pytest acreditadas. Las fichas PT-DCP-01 no se renumeraron: los identificadores PM son nuevos, con conciliación documental pendiente donde no hay ficha equivalente.


## Antecedentes preservados del checkpoint RF-10

Las siguientes secciones pertenecen a incrementos anteriores; la ejecución de Fase 3 utilizó seleccion_final, 553 solicitudes y 2107 aserciones; son antecedentes históricos.

## Complemento main condicionado RF-12/RF-23/RF-25

La presente matriz usa la nueva regresión `evidencias/participation_fase1_20261109T215053Z/regresion_postman_27/`. Se conserva 16 APROBADOS/11 BLOQUEADOS. La composición principal de consentimiento e inicio permanece cerrada sin proveedores productivos aprobados. Las 79 solicitudes complementarias main (políticas positivas exclusivamente LAB y controles sin ellas) se trazan individualmente en `../participation_fase1/matriz_fase1.csv`; su informe es `backend/docs/PARTICIPATION_FASE1_MAIN_CONDICIONADO.md`. No se atribuye aprobación integral a esos tres RF ni se suman las ejecuciones.


## Continuidad RF-10: contrato Angular y recorrido main

Se conserva RF-10 **BLOQUEADO** integralmente. La aclaración de respuestas inmutables prevalece sobre el texto original; no se reabre PUT/PATCH. Las reglas de varias preguntas por escena, ciclos y revisitas siguen pendientes. Los estados de los otros 26 RF no cambian: total 16 APROBADOS y 11 BLOQUEADOS.

Nuevo complemento: `backend/docs/postman/rf10_main/` y `backend/docs/RF10_CONTRATO_ANGULAR.md`. 21 solicitudes **solo app.main**, 76 aserciones Newman aprobadas y lectura SQL independiente. El intento y sus relaciones se preparan previamente SOLO LAB; no se acredita inicio productivo ni aprobación del consentimiento. La maestra RF-10 también se volvió a ejecutar: 32 solicitudes/141 aserciones, sin fallos técnicos, conservando su separación de 28 operaciones main y cuatro LAB. No se suman ambos recorridos ni se afirma reejecución de los demás RF en Postman.

Evidencia nueva: `evidencias/rf10_contrato_20261109/newman_main_2/` y `newman_maestra_rf10/`. La trazabilidad nominal complementaria está en `backend/docs/postman/rf10_main/matriz_rf10_main.csv`. El único cambio de producción declara los errores HTTP ya existentes en OpenAPI, incluido el esquema real de 422; no añade endpoints ni cambia políticas.


## Fase 4 — RF04: alcance vigente

Ejecución nueva: evidencias/rf04_fase4_20261109/newman_27/. 556 solicitudes / 2118 pm.test, cero fallos técnicos, 16 APROBADOS y 11 BLOQUEADOS. RF04: 16 solicitudes / 53 aserciones; sigue BLOQUEADO. GET /scheduling/espacios (main) limita el listado a grants explícitos; las nuevas solicitudes PM-RF-04-10/11/12 acreditan selección propia, exclusión del espacio ajeno y rechazo sin JWT.

No se afirma asociación integral: rf_sesion se crea por HTTP, pero las convocatorias se demuestran sobre rf_sesion_convocatoria, otra sesión preparada con asignación en LAB. Falta el contrato productivo de fecha_limite_ingreso, intentos_base y estado del puente académico; no se promueven defaults/fixtures a políticas. No hay nueva ruta ni migración. Informe: backend/docs/RF04_SELECCION_ACADEMICA_Y_BLOQUEOS.md. General final nueva:2525 aprobadas/38 omitidas/cero fallos o errores; primera general de dos fallos unitarios preservada y corregida sin relajar HTTP esperados. No sumar ejecuciones.
