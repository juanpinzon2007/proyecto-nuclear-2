# Plan de persistencia real — revisión del 28 de octubre de 2026

## Evidencia y alcance

Rama `martin`, HEAD inspeccionado `072d704`, árbol inicialmente limpio.
`git fetch origin` completado; `origin/main` (`ae45e95`) es ancestro de martin.
Las referencias `origin/alejandro`, `origin/juan` y `origin/maicol` apuntan a
`c3cda63` y no contienen archivos bajo `backend/`. No hay modelos ni migraciones
remotas que puedan reutilizarse todavía en esas ramas. Esto describe lo publicado,
no el trabajo local que puedan tener los compañeros. No se hicieron merges.

La arquitectura compartida tiene una sola `Base`, motor y fábrica de sesiones.
Alembic usa `Base.metadata`, pero todavía no importa modelos; `versions/` solo
tiene `.gitkeep` y `alembic heads` no devuelve revisiones. La consulta de solo
lectura a `information_schema.tables` de `sps` no devolvió tablas de usuario.
Se volvió a inspeccionar visualmente `_referencias_locales/modelo ER.png`.
No se alteró el esquema ni los datos de `sps`.

La conexión real ya comprobada por Martín deja de ser un bloqueo. Los límites
documentados en PERSISTENCIA.md sobre Docker/credenciales describen la sesión
anterior; el laboratorio actual sí ejecutó PostgreSQL 17 real.

## Modelos propios y dependencias exactas

Los siguientes modelos deben heredar de `app.db.base.Base`, separarse de las
dataclasses inmutables y usar los nombres/IDs enteros del ER. No se proponen
relaciones ORM a clases de compañeros que todavía no existen; primero acordar
sus tablas y FK. `relationship()` es opcional, no requisito del repositorio.

| Modelo propuesto | Columnas del ER | Dependencias externas |
| --- | --- | --- |
| ParticipacionORM | id_participacion, id_asignacion, id_grupo_estudiante, estado, fecha_registro | asignacion_caso.id_asignacion; grupo_estudiante.id_grupo_estudiante |
| IntentoORM | id_intento, id_participacion, id_consentimiento, id_permiso_extra nullable, numero_intento, estado, inicio, fin nullable | consentimiento.id_consentimiento; permiso_intento_extra.id_permiso_extra |
| PasoSimulacionORM | id_paso, id_intento, id_decision, id_opcion, numero_paso, registrado_en, tiempo_segundos, reflexion_estudiante nullable | decision.id_decision; opcion_respuesta.(id_opcion,id_decision) |
| ResultadoIntentoORM | id_resultado, id_intento, nota_final NUMERIC(4,2), fecha_calculo, comentario_automatico nullable | Contexto histórico pendiente; FK interna a intento |
| ResultadoCriterioORM | id_resultado_criterio, id_resultado, id_criterio, id_nivel, puntaje_obtenido NUMERIC(5,2) | criterio_rubrica.id_criterio; nivel_criterio.(id_nivel,id_criterio) |
| ResultadoParticipacionORM | id_resultado_participacion, id_participacion, situacion, nota_definitiva NUMERIC(4,2) nullable, fecha_calculo, observacion nullable | Política de consolidación/ausencia pendiente; FK interna a participacion |

Las FK compuestas requieren claves UNIQUE/PK referenciables en las tablas de
Juan Andrés. Debe confirmarse su orden y tipos. No basta crear dos FK simples:
permitirían combinar una opción con otra decisión o un nivel con otro criterio.
No se inferirán cascadas de borrado ni se duplicarán entidades externas.

## Bloqueos para escritura, separados por prioridad

1. **DDL compartido:** nombres, claves, nulabilidad, generación de IDs y estados
   persistidos de Identity, Cases y Scheduling. Los valores de fixture no son
   estados aprobados. Confirmar restricciones antes de Alembic autogenerate.
