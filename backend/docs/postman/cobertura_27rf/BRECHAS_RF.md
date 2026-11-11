# Brechas RF-01 a RF-27

Las capacidades parciales se ejecutaron, pero no se aprueba íntegramente su RF. Ningún 503 fue aceptado como cumplimiento.

- **RF-03 — Administrar docentes, roles y permisos:** Alta, consulta y validación del perfil del catálogo están acreditadas. Falta precisar la configuración/asignación operativa de permisos globales por rol frente a excepciones individuales. Multirrol y DOCENTE ADMINISTRADOR no se presuponen requisitos expresos del RF original.
- **RF-04 — Asociar espacio académico y estudiantes:** Asociaciones y grants explícitos requieren preparación administrativa; falta una API aprobada de vinculación docente/grupo/asignación. No se confunde agendar sesión con crear ese vínculo.
- **RF-10 — Responder y modificar respuestas:** El PDF RF-10/RN-10/11 permite modificar; la profesora aclaró después respuestas inmutables. Se prueba la inmutabilidad vigente ya confirmada; faltan conciliar el documento y definir recorridos con varias preguntas/ciclos/revisitas, no reabrir PUT.
- **RF-12 — Registrar inicio y fin de participación:** Composición main condicionada presente; faltan documento institucional aprobado y políticas productivas definitivas de provisión/inicio. El recorrido positivo con puertos LAB no acredita disponibilidad productiva ni feedback por pregunta completo.
- **RF-13 — Calcular nota con rúbrica:** Cálculo/persistencia técnica PREGUNTAS_100_V1 acreditados en main. Conciliar UC05 con comando docente separado y la aplicabilidad a otras rúbricas/recorridos. La regla histórica distinta devuelve 503 sin nota; no se transforma ni se exige publicación oficial como parte de RF13. Auditoría nueva: RF13_AUDITORIA_Y_DTO_PROGRAMACION_20261110.md.
- **RF-20 — Asignar y validar código de autorización:** Código de una sola entrega y hash sí; falta entrega externa segura al estudiante. Una notificación interna no es correo.
- **RF-21 — Notificar convocatoria y cambios:** No existe proveedor/remitente/URL institucional y recuperación del código para envío seguro. No se inventa SMTP ni se considera enviado un correo.
- **RF-23 — Controlar tiempo máximo:** Contador y vencimiento de intentos existentes tienen pruebas; el inicio productivo que lo activa permanece cerrado. Se acredita recorrido LAB, no requisito integral productivo.
- **RF-24 — Evaluar incompletos y ausencias:** Ausencia explícita y parcial técnicos demostrables; políticas propuestas no se presentan como aprobación institucional ni ausencia inferida.
- **RF-25 — Autorizar repetición excepcional:** Permiso individual de un uso disponible; consumo por inicio productivo y vinculación de caso distinto siguen pendientes.

## Decisiones y límites que no se corrigen con pruebas verdes

- RF-10: el PDF y RN-10/11 describen modificación; la aclaración posterior de la profesora exige inmutabilidad. Se conserva el comportamiento vigente y se solicita conciliación documental, no reabrir PUT. Fuente: FASE_8B_RESPUESTAS_INMUTABLES.md.
- RF-22: se conserva sala de espera/concesión de admisión aprobada por el equipo; no se inventa un umbral tardío ni se recupera la anticipación descartada. Fuente: DECISIONES_FUNCIONALES_RF22.md y SALA_ESPERA_ADMISION_DISENO.md.
- RF-13/RF-24: fórmula técnica, ausencia y cierre parcial se prueban como reglas del equipo; no se atribuyen aprobaciones institucionales ausentes. Fuente: CONTRATO_FUNCIONAL_EVALUATION_PROPUESTO_20261107.md y matriz vigente.
- RF-20/RF-21: se exige un contrato y proveedor de correo seguro; no se sustituye entrega externa por una fila INTERNA ni se fabrican códigos recuperables.
- Consentimiento: se necesita la fuente institucional publicada y su composición productiva. Un documento sintético y una clase InicioLaboratorio no satisfacen esa aprobación.

## Fallos reales conservados y corrección

Los dos primeros ciclos RF-07 rechazaron correctamente una opción de orden 3 duplicada por el generador. Se corrigió la copia de la fixture; no se cambió el esperado 200 de una edición válida. El primer ciclo integral falló al convocar sobre EN_CURSO (RF-04/18/20/21) y preparar una ausencia después del cierre (RF-24). Se corrigieron exclusivamente precondiciones/orden de laboratorio. Los JSON, JUnit y logs diagnósticos se conservan. Ningún archivo productivo se modificó para evitar esos rechazos.

Las pruebas complementarias de permisos, concurrencia, rollback y guards PostgreSQL se conservan en los JUnit de pytest; no se presentan como capturas de Postman ni se suman sus conteos con pm.test.


## Antecedentes preservados del checkpoint RF-10

