# Contrato funcional de Evaluation — conciliación para aprobación

> Documento histórico de su fecha. Se conserva el análisis/propuesta original;
> los bloqueos y menciones «sin commit» se refieren a aquel corte. Para las decisiones
> posteriores efectivamente implementadas ver EVALUATION_CICLO_ACADEMICO.md y la
> matriz vigente §34. Publicarlo no constituye aprobación institucional.

**Estado: propuesta funcional y técnica, no política institucional aprobada.**
7 de noviembre de 2026, America/Bogota. No implementa fórmulas, cambia tablas ni
habilita resultados. Complementa la auditoría dirigida existente; no la sustituye.

## 1. Base protegida y alcance

Checkpoint local Postman: `65e6583b8eff130f6e7e6eaffe45bc5b4f201c0f`, padre
`8e1c03400b47d571eb903e40f0175c3d1c3f1008`, rama feature/backend-continuidad.
Mensaje: `test(postman): preparar colecciones y recorrido HTTP integral`.

Se verificaron los 19 archivos, sus huellas, el entorno vacío y la ausencia de
secretos materializados. Se versionaron 13 archivos reproducibles de
`backend/docs/postman/`: las dos colecciones, Environment sin secretos, OpenAPI,
inventarios MD/JSON, README, RECORRIDO, RESULTADOS y cuatro scripts auxiliares.
Los tres resultado_http_*.json, VALIDACION.json, PRESERVACION.json y MANIFIESTO.json
son evidencia local temporal: permanecen intactos y sin seguimiento. Evaluation
y sus evidencias anteriores no se incluyeron en ese commit.

La revisión completa del índice coincidió con las fuentes acreditadas y superó
`git diff --cached --check`. No se repitieron pruebas HTTP, PostgreSQL o pytest.
La revisión sintáctica de 206 scripts es estática; no equivale a ejecutar pm.test.
Los 30 pasos TCP previos y las 2265 aprobaciones/38 omisiones de la regresión
anterior son resultados históricos, no ejecuciones de este contrato.

## 2. Fuentes y precedencia

| ID | Fuente y ubicación | Autoridad y límite |
|---|---|---|
| S1 | `_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf`, p.4 RF-13/14/16/17; p.5 RF-24/25; p.7 RN-14–19; p.11 UC-05; p.12 UC-07 | Requisitos académicos de referencia: rúbrica/versionado, parciales, ausencia, ámbito y repetición por el creador. No especifica todas las fórmulas ni el redondeo. |
| S2 | `_referencias_locales/Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf`, pp.6–7, §5.7 p.32 y §6.3 p.37 | Contexto académico y Strategy; no convierte una propuesta de implementación en política aprobada. |
| S3 | `_referencias_locales/Agile Inception SPS.pdf`, §1.3 p.3, §4.3 p.9 | Declara negociables ejemplos, parciales y redondeo. No resuelve estos contratos. |
| S4 | Respuestas de Diana Ma Valencia comunicadas por el usuario y registradas en `FASE_8C_EVALUATION_INTEGRACION.md`, §1–2, 2026-11-02 | Fuente posterior recibida: una selección por pregunta; escala 0–100; criterios iguales; pendientes al vencer valen cero. La frase sobre ausencia «la nota sigue siendo la misma» no autoriza copiar una nota anterior. El registro no es un acta institucional firmada. |
| S5 | Decisiones del equipo ya registradas en `AUDITORIA_COBERTURA_BACKEND_20261105.md`, §26 | Publicación de todos los estudiantes de la sesión, confirmación docente de ausencia, autorización con ámbito y ninguna publicación automática al terminar. No completan algoritmos omitidos. |
| S6 | Prompt «CHECKPOINT POSTMAN Y CONTRATO FINAL DE EVALUATION», recibido el 2026-11-07 | Propuestas actuales del equipo para los cinco RF. Se reproducen y contrastan abajo; no constituyen aprobación institucional ni sustituyen silenciosamente S1/S4. |
| S7 | `backend/app/modules/identity/reference/sps.dbml`, rubrica/criterio/nivel y resultado_intento/resultado_criterio/resultado_participacion | ER académico conceptual oficial. No se modifica. Las adaptaciones físicas previas autorizadas no aprueban nuevas cardinalidades o entidades. |

Se comprobaron SHA-256 de los tres PDF originales, ER y registro 8C contra
`evidencias/auditoria_politicas_evaluation_20261107T040803Z/fuentes_verificadas.json`.
Coinciden. Se reutilizaron sus extracciones verificadas, especialmente páginas
4/5/7 de S1. La matriz vigente evolucionó después de esa auditoría: sus cambios
RF-03 no son una alteración de las fuentes académicas.

