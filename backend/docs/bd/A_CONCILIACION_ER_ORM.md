# A — Correspondencia del ER oficial de 28 tablas con el ORM

**BD-1.2 · solo análisis y diseño.** La única referencia académica objetivo es sps.dbml original. El [DBML objetivo de 28](ER_OBJETIVO_APROBADO_28_TABLAS.dbml) reproduce sus atributos/PK/FK/defaults; no usa la propuesta histórica de 40.

Estado comprobado en memoria, sin motor/conexión: **19 integradas + 2 declaradas pendientes**. Clasificación de las 28 entidades: 4 fieles, 11 parciales y 13 sin tabla ORM productiva. «Integrada» no significa aplicada en PostgreSQL.

| Tabla oficial | Modelo actual / función cercana | Estado | Diferencia demostrable | Implementación recomendada | Incompatibilidad / aprobación |
|---|---|---|---|---|---|
| rol | rol / RolORM | Fiel; integrada | INTEGER, nombre UNIQUE y descripción coinciden. | Conservar; reutilizar Identity. | No cambiar contratos ni datos. |
| permiso | permiso / PermisoORM | Fiel; integrada | INTEGER, código UNIQUE y descripción obligatoria coinciden. | Conservar; permisos del servidor. | Tabla no prueba autorización de cada operación. |
| rol_permiso | rol_permiso / RolPermisoORM | Fiel; integrada | PK compuesta y FK de acceso coinciden. | Conservar. | No convertir permisos en membresía. |
| usuario | usuario / UsuarioORM | Fiel; integrada | PK INTEGER y rol único, correo/hash/activo coinciden. | Conservar cuenta y JWT; ninguna conversión a UUID. | El dominio expone ID como cadena; no es otra identidad. |
| grupo_academico | Sin equivalente directo; espacio_academico no es grupo | Sin ORM | Faltan id_grupo, profesor usuario, nombre y período del ER. | Implementar entidad original tras acordar padrón/grupos. | No crear grupos para cada espacio existente por inferencia (R03/R08). |
| grupo_estudiante | Sin ORM; convocatoria no es matrícula | Sin ORM | Faltan PK de membresía, grupo/usuario, ingreso/activo y UNIQUE(grupo,usuario). | Conservar el diseño original en objetivo; altas verificadas. | El ER no guarda episodios/reingreso; no se restaura M2 de BD-1.1 (R08). |
| consentimiento | Puerto IdentityPort y dominio; sin ORM | Sin ORM | Texto versionado y aceptación/revocación no están persistidos. | Crear estructura original con FK a usuario; ninguna aceptación ficticia. | intento exige consentimiento en el ER; alcance D03 previo no resuelto (R05). |
| caso | caso / CasoModel + version_caso / VersionCasoModel | Parcial; integrada | Caso actual: UUID/creador UUID/fecha con zona; título, estado y contenido viven en versión. ER: PK int, profesor usuario y contenido en caso. | Conservar implementación mientras se define migración de identidad/contenido. | Dos versiones y sus rúbricas no caben en una única fila ER sin pérdida; R02. |
| objetivo_aprendizaje | Sin ORM | Sin ORM | ER: caso INTEGER, descripción y orden UNIQUE por caso. | Crear la entidad del ER; no asociarla a version_caso en este objetivo. | Contenido no deducible de desarrollo/contexto. |
| escena | escenario / EscenarioModel | Parcial; integrada | UUID, FK a versión, orden/contexto; ER usa int/caso y exige título/tipo. | Mapeo explícito de contenido y IDs, no solo renombre. | Título/tipo legados desconocidos bloquean backfill, no cadenas ficticias. |
| personaje | Sin ORM | Sin ORM | Nombre/descripción por caso INTEGER no existen. | Crear entidad original, separada de personas de Identity. | No extraer personajes automáticamente del texto. |
| personaje_escena | Sin ORM | Sin ORM | PK personaje/escena y dos FK originales no existen. | Crear relación original N:M. | Mismo caso debe comprobarse adicionalmente; el ER no lo garantiza por FK simple. |
| decision | pregunta / PreguntaModel; valoracion_opcion tiene otra granularidad | Parcial; integrada | ER exige un criterio por decisión y IDs int; ORM pregunta UUID sin criterio, valoración por opción/criterio. | Resolver R02/R06 antes de transformar preguntas. | Una opción con varios criterios es representable hoy y no se reduce a un criterio sin decisión académica. |
| opcion_respuesta | opcion_respuesta / OpcionRespuestaModel | Parcial; integrada | UUID/pregunta/justificacion vs int/decisión/justificacion_teorica; falta destino de escena y UQ opción/decisión del ER. | Preservar campos y rutas del ER en destino; plan de IDs. | No convertir la PK ni suponer ramificación ya implementada. |
| pista | Sin ORM | Sin ORM | ER guarda texto por decisión INTEGER. | Crear entidad original. | Visibilidad/penalización no se inventan. |
| rubrica | rubrica / RubricaModel | Parcial; integrada | UUID por versión, version_regla; ER int UNIQUE por caso y nota_maxima decimal(4,2). | Conservar ORM actual hasta resolver R02/R06; no degradar versión. | No hay nota_maxima actual ni fórmula aprobada demostrada. |
| criterio_rubrica | criterio_rubrica / CriterioRubricaModel | Parcial; integrada | UUID/rúbrica UUID/peso; ER int/rúbrica int/peso_porcentaje. | Exigir equivalencia académica antes de trasladar peso. | Nombre distinto no demuestra porcentaje; escala R06. |
| nivel_criterio | nivel_rubrica / NivelRubricaModel | Parcial; integrada | UUID/puntaje/descriptor vs int/logro_porcentaje; ER UQ criterio/nombre y nivel/criterio. | Mapeo certificado de niveles; no conversión de puntaje por inferencia. | Cambiar nombre no resuelve escala ni datos duplicados. |
| asignacion_caso | sesion_programada + convocatoria + espacio_academico; sin ORM homónimo | Parcial; función distribuida | ER: grupo/caso int, horario/umbral, intentos y hash grupal; ORM: sesión UUID/version/espacio y código individual por convocatoria. | Implementar asignacion_caso como objetivo; se retira su sustitución por el modelo de 40. | Convocatoria individual, matrícula y horarios no son equivalentes exactos (R03). |
| participacion | Participacion de dominio; sin ORM | Sin ORM | Dominio conserva IDs int de asignación/membresía; no tiene relación persistida con convocatoria UUID de 8A. | Crear tabla original, UQ(asignación,membresía), default pendiente literal. | No imponer una participación por convocatoria del modelo de 40; puente a 8A pendiente R03. |
| permiso_intento_extra | PermisoIntentoExtraORM en academic_metadata | Parcial; no integrada | PK/profesor/cantidad/texto/fecha acordes; FK a participación no resuelta y tipo local NULLTYPE en esa columna. | Integrar una sola clase/tabla cuando exista participación. | No registrar metadata incompleta ni duplicarla; creador/cupo se valida en servicio. |
| intento | Intento de dominio; sin ORM | Sin ORM | IDs/consentimiento/permiso/número/estado/fechas; dominio conserva duración que el ER no almacena. | Crear definición original; tiempo individual necesita contrato de reconstrucción estable. | Consentimiento NOT NULL y timestamps sin zona requieren R05/R07; sin vence_en agregado automático. |
| paso_simulacion | PasoSimulacion de dominio; sin ORM | Sin ORM | ER FK opción/decisión y UQ intento/número; no UQ por pregunta. Dominio representa última selección. | Crear tabla original; elegir proyección vigente o registro secuencial dentro de esta misma tabla. | Historial append-only posible con contrato de lectura/escritura distinto; no ya implementado (R08). |
| resultado_intento | DatosEvaluacion/servicio; sin ORM productivo | Sin ORM | UQ intento, nota decimal(4,2), fecha/comentario sin columnas de versión/política. | Persistir solo evaluación definitiva con referencia académica estable por cadena del ER. | No datos de ejemplo ni precisión/fórmula inventadas; R02/R06. |
| resultado_criterio | ResultadoCriterio de dominio; sin ORM | Sin ORM | FK nivel/criterio compuesta; cabecera por intento obligatoria. | Crear estructura original para resultados por intento. | No permite guardar detalle de ausencia sin intento/nivel; no crear ficticios (R06). |
| resultado_participacion | Puerto/resultados de aplicación; sin ORM | Sin ORM | UQ participación, situación/nota no NULL, fecha/observación. | Definitivo por participación; pendiente = sin fila definitiva. | Puede representar cabecera de ausencia sin intento; detalle y consolidación no quedan resueltos. |
| retroalimentacion_docente | RetroalimentacionDocenteORM en academic_metadata | Parcial; no integrada | Campos del ER, UQ asignación, FK a asignación sin resolver y NULLTYPE local. | Conservar entidad original; no sustituirla automáticamente por feedback_participacion. | No expresa destinatario individual RF-26; cambio dentro de la entidad necesita R04. |
| notificacion | notificacion / NotificacionModel | Parcial; integrada | UUID/destinatario UUID/convocatoria/canal/estado vs int/usuario/asignación/envío/lectura. | Preservar avisos actuales; migrar destinatario solo con evidencia y decidir entrega R09. | Mismo nombre con PK/FK y semántica incompatibles; no reemplazar in situ. |

