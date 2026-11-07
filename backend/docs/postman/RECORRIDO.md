# Orden del recorrido de laboratorio

Ejecutar una sola iteración, sobre un laboratorio nuevo. No es un recorrido productivo completo: consentimiento e inicio usan servidor separado y políticas LAB explícitas.

| Paso | Operación/superficie | Método | URL | HTTP exacto |
|---|---|---|---|---|
| 1 | MAIN — login admin | POST | `{{base_url}}/api/v1/identity/auth/personal` | 200 |
| 2 | MAIN — login docente | POST | `{{base_url}}/api/v1/identity/auth/personal` | 200 |
| 3 | MAIN — listar docentes | GET | `{{base_url}}/api/v1/identity/docentes` | 200 |
| 4 | MAIN — login estudiante | POST | `{{base_url}}/api/v1/identity/auth/estudiantes` | 200 |
| 5 | MAIN — login ajeno | POST | `{{base_url}}/api/v1/identity/auth/estudiantes` | 200 |
| 6 | MAIN — identidad privada | GET | `{{base_url}}/api/v1/identity/me` | 200 |
| 7 | MAIN — admisión persistida en preparación LAB | GET | `{{base_url}}/scheduling/convocatorias/{{convocatoria_id}}/admision` | 200 |
| 8 | MAIN — validar ingreso sin crear P/I | POST | `{{base_url}}/scheduling/validar-ingreso` | 200 |
| 9 | LAB AISLADA — documento sintético versionado | GET | `{{base_url_laboratorio}}/api/v1/identity/convocatorias/{{convocatoria_id}}/asignaciones/{{id_asignacion}}/consentimiento` | 200 |
| 10 | LAB AISLADA — aceptación explícita LAB | POST | `{{base_url_laboratorio}}/api/v1/identity/convocatorias/{{convocatoria_id}}/asignaciones/{{id_asignacion}}/consentimiento/aceptacion` | 200 |
| 11 | LAB AISLADA — inicio transaccional LAB | POST | `{{base_url_laboratorio}}/api/v1/convocatorias/{{convocatoria_id}}/intentos` | 201 |
| 12 | LAB AISLADA — inicio repetido sin duplicados | POST | `{{base_url_laboratorio}}/api/v1/convocatorias/{{convocatoria_id}}/intentos` | 409 |
| 13 | MAIN — progreso ajeno rechazado | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/progress` | 403 |
| 14 | MAIN — progreso inicial | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/progress` | 200 |
| 15 | MAIN — escenario actual 1 | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario` | 200 |
| 16 | MAIN — primera selección 1 | POST | `{{base_url}}/api/v1/attempts/{{id_intento}}/decisions/{{id_decision}}` | 201 |
| 17 | MAIN — segunda selección rechazada | POST | `{{base_url}}/api/v1/attempts/{{id_intento}}/decisions/{{id_decision}}` | 409 |
| 18 | MAIN — escenario actual 2 | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario` | 200 |
| 19 | MAIN — primera selección 2 | POST | `{{base_url}}/api/v1/attempts/{{id_intento}}/decisions/{{id_decision}}` | 201 |
| 20 | MAIN — ruta terminal | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario` | 200 |
| 21 | MAIN — progreso completo privado | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/progress` | 200 |
| 22 | MAIN — cierre ajeno rechazado | POST | `{{base_url}}/api/v1/attempts/{{id_intento}}/finish` | 403 |
| 23 | MAIN — cierre titular | POST | `{{base_url}}/api/v1/attempts/{{id_intento}}/finish` | 200 |
| 24 | MAIN — cierre idempotente | POST | `{{base_url}}/api/v1/attempts/{{id_intento}}/finish` | 200 |
| 25 | MAIN — escenario cerrado | GET | `{{base_url}}/api/v1/attempts/{{id_intento}}/current-scenario` | 409 |
| 26 | MAIN — feedback individual docente | POST | `{{base_url}}/api/v1/identity/seguimiento/participaciones/{{id_participacion}}/feedback` | 201 |
| 27 | MAIN — consulta privada feedback | GET | `{{base_url}}/api/v1/identity/seguimiento/participaciones/{{id_participacion}}/feedback` | 200 |
| 28 | MAIN — feedback ajeno rechazado | GET | `{{base_url}}/api/v1/identity/seguimiento/participaciones/{{id_participacion}}/feedback` | 403 |
| 29 | MAIN — avisos internos propios | GET | `{{base_url}}/scheduling/notificaciones?destinatario_id={{estudiante_id}}` | 200 |
| 30 | MAIN — reporte oficial cerrado | GET | `{{base_url}}/api/v1/identity/seguimiento/sesiones/{{sesion_id}}/reporte` | 503 |

Los logins capturan tokens en pm.variables; la consulta de documento captura versión, referencia y huella; aceptación captura id_consentimiento; inicio captura id_participacion/id_intento; cada escenario captura únicamente la pregunta/opción actualmente habilitadas.
No se crean opciones o respuestas ficticias, ni se calcula/publica una nota. El primer camino seleccionado corresponde al grafo SQL real del fixture.
La preparación administrativa previa incluye espera y habilitación docente; el recorrido verifica su concesión persistida. No se atribuye a app.main la creación del intento realizada en la superficie LAB.