Referencias previas que se conservan:
`AUDITORIA_POLITICAS_EVALUATION_20261106.md`, `EVALUATION_PREPARACION_SESION.md`,
`FASE_8C_EVALUATION_INTEGRACION.md` y la matriz de los 27 RF. Tests y clases son
evidencia técnica, no fuente de aprobación de una fórmula.

## 3. Reglas propuestas y contraste funcional

| RF | Propuesta del equipo S6 | Respaldo anterior | Estado contractual y condición |
|---|---|---|---|
| RF-13 | Escala 0–100 | S4 y adaptación física de resultado_intento a NUMERIC(5,2), CHECK inclusivo | Compatible; no falta elegir otra escala. No reescalar resultados históricos. |
| RF-13 | Puntaje individual de cada pregunta configurado por el docente | S1 RF-17 respalda autoría de rúbrica; Cases permite valoraciones por opción/criterio | Falta significado exacto: logro obtenido, máximo de la pregunta o valor de cada alternativa. No existe un atributo físico/DSL de puntaje global por pregunta. |
| RF-13 | Todas las preguntas con igual peso global | S4 establece igualdad entre criterios, no entre preguntas | Nueva regla propuesta; requiere conciliación explícita de ambos ejes, no reemplazar criterios iguales. |
| RF-13 | No respondidas, incluidas ramas no visitadas, cuentan cero | S4/RN-14 cubren pendientes al vencer; no resuelven ramas excluidas ni cierre voluntario | Ampliación propuesta que cambia el universo evaluable y puede impedir alcanzar 100. No está aplicada. |
| RF-13 | Nota final con dos decimales y sin redondeo intermedio aprobado | S1 no fija modo; S3 lo dejaba negociable; almacenamiento final ya admite dos decimales | Falta método final de redondeo. No elegirlo por defecto de Decimal/PostgreSQL. No redondear aportes para hacerlos caber. |
| RF-24 | Incompletos: respondidas frente al total definido | S1 RF-24/RN-14 respalda cálculo parcial por rúbrica | Cobertura respondidas/total no equivale a nota: responder todo incorrectamente no acredita 100. Falta universo y relación con rúbrica. |
| RF-24 | Pendientes al vencer cero | S4 y RN-14 | Compatible en el alcance confirmado; conservar selecciones reales y modalidad PARCIAL. No fabricar opciones. |
| RF-24 | Ausencia confirmada por docente, nota cero | S1 RF-24/RN-15 pide ceros por pregunta; S5 exige confirmación expresa | Compatible con la dirección de las fuentes, pero la nota cero explícita es la precisión de S6. Falta aprobación y soporte sin intento/participación ficticios. |
| RF-24 | Rectificar ausencia con trazabilidad | S6 | Nueva operación propuesta; requiere reglas de momento, motivo, efecto e integridad frente a inicio/publicación concurrentes. |
| RF-25 | Docente autoriza individualmente cuando sea necesario, mismo o distinto caso, conserva autorización/historial | S1 RF-25/RN-16 reserva permiso al docente creador y prohíbe sesión finalizada | No ampliar a cualquier docente ni reabrir sesión por esta redacción. Caso distinto, autoridad de origen/destino, cantidad y vigencia requieren precisión. |
| RF-25 | Mayor nota entre intentos de la misma evaluación; no mezclar independientes | S6; antes no había selector aprobado | Regla de selección propuesta clara, pero falta identidad persistente de «misma evaluación», comparabilidad y tratamiento de empates/correcciones. |
| RF-14 | Visibilidad inmediata configurable por docente; nota provisional, desglose, correctas y explicaciones al terminar | S1 RF-14 exige feedback al terminar y no anticiparlo durante resolución | El interruptor y la distinción provisional son propuestas nuevas. Falta ámbito/versionado de configuración y resolver filtración a otros estudiantes activos/repetidores. |
| RF-14 | Provisional no equivale a oficial; oficial exige autorización docente | S5 y S6 | Separación compatible. Cierre de intento no publica. La autorización debe referirse al conjunto y versión concretos. |
| RF-16 | Excel y PDF; estudiantes, grupos, casos, convocatorias, notas, estados, fechas, duración e intentos | S1 RF-16 exige reporte académico con parciales/ausentes; RN-18 limita ámbito | Los formatos y columnas detallados se reciben de S6. CSV existente no acredita Excel/PDF. Faltan granularidad, significado de estados y duración. |
| RF-16 | Retiradas visibles como antecedentes | Consulta de preparación ya conserva retiradas; S6 precisa visibilidad | Conservar historial es viable. No determina si integran el padrón calificable, se marcan ausentes o reciben nota. |
| RF-16 | Corrección trazable, nueva autorización y última versión oficial vigente hasta publicar corrección | S6 | Requiere publicaciones/versiones durables y cambio atómico de vigencia; no sobrescribir notas vigentes ni resultados LAB. |

