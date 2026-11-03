# BD2-03 — Autorización específica pendiente para U1

2026-11-02 · Rama `feature/integracion-backend` · **NO IMPLEMENTADO / SQL NO EJECUTADO.**

## 1. Unidad seleccionada y punto de detención

U1 de [BD2-02D](BD2_02D_DECISION_COMPATIBILIDAD_ER28.md), sección 6:
lectura de una referencia de edición ER28 con identidad UUID conservada,
sin sustituir el escritor actual, abrir endpoints o activar intentos.

No puede implementarse de manera útil sobre el ER literal sin decidir su esquema:
el DTO existente exige UUID de caso/versión/rúbrica, número de versión y versión
de regla; ninguna de esas cinco referencias completas puede reconstruirse solo
con las claves INTEGER y textos originales. Un adaptador con valores constantes,
conversiones o campos vacíos incumpliría el contrato.

La preparación productiva sin cambio de esquema **ya existe**:
`ConsultaVersionPublicada` y el parámetro `consulta_version` de
`ConsultaIngresoSQLAlchemy`. No se duplicaron. `ConsultaIngresoParticipacion`
permite sustituir la consulta completa, pero tampoco proporciona correspondencias
de datos. No se encontró otro incremento mínimo de esta unidad que justifique
crear código operativo sin aprobar previamente esas referencias.

Por ello esta entrega solo crea este documento. Se detiene antes de ORM,
metadata de ensayo enriquecido, adaptador nuevo o migración. La autorización
general del usuario no se interpreta como aprobación de D1–D10.

## 2. Evidencia actual verificada sin conectar PostgreSQL

| Evidencia | Observación |
|---|---|
| [Cases: published_version.py](../../app/modules/cases/application/published_version.py) | Consulta exacta por UUID de versión PUBLICADO; join con su rúbrica; retorno íntegro; protocolo callable existente |
| [Cases ORM](../../app/modules/cases/infrastructure/models/caso.py) | `caso.id` UUID es familia; `version_caso.id` UUID y `(caso_id,numero)` identifican ediciones |
| [Rúbrica actual](../../app/modules/cases/infrastructure/models/rubrica.py) | UUID propio, FK a versión, `version_regla`; valoraciones por opción/criterio se conservan |
| [Scheduling](../../app/modules/scheduling/application/programar_sesion.py) | Recibe versión exacta, verifica PUBLICADO y compara duración con tiempo estimado; no puede recibir un caso genérico como sustituto |
| [8A](../../app/modules/participation/infrastructure/integration.py) | Inyección posterior a Identity, titularidad, convocatoria y Scheduling; sin escrituras |
| [Dependencia de fachada](../../app/modules/participation/api/dependencies.py) | Continúa respondiendo 503 `INTEGRACION_NO_CONFIGURADA` |
| Fuente y objetivo oficial | Ambos declaran las 28 entidades; no se modificaron |
| [BD2-02B](laboratorio_er28/INFORME_BD2_02B.md) / [BD2-02C](laboratorio_compatibilidad_cases/INFORME_BD2_02C.md) | Evidencias guardadas: 198 y 37 comprobaciones, estado passed y limpieza verificada. Solo se leyeron; no se repitieron |
| Registro de metadata en memoria | 22 tablas, FK registradas resueltas; sin crear engine/conexión ni DDL |
| Grafo Alembic leído con ScriptDirectory | 7 revisiones, una cabeza: `20261101_er28_base_academica`; no se ejecutó env.py ni migración |

El esquema físico del equipo no se inspeccionó. Las **1142 aprobadas, 38 omitidas
y 1 advertencia** siguen siendo línea base histórica; no son pruebas de BD2-03.

## 3. Autorización mínima propuesta: solo referencia de edición en laboratorio

Se reduce U1 al subconjunto de D1–D3 que necesita la consulta de referencia:
**cuatro atributos en `caso` y dos en `rubrica`**. No se solicitan todavía todos
los UUID de hijos, los textos/tiempo estimado nuevos, la colección multicriterio,
ni cambios a Scheduling, Participation, resultados o consentimiento.

