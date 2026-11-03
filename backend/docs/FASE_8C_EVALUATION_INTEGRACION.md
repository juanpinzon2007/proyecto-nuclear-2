# Fase 8C — Políticas aprobadas e integración real

2026-11-02 · Rama `feature/integracion-backend`.

**Implementado:** escala inclusiva 0–100, peso igual por criterio, entradas con
cero para preguntas pendientes al vencer y una valoración general editable por
participación, con destinatario individual verificado. Se reutilizan Strategy,
CalculadorRubrica, los repositorios de resultados y el servicio de feedback de Identity.

**Evaluation todavía no puede producir notas académicas completas por defecto**:
falta precisar el mapeo de puntajes/niveles, la agregación de varias preguntas y el
redondeo cuando sea necesario. Los ejemplos numéricos persistidos continúan siendo
LABORATORIO, sin publicación oficial. No se inicia fase 9.

## 1. Decisiones incorporadas y trazabilidad

Fuente de aprobación: las tres respuestas de Diana Ma Valencia trasladadas por el
usuario en esta conversación. Son posteriores a los RF y complementan sus reglas.
El usuario confirmó además la ampliación física para admitir 100.00 y eligió
**una valoración editable**, en lugar de múltiples versiones de feedback.

| Definición / RF | Implementación efectiva | Límite |
|---|---|---|
| Selección única, RF-13/14 | Se conservan el agregado y UNIQUE(intento,decisión); modificar reemplaza la selección actual. Se prueba guardar la tercera de tres alternativas, rechazar otra selección duplicada y modificar conservando un solo paso. | No se reduce el número de alternativas disponibles. |
| Nota 0–100, RF-13/17 | `PoliticaAcademicaConfirmada` y `MapeoEscala100`; el calculador exige máximo 100 para la política nueva. Persistencia admite 100.00 mediante adaptación autorizada. | La escala no define por sí sola cómo interpretar los puntajes existentes como logros. |
| Criterios de igual peso, RF-13/17 | Fórmula `PROMEDIO_IGUALITARIO_100`, peso efectivo exacto 1/N por criterio. | Los pesos almacenados de rúbricas históricas se conservan; la política nueva registra una ponderación efectiva igualitaria. |
| Tiempo vencido, RF-24/RN-14 | Mantiene PARCIAL. Cada pendiente llega a la resolución de niveles con valor cero y `id_opcion=None`; no se crea una selección. | La conversión/agregación de esas preguntas a niveles debe estar definida; no se inventa un nivel cero. |
| Ausencia, RF-16/24/RN-15 | Se mantiene ausencia confirmada sin Intento y ceros por pregunta; se prepara para la misma fórmula general. | No se interpreta «la nota sigue siendo la misma» como permiso para copiar una nota anterior. Confirmar alcance/roster y resolver mapeo/almacenamiento sin intento antes de una nota oficial. |
| Resultado y explicaciones, RF-14 | Se conserva cierre, titularidad, rúbrica histórica y preparación de feedback por selección. | Previsualización y resultado LABORATORIO no se publican como nota oficial. |
| Feedback general, RF-26 | Tabla oficial integrada, FK individual a participación y UNIQUE(participación), texto editable por el docente autorizado. Dos alumnos de una asignación reciben valoraciones distintas. | No es historial de múltiples comentarios; no se reasignan autor/destinatario. |
| Avisos, RF-27 | Se mantiene la separación entre persistencia y publicación. | No se habilitan notificaciones ni endpoints; su entrega después de commit sigue pendiente. |

## 2. Fórmula confirmada y reglas todavía sin inventar

Si el mapeo aprobado entrega el logro de cada criterio en 0–100:

`nota = (logro_1 + ... + logro_N) / N`.

La misma clase `CalculadorRubrica` incorpora esa fórmula. Usa fracciones exactas
para el peso 1/N; no aproxima tres criterios a 33.33, 33.33 y 33.34. La rama
porcentual histórica permanece para reproducir resultados anteriores, sin aplicar
la escala nueva retroactivamente.

