# U1 experimental — seis columnas, garantías bajo prueba

Ejecutar desde la raíz del repositorio, únicamente con Docker disponible y la
imagen local `postgres:17`, sin usar conexiones externas:

```powershell
.\.venv\Scripts\python.exe -B backend/docs/bd/laboratorio_u1_experimental/run_u1.py
```

No instala paquetes ni descarga imágenes. Reutiliza sin modificar la clase `Lab`
y el verificador del laboratorio [BD2-02B](../laboratorio_er28/run_experiment.py),
el [generador del ER original](../laboratorio_er28/schema_support.py), el SQL
literal de 28 tablas y la lectura/datos de [BD2-02C](../laboratorio_compatibilidad_cases/README.md).

Archivos propios:

- [seis_columnas.sql](seis_columnas.sql): exactamente el delta de A1/A2 propuesto,
  con sus cinco restricciones nuevas, sin triggers ni tablas auxiliares.
- [resultado_sintetico.sql](resultado_sintetico.sql): respuesta/nota de ensayo
  para comparar conservación; **no calcula ni aprueba una nota académica**.
- [run_u1.py](run_u1.py): crea el laboratorio, identifica fuente sintética UUID,
  aplica el delta, lee dos ediciones y trata de vulnerar las garantías.
- [INFORME_U1.md](INFORME_U1.md): resultados, límites y recomendación.
- [Evidencia final](evidencia_64c4f0d1126d4b11965f031e493a374d.json) y
  [repetición con el mismo código](evidencia_64f2031bcee147539ae31e03145fbb58.json).

## Interpretación del resultado

El ejecutor registra **28 garantías: 16 satisfechas y 12 vulneradas**. Hay además
8 controles de infraestructura/catálogo/rollback satisfechos por ejecución.
No se deben sumar como «36 pruebas aprobadas» ni ocultar las doce vulneraciones.
`completed_with_limitations` significa que la investigación terminó y encontró
fallos de diseño, no que U1 cumpla sus requisitos de seguridad/inmutabilidad.

El código de salida cero solo indica que terminó el experimento y la limpieza.
Un consumidor debe leer `status` y `garantias[].satisfecha`; ante error operativo
el ejecutor usa `execution_error`, conserva la evidencia y sale con error.

Las mutaciones adversas usan una transacción que se revierte. Se registra el
SQLSTATE y, cuando se aceptan, el dato modificado antes de rollback. La expectativa
de inmutabilidad es **rechazar**; `00000` deja la garantía como falsa. No hay
skip/xfail ni una expectativa artificial de aceptar la vulneración.

## Identidades, alcance y aislamiento

Cada ejecución genera un manifiesto `fuente_sintetica_uuid`: familia, dos versiones
y sus rúbricas, como entidades nuevas de laboratorio. Las PK INTEGER 10/50 y 20/60
son independientes; no se convierten a UUID. El manifiesto se conserva en el JSON
y se compara con el SELECT real del destino. No acredita ningún vínculo histórico
del equipo ni identidad/rol del docente fuera del fixture.

Se crean 28 tablas originales y luego solo las seis columnas, total 150. No hay
`version_caso` en el laboratorio; la tabla productiva no se toca. La marca de
congelación se carga como dato para intentar vulnerarla: no se afirma que el
contenido haya pasado la publicación académica del backend.

Antes de SQL, `Lab` verifica ID/nombre/etiqueta propios, imagen, red `none`, ningún
puerto publicado ni bind/volumen persistente, tmpfs configurado y montaje real
comprobado. Espera TCP dentro de su contenedor y confirma usuario/base/PostgreSQL
17; después exige una base sin tablas. No usa `.env`, engines del backend ni
credenciales del equipo. No importa modelos/servicios productivos.

El `finally` solo elimina el ID creado en esa ejecución después de verificar
propiedad, y confirma su ausencia mediante inspect. Cada nueva ejecución guarda
su propia evidencia con hashes de todos los artefactos de entrada. No hay Compose,
migraciones Alembic, limpieza global ni modificación de recursos ajenos.

El SQL de datos de cada experimento puede reconstruirse con los archivos enlazados,
`fuente_sintetica_uuid` y `insercion_v2_sql` de su evidencia. Una nueva ejecución
genera UUID nuevos para nuevas entidades sintéticas, manteniendo el mismo escenario.

No se ejecuta pytest ni la suite del backend. 1142 aprobadas/38 omitidas sigue
siendo línea base histórica, separada de este experimento.
