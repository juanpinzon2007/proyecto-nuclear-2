# RF-13 / RF-24 — persistencia técnica exacta

## Checkpoint y alcance

Checkpoint autorizado del motor: **2a79dc7d2e8937129932e9f8f10c962c2c042cd9**,
padre 9a1d1333e74289661aba4e911f3edb3e0fabcc9c. Mensaje:
`feat(evaluation): calcular resultados con peso igual por pregunta`.
Incluyó únicamente las diez rutas verificadas del manifiesto del motor; huellas,
diff preparado y JUnit anteriores fueron comprobados. No se publicaron commits.
La persistencia de este informe son cambios posteriores SIN COMMIT.

Actualiza el estado histórico de RF13_RF24_MOTOR_PREGUNTAS.md. La fórmula y el
calculador del checkpoint se reutilizan, sin otro motor ni niveles inventados.
No se modifica el ER académico original ni se sustituyen resultados antiguos.

## Fuente canónica y modelo físico

`resultado_intento` sigue siendo la ÚNICA cabecera y conserva su UNIQUE(id_intento).
Por tanto hay como máximo un resultado técnico inmutable por intento, incluso
entre motores. No se inserta otra versión para recalificar automáticamente.

| Estructura | Datos y claves |
|---|---|
| resultado_intento existente | Intento, caso INTEGER/UUID real, versión UUID exacta, rúbrica, regla, modalidad, nota final, fecha, definición/procedencia y huellas |
| resultado_calculo_preguntas | PK/FK id_resultado; suma NUMERIC sin typmod, N exigidas entero positivo, respondidas, pendientes y SHA-256 de la configuración |
| resultado_pregunta | PK resultado/pregunta; opción y puntaje Decimal exacto; orden único por resultado; FK compuesta opción/pregunta |
| resultado_criterio_exacto | PK resultado/criterio; FK compuestas a cabecera/rúbrica y criterio/rúbrica; suma exacta, cantidad evaluable, numerador entero y denominador entero positivo |

Las tres tablas nuevas son detalles del resultado, no otra fuente de notas.
No contienen id_nivel ni modifican resultado_criterio: sus campos discretos y
su precisión histórica permanecen intactos. Hay 36 tablas en metadata, frente
a 33 anteriores; el DBML conceptual original de 28 no se cambia.

La cabecera distingue LABORATORIO antiguo y TECNICO nuevo. El CHECK solo permite
TECNICO con PREGUNTAS_100_V1; nunca OFICIAL. Los guards del formato anterior se
conservan para LABORATORIO, incluido su límite de base de laboratorio. El nuevo
escritor técnico exige PostgreSQL/transacción, autorización persistente y regla
configurada; no depende de un nombre ficticio de BD. Se probó en una segunda
base NUEVA dentro del contenedor temporal propio, nunca en una base permanente.

El ámbito/formato persistido determina el lector. El nombre de la rúbrica por sí
solo no convierte un resultado antiguo: hay una prueba de LABORATORIO con la misma
cadena PREGUNTAS_100_V1, que sigue legible y no admite sustitución.

## Representación exacta

La nota siempre es G = suma de puntajes seleccionados / N. Los pendientes de un
intento VENCIDO aportan cero, sin filas ni selecciones ficticias. N pertenece a
una ruta completa válida de la edición asignada, no a la unión de ramas.

Los puntajes individuales y las sumas se guardan como NUMERIC sin precisión/escala
restrictiva, usando Decimal. Se probaron sumas de 1200, que no cabían en el detalle
NUMERIC(5,2) anterior. La fuente docente de opciones conserva su precisión actual;
no se reescriben ni amplían implícitamente sus valores históricos.

Para contabilizar por criterio una pregunta se distribuye uniformemente entre
sus correspondencias. Esto NO determina la nota: cada pregunta conserva 1/N.
La publicación vigente exige matriz completa y puntajes coincidentes por opción;
con C criterios, S_c conserva la suma cruda y A_c = S_c/(N*C). Entonces la suma
de A_c es exactamente G. No se usan los pesos históricos de criterio para multiplicar
la nota ni se introduce un factor configurable. Una matriz contradictoria se rechaza.

Los aportes se normalizan como fracciones exactas de enteros obtenidas de Decimal,
sin float. Ejemplo real de aceptación: S=100, N=3. Con un criterio se persiste
100/3; con dos se persisten 50/3 y 50/3. Solo la cabecera muestra 33.33 después
de ROUND_HALF_UP. Nunca se guarda 33.33 ni 16.67 como contribución aproximada.

