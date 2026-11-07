# Evaluation: preparación interna del cierre de una sesión

## Contrato y aceptación del incremento

RF-13 y RF-24 siguen bloqueados para notas oficiales. Se reutilizan Strategy,
CalculadorRubrica y el repositorio técnico; no se sustituye una política pendiente.
Las decisiones del equipo exigen considerar toda la sesión, confirmar ausencias
por el docente y separar cálculo, consolidación y publicación.

Este incremento implementa una consulta interna de preparación, sin endpoint ni
permiso para publicar. El padrón observado son TODAS las convocatorias persistidas,
incluidas retiradas y estudiantes sin participación. No afirma que ese padrón sea
el corte académico definitivo ni infiere ausencias de la falta de intentos.

Criterios de aceptación:

- Cuenta docente activa y asociaciones inequívocas CASES/SCHEDULING verificadas
  desde SQL; sesión propia, autoría del caso y grupos de asignación coherentes.
- Lectura de una instantánea PostgreSQL REPEATABLE READ y READ ONLY, sin DML,
  flush ni commit. No se persiste el vencimiento efectivo.
- Una fila por convocatoria, con todos sus intentos y versión/rúbrica exactas.
  Sin notas, respuestas, correcciones, contenido de políticas o datos de contacto.
- Los resultados LAB se verifican mediante el repositorio existente y nunca
  habilitan consolidación, reporte oficial o notificación de calificaciones.
- Retirados, falta de matrícula inequívoca, intentos abiertos, ausencia sin
  confirmación y repeticiones se muestran como bloqueos, sin resolver políticas.
- Errores SQL, referencias incoherentes y autorización fallida no devuelven
  informes parciales. Una lectura concurrente no mezcla dos estados confirmados.

## Límites deliberados

No se añade un registro de ausencias: requiere definir su identidad causal,
momento permitido, corrección/historial y almacenamiento sin intento ficticio.
No se elige mejor/último/promedio de intentos. ADMINISTRADOR por sí solo no obtiene
acceso docente: se reutiliza DOCENTE y el ámbito persistente existente. La expresión
«DOCENTE ADMINISTRADOR» no crea un nuevo rol ni multirrol automáticamente.

No cambia app.main, RF-16 ni RF-27. El informe es diagnóstico técnico de preparación,
no resultado consolidado ni publicación. Incluso sin bloqueos individuales siguen
pendientes fórmula completa, consolidación y contrato de publicación oficial.

## Validación

Código: HEAD 48c2638b3d0b90fe18016fe56024d05237765a4a más los cambios locales de
este incremento. Rama feature/backend-continuidad, carpeta original. Las fuentes
Python permanecieron idénticas durante las ejecuciones. No se crearon commits.

| Ejecución actual | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Aceptación nueva interna PG17, incluida en las siguientes selecciones | 13 | 0 | 0 | 0 | No contabilizar como ejecución adicional |
| Relacionada mixta (SQL real, SQLite y unitarias) | 535 | 9 | 0 | 0 | 1 |
| General completa, nueva ejecución | 2239 | 38 | 0 | 0 | 1 |

No sumar suites solapadas. Duraciones: relacionada 119.72 s; general 1136.73 s.
Advertencia conocida: Starlette/httpx. Las 38 omisiones son 29 pruebas de Identity
condicionadas a SPS_IDENTITY_TEST_URL y 9 antiguas de Participation condicionadas
a configuración/URL de laboratorio. No se configuró una BD compartida para
desbloquearlas ni se modificaron esos tests. Los 13 escenarios nuevos usan el
fixture PostgreSQL 17 desechable, migraciones reales y relaciones SQL persistidas.

La aceptación cubre: todas las convocatorias (incluidas sin P y retiradas),
matrícula no inequívoca, referencia histórica, verificación del resultado LAB
por el repositorio existente, privacidad, seis rechazos de autorización SQL,
sesión inexistente/grupo incoherente, lectura concurrente, todos los intentos
sin seleccionar uno ni persistir vencimiento, snapshot concurrente y fallo SQL
real con rollback/recuperación. No confirma ausencia ni inserta intentos ficticios.

Se reutilizaron además las pruebas existentes de resultados técnicos: duplicados,
FK compuestas y rechazo de versiones cruzadas, inmutabilidad, concurrencia del
escritor y rollback tras cabecera. Las políticas positivas de cálculo de esas
fixtures siguen siendo LAB. No acreditan una fórmula académica productiva.
La relacionada/general incluyen el recorrido HTTP estudiantil y los cierres
seguros de reporte y notificación; la nueva consulta se acredita internamente,
no mediante un endpoint nuevo.

Incidencias conservadas, sin ocultarlas:

- Primera aceptación: 10 aprobadas y 1 fallo de preparación por convocar después
  de finalizar la sesión. Se ordenó correctamente la fixture sin relajar Scheduling.
  Reejecución de esos 11 casos: todos aprobados; se añadieron después dos casos
  de ámbito y concurrencia incluidos en los 13 finales.
