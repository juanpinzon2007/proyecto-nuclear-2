# U1 experimental — resultado: corregir antes de aprobación definitiva

2026-11-02 · `feature/integracion-backend` · Autorización exclusivamente experimental.

**Las seis columnas permiten representar dos ediciones y conservar UUID junto a
INTEGER, pero no garantizan historia inmutable ni asociaciones correctas.** Se
encontraron 12 garantías vulneradas mediante SQL real. No se agregaron columnas,
tablas, triggers o políticas para hacer desaparecer esos fallos.

## 1. Modificaciones exactas experimentadas

Se creó desde cero el ER28 literal, con 28 tablas/144 columnas/28 PK/40 FK/19 UQ.
Luego se aplicó el [delta propuesto](seis_columnas.sql):

| Tabla | Columnas nuevas | Restricciones nuevas |
|---|---|---|
| caso | uuid_caso UUID; uuid_version UUID; numero_version INTEGER; contenido_congelado BOOLEAN | UNIQUE(uuid_version); UNIQUE(uuid_caso,numero_version); CHECK conjunto completo con número positivo o todo NULL |
| rubrica | uuid_publico UUID; version_regla VARCHAR(20) | UNIQUE(uuid_publico); CHECK ambos completos con regla no vacía o ambos NULL |

Catálogo observado: **28 tablas, 150 columnas, 28 PK, 40 FK, 22 UQ, 2 CHECK,
50 índices de soporte y 0 triggers de usuario**. Se compararon PK/FK originales,
tabla por tabla: sin cambios. Solo existen las seis columnas adicionales.

La congelación A3 no es parte del delta ejecutable de seis columnas: una columna
boolean no equivale a una guarda. La autorización experimental no se utilizó para
añadir por iniciativa propia una implementación de triggers ni más atributos.
El SQL no se integró en Alembic; no se crearon ORM/adaptadores productivos.

## 2. Datos y método

Se reutilizó el fixture de contenido de BD2-02C para V1: caso 10, rúbrica 20,
tres escenas, tres decisiones y seis opciones. Se añadieron únicamente filas
en entidades oficiales para consentimiento, participación, intento, paso y una
nota **sintética almacenada** 3.25 con dos detalles de criterio. No hay fórmula
académica, calificación oficial ni validación de ingreso en estos datos.

La fuente sintética declara una familia UUID F, versiones V1/V2 y rúbricas R1/R2.
Los UUID se generan una vez como identidades de entidades nuevas, se registran
en el manifiesto y se copian a los campos destino; no derivan de INTEGER.

Primero se lee asignación 401→caso 10/rúbrica 20 y el resultado guardado. Después
se crea caso 50 como edición número 2 de la misma familia, con rúbrica 60,
criterio/nivel/escena/decisión/opción propios y otra regla sintética. Se relee
V1 y se comparan los objetos completos y la nota almacenada. Por último se
intentan mutaciones ilegítimas, cada una dentro de su transacción revertida.

La consulta de referencia por UUID está exclusivamente en el script experimental:
exige PUBLICADO, marca de congelación y referencias completas, y devuelve los
cinco valores del contrato. **No prueba por sí misma que la marca sea verdadera**,
no autentica, y no está conectada a 8A. Un UUID desconocido devuelve ausencia sin
elegir la última versión.

## 3. Resultado ejecutado

Dos ejecuciones finales independientes del mismo código produjeron el mismo
diagnóstico: **16 garantías satisfechas, 12 vulneradas; 8 controles de infraestructura
y restauración satisfechos**. No son pruebas pytest ni 28 aprobaciones.

| Capacidad | Observación real | Conclusión |
|---|---|---|
| Identidad lógica reconocible | Casos INTEGER 10 y 50 conservan el mismo F y diferentes V1/V2 y números 1/2; retorno R1/R2 correcto | Representable; aún mutable sin guardas |
| Correspondencia UUID–INTEGER | SELECT del destino coincide exactamente con el manifiesto fuente de cada ejecución | Verificada solo para datos sintéticos; ninguna equivalencia histórica presumida |
| Añadir edición posterior | Insertar V2 no altera objeto completo de asignación/contenido/rúbrica V1 ni el resultado almacenado | Conservación ante inserción independiente demostrada |
| Versión exacta | Consulta V1 sigue retornando V1/R1/regla propia; UUID desconocido no devuelve otra edición | Lectura correcta bajo datos íntegros |
| Unicidad/completitud local | Duplicar UUID de versión/rúbrica o número familiar: 23505; número cero, referencia parcial o regla vacía: 23514 | Restricciones propuestas funcionan localmente |
| Huérfanos inexistentes | Asignación/rúbrica con caso inexistente y paso con par opción/decisión incorrecto: 23503 | FK originales conservadas y útiles |
| Inmutabilidad y pertenencia global | Se aceptaron las doce mutaciones siguientes, SQLSTATE 00000 | Garantías no satisfechas; no habilitar el diseño como definitivo |

