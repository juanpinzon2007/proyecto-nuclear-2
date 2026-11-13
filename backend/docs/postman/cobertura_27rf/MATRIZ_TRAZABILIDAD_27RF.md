# Matriz de trazabilidad RF-01 a RF-27

Fuente literal: `REQUISITOS_FUENTE.json`, PDF central pp. 4–5 con SHA-256. Se conservan las decisiones posteriores y sus discrepancias; no se declara aprobación institucional por una implementación o fixture.

APROBADO identifica aceptación técnica del MVP confirmado por el equipo, mediante app.main y PostgreSQL17 de laboratorio. La aprobación académica o externa se registra por separado. La activación productiva del consentimiento requiere una fuente oficial aprobada. BLOQUEADO puede contener operaciones técnicas aprobadas: no representa cumplimiento integral. FALLIDO conserva un defecto observado; NO EJECUTADO no tiene veredicto.

Cada carpeta se prepara en una base nueva. Las precondiciones repetidas por RF son solicitudes reales, pero no se contabilizan como funcionalidades distintas. Un HTTP negativo esperado es aceptación de seguridad; 503 no es un caso positivo de funcionalidad.

| RF | Requisito | Aceptación técnica MVP | HTTP ejecutadas | pm.test | Evidencia / detalle | Aceptación académica o externa |
|---|---|---|---:|---:|---|---|
| RF-01 | Autenticar estudiantes | **APROBADO** | 6 | 18 | [RF-01](RF-01.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-02 | Controlar acceso por rol | **APROBADO** | 15 | 49 | [RF-02](RF-02.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-03 | Administrar docentes, roles y permisos | **APROBADO** | 26 | 85 | [RF-03](RF-03.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-04 | Asociar espacio académico y estudiantes | **APROBADO** | 14 | 46 | [RF-04](RF-04.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-05 | Registrar estructura académica del caso | **APROBADO** | 15 | 49 | [RF-05](RF-05.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-06 | Registrar contextos y preguntas por escenario | **APROBADO** | 15 | 49 | [RF-06](RF-06.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-07 | Administrar preguntas y respuestas | **APROBADO** | 15 | 49 | [RF-07](RF-07.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-08 | Justificar respuestas correctas e incorrectas | **APROBADO** | 15 | 49 | [RF-08](RF-08.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-09 | Validar estructura y rúbrica del caso | **APROBADO** | 16 | 53 | [RF-09](RF-09.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-10 | Responder y modificar respuestas | **APROBADO** | 32 | 141 | [RF-10](RF-10.md) | MVP confirmado por el equipo, una pregunta por escena, sin ciclos alcanzables. Conciliar el documento original con la inmutabilidad posterior. |
| RF-11 | Registrar respuestas y mostrar progreso | **APROBADO** | 32 | 141 | [RF-11](RF-11.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-12 | Registrar inicio y fin de participación | **APROBADO** | 34 | 147 | [RF-12](RF-12.md) | Documento institucional de consentimiento todavía sin aprobación verificable. Main solo se habilita con paquetes confiables del operador; el paquete sintético se limita a LABORATORIO. |
| RF-13 | Calcular nota con rúbrica | **APROBADO** | 32 | 141 | [RF-13](RF-13.md) | Orden docente y recuperación confirmadas por el equipo. La fórmula del motor conserva su procedencia y requiere conciliación documental académica. |
| RF-14 | Mostrar resultado y feedback final | **APROBADO** | 19 | 68 | [RF-14](RF-14.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-15 | Consultar participaciones de estudiantes | **APROBADO** | 42 | 174 | [RF-15](RF-15.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-16 | Descargar reporte de participación | **APROBADO** | 15 | 52 | [RF-16](RF-16.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-17 | Registrar y asociar la rúbrica | **APROBADO** | 15 | 49 | [RF-17](RF-17.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-18 | Agendar fecha, horario y condiciones | **APROBADO** | 12 | 39 | [RF-18](RF-18.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-19 | Administrar estados de sesiones | **APROBADO** | 17 | 54 | [RF-19](RF-19.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-20 | Asignar y validar código de autorización | **APROBADO** | 17 | 57 | [RF-20](RF-20.md) | Proveedor SMTP institucional pendiente de configuración y validación externa. |
| RF-21 | Notificar convocatoria y cambios | **APROBADO** | 17 | 57 | [RF-21](RF-21.md) | Proveedor SMTP institucional pendiente de configuración y validación externa. |
| RF-22 | Restringir ingreso tardío | **APROBADO** | 6 | 18 | [RF-22](RF-22.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-23 | Controlar tiempo máximo | **APROBADO** | 32 | 141 | [RF-23](RF-23.md) | Inicio técnico acreditado con configuración explícita LAB. La activación productiva requiere consentimiento institucional aprobado y configuración del operador. |
| RF-24 | Evaluar incompletos y ausencias | **APROBADO** | 18 | 62 | [RF-24](RF-24.md) | Evaluación técnica por orden docente confirmada. No se atribuye a la profesora la política técnica del equipo. |
| RF-25 | Autorizar repetición excepcional | **APROBADO** | 40 | 168 | [RF-25](RF-25.md) | MVP confirmado para el mismo caso y versión histórica, permiso individual de un uso. Vínculos entre casos distintos fuera de este alcance. Activación productiva condicionada al consentimiento institucional. |
| RF-26 | Registrar feedback general docente | **APROBADO** | 38 | 161 | [RF-26](RF-26.md) | Contrato vigente conservado; aprobación nueva no atribuida. |
| RF-27 | Notificar calificaciones y feedback | **APROBADO** | 21 | 73 | [RF-27](RF-27.md) | Contrato vigente conservado; aprobación nueva no atribuida. |

**Total: 27 APROBADOS, 0 BLOQUEADOS, 0 FALLIDOS y 0 NO EJECUTADOS.** 576 solicitudes ejecutadas y 2190 aserciones pm.test; La aceptación académica o externa conserva sus condiciones explícitas en la última columna.

La matriz CSV contiene una fila por caso, método, endpoint, aserciones reales, veredicto, evidencia nominal y referencias pytest acreditadas. Las fichas PT-DCP-01 no se renumeraron: los identificadores PM son nuevos, con conciliación documental pendiente donde no hay ficha equivalente.