La verificación SQL usa productos cruzados para sumar/comparar fracciones, y
cociente/resto para el único redondeo final. round(numerador,0) en un CHECK solo
verifica que es entero: no transforma ni redondea datos guardados.

## Composición y transacción

Operaciones internas: `persistir_resultado_preguntas` y `consultar_resultado_tecnico`
en participation/infrastructure/persisted_questions.py. El servicio recibe usuario,
intento, fábrica de Session nueva, zona histórica y reloj consciente de zona.
No recibe puntajes del cliente ni completa configuración ausente.

En una UoW se autorizan cuenta/titularidad/convocatoria y se bloquean los recursos
con los repositorios existentes; se lee la versión exacta, se reutilizan las
estrategias y el calculador, se valida procedencia y se guardan cabecera/todos los
detalles. Un único commit confirma el conjunto. Error SQL revierte todo.

UNIQUE(id_intento), locks y recuperación verificada del resultado existente
permiten reintentos idempotentes. Dos solicitudes concurrentes recuperan el mismo
id_resultado y la fecha original. No hay upsert ni sustitución silenciosa.

La procedencia incluye definición versionada, fuentes de motor/validador/contabilidad,
configuración histórica y su documento/hash, intento y respuestas reales, precisión,
rúbrica y fracciones efectivamente utilizadas. El lector vuelve a contrastar
referencias, filas y cálculo, sin ejecutar código almacenado. Una definición bajo
id/versión no acepta otra huella; futuros cambios deben conservar la implementación
histórica o introducir otra versión explícita, nunca recalificar por defecto.

El cierre existente NO se modifica ni se conecta automáticamente al cálculo.
Se exige el intento ya cerrado: FINALIZADO con FIN real o VENCIDO/PARCIAL.
La atomicidad acreditada es cálculo+persistencia, no cierre+evaluación automática.
No hay confirmación de ausencias, consolidación, repetición ni publicación.

## Migración y garantías PostgreSQL

Revisión **20261107_question_results**, dependiente de **20261106_consent_versions**.
DDL manual revisado: tres tablas, sus PK/FK/UNIQUE/CHECK, índice candidato
uq_8c_opcion_pregunta y ampliación condicionada del CHECK de ámbito de la cabecera.
No cambia columnas, PK o identificadores históricos ni hace UPDATE/backfill.

Funciones nuevas fp8_longitud, fp8_cabecera, fp8_completo y fp8_detalle; nueve
triggers sobre los detalles para inmutabilidad y completitud diferida. Se amplían
las dos funciones de validación 8C existentes con dispatch por ámbito; su rama
legacy conserva el SQL original versionado. SECURITY INVOKER y search_path explícito.
La entrada JSONB del validador evita dependencias DDL por una firma de tipo tabla;
se reconstruye localmente el mismo registro tipado para validarlo.

Se verifican estado cerrado y modalidad, versión publicada/archivada, contexto
asignado, hashes, puntajes y pertenencias reales, secuencia de selecciones, FIN,
longitudes iguales sin ciclos alcanzables, denominador, completitud de filas y
suma exacta de contribuciones. La validación de longitudes usa estados memoizados
en memoria, sin tablas auxiliares ni escoger una continuación arbitraria.

El escritor exige READ COMMITTED y mantiene el orden de locks existente. El lock
advisory de definición impide dos huellas para la misma política. El lector docente
conserva REPEATABLE READ/READ ONLY: usa el adaptador lector sin FOR UPDATE, DML,
flush ni commit. La consulta HTTP solo anuncia disponibilidad técnica, no la nota.

Downgrade vacío: retira solo elementos nuevos y restaura funciones/CHECK anteriores.
Con resultados TECNICO se rechaza antes de perder datos. Con solo resultados legacy
se admite y estos siguen legibles, incluso después de re-upgrade. DDL requiere
ventana sin escritores; no se promete migración online libre de bloqueos/deadlocks.
No se aplica a bases permanentes. Casos grandes necesitan medición de rendimiento
de los checks diferidos; no se declara satisfecho un SLA por estas pruebas.

## Validación y evidencia