Las respuestas siguen siendo inmutables por la aclaración posterior de la profesora.
Nada de S6 permite editar selecciones, reabrir intentos o cambiar su grafo histórico.

## 4. Inconsistencias y decisiones que deben resolverse

### D01. Igualdad por criterio e igualdad por pregunta

No son automáticamente incompatibles, pero tampoco equivalentes. Ejemplo:
Q1 evalúa C1 y Q2/Q3 evalúan C2. Promediar primero las preguntas de cada criterio
y después dar 1/2 a C1 y C2 deja pesos efectivos Q1=1/2, Q2=Q3=1/4. No cumple
igualdad global de preguntas.

Con todas las preguntas evaluando todos los criterios en una misma escala y una
agregación lineal, ambas igualdades podrían coexistir: el promedio doble sobre
una matriz completa tiene pesos 1/(N·C). Esto es una **demostración condicional**,
no una fórmula adoptada. No hay respaldo para inventar ceros en criterios no
aplicables, repartir faltantes o imponer esa matriz a rúbricas anteriores.

Decidir si se conservan ambos ejes; qué pregunta aporta a qué criterio; qué
significa no aplicable y qué datos entrega la rúbrica. Exigir una tabla docente
con pregunta, alternativa, criterio, nivel/logro y resultado esperado. No cambiar
el motor a una media simple de preguntas por interpretar S6 aisladamente.

### D02. Ramas mutuamente excluyentes y posibilidad de alcanzar 100

Caso reproducible conceptual: Q1 conduce a Q2 **o** Q3 y luego FIN. Hay tres
preguntas en la versión y solo dos pueden contestarse en un recorrido. Si cada
pregunta tiene logro máximo 100 y peso global 1/3, penalizar la no visitada con
cero limita cualquier recorrido a 200/3 ≈ 66,666… . No puede alcanzar 100.

No se corrige automáticamente el denominador. Opciones que requieren decisión:

1. Mantener todas las preguntas de la versión y aceptar formalmente ese máximo
   alcanzable inferior a 100 y su consecuencia entre ramas de distinta longitud.
2. Cambiar la propuesta y excluir preguntas no accesibles de la ruta autorizada,
   definiendo además el conjunto antes de FIN y cuando vence sin elegir una rama.
3. Aprobar grupos equivalentes de preguntas/rutas o un diseño de caso donde
   todos los puntos evaluables puedan alcanzarse; no imponer navegación lineal.

También decidir si «total definido» incluye escenarios desconectados/editoriales
o solo el subgrafo alcanzable publicado. El código actual evalúa el recorrido
conocido y solo declara total completo al llegar a FIN; no entrega ese nuevo N
global. Los recorridos ejecutables siguen restringidos a una pregunta por escena,
sin ciclos alcanzables. No ampliar navegación por una decisión de calificación.

Separar tres hechos: FIN alcanzado, cobertura de preguntas y modalidad de evaluación.
Un recorrido legítimo terminado no debe convertirse silenciosamente en PARCIAL
solo porque otras ramas no se visitaron. Definir asimismo cierre voluntario
incompleto: el cero autorizado por vencimiento no lo resolvía automáticamente.

### D03. Fuente de puntajes y mapeo de niveles

`cases/infrastructure/models/caso.py::PreguntaModel` conserva ID, escenario, orden
y enunciado, sin puntaje global ni máximo de pregunta. `caso_schemas.py` es estricto:
un nuevo campo no se puede enviar como si estuviera soportado. La autoría actual
almacena `OpcionSchema.valoraciones`, `ValoracionOpcionModel.puntaje`,
`NivelRubricaModel.puntaje` y pesos/descriptores por criterio.

No se demuestra que un puntaje 5 signifique 100 ni que correcto=True signifique
logro máximo. Si los máximos docentes son distintos, sumar valores crudos no
garantiza escala 0–100 ni igualdad de preguntas. Aclarar el significado y, si
procede, una normalización explícita aprobada; no usar el máximo observado de
las alternativas como máximo académico por deducción.

La fuente debe ser la definición docente autorizada de la versión exacta: valores,
unidades, rango, máximos si aplican, matriz pregunta-criterio y mapeo a niveles
reales. Publicar debe validar completitud y correspondencia; contenido/política
publicados quedan inmutables. Cambios físicos/DSL necesitan diseño y aprobación
antes de implementarse; no se añade una columna ni una nueva entidad aquí.

### D04. Dos decimales y ausencia de redondeo intermedio

