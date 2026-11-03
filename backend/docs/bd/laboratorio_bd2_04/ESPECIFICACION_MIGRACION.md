# Futura revisión Alembic — propuesta NO incorporada

> Antecedente experimental: el estado «NO incorporada» corresponde a la fase
> previa. La integración posteriormente autorizada y sus resultados se documentan
> en [BD2_04_INTEGRACION_AUTORIZADA.md](../BD2_04_INTEGRACION_AUTORIZADA.md).

## Identificación y alcance

- Revisión propuesta: `20261102_cases_history_guard`.
- Padre esperado, sujeto a comprobar al implementar: `20261101_er28_base_academica`.
- PostgreSQL: instalar exactamente [protecciones.sql](protecciones.sql).
- Reversión: exactamente [revertir_protecciones.sql](revertir_protecciones.sql).
- No existe archivo nuevo en `backend/alembic/versions/`; no cambió el head real.
- No cambia PK/FK/UQ, columnas, UUID, ORM, tablas, 8A ni la referencia académica ER28.

Hashes del SQL validado:

```text
upgrade SHA256 99b9ed5ad4ff70cbcf57e3c03b65906166cd68cb02af9448dc79e857f41d1ece
downgrade SHA256 86d6959fb813532a88b15fbfb57b3b6c4c5886fd9a71646c19410e139902be91
```

La revisión futura deberá contener copias literales e inmutables del SQL revisado,
no leer un archivo mutable de docs durante despliegue. Alembic ofrece la transacción:
no añadir BEGIN/COMMIT interno ni ejecutar autocommit. Con SQLAlchemy/psycopg,
el mecanismo ensayado es `bind.exec_driver_sql(SQL, execution_options={"no_parameters": True})`.
Evita que los porcentajes literales de PL/pgSQL se interpreten como placeholders.

Compatibilidad de dialecto propuesta: PostgreSQL instala estas guardas; SQLite
permanece sin DDL de triggers y **sin esa garantía de base de datos**, conservando
las pruebas portables de aplicación. Cualquier otro dialecto rechaza explícitamente
la revisión hasta definir soporte. Esta rama portable de la futura revisión aún
no se implementó/probó: debe verificarse al integrarla y no sustituye las pruebas PG.

## Objetos exactos

Seis funciones SECURITY INVOKER, con search_path fijo pg_catalog/public y tablas
referenciadas como public.*:

| Función | Contrato |
|---|---|
| bd204_version(text,jsonb) | Resuelve la raíz UUID a través de los padres existentes, sin columnas auxiliares |
| bd204_borrador(uuid,boolean) | Bloquea la versión FOR UPDATE y exige BORRADOR; ausencia solo tolerada en cascada DELETE cuya cadena de padres ya fue protegida |
| bd204_guardar_hijo() | Identidades/padres estables; contenido editable solo en borrador; valoración de la misma versión |
| bd204_guardar_version() | Inicial BORRADOR, identidad estable, transiciones y congelación; coordina familia con FOR KEY SHARE |
| bd204_guardar_caso() | Metadatos familiares estables; DELETE familiar solo si todas las ediciones son BORRADOR, bloqueadas |
| bd204_no_truncar() | Rechaza TRUNCATE explícitamente |

Dieciocho triggers:

| Tabla | Trigger por fila | Operaciones | Trigger por sentencia |
|---|---|---|---|
| caso | bd204_caso | BEFORE UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| version_caso | bd204_version | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| escenario | bd204_escenario | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| pregunta | bd204_pregunta | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| opcion_respuesta | bd204_opcion | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| rubrica | bd204_rubrica | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| criterio_rubrica | bd204_criterio | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| nivel_rubrica | bd204_nivel | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |
| valoracion_opcion | bd204_valoracion | BEFORE INSERT/UPDATE/DELETE | bd204_truncar BEFORE TRUNCATE |

Errores propuestos: 23514 para violaciones de contenido/estado/pertenencia/identidad;
23503 para padres inexistentes, además de las FK originales. No se modifican
las traducciones HTTP: los escritores actuales ya traducen SQLAlchemyError y
revierten. READ COMMITTED espera el bloqueo y relee estado; REPEATABLE READ puede
rechazar con 40001. Deadlocks 40P01 de transacciones multirraíz requieren rollback
y reintento completo: no se promete ausencia de deadlock ni reintentos silenciosos.

