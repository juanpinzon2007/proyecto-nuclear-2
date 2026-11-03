# D — Incompatibilidades, alternativas y aprobaciones para el objetivo de 28

**BD-1.2 · objetivo vinculante: las 28 entidades oficiales.** Ninguna alternativa aquí autoriza tablas adicionales, cambios de código o migraciones. La propuesta BD-1/BD-1.1 de 40 tablas/73 FK queda retirada como objetivo y conservada solo como antecedente.

## 1. Tres planos que no se deben confundir

1. **Modelo académico aprobado:** 28 tablas, 156 atributos y 40 FK del original; nuevo DBML idéntico en definiciones.
2. **Implementación existente:** 19 tablas integradas y dos clases pendientes; UUID/versiones/sesión/convocatoria y contratos reales que se conservan.
3. **Esquema físico:** no inspeccionado. No se conoce su revisión aplicada ni datos efectivos; no se presume que ninguna tabla haya sido creada.

Conservar hoy el backend existente no aprueba sus diez nombres adicionales como ampliación definitiva del ER. Tampoco permite eliminarlos para alcanzar 28. La transición requiere una estrategia explícita y pruebas posteriores.

## 2. Demostración de incompatibilidad con un reemplazo directo

| Conflicto | Evidencia de código/esquema | Consecuencia si se reemplaza por el ER sin adaptar código |
|---|---|---|
| Nombre y tipo de PK de caso | CasoModel usa id UUID; ER usa id_caso INTEGER y profesor INTEGER | SELECT/INSERT del ORM esperan columnas distintas y FK como caso.id dejan de resolverse. Un UUID no se convierte en ID oficial INTEGER |
| Contenido versionado | VersionCasoModel con UNIQUE(caso_id,numero), escenarios/rúbrica por versión; sesión referencia version_caso.id | El ER no tiene version_caso. Código y FK actuales requieren esa tabla. Dos versiones con contenido/rúbrica distintos no caben en una sola fila caso con una rúbrica UNIQUE |
| Valoración multicriterio | ValoracionOpcionModel PK(opcion_id,criterio_id); PreguntaModel sin criterio directo | ER decision tiene exactamente un criterio obligatorio. Datos válidos actuales con varios criterios por opción no se reducen sin pérdida/decisión académica |
| Sesión/convocatoria | SesionProgramadaModel/ConvocatoriaModel UUID; id_convocatoria en JWT y ValidadorConvocatoriaScheduling | asignacion_caso por grupo no sustituye esos UUID/contextos ni código individual. El login/8A dejaría de encontrar convocatoria si se retirase la tabla |
| Organización desconocida | Scheduling tiene espacio y estudiantes UUID; ER exige grupo y matrícula reales | No se puede fabricar período, grupo o inscripción de un convocado. Falta de dato no se arregla creando un grupo genérico |
| Igual nombre con estructura diferente | opcion_respuesta, rubrica, criterio_rubrica y notificacion ya existen con UUID/FK distintas | No crear una segunda tabla homónima en el mismo schema/metadata, ni usar extend_existing para tapar el conflicto |
| Identidad personal | Usuario INTEGER; alias UUID por sistema almacenados hoy | Quitar identidad_academica rompe resolver/titularidad. El objetivo final podría usar FK directas a usuario, pero eso exige adaptar los consumidores y verificar dueños |
| Tiempos | ORM con TIMESTAMP WITH TIME ZONE y dominio aware; ER timestamp sin zona | Cast/ALTER TYPE sin contrato de zona cambia instantes o ambigüedad. No asumir zona de timestamps históricos |
| Campos funcionales fuera del original | tiempo_estimado_min en versión; lugar/mensaje en sesión | El ER exacto no contiene esos campos académicos de RF-05/18; no perderlos ni confundir tiempo estimado con máximo autorizado |

Fuentes: [Cases ORM](../../app/modules/cases/infrastructure/models/caso.py), [rúbrica](../../app/modules/cases/infrastructure/models/rubrica.py), [Scheduling ORM](../../app/modules/scheduling/infrastructure/models.py), [resolver](../../app/modules/identity/application/academic_identity.py), [login](../../app/modules/identity/infrastructure/scheduling_access.py), [8A](../../app/modules/participation/infrastructure/integration.py).

