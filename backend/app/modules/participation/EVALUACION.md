# Tercer incremento: motor de evaluación

## Alcance real

Se implementan Strategy, preparación de evidencias, matemáticas con parámetros
explícitos y coordinación transaccional mediante puertos. No se implementan
rúbricas de Cases, reglas académicas oficiales, ORM, migraciones, API, reportes
ni notificaciones. Los dobles y las rúbricas ficticias están únicamente en tests.

Se consultaron las secciones pertinentes de los cuatro documentos locales:

- `Agile Inception SPS.pdf`, página 9: evaluación parcial, ausencias y redondeo
  aparecen entre las precisiones académicas pendientes.
- `Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf`, páginas 24 y 32:
  las tres estrategias preparan datos diferentes para un calculador compartido;
  ausencia exige convocatoria y condiciones de cierre, sin intento iniciado.
- `ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, páginas 7, 14 y 27: referencia
  académica estable, necesidad de mapeo de opciones a criterios y diferencia
  entre respuestas, detalle de evaluación y resultados.
- `modelo ER.png`: rúbrica con máximo, criterios con pesos y niveles con logro
  porcentual; resultados por intento y por participación son registros distintos.

Los PDF incluyen propuestas que no están en el ER, como VALORACION_OPCION y
versionado explícito. No se crean esas tablas ni se inventan sus datos. La
referencia versionada de este motor es un contrato de lectura: Cases debe
proporcionarla desde una fuente real o declarar la política pendiente.

## Componentes y separación de responsabilidades

| Archivo | Responsabilidad |
| --- | --- |
| `domain/evaluation.py` | Valores de contexto, modalidad, evidencias, proyecciones de rúbrica y `DatosEvaluacion` |
| `domain/estrategias_evaluacion.py` | `IEstrategiaEvaluacion` y estrategias completa, parcial y ausencia |
| `domain/calculador_rubrica.py` | Fórmula explícita, validación de parámetros y operaciones Decimal |
| `application/evaluation_ports.py` | Contratos académicos, ausencia, repositorio y unidad de trabajo de evaluación |
| `application/evaluation_service.py` | Selección de estrategia, cálculo autorizado, confirmación y lectura |
| `application/dto.py` | Añade `EstadoEvaluacion`, sin notas ni detalles académicos de candidatos |
| `application/facade.py` | Añade operaciones que delegan en un motor configurado explícitamente |
| `tests/evaluation_fakes.py` | Únicas implementaciones de ejemplo para contratos todavía pendientes |
| `tests/test_evaluation_domain.py` | Estrategias, matemáticas y rechazo de inconsistencias |
| `tests/test_evaluation_application.py` | Autorización, persistencia simulada, reintentos y no publicación prematura |

Las proyecciones de rúbrica son datos inmutables consumidos por Participación;
no representan autoría, CRUD ni nuevas entidades ORM del módulo Cases.

Hay cinco pasos diferentes:

1. `PasoSimulacion` conserva una selección del estudiante, sin calificarla.
2. Un contrato académico determina el nivel obtenido en cada criterio a partir
   de esas evidencias. El motor no equipara `es_correcta` con un nivel.
3. El calculador aplica pesos, logros y máximo solo con una fórmula explícita.
4. El resultado calculado por intento se confirma antes de poder consultarlo.
5. La consolidación en una nota de participación sigue sin implementar. Existe
   `PoliticaConsolidacionPort`, sin seleccionar mejor nota, última nota o promedio.

## Qué hace cada Strategy

`IEstrategiaEvaluacion.preparar(contexto)` devuelve `DatosEvaluacion`. Las tres
estrategias comparten la misma salida; ninguna contiene una fórmula de nota.

**Completa:** exige modalidad COMPLETA, intento FINALIZADO y selección para todas
las decisiones del recorrido evaluable. Por ejemplo, las selecciones 50→60 y
51→63 se convierten en evidencias, sin revelar ni deducir sus niveles.

**Parcial:** exige un intento cerrado y modalidad PARCIAL determinada por el
contrato académico. Conserva respuestas existentes y representa pendientes con
`id_opcion=None`, sin asignarles cero. Puede aplicarse a un cierre voluntario con
pendientes o a un vencimiento, según la clasificación suministrada. Por ejemplo,
50→60 y 51 sin respuesta quedan sin nota si falta política parcial.

**Ausencia:** exige confirmación académica y ningún intento. Prepara cada decisión
evaluable sin opción elegida y con cero por RF-24. No crea un `Intento`, no fabrica
un nivel cero y no inserta `resultado_intento`. Si no se conoce la lista completa
de decisiones que debe evaluar una ausencia en un caso ramificado, se detiene con
`PoliticaEvaluacionPendiente`; no cuenta todo el caso por su cuenta.

El estado de ejecución VENCIDO no es una modalidad llamada INCOMPLETA. Un cierre
voluntario tampoco implica automáticamente COMPLETA. `PoliticaEvaluacionPort`
clasifica con reglas externas explícitas; el contexto rechaza combinaciones
incompatibles y datos ajenos al recorrido.

## CalculadorRubrica: fórmula soportada y límites

Solo se soporta `SUMA_PONDERADA_PORCENTUAL`, elegida explícitamente por el llamador:

```text
aporte_criterio = nota_maxima × peso_porcentaje × logro_porcentaje / 10000
nota_sin_redondear = suma(aporte_criterio)
nota_final = cuantización explícita de esa suma
```

Esto es una operación matemática disponible, NO una fórmula oficial aprobada de
SPS. Para ejecutarla se deben proporcionar:

- Rúbrica con referencia académica estable, máximo y todos los criterios/niveles.
- Un nivel real perteneciente a cada criterio, determinado externamente.
- Identificador de política, fórmula, cantidad de decimales y modo de redondeo.

Los pesos deben sumar exactamente 100; no se normalizan pesos defectuosos.
Se rechazan floats, NaN, infinitos, porcentajes fuera de 0–100, criterios/niveles
duplicados o ajenos y niveles faltantes. Se usa contexto Decimal local suficiente
para los parámetros; la precisión y trampas globales no cambian el resultado.
No se redondea cada aporte. Si el redondeo final supera el máximo, se rechaza la
configuración en lugar de recortar la nota sin autorización.

Ejemplo exclusivamente de prueba:

| Criterio | Peso | Logro proporcionado | Aporte sobre máximo 5 |
| --- | --- | --- | --- |
| 1 | 60 % | 100 % | 3 |
| 2 | 40 % | 50 % | 1 |

Con política ficticia explícita de dos decimales y ROUND_HALF_UP: **4.00**.
El test calcula ese valor con el calculador real, no con un mock de su resultado.
Una prueba parcial autoriza expresamente un nivel cero para el criterio pendiente
y obtiene 3.00; esa decisión solo existe en la fixture, no en producción.

## DatosEvaluacion y publicación

El DTO contiene modalidad, referencia académica, participación, intento opcional,
evidencias, resultados por criterio, nota opcional, identificador de política y
pendientes. Una nota calculada necesita criterios y política. Un DTO de ausencia
solo admite ceros y ningún intento. Ningún candidato acredita persistencia.

`lista_para_persistir` requiere nota y ausencia de pendientes. No se guardan
borradores ni se sustituyen reglas faltantes por una nota. Una política ausente
devuelve `EstadoEvaluacion(confirmada=False, pendientes=...)`, sin nota. Fallos
técnicos o inconsistencias se propagan; no se disfrazan de políticas pendientes.
Si ni siquiera es posible clasificar o determinar un recorrido, la excepción
explícita impide preparar una evaluación académica ficticia.

## Integración e idempotencia

El flujo preparado es:

```text
finalizar / procesar_vencimiento
    → cierre confirmado con la semántica anterior