## Coincidencia de nombres frente a equivalencia real

Hay **9 nombres de tabla comunes** a Base.metadata y al ER: rol, permiso, rol_permiso, usuario, caso, opcion_respuesta, rubrica, criterio_rubrica, notificacion. Solo los cuatro de acceso son fieles; compartir nombre no hace compatibles las cinco estructuras restantes.

Hay **10 nombres integrados que no figuran literalmente** entre las 28 tablas. Tres son equivalencias parciales de nombres del ER; los siete restantes contienen información técnica o de negocio distribuida que tampoco puede borrarse sin evaluar consumidores:

| Tabla integrada fuera del listado literal | Relación con el ER | Información/consumidores que se perderían al retirarla |
|---|---|---|
| escenario | Parcial de escena | Contexto/orden de una versión UUID; no título/tipo original |
| pregunta | Parcial de decision | Opciones por escenario; falta criterio directo del ER |
| nivel_rubrica | Parcial de nivel_criterio | Descriptor/puntaje; no prueba de logro porcentual |
| identidad_academica | Sin entidad directa; hoy puente de usuarios INTEGER/UUID | Resolver persistente y autorización Cases/Scheduling/8A |
| version_caso | Parte del rediseño de caso; no entidad oficial | Ediciones, publicación y rúbrica exacta utilizadas por sesión/8A |
| valoracion_opcion | Diferente de decision.id_criterio | Aportes numéricos de cada opción a varios criterios |
| espacio_academico | No equivale a grupo_academico | Espacio elegido por Scheduling sin período/matrícula/grupo |
| sesion_programada | Función parcial de asignacion_caso | Estados, responsable, horario, lugar/mensaje, versión y cierre |
| convocatoria | Parte del acceso individual; sin tabla homónima en ER | UUID en JWT, hash individual, estado ACTIVA/RETIRADA, usuario académico |
| evento_auditoria | Sin entidad directa | Trazabilidad de cambios de sesión y observadores |

