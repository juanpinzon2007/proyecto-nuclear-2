# BD2-02D — Decisión mínima de compatibilidad ER28–Backend

2026-11-02 · Rama `feature/integracion-backend` · **Propuesta para aprobación; no DDL autorizado.**

## 1. Decisión recomendada y límite de la respuesta

Recomiendo **un núcleo académico de las mismas 28 tablas, enriquecido dentro de
esas tablas, con una fila de `caso` por edición, doble identidad persistente y
valoraciones multicriterio estructuradas en `opcion_respuesta`**, consumido mediante
adaptadores que preserven los contratos actuales. La transición conserva las
estructuras existentes hasta demostrar cada sustitución, sin aprobarlas como
tablas permanentes adicionales. No se propone el modelo de 40.

**Conservar el ER literal sin modificarlo y mantener simultáneamente todas las
funcionalidades actuales es imposible.** Dos versiones con rúbricas distintas no
tienen identidad separada dentro de una misma fila de caso; la asignación original
solo referencia esa fila; una FK de criterio por decisión no almacena la matriz
de puntajes de todas sus opciones para todos los criterios. BD2-02C lo demostró
mediante edición seguida de lectura y rechazo del contrato real de Cases.

Las seis capacidades solicitadas son representables con **28 nombres de tabla**
si se aprueban los cambios semánticos y la desnormalización controlada de este
documento. Eso **no conserva el ER aprobado literalmente**, ni constituye una
demostración ejecutada de esta propuesta. Una colección JSONB de valoraciones
introduce una relación lógica adicional aunque no incremente tablas: necesita
aprobación expresa, integridad entre tablas y pruebas, no solo un CHECK de JSON.

Tampoco puede declararse resuelto un **esquema físico único de exactamente 28
tablas para todo el backend**: identidad académica, espacio y auditoría no tienen
todavía destinos equivalentes aprobados. Esta propuesta no los oculta en textos,
no los borra ni cambia su cardinalidad para cuadrar el conteo. `alembic_version`
es además una tabla técnica: el criterio de 28 debe referirse a tablas académicas
o reconocer explícitamente esa excepción técnica, sin borrar el control Alembic.

## 2. Evidencia acotada utilizada

- Fuente oficial: [sps.dbml](../../app/modules/identity/reference/sps.dbml). No se modifica.
- [BD2-02C](laboratorio_compatibilidad_cases/INFORME_BD2_02C.md): recorrido INTEGER posible, asignación sin versión, campos ausentes y matriz multicriterio no representada. No se repite el laboratorio.
- [ConsultaVersionPublicada/ReferenciaVersionPublicada](../../app/modules/cases/application/published_version.py): consulta inyectable, UUID de caso/versión/rúbrica, número y `version_regla`. Es el contrato que debe seguir devolviéndose completo.
- [Cases ORM](../../app/modules/cases/infrastructure/models/caso.py) y [rúbrica/valoraciones](../../app/modules/cases/infrastructure/models/rubrica.py): versiones y matriz opción×criterio.
- [Scheduling](../../app/modules/scheduling/infrastructure/models.py): sesión vinculada a `version_caso.id`; convocatoria individual y auditoría.
- [8A](../../app/modules/participation/infrastructure/integration.py) y [sus referencias](../../app/modules/participation/application/integration_ports.py): autorizaciones antes de Cases; sin escritor productivo.
- [CasesEvaluacionPort/RepositorioResultados](../../app/modules/participation/application/evaluation_ports.py) y [DatosEvaluacion](../../app/modules/participation/domain/evaluation.py): marco histórico coherente, políticas identificadas y publicación posterior a persistencia.
- RF citados según [la matriz documental existente](E_TRAZABILIDAD_RF.md); las referencias técnicas a versión/UUID son decisiones de compatibilidad, no requisitos académicos nuevos atribuidos al profesor.

22 tablas ORM y 1142 aprobadas/38 omitidas son estado histórico. En BD2-02D no
se importó metadata, no se inspeccionaron datos físicos ni se ejecutaron pruebas.