evaluar_intento
    → autorizar → recuperar contexto histórico → clasificar → seleccionar Strategy
    → preparar evidencias → resolver política → calcular → insertar → commit
consultar_evaluacion
    → autorizar → exigir intento cerrado → recuperar solo una evaluación confirmada
```

Se separa evaluación de cierre para que la falta de una política no cambie un
fin ya confirmado ni comprometa su idempotencia. El servicio de cierre no calcula
ni publica notas. La fachada recibe un `ServicioEvaluacion` opcional explícito;
sin él las operaciones académicas fallan cerradas con `ReglaPendiente`.

La evaluación exige cierre previamente confirmado, incluso si el reloj ya ha
vencido pero el cierre aún no está guardado. Los reintentos consultan primero la
evaluación definitiva: no recalculan con una política nueva, no escriben otra
evaluación y no dependen de que Cases siga disponible para leer el histórico.
Se autoriza al solicitante antes de devolver cualquier resultado existente.

`RepositorioResultados` inserta sin upsert por clave participación/intento. El
adaptador debe impedir duplicados también ante carreras. Una confirmación fallida
no permite leer el candidato; el cierre anterior sigue conservado y se puede
reintentar la evaluación. Las pruebas con memoria no demuestran integración ni
concurrencia real con PostgreSQL.

## Ausencia y límites concretos del ER

La ausencia puede tener un resumen en `resultado_participacion` sin crear un
intento. Sin embargo, `resultado_criterio` depende de `resultado_intento`, y este
requiere un intento. El ER tampoco incluye el detalle por decisión de una ausencia
que propone el otro modelo de los PDF.

Por eso el DTO conserva `mapeo_er_detalle_ausencia_pendiente`, incluso si una
política explícita permitiera calcular matemáticamente cero. No se persiste como
evaluación definitiva ni se elimina ese pendiente automáticamente. No se presenta
como implementación terminada de RF-24: falta acordar qué evidencia se conservará
y cómo representarla. No se crean tablas ni intentos artificiales para resolverlo.

## Contratos pendientes con el equipo

- **Juan Andrés / Cases:** `CasesEvaluacionPort.obtener_marco_evaluacion` debe
  devolver rúbrica y recorrido de la misma referencia histórica y validar las
  selecciones allí. Recibe IDs de caso, participación e intento para identificar
  ese contexto. No basta con devolver la última rúbrica del caso.
- **Responsable académico con Juan Andrés:** implementar `PoliticaEvaluacionPort`
  para clasificar, mapear decisiones a niveles, resolver parciales y suministrar
  fórmula/redondeo. Sin esta fuente real, el motor no produce notas oficiales.
- **Alejandro / Identity:** reutilizar autorización real del solicitante. Los
  flujos de estudiante no se convierten en una puerta privilegiada para el Worker
  ni para operaciones administrativas.
- **Maicol / Scheduling:** vincular correctamente asignación y caso; implementar
  `AusenciasPort` para convocatoria y condiciones de cierre. No tener intentos en
  memoria no acredita por sí solo una ausencia académica.
- **Equipo:** decidir consolidación con `PoliticaConsolidacionPort` y resolver el
  mapeo ER de ausencias. Ese contrato no está conectado ni tiene implementación.

## Riesgos antes de PostgreSQL

1. Verificar unicidad real de `resultado_intento.id_intento` y protección ante
   cierres/evaluaciones simultáneos. Para claves con intento NULL, una restricción
   compuesta convencional puede no impedir ausencias duplicadas: acordar la
   restricción compatible con el esquema definitivo, sin generar migraciones aquí.
2. Garantizar el mismo límite transaccional y lecturas estables sobre intento o
   participación. Coordinar también ausencia frente a un inicio o repetición tardía.
3. Acordar estabilidad de contenido, rúbrica y política. El ER no expone el mismo
   versionado que el PDF; una cadena de versión fabricada no protege el historial.
4. `resultado_criterio.puntaje_obtenido` tiene escala limitada. Los aportes exactos
   del calculador pueden requerir más decimales: no truncarlos silenciosamente.
   Validar también escala/rango de nota_final y fecha_calculo del servidor.
5. Conservar datos y referencias necesarios para reproducir la nota. El motor
   no considera que un identificador de política mutable sea suficiente.
6. No escribir resultados de intentos como si fueran la nota definitiva de la
   participación. No hay selección automática entre varios intentos.

## Ejecutar las pruebas

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests backend/tests -c backend/pyproject.toml -q
```

Se mantienen las pruebas de los dos incrementos anteriores. Las nuevas prueban
estrategias, ceros sin intento, precisión Decimal, parámetros incompletos,
resultados inconsistentes, confirmación, aislamiento, rollback y duplicados.
