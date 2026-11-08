> Revisión posterior autorizada: la implementación interna está en
> CONSENTIMIENTO_VERSIONADO_IMPLEMENTACION.md. El selector se separó de
> asignacion_caso para conservar bd205_asignacion, sin ampliar su excepción.
> Son dos tablas técnicas (33 físicas), no la propuesta anterior de 32. Este
> documento conserva el razonamiento previo; el borrador institucional sigue NO aprobado.

---

# Checkpoints y persistencia de consentimiento: propuesta física pendiente

Fecha: 5 de noviembre de 2026, America/Bogota. Rama feature/backend-continuidad.
Este documento distingue controles existentes, propuesta técnica y aprobación
institucional. No declara aprobado el borrador ni introduce una versión oficial.

## 1. Checkpoints locales concluidos

Se cotejaron las 77 rutas, tamaños y SHA-256 de
CHECKPOINT_SALA_ESPERA_ADMISION_20261105.json; sin faltantes, repetidos ni diferencias.
Los Python coinciden con las huellas de la general histórica 2158/38. Se revisaron
patrones de claves privadas, JWT literales y URLs con credenciales: sin hallazgos.
Las credenciales sintéticas identificadas en pruebas no son credenciales reales.
Esto es una revisión acotada, no una certificación de seguridad exhaustiva.

Los cuatro conjuntos son disjuntos y su unión contiene exactamente las 77 rutas.
Se preparó cada ruta explícitamente, se revisó índice, blobs, diff y
`git diff --cached --check` antes de cada commit. Ningún archivo de código cambió
durante los checkpoints. Las fixtures compartidas de ingreso y consentimiento
están juntas para no separar contratos que se necesitan mutuamente.

| Commit | Responsabilidad | Archivos |
|---|---|---:|
| `a6f7e48` | fix(scheduling): ejecutar worker RF-19 con errores seguros | 4 |
| `906aec9` | feat(identity): integrar acceso del personal y consultas protegidas | 17 |
| `8a08e8b` | feat(backend): consolidar admision y consentimiento interno | 50 |
| `28be564` | docs(backend): consolidar contratos y trazabilidad funcional | 6 |

Selección exacta por commit, comandos de comprobación y registro:
`evidencias/checkpoints_consentimiento_20261106T031805Z/plan_commits.json`,
`commits_creados.json`, `C1_seleccion.txt` a `C4_seleccion.txt` y
`auditoria_inicial.json`. Desde esta carpeta docs, los archivos están bajo
`../../evidencias/checkpoints_consentimiento_20261106T031805Z/`.
El manifiesto de control de 77 rutas excluye su propia autorreferencia: se conserva
sin seguimiento y no se añadió como un archivo 78 no enumerado. Los otros
manifiestos históricos sí están en sus rutas autorizadas y mantienen sus bytes.
Evidencias, ZIP, Word, respaldos y archivos universitarios ajenos siguen excluidos
y preservados. No hubo push, merge, PR, cambio de rama, consumo del stash ni .env.
Git avisó de normalización LF/CRLF futura; las 77 huellas de trabajo no cambiaron.

## 2. Diagnóstico focalizado: por qué no se crea una migración todavía

- `identity/application/consent.py::DocumentoConsentimiento`: referencia <=30,
  documento_id, versión, texto UTF-8, vigente; hash del texto calculado. No almacena
  aprobación, original binario ni procedencia institucional. El puerto
  `FuenteConsentimiento.vigente(id_asignacion, ahora)` no determina si el ámbito
  institucional será global, por programa o por asignación, ni tiene recuperación
  histórica en SQL.
- `identity/infrastructure/academic_base_models.py::ConsentimientoORM` pertenece
  a un estudiante y exige su FK y fecha. Usarla para publicar documentos antes de
  que alguien acepte exigiría inventar un estudiante o mezclar dos entidades.
- `identity/infrastructure/consent.py::ServicioConsentimientoSQLAlchemy` verifica
  aceptación explícita/referencia/hash/titular; registra solo la referencia y fecha.
  Segundo registro de misma referencia falla cerrado: evita duplicación, pero NO
  acredita todavía idempotencia transparente ni evidencia explícita durable.