## 3. Tabla de decisiones y cambios inevitables

Todos los nombres de atributos nuevos son propuestas; su detalle se congela solo
después de aprobación. Ninguna fila significa que ya exista una migración.

| ID | Entidad/atributo o restricción propuesta | Justificación e impacto en el ER académico | RF relacionado | Impacto Cases / Scheduling / Participation | Aprobación necesaria |
|---|---|---|---|---|---|
| D1 | `caso.id_caso` INTEGER se conserva; añadir `uuid_caso`, `uuid_version`, `numero_version`, `contenido_congelado`; UNIQUE(uuid_version), UNIQUE(uuid_caso,numero_version), número positivo | Cada fila pasa a ser una edición asignable; `uuid_caso` agrupa la familia y se repite entre sus ediciones. Cambia el significado de caso, sin tabla nueva. Congelación irreversible del contenido tras publicación | RF-05/09/12/14/17; UUID/versionado por compatibilidad | C conserva caso/versión públicos separados; S asigna edición exacta; P conserva marco histórico | Profesor/equipo: cambio de granularidad y atributos. No se aprueba aquí |
| D2 | `escena`, `decision`, `opcion_respuesta`, `rubrica`, `criterio_rubrica`, `nivel_criterio`: añadir `uuid_publico UNIQUE`; mantener PK/FK INTEGER | Conservar UUID reales de cada entidad actual y resolver ambos sentidos. No usar nombres/orden para emparejar. Un UUID por fila fuente demostrada, no una conversión numérica | RF-05–08/17; compatibilidad de contratos | C adapta consultas/serialización; S/8A reciben UUID existentes; P usa INTEGER internamente | Equipo/validación del modelo ampliado |
| D3 | `caso`: añadir `desarrollo_situacional`, `contexto_historia`, `tiempo_estimado_min`; conservar `introduccion_teorica`. `rubrica`: `version_regla`; `nivel_criterio`: `puntaje`, `descriptor`, conservando `logro_porcentaje` | Evitar fusionar dos textos o equiparar puntaje y porcentaje. Los campos oficiales sin fuente equivalente quedan pendientes de completar, no se rellenan con datos ficticios. Máximo, pesos y escalas requieren equivalencia aprobada | RF-05/13/17/18 | C recupera campos íntegros; S conserva comparación duración/estimado; P no deriva una fórmula de un booleano | Profesor/equipo para nuevos campos; académico para equivalencias de escala |
| D4 | `opcion_respuesta.valoraciones JSONB`; `decision.id_criterio` pasa a admitir NULL cuando el origen no designa un criterio único | Matriz arbitraria opción×criterio, con decimal exacto. Se conserva el criterio directo original si existe con significado acreditado; no se elige uno como «principal» por conveniencia. Relación obligatoria original se vuelve opcional y se añade colección lógica N:M | RF-07/09/13/17 | C reconstruye `valoraciones`; su Chain mantiene exigencia de valoración por cada criterio; P conserva entradas de cálculo; S no calcula | **Profesor/equipo: desnormalización y cambio de cardinalidad. Sin esta aprobación, no hay sustitución multicriterio** |
| D5 | `asignacion_caso.id_caso` apunta a la fila-edición D1; añadir `uuid_sesion UNIQUE`, `docente_usuario_id`, `lugar`, `mensaje_personalizado`, `finalizado_en`; inmovilizar edición al convocar | Conserva FK oficial, precisando que no es familia ni «última versión». Docente de sesión puede diferir del creador. Lugar/mensaje/cierre no deben perderse | RF-18/19/23 | S adapta sesión↔asignación solo con grupo/espacio acreditados; C resuelve versión desde la edición; P usa referencia fijada | Equipo/academia: equivalencias de programación y granularidad |
| D6 | `participacion`: `uuid_convocatoria UNIQUE`, hash individual, estado de convocatoria separado del estado de participación y fecha de retirada; conservar FK asignación/matrícula | Representar invitación antes del primer intento, sin confundir RETIRADA con VENCIDO. UNIQUE(asignación,matrícula) no demuestra por sí solo equivalencia con convocatoria | RF-01/04/20/21/24 | S/Identity deben conservar JWT de convocatoria, código individual y titularidad; P no recibe permiso por existir una fila | Académico/equipo: participación previa al intento, roster y vínculo con membresía; bloquea sustitución completa de Scheduling |
| D7 | `intento`: duración concedida e instante de vencimiento histórico; `asignacion_caso`/fechas: zona explícita y guardas de edición; conservar claves originales | No reconstruir plazos antiguos usando una duración cambiada. Conversión de timestamps legados solo con zona demostrada. No se altera aplicabilidad de consentimiento ni se inventa RF-22 | RF-10/11/22/23/25 | S conserva política; P reloj/estado/duración inyectables y congelados | Equipo para persistencia; académico para ventana, consentimiento y repetición aún pendientes |
| D8 | `resultado_intento` y `resultado_participacion`: modalidad, referencia de política/motor, `contexto_calculo JSONB` y hash canónico; conservar nota/fecha y UQ originales. `resultado_criterio` mantiene FK compuesta | Persistir evidencia, ruta efectiva, parámetros y referencias exactas. Cabecera de ausencia sin intento usa contexto en resultado_participacion; no crea intento/nivel ficticio. Es otra desnormalización explícita, no una tabla de detalle escondida | RF-12–16/24/27 | P guarda solo definitivos atómicos; C proporciona marco congelado; S aporta roster/cierre verificados | Equipo para formato/integridad; académico para fórmula, escala, redondeo, ausencia y consolidación |
| D9 | FK/validaciones de pertenencia entre edición, escena, personaje, decisión, opción, criterio y nivel; congelación de grafo y resultados | Las FK originales permiten ciertos cruces entre casos; columnas auxiliares con FK compuestas donde sea viable, y constraint triggers transaccionales donde no. No afirmar que JSONB tiene FK nativa | RF-06/10/11/13/17 | C impide grafo ajeno; P rechaza evidencias fuera de edición; S no sustituye edición | Equipo: integridad técnica, con revisión de cambios al ER |
| D10 | `retroalimentacion_docente`: posible FK a participación, revisando UQ por asignación; `notificacion`: conservar UUID, canal, estado, destino real y vínculos individuales | Necesario para retirar soporte actual sin perder feedback individual o entrega. No copiar comentario grupal a todos los alumnos ni inventar autores | RF-15/21/26/27 | Seguimiento/Identity y S deben adaptar sus contratos antes de retirar estructuras; P solo notifica tras persistencia | Académico/equipo: ámbito individual y cardinalidad de feedback; contrato de entrega |

