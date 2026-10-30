# Integración ORM y Alembic: Identity, Cases y Participation

Revisión del 28 de octubre de 2026, rama `alejandro`. Base de trabajo limpia en
`451583f`, que ya contiene la unión de develop y los dos routers. Los commits
publicados se conservaron. No se hizo commit, push ni operación sobre el PR #3.

## Causas raíz reproducidas

1. **NoReferencedTableError.** Al recolectar las pruebas, Identity importaba
   academic_models y registraba permiso_intento_extra y retroalimentacion_docente
   en Base.metadata. Sus FK apuntaban a participacion y asignacion_caso, ausentes
   del esquema integrado. La fixture de Cases crea el esquema común completo:
   por eso una importación de Identity rompía también las 26 pruebas de Cases.
2. **Multiple heads.** Dos ramas desarrollaron revisiones iniciales independientes
   con down_revision=None: 20261028_identity_access y c27a750108db. Un merge de Git
   no une el grafo de Alembic; por ello upgrade head era ambiguo.
3. **Pruebas antiguas de Participation.** La suite ampliada reveló además dos
   suposiciones incompatibles con el monolito integrado: Base.metadata vacía y
   ninguna ruta /api/v1 registrada. Su intención era comprobar que el lector no
   declara tablas y que el router provisional de Participation no está habilitado.

No existe un ORM productivo de participacion pendiente de importar. Martín tiene
dataclasses y adaptadores que reciben Table externas. Los Table de sus pruebas
son fixtures, no modelos autorizados para registrar en la Base del producto.

## Registro ORM corregido

`app/db/models.py` registra explícitamente las cuatro tablas publicadas de acceso
y las nueve de Cases. Valida todas sus FK; una referencia activa desconocida sigue
provocando un error. Lo utilizan tanto FastAPI como Alembic. No ejecuta DDL.

Los dos mapeos académicos pendientes conservan **la misma Base y el mismo registry**,
pero declaran una MetaData explícita de estado pendiente. No son parte del esquema
desplegable mientras sus dependencias reales no existan. No hay otra Base, otra
tabla usuario, eliminación de FK ni filtros que descarten referencias inválidas.
Las FK al usuario resuelven el objeto Column real de UsuarioORM, sin copiar su tabla.
Las FK a participacion/asignacion_caso se conservan y fallan explícitamente si se
intenta validar o desplegar esa metadata incompleta.

Es una frontera explícita de registro entre esquema integrado y contrato aún no
integrado; no se inserta una definición ficticia de participación para completar
el grafo. Su promoción al esquema común requiere una integración revisada con los
modelos externos y su migración. Los repositorios académicos y sus pruebas de
contrato DBML se conservan; sus endpoints siguen bloqueados con 503.

## Unión de migraciones

| Revisión | Dependencia | Operaciones |
| --- | --- | --- |
| 20261028_identity_access | base | Crea rol, permiso, rol_permiso y usuario |
| c27a750108db | base | Crea las nueve tablas UUID de Cases |
| 20261028_merge_access_cases | Ambas revisiones anteriores | Unión sin DDL, upgrade/downgrade vacíos |

Las dos revisiones publicadas no crean las mismas tablas y sus FK dependen solo
de sus respectivas ramas. No hay operaciones DDL duplicadas ni una dependencia
cruzada que obligue a reescribir su orden. Se añadió únicamente el mergepoint.
Alembic informa ahora un solo head: `20261028_merge_access_cases`.

Las regresiones SQLite comprueban upgrade head desde base, desde cada revisión
publicada y desde las dos revisiones ya aplicadas. Conservan filas anteriores de
rol y caso, verifican la versión final, comparan el esquema contra la metadata
integrada y ejecutan downgrade base. Las pruebas PostgreSQL de Identity también
ejecutan upgrade/downgrade del head conjunto, no solo su rama.

No se usó stamp, no se borró ninguna revisión publicada y no se migró la base del
proyecto. create_all sigue limitado a laboratorios de prueba existentes.

## Archivos modificados y propósito

| Archivo | Motivo |
| --- | --- |
| app/db/models.py | Registro determinista y comprobación estricta de referencias |
| app/main.py | Validar registro al componer la aplicación; conserva ambos routers |
| alembic/env.py | Usar el mismo registro que FastAPI |
| identity/infrastructure/academic_models.py | Separar metadata pendiente conservando Base, registry, columnas y FK |
| alembic/versions/20261028_merge_access_cases.py | Unir heads sin cambiar DDL ni historial publicado |
| tests/identity/test_persistence.py | Verificar el head conjunto y separar el laboratorio DBML aún incompatible |
| tests/integration/test_schema_integration.py | Regresiones de metadatos, importación, migraciones y routers |
| participation/tests/test_api.py | Comprobar solo la ausencia del router provisional de Participation |
| participation/tests/test_sqlalchemy_queries.py | Comprobar que el lector no modifica la metadata preexistente |
| Documentación de Identity | Actualizar estado y enlazar esta revisión |