- `participation/infrastructure/provision.py::_obtener_o_crear` valida antes del
  INSERT P; `ParticipacionModel` no conserva la aceptación usada. Solo IntentoModel
  tiene la FK. No se puede reconstruir arbitrariamente el enlace histórico desde
  un intento, ni desde MAX(fecha_aceptacion).
- `BORRADOR_CONSENTIMIENTO_INFORMADO.md`: NO APROBADO, sin versión/vigencia oficial.
  Permanece intacto y fuera de cualquier proveedor productivo.

Conclusión: guardar documentos y aprobación en PostgreSQL necesita una estructura
separada de las aceptaciones. La recomendación anterior de artefactos externos era
otra propuesta; no proporciona FK SQL ni satisface por sí sola la nueva petición
de persistencia documental. El ER oficial sigue teniendo 28 entidades; el backend
físico tiene 31 tablas. La propuesta siguiente pasaría a 32. Esa adaptación y el
selector de ámbito NO tienen aprobación física expresa en los contratos previos.
La condición de esta solicitud permite presentar el diseño y detener esa parte;
no se interpreta como aprobación automática de una tabla y cardinalidad concretas.

## 3. Una arquitectura recomendada: versión publicada + selector explícito

Reutilizar FuenteConsentimiento, el servicio de aceptación, consentimiento, P/I
y la UoW actual. Agregar UNA tabla técnica de versiones publicadas y referencias
en tablas existentes. No agregar otra tabla de aceptaciones, registro de espera,
servicio de autenticación ni un segundo motor de consentimiento.

Se recomienda seleccionar la definición por asignación, coherente con el parámetro
actual del puerto. Es una cardinalidad PROPUESTA para aprobación, no un requisito
institucional demostrado. Una versión podrá ser seleccionada por muchas asignaciones;
una asignación tendrá cero o una definición aplicable. NULL significa cerrado,
nunca una versión predeterminada. No inferir vigencia de la versión mayor o de
la aceptación más reciente. No se activarán definiciones automáticamente.

### 3.1 Nueva tabla propuesta: documento_consentimiento_version

Contendrá solo publicaciones verificadas, no borradores ni filas sintéticas.
No habrá fila productiva hasta recibir documento y aprobación verificables.

| Atributos | Tipos/restricciones propuestos | Propósito |
|---|---|---|
| id_version_documento | INTEGER identity PK | Clave técnica, sin conversión UUID |
| referencia | VARCHAR(30) NOT NULL UNIQUE, no vacía | Compatible con version_texto actual; identifica una definición inmutable |
| documento_id, version | TEXT NOT NULL; UNIQUE(documento_id, version); no vacíos | Identidad lógica y edición, sin ordenar etiquetas para elegir vigencia |
| contenido_original, tipo_media, sha256_original | BYTEA, TEXT, CHAR(64) NOT NULL | Conservar bytes originales, formato y huella verificable |
| texto_presentado, sha256_texto | TEXT y CHAR(64) NOT NULL | Mantener el texto UTF-8 del contrato actual, separado del original PDF/DOCX si lo hubiera |
| autoridad_aprobadora, aprobado_en | TEXT y TIMESTAMPTZ NOT NULL | Datos reales de la aprobación; no inferir autoridad del rol ADMINISTRADOR |
| evidencia_aprobacion, sha256_aprobacion | BYTEA y CHAR(64) NOT NULL | Evidencia exacta conservada y verificable, no solo un enlace mutable |
| publicado_por, publicado_en | INTEGER FK usuario.id_usuario; TIMESTAMPTZ NOT NULL | Operador técnico y fecha, distintos de la autoridad institucional |
| vigente_desde | TIMESTAMPTZ NOT NULL | Fecha explícita de aplicabilidad, sin valor automático ni margen académico |

CHECK de no vacíos y formato hexadecimal completo; comprobar las tres huellas
contra sus bytes/texto al escribir y al recuperar. Función SQL concreta de hash
se verificará en PG17 al implementar, sin asumir extensiones instaladas. Hash
correcto no demuestra por sí mismo una aprobación real: publicación exige proceso
controlado que verifique autoridad, evidencia y representación presentada.