**Conclusión técnica:** no es posible tener exactamente las definiciones oficiales como único esquema físico y mantener sin cambios todos los ORM/consultas/contratos actuales. Sí se puede diseñar una transición hacia 28 conservando el código actual durante esta fase. La incompatibilidad no autoriza ampliar a 40.

## 3. Alternativas reales, ninguna ejecutada

| Alternativa | Qué conserva y qué exige | Límite |
|---|---|---|
| A. Objetivo físico único de 28, con adaptación gradual del backend | Se mantiene el objetivo académico; futuros modelos/adaptadores/contratos se reorientan a INTEGER y asignación/matrícula. Casos y referencias requieren importación verificada | Es la dirección conforme a la solicitud, pero necesita resolver R02–R09 y autorización de futuras modificaciones; no compatibilidad automática |
| B. Coexistencia temporal y aislada durante transición a A | Mantener las estructuras actuales en su namespace mientras se ensaya el destino en laboratorio/schema de transición, sin conflictos de nombres | Durante la transición habrá más de 28 tablas físicas; **no es el objetivo final ni está autorizada aquí**. Si se exige 28 incluso durante transición, usar copia aislada, nunca crear paralelo en ambiente del equipo |
| C. Declarar 28 solo como vista académica del ORM de 19 | Evitaría reescritura inmediata, pero una proyección no demuestra las PK/FK/atributos aprobados ni crea entidades ausentes | No se recomienda como supuesto cumplimiento; requiere aceptar expresamente otro modelo físico. Tampoco es aprobación de 40 |
| D. Ajustes puntuales dentro de las mismas 28 entidades | Agregar/modificar columnas/relaciones donde RF y ER se contradicen, previa aprobación académica y del equipo | Mantiene 28 entidades, pero deja de ser reproducción exacta del original en atributos/relaciones. **No aplicado al DBML entregado** |

Recomendación: A como destino, con B solo si se autoriza un entorno transitorio y se define salida verificable. Antes de programar, decidir si se permite D para resolver RF concretos. Si se exige simultáneamente ER idéntico, contratos existentes idénticos y esquema físico único de 28, se debe detener el punto incompatible, no ocultarlo con vistas, JSON o conversiones de UUID.

## 4. Decisiones concretas previas a BD-2

| ID | Quién decide / pregunta | Recomendación o alternativa sin nuevas entidades automáticas | Qué bloquea |
|---|---|---|---|
| R01 | Usuario/equipo: ¿28 es el destino físico único y se permite coexistencia temporal fuera de ese destino? | Mantener 28 como objetivo. Autorizar por separado laboratorio/transición; no ampliar el ER por conservar temporalmente el backend | Estrategia DDL, namespace y orden de integración |
| R02 | Cases + académico: ¿cómo preservar versiones e identidad estable del caso dentro de 28? | Una fila caso independiente e inmutable por edición usada puede preservar cada contenido/rúbrica, pero pierde relación formal de versiones. Otra opción: campos de procedencia/autorreferencia en caso, solo si se aprueban. No colapsar versiones distintas | Migración de Cases, sesiones históricas, referencias de 8A |
| R03 | Scheduling + académico: ¿cómo representar convocatoria individual, espacio/grupo, RF-05/18 y continuidad de códigos? | Puede proponerse enriquecer participacion como invitación de una asignación/matrícula con hash individual y referencias de procedencia, y conservar atributos necesarios en caso/asignacion. Son cambios de columnas/semántica por aprobar, no tablas nuevas ni supuestos del DBML | Login contextual, roster, programación e ingreso reales |
| R04 | Académico + seguimiento: ¿feedback es individual como RF-26? | Recomendar reorientar retroalimentacion_docente hacia participación con autor/fecha conservados; revisar UQ y legado por asignación. Alternativa observacion de resultado es limitada: requiere nota definitiva y no conserva autor/fecha del comentario por separado | RF-26/27 fieles y migración de comentarios |
| R05 | Académico/privacidad: ¿consentimiento obligatorio en todo intento o hay no aplicable? | ER lo exige NOT NULL. Si se aprueba no aplicable, proponer nullable en la misma entidad y resolver aplicabilidad confiable; no aceptación ficticia. Si se confirma universal, obtener evidencia real antes de inicio | Inicio sin consentimiento real; no bloquea diseñar tabla vacía |
| R06 | Académico/Evaluation: escala, equivalencia peso/puntaje, parcial/ausencia, consolidación y trazabilidad de regla | El ER ya tiene porcentajes/máximo; no inventar fórmula. Cero por ausencia en resultado_participacion sin intento; detalle reconstruible solo con contenido/regla inmutables y universo aprobado. Campos de referencia de regla en resultados podrían requerir aprobación | Calificación oficial y traslado multicriterio/ausencias |
| R07 | Académico/Scheduling: RF-22 y tiempo individual estable; equipo: zona de timestamps | Umbral del servidor solo tras aprobación; tiempo individual reconstruido de inicio + máximo exige asignación inmutable o campo aprobado en intento. Fechas UTC explícitas para nuevos datos, nunca asumir zona de legado | Ingreso RF-22, vencimiento reproducible y migración de fechas |
| R08 | Académico/equipo: matrícula/reingreso, recorrido ramificado y último valor/historial de pasos | Mantener UNIQUE original de matrícula hasta decidir. paso_simulacion puede registrar cambios secuenciales con proyección última por decisión, pero necesita contrato nuevo e invalidación de rutas aprobada. Sin tabla histórica extra por defecto | Reingreso, progreso de rutas y persistencia de cambios |
| R09 | Equipo/seguridad: correspondencias verificadas, contratos UUID/INTEGER, entrega/auditoría y rollback | Manifiesto de migración verificable y conservación de origen; no puente productivo efímero ni reinterpretación de IDs. Notificacion puede servir de cola básica, pero reintentos/dedup requieren diseño seguro, quizá columnas aprobadas en esa misma tabla | Datos históricos, retiro seguro de estructuras técnicas y notificaciones confiables |