2. **Límite individual histórico:** `Intento.tiempo_maximo` no está en el ER.
   Propuesta explícita para aprobación: conservar `vence_en TIMESTAMPTZ` junto
   con inicio consciente de zona; alternativa: una instantánea inmutable real
   mantenida por Scheduling. No reconstruir desde su configuración actual ni fin.
3. **Tiempo y pasos:** acordar UTC/TIMESTAMPTZ o semántica expresa de timestamps
   sin zona; confirmar que tiempo_segundos mide desde inicio hasta último guardado.
   Acordar selección actual frente a historial/revisitas. La implementación actual
   guarda una selección por decisión y no resuelve invalidaciones por ramificación.
4. **Resultado reproducible:** DatosEvaluacion necesita modalidad, referencia de
   caso/rúbrica y versión, política de cálculo, evidencias (incluidas decisiones
   aplicables sin respuesta), criterios y nota. El ER no conserva todo esto.
   Cases debe garantizar referencia histórica y ruta inmutables; aprobar dónde
   se guardan las referencias y la política. No usar comentario_automatico como
   JSON encubierto ni recalcular un resultado anterior con la rúbrica actual.
5. **Precisión:** los aportes por criterio pueden exceder dos decimales. Aprobar
   escala de almacenamiento o regla académica explícita, sin truncado silencioso.
6. **Ausencia y consolidación:** resultado_participacion puede representar un
   resumen sin intento, pero el detalle cero por decisión no tiene mapeo en el ER.
   resultado_criterio exige resultado_intento. No fabricar intentos; no confundir
   resumen de participación con nota de un intento ni elegir mejor/última/promedio.
7. **Concurrencia entre módulos:** verificar y consumir permisos extra y cupos
   de forma coordinada con inicio/cierre de asignación. Los puertos actuales solo
   autorizan; no acreditan consumo atómico. Acordar misma transacción si es posible
   en este monolito, o protocolo explícito de reserva/confirmación si no lo es.

Los puntos 1–3 bloquean escritura segura del agregado. Los puntos 4–6 bloquean
el repositorio definitivo de resultados. Se puede integrar el agregado antes que
las notas, manteniendo la evaluación pendiente y los endpoints protegidos.

## Archivos que implementar, sin crearlos prematuramente

Todos los siguientes paths son relativos a `backend/app/modules/participation/`.

| Archivo | Responsabilidad concreta |
| --- | --- |
| infrastructure/models.py | Solo los seis modelos propios, una vez aprobado el DDL; no otra Base |
| infrastructure/mappers.py | Dominio ↔ filas, estados, UTC, plazo histórico y Decimal exacto; reconstrucción completa sin descartar campos |
| infrastructure/repositories.py | RepositorioParticipacion completo: lecturas bloqueadas, reservar IDs, insertar intento y guardar diferencias de pasos comparando esperado |
| infrastructure/result_repository.py | RepositorioResultados: insertar resultado y criterios juntos, recuperar DatosEvaluacion íntegro confirmado; sin upsert/calificación pendiente |
| infrastructure/composition.py | Construir la fábrica de UnidadTrabajoSQLAlchemy con ambos repositorios y sesión compartida; inyectar adaptadores externos reales y reloj |
| infrastructure/queries.py | Reutilizar/refactorizar las lecturas existentes, sin mantener dos reconstrucciones divergentes |
| infrastructure/unit_of_work.py | Conservar ciclo de transacción; completar traducción coherente de conflictos si ocurren durante execute/flush, además de commit |
| tests/test_postgresql_repositories.py | CRUD real, FK reales, rollback agregado, comparación esperado, pasos conservados, doble inicio/cierre y concurrencia |
| tests/test_postgresql_results.py | Ida/vuelta exacta de resultados, precisión, unicidad, fallo parcial y lectura solo tras commit |