D1–D4 y D8 resuelven el núcleo de las seis capacidades, condicionadas a D9 y a
políticas disponibles. D5–D7 son necesarias para conectarlo al ingreso real; D10 y
los soportes de §7 impiden declarar el backend completo reconciliado por ese solo
núcleo. No se propone aplicar diez cambios juntos ni habilitar funciones pendientes.

## 4. Cómo se preservarían historia e integridad

### 4.1 Identidades y versiones: correspondencia verificable, no conversión

Ejemplo conceptual, **no datos existentes ni UUID de prueba**:

| Origen verificado | Destino propuesto |
|---|---|
| Familia con UUID F, versión UUID V1, número 1 | Caso INTEGER I1, uuid_caso=F, uuid_version=V1, numero_version=1 |
| Misma familia F, versión UUID V2, número 2 | Caso INTEGER I2, uuid_caso=F, uuid_version=V2, numero_version=2 |
| Rúbricas originales R1 y R2 | Una rúbrica INTEGER por I1/I2; uuid_publico conserva R1/R2 |
| Sesión asignada a V1 | Asignación con FK a I1, aunque exista I2; uuid_sesion conserva su UUID fuente |

F, V1, V2, R1 y R2 son símbolos para valores fuente, no UUID generados. Los
INTEGER nuevos los asigna la base de destino; los UUID existentes se copian sin
alteración. Para contenido nuevo, el servicio genera una sola vez los UUID de
familia/versión/hijos según el contrato actual, los persiste en la misma transacción
y los reutiliza; no regenera identidades al leer ni crea vínculos históricos.