Conservar exactitud interna; dos decimales de salida no eligen el desempate final.
Por ejemplo, el valor exacto 2.345 da 2.35 con HALF_UP y 2.34 con HALF_EVEN.
Elegir modo, etapa y política versionada; definir si «dos decimales» es solo
presentación o también cuantización de la nota persistida. No utilizar float,
el cast NUMERIC ni el contexto Decimal global como decisión académica.

Hay un bloqueo adicional: el calculador igualitario actual rechaza un aporte
no Decimal finito (100/3), y resultado_criterio guarda NUMERIC(5,2). Aunque el
total sea exactamente 100, tres detalles exactos de 100/3 no caben. Redondearlos
a 33.33 o repartir 33.34 alteraría igualdad/precisión sin aprobación.

El diseño posterior debe preservar aportes exactos (por ejemplo, racionales en
una representación histórica aprobada) y cuantizar solo la salida final con
la regla elegida. Más decimales fijos no representan exactamente 1/3. Cambiar
el significado del detalle de aporte a logro o guardar aproximaciones de
presentación exige contrato explícito y adaptación física, no un parche oculto.

### D05. Repetición y unidad de evaluación académica

La identidad académica del estudiante no es la identidad de la evaluación.
Compartir caso, rúbrica, docente, grupo o sesión no demuestra que dos intentos
sean la misma evaluación; tampoco dos versiones del mismo caso son equivalentes
automáticamente. S6 propone la mayor nota únicamente dentro de un grupo de
evaluación declarado, con intentos válidos y autorizados.

Hoy participación pertenece a una asignación/matrícula y convocatoria; sus
intentos conservan esa referencia. `PermisoIntentoExtraORM` se vincula a una
participación, y `start.py` valida creador/consumo con locks. No modela mover ese
intento a otro caso ni agrupar otra participación de forma oficial.

Recomendación de diseño, **pendiente de aprobación**: referencia estable de
evaluación declarada por servidor y relación de concesión origen→destino,
estudiante, actor, motivo, vigencia y usos. Estudiar primero una referencia
explícita a asignación raíz entre asignaciones existentes; no crear otra entidad
ni usar similitudes de datos como agrupación. Definir alcance antes de elegir FK,
cardinalidad y migración. Caso distinto conserva nueva asignación, convocatoria,
versión y participación; nunca sustituir referencias históricas del intento.

Resolver quién autoriza si los creadores de origen/destino son distintos, si el
permiso concede un inicio o varios y hasta cuándo. RN-16 exige al creador; no
ampliarlo a todo DOCENTE por la expresión «cuando considere necesario». RN-16/
RF-25 tampoco autorizan iniciar en una sesión FINALIZADA: una nueva oportunidad
necesitaría un contexto de sesión permitido y explícitamente vinculado.

Para consolidar, definir qué resultados válidos participan, cómo comparar notas
exactas/finales y cómo preservar empates y procedencia. Mayor nota no autoriza
elegir silenciosamente primer/último intento empatado. No incluir pendientes,
ausencia sin resolver o resultados LAB como oficiales. Correcciones posteriores
de un intento obligan a recalcular candidato y reautorizar su publicación.

### D06. Ausencia sin intento, confirmación y rectificación

Sin intentos no implica ausencia. Confirmación debe verificar convocatoria,
matrícula, estado de sesión y ausencia real con autorización docente persistente.
Faltan el momento habilitado y el tratamiento de retiros. Debe competir de forma
segura con inicio/retirada/publicación bajo la misma referencia académica.

El evento requiere sujeto verificable, actor, instante, motivo y evidencia; la
rectificación referencia el anterior y conserva ambos. No se borra ni edita la
historia para corregirla. Tras publicación, la rectificación prepara un candidato:
no cambia la versión oficial vigente sin nueva autorización.

`resultado_intento` exige intento NOT NULL y modalidad COMPLETA/PARCIAL;
`resultado_participacion` del ER exige participación NOT NULL. El flujo vigente
exige consentimiento antes de crear participación. Por tanto, un ausente sin
P/I no cabe con seguridad creando una fila artificial para cumplir FK. Tampoco
se inventa un nivel cero para resultado_criterio.id_nivel obligatorio.

Hace falta aprobar dónde se conserva la ausencia confirmada vinculada a
convocatoria/matrícula y cómo representa su cero oficial sin intento. Puede exigir
adaptar relaciones del resultado conceptual; no se crean tablas, se vuelven
nullable FK ni se altera el ER en este documento.

### D07. Visualización provisional y seguridad entre estudiantes

S6 permite al docente configurar publicación provisional al terminar el intento,
con nota/desglose/correctas/explicaciones. S1 prohíbe anticipar justificaciones
durante la resolución. El fin del intento propio no implica el fin de la sesión,
de los intentos de compañeros ni de futuras repeticiones del mismo caso.
Mostrar las correctas puede comprometer esos otros intentos; respuestas propias
inmutables no evita compartir la solución por fuera de la plataforma.

