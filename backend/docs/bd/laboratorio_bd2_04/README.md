# BD2-04 — Laboratorio de integridad PostgreSQL

Desde la raíz del repositorio, con el entorno existente y Docker/imagen local
`postgres:17` disponibles:

```powershell
.\.venv\Scripts\python.exe -B backend/docs/bd/laboratorio_bd2_04/run_lab.py
```

No instala paquetes, descarga imágenes, usa Compose ni toma URLs externas.
El ejecutor retira las URLs de prueba heredadas en su proceso y habilita solamente
el fixture que crea un contenedor **nuevo**: `motor_postgresql_desechable`.
No cambia `.env` ni modifica el helper existente.

## Qué ejecuta

1. Crea PostgreSQL 17, base vacía, tmpfs y puerto dinámico de localhost. Verifica
   ID/nombre/etiqueta/montajes, conexión TCP y nombre de base. Registra el montaje
   real de datos y comprueba que es tmpfs.
2. Ejecuta `upgrade 20261101_er28_base_academica`, pasando la conexión del
   laboratorio explícitamente a Alembic, para conservar la reproducción anterior
   a las guardas incluso después de integrarlas. No utiliza el DBML alternativo
   ni el experimento U1. Por defecto instala SQL experimental; la regresión
   autorizada llama `main(revision_guard="20261102_cases_history_guard")` y usa
   upgrade/downgrade/reupgrade de la revisión real en lugar del transporte SQL.
3. Reproduce dos bypass anteriores y los revierte. Prueba rechazo de instalación
   sobre datos incoherentes, sin reparación ni objetos dejados a medias.
4. Aplica [protecciones.sql](protecciones.sql) en una transacción. Solo crea
   seis funciones y dieciocho triggers, sin nuevas tablas, columnas, FK, UQ o índices.
5. Prueba SQL directo, escritores reales, tres escenarios concurrentes y un rol
   de laboratorio sin propiedad/superusuario. Ese rol es solo fixture; no es una
   propuesta de permisos académicos ni una cuenta del equipo.
6. Ejecuta [revertir_protecciones.sql](revertir_protecciones.sql) en el laboratorio,
   comprueba catálogo original y filas preservadas. No borra tablas/datos al revertir.
7. El finally destruye únicamente el ID propio creado por el fixture y después
   verifica que ya no existe. Nunca selecciona recursos del equipo para eliminar.

Los ensayos DML solo afectan datos sintéticos de ese contenedor. Los ataques se
revierten; la eliminación legítima de un borrador se prueba solo allí. No se usa
la base `sps` ni un contenedor existente. No hay limpieza global Docker.

## Resultados y archivos

- [Informe](INFORME_BD2_04.md).
- [Especificación exacta de futura migración, aún no incorporada](ESPECIFICACION_MIGRACION.md).
- [Evidencia final](evidencia_d88a3a2475bf4912be52f87735042ad2.json) y
  [repetición independiente del mismo código](evidencia_5ef9153f1a4e4fe397c3539c1f1c5b9a.json):
  **109/109 comprobaciones por ejecución**. Incluyen diagnósticos de antes/después;
  no son 109 pruebas nuevas de la suite del backend ni se suman entre ejecuciones.

Cada evidencia registra SQL, SQLSTATE esperado/observado, hashes de scripts,
migraciones y escritores utilizados, catálogos antes/después, controles de bloqueo,
aislamiento y limpieza. No registra contraseñas ni URL de conexión.

El ejecutor sale con error si una comprobación o limpieza falla y conserva el
JSON de ese intento. Se conservaron dos intentos iniciales fallidos del driver,
corregidos sin relajar pruebas, y dos ejecuciones intermedias antes de ampliar
cobertura. El historial completo está en el informe.

No se ejecutó pytest ni la suite general en esta fase. **1157 aprobadas/38
omitidas/1 advertencia** continúa siendo antecedente histórico. La regresión
general con una futura revisión integrada requiere el trabajo de fixtures
indicado en la especificación: no se afirma que ya esté realizada.

Ese párrafo describe la fase experimental original. La integración posterior
autorizada añade la prueba `backend/tests/integration/test_cases_guard_migration.py`,
que conserva las 109 comprobaciones y agrega cuatro comprobaciones de head real
y reupgrade (113 en total), sin cambiar el SQL probado. Sus evidencias nuevas se
conservan también aquí; los resultados de pytest se informan por separado.

## Alcance de seguridad

Los triggers no autentican JWT, no autorizan al docente y no replican la Chain
académica de publicación. Protegen contenido congelado y pertenencia estructural
para escritores sujetos a esos triggers. Un propietario/superusuario puede
retirarlos: producción exige separar rol de migración y rol de aplicación.
No hay bypass mediante variable de sesión diseñado en esta propuesta.

Los scripts dependen de nombres y esquema `public` actuales. No ejecutarlos fuera
del laboratorio sin aprobación del informe/especificación. La política estricta
de IDs/padres estables, creación inicial BORRADOR y prohibición de TRUNCATE también
forma parte de lo que debe aprobarse; no se presenta como comportamiento implícito
ya autorizado del modelo académico.