UNIQUE por UUID de versión/hijo, UNIQUE(familia,número), FK por edición y validación
de creador consistente en la familia evitan mezcla. La agrupación por F no es una
FK a una entidad familia inexistente: el servicio controla creación/numeración
serializando por familia y la base impide números duplicados. No se presupone una
correspondencia entre UUID docente y usuario INTEGER: se consume el resolver real
y se rechaza ausencia/ambigüedad.

Todas las escenas, personajes, objetivos, rúbrica, criterios y opciones de una
edición se congelan juntos. Escrituras de hijos y publicación deben bloquear la
misma fila-edición; una marca irreversible de congelación impide desbloquear el
contenido cambiando el estado a BORRADOR. Archivar cambia disponibilidad para nuevas
asignaciones, no borra el grafo. El adaptador de ingreso conserva la consulta exacta
PUBLICADO de hoy; leer resultados históricos archivados requiere un puerto de
lectura histórica autorizado distinto, no relajar la autorización de ingreso.

### 4.2 Multicriterio: formato e integridad necesarios

Formato propuesto por opción, usando solo INTEGER reales del destino:

```json
[{"id_criterio": 21, "puntaje": "1.25"}, {"id_criterio": 22, "puntaje": "0.75"}]
```

Es una lista para detectar criterios repetidos; los decimales son cadenas canónicas
convertidas a Decimal/NUMERIC sin float. No se infieren desde `es_correcta`, pesos o
nivel. Un conjunto de 6 opciones y 2 criterios conserva sus **12 valores independientes**
en seis colecciones. En el ER literal no hay lugar equivalente: `resultado_criterio`
es un resultado de un intento, no una valoración de autoría; reutilizarlo crearía
intentos ficticios o cambiaría su entidad.

La integridad exige, además de validación de aplicación:

1. CHECK local de array y validación estricta de estructura, IDs, duplicados,
   decimal finito y precisión admitida; nada de claves/valores ignorados.
2. Constraint triggers en opción y cambios relevantes de criterio/rúbrica/decisión
   que comprueben que cada ID existe y pertenece a la rúbrica de **esa edición**.
   Un CHECK PostgreSQL ordinario no verifica otras tablas ni sustituye una FK.
3. En borrador, permitir incompletitud solo si el contrato de edición lo admite;
   al publicar, exigir exactamente los criterios requeridos por la Chain actual.
   Publicación y cambios de criterios/opciones serializados por la misma edición;
   restricciones diferidas al commit para ediciones atómicas sin referencias colgantes.
4. Borrado/cambio de criterio referenciado debe rechazarse o actualizarse junto
   con todas las opciones dentro de la transacción de borrador. Congelado, se
   rechaza la mutación. También hay que validar cambios de padres, no solo INSERT.
5. Usuario de aplicación sin permisos para desactivar triggers o alterar schema;
   pruebas concurrentes y de SQL directo deben intentar vulnerar esas guardas.

Los adaptadores pueden reconstruir el diccionario UUID→Decimal actual usando
`criterio_rubrica.uuid_publico`, sin alterar Builder, Chain o Strategy. `id_criterio`
directo de decisión no se rellena con el primer criterio de la lista. Si se exige
normalización estricta y FK declarativa por cada valor, **esta representación en
28 tablas no satisface esa exigencia**: se debe rechazar D4 y revisar el requisito
de conteo, en otra decisión; no crear una tabla 29 automáticamente.

### 4.3 Reproducción de evaluaciones

Cadena de identidad: resultado→intento→participación→asignación→edición congelada→
rúbrica congelada. Pasos deben corresponder a decisiones/opciones de esa misma
edición; no basta con que sus IDs existan. Una vez iniciado un intento, su asignación
no puede apuntar a otra edición y sus parámetros históricos no pueden cambiarse.