Guards de UPDATE/DELETE/TRUNCATE para preservar TODA versión publicada, también
cuando todavía no tiene aceptaciones. Sin ON DELETE CASCADE. Una corrección crea
otra versión/referencia; no cambia contenido, aprobación o metadatos históricos.
No se añade endpoint público de publicación ni se otorga ese permiso a un rol
por iniciativa técnica. El proceso y responsable de publicación deben aprobarse.
La representación aceptada debe corresponder al documento realmente aprobado;
no equiparar un texto extraído o un PDF exportado con los bytes originales.

### 3.2 Adaptaciones de tablas existentes

| Tabla/atributos nuevos propuestos | Relación y garantía |
|---|---|
| asignacion_caso.consentimiento_vigente_id INTEGER NULL | FK a la versión publicada; selector controlado por servidor, nunca por alumno. NULL legado conserva cierre seguro |
| consentimiento.id_version_documento INTEGER NULL | FK exacta al documento publicado. NULL legado NO prueba aprobación |
| consentimiento.aceptacion_explicita BOOLEAN NULL y huella_aceptada CHAR(64) NULL | Solo True con huella completa y documento verificable constituye evidencia nueva; no rellenar legado |
| consentimiento.id_asignacion_origen INTEGER NULL | FK a asignacion_caso; conserva el ámbito que acreditó la aceptación. No obliga a repetir aceptación en otra asignación si selecciona la misma versión |
| participacion.id_consentimiento INTEGER NULL | FK a aceptación exacta usada al crear P, protegida contra sustitución; legado permanece NULL |

Proponer FK compuesta `(id_version_documento, version_texto, huella_aceptada)` a
`(id_version_documento, referencia, sha256_texto)` con UNIQUE parental necesario.
La huella del documento original se conserva además en el documento, sin confundir
ambas representaciones. CHECK exige evidencia nueva completa o todas sus columnas
nuevas NULL en legado; una FK sola no acredita voluntad explícita o titularidad.

Unicidad parcial propuesta en consentimiento `(id_estudiante,id_version_documento)`
para evidencia explícita no revocada: una aceptación vigente reutilizable, muchas
aceptaciones históricas por alumno. Legado queda fuera del índice. No se autoriza
un flujo de reaceptación tras revocación por añadir ese índice. Si se aprueba, un
reintento explícito coincidente y autorizado devuelve el mismo id persistido;
ambigüedad, referencia/hash diferentes o legado sin prueba fallan cerrados.

P nuevas exigen enlace completo, titular de C igual al alumno de grupo_estudiante,
aceptación previa/no revocada y documento aplicable a A en esa transacción. El
trigger de INSERT y el servicio deben verificarlo: NOT NULL universal rompería
historia y no es la transición propuesta. P e I históricas nunca se reescriben.
No imponer automáticamente igualdad universal I.consentimiento=P.consentimiento:
los intentos históricos pueden tener otra relación, y la repetición está bloqueada.
Para el primer intento del flujo combinado, conservar el mismo registro validado
antes de crear P. Los demás casos requieren contrato, no una asociación inventada.

## 4. Conflicto real del selector con los guards actuales

`20261102_assignment_bridge.py::bd205_asignacion` valida PUBLICADO y bloquea
version_caso en TODO UPDATE de asignacion_caso, aunque solo cambie una columna
nueva. Actualizar el selector de una asignación ligada a una versión ARCHIVADO
fallaría. Añadir una columna no resuelve esa semántica. No se modificó ese guard
ni su migración histórica. Hay que aprobar el ámbito de las actualizaciones:
si solo se activan definiciones en asignaciones todavía ejecutables, conservar
el guard; si deben actualizarse otras, especificar la operación administrativa y
su excepción estricta, sin permitir reasignar caso/versión ni historia.

## 5. Transacciones y escritores: plan ejecutable, no garantía ya implementada

1. Publicación: verificar aprobación y representaciones; INSERT de versión
   inmutable, sin declararla automáticamente aplicable a todas las asignaciones.
2. Activación: bloquear los contextos en orden determinista y actualizar únicamente
   los selectores expresamente autorizados; resolver el punto del guard anterior.
