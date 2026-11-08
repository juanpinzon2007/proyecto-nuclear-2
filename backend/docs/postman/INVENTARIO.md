# Endpoints registrados en app.main

Fuente: openapi_main.json y dependencias de los routers. No acredita despliegue ni ejecución HTTP.

| Método | Ruta | Rol | Estado | Dependencias |
|---|---|---|---|---|
| GET | /api/v1/cases | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| POST | /api/v1/cases | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| GET | /api/v1/cases/{version_id} | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| PUT | /api/v1/cases/{version_id} | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| POST | /api/v1/cases/{version_id}/publish | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| POST | /api/v1/cases/{version_id}/archive | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| GET | /api/v1/cases/{version_id}/graph | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| PUT | /api/v1/cases/{version_id}/graph | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables. |
| POST | /api/v1/identity/auth/estudiantes | PUBLICO | REGISTRADO_CON_PRECONDICIONES | Ninguna para acceder; el login valida credenciales y cuenta persistente. |
| POST | /api/v1/identity/auth/personal | PUBLICO | REGISTRADO_CON_PRECONDICIONES | Ninguna para acceder; el login valida credenciales y cuenta persistente. |
| GET | /api/v1/identity/me | AUTENTICADO | REGISTRADO_CON_PRECONDICIONES | Cuenta activa y rol vigente desde PostgreSQL. |
| POST | /api/v1/identity/docentes | ADMINISTRADOR | REGISTRADO_CON_PRECONDICIONES | Cuentas de Identity; no concede ámbito académico ni DOCENTE ADMINISTRADOR. |
| GET | /api/v1/identity/docentes | ADMINISTRADOR | REGISTRADO_CON_PRECONDICIONES | Cuentas de Identity; no concede ámbito académico ni DOCENTE ADMINISTRADOR. |
| PUT | /api/v1/identity/docentes/{id_docente}/autorizaciones | ADMINISTRADOR | REGISTRADO_CON_PRECONDICIONES | Cuentas de Identity; no concede ámbito académico ni DOCENTE ADMINISTRADOR. |
| GET | /api/v1/identity/seguimiento/casos | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales. |
| GET | /api/v1/identity/seguimiento/participaciones/{id_participacion} | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales. |
| GET | /api/v1/identity/seguimiento/casos/{id_caso}/participaciones | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales. |
| GET | /api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte | DOCENTE | REGISTRADO_BLOQUEADO | Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales. |
| POST | /api/v1/identity/seguimiento/participaciones/{id_participacion}/feedback | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales. |
| GET | /api/v1/identity/seguimiento/participaciones/{id_participacion}/feedback | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | Participación propia y condiciones de visibilidad; no muestra notas ni correcciones. |
| POST | /api/v1/identity/excepciones/repeticiones | DOCENTE | REGISTRADO_BLOQUEADO | Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales. |
| GET | /scheduling/espacios | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| POST | /scheduling/espacios | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| GET | /scheduling/sesiones | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| POST | /scheduling/sesiones | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| GET | /scheduling/sesiones/{sesion_id} | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| POST | /scheduling/sesiones/{sesion_id}/estado | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| GET | /scheduling/sesiones/{sesion_id}/convocatorias | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| POST | /scheduling/sesiones/{sesion_id}/convocatorias | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| DELETE | /scheduling/sesiones/{sesion_id}/convocatorias/{convocatoria_id} | DOCENTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| POST | /scheduling/validar-ingreso | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING, convocatoria propia y matrícula; ingreso exige concesión de admisión y EN_CURSO, nunca crea P/I. |
| GET | /scheduling/notificaciones | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING, convocatoria propia y matrícula; ingreso exige concesión de admisión y EN_CURSO, nunca crea P/I. |
| POST | /scheduling/calificaciones/notificar | DOCENTE | REGISTRADO_BLOQUEADO | Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual. |
| POST | /scheduling/convocatorias/{convocatoria_id}/espera | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING, convocatoria propia y matrícula; ingreso exige concesión de admisión y EN_CURSO, nunca crea P/I. |
| GET | /scheduling/convocatorias/{convocatoria_id}/admision | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | Identidad SCHEDULING, convocatoria propia y matrícula; ingreso exige concesión de admisión y EN_CURSO, nunca crea P/I. |
| GET | /scheduling/sesiones/{sesion_id}/evaluacion/preparacion | DOCENTE | REGISTRADO_CON_PRECONDICIONES | RF-13/RF-24/RF-16: preparación, no notas. Cuenta activa, identidades CASES/SCHEDULING inequívocas, sesión/caso/grupos propios y matrículas ciertas; zona histórica explícita. READ ONLY; publicable=false. |
| GET | /scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico | DOCENTE | REGISTRADO_CON_PRECONDICIONES | RF-13/RF-24: resultado técnico previamente persistido, no oficial. JWT/cuenta/rol y ámbito sesión/caso/grupos/participación/intento. REPEATABLE READ/READ ONLY; GET no genera resultados; 404 si no existe. |
| POST | /scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico | DOCENTE | REGISTRADO_CON_PRECONDICIONES | RF-13/RF-24: comando explícito sobre intento cerrado. Identidad/rol y ámbito persistentes bajo locks; UoW independiente del cierre. Idempotente 200; activo u otro motor 409; fallo 503 recuperable. Sin cuerpo ni puntajes del cliente, sin notas oficiales. |
| GET | /api/v1/attempts/{attempt_id}/current-scenario | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | JWT con convocatoria propia activa, matrícula, intento propio, versión histórica, zona explícita y condiciones temporales del caso de uso. |
| GET | /api/v1/attempts/{attempt_id}/progress | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | JWT con convocatoria propia activa, matrícula, intento propio, versión histórica, zona explícita y condiciones temporales del caso de uso. |
| POST | /api/v1/attempts/{attempt_id}/decisions/{decision_id} | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | JWT con convocatoria propia activa, matrícula, intento propio, versión histórica, zona explícita y condiciones temporales del caso de uso. |
| POST | /api/v1/attempts/{attempt_id}/finish | ESTUDIANTE | REGISTRADO_CON_PRECONDICIONES | JWT con convocatoria propia activa, matrícula, intento propio, versión histórica, zona explícita y condiciones temporales del caso de uso. |
| GET | /health | PUBLICO | REGISTRADO_CON_PRECONDICIONES | Ninguna para acceder; el login valida credenciales y cuenta persistente. |
| GET | /openapi.json | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| HEAD | /openapi.json | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| GET | /docs | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| HEAD | /docs | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| GET | /redoc | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| HEAD | /redoc | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| GET | /docs/oauth2-redirect | PUBLICO | DOCUMENTACION_AUTOMATICA |  |
| HEAD | /docs/oauth2-redirect | PUBLICO | DOCUMENTACION_AUTOMATICA |  |

Parámetros, cuerpos y esquemas de respuesta completos: inventario_endpoints.json y openapi_main.json.
Preparación y resultado técnico docente están registrados; no hay publicación oficial. Inicio/provisión/consentimiento no están en main. PUT de decisiones no está montado: 405, no una operación disponible.
OpenAPI no enumera todos los errores funcionales: revisar archivo/función/dependencias indicados y README.