Además de nota y niveles, `contexto_calculo` debe guardar: versión de formato,
edición/rúbrica y hash de contenido, decisiones aplicables ordenadas y selecciones
efectivas, valores multicriterio utilizados, modalidad, parámetros/identificadores
inmutables de política, reglas de escala/redondeo y digest de versión del motor.
El contexto lo construye el servidor y se contrasta con las FK y datos congelados;
no se acepta una fotografía enviada por el cliente. Serialización canónica sin
float; guardar hash detecta cambios, pero **no proporciona autorización ni sustituye
el contenido**.

El código exacto del motor/política debe conservarse como artefacto ejecutable
versionado y recuperable por digest; un texto `v1` o un hash sin ese artefacto no
permite reproducir. Hasta poder recuperar datos, parámetros y algoritmo, solo puede
asegurarse consulta del resultado guardado, no recálculo reproducible.

Resultado, detalle por criterio y contexto se confirman en una transacción y se
hacen visibles después del commit y autorización. Repetición con misma clave y
mismo contexto devuelve lo persistido; contexto distinto es conflicto, no upsert.
No se diseña aquí una política de rectificación de notas. Ausencia sin intento
requiere roster/cierre acreditados y su contexto en resultado_participacion; nunca
un resultado_criterio con nivel inventado. Si fórmula, consolidación o equivalencias
puntaje/porcentaje no están aprobadas, **no se calcula una calificación oficial**.

### 4.4 Datos históricos: condiciones de traslado

No se conoce el contenido físico de las bases del equipo en esta fase. Antes de
cualquier backfill se exige un inventario autorizado de filas fuente, duplicados,
referencias, timestamps/zonas y escalas reales. Los ejemplos sintéticos previos no
acreditan correspondencias históricas.

El traslado debe leer una fotografía consistente de origen y producir un manifiesto
auditable: UUID fuente→INTEGER destino, familia/edición, conteos por entidad,
relaciones, matriz completa y hashes canónicos. Ese manifiesto es evidencia externa
de migración, no tabla académica adicional ni resolver operativo. El destino guarda
los UUID necesarios para que la correspondencia permanezca recuperable sin él.

Validaciones de aceptación: igualdad de cada campo y valor Decimal; dos versiones
conservadas por separado; todas las referencias de sesión y pasos resueltas a su
edición; evaluación histórica con mismo contexto/artefacto produce el mismo resultado.
Un legado sin título/tipo de escena, máximo de rúbrica, escala, zona o marco histórico
acreditado **no se rellena con defaults ficticios**: se detiene ese lote y sigue
operativo en el esquema actual. Una nota histórica aislada no permite reconstruir
las evidencias que nunca se conservaron; se marca no reproducible, sin falsificarlas.

No escribir en ambos esquemas de forma independiente. Durante traslado, pausar
escrituras del agregado afectado o usar una transacción/coordinar un corte verificado;
comparar lecturas en sombra y mantener reversible la selección del adaptador. No
retirar el origen ni redirigir escrituras hasta superar las equivalencias.

## 5. Comparación breve con mantener el ER literal

| Criterio | Arquitectura recomendada, sujeta a aprobación | ER literal intacto |
|---|---|---|
| Entidades académicas | Mismas 28; atributos, granularidad y relación multicriterio cambian | Exactamente el modelo aprobado sin cambios |
| UUID e INTEGER | Ambos persistidos; traducción acreditada | Solo INTEGER; UUID actuales sin destino |
| Ediciones y asignación | Una fila por edición, UUID/número y congelación; FK exacta | Asignación a caso mutable, sin identidad de edición |
| Matriz opción×criterio | Colección tipada y guardas transaccionales, costo de desnormalización | No representa los valores independientes |
| Reproducibilidad | Posible solo con contexto, grafo y motor retenidos | Nota guardable; no asegura reconstrucción histórica |
| Compatibilidad actual | Adaptadores tras aprobar/balancear campos y datos | Solo lectura parcial del laboratorio; sustitución no compatible |