### Doce contraejemplos reproducibles

| Garantía requerida | Mutación aceptada y testigo guardado |
|---|---|
| Cabecera histórica inmutable | Cambiar título de caso 10 con contenido_congelado=true |
| Hijos históricos inmutables | Cambiar enunciado de decisión 201 de V1 |
| Rúbrica histórica inmutable | Cambiar peso del criterio 21 de V1 |
| Marca irreversible | Poner contenido_congelado=false en V1 |
| Asignación anterior fija | Reapuntar asignación 401 al caso 50/V2; el resultado 901 conserva nota 3.25 pero su cadena ahora refiere V2/R2 |
| Familia histórica estable | Cambiar uuid_caso de V2 por otra identidad sintética |
| Propietario familiar consistente | Cambiar profesor de V2 a otro usuario existente; no coincide con el dueño de V1 |
| Criterio de la edición correcta | Decisión 201/V1 puede usar criterio 61/V2, aunque ambos existen |
| Destino de la edición correcta | Opción 301/V1 puede apuntar a escena 151/V2 |
| Resultado definitivo protegido | Cambiar directamente nota del resultado 901 a 1 |
| Resultado/criterio coherentes | Detalle 911/V1 acepta criterio 61 y nivel 62 de V2: el par sí es válido, pero pertenece a otra edición |
| Referencia publicada no desaparece | Borrar conjuntamente las cuatro referencias de caso 10 dejando su rúbrica con UUID/regla: el CHECK local lo acepta |

Estos casos diferencian **no tener huérfanos** de **tener asociaciones correctas**:
las FK pueden seguir satisfechas mientras la asignación o el criterio corresponden
a otra edición. También demuestran que una nota conservada numéricamente puede
perder el contexto que permitiría explicarla/reproducirla.

Todas las mutaciones adversas se revirtieron y se confirmó igualdad final con la
lectura/resultado inicial y catálogo sin más cambios. Los testigos se capturan
antes del rollback, para que su reversión no oculte el defecto.

## 4. Evidencias y limpieza

| Ejecución | Evidencia | Resultado y contenedor eliminado |
|---|---|---|
| Diagnóstico inicial | [6f6767cb](evidencia_6f6767cb011744ce9ce91af432420471.json) | 16/12; `ebb24f9043d8ae07ea66b7232be464ab092b8114327f929d71d1acabc65c5f98` |
| Final 1 | [64f2031b](evidencia_64f2031bcee147539ae31e03145fbb58.json) | 16/12; `eb790b0a5e905f6655c3dd93fe2bbf8988be51afd49f42b3e42ec835672f78e6` |
| Final 2 | [64c4f0d1](evidencia_64c4f0d1126d4b11965f031e493a374d.json) | 16/12; `28b37dc3b360117609ad4de7f125a498e968a60758a1f1d9ad59f4bbd765d1dd` |

La segunda versión del script solo amplió el testigo de reasignación para mostrar
la cadena del resultado y su nota; no corrigió esquema ni cambió expectativas.
Las dos ejecuciones finales tienen el mismo hash de código y SQL.

En las tres: PostgreSQL 17.11, contenedor nuevo con ID/nombre/etiqueta exclusivos,
red `none`, ningún puerto publicado, ningún bind/volumen persistente, datos en
tmpfs verificado en montaje real, conexión TCP interna y base vacía inicial.
El finally verificó propiedad antes de eliminar exclusivamente su ID: **rm=0,
inspect posterior=1, cleanup=removed_verified**. No se conectaron bases existentes,
no se usaron credenciales de `.env`, ni hubo Compose o limpieza global.

Hubo una comprobación preliminar de Docker que inicialmente devolvió imagen no
encontrada; la inspección posterior de la imagen local tuvo éxito. No se descargó
ni modificó la imagen. No se atribuye una causa definitiva a esa respuesta transitoria.

## 5. Comparación con version_caso actual