3. Aceptación: revalidar actor ESTUDIANTE y ámbito persistente de convocatoria/
   matrícula/asignación; bloquear cuenta, selector y definición conforme al orden
   compatible con la UoW actual. Resolver en servidor, validar True y referencia/
   huellas presentadas, insertar evidencia o recuperar la misma evidencia nueva
   inequívoca. La operación no concede admisión ni crea P/I.
4. Provisión: reutilizar locks/UoW existentes. Mantener selector y C bloqueados,
   validar consentimiento ANTES de agregar P y guardar el id exacto en el INSERT.
   Si cambia selector primero, rechazar hasta nueva aceptación; si provisión gana
   primero, su enlace histórico se conserva. Un error revierte todo.
5. Inicio: reutilizar preparar_inicio_en_uow, sin otro motor. El guard de revocación
   y cualquier futuro escritor deben operar sobre la misma aceptación en una UoW.
   Si inicio confirma EN_CURSO primero, revocación se rechaza; si una revocación
   autorizada confirma primero, inicio se rechaza. Un vencimiento no persistido
   no concede por sí solo permiso de revocación.

No hay política general de revocación ni endpoint nuevo. El guard interno existente
no protege SQL que lo eluda; para prometer esa garantía se necesitan triggers y
pruebas cruzadas de I/C, sin debilitar los guards actuales. El orden de locks debe
probarse para publicación/aceptación/provisión/revocación; no afirmar ausencia de
deadlocks por inspección. No hacer commits dentro de repositorios de Session prestada.

Una P ya creada, aún sin primer intento, cuando cambia el consentimiento: contrato
pendiente. No cambiar su enlace ni inventar si puede iniciar con versión anterior.
Mantener cerrado ese caso hasta decisión; no bloquea diseñar documentos/aceptación.

## 6. Primera unidad a autorizar y archivos afectados

Autorizar expresamente la tabla técnica (31→32 físicas, ER académico intacto),
las columnas/FK anteriores, la unicidad para evidencia nueva y el selector por A.
Una futura revisión aditiva dependerá de `20261105_waiting_admission`; no hay
identificador de revisión creado ni DDL aplicado en esta tarea.

| Archivo | Cambio futuro concreto |
|---|---|
| identity/infrastructure/consent_document_models.py (nuevo) | ORM de versión publicada, no otro modelo de aceptación |
| identity/infrastructure/academic_base_models.py | Campos de evidencia en ConsentimientoORM |
| scheduling/infrastructure/assignment_models.py | Selector explícito, sin modificar sala de espera |
| participation/infrastructure/models.py | FK nullable de P, sin tocar respuestas/resultados |
| app/db/models.py | Registro único del modelo nuevo |
| identity/application/consent.py | Extender contrato para procedencia y consulta histórica por referencia |
| identity/infrastructure/consent_repository.py (nuevo) | Adaptador SQL de FuenteConsentimiento y lectura histórica |
| identity/infrastructure/consent.py | Ampliar el servicio existente: evidencia durable e idempotencia verificable |
| participation/infrastructure/provision.py y start.py | Persistir enlace exacto y reutilizar validación antes de P/I |
| alembic/versions/<fecha>_consent_version.py (futuro) | Tabla/columnas, FK/CHECK/índice y guards revisados, sin backfill |
| tests/integration/test_consent_version_persistence.py (nuevo) | Aceptación real del esquema/adaptador en PG17 propio |

Preflight: detectar duplicados, referencias legadas y P/I sin correspondencia;
no asignar documentos por etiqueta, fecha aproximada o alumno ficticio. Campos
nuevos nullable para legado; guards para nuevas escrituras se despliegan coordinados
con escritores adaptados. No instalar un guard que rompa escritores legítimos sin
actualizarlos y probarlos. No modificar revisiones anteriores.

Downgrade propuesto: bloquear las tablas afectadas, comprobar ausencia de cualquier
nueva publicación/evidencia/selector/enlace y rechazar si se perdería información;
solo en esquema vacío retirar objetos propios. No borrar evidencia para revertir.
Upgrade/downgrade y garantías SQL futuras NO se han probado ni se declaran existentes.