Se necesita aprobación expresa de una política de divulgación:

- Embargo de soluciones hasta cierre colectivo autorizado, conservando una
  consulta provisional de alcance restringido si se aprueba ese subconjunto.
- O divulgación inmediata completa con aceptación explícita del riesgo para
  compañeros/repetidores/reutilización del caso. No declararla segura por defecto.

Ambas modifican o precisan S6; ninguna se adopta aquí. Definir si el interruptor
pertenece a sesión/asignación, cuándo se fija, quién puede cambiarlo y su historia.
Se recomienda ámbito de sesión/asignación con versión de política y auditoría,
no modificar el caso publicado ni confiar en un parámetro del estudiante.

Una lectura provisional exige titularidad y cierre persistido, configuración
servidora vigente, reglas de embargo y proyección autorizada de la versión exacta.
No mostrar soluciones de preguntas futuras/no autorizadas por deducción. La
etiqueta PROVISIONAL es obligatoria; no alimenta reporte ni aviso de nota oficial.
Retirada de convocatoria y acceso histórico del estudiante también necesitan
su regla: conservar antecedentes no concede acceso implícito a una cuenta retirada.

### D08. Padrón, publicación y correcciones oficiales

Conservar convocatorias retiradas como antecedentes es distinto de incluirlas
en el denominador de publicación o declararlas ausentes. Aprobar el corte del
padrón y la situación de cada retirada antes/después de intento y publicación.
No sustituir notas faltantes por cero para completar un lote.

Diseño recomendado: candidato consolidado con fuentes/políticas inmutables;
autorización docente sobre un lote y revisión concretos; publicación atómica
de todo el conjunto aprobado. Revalidar rol/ámbito, padrón, cierres, ausencias,
permisos, resultados y huellas dentro de la transacción. La consulta de preparación
no es una autorización durable. Reintentos con identidad estable no vuelven a
publicar ni duplican avisos.

Una corrección crea nueva revisión candidata con actor, motivo, revisión base,
fuentes y cambios; **la última publicación continúa vigente**. Una nueva
autorización cambia atómicamente la referencia vigente conservando la anterior.
Versionar el lote evita mezclar estudiantes con revisiones oficiales distintas
sin que esa mezcla haya sido autorizada. Precisar si se republica el lote entero
y cómo se notifican rectificaciones, incluyendo correcciones de ausencia.

La unicidad actual por intento y la inmutabilidad de resultados técnicos impiden
sobrescribir/reinsertar una nueva nota del mismo intento en ese repositorio.
No desactivar sus guards ni actualizar LAB→OFICIAL. Aprobar almacenamiento
versionado de consolidación/publicación/rectificación y su relación con fuentes
antes de crear migraciones. El ER resultado_participacion tiene nota_definitiva
DECIMAL(4,2), insuficiente para 100.00; no tiene ORM oficial integrado. Una futura
adaptación a 0–100 necesita aprobación técnica específica, como la ya realizada
solo para resultado_intento, sin reescribir resultados históricos.

### D09. Reportes Excel/PDF y semántica de columnas

Definir la unidad de fila: estudiante/evaluación, participación o intento. Una
recomendación técnica es separar resumen oficial, detalle de intentos y
antecedentes en hojas/secciones enlazadas, sin duplicar notas por joins a
criterios. Columnas mínimas propuestas: identificadores públicos permitidos,
estudiante/grupo, caso/versión, convocatoria/estado, participación/intento,
modalidad, nota y versión oficial, fechas, duración y referencia de corrección.

Faltan estados aprobados para retiradas/no iniciadas y la duración solicitada:
tiempo concedido, tiempo cronológico entre marcas o tiempo académico computable
no son sinónimos. Exportar marcas y duración concedida con nombres explícitos es
distinto de inventar una métrica académica. No añadir APROBADO/REPROBADO sin umbral.

Los dos formatos deben salir del mismo snapshot oficial vigente, con ámbito
docente, numeración/fecha de publicación y procedencia; nunca consultar el
candidato no publicado como si fuera vigente. Conservar antecedentes retirados
y marcar correcciones mediante referencias, no borrar las filas anteriores.

Actualmente `identity/application/services.py::ServicioReportes.descargar`
genera CSV y valida filas; el endpoint registrado está cerrado. Reutilizar sus
validaciones y lectura autorizada, no presentar un CSV renombrado como .xlsx/.pdf.
Proponer formato explícito/negociación de contenido antes de cambiar el contrato.
Verificar celdas, fechas, tipos numéricos, caracteres y páginas; evitar fórmulas
inyectadas en celdas y ejecución de HTML/URLs externas en PDF. Las dependencias
de generación se justificarán antes de instalarse.