No se recomiendan reducción de funcionalidad, códigos grupales como identidad,
conversión INTEGER→UUID, entidad polimórfica para esconder valoraciones ni nueva
tabla permanente no autorizada. Si no se aprueban las desviaciones, la decisión
correcta es conservar el backend vigente y mantener cerrada su sustitución ER28.

## 6. Primer incremento autorizable y criterios de aceptación

**Unidad U1: identidad de edición y correspondencia de lectura en Cases, sin
activar Scheduling/Participation ni cambiar el escritor actual.** Solo después de
aprobar D1–D3 para esta unidad. D4 se aprueba antes de importar/publicar contenido
multicriterio; U1 no intenta sortearla. La inyección de 8A ya existe y no se repite.

Archivos concretos propuestos para U1, ninguno modificado/creado ahora:

- `backend/tests/integration/er28_compatibility_support.py`: metadata **privado**
  derivado de las 28 originales, con solo las extensiones D1–D3 aprobadas para
  esta unidad; fixture de dos ediciones y sus rúbricas en base nueva desechable.
  No se registra en Base.metadata ni se hace backfill de datos del equipo.
- `backend/app/modules/cases/infrastructure/er28_published_version.py`: candidato
  de adaptador SQL de lectura que recibe explícitamente Session y tablas de
  destino, busca `uuid_version` exacto y devuelve el DTO existente completo, o
  rechaza. No fabrica campos ni crea motor, tablas o conexiones por su cuenta;
  no se registra como proveedor predeterminado ni en API/8A.
- `backend/tests/integration/test_er28_published_version.py`: paridad de referencia
  con el contrato actual usando datos de origen sintéticos explícitos, unicidad,
  destino inexistente/no publicado/sin rúbrica, conservación de sesión y no autoflush.
  Los UUID de esos fixtures son nuevas entidades sintéticas, no vínculos históricos.

El contrato en `cases/application/published_version.py`, el escritor actual y
8A no necesitan cambiar para U1. Esta unidad prueba solo la referencia de versión,
no importa la matriz multicriterio ni declara equivalente un CasoDetalle completo.

**Primera migración productiva: aún no autorizable con este documento solo.**
La colisión de nombres `caso`/`rubrica` entre origen y destino impide registrar
dos modelos distintos del mismo nombre en el mismo metadata. Antes del DDL se
debe aprobar un destino físico separado para el corte transicional, su ciclo de
versionamiento y la estrategia de importación; no basta con añadir una revisión
al head y convertir la PK actual. Un destino con las mismas 28 entidades es
coexistencia física temporal, no 28 físicas finales. Después de esa decisión se
revisarían los ORM/adaptadores y una revisión posterior al head histórico
`20261101_er28_base_academica`, sin reescribir revisiones ni tocar claves fuente.

Aceptación U1: contrato UUID intacto; una familia con dos versiones existentes
conserva ambos UUID/números; sesión de V1 jamás devuelve V2; creador y rúbrica
corresponden; asociaciones ausentes/ambiguas rechazan; no hay escrituras/commit en
lectura ni cambios de PK; migración solo aditiva en laboratorio futuro y reversible
sin borrar origen. Si faltan atributos oficiales obligatorios con fuente demostrable,
se informa bloqueo y no se presenta un DTO parcial como compatible. Comparar lecturas
y ejecutar posteriormente regresión aislada contra la línea base, sin contar omitidas.

U1 no necesita aprobar una fórmula nueva ni RF-22, porque no abre ingreso ni
calificación. Su DDL de prueba solo vive en el laboratorio futuro; no debe
registrarse el candidato como adaptador operativo sin completar la transición.
Autorizar U1 significa autorizar estos tres archivos y pruebas aisladas, **no**
ORM/migración productivos, corte de datos o integración de intentos. Si no se
aprueban D1–D3, ni siquiera el modelo privado enriquecido debe darse por objetivo.