## 7. Pruebas actuales y pendientes, sin aumentar estadísticas

Se ejecutaron los tests existentes de consentimiento interno y sala de espera,
no pruebas nuevas artificiales ni otra suite general: **56 aprobadas, 0 omitidas,
0 fallidas, 0 errores, 1 advertencia Starlette conocida**, 76.08 s.
HEAD probado: `28be564`, mismo contenido Python que los checkpoints.
Comando: `C:\Python313\python.exe -B evidencias/checkpoints_consentimiento_20261106T031805Z/ejecutar_validacion.py casos`.
El runner desactiva lectura de .env/URLs externas en el hijo; usa PostgreSQL17
nuevo, etiquetado, tmpfs y puerto TCP efímero. No bases permanentes.

Logs, XML nominal y huellas:
`evidencias/checkpoints_consentimiento_20261106T031805Z/pruebas_casos_20261106T032316Z/`.
Los 24 casos de consentimiento usan fuente documental LAB y SQL de aceptaciones
real; los otros 32 prueban main/Identity/Scheduling/admisión real. No sumar estas
56 al histórico 2158: se solapan. La general 2158/38 no se ejecutó de nuevo;
no cambió código compartido, ORM ni migraciones después de los checkpoints.

| Garantía | Evidencia actual o estado |
|---|---|
| Documento vigente/reemplazado | Tests internos con FuenteConsentimientoLaboratorio; NO SQL de documentos oficiales |
| Aceptación ausente/ajena/negada | test_consentimiento_rechazado_antes_de_cualquier_insert_p y test_consulta_ajena_no_acredita_aceptacion |
| Acción explícita y recuperación SQL | test_aceptacion_explicita_persistida_y_recuperada_en_otra_session; el esquema aún no conserva todos los metadatos propuestos |
| Cambio de versión | test_version_nueva_exige_nueva_aceptacion_sin_reescribir_la_anterior, fuente LAB |
| Revocación activa | test_guard_no_permite_revocar_con_intento_en_curso; guard de aplicación, no protección SQL nueva |
| Rollback/concurrencia de aceptación | test_rollback_aceptacion_no_deja_fila; test_dos_aceptaciones_concurrentes_no_duplican_registro: un éxito y otro cierre seguro, NO idempotencia transparente |
| Enlace histórico P→C, documento/aprobación SQL, fuente SQL vigente y huellas, nuevo índice/guards | PENDIENTES; no existen ni se dan por acreditados |
| Upgrade/downgrade nuevo y carrera selector↔P o revocación↔inicio | PENDIENTES de diseño aprobado y prueba PG real |

Criterios de aceptación de la futura unidad: versión publicada recuperable desde
otra Session con sus bytes y evidencia idénticos; no modificación/borrado SQL;
selector explícito y cerrado si ausente; aceptación propia/expresa idempotente;
P no insertada si falta prueba y enlace conservado tras cierre; legado sin fake
backfill; dos carreras con ganadores inequívocos/rollback; reversión controlada;
regresión compartida sin omitir fallos. Nada de ello publica calificaciones.

## 8. Decisiones y siguiente paso

1. Aprobar o ajustar el diseño físico concreto y su ámbito (incluye una tabla
   técnica adicional, no ampliación automática del ER académico aprobado).
2. Confirmar la representación que será aprobada/presentada y el proceso/autoridad
   real de aprobación y publicación. No hay valores productivos que insertar hoy.
3. Definir tratamiento de P existente sin intento ante cambio de documento; no
   inventar repetición, permisos excepcionales ni revocación fuera de la regla dada.

RF-12 permanece PARCIAL. RF-22 acreditado no se modifica. Los 27 RF mantienen
14 IMPLEMENTADO, 8 PARCIAL y 5 BLOQUEADO. Checkpoints y propuesta no completan RF.
No se registran rutas de aceptación/provisión/inicio ni notas oficiales.

Siguiente incremento: con aprobación física, implementar primero la versión
publicada SQL y su fuente histórica, evidencia de aceptación y enlace P en una
unidad coordinada probada en PG17 propio. Mantener vacía la publicación productiva
hasta aprobación institucional; la ausencia de documento no se suple con el borrador.