## 5. Arquitectura reutilizable y límites físicos comprobados

| Componente existente | Reutilización | Límite que impide habilitarlo como oficial |
|---|---|---|
| `participation/application/evaluation_service.py::ServicioEvaluacion` y `domain/estrategias_evaluacion.py` | Clasificación, evidencia del intento y separación del cierre | `_marco` depende del conjunto aplicable; ausencia requiere participación actual; no inventar universo global. |
| `application/academic_policy.py::PoliticaAcademicaConfirmada`, MapeoEscala100, ResolucionNivelesAcademicos | Escala, pesos efectivos por criterio, ceros confirmados y puerto de resolución | No hay mapeo/agregador oficial; cierre voluntario incompleto y ramas globales no resueltos. |
| `domain/calculador_rubrica.py::CalculadorRubrica` y PoliticaCalculo | Un solo calculador, exactitud y fórmula histórica conservada | Promedio igualitario actual rechaza redondeo configurado y aportes periódicos; adaptar tras aprobar D01–D04, no duplicar Strategy/calculador. |
| Cases `models/caso.py`, `models/rubrica.py`, `api/schemas/caso_schemas.py` | Preguntas/opciones, valoraciones y rúbrica inmutable por versión | No hay puntaje global por pregunta; Decimal persistido no certifica porcentaje/logro ni nivel. |
| `infrastructure/cases_route.py::RecorridoCasesSQLAlchemy`, `cases/application/graph.py::GrafoVersion` | Ruta real, pertenencia y privacidad de pregunta habilitada | Conjunto de ruta no equivale a todas las preguntas del caso; multipregunta/ciclos siguen cerrados. |
| `infrastructure/persisted_evaluation.py` y `result_repository.py` | UoW, trazabilidad canónica, huellas, reproducción y rechazo de duplicados | `ResultadoTecnico.oficial=False`, lectura oficial cerrada. Guardado técnico no es consolidación ni publicación. |
| `infrastructure/result_models.py` | FK compuestas criterio/nivel/rúbrica, unicidad y NUMERIC(5,2) final | CHECK ambito=LABORATORIO; intento obligatorio; detalle de criterio a dos decimales. No puede almacenar ausencia ni publicación oficial directamente. |
| `application/evaluation_readiness.py` e `infrastructure/evaluation_readiness.py` | Snapshot docente de convocatorias, incluidas retiradas/sin participación e intentos históricos | `publicable=False`; inventario no es padrón oficial ni confirma ausencia. |
| `evaluation_ports.py::PoliticaConsolidacionPort` y AusenciasPort | Extender los contratos existentes cuando el alcance esté aprobado | Consolidación actual recibe una participación; no agrupa varias por otra evaluación/caso. No hay proveedor oficial durable de ausencias. |
| `identity/infrastructure/academic_models.py::PermisoIntentoExtraORM` y `participation/infrastructure/start.py` | Concesiones trazables, creador del caso, locks y consumo transaccional | Permiso por participación; no identifica evaluación raíz ni destino de caso diferente. |
| `cases/application/answer_feedback.py` | Recuperar explicaciones de la alternativa real en la versión histórica | Su existencia no aprueba la divulgación RF-14. Separar de feedback general docente RF-26 ya operativo. |
| Identity/JWT, resolver académico y ámbito SQL docente | Actor activo, permisos vigentes y pertenencia | No existe rol ejecutable DOCENTE ADMINISTRADOR; ADMINISTRADOR no obtiene facultades docentes por el nombre. |
| Notificaciones/Observer SQL existentes | Aviso causal tras publicación autorizada, sin doble efecto | No emitir calificación al cerrar ni confundir registro interno con correo entregado. RF-27 de notas permanece cerrado. |

No hay un almacén oficial versionado ni una ruta Evaluation en app.main. No se
introducen modelos nuevos, se usa el repositorio LAB como oficial, ni se añade
infraestructura Outbox por anticipación.

## 6. Secuencia de implementación propuesta y aceptación