### Definiciones originales aprobadas relevantes

```dbml
Table caso {
  id_caso int [pk, increment]
  id_profesor int [not null, ref: > usuario.id_usuario]
  titulo varchar(160) [not null]
  introduccion_teorica text [not null]
  estado varchar(20) [not null, default: 'borrador']
  fecha_creacion timestamp [not null]
  fecha_validacion timestamp
}
Table rubrica {
  id_rubrica int [pk, increment]
  id_caso int [not null, unique, ref: > caso.id_caso]
  nombre varchar(120) [not null]
  nota_maxima decimal(4,2) [not null]
}
```

### Cambios sometidos a aceptación o rechazo

| Solicitud | Propuesta exacta y restricciones | Justificación / RF | Impacto académico y técnico |
|---|---|---|---|
| A1 | `caso`: añadir `uuid_caso UUID`, `uuid_version UUID`, `numero_version INTEGER`, `contenido_congelado BOOLEAN`; UNIQUE(uuid_version), UNIQUE(uuid_caso,numero_version), número positivo y conjunto completo o completamente NULL | Conservar familia y edición por separado; RF-05/09/12/14 y compatibilidad de versiones del backend | **Cambio semántico académico**: fila de caso pasa a identificar una edición, no toda la familia. UUID de familia se repite entre versiones; UUID de versión es único. Mantener PK INTEGER y todas las FK originales |
| A2 | `rubrica`: añadir `uuid_publico UUID UNIQUE`, `version_regla VARCHAR(20)`; ambos presentes y regla no vacía, o ambos NULL | Devolver identidad y regla de la rúbrica propia de la edición; RF-13/17 y preservación del contrato | Nuevos atributos de compatibilidad. Mantener UNIQUE(id_caso), FK a caso, máximo original y todos los datos previos |
| A3 | Marca de contenido congelado irreversible; validaciones de pertenencia de rúbrica y bloqueo del grafo al publicar | Una bandera sola no crea inmutabilidad; RF-09/12/14/17 | Integridad técnica con política de congelación de ediciones publicada **a aprobar expresamente**. No confundir archivo con borrado ni usar la marca como permiso de ingreso |
| A4 | Autorizar únicamente metadata privado, adaptador candidato no registrado y pruebas en laboratorio nuevo; ningún cambio a esquema existente | Colisiones actuales `caso`/`rubrica` con PK UUID impiden un ALTER directo del destino INTEGER | No cambia contratos públicos ni tablas productivas. Las mismas 28 entidades del ensayo no se convierten en nuevas tablas permanentes |

La nulabilidad es de transición explícita: filas sin correspondencia no están
habilitadas para el adaptador; no son referencias completas. Una fila de referencia
habilitada debe cumplir A1/A2 íntegros, estado PUBLICADO acreditado y congelación
comprobada. Los NULL no se sustituyen por UUID nuevos, número 1 o regla ficticia.
La aprobación de A1 es necesaria incluso si se prueba solo en metadata privado:
el documento anterior no autorizó tratar ese diseño como destino aceptado.

### SQL ilustrativo — NO EJECUTADO, NO ES UNA MIGRACIÓN PRODUCTIVA

Este fragmento se refiere **solo a tablas ER28 originales en una base futura de
laboratorio vacía**. No corresponde al `caso`/`rubrica` ORM actual con claves UUID.
No crea base, tablas, datos, triggers ni correspondencias. No debe aplicarse al
esquema del equipo. Es el delta de atributos sometido a revisión:

