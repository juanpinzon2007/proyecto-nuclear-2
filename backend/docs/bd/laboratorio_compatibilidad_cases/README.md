# BD2-02C — Reproducción segura

Ensayo de lectura funcional del ER28, separado de producción. No es una API,
un repositorio productivo ni una migración. Fecha: 2026-11-02.

Desde la raíz del repositorio, en `feature/integracion-backend`:

```powershell
.\.venv\Scripts\python.exe -B backend/docs/bd/laboratorio_compatibilidad_cases/run_cases_experiment.py
```

Requisitos: Python del entorno existente, Pydantic ya instalado, cliente/motor
Docker disponible e imagen local `postgres:17`. No instala dependencias ni hace
pull. Si Docker está apagado, el script falla antes de crear recursos. La primera
ejecución de esta fase encontró el motor apagado; después se inició Docker Desktop
sin ejecutar Compose. El mensaje heredado «Imagen ... no disponible» no distingue
ese fallo de la ausencia de imagen; el diagnóstico separado de `docker version`
mostró que faltaba la tubería del motor. La imagen ya estaba disponible localmente.

## Archivos

- [datos_sinteticos.sql](datos_sinteticos.sql): fixture legible, transaccional y determinista.
- [leer_caso.sql](leer_caso.sql): consulta anidada, ordenada y sin productos cartesianos.
- [run_cases_experiment.py](run_cases_experiment.py): ejecutor y 37 comprobaciones.
- [INFORME_BD2_02C.md](INFORME_BD2_02C.md): límites, contratos y primer cambio recomendado.
- [Resultado final](resultado_7619a2c727074a59b00553d124461295.json) y [repetición previa satisfactoria](resultado_c13ddbeecf4d4dac92e8cf472d5fdac6.json): catálogo, lecturas, rechazos, hashes y limpieza.

Reutiliza sin modificarlos el [SQL original del laboratorio](../laboratorio_er28/er28_experimental.sql),
su [generador](../laboratorio_er28/schema_support.py) y la clase `Lab`/verificador
de catálogo de [BD2-02B](../laboratorio_er28/run_experiment.py).
El SQL debe coincidir con la generación del DBML original y su hash conocido;
si no coincide, se detiene antes de Docker.

## Aislamiento

El ejecutor crea un contenedor con nombre aleatorio y etiqueta propia. Antes de
SQL verifica ID, nombre, etiqueta, imagen, red `none`, ausencia de puertos/binds/
volúmenes persistentes y montaje real `tmpfs` de los datos. Espera conexión TCP
dentro del contenedor a `127.0.0.1`, comprueba nombre de base, usuario y PostgreSQL
17, y exige una base sin tablas. No usa URLs heredadas ni `.env`.

Solo llama a `docker exec` contra su propio ID. El único borrado es `docker rm
--force` de ese ID, después de volver a verificar propiedad. Un `finally` exige
comprobar que el contenedor dejó de existir y registra el resultado. No se deben
extraer comandos para ejecutarlos sobre otro contenedor. No hay limpieza global.

Los UUID aleatorios del ejecutor son identificadores de recursos/archivos del
laboratorio; **ninguno representa caso, versión, docente o estudiante**.
Los IDs académicos sintéticos son INTEGER explícitos. Las claves/hash de ensayo
no son credenciales operativas. Cada ejecución crea todo desde cero y guarda una
evidencia nueva, también cuando falla; nunca sobreescribe evidencias anteriores.

## Alcance funcional

La lectura recupera asignación, caso, objetivos, personajes, escenas, decisiones,
opciones, pistas y rúbrica con criterios/niveles. Las lecturas normales usan una
transacción `READ ONLY`; las mutaciones negativas son transacciones revertidas.
Se verifican dos secuencias de arcos elegidas explícitamente por el fixture:

```text
101 --301--> 102 --303--> 103 --305--> NULL
101 --302----------------> 103 --305--> NULL
```

Esto prueba navegación de referencias, **no** una política de comienzo, fin,
progreso, obligatoriedad, invalidación o puntuación. `NULL` solo indica ausencia de
arco; no se traduce a intento finalizado. El fixture no se declara una versión
publicable por el backend: falta, entre otros datos, la valoración por opción y
criterio exigida por su cadena de publicación.

La consulta es interna y contiene corrección/justificación sintéticas para
comparar Cases docente. No puede exponerse a estudiantes. No demuestra JWT,
titularidad, login, autorización, política temporal ni endpoints. El hash del
código productivo leído está en la evidencia; solo se importa el esquema Pydantic
real y su enum para comprobar un rechazo. No se importa `app.main`, ORM o DB ni
se ejecuta Scheduling/8A contra el ER28.

Las pruebas negativas comprueban SQLSTATE y errores concretos de Pydantic; no
consideran compatible un candidato parcial. No se inventan `version_id`, números
de versión, UUID, `version_regla`, tiempos estimados ni puntajes a partir de
booleanos. Las dos faltas de pertenencia que PostgreSQL permite se registran como
limitaciones del ER y las guardas experimentales las rechazan.

La suite del backend no se ejecuta desde este script. La línea base histórica
1114 aprobadas/38 omitidas y los 198 probes previos no se suman a estos resultados.

## Resultados y fallos conservados

Hubo un intento sin motor Docker (sin contenedor), un fallo del lector de ensayo
al interpretar la ausencia de asignación y dos ejecuciones completas con 37/37.
El defecto del lector se corrigió mediante `COALESCE(..., 'null'::jsonb)`, sin
cambiar esquema ni relajar la prueba. Las cuatro evidencias se conservan y se
detallan en el informe. Todos los contenedores realmente creados fueron eliminados.