## 7. Destino de las diez tablas ORM no literales

Las 22 actuales incluyen 12 nombres oficiales y 10 no literales; no son 22 de las
28 ya completas. BD2-01 añadió las tres oficiales de organización/consentimiento.

| Tabla actual | Destino o bloqueo en esta arquitectura | Condición para dejar de depender de ella; ninguna eliminación autorizada |
|---|---|---|
| `version_caso` | Ediciones de `caso`, D1–D3 | Probar identidad, todas las versiones/rúbricas y referencias S/8A; no colapsar familias |
| `escenario` | `escena` con UUID conservado | Completar título/tipo sin inventarlos y verificar hijos/orden |
| `pregunta` | `decision` | Aprobar D4 y cambio de obligatoriedad de criterio, preservar opciones |
| `nivel_rubrica` | `nivel_criterio` enriquecido | Conservar descriptor/puntaje sin equiparar automáticamente logro |
| `valoracion_opcion` | Colección D4 en opciones | Paridad exacta, triggers/concurrencia, publicación y recálculo demostrados |
| `sesion_programada` | `asignacion_caso` enriquecida | Resolver grupo/espacio/usuario, versión exacta, estados y condiciones históricas |
| `convocatoria` | `participacion` enriquecida D6 | Acreditar matrícula y preservación de UUID JWT, códigos individuales y retiro; no crear membresías ficticias |
| `espacio_academico` | **Sin equivalencia aprobada** con grupo/período | Decidir y demostrar cardinalidad: un espacio puede agrupar varios grupos; copiar UUID a grupo como UNIQUE impondría 1:1 no demostrado. Se conserva |
| `identidad_academica` | **Soporte de seguridad sin destino aprobado** | Hoy admite múltiples UUID por usuario/sistema y exige propiedad única por (sistema,UUID). Una columna UUID en usuario impondría otra cardinalidad. No se sustituye por JSON ni se desactiva el resolver en U1 |
| `evento_auditoria` | **Sin sustitución equivalente aprobada** | `notificacion` no equivale a auditoría. Preservar eventos, orden, actor/origen y transacción/Observer; no moverlos a un array de sesión sin diseño y aprobación específicos |

Conservar estas últimas tres como tablas permanentes adicionales no cumpliría
un destino físico estricto de 28. Su retirada requiere otra conciliación explícita
de funciones y datos, o aprobación de soporte técnico fuera del conteo; no está
resuelta por D1–D4. Esta es una limitación real, no una autorización implícita de
31/40 tablas. Las revisiones Alembic existentes y datos anteriores se conservan.

## 8. Aprobación concreta que permite decidir ahora

Se solicita decidir **sí/no**, por separado, sobre:

1. Mantener 28 entidades académicas **permitiendo** enriquecer atributos y que
   `caso` represente una edición (D1–D3), con procedencia UUID y congelación.
2. Aceptar la relación multicriterio desnormalizada y verificable D4, incluida
   nulabilidad de criterio directo, o rechazarla reconociendo que ER literal más
   normalización estricta no conserva Cases actual con solo las 28 entidades.
3. Aprobar contexto histórico D8 y retención de motor/políticas; sus contenidos no
   aprueban fórmula, escala, consolidación o ausencia aún no definidas.
4. Autorizar U1 con alcance explícito y coexistencia **solo temporal**; aplazar
   el corte de Scheduling hasta D5–D7 y los destinos de identidad/espacio/auditoría.
5. Fijar el significado final de «28»: académicas frente a todas las tablas físicas,
   incluida la excepción Alembic. Si se exige exactamente 28 físicas sin cambios
   al ER ni excepciones, **no existe una ruta compatible demostrada** y no debe
   autorizarse una migración que prometa conservar las funcionalidades actuales.

Solo se creó este documento. No se ejecutaron Docker, PostgreSQL, pytest ni
migraciones; no cambiaron ER, ORM, código, 8A, patrones o rama. No se inició BD2-03.
