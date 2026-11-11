# Cierre técnico del MVP V3

Código acreditado `44081b7499afcbbcdb0e33c0cdfe9fc7f297814f` en codex/acelerado-candidato-20261110. Fecha UTC 2026-11-11T18:20:56.528190+00:00.

## Alcance y decisiones

El equipo confirmó una pregunta por escena, grafos sin ciclos alcanzables, respuestas inmutables, estado inicial pendiente para participación, cálculo técnico por orden docente después del cierre con recuperación, y repetición del mismo caso y versión histórica mediante permiso individual de un uso. Son decisiones del proyecto. Multipregunta, ciclos, revisitas y vínculos entre casos distintos conservan sus restricciones.

## Implementación

- Consentimiento versionado SQL cotejado con atestación canónica Ed25519 del operador, pin SHA-256, ámbito, vigencia, documento, evidencia de aprobación y asignación. La clave privada sintética existe solo en memoria de LAB.
- Inicio y provisión reutilizan el coordinador y la UoW. Archivo canónico del servidor con SHA-256, estado pendiente explícito, cupo base uno y permiso extra de un uso. JWT, matrícula, convocatoria, admisión causal, sesión, versión y consentimiento se revalidan dentro de la transacción.
- Corregida la segunda comprobación de consentimiento del adaptador de inicio, que reconstruía la fuente sin el proveedor de aprobación del coordinador. Ahora ambas comprobaciones reciben la misma fábrica autorizada.
- Auditoría INICIO_INTENTO_POLITICA en la misma transacción del intento y consumo del permiso. Registra identidad de la política y huella, con exclusión del código de acceso.
- Recuperación interna de cierres por selección expresa del docente. Reutiliza consulta autorizada y POST técnico existentes, con una transacción por intento. Una respuesta perdida después del commit se recupera por el resultado persistido. Los intentos activos o retirados permanecen pendientes.
- Configuración Compose opcional y .env.example sin valores de aprobación. Migraciones nuevas y tablas nuevas, cero. El resultado técnico conserva su fuente canónica.

## API y Angular

Los contratos HTTP existentes conservan método, ruta y DTO. GET consentimiento y GET/POST aceptación en /api/v1/identity/convocatorias/{convocatoria_id}/asignaciones/{id_asignacion}/consentimiento. POST /api/v1/convocatorias/{convocatoria_id}/intentos crea P e I juntos. No se expone provisión independiente en main.

Current-scenario, decisions, progress y finish conservan privacidad y respuestas inmutables. No se habilitan PUT/PATCH. El POST inicial devuelve 201. El replay con intento activo devuelve 409. Angular debe conservar el identificador recibido para recargar escenario y progreso. La recuperación de un inicio cuya primera respuesta se pierde antes de obtener su identificador no se acredita con estas pruebas. Un permiso consumido devuelve 403 después del cierre. La consulta del escenario conserva su DTO, sin añadir una versión inexistente. La repetición recupera los mismos UUID históricos.

La evaluación docente sigue usando POST/GET /scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico. La selección por lotes recuperable es interna. Readiness permite detectar los IDs pendientes y los clientes pueden repetir los POST individuales. Finish no calcula ni publica notas.

## Validación actual

Pytest general completa, 136 archivos en cuatro particiones disjuntas. 2682 aprobadas, 38 omitidas, 0 fallidas y 0 errores. Huellas de app/tests/Alembic estables durante la ejecución. Los logs conservan los motivos de omisión y las advertencias, incluida StarletteDeprecationWarning.

Newman completo de 27 RF, 576 solicitudes y 2190 aserciones. Todos los laboratorios informaron limpieza. Cada RF usó una base PG17 nueva. Los 21 requisitos anteriores conservan aceptación técnica. Los conteos focales y relacionados se informan por ejecución y no se suman a la general.

Focal integrada final de 45 aprobadas. Relacionada previa de 94 aprobadas. Consentimiento final de 17 focales y 101 relacionadas. Inicio final de 33 focales y 127 relacionadas. Recuperación de 13 focales y 150 relacionadas. Existen solapamientos entre estas ejecuciones y con la general.

Evidencias originales en C:/SPS/nuclear_v3_20261111. General en general_final/junit_general.xml y g0–g3/consola.log. Newman en newman_final/RF-xx/resultado.json y junit.xml. Se conservan los ciclos diagnósticos anteriores, incluido el esperado SQL incorrecto, las importaciones del preparador, el reloj congelado y la aserción numérica JavaScript.

## Estado por requisito