- Primera general: interrumpida al 28 %, sin resumen/JUnit final ni veredicto.
  Se observó Docker Engine no disponible después; no se demuestra la causa exacta
  de terminación del proceso. El log no se sobrescribió. Tras reanudar Docker por
  el usuario, se verificó y eliminó solo el contenedor propio detenido, con etiqueta,
  ID completo, fecha de creación en la ejecución y almacenamiento tmpfs sin mounts.
  La general completa posterior se ejecutó en recursos nuevos.

Evidencia local (comandos, HEAD, hashes, logs, JUnit y resultados nominales):

```text
evidencias/evaluation_preparacion_20261106T225458Z/
  pruebas_focal_20261106T225658Z/
  pruebas_total_20261106T230023Z/       # interrumpida; interrupcion.json
  pruebas_total_20261107T033737Z/       # general completa
```

Fechas de carpetas en UTC; la ejecución completa terminó el 6 de noviembre de
2026 a las 22:56:49 America/Bogota. Las 2224/38 anteriores son históricas.

Reproducir desde la carpeta original, con Docker disponible:

```powershell
.\.venv\Scripts\python.exe -B evidencias/evaluation_preparacion_20261106T225458Z/ejecutar_validacion.py casos
.\.venv\Scripts\python.exe -B evidencias/evaluation_preparacion_20261106T225458Z/ejecutar_validacion.py focal
.\.venv\Scripts\python.exe -B evidencias/evaluation_preparacion_20261106T225458Z/ejecutar_validacion.py total
```

El ejecutor desactiva la lectura de .env y retira URLs externas solo en el proceso
de prueba. Cada ejecución conserva una carpeta nueva; no edita archivos mientras
pytest está activo. La general produjo un JSON adicional de evidencia BD2-04,
identificado en resultado.json y preservado, sin modificar fuentes anteriores.

## Archivos y alcance real

- application/evaluation_readiness.py: DTOs inmutables de preparación, sin notas.
- infrastructure/evaluation_readiness.py: autorización y snapshot SQL por operación.
- infrastructure/result_repository.py: lector existente opcional para reproducir
  resultados sin FOR UPDATE; el escritor conserva su dependencia predeterminada.
- tests/integration/test_evaluation_readiness.py: 13 aceptaciones PostgreSQL.
- Este documento y AUDITORIA_COBERTURA_BACKEND_20261105.md: alcance y evidencia.

No cambiaron ORM, Alembic, DBML, Strategy, CalculadorRubrica, políticas académicas,
Identity, Scheduling ni app.main. Una cabeza: 20261106_consent_versions; metadata
integrado de 33 tablas, comprobado por la regresión. Sin migraciones nuevas ni
aplicación a bases permanentes. Se conservan las ramas, stash, .env y arrastres.

Main conserva GET current-scenario/progress y POST decisions/finish del intento
existente. GET /api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte y
POST /scheduling/calificaciones/notificar siguen registrados con cierre seguro;
no se conectaron a esta consulta ni a resultados LAB. No hay endpoint nuevo de
preparación, evaluación, consolidación o publicación. Una instantánea de lectura
no es una autorización reutilizable para una escritura o publicación posterior.

## Pendientes concretos y siguiente incremento

RF-13 y RF-24 continúan BLOQUEADO para notas oficiales. RF-16 y la parte de notas
de RF-27 conservan su bloqueo. Sin reclasificaciones: 14 IMPLEMENTADO, 8 PARCIAL,
5 BLOQUEADO. La consulta reduce una dependencia técnica; no completa esos RF.

1. Precisar nivel→logro y agregación de varias preguntas por criterio, incluidos
   ceros de pendientes; redondeo si es necesario y cierre voluntario incompleto.
2. Registrar confirmación expresa de ausencia sin inventar P/I ni consentimiento:
   definir referencia a convocatoria, actor/fecha, momento y corrección/historial.
   El port actual solo exige confirmación; no existe el registro persistente.
3. Definir selección/consolidación de varios intentos y el padrón/corte oficial,
   incluidas retiradas. No se adopta mejor, último o promedio por deducción.
4. Diseñar la publicación integral autorizada y su persistencia: hoy resultado_intento
   admite exclusivamente LABORATORIO, no existe resultado_participacion integrado
   ni estado durable de publicación. No convertir filas LAB en oficiales.
5. Conectar reporte/avisos solo a resultados oficialmente consolidados/publicados,
   con autorización revalidada en su propia transacción y sin envíos automáticos
   por finalizar un intento. Aclarar el encaje de DOCENTE ADMINISTRADOR en los
   roles/permisos existentes antes de conceder nuevas facultades.

Prioridad siguiente: cerrar el mapeo/agregación académicos para reutilizar el motor
actual con una política versionada aprobada; y concretar el contrato de confirmación
durable de ausencias. Este incremento no implementa esas decisiones pendientes.