No se selecciona un modo de redondeo ni un número de decimales académico por defecto.
La fórmula nueva utiliza cálculo exacto; si un aporte no tiene representación
Decimal finita, se devuelve política pendiente. Por ejemplo, tres aportes de
100/3 no pueden materializarse en el detalle actual sin decidir su precisión,
aunque la suma matemática sea 100. La prueba con logros 30,60,90 y tres criterios
sí calcula exactamente 10+20+30=60. El repositorio sigue rechazando truncamiento o
redondeo implícito de importes que no quepan exactamente en sus columnas.
La conversión de fracciones finitas construye el Decimal exacto, sin depender
de una división con precisión insuficiente; se prueba también el logro 1/2**100.

`ResolucionNivelesAcademicos` recibe preguntas con selección real o valor cero
por pendiente. Debe devolver un nivel existente de cada criterio. **No tiene
implementación académica predeterminada**: no promedia automáticamente
`valoracion_opcion`, no usa `es_correcta` como nivel y no normaliza por el mayor
puntaje observado. `MapeoEscala100` aplica el máximo confirmado, pero necesita
un mapeo explícito de los niveles; no convierte un puntaje 5 en logro 100 por sí solo.

El servicio pasa el intento real dentro de la UoW a la extensión contextual de la
política. Los proveedores históricos siguen usando su interfaz anterior. En un
cierre voluntario incompleto no se extiende automáticamente la regla específica
de ceros por vencimiento; esa condición necesita precisión adicional.

## 3. Persistencia, procedencia e historia

Se reutilizan `resultado_intento` y `resultado_criterio`, sus FK compuestas,
UNICITY por intento/criterio, transacciones, locks e inmutabilidad de 8C.
El alcance de los resultados permanece **LABORATORIO**, con DTO `oficial=False`,
lectura oficial cerrada y sin repositorio productivo instalado en la API.

Se capturan los parámetros efectivos, las implementaciones y sus dependencias
trazables de mapeo/resolución. Para la política nueva, `preguntas_aplicadas` guarda
explícitamente los ceros sin opciones ficticias. El repositorio verifica que esa
proyección coincida con el intento antes de aceptar/reproducir el resultado.

Se conserva la huella conocida del motor anterior a esta aprobación:
`00571eb465608fa91d158aa399882d744846c2ff4cf8f34f1cfaf9d876a740cc`.
Solo se admite ese motor anterior con la fórmula porcentual histórica conservada.
No se ejecuta código recibido de la BD ni se acepta cualquier huella antigua.
Un snapshot JSON del motor v1 existe únicamente como dato de prueba, no como
segundo motor ejecutable. Las pruebas comprueban lectura de esa procedencia y
preservación de nota, documento y SHA-256 durante la migración. Una nota anterior
5.00 continúa siendo 5.00, no se transforma en 100 ni se recalifica.

Los identificadores de política no bastan por sí solos: siguen vinculados a su
definición, implementación, versión y parámetros canónicos. Una política cambiada
necesita nueva versión; los resultados anteriores no se actualizan.

## 4. Migración y feedback individual

Revisión nueva **`20261102_academic_policy`**, padre **`20261102_evaluation_results`**.
Se prueba exclusivamente en PostgreSQL desechable:

- `resultado_intento.nota_final`: NUMERIC(4,2) → NUMERIC(5,2).
- CHECK: rango inclusivo 0 ≤ nota_final ≤ 100, manteniendo modalidades permitidas.
- Integración de `retroalimentacion_docente`, reutilizando su clase ORM existente:
  PK INTEGER, FK a asignación conservada, FK nueva a participación NOT NULL UNIQUE,
  FK de autor usuario, texto y fecha. Se retira la unicidad por asignación.
- Un trigger comprueba correspondencia participación/asignación/profesor, rol y
  actividad del autor, y protege autor/destinatario frente a reasignaciones.
  Otro protege TRUNCATE. Las FK siguen intactas.

No hay UPDATE de resultados históricos, backfill ficticio ni cambio de claves.
El downgrade en vacío restaura la escala previa. Si existen notas 100 o feedback
individual, rechaza la reversión para no truncar notas ni eliminar comentarios.
El DBML original permanece sin cambios: son adaptaciones físicas respaldadas por
las nuevas decisiones. El metadata tiene **30 tablas físicas**, no un nuevo modelo
conceptual de 30 entidades; el catálogo académico oficial sigue siendo el de 28.

