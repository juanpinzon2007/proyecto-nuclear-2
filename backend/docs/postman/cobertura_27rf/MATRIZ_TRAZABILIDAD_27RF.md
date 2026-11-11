# Matriz de trazabilidad RF-01 a RF-27

Fuente literal: `REQUISITOS_FUENTE.json`, PDF central pp. 4–5 con SHA-256. Se conservan las decisiones posteriores y sus discrepancias; no se declara aprobación institucional por una implementación o fixture.

APROBADO significa aceptación funcional del RF en el alcance académico vigente documentado, mediante backend real y PG17 de laboratorio. No acredita despliegue permanente. BLOQUEADO puede contener operaciones técnicas aprobadas: no representa cumplimiento integral. FALLIDO conserva un defecto observado; NO EJECUTADO no tiene veredicto.

Cada carpeta se prepara en una base nueva. Las precondiciones repetidas por RF son solicitudes reales, pero no se contabilizan como funcionalidades distintas. Un HTTP negativo esperado es aceptación de seguridad; 503 no es un caso positivo de funcionalidad.

| RF | Requisito | Veredicto integral | HTTP ejecutadas | pm.test | Evidencia / detalle |
|---|---|---|---:|---:|---|
| RF-01 | Autenticar estudiantes | **APROBADO** | 6 | 18 | [RF-01](RF-01.md) |
| RF-02 | Controlar acceso por rol | **APROBADO** | 15 | 49 | [RF-02](RF-02.md) |
| RF-03 | Administrar docentes, roles y permisos | **APROBADO** | 26 | 85 | [RF-03](RF-03.md) |
| RF-04 | Asociar espacio académico y estudiantes | **APROBADO** | 14 | 46 | [RF-04](RF-04.md) |
| RF-05 | Registrar estructura académica del caso | **APROBADO** | 15 | 49 | [RF-05](RF-05.md) |
| RF-06 | Registrar contextos y preguntas por escenario | **APROBADO** | 15 | 49 | [RF-06](RF-06.md) |
| RF-07 | Administrar preguntas y respuestas | **APROBADO** | 15 | 49 | [RF-07](RF-07.md) |
| RF-08 | Justificar respuestas correctas e incorrectas | **APROBADO** | 15 | 49 | [RF-08](RF-08.md) |
| RF-09 | Validar estructura y rúbrica del caso | **APROBADO** | 16 | 53 | [RF-09](RF-09.md) |
| RF-10 | Responder y modificar respuestas | **BLOQUEADO** | 32 | 141 | [RF-10](RF-10.md) |
| RF-11 | Registrar respuestas y mostrar progreso | **APROBADO** | 32 | 141 | [RF-11](RF-11.md) |
| RF-12 | Registrar inicio y fin de participación | **BLOQUEADO** | 32 | 141 | [RF-12](RF-12.md) |
| RF-13 | Calcular nota con rúbrica | **BLOQUEADO** | 32 | 141 | [RF-13](RF-13.md) |
| RF-14 | Mostrar resultado y feedback final | **APROBADO** | 19 | 68 | [RF-14](RF-14.md) |
| RF-15 | Consultar participaciones de estudiantes | **APROBADO** | 42 | 174 | [RF-15](RF-15.md) |
| RF-16 | Descargar reporte de participación | **APROBADO** | 15 | 52 | [RF-16](RF-16.md) |
| RF-17 | Registrar y asociar la rúbrica | **APROBADO** | 15 | 49 | [RF-17](RF-17.md) |
| RF-18 | Agendar fecha, horario y condiciones | **APROBADO** | 12 | 39 | [RF-18](RF-18.md) |
| RF-19 | Administrar estados de sesiones | **APROBADO** | 17 | 54 | [RF-19](RF-19.md) |
| RF-20 | Asignar y validar código de autorización | **APROBADO** | 17 | 57 | [RF-20](RF-20.md) |
| RF-21 | Notificar convocatoria y cambios | **APROBADO** | 17 | 57 | [RF-21](RF-21.md) |
| RF-22 | Restringir ingreso tardío | **APROBADO** | 6 | 18 | [RF-22](RF-22.md) |
| RF-23 | Controlar tiempo máximo | **BLOQUEADO** | 32 | 141 | [RF-23](RF-23.md) |
| RF-24 | Evaluar incompletos y ausencias | **BLOQUEADO** | 18 | 62 | [RF-24](RF-24.md) |
| RF-25 | Autorizar repetición excepcional | **BLOQUEADO** | 35 | 150 | [RF-25](RF-25.md) |
| RF-26 | Registrar feedback general docente | **APROBADO** | 38 | 161 | [RF-26](RF-26.md) |
| RF-27 | Notificar calificaciones y feedback | **APROBADO** | 21 | 73 | [RF-27](RF-27.md) |

**Total: 21 APROBADOS, 6 BLOQUEADOS, 0 FALLIDOS y 0 NO EJECUTADOS.** 569 solicitudes ejecutadas y 2166 aserciones pm.test; no significa 27 RF aprobados.

La matriz CSV contiene una fila por caso, método, endpoint, aserciones reales, veredicto, evidencia nominal y referencias pytest acreditadas. Las fichas PT-DCP-01 no se renumeraron: los identificadores PM son nuevos, con conciliación documental pendiente donde no hay ficha equivalente.