Las rutas abreviadas identity/ y participation/ corresponden a app/modules/.
No se modificó código productivo ni pruebas de Cases, ni funcionalidades de
Participation/Scheduling. Los dos cambios dentro de Participation son únicamente
aserciones de pruebas de integración; no se eliminó ninguna prueba ni se añadió skip.

El laboratorio DBML usa una base/esquema de prueba separado: el caso INTEGER del
contrato académico no se mezcla ni se presenta como el caso UUID publicado por
Juan. Los repositorios de acceso se prueban contra el esquema integrado real.

## Bloqueo académico que requiere acuerdo del equipo

Cases publica caso.id UUID, docente_creador_id UUID y rúbricas asociadas a
version_caso. El DBML recibido utiliza caso.id_caso INTEGER, id_profesor hacia
usuario.id_usuario INTEGER y rubrica.id_caso. También difieren escena/decision
frente a escenario/pregunta. No son equivalencias automáticas.

La mínima definición de participacion descrita por el DBML es:

- id_participacion INTEGER PK autoincremental.
- id_asignacion INTEGER NOT NULL, FK a asignacion_caso.id_asignacion.
- id_grupo_estudiante INTEGER NOT NULL, FK a grupo_estudiante.id_grupo_estudiante.
- estado VARCHAR(20) NOT NULL, default 'pendiente'.
- fecha_registro TIMESTAMP sin zona NOT NULL.
- UNIQUE(id_asignacion, id_grupo_estudiante).

No se implementó esa tabla unilateralmente: necesita los modelos de programación
y membresía, y asignacion_caso depende del identificador de caso que actualmente
es incompatible entre fuentes. Juan, Martín y Maicol deben ratificar el contrato
relacional, los tipos/referencias y el orden de migraciones. No se introdujeron
casts, alias, tablas parciales ni claves externas sin destino real.

Se mantienen los bloqueos de convocatoria, ámbito académico, reporte completo,
repetición y feedback individual. En especial, unir los heads no resuelve que
retroalimentacion_docente sea única por asignación y no por participación.

## Resultados reales

Comando completo, incluyendo el módulo de Participation cuyos tests viven fuera
de backend/tests:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend/tests backend/app/modules/participation/tests -c backend/pyproject.toml -q -p no:cacheprovider --tb=short
```

| Ejecución | Aprobadas | Omitidas | Fallidas | Errores |
| --- | ---: | ---: | ---: | ---: |
| Antes de la corrección, suite ampliada | 502 | 38 | 2 | 55 |
| Después, sin habilitar PostgreSQL opcional | 569 | 38 | 0 | 0 |
| Después, PostgreSQL opcional habilitado y SQLite | 607 | 0 | 0 | 0 |

La última ejecución informó `607 passed, 1 warning in 58.09s`. La advertencia es
la deprecación existente de Starlette/HTTPX; no se ocultó con filtros.

Las 38 omisiones de la ejecución sin PostgreSQL eran opt-in preexistentes:
29 de Identity y 9 de Participation. Se habilitaron todas, sin cambiar sus marcas,
para la última ejecución. Las pruebas de Cases también se ejecutaron en PostgreSQL.

Se utilizó PostgreSQL 18.4 local en un clúster temporal ligado a 127.0.0.1, con
tres bases independientes: sps_cases_integration_test, sps_identity_test y
sps_participation_test. Se pasaron las variables TEST_DATABASE_URL,
SPS_IDENTITY_TEST_URL, SPS_PERSISTENCE_LAB_URL, SPS_TEST_POSTGRESQL y POSTGRES_*
solo al proceso de prueba. No se modificó .env ni se utilizó la BD del proyecto.
PostgreSQL 17, objetivo de Compose, no se presenta como ejecutado en esta revisión.

Los laboratorios terminaron sin tablas residuales y el clúster temporal se detuvo.
Los archivos del laboratorio se conservan fuera del repositorio.

Referencias del mecanismo: [merge de ramas Alembic](https://alembic.sqlalchemy.org/en/latest/branches.html#merging-branches)
y [metadata por jerarquía sobre un mismo registry de SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/declarative_config.html#metadata).