Las 2 clases académicas pendientes sí tienen nombres del ER, pero **no pertenecen a las 19**: permiso_intento_extra y retroalimentacion_docente. Son la misma propiedad conceptual, no dos nuevas tablas que deban crearse otra vez con otro dueño. Sus FK externas aún no se resuelven; no se oculta este bloqueo asignando un tipo arbitrario.

## Fuentes verificables del código actual

- Identity: [models.py](../../app/modules/identity/infrastructure/models.py), [academic_identity_models.py](../../app/modules/identity/infrastructure/academic_identity_models.py), [academic_models.py](../../app/modules/identity/infrastructure/academic_models.py).
- Cases: [caso.py](../../app/modules/cases/infrastructure/models/caso.py), [rubrica.py](../../app/modules/cases/infrastructure/models/rubrica.py).
- Scheduling: [models.py](../../app/modules/scheduling/infrastructure/models.py).
- Registro: [db/models.py](../../app/db/models.py); Participation: [entities.py](../../app/modules/participation/domain/entities.py) y [integration.py](../../app/modules/participation/infrastructure/integration.py).

No se propone eliminar las diez tablas de nombre adicional para «hacer cuadrar» 28. [D](D_DECISIONES_Y_RIESGOS.md) distingue esquema académico, transición y un eventual esquema físico único; [C](C_PLAN_MIGRACIONES_ALEMBIC.md) condiciona cualquier DDL a esa decisión.