| RF | Implementación y aceptación técnica | Aceptación académica o externa | Evidencia |
|---|---|---|---|
| RF-01 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-01.md) |
| RF-02 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-02.md) |
| RF-03 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-03.md) |
| RF-04 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-04.md) |
| RF-05 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-05.md) |
| RF-06 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-06.md) |
| RF-07 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-07.md) |
| RF-08 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-08.md) |
| RF-09 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-09.md) |
| RF-10 | APROBADO MVP | MVP confirmado por el equipo, una pregunta por escena, sin ciclos alcanzables. Conciliar el documento original con la inmutabilidad posterior. | [HTTP y SQL](postman/cobertura_27rf/RF-10.md) |
| RF-11 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-11.md) |
| RF-12 | APROBADO MVP | Documento institucional de consentimiento todavía sin aprobación verificable. Main solo se habilita con paquetes confiables del operador; el paquete sintético se limita a LABORATORIO. | [HTTP y SQL](postman/cobertura_27rf/RF-12.md) |
| RF-13 | APROBADO MVP | Orden docente y recuperación confirmadas por el equipo. La fórmula del motor conserva su procedencia y requiere conciliación documental académica. | [HTTP y SQL](postman/cobertura_27rf/RF-13.md) |
| RF-14 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-14.md) |
| RF-15 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-15.md) |
| RF-16 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-16.md) |
| RF-17 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-17.md) |
| RF-18 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-18.md) |
| RF-19 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-19.md) |
| RF-20 | APROBADO MVP | Proveedor institucional pendiente de configuración y verificación. | [HTTP y SQL](postman/cobertura_27rf/RF-20.md) |
| RF-21 | APROBADO MVP | Proveedor institucional pendiente de configuración y verificación. | [HTTP y SQL](postman/cobertura_27rf/RF-21.md) |
| RF-22 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-22.md) |
| RF-23 | APROBADO MVP | Inicio técnico acreditado con configuración explícita LAB. La activación productiva requiere consentimiento institucional aprobado y configuración del operador. | [HTTP y SQL](postman/cobertura_27rf/RF-23.md) |
| RF-24 | APROBADO MVP | Evaluación técnica por orden docente confirmada. No se atribuye a la profesora la política técnica del equipo. | [HTTP y SQL](postman/cobertura_27rf/RF-24.md) |
| RF-25 | APROBADO MVP | MVP confirmado para el mismo caso y versión histórica, permiso individual de un uso. Vínculos entre casos distintos fuera de este alcance. Activación productiva condicionada al consentimiento institucional. | [HTTP y SQL](postman/cobertura_27rf/RF-25.md) |
| RF-26 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-26.md) |
| RF-27 | APROBADO MVP | Contrato vigente conservado, sin aprobación institucional nueva atribuida. | [HTTP y SQL](postman/cobertura_27rf/RF-27.md) |

## Activación externa pendiente

Debe recibirse el documento institucional aprobado, con responsable, versión, vigencia y evidencia verificable. Un operador confiable publica y selecciona la versión SQL histórica y emite una atestación PRODUCCION con la clave custodiada externamente. El servidor requiere el pin, la clave pública y una decisión de inicio PRODUCCION aprobada y referenciada. No hay registro público de aprobadores ni una clave privada en el backend.

Un paquete LABORATORIO es rechazado en PRODUCCION. Las rutas permanecen cerradas sin configuración o con firmas, huellas o ámbitos incompatibles. Las pruebas usan documentos y aprobación sintéticos explícitamente marcados. Las firmas acreditan la procedencia de la atestación del operador, sin sustituir la aprobación institucional del contenido.

En contenedores los dos archivos deben montarse de solo lectura mediante una configuración de despliegue externa y rutas internas. Compose transmite las variables y no crea aprobaciones. El proveedor institucional de correo requiere configuración y validación externa. Las notas oficiales conservan autorización explícita y no se generan al finalizar.

## Reproducción y capturas

En PowerShell, desde C:/SPS/nuclear-acelerado-candidato, con Docker Engine disponible y dependencias del backend instaladas en un entorno propio. La validación actual reutilizó el ejecutable Python existente y dependencias adicionales del directorio privado de laboratorio.

```powershell
$py = 'C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2\.venv\Scripts\python.exe'
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend') + ';C:\SPS\acelerado_nuclear_20261110\correo\vendor'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $py -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-25 --preparar
```

Importar la colección y el Environment temporal que imprime el preparador. Seleccionar el Environment del RF y ejecutar su carpeta en orden. Usar un laboratorio nuevo por RF. Conservar la consola abierta y cerrar con q. Las credenciales sintéticas permanecen en el directorio privado temporal y no se comparten.

Capturas sugeridas de RF-25, solicitudes 34–40, autorización, mismo permiso, segundo intento, conflicto de duplicado, escenario histórico, cierre y permiso agotado. RF-12, solicitudes 9–12, texto sintético, aceptación, inicio y duplicado. RF-13, POST técnico y GET del mismo resultado. RF-10, primera respuesta, segunda selección rechazada, FIN y cierre. Mostrar URL, estado HTTP y Test Results. Ocultar Authorization, códigos y cuerpos de login. Las capturas manuales siguen pendientes.

## Continuidad

El siguiente incremento es activar la fuente oficial de consentimiento cuando se entregue su aprobación verificable y validar el despliegue institucional, seguido de aceptación Angular del alcance MVP. El código y los cambios permanecen en checkpoints locales del candidato. Se preservan checkout original, stash, .env, evidencias y respaldos. No se ejecutó push ni merge a develop.