No hace falta cambiar las firmas públicas de Facade para sustituir la fábrica
actual por la SQL. Crear una participación no está hoy en ese puerto ni en Facade:
la participación debe existir antes de iniciar. Acordar con Maicol quién la
materializa y, si corresponde a este módulo, añadir un caso de provisión separado
e idempotente; no hacer que iniciar cree una convocatoria implícita.

Los cambios compartidos futuros deben coordinarse aparte: importaciones de modelos
en `backend/alembic/env.py` y revisiones en `backend/alembic/versions/`. No se
modificaron aquí. Nunca ejecutar create_all en arranque de la aplicación.

## Cómo conecta cada operación existente

1. **Inicio:** nueva Session/UoW; bloquear participación; autorizar con Identity y
   Scheduling; listar intentos bajo ese bloqueo; reservar ID de secuencia aprobada;
   crear Intento con reloj inyectado; insertar incluyendo plazo histórico; commit.
   Los métodos nuevo_id_* requieren reservar nextval antes de construir la entidad:
   acordar secuencias/IDENTITY compatible, nunca MAX(id)+1. Huecos tras rollback son
   normales; numero_intento es otra secuencia lógica protegida por bloqueo+UNIQUE.
2. **Registrar/modificar:** cargar padre y luego intento con FOR UPDATE; autorizar;
   Cases valida opción/ruta; entidad devuelve nuevo objeto; guardar compara con
   esperado bajo bloqueo, inserta pasos nuevos y actualiza únicamente los cambiados.
   Preservar IDs y número de pasos; no borrar/reinsertar ni eliminar rutas por cuenta propia.
3. **Progreso:** reconstruir respuestas, preguntar ruta a Cases; guardar vencimiento
   si corresponde. Es una operación que puede escribir, por lo que requiere UoW
   coherente aunque el endpoint sea GET. No calcula aciertos ni nota.
4. **Finalización/vencimiento:** guardar estado/fin y conservar pasos en la misma
   transacción. La repetición carga el cerrado y no vuelve a escribir.
5. **Evaluación:** otra UoW, mismo orden de bloqueo; consultar resultado confirmado;
   si existe devolverlo; si no, marco histórico → Strategy → política → calculador;
   insertar cabecera y criterios juntos solo con mapeo completo y commit exitoso.
   La lectura de resultados usa otra operación autorizada. No exponer nota antes.

Se conserva la semántica actual de cierre y evaluación en operaciones separadas:
un fallo de política no impide guardar respuestas/cierre. No es necesario unirlas
para conectar Facade a PostgreSQL. Cualquier exigencia futura de cierre académico
conjunto requiere un nuevo caso de uso explícito y decisión del equipo.

El adaptador debe traducir SQLSTATE conocidos donde realmente se producen.
Actualmente UoW los traduce dentro de commit; Core execute o flush explícito pueden
fallar antes. Los futuros escritores deben cubrir esa frontera sin ocultar errores
inesperados, sin reintentos automáticos ni commits propios.

## Orden de integración y migraciones

1. Juan Andrés confirma decision/opcion, rúbrica/criterios/niveles y versionado;
   Alejandro confirma consentimiento, permiso extra y consumo; Maicol confirma
   asignacion_caso, grupo_estudiante, provisión y plazo histórico. Responsabilidad
   concreta de permiso_intento_extra debe ratificarse con el equipo.
2. Aprobar un DDL integrado: estados, UTC, secuencias, plazo, relaciones compuestas,
   precisión y restricciones. Proponer UNIQUE de participación por asignación/
   membresía, número de intento por participación, intento activo parcial, paso
   por decisión/número y resultado por intento/criterio; no declararlas definitivas
   mientras historial/revisitas y políticas no estén resueltos.
3. Publicar e integrar mediante revisión las dependencias ORM sobre la Base común.
   Acordar una cadena Alembic, revisando heads antes de cada revisión. No apuntar
   arbitrariamente a una revisión de compañero todavía inexistente.