El adaptador de feedback utiliza `ServicioFeedbackDocente`, `FeedbackDocente` y
`UnidadTrabajoIdentitySQLAlchemy` existentes. Verifica en la transacción cuenta
activa/rol desde el repositorio, pertenencia de grupo/participación y titularidad
de Cases/Scheduling mediante los UUID realmente asociados en Identity. Si falta
la asociación o el ámbito no coincide, falla cerrado; no genera UUID ni vínculos.

El upsert se aplica únicamente al comentario editable: mantiene la PK y actualiza
texto/fecha de la valoración vigente, sin historial de textos. El autor y el
estudiante destinatario no cambian. Los resultados de nota siguen sin upsert.
La consulta estudiantil verifica cuenta y convocatoria propias, bloquea lectura
con intentos activos y entrega solo su valoración individual. No elige ni consolida
una nota entre intentos. Los controles SQL de integridad complementan, sin
sustituir, la autorización de aplicación.
También se prueba registrar feedback para un convocado sin intento, sin crear
uno artificial ni una nota. La consulta estudiantil sin intento conserva su
bloqueo hasta resolver la confirmación/entrega de ausencia; registrar el comentario
individual no certifica ausencia ni activa notificaciones.

## 5. Archivos de esta entrega

Nuevos:

- `backend/app/modules/participation/application/academic_policy.py`.
- `backend/app/modules/participation/infrastructure/individual_feedback.py`.
- `backend/alembic/versions/20261102_academic_policy.py`.
- `backend/tests/integration/test_academic_policy.py`.
- `backend/tests/fixtures/evaluation_motor_v1.json` (snapshot de prueba no ejecutable).

Actualizados: calculador existente; coordinación y puertos de Evaluation;
composición/captura/procedencia/repositorio técnico; modelo de resultados;
modelo académico de Identity reutilizado y registro de metadata. Las regresiones
de Identity, esquema ER28, Cases y Participation actualizan inventario/cabeza/FK
según las adaptaciones autorizadas, sin desactivar controles ni sustituir SQL
real por fakes. El soporte SQLite crea el DDL ORM actual sobre sus migraciones
históricas hasta 8B; no ejecuta ni estampa las revisiones nuevas PostgreSQL.

## 6. Pruebas y verificación final

| Ejecución | Resultado |
|---|---|
| Regresión focalizada previa de motor y persistencia | 166 aprobadas, 0 omitidas/fallos/errores; 44,23 s |
| Política nueva y regresiones del calculador, incluida precisión alta | 65 aprobadas, 0 omitidas/fallos/errores; 25,89 s |
| Grupo final de reglas/feedback/migración de esta entrega | **24 aprobadas, 0 omitidas, 0 fallos, 0 errores; 24,83 s** |
| Suite completa definitiva | **1546 aprobadas, 38 omitidas, 0 fallos, 0 errores, 1 advertencia conocida; 285,98 s** |

Son 24 pruebas nuevas respecto de la línea base de 1522: nueve sin BD y quince
en PostgreSQL desechable. Los grupos se superponen; no se suman como pruebas
distintas. La suite mantiene las regresiones SQLite aisladas. Las 38 omisiones
son las conexiones externas/configurables no habilitadas previamente; no se
cuentan como aprobadas. La advertencia es `StarletteDeprecationWarning` sobre
TestClient/httpx; no se instalaron dependencias ni se suprimió la advertencia.

Una pasada intermedia adicional obtuvo 1544 aprobadas y 38 omitidas, antes de
añadir los casos de precisión alta y feedback sin intento. Fue sustituida por
la ejecución definitiva de 1546; no se atribuye al código anterior la prueba final.

Cobertura nueva: selección única con tres alternativas reales; extremos 0 y 100;
pesos iguales preservando rúbricas históricas; fracciones exactas y rechazo de
redondeo no aprobado; parcial vencido con entradas cero y cero selecciones SQL;
ausencia sin intento ficticio; almacenamiento/recuperación de 100.00 en laboratorio;
lector histórico v1; preservación al migrar; feedback individual editable,
separación de dos alumnos de una asignación, actor ajeno/rol falsificado,
concurrencia y rollback; protección de destinatario por SQL y downgrade seguro.
Los mapeos numéricos positivos de ejemplo están marcados SOLO LABORATORIO: no se
presentan como aprobación de agregación o traducción de niveles.