```sql
ALTER TABLE caso
  ADD COLUMN uuid_caso UUID,
  ADD COLUMN uuid_version UUID,
  ADD COLUMN numero_version INTEGER,
  ADD COLUMN contenido_congelado BOOLEAN,
  ADD CONSTRAINT uq_er28_caso_uuid_version UNIQUE (uuid_version),
  ADD CONSTRAINT uq_er28_caso_familia_numero UNIQUE (uuid_caso, numero_version),
  ADD CONSTRAINT ck_er28_caso_referencia_completa CHECK (
    (uuid_caso IS NULL AND uuid_version IS NULL AND numero_version IS NULL
      AND contenido_congelado IS NULL)
    OR
    (uuid_caso IS NOT NULL AND uuid_version IS NOT NULL AND numero_version IS NOT NULL
      AND numero_version > 0 AND contenido_congelado IS NOT NULL)
  );

ALTER TABLE rubrica
  ADD COLUMN uuid_publico UUID,
  ADD COLUMN version_regla VARCHAR(20),
  ADD CONSTRAINT uq_er28_rubrica_uuid_publico UNIQUE (uuid_publico),
  ADD CONSTRAINT ck_er28_rubrica_referencia_completa CHECK (
    (uuid_publico IS NULL AND version_regla IS NULL)
    OR
    (uuid_publico IS NOT NULL AND version_regla IS NOT NULL
      AND length(btrim(version_regla)) > 0)
  );
```

Este SQL **no garantiza por sí mismo** A3: se necesitarían guardas transaccionales
en el padre y en cada tabla del grafo afectada, para serializar publicación y
ediciones de hijos, impedir reparentado/borrado y evitar que se quite la marca.
Su futura implementación debe bloquear la misma fila-edición y conservar la marca
al archivar; un cambio de estado a BORRADOR no puede descongelar contenido. No se
presenta un trigger vacío como solución. El alcance de U1 es solo lectura de
referencia y pruebas; no certifica que el grafo completo pueda importarse/publicarse.

## 4. Preservación demostrable, no sustitución automática

La siguiente correspondencia es simbólica; no son usuarios ni UUID históricos inventados:

| Origen acreditado | Destino de ensayo propuesto | Retorno del contrato |
|---|---|---|
| Familia F, versión V1 número 1 y rúbrica R1 | caso I1: uuid_caso=F, uuid_version=V1; rúbrica con uuid_publico=R1 | F, V1, 1, R1 y regla propia |
| Misma familia F, versión V2 número 2 y rúbrica R2 | caso I2 distinto: uuid_caso=F, uuid_version=V2; rúbrica con uuid_publico=R2 | F, V2, 2, R2 y regla propia |
| Sesión actual asignada a V1 | No se modifica la sesión ni su FK; la consulta de ensayo recibe V1 | Debe resolver exclusivamente I1/R1 aunque exista I2/R2 |

La familia F debe conservar el propietario acreditado entre sus ediciones; no
se agrupan casos de docentes distintos por nombre o parecido de contenido. La
creación concurrente de ediciones exige serialización por familia y validación
del propietario en almacenamiento, además de UNIQUE(familia,número). El diseño
de esa guarda debe incluir el caso de primera inserción concurrente: bloquear
una fila aún inexistente no basta. Se debe probar antes de admitir escritura.

Los UUID se copian de cada entidad fuente acreditada; INTEGER de destino se
asigna independientemente por la base. No se deriva uno del otro, no se busca
«última versión» ni se empareja por título/orden. No se reemplaza `version_caso`,
se eliminan versiones ni se redirigen sesiones/convocatorias en esta unidad.

Para datos nuevos sintéticos del laboratorio se crean entidades nuevas con UUID
persistidos una sola vez. Para datos existentes, la falta de equivalencia de
docente UUID→usuario INTEGER, máximo de rúbrica, introducción teórica u otro campo
obligatorio detiene el traslado de esa fila: no se rellena con valores de ensayo.
Los códigos/convocatorias, valoraciones y resultados existentes permanecen en su
origen íntegro; U1 no representa una migración de su contenido.

La referencia de regla no aprueba una fórmula. Tampoco seis columnas vuelven
reproducible una evaluación histórica: siguen siendo necesarios marco congelado,
matriz completa, políticas/parámetros y motor recuperable, según BD2-02D.

## 5. Impactos, riesgos y reversión

- **Cases:** el adaptador candidato puede implementar el callable actual sin
  modificar DTO/Builder/Chain. No puede afirmar equivalencia de CasoDetalle ni
  reconstruir valoraciones aún no representadas. La obligatoriedad de criterio
  de decisión y la propuesta JSONB multicriterio **no se aprueban con A1–A4**.
