# Fase 9: integración segura con la aplicación principal

Actualización posterior: [FASE_9A_PARTICIPATION.md](FASE_9A_PARTICIPATION.md)
documenta el progreso puro y las operaciones de selección y cierre añadidas.
Este informe conserva la evidencia del primer montaje limitado al escenario.

Fecha local: 4 de noviembre de 2026, America/Bogota.
Directorio único: `C:\Users\MARTIN GIL GARCIA\Documents\ChatGPT\Proyecto Nuclear\proyecto-nuclear-2`.
Rama: `feature/backend-continuidad`. HEAD inicial y final:
`eba0f7e83bf10fd685637ba911fc454f2252c6f2` (merge PR #8).
Se ejecutó fetch y se comprobó igualdad con origin/develop antes de editar:
0 commits exclusivos de cada lado. No fue necesario sincronizar mediante merge.

## Composición habilitada

La principal ya registraba Identity, Cases y Scheduling. Ahora incluye únicamente
el router específico de lectura:

`GET /api/v1/attempts/{attempt_id}/current-scenario`.

El handler existente se trasladó a `current_scenario_router.py`; el router completo
de Participation también incluye este subrouter para conservar sus pruebas y URL.
No hay otro caso de uso, algoritmo ni repositorio de grafos. La principal NO monta
inicio, provisión, decisiones POST/PUT, progreso, cierre, resultados o ausencias.
Estas rutas siguen ausentes (404), no solo protegidas por una política permisiva.

## Dependencias reales y configuración

- Identity autentica Bearer JWT y recarga cuenta, actividad, rol y relaciones desde
  SQL. No se aceptan roles, estudiantes ni versiones del cliente como autoridad.
- `obtener_consulta_escenario` compone la clase existente mediante
  `crear_dependencia_escenario_8b`. Su fábrica usa el `get_session_factory` compartido,
  de forma diferida, sin otro engine productivo ni Session global de solicitud.
- `RelojSistema` aporta el instante UTC del servidor, con offset. Esto NO implica
  que los timestamps históricos sin offset sean UTC.
- Nueva configuración **`PARTICIPATION_TIMESTAMP_ZONE`**, opcional y sin valor
  predeterminado. Debe ser una zona IANA disponible y corresponder a la convención
  real de los datos históricos. Se valida en la dependencia de esta consulta;
  una zona inválida no inutiliza por sí sola las otras funciones de la aplicación.
- Ausencia, cadena vacía o zona desconocida: 503 mediante `ReglaPendiente` y el
  traductor existente. No se infiere la zona del equipo ni se adopta UTC por defecto.
- Si hay datos históricos de convenciones distintas, configurar una zona global
  sin conciliarlos NO es una solución válida. No se migran ni reinterpretan datos.
- `FechasPersistencia`, la UoW y los autorizadores ya existentes comprueban
  titularidad, matrícula, convocatoria, versión exacta, sesión y ventana de respuesta
  confirmada; no autorizan ingreso RF-22 ni inicio de nuevos intentos.
- La UoW conserva locks y sale sin commit, con rollback/cierre. La lista blanca,
  los errores seguros y `Cache-Control: no-store` se conservan. No es una transacción
  PostgreSQL READ ONLY: usa los locks de los escritores para leer de forma coherente,
  pero no ejecuta DML, guarda estados ni confirma transacciones.

La conexión compartida, el esquema existente, JWT y el catálogo/relaciones reales
deben estar configurados. No se leyó ni modificó la base persistente para comprobarlo.
No se creó ni ejecutó una migración nueva. `.env` no se modificó.

## Pruebas sobre app.main.app

`backend/tests/integration/test_main_current_scenario.py` añade 11 escenarios.
Usa el objeto real `app.main.app`, no un FastAPI alternativo. Las cuentas, permisos,
asociaciones, matrícula, consentimiento y asignación se preparan explícitamente
como datos sintéticos. El intento se inicia en la app aislada existente con
políticas SOLO de laboratorio; no se presenta ese inicio como operación productiva.

Para la lectura principal se configuran por entorno las fábricas REALES con el
PostgreSQL propio y los parámetros JWT sintéticos; el estudiante efectúa login
correo/código mediante Identity en la principal. Solo se sustituye el reloj.
Una aserción exige que ese sea el único dependency override de app.main durante
el escenario positivo. No se sustituyen autenticación, autorización ni repositorios.
UTC se configura únicamente porque corresponde a las fechas sembradas del laboratorio.

Se acreditaron:

- Login real, contenido actual, esquema sin información académica privada,
  no-store, repetición idéntica, cero DML y cero eventos COMMIT en el engine real.
- Rechazos de anónimo (401), ajeno/matrícula/convocatoria/horario (403), intento
  vencido o cerrado (409) y zona ausente o inválida (503), sin mutar el agregado.
- Avance leído desde main tras una respuesta confirmada por el escritor aislado;
  no se instala ese escritor en la principal.
- Segunda edición del mismo caso y archivo de la asignada sin sustituir el
  contenido histórico. Se reutiliza un helper de preparación de edición de la
  prueba anterior; no hay un nuevo endpoint de creación de ediciones.
- OpenAPI de main expone únicamente el GET indicado entre las rutas de Participation;
  las demás operaciones probadas responden 404.

## Resultados actuales

Evidencia relativa: `evidencias/fase9_principal_20261105T031924Z/`.
Los nombres usan UTC; las ejecuciones corresponden al 4 de noviembre local.

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores | Advertencias pytest |
| --- | ---: | ---: | ---: | ---: | ---: |
| Focal inicial | 94 | 0 | 1 | 0 | 1 |
| Focal corregida, 57.87 s | **95** | **0** | **0** | **0** | **1** |
| General, 595.42 s | **1964** | **38** | **0** | **0** | **1** |

Las 11 nuevas de main están incluidas en focal y general. El subconjunto relacionado
seleccionado dentro de la general contiene **772 aprobadas y 9 omitidas**, sin fallos
ni errores; se documenta como subconjunto, NO como otra ejecución. No sumar cifras.
La general se ejecutó sobre `backend/tests` y `backend/app/modules/participation/tests`.

El único fallo inicial fue de inspección de un test anterior: intentaba usar `.path`
en el contenedor `_IncludedRouter` de FastAPI. Se cambió a verificar el OpenAPI
expandido y se conservó la aserción estricta de que solo el GET esté registrado.
No fue un fallo de autenticación o del servicio. El registro fallido se conserva.

Las 38 omisiones son 29 dependientes de `SPS_IDENTITY_TEST_URL`, tres pruebas antiguas
de conexión externa y seis dependientes de `SPS_PERSISTENCE_LAB_URL`. Están
deshabilitadas para evitar conexiones del equipo; NO se consideran aprobadas.
Las pruebas nuevas sí utilizaron PostgreSQL17 desechable. La advertencia conocida
es Starlette/TestClient-httpx.

Artefactos: `estado_inicial.json`, cada `pruebas_*/` con comando, fuentes, consola,
JUnit y resultado; `aceptacion_main.json`, `respuesta_main.json`,
`regresion_relacionada_en_general.json` y `CIERRE.json`.
El JSON público observado contiene solo escenario, contexto, pregunta/opciones y
progreso, sin códigos ni tokens. No se fabricaron respuestas ni resultados.

El ejecutor desactiva `.env` SOLO en el proceso hijo de pytest, excluye credenciales
y URLs heredadas y habilita exclusivamente laboratorios Docker propios. No oculta
fallos ni modifica la lógica de las pruebas. Comprueba fuentes estables durante
pytest y conserva nuevas evidencias sin borrarlas. Los fixtures crean PostgreSQL17
en tmpfs, verifican TCP/base aislada y eliminan exclusivamente sus propios IDs.

```powershell
# Desde el directorio autorizado, sin cambiar de carpeta:
& C:\Python313\python.exe -B .\evidencias\fase9_principal_20261105T031924Z\ejecutar_validacion.py focal
& C:\Python313\python.exe -B .\evidencias\fase9_principal_20261105T031924Z\ejecutar_validacion.py total
# Solo consultar la respuesta ya capturada:
Get-Content .\evidencias\fase9_principal_20261105T031924Z\respuesta_main.json -Encoding UTF8
```

## Archivos y justificación

| Archivo | Cambio |
| --- | --- |
| `app/core/config.py` | Zona histórica explícita, opcional y sin valor predeterminado |
| `app/main.py` | Montaje exclusivo del router de lectura |
| `participation/api/current_scenario_router.py` | Handler trasladado, mismo contrato y traductor de errores |
| `participation/api/router.py` | Reutiliza el subrouter, conserva escrituras solo para composición aislada |
| `participation/api/dependencies.py` | Configuración, reloj y fábrica real de sesiones, con cierre seguro |
| `participation/tests/test_api.py` | Contrato OpenAPI estricto adaptado al montaje limitado |
| `tests/integration/test_main_current_scenario.py` | Aceptación de la aplicación principal real |
| `tests/integration/test_current_scenario_http.py` | Extrae preparación histórica compartida; mantiene su aceptación anterior |
| `participation/api/HTTP.md` | Distingue ruta montada de contratos no expuestos |
| `docs/FASE_9_ESCENARIO_ACTUAL.md` | Enlaza la actualización; preserva resultados históricos |
| Este informe | Evidencia y límites actuales |

No se modifican ORM, migraciones, DBML, reglas de Evaluation ni políticas académicas.

## Estado y continuidad

**Implementado e integrado:** el GET está registrado en la principal con dependencias
reales y puede operar para un intento existente si configuración, datos y autoridad
son válidos. **Probado:** app.main en ASGI/TestClient y PostgreSQL17 nuevo; no un
servidor desplegado. **Uso real:** condicionado a verificar la convención temporal,
configurar el entorno y comprobar el esquema/relaciones del despliegue. No se
declara producción acreditada por las políticas o cuentas sintéticas del laboratorio.

RF-22, consentimiento/revocación, provisión, repetición y notas oficiales mantienen
sus bloqueos. No se implementa login del personal. La falta de esas decisiones no
se resuelve habilitando el router completo.

Git conserva feature/backend-continuidad, HEAD eba0f7e y las otras referencias/stash;
sin commits, push, merges ni worktrees nuevos. La lista exacta de cambios, huellas
y archivos locales preservados está en CIERRE.json. No se borran evidencias ni respaldos.

Siguiente incremento recomendado, sin ejecutarlo: revisar la integración restringida
del progreso privado para intentos existentes, verificando antes sus efectos de
vencimiento/escritura. El inicio productivo continúa bloqueado por sus decisiones
académicas; no se monta junto con una nueva lectura.