## Preflight y datos anteriores

En la misma transacción, adquirir SHARE ROW EXCLUSIVE en las nueve tablas en el
orden exacto del script, para drenar/bloquear escrituras durante auditoría/instalación.
Usar ventana de mantenimiento y límites operativos de espera autorizados. No
desactivar restricciones ni truncar para instalar.

El script aborta si hay FK previas no validadas, estados distintos de los tres
del dominio o valoraciones cuyo criterio y opción pertenecen a versiones diferentes.
No repara ni reasigna filas. El laboratorio comprobó que una instalación rechazada
no deja funciones/triggers. Antes de autorizar un entorno del equipo se necesita
una auditoría de datos explícitamente permitida y resolución humana de discrepancias.

Filas PUBLICADO/ARCHIVADO coherentes quedan protegidas sin reescribirlas. No es
necesario reconstruir contenido ni inventar UUID. La protección comienza al
instalar; no permite recuperar datos históricos que ya se hubieran perdido.
La revisión no añade fórmulas, umbrales, niveles ni políticas de evaluación.

Precondición de seguridad operacional: inventariar rol de ejecución de la app,
propiedad de tablas/funciones, privilegios de schema y parámetros de replicación.
La app no debe ser superusuario/propietaria ni poder desactivar triggers o cambiar
session_replication_role; migrador separado. El rol de laboratorio ensayado no
es una instrucción de GRANT para producción. Si la aplicación tiene esos privilegios,
la garantía contra SQL malicioso no está completa y el despliegue debe detenerse.

## Compatibilidad y pruebas exigidas al integrar

1. Ejecutar las 109 comprobaciones experimentales y convertir su cobertura en
   pruebas PostgreSQL de regresión de la revisión integrada, no en omisiones.
2. Verificar upgrade/downgrade y reupgrade con snapshots de filas y catálogo;
   la reversión quita objetos bd204_, no borra datos ni tablas.
3. Conservar BORRADOR→PUBLICADO→ARCHIVADO, reemplazo de borrador mediante DELETE/
   INSERT, cascadas de eliminación de borradores, UUID de familia/edición/rúbrica
   y sesiones exactas. No hay escritor productivo que necesite reparentar o cambiar IDs.
4. Los fixtures actuales de login/8A que insertan versiones PUBLICADO y agregan
   rúbrica posteriormente deberán crear BORRADOR, cargar hijos y luego publicar.
   Ejemplos a revisar: `tests/identity/test_student_login_scheduling.py`,
   `tests/integration/test_participation_8a.py` y fixtures Scheduling relacionados.
   No habilitar un bypass de triggers para preparar pruebas.
5. Las limpiezas de pruebas que hacen DELETE de versiones publicadas o TRUNCATE
   deberán usar aislamiento por rollback/laboratorio desechable. Revisar
   `tests/integration/cases/conftest.py` y `tests/integration/scheduling/conftest.py`.
   Cambiar la estrategia de aislamiento no autoriza borrar historia en producción.
6. `test_esquema_actual_no_es_barrera_ante_SQL_directo` de BD2-03B documenta el
   hueco anterior: con la nueva revisión su expectativa debe convertirse en
   rechazo explícito, sin skip/xfail. Este cambio no se hizo en BD2-04.
7. Ejecutar suite general aislada incluyendo 8A. La aprobación actual del laboratorio
   no demuestra esa suite con triggers integrados; 1157/38 es la línea base previa.

## Reversión y aprobación

Downgrade ejecuta las dos fases explícitas del archivo de reversión: retirar los
18 triggers, después las seis funciones en orden de dependencias. Mismo bloqueo
de tablas y transacción. Sin DROP CASCADE ni eliminación de datos. En laboratorio
se verificaron catálogo y filas conservadas, y que el bypass anterior vuelve a
ser posible: **revertir reabre la vulnerabilidad**, requiere decisión operacional.

Se solicita aprobación específica de esta revisión, sus restricciones de identidad/
reparentado incluso en borradores, creación inicial BORRADOR, prohibición TRUNCATE,
precondiciones de roles y adaptación de fixtures/regresión. No se solicita aprobar
A1–A3 del ER alternativo ni una nueva tabla. **No implementar todavía esta revisión
ni aplicar SQL a una base existente sin esa autorización.**