Las siguientes secciones pertenecen a incrementos anteriores; la ejecución de Fase 3 utilizó seleccion_final, 553 solicitudes y 2107 aserciones; son antecedentes históricos.

## Continuidad RF-10: contrato Angular y recorrido main

Se conserva RF-10 **BLOQUEADO** integralmente. La aclaración de respuestas inmutables prevalece sobre el texto original; no se reabre PUT/PATCH. Las reglas de varias preguntas por escena, ciclos y revisitas siguen pendientes. Los estados de los otros 26 RF no cambian: total 16 APROBADOS y 11 BLOQUEADOS.

Nuevo complemento: `backend/docs/postman/rf10_main/` y `backend/docs/RF10_CONTRATO_ANGULAR.md`. 21 solicitudes **solo app.main**, 76 aserciones Newman aprobadas y lectura SQL independiente. El intento y sus relaciones se preparan previamente SOLO LAB; no se acredita inicio productivo ni aprobación del consentimiento. La maestra RF-10 también se volvió a ejecutar: 32 solicitudes/141 aserciones, sin fallos técnicos, conservando su separación de 28 operaciones main y cuatro LAB. No se suman ambos recorridos ni se afirma reejecución de los demás RF en Postman.

Evidencia nueva: `evidencias/rf10_contrato_20261109/newman_main_2/` y `newman_maestra_rf10/`. La trazabilidad nominal complementaria está en `backend/docs/postman/rf10_main/matriz_rf10_main.csv`. El único cambio de producción declara los errores HTTP ya existentes en OpenAPI, incluido el esquema real de 422; no añade endpoints ni cambia políticas.


## Fase 4 — RF04: alcance vigente

Ejecución nueva: evidencias/rf04_fase4_20261109/newman_27/. 556 solicitudes / 2118 pm.test, cero fallos técnicos, 16 APROBADOS y 11 BLOQUEADOS. RF04: 16 solicitudes / 53 aserciones; sigue BLOQUEADO. GET /scheduling/espacios (main) limita el listado a grants explícitos; las nuevas solicitudes PM-RF-04-10/11/12 acreditan selección propia, exclusión del espacio ajeno y rechazo sin JWT.

No se afirma asociación integral: rf_sesion se crea por HTTP, pero las convocatorias se demuestran sobre rf_sesion_convocatoria, otra sesión preparada con asignación en LAB. Falta el contrato productivo de fecha_limite_ingreso, intentos_base y estado del puente académico; no se promueven defaults/fixtures a políticas. No hay nueva ruta ni migración. Informe: backend/docs/RF04_SELECCION_ACADEMICA_Y_BLOQUEOS.md. General final nueva:2525 aprobadas/38 omitidas/cero fallos o errores; primera general de dos fallos unitarios preservada y corregida sin relajar HTTP esperados. No sumar ejecuciones.


## Cierre RF14 Fase7 — evidencia y límites

RF14 APROBADO para consulta de resultados válidos existentes, con política funcional de visibilidad confirmada.19 HTTP/68 pm.test; positivo de nota/acierto/error/explicación, recarga y privacidad. No se obliga a publicar ni se calcula desde GET. Nuevo404 cuando falta cálculo, sin DML.13 focales y180 relacionadas; general nueva2538 aprobadas/38 omitidas/cero fallos o errores.

Selección final27RF:evidencias/rf14_fase7_20261110/seleccion_final/,560HTTP/2134aserciones;17 APROBADOS y10 BLOQUEADOS. Solo RF14 cambia de estado. RF13 continúa BLOQUEADO y no se cambian inicio/repetición/RF04/DTO. Los antecedentes16/11 son históricos. El primer RF14Newman falló por redeclaración JS; se conserva y se sustituye por la nueva ejecución sin cambiar HTTP esperados.

Criterios y límites:backend/docs/RF14_CIERRE_CONTROLADO_20261110.md; contrato para Angular:backend/docs/RF14_CONTRATO_ANGULAR.md. MAIN no equivale a despliegue permanente; fixtures académicas son LAB, no aprobación de consentimiento ni de fórmulas fuera de alcance. Sin prueba de navegador.


## RF24 Fase9 — bloqueo preciso y alternativas

Parcial vencido, persistencia, autorización y ausencia confirmada/rectificada pasan la ejecución nueva sobre main/PG17; no se cambia su estado integral. Falta conciliar UC05 con el disparador docente y delimitar las rúbricas académicamente evaluables fuera de PREGUNTAS_100_V1. El cierre voluntario v2 conserva procedencia de propuesta técnica. No basta una ausencia0.00 o un503 para declarar APROBADO. Informe: `backend/docs/RF24_CIERRE_CONTROLADO_20261110.md`. RF20/RF21 evaluados como alternativas: hash y avisos internos existen, pero falta entrega externa segura del código y contrato/proveedor/remitente/URL de correo; no se declaran libres de dependencias.