Regresión funcional final: **256 aprobadas**, 0 omitidas/fallidas/errores, una
advertencia conocida de Starlette, 167.69 s. Incluye 44 escenarios nuevos PG17.
Esquema/migraciones final: **215 aprobadas**, 0 omitidas/fallidas/errores, una
advertencia, 114.56 s. Incluye la comparación de la revisión histórica de espacios.
General final: **2367 aprobadas, 38 omitidas, 0 fallidas, 0 errores**, una advertencia
conocida de Starlette, 1365.04 s; 2405 casos JUnit. No se suman selecciones solapadas.
Las 38 omisiones conservadas requieren configuración/URLs externas (29 Identity,
3 conexión PostgreSQL, 6 laboratorio independiente); ninguna aceptación nueva omitida.

La primera general tuvo 2366 aprobadas, 38 omitidas y un fallo en
`test_teacher_space_migration.py::test_upgrade_integridad_sin_autoconcesion_y_downgrade_controlado`:
comparaba metadata actual con una revisión anterior a las tres tablas y al índice
compuesto nuevos. Se corrigió solo el filtro histórico y se añadió la aserción
expresa de ausencia de esas tablas en la revisión antigua. La comparación de la
cabeza actual sigue siendo completa. Se conserva ese log/JUnit fallido.

Ejecuciones finales:
- Focal: `pruebas_focal_20261107T232031Z/`.
- Esquema: `pruebas_seguridad_20261107T235542Z/`.
- General: `pruebas_total_20261107T235758Z/` (fin UTC 2026-11-08 00:21;
  fecha local Bogotá 2026-11-07).

En la general final no cambiaron fuentes preexistentes. Solo se añadió la evidencia
sintética BD2-04 prevista por su prueba. No quedaron contenedores propios activos
ni detenidos bajo la etiqueta `sps.identity.mapping.lab=true`.

Evidencias en evidencias/persistencia_preguntas_20261107/: comandos, HEAD, hashes,
consola y JUnit, incluidos fallos iniciales y correcciones. Se corrigieron sintaxis
del SQL nuevo, alias y dependencia de firma; las fixtures antiguas se actualizaron
para las tres tablas, nueva cabeza y nueve triggers. La prueba negativa de TRUNCATE
incluye los detalles nuevos para verificar el guard, sin quedarse en un error previo
por FK. No se quitaron controles ni se añadieron skip/xfail.

El ejecutor opcional guarda JSON numéricos de filas reales ya confirmadas y lecturas
desde otra Session: 100/0, peso uniforme, suma 1200 y tercios. Son datos sintéticos,
sin credenciales, correos ni JWT. No se presentan como notas oficiales.

```powershell
.\.venv\Scripts\python.exe -B evidencias\persistencia_preguntas_20261107\ejecutar_validacion.py casos
.\.venv\Scripts\python.exe -B evidencias\persistencia_preguntas_20261107\ejecutar_validacion.py focal
.\.venv\Scripts\python.exe -B evidencias\persistencia_preguntas_20261107\ejecutar_validacion.py seguridad
.\.venv\Scripts\python.exe -B evidencias\persistencia_preguntas_20261107\ejecutar_validacion.py total
```

El ejecutor es evidencia local sin seguimiento. Desactiva .env solo en pytest y
elimina URLs heredadas; el fixture crea exclusivamente contenedores nuevos postgres:17
con tmpfs, puerto TCP local e identidad verificados. Limpia únicamente su ID propio.
No se usan contenedores del equipo ni volúmenes persistentes.

## Disponibilidad y pendientes

No hay rutas nuevas, ni cambios Postman ni ejecución de pm.test. Se acreditó por
ASGI/HTTP, app.main y JWT real que la consulta docente de preparación reconoce
TECNICO, conserva privacidad y no muestra nota, respuestas o rúbricas.

RF-13 sigue PARCIAL: cálculo/almacenamiento/lectura técnicos acreditados para el
contrato soportado; falta composición de uso del producto y consolidación oficial.
RF-24 sigue PARCIAL: vencidos persistidos sin ficción; ausencias/rectificación
expresa siguen fuera. RF-14, RF-16 y RF-25 conservan sus bloqueos de visibilidad,
padrón/consolidación/publicación e identidad/autorización de repeticiones.

Siguiente incremento seguro: consulta docente privada del resultado técnico ya
persistido, reutilizando el ámbito de preparación y el lector READ ONLY, sin
publicarlo a estudiantes ni clasificarlo como nota oficial. No se implementa aquí.