Incidencias corregidas: una importación de la nueva prueba apuntaba al paquete
equivocado; el escenario de downgrade de nota 100 necesitó una base propia para
no encontrarse antes con el guard de feedback de otros tests. La primera pasada
completa registró **1543 aprobadas, 1 fallida, 38 omitidas, 1 advertencia; 287,80 s**.
La prueba fallida aún exigía unicidad por asignación: ahora conserva la comprobación
del DBML original y verifica por separado la adaptación física individual aprobada,
incluyendo UNIQUE por participación y la FK. No se ocultó ni se omitió el caso.

Estado final: rama `feature/integracion-backend`, **30 tablas ORM físicas**, **13
revisiones**, cabeza única **`20261102_academic_policy`**. El inventario de
contenedores con etiqueta `sps.identity.mapping.lab=true` terminó vacío.

Se retiraron las URLs externas del proceso hijo y se habilitó únicamente el
creador de laboratorios Docker existente. Cada contenedor PostgreSQL 17 usa
nombre/ID propios, tmpfs, puerto TCP efímero y comprobación de identidad de base
vacía; el finally elimina solo sus recursos. Las revisiones nuevas se probaron
exclusivamente allí. No se usó una base persistente ni se modificó `.env`.

La comparación SHA-256 con el inventario inicial confirma los archivos descritos
en la sección 5 y las adaptaciones explícitas de regresión; no se eliminó ningún
archivo anterior ni se sobrescribió evidencia previa. Las tres pasadas generales
generaron evidencias adicionales propias de BD2-04:

- `backend/docs/bd/laboratorio_bd2_04/evidencia_6eb5e30899ab48d8a7e9af5c8a6abfd3.json`.
- `backend/docs/bd/laboratorio_bd2_04/evidencia_ce3f873d268948dc87923bb326fe3d3b.json`.
- `backend/docs/bd/laboratorio_bd2_04/evidencia_60e8acc0a5294904a9622a0f43b2c989.json`.

El diff contra HEAD incluye avances previos sin commit; no se atribuye íntegro
a esta solicitud. `git diff --check` terminó con código 0, sin errores de espacios,
conservando solo el aviso previo LF/CRLF de un repositorio de Cases.

Configuración reproducible empleada (solo altera el entorno del proceso hijo):

```powershell
.\.venv\Scripts\python.exe -B -c "import os,subprocess,sys;e=os.environ.copy();[e.pop(n,None) for n in ('TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL')];e.update(SPS_TEST_POSTGRESQL='0',SPS_TEST_IDENTITY_MAPPING_DOCKER='1',PYTHONDONTWRITEBYTECODE='1');sys.exit(subprocess.run([sys.executable,'-B','-m','pytest','-c','backend/pyproject.toml','backend/tests','backend/app/modules/participation/tests','-q','-rs','--tb=short'],env=e).returncode)"
```

## 7. Qué falta para una Evaluation académica completa

1. Definir si el puntaje de cada nivel ya representa logro 0–100 o su conversión.
2. Definir cómo varias preguntas/valoraciones, incluidos ceros por pendientes,
   determinan un nivel por criterio. No basta la igualdad entre criterios.
3. Aprobar precisión/redondeo cuando el resultado o sus detalles no sean exactos
   y representables en las columnas actuales.
4. Confirmar la interpretación operacional de ausencia, su roster/cierre y el
   almacenamiento sin intento; no copiar notas previas ni crear un Intento.
5. Mantener pendiente la consolidación de varios intentos y `resultado_participacion`.
6. Resolver los contratos 8B de recorrido y autorización de respuesta/modificación.

La cardinalidad del feedback general y la adaptación para almacenar 100 ya están
resueltas e implementadas; no se vuelven a pedir. La notificación RF-27 y la
publicación oficial siguen sin habilitarse. RF-22 permanece cerrado. No hay
cambio de rama, commit, push, merge ni inicio de fase 9.