4. Resolver ciclo ER: permiso_intento_extra referencia participacion e intento
   referencia permiso_intento_extra. Crear primero dependencias raíz, participación,
   permiso y luego intento, o añadir las FK del ciclo en una revisión posterior
   coordinada. No crear una tabla falsa para que autogenerate pase.
5. Implementar modelos y escritores del agregado con pruebas en base vacía aislada;
   ejecutar upgrade/downgrade y FK reales una vez existan revisiones aprobadas.
6. Conectar la fábrica SQL a Facade mediante composición; conservar dominio y API.
   Validar pruebas previas y flujo completo con adaptadores externos reales.
7. Aprobar mapeo/políticas de resultados y ausencia; implementar su repositorio y
   migración posterior, probar referencias y reproducibilidad sin recalcular.
8. Integrar dependencias de seguridad reales. Solo después considerar registro
   del router y despliegue. Ningún endpoint se habilitó en main.py.

## Laboratorio ejecutado y reproducible

Se creó un contenedor PostgreSQL 17 desechable, sin volumen, con puerto aleatorio
limitado a 127.0.0.1 y base `sps_participation_test`. No compartió almacenamiento
con el contenedor existente. La confianza sin contraseña se usó únicamente en
ese laboratorio local efímero. Se eliminó al terminar.

`tests/test_postgresql_isolated.py` agrega seis pruebas con SQLAlchemy/psycopg reales:
commit visible desde otra conexión; rollback sin commit; UNIQUE diferido que falla
en commit y revierte todo; reconstrucción con pasos; rechazo sin duración histórica;
FOR UPDATE del lector que bloquea a otra conexión (SQLSTATE 55P03) y libera al cerrar.

Las tablas de fixture no tienen FK externas ni representan DDL académico aprobado.
La duración de diez minutos y UTC son decisiones explícitas de prueba. No se
demostraron todavía escritores académicos, autenticación, FK definitivas ni
recuperación integral de resultados. Se ejercitaron los lectores y UoW existentes.

Resultado: **361 passed, 1 warning, cero skips**: 352 anteriores + tres de conexión
ejecutadas también contra el laboratorio + seis nuevas. La advertencia conocida
es Starlette/httpx. Sin variables opt-in, las nueve PostgreSQL se omiten.

Desde la raíz, con Docker activo:

```powershell
docker run --detach --rm --name sps-participation-persistence-lab --env POSTGRES_DB=sps_participation_test --env POSTGRES_HOST_AUTH_METHOD=trust --publish 127.0.0.1::5432 postgres:17
# Esperar a que pg_isready indique accepting connections.
docker exec sps-participation-persistence-lab pg_isready -U postgres -d sps_participation_test
$puertoLab = (docker port sps-participation-persistence-lab 5432).Split(':')[-1]
$env:SPS_PERSISTENCE_LAB_URL = "postgresql+psycopg://postgres@127.0.0.1:$puertoLab/sps_participation_test"
try {
    .\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests/test_postgresql_isolated.py -q
} finally {
    Remove-Item Env:SPS_PERSISTENCE_LAB_URL
    docker stop sps-participation-persistence-lab
}
```

Para repetir las 361 juntas, usar un proceso PowerShell dedicado y configurar
también SPS_TEST_POSTGRESQL=1, POSTGRES_HOST=127.0.0.1, POSTGRES_PORT con ese puerto,
POSTGRES_DB=sps_participation_test, POSTGRES_USER=postgres y POSTGRES_PASSWORD con
un valor de laboratorio (la configuración compartida exige valor aun con trust).
No editar .env. Ejecutar pytest sobre `backend/app/modules/participation/tests`
y `backend/tests`, con `-c backend/pyproject.toml`. No ejecutar esta suite en paralelo
con xdist: las fixtures comparten nombres de tablas en la base desechable.

No hubo commit, push, Pull Request, cambios de rama, migraciones ni modificaciones
a módulos de compañeros o configuración global.