RF-22 sigue pendiente; aprobar 28 tablas no aprueba su umbral. RN-21 (congelación publicada) y RN-22 (catálogo académico) eran propuestas: no se vuelven reglas oficiales por una migración.

## 5. Integridad técnica a resolver sin añadir entidades

| Garantía | Soporte oficial / trabajo posterior |
|---|---|
| Titularidad y rol | FK usuario existe. Identity autentica/autoriza; comprobar usuario de membresía, consentimiento y permiso bajo la misma UoW |
| Opción de decisión / nivel de criterio | Conservar exactamente las dos FK compuestas oficiales; validar también que correspondan al caso/rúbrica usados |
| Un intento activo / un resultado | UQ resultado/intento ya en ER; índice parcial activo y guardas de estado propuestos sobre intento, no tabla nueva |
| Publicación, ruta y ámbito | Validación Cases y guardas intertabla; no inferir destino NULL ni eliminar pasos por otra rama |
| Tiempo y transacción | Reloj inyectado, bloqueos y un commit; sin CHECK con now() ni snapshot 8A usado como permiso |
| No pérdida académica | Congelar contenido/rúbrica referenciados o aprobar campos de referencia dentro de 28; sin recalificar histórico automáticamente |
| Feedback y entrega | No distribuir comentario grupal ni guardar códigos en claro; conservar mensajes/notificaciones actuales mientras falta correspondencia |

## 6. Qué queda expresamente sin autorización

- Ninguna ampliación del ER a 40 ni tablas del modelo histórico (historial_decision, politica_academica, evento_salida, etc.).
- Ningún DROP de las diez tablas de nombre adicional del ORM, ni cambio de PK, renombre de columna o borrado de alias.
- Ningún cambio propuesto de columnas/FK de R02–R09 está ya aprobado o incluido silenciosamente en el nuevo DBML.
- Ninguna migración, escritor, API nueva, ejecución PostgreSQL o conexión a base compartida.
- El hito BD2-01 de BD-1.1 **no es un plan vigente automático** para este rumbo. Las asociaciones actuales se conservan; cualquier incremento de claves de dueño debe revisarse con R01 y los consumidores del destino de 28.

8A permanece intacta: conserva JWT/rol/resolver, convocatoria/sesión y versión/rúbrica exactas. El nuevo documento no convierte sus UUID en los INTEGER oficiales ni declara integrada la persistencia de Participation.