| Orden | Incremento acotado | Prerrequisito y archivos principales | Aceptación verificable |
|---|---|---|---|
| 1 | Exponer preparación académica privada docente, sin notas ni permiso de publicar | Reutilizar consultas readiness e Identity/ámbito persistente; contrato HTTP lector. Es el siguiente incremento independiente de la fórmula, sujeto a revisión de su proyección. | HTTP/JWT/PG17: solo sesión propia, retiradas/sin P, versiones históricas, cero DML/flush/commit y sin notas/soluciones; `publicable` sigue false. |
| 2 | Especificación docente versionada de puntajes/matriz y universo evaluable | Aprobar D01–D03. Revisar Cases DSL, models/caso.py, models/rubrica.py, validadores, snapshot y evaluación histórica. Diseñar y autorizar antes cualquier columna/FK. | Ejemplo docente calculable a mano, rechazo de referencias cruzadas/incompletas; ramas y máximos comprobados, sin modificar publicaciones antiguas. |
| 3 | Calcular y persistir resultados académicos candidatos RF-13/24 | Aprobar D04 y adaptación exacta de detalle/resultado; reutilizar CalculadorRubrica, política, Strategy y repositorios con contrato de ámbito explícito. | Casos completo, vencido y voluntario incompleto según regla; escala y pesos; 3 criterios/tercios; modo final aprobado; otra Session, concurrencia/rollback; ninguna publicación. |
| 4 | Ausencia confirmada y rectificada RF-24 | Aprobar D06, D08 y representación sin P/I ficticios. Servicio/UoW durable con actor/razón/historia. | Confirmación explícita; sin inicio no basta; cero solo tras confirmar; rechazo de ámbito ajeno, competencia con inicio, rectificación sin pérdida y sin tocar vigente. |
| 5 | Autorización de repetición y consolidación RF-25 | Aprobar D05: autoridad creador, cantidad/vigencia, raíz de evaluación y destino. Reutilizar permisos/start y extender consolidación con vínculos explícitos. | Mismo/distinto caso conservan versiones; consumo único; mayor nota solo de la misma evaluación; independientes nunca se mezclan; sesiones finalizadas rechazadas. |
| 6 | Consulta provisional RF-14 | Aprobar D07 y contar con cálculo candidato real. Adaptar DTO/lector existente, configuración servidora trazable. | Titular cerrado y embargo/configuración; otros alumnos y repetidores protegidos; etiqueta provisional, sin nota oficial ni aviso oficial. |
| 7 | Publicación y nueva publicación oficial | Aprobar D08: padrón, retiradas, cierres, revisiones y almacenamiento. UoW existente más diseño aditivo autorizado, nunca conversión de filas LAB. | Lote completo, actor con ámbito, reintento estable, concurrencia/rollback, corrección candidata mantiene vigente anterior y cambio atómico autorizado. |
| 8 | Reportes RF-16 y avisos dependientes RF-27 | Aprobar D09, disponer de snapshot oficial y contrato de archivo; reutilizar validaciones CSV, autorización y notificaciones. | XLSX/PDF reales del mismo lote, sin duplicados ni fórmulas, antecedentes/correcciones visibles; actor ajeno rechazado; aviso por publicación correcta y sin doble efecto. |

Las etapas anteriores son una secuencia de trabajo dentro de los RF existentes,
no fases nuevas del proyecto. Orden 1 puede avanzar sin algoritmo académico, pero
no se implementa en esta entrega. Investigación de esquema, diseño de DTO lector
y pruebas de autorización pueden prepararse antes; no las confundir con cerrar
RF-13/14/16/24/25. Rectificación sin soporte durable y publicación a medias no son
incrementos aceptables.

## 7. Endpoints futuros para Postman — NO registrados ni incluidos como disponibles

Nombres orientativos sujetos a revisión del contrato de API; no se añaden a las
colecciones confirmadas en este checkpoint.

| Superficie propuesta/reutilizada | Actor y condición | Cuándo incorporarla |
|---|---|---|
| GET `/scheduling/sesiones/{sesion_id}/evaluacion/preparacion` | DOCENTE y ámbito persistente; lector sin notas | Tras aceptación del orden 1. |
| POST `/scheduling/sesiones/{sesion_id}/evaluacion/calculos` | DOCENTE autorizado; política aprobada y versión exacta | Candidatos sin publicación, con identidad idempotente y rollback. |
| POST `.../evaluacion/ausencias/{convocatoria_id}/confirmaciones` y `.../rectificaciones` | DOCENTE de ámbito, razón y revisión base | Tras representación aprobada sin intento ficticio y control concurrente. |
| POST `/api/v1/identity/excepciones/repeticiones` existente, actualmente 503 | Creador autorizado y origen/destino verificables | Extender el contrato existente si procede; no crear un segundo servicio de permisos. |
| PUT `/scheduling/sesiones/{sesion_id}/evaluacion/visualizacion` | DOCENTE con configuración versionada | Tras resolver embargo y efecto de cambios, nunca parámetro estudiantil. |
| GET `/api/v1/participations/{p}/attempts/{i}/result`, contrato aislado existente | Estudiante titular, intento cerrado y permiso de visualización | Adaptar explícitamente DTO para distinguir provisional/oficial; no montar el router general ni revelar LAB bajo etiqueta definitiva. |
| POST `/scheduling/sesiones/{sesion_id}/evaluacion/publicaciones` | DOCENTE y autorización de lote/revisión completos | Solo con almacenamiento versionado y controles de integridad aprobados. |
| POST `.../evaluacion/correcciones`, GET `.../evaluacion/publicaciones/vigente` | Candidato docente / lectura docente de ámbito | Nueva autorización separada, sin alterar vigente al guardar candidato; estudiante solo su proyección privada. |
| GET `/api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte` existente con formato explícito propuesto | DOCENTE de ámbito; snapshot oficial vigente | Aprobar negociación XLSX/PDF y compatibilidad con contrato CSV antes de habilitar. |