| Aspecto | Backend actual | Experimento de seis columnas |
|---|---|---|
| Identidad familiar | Fila caso UUID estable, versiones con FK a esa fila | UUID familiar repetido en filas-edición, sin entidad familiar referenciada |
| Edición y orden | version_caso UUID y UNIQUE(caso_id,numero) | caso INTEGER + uuid_version y UNIQUE(uuid_caso,numero_version) |
| Propietario | Se obtiene del caso familiar compartido por sus versiones | Duplicado por fila-edición; divergencia aceptada en el experimento |
| Asignación | sesion_programada.version_caso_id FK a edición | asignacion_caso.id_caso FK a fila-edición; apuntar a otra existente sigue permitido |
| Rúbrica | Una por versión, UUID y version_regla | Una por fila-edición, con UUID/regla añadidos |
| Protección de edición | VersionCaso.asegurar_editable y servicios restringen a BORRADOR | No se trasladaron servicios ni se añadieron guardas; bandera no bloquea SQL |
| Multicriterio | valoracion_opcion guarda puntajes por opción/criterio | Sigue sin destino en las seis columnas; no se ensayó ni se simplificó |
| Reproducción | Exige marco histórico y política/motor según puertos; no queda aprobada por existir el ORM | Solo comparación de nota sintética almacenada; no demuestra recálculo |

La comparación del backend actual es estática; **no se ejecutaron ataques SQL
contra sus tablas ni se afirma que su ORM tenga triggers de inmutabilidad**.
Ningún servicio, contrato, modelo, endpoint o tabla `version_caso` fue modificado.

Riesgos propios de una fila de caso por edición: contar ediciones como casos,
autorizar solo una fila cuando el permiso depende de la familia, perder continuidad
por cambios de uuid_caso, duplicar/divergir creador y contenido, mover hijos entre
ediciones y borrar la última evidencia de pertenencia. Esos problemas no se
resuelven solo con UNIQUE(familia,número) ni una bandera.

## 6. Recomendación para A1–A4

**Corregir antes de aprobar implementación definitiva.** El resultado no obliga
a añadir una séptima columna: parte de las brechas puede resolverse con guardas,
transacciones y servicios usando las seis existentes, pero eso requiere diseño,
autorización y nuevas pruebas; no se implementó aquí.

- **A1:** útil para representación/identidades, insuficiente para familia histórica
  estable, propiedad y congelación. Mantenerlo como candidato experimental hasta
  diseñar serialización por familia, inmutabilidad y revisión de la granularidad.
- **A2:** unicidad y completitud local verificadas; falta preservar la pertenencia
  de la rúbrica y hacer que su identidad/regla y criterios sean históricos.
- **A3:** no demostrado, y el delta de seis columnas **no lo implementa**. Exigir
  guardas en cabecera/hijos/rúbrica/asignación/resultados, edición/padre coherentes
  y pruebas de concurrencia antes de afirmar irreversibilidad. Una capa de servicio
  debe conservar autorización y congelación; una marca no la reemplaza.
- **A4:** aislamiento, no registro productivo y ausencia de cambios al backend
  cumplidos. Es válida como condición experimental, no aprobación académica.

Siguen pendientes el multicriterio, las políticas/fórmula y artefactos del motor,
la correspondencia de convocatorias/membresías, timestamps y el destino de soporte
actual fuera de las 28. No se abre 8A ni se declara compatible Cases completo.

Próxima decisión posible, sin ejecutarla: autorizar o rechazar un ensayo separado
de guardas de integridad/inmutabilidad sobre estas mismas seis columnas. Si se
requieren atributos adicionales para otra capacidad, se presentarán por separado.
No se amplía este experimento ni se inicia otra fase automáticamente.

## 7. Alcance final

Solo se crean archivos en `backend/docs/bd/laboratorio_u1_experimental/`.
No se ejecutó pytest ni la suite general: **1142 aprobadas/38 omitidas es histórico**.
No hubo migraciones reales, ORM, DBML, servicios, contratos, patrones, 8A,
commits/push/merge ni cambios de rama. Las instrucciones reproducibles están en
[README.md](README.md).

Cierre verificado: los 272 archivos preexistentes registrados conservan sus
hashes; hay ocho archivos nuevos, todos en la carpeta experimental. Los hashes
de los ocho artefactos de entrada coinciden con las dos evidencias finales.
Análisis sintáctico del ejecutor, enlaces locales y whitespace de archivos nuevos
correctos; `git diff --check` sin incidencias. No se alteró la rama.