- **Scheduling:** no cambiar `version_caso_id`, estado, duración, asignación ni
  convocatoria. No registrar el nuevo adaptador como predeterminado. Un futuro
  corte requiere aprobar destino físico y correspondencia sesión/asignación,
  que este incremento no proporciona.
- **8A/Participation:** conservar la inyección y todas las autorizaciones, el
  bloqueo RF-22 y la fachada 503. Referencia UUID completa o rechazo; no acceso
  por ID de URL ni permiso implícito para iniciar intentos.
- **Integridad:** UNIQUE no prueba procedencia ni pertenencia a una familia real;
  se exige manifiesto/verificación de origen y guardas de congelación. La marca
  no reemplaza revisión del contenido ni conserva por sí sola evidencias perdidas.
- **Reversión de U1:** destruir únicamente su laboratorio propio; candidato sin
  registrar y metadata privado no cambian operación actual. No proponer DROP de
  columnas de una base persistente como reversión: si alguna vez guardan datos,
  retirarlas sería destructivo y exigiría un plan/autorización diferentes.
- **Estado final de 28 físicas:** el destino de identidad académica, espacio y
  auditoría sigue abierto. No se autoriza añadir soporte permanente ni retirarlo.

## 6. Próxima implementación si se aprueba A1–A4

Solo estos tres archivos, siguiendo U1 de BD2-02D:

1. `backend/tests/integration/er28_compatibility_support.py`: metadata privado
   ER28 enriquecido y laboratorio desechable explícito; ninguna importación a Base.
2. `backend/app/modules/cases/infrastructure/er28_published_version.py`: lector
   candidato de Session/tablas inyectadas, sin motor ni conexión propia, no registrado.
3. `backend/tests/integration/test_er28_published_version.py`: pruebas de contrato
   y conservación de referencia; sin activar API, escritor o intento real.

Criterios de aceptación propuestos:

- Exactamente las 28 entidades del ensayo, sin tabla auxiliar ni Alembic productivo.
- Dos versiones de una familia conservan sus UUID/números/rúbricas sin fusión.
- UUID versión/rúbrica duplicados, número repetido o referencia parcialmente poblada
  se rechazan; ausencia/ambigüedad no produce fallback ni nuevo UUID.
- Consulta de V1 devuelve V1/R1/regla propia, nunca V2, dentro de la Session ajena,
  sin flush, commit ni cierre; no revela contenido/corrección en esta proyección.
- Rechazo de edición no publicada, sin congelación o sin rúbrica/referencia completa.
- Pruebas de SQL directo y concurrencia de las guardas A3 antes de afirmar
  inmutabilidad; si A3 no se implementa completamente, declarar U1 prueba de
  lectura solamente y no habilitar publicaciones/importación de grafo.
- Paridad con consulta existente sobre fixtures acreditados, y regresión de
  Identity/Scheduling/8A en SQLite aislado y PostgreSQL nuevo desechable. Las
  pruebas de RF-22/fachada deben seguir cerradas. Omitidas separadas de aprobadas.
- Ninguna migración del equipo ni cambio de PK, contratos HTTP o siete patrones.

## 7. Cierre y decisión solicitada

**No se implementó código ni se ejecutó pytest**, porque U1 necesita aprobación
previa del diseño académico. No se ejecutó Docker/PostgreSQL. Se verificaron
metadata y grafo Alembic en memoria, sin engine ni acceso físico. La cabeza sigue
en `20261101_er28_base_academica`; metadata declara 22 tablas, no el destino ER28.

La autorización concreta propuesta es: **aprobar o rechazar A1–A4 exclusivamente
para U1 de lectura aislada**, incluyendo el cambio semántico caso→edición y los
seis atributos expuestos. No implica aprobar D4/JSONB, toda D3, migración
productiva, backfill histórico, sustitución de version_caso, cambios a asignaciones
o ejecución de BD2-04. Si se rechaza, el backend actual permanece intacto y no se
construye un adaptador que simule compatibilidad.