RF-27 `/scheduling/calificaciones/notificar` sigue cerrado. Su esquema actual
recibe participacion_id UUID, mientras Participation persiste un INTEGER: no
convertirlo ficticiamente ni pasar esos dos UUID como prueba de una publicación.
La futura notificación debe derivarse del lote oficial y resolver destinatarios
persistentes; adaptar/deprecar el contrato con revisión expresa, sin sistema paralelo.

Postman deberá distinguir cálculo, provisional y oficial. Añadir después pruebas
positivas/negativas para mapeo, denominador, límites, redondeo, empates, agrupación,
ausencias, retiradas, embargo y republicación; no solo HTTP 200. Mantener blancos
los secretos y separar las superficies de laboratorio de las rutas aprobadas.

## 8. Decisiones concretas para profesora/equipo e institución

1. ¿Se mantienen simultáneamente criterios y preguntas iguales? Entregar una
   matriz real de tres preguntas/dos criterios con sus resultados esperados.
2. ¿Se acepta que una rama no visitable reste nota y que el máximo alcanzable
   pueda ser inferior a 100? Definir el total y un ejemplo Q1→Q2 o Q3.
3. ¿Qué configura exactamente el docente por pregunta/opción y cómo se transforma
   en logro/nivel? Definir rango/máximo y criterios no aplicables.
4. ¿Cuál es el modo final de redondeo? Resolver 2.345 y los detalles 100/3 sin
   redondeo intermedio. Aprobar representación exacta del desglose.
5. ¿Cómo se clasifica el cierre voluntario incompleto y un FIN legítimo con ramas
   no visitadas? Distinguir cobertura de nota y de modalidad COMPLETA/PARCIAL.
6. ¿Cuándo confirmar/rectificar ausencia? ¿Qué ocurre ante inicio concurrente,
   retirada o publicación previa? Aprobar representación sin P/I artificiales.
7. ¿Quién autoriza repetición si cambia el creador/caso/sesión, con cuántos usos
   y vigencia? Declarar explícitamente qué asignaciones son una evaluación común.
8. ¿Qué resultados compiten por la mayor nota y cómo se conservan empates y
   correcciones? No agrupar por parecido de caso/rúbrica/grupo.
9. ¿Las soluciones pueden revelarse mientras compañeros/repetidores aún pueden
   responder? Elegir embargo o aceptar expresamente el riesgo de divulgación.
10. ¿Dónde/cuándo configura el docente la visualización y qué habilita a cada
    estudiante? La configuración no es autorización de publicación oficial.
11. ¿Cuál es el corte del padrón y el tratamiento calificable de cada retirada?
    Definir lote, cierres y nueva autorización de correcciones.
12. ¿Cuál es la fila/estado/duración oficial del Excel/PDF y qué información de
    corrección debe aparecer? No introducir umbrales de aprobación por deducción.

Las propuestas de S6 deben validarse por el responsable académico y registrar
autor, fecha, versión, contenido y evidencia de aprobación. Los cambios de
persistencia/permisos requieren además revisión técnica y del responsable de
Identity/Cases/Scheduling. No se atribuye aprobación institucional a este texto.

## 9. Estado y siguiente acción

RF-13, RF-14, RF-16, RF-24 y RF-25 mantienen **BLOQUEADO** en la matriz vigente;
RF-27 sigue PARCIAL por los avisos internos de feedback; los avisos de notas
oficiales siguen cerrados. Totales sin cambios: 14 IMPLEMENTADO,
8 PARCIAL y 5 BLOQUEADO. No se modifica la matriz por recibir propuestas sin
implementación/aceptación nueva.

Recomendación inmediata: aprobar la proyección de la consulta docente de
preparación (orden 1) como próximo incremento técnico y obtener en paralelo las
respuestas D01–D09 con ejemplos numéricos. No prometer cierre de Evaluation
antes de resolver denominador/puntajes/redondeo y la representación oficial.

Este documento queda **sin commit**, después del único checkpoint autorizado.
No hay código productivo, migraciones ni rutas modificadas; no se consultaron
bases permanentes, no se ejecutó Docker y no se implementó un algoritmo nuevo.
Las ocho políticas auditadas previamente y las evidencias históricas se preservan.
