# BD2-00 — Preparación de la primera implementación del ER oficial de 28 tablas

**Estado: plan para aprobar, no implementación. Fecha: 2026-11-01.** Rama verificada: feature/integracion-backend. HEAD: ee025d275dfdd2805da8833345ad40a71d0e3eb9, con cambios locales previos que se conservan.

## 1. Decisión ejecutiva: qué implementar primero

Recomiendo **U01: base académica mínima**, una revisión aditiva que cree únicamente **grupo_academico, grupo_estudiante y consentimiento, vacías**, con las definiciones oficiales. Comparten un único padre existente: usuario.id_usuario INTEGER. No necesitan resolver casos UUID, versiones, sesiones, convocatorias ni fórmulas para existir.

La unidad futura incluye tres modelos SQLAlchemy, su registro, una revisión Alembic y pruebas. **No incluye repositorios de negocio, servicios, endpoints, carga de estudiantes, aceptaciones, cambios de JWT ni integración de Participation.** Crear consentimiento no aprueba su aplicabilidad universal; crear matrícula no habilita reingreso.

Esta es una elección de menor acoplamiento, no una declaración de riesgo cero: falta inspección física autorizada, revisión de cadena y prueba de DDL. La unidad solo podría ejecutarse después de aprobación y primero en laboratorio desechable. Si cualquiera de las tres tablas ya existe físicamente con otro origen, se detiene; no se usa IF NOT EXISTS ni stamp para ocultarlo.

Proyección si se implementa: **19 + 3 = 22 tablas integradas**, con las 19 anteriores intactas y las dos clases pendientes aún fuera de ese conjunto. Es una transición, no «22 de las 28 ya cumplidas»: diez nombres de las actuales no pertenecen al listado oficial. No se ha autorizado ahora ningún DDL.

## 2. Fuentes y estado verificado

- [ER objetivo aprobado](ER_OBJETIVO_APROBADO_28_TABLAS.dbml) y [fuente original](../../app/modules/identity/reference/sps.dbml): definiciones idénticas, 28 tablas, **144 columnas reales** y 40 FK. SHA-256 original: fb6ab07cfdfee38ba59e1acc879335ec0b377150acc3474b4a817a9eece229d7.
- [Matriz BD-1.2](A_CONCILIACION_ER_ORM.md), [inventario](B_MODELO_RELACIONAL_Y_RESTRICCIONES.md), [decisiones R01–R09](D_DECISIONES_Y_RIESGOS.md) y [RF](E_TRAZABILIDAD_RF.md).
- [Registro de modelos](../../app/db/models.py), [Identity](../../app/modules/identity/infrastructure/models.py), [académicos pendientes](../../app/modules/identity/infrastructure/academic_models.py), [Cases](../../app/modules/cases/infrastructure/models/caso.py), [rúbrica](../../app/modules/cases/infrastructure/models/rubrica.py), [Scheduling](../../app/modules/scheduling/infrastructure/models.py).
- [Alembic env](../../alembic/env.py), revisiones y pruebas citadas abajo; [8A](../../app/modules/participation/INTEGRACION_8A.md) y [adaptador](../../app/modules/participation/infrastructure/integration.py).

Se volvió a inspeccionar metadata en memoria con creación de motores/conexiones bloqueadas. Hay 19 tablas integradas y dos modelos separados: permiso_intento_extra.id_participacion y retroalimentacion_docente.id_asignacion conservan FK no resolubles/NULLTYPE local. No se eliminan esas referencias ni se registran placeholders.

**Errata técnica de BD-1.2:** el conteo anterior de 156 incluía las 12 líneas de apertura de bloques indexes como si fueran atributos. El nuevo conteo reconoce solo declaraciones de tipos de columna del DBML: 156−12=144. Los 28 nombres, PK, FK y definiciones oficiales no cambian. Esta errata afecta el conteo y ciertos inventarios/preámbulos documentales anteriores, no agrega/quita atributos al ER. Por el alcance de BD2-00 se deja constancia aquí y no se modifican los ocho archivos previos. Los bloques indexes nunca deben producir una columna llamada indexes en modelos o pruebas; el lector de tipos de persistence_support.py evita ese error.

No se verificó esquema físico ni alembic_version de PostgreSQL. Ningún dato histórico se afirma existente solo por tener un modelo. La propuesta de 40 tablas no es fuente para esta unidad ni para su autogeneración.

## 3. Preparación de cada una de las 28 tablas

«Falta tabla completa» enumera el destino, no autoriza crearla sobre referencias que aún no existen. FK/UQ indicadas son las del ER; la autorización y la coherencia entre casos requieren aplicación/guardas adicionales.

| Tabla oficial | Implementación actual | Columnas / claves faltantes o incompatibles | Dependencias y tipos | Conflicto y orden de trabajo |
|---|---|---|---|---|
| rol | RolORM, integrada y fiel | Ninguna | PK int y nombre UQ | Conservar sin DDL. |
| permiso | PermisoORM, integrada y fiel | Ninguna | PK int y código UQ | Conservar sin DDL. |
| rol_permiso | RolPermisoORM, integrada y fiel | Ninguna | PK compuesta y FK rol/permiso int | Conservar sin DDL. |
| usuario | UsuarioORM, integrada y fiel | Ninguna | PK int; rol FK; correo UQ; hash/activo | Padre de la primera unidad; no recrear usuarios ni roles. |
| grupo_academico | Sin ORM | Tabla completa: id_grupo, id_profesor, nombre, periodo; PK y FK profesor→usuario | Todos INTEGER salvo textos; usuario ya existe | U01: crear vacía. No equivale a espacio_academico. |
| grupo_estudiante | Sin ORM | Tabla completa: id_grupo_estudiante, id_grupo, id_estudiante, fecha_ingreso, activo; PK, 2 FK y UQ(grupo,estudiante) | Grupo nuevo y usuario existente; timestamp sin zona | U01: crear vacía después de grupo. No reingreso/episodios nuevos. |
| consentimiento | Sin ORM | Tabla completa: id_consentimiento, id_estudiante, version_texto, fecha_aceptacion, fecha_revocacion; PK/FK | Usuario int existente; timestamp sin zona | U01: crear vacía; no aceptación automática ni obligación universal resuelta. |
| caso | CasoModel + VersionCasoModel, parcial | En caso faltan nombres/estructura oficiales: id_caso int, id_profesor int, titulo, introduccion_teorica, estado, fecha_creacion/validacion | Actual id/creador UUID; contenido/estado en versión; fecha con zona | Homónima incompatible: adaptar modelos y resolver versiones antes de DDL o importación. |
| objetivo_aprendizaje | Sin ORM | Todos: id_objetivo, id_caso, descripcion, orden; PK/FK y UQ(caso,orden) | Requiere caso.id_caso INTEGER, inexistente hoy | Es aditiva por nombre, pero no ejecutable con FK oficial sobre caso actual. |
| escena | EscenarioModel/escenario, parcial | id_escena int, id_caso int, titulo, contexto, tipo; UQ(caso,orden); orden actual reutilizable solo tras mapeo | UUID/versión vs INTEGER/caso | Renombre aislado no basta; no generar título/tipo ficticios. |
| personaje | Sin ORM | Todos: id_personaje, id_caso, nombre, descripcion; PK/FK | Padre caso int pendiente | Aditiva después de reconciliar caso. |
| personaje_escena | Sin ORM | id_personaje, id_escena; PK compuesta y ambas FK | Personaje y escena int pendientes | Aditiva solo con padres oficiales, verificar mismo caso. |
| decision | PreguntaModel/pregunta, parcial | id_decision int, id_escena int e id_criterio int obligatorios; UQ(escena,orden) | Enunciado/orden existen; pregunta UUID sin criterio; valoración por opción/criterio | Modelo multicriterio actual no se reduce automáticamente a un criterio por decisión. |
| opcion_respuesta | OpcionRespuestaModel, parcial | id_opcion/int, id_decision/int, id_escena_destino, justificacion_teorica; UQ(decisión,orden) y UQ(opción,decisión) | PK/FK UUID/pregunta; texto/correcta/orden presentes | Homónima: adaptar datos y consumidores; destino de ruta no existe. |
| pista | Sin ORM | Todos: id_pista, id_decision, texto; PK/FK | Decisión int pendiente | Aditiva una vez disponibles padres; no inferir pista desde justificación. |
| rubrica | RubricaModel, parcial | id_rubrica int, id_caso int UNIQUE y nota_maxima | Actual UUID y UNIQUE(version_caso_id), nombre/version_regla | Una rúbrica por caso vs por versión; preservar ambas referencias antes de migrar. |
| criterio_rubrica | CriterioRubricaModel, parcial | id_criterio int, id_rubrica int, peso_porcentaje; nombre actual presente | UUID y peso numeric(5,2) no demostrado porcentaje | Homónima: equivalencia académica y cambio de adaptador previo. |
| nivel_criterio | NivelRubricaModel/nivel_rubrica, parcial | id_nivel int, id_criterio int, logro_porcentaje; UQ(nivel,criterio) y UQ(criterio,nombre) | UUID/puntaje/descriptor; nombre presente | Conservar descriptor y puntaje de origen; no convertirlos por inferencia. |
| asignacion_caso | Sin homónima; sesión/convocatoria/espacio aportan función parcial | Toda tabla: id_asignacion, id_grupo, id_caso, apertura, cierre, fecha_limite_ingreso, intentos_base, tiempo_maximo_min, codigo_acceso_hash, estado; PK y FK grupo/caso | Padres grupo/caso int; actual sesión/version/estudiante UUID | Bloqueada: código grupal no sustituye convocatoria individual ni espacio demuestra matrícula. |
| participacion | Dominio INTEGER, sin ORM | Todos: id_participacion, id_asignacion, id_grupo_estudiante, estado, fecha_registro; PK/FK y UQ(asignación,membresía) | Asignación int pendiente; miembro int nuevo; 8A trae convocatoria UUID | No crear por convocatoria del modelo de 40; contrato original por asignación/membresía. |
| permiso_intento_extra | PermisoIntentoExtraORM, metadata pendiente | Columnas declaradas; falta resolver FK participación y desplegar tabla | id_participacion es NULLTYPE local por FK no resuelta; profesor int resuelto | No integrar con U01; no duplicar clase/tabla ni meter placeholder participación. |
| intento | Dominio, sin ORM | Toda tabla: id_intento, id_participacion, id_consentimiento, id_permiso_extra, numero_intento, estado, inicio, fin; PK/FK y UQ(participación,número) | INTEGER; dominio guarda duración/fechas aware, ER sin duración y timestamps naive | Después de padres/tiempo/consentimiento. No añadir vence_en ni hacer nullable el consentimiento automáticamente. |
| paso_simulacion | Dominio de selección vigente, sin ORM | Toda tabla: id_paso, id_intento, id_decision, id_opcion, numero_paso, registrado_en, tiempo_segundos, reflexion_estudiante; PK, FK intento y FK compuesta opción/decisión; UQ(intento,número) | Dominio IDs int; contenido actual UUID | Requiere padres INTEGER; historial posible en misma tabla solo con contrato explícito. |
| resultado_intento | Servicio/Strategy, sin ORM productivo | Todos: id_resultado, id_intento UNIQUE, nota_final decimal(4,2), fecha_calculo, comentario_automatico | Intento int pendiente; precisión/regla y referencia histórica por definir | Aditiva después de intentos, pero sin escritura oficial hasta política suficiente. |
| resultado_criterio | Dominio, sin ORM | Todos: id_resultado_criterio, id_resultado, id_criterio, id_nivel, puntaje_obtenido; UQ(resultado,criterio) y FK compuesta nivel/criterio | Contenido/rúbrica int pendientes frente a UUID actuales | No nivel cero ni intento ficticio para ausencias; exige referencia de la misma rúbrica. |
| resultado_participacion | Contrato, sin ORM productivo | Todos: PK, participación UNIQUE, situación, nota_definitiva, fecha_calculo, observacion | Part int pendiente, nota decimal(4,2) NN | Aditiva después de participación; pendiente no es cero y consolidación no aprobada. |
| retroalimentacion_docente | RetroalimentacionDocenteORM, metadata pendiente | Columnas declaradas; FK asignación sin resolver; despliegue pendiente | id_asignacion NULLTYPE local; UQ asignación | No integrar con U01. ER por asignación no satisface feedback individual sin decisión posterior. |
| notificacion | NotificacionModel, parcial | id_notificacion int, id_usuario int, id_asignacion opcional, fecha_creacion/envio/lectura y FK oficiales | Actual PK/destinatario UUID, convocatoria, canal/estado, tipo(60) vs (40), creada_en TZ | Homónima: preservar mensajes/destinos; no truncar ni reemplazar in situ. |

Balance de la matriz: cuatro fieles, once parciales y trece sin tabla productiva; nueve nombres coinciden literalmente con las 19 integradas. Los dos modelos pendientes se incluyen en las parciales, no se cuentan como integrados.

## 4. Destino de los diez nombres adicionales de la implementación

Clasificación principal para planificar, no permiso de eliminación. **Las diez se conservan hoy.** EF = equivalencia funcional parcial; ST = soporte técnico existente durante transición; DA = decisión arquitectónica posterior.

| Tabla actual no literal | Clase | Relación con el ER y dependencia real | Qué hacer antes de cualquier retiro |
|---|---|---|---|
| escenario | EF | Parcial de escena, pero UUID y version_caso en vez de caso INTEGER; falta título/tipo | Adaptar consumidores y datos, verificar correspondencia; no simple RENAME |
| pregunta | EF | Parcial de decision; no tiene criterio obligatorio y usa UUID | Resolver granularidad, criterio, opciones y rutas antes de convertir |
| nivel_rubrica | EF | Parcial de nivel_criterio; puntaje/descriptor no son logro porcentual demostrado | Certificar escala y conservar descriptor/origen; no cast numérico por semejanza |
| identidad_academica | ST | Puente real por sistema entre cuenta INTEGER y UUID; lo usan JWT/titularidad/Cases/Scheduling/8A | Mantener PK(sistema,UUID), FK usuario y resolver exactamente uno; nunca reasignar ni retirar mientras haya consumidores |
| evento_auditoria | ST | Trazabilidad de sesión/State/Observer existente | Preservar eventos y diseñar destino de auditoría si se exige un físico final de 28; no borrar historia por conteo |
| version_caso | DA | Identidad de edición y rúbrica exacta; FK desde sesión, escena y rúbrica | Decidir representación dentro de 28, preservar cada edición y referencias; no aplanar todas en un caso |
| valoracion_opcion | DA | Matriz opción/criterio con puntaje; ER exige criterio por decisión | Validar semántica y regla académica, no sumar/reducir automáticamente |
| espacio_academico | DA | Espacio de Scheduling sin período/membresía/grupo | Acordar relación con grupo; no generar matrículas o períodos |
| sesion_programada | DA | Función parcial de asignacion_caso; estados, lugar/mensaje, máximo, versión | Acordar programación, campos no presentes y trazabilidad de UUID, sin dos autoridades divergentes |
| convocatoria | DA | Código/hash por estudiante, estado y UUID en JWT; no tabla equivalente directa | Resolver acceso individual dentro del objetivo y compatibilidad de tokens; no sustituir por hash grupal ni eliminar antes de migrar login |

Son 3 EF, 2 ST y 5 DA. «Soporte técnico» no significa prescindible. U01 no modifica estas tablas ni toma la decisión de si quedarán o no en un ambiente final.

## 5. Estrategia UUID/INTEGER y conservación de integridad

### Identidad personal: resolver, no convertir

Usuario.id_usuario INTEGER sigue siendo la autoridad. Para recursos actuales se conserva identidad_academica por sistema; no se presupone que Cases y Scheduling compartan UUID. Convertir la cadena decimal de Identity a su misma PK INTEGER validada no crea un UUID académico.

Un recurso con dueño UUID solo puede relacionarse con una cuenta por una asociación real y verificada. Cero/múltiples/corruptos siguen cerrados. Correo/nombre parecido, hash del entero, uuid5, ceros, UUID aleatorio o substring del UUID no son equivalencias. U01 usa directamente FK a usuario; no necesita generar ni cargar alias.

### Identidad de negocio: nueva PK con procedencia, no cast

Si se migra una versión/escena/opción UUID a una entidad oficial INTEGER, el destino obtiene una PK INTEGER nueva legítima y se registra su correspondencia real con objeto, versión y dependencias fuente. No se cambia el tipo de la PK actual en producción.

Para un traslado futuro se propone un manifiesto externo controlado: tipo de entidad, sistema/tabla fuente, UUID/PK fuente, versión/rúbrica, PK destino, evidencia, hash de contenido/relaciones y estado de revisión. No se crea una tabla de mapeo extra, ni se publican datos personales/secretos en Git o logs. El manifiesto es evidencia de importación, **no** un resolver productivo improvisado.

Si clientes/JWT necesitan seguir usando UUID, conservar fuente/adaptador mientras se acuerdan campos de procedencia dentro de las 28 u otra alternativa explícitamente aprobada. Un diccionario en memoria o un CSV como autoridad permanente de autorización no garantiza FK, transacciones ni compatibilidad.

### Orden del traslado, una vez aprobado

1. Verificar cuentas y dueños personales; no inventar matrícula.
2. Resolver caso/edición/rúbrica y mapeos de padres antes de escenas/decisiones/opciones.
3. Resolver grupo, matrícula y programación antes de participación; consentimiento real cuando aplique.
4. Trasladar hijos usando el mapeo del padre correcto; comprobar criterio/nivel y opción/decisión del mismo ámbito.
5. Comparar contenido, precisión, instantes y vínculos, no solo cantidad de filas.
6. Mantener fuentes y API antiguas hasta verificar todos los consumidores; no dual write sin contrato transaccional ni cortar UUID históricos por el hecho de crear nuevas tablas.

U01 no ejecuta ninguno de esos backfills: **las tres tablas se crean vacías y sin asociaciones históricas**.

## 6. Primera migración segura y cadena Alembic

Grafo leído por AST, sin invocar upgrade/downgrade:

```text
20261028_identity_access ───────────┐
                                  ├─20261028_merge_access_cases─┐
c27a750108db───────────────────────┘                            │
       └─36b9e0790539───────────────────────────────────────────┤
                                                               └─6867083574f6
                                                                    └─20261031_academic_identity
                                                                         └─U01 PROPUESTA
```

Hay seis revisiones locales, dos raíces, dos merges sin DDL y una cabeza: 20261031_academic_identity. Su archivo sigue sin seguimiento Git. No se asume aplicada ni se reescriben raíces/merges.

Nombre futuro propuesto: **backend/alembic/versions/20261101_er28_base_academica.py**, con revision propuesta 20261101_er28_base_academica y down_revision=20261031_academic_identity **si sigue siendo la cabeza reconciliada al implementar**. No se crea ni reserva esa revisión en BD2-00.

Antes de implementarla: revisar/versionar mediante el proceso del equipo toda la cadena local necesaria y comprobar que no cambió la cabeza. Si otra revisión aparece, reevaluar padre/diff; no crear un merge o cambiar ramas automáticamente. Antes de aplicarla: inspección autorizada de la base de destino en laboratorio/copia, sin stamp ni IF NOT EXISTS para encubrir drift.

Alembic env ya recibe config.attributes['connection']; las pruebas nuevas deben usar esa conexión aislada validada. No necesitan cambiar env.py, PostgreSQL global o .env. No ejecutar el CLI de upgrade contra la configuración implícita del proyecto.

La revisión futura se redacta/revisa como **lista cerrada de tres CREATE TABLE**, no como diff global que pudiera proponer DROP/ALTER de tablas divergentes. Al terminar, comparar metadata completa contra laboratorio: no aceptar cambios en las 19 anteriores.

## 7. Contrato exacto de U01

### Tablas, columnas y tipos oficiales

| Tabla | Columnas / nulabilidad / default |
|---|---|
| grupo_academico | id_grupo INTEGER PK autoincremental; id_profesor INTEGER NOT NULL; nombre VARCHAR(120) NOT NULL; periodo VARCHAR(30) NOT NULL |
| grupo_estudiante | id_grupo_estudiante INTEGER PK autoincremental; id_grupo INTEGER NOT NULL; id_estudiante INTEGER NOT NULL; fecha_ingreso TIMESTAMP WITHOUT TIME ZONE NOT NULL; activo BOOLEAN NOT NULL DEFAULT true |
| consentimiento | id_consentimiento INTEGER PK autoincremental; id_estudiante INTEGER NOT NULL; version_texto VARCHAR(30) NOT NULL; fecha_aceptacion TIMESTAMP WITHOUT TIME ZONE NOT NULL; fecha_revocacion TIMESTAMP WITHOUT TIME ZONE NULL |

Total: **14 columnas, 3 PK, 4 FK y 1 UNIQUE adicional**:
- grupo_academico.id_profesor → usuario.id_usuario.
- grupo_estudiante.id_grupo → grupo_academico.id_grupo.
- grupo_estudiante.id_estudiante → usuario.id_usuario.
- consentimiento.id_estudiante → usuario.id_usuario.
- UNIQUE(grupo_estudiante.id_grupo, grupo_estudiante.id_estudiante).

Nombres técnicos sugeridos para esas FK/UQ: fk_grupo_academico_profesor_usuario, fk_grupo_estudiante_grupo, fk_grupo_estudiante_estudiante_usuario, fk_consentimiento_estudiante_usuario y uq_grupo_estudiante_grupo_estudiante. Deben ser iguales en ORM/migración; no son relaciones nuevas. PK y secuencias pertenecen a sus propias tablas, nunca copian IDs de usuario.

### Restricciones del incremento

No agregar fecha_retiro, hash_texto, espacio_academico_id, episodio, política, UUID, campos de la propuesta de 40, nuevas CHECK académicas o índices no presentes por defecto. Mantener solo el UNIQUE original; no aprobar reingreso ni intervalos de matrícula. Conservar acciones FK por defecto del ER, sin cascadas de borrado introducidas.

DateTime(timezone=False) refleja el ER, sin defaults now()/aceptación automática ni normalización de datos legados. Las tablas vacías permiten separar esta definición de las futuras reglas de interpretación horaria. Ninguna fila de consentimiento nace al autenticar.

No crear relaciones ORM de negocio innecesarias. Las FK a usuario comprueban existencia, **no** rol DOCENTE/ESTUDIANTE, activo, consentimiento vigente ni autorización; esos controles siguen siendo responsabilidad de los servicios cuando se implementen. No añadirlos a JWT, routers o dependencias como parte de U01.

La ubicación de las tres clases en infraestructura de Identity es una propuesta de propiedad técnica por la referencia a usuario y los modelos académicos actuales; el equipo debe validarla. Organización, matrícula y consentimiento siguen siendo conceptos distintos del rol; no se amplía el agregado de autenticación ni se crean módulos nuevos.

### Evolución de inventario esperada, no ejecutada

Base.metadata pasaría de 19 a **22**, con 106 columnas, 22 PK, 22 FK, 10 UNIQUE, los mismos 6 CHECK y los mismos 17 índices explícitos no únicos. Los índices implícitos de PK/UQ son otra cuenta. Las dos clases de academic_metadata continúan pendientes y excluidas; no se esperan 24 tablas integradas.

Crear primero grupo_academico, luego grupo_estudiante; consentimiento puede ir después. No insertar datos, mover filas ni actualizar tablas anteriores. Verificar previamente que los tres nombres no estén ocupados físicamente.

## 8. Archivos específicos de la unidad futura

**Son cambios propuestos para después de aprobación; ninguno se crea/modifica ahora.**

| Archivo desde la raíz | Acción futura concreta |
|---|---|
| backend/app/modules/identity/infrastructure/academic_base_models.py | Nuevo: GrupoAcademicoORM, GrupoEstudianteORM y ConsentimientoORM con Base compartida, nombres y 14 columnas oficiales; sin repositorios ni relaciones innecesarias |
| backend/app/db/models.py | Importar exclusivamente ese archivo en registrar_modelos_integrados y seguir validando todas las FK. No importar academic_models como desplegable ni copiar tablas ficticias para resolverlo |
| backend/alembic/versions/20261101_er28_base_academica.py | Nueva revisión aditiva de tres tablas, sin datos/ALTER/DROP en upgrade, padre reconciliado y downgrade restringido según §10 |
| backend/tests/integration/test_er28_academic_base.py | Nuevo: contrato de modelos/DBML, DDL, integridad y preservación, con laboratorios propios |
| backend/tests/integration/test_schema_integration.py | Actualizar inventario exacto/ancestría e importación aislada para nuevas tablas; conservar controles contra placeholders y regresiones de las 19 |
| backend/tests/identity/test_academic_identity_repository.py | Separar prueba histórica de ciclo de identidad de la nueva cabeza y evitar downgrade destructivo sobre fixture compartida |

Se reutilizan **sin cambiar por defecto** backend/tests/identity/academic_identity_support.py (laboratorio TCP/aislamiento/config), backend/alembic/env.py y backend/tests/identity/persistence_support.py (lector del DBML). REVISION/ANTERIOR del soporte conservan significado histórico; no reemplazarlos globalmente por la revisión nueva.

No se modifican main.py, configuración, servicios Cases/Scheduling/Participation, puertos, API, autenticación, siete patrones ni los dos modelos académicos pendientes. No hacen falta dependencias nuevas.

## 9. Ajustes de pruebas existentes necesarios, sin esconder fallos

Se localizaron contratos de inventario que fallarían **legítimamente** al agregar las tres tablas:

- En test_schema_integration.py: INTEGRATED_TABLES, assert len(metadata.tables)==19, la cadena de código del subprocess con len(tablas)==19, comparación de tablas físicas y cabeza HEAD_IDENTIDADES.
- Mantener HEAD_IDENTIDADES=20261031_academic_identity como revisión histórica hija de 6867083574f6; agregar una cabeza actual propuesta y verificar que su padre sea la anterior. No cambiar la historia para que coincida una aserción.
- Definir conjunto exacto esperado = las 19 anteriores UNION las tres de U01 y contar 22; no sustituir igualdad por subconjunto, borrar la comprobación o excluir la nueva migración.
- Seguir exigiendo que participacion, asignacion_caso, permiso_intento_extra y retroalimentacion_docente no aparezcan como tablas integradas/ficticias.

La prueba **test_migracion_aditiva_ciclo_y_datos_previos** de test_academic_identity_repository.py actualmente usa una fixture de módulo migrada a head, reúne todas las tablas salvo identidad_academica, baja a ANTERIOR y vuelve a REVISION histórica. Con U01:
1. La nueva cabeza ya no sería REVISION.
2. El downgrade también retiraría las tres nuevas.
3. Volver a REVISION no las recrearía y la lectura de 'despues' intentaría consultarlas.
4. Si alguien las poblara, ese ciclo podría perder datos o ser rechazado por el guard de downgrade.

Solución propuesta: probar el ciclo histórico en **laboratorio independiente iniciado en su revisión histórica**, limitado a sus tablas; verificar la cabeza actual por separado y probar U01 en su propio laboratorio. No hacer round-trip de revisiones antiguas sobre el engine compartido con otras pruebas.

Las fixtures académicas derivadas del DBML en persistence_support.py se conservan como metadata de pruebas y revisión de acceso aislada; no registran esas tablas en Base ni se usan para crear un caso INTEGER paralelo en la base vigente. Las regresiones de login/resolver/8A que usan head deben funcionar con las tres tablas vacías, sin cambiar sus reglas.

Modificar esas expectativas en una iteración autorizada documenta un cambio real de esquema. No autoriza relajar JWT, permisos, propiedad, errores, rollback, ni marcar nuevos skip/xfail para evitar una regresión. Aquí solo se identifica el trabajo: no se edita ninguna prueba.

## 10. Plan de pruebas de U01 y rollback

Todos los siguientes son **criterios futuros, no pruebas ejecutadas**.

| ID / tipo | Escenario | Resultado exigido |
|---|---|---|
| U01-01 · estática/modelos | Comparar contra bloques originales de las tres tablas | 14 columnas, tipos/nullable/default exactos; 3 PK/4 FK/1 UQ, sin campos añadidos |
| U01-02 · metadata/subprocess | Registrar modelos en distintos órdenes | Conjunto exacto de 22, FK resolubles; los dos pendientes siguen separados, sin NULLTYPE en las tres nuevas |
| U01-03 · SQLite y PostgreSQL | Insertar grupo, membresía y consentimiento con cuentas reales de fixture | PK propias autogeneradas; lectura/round-trip y default activo true correctos; datos solo del laboratorio |
| U01-04 · SQLite FK activadas y PostgreSQL | Cada una de las cuatro FK con usuario/grupo inexistente | IntegrityError y rollback sin alterar las 19 tablas anteriores |
| U01-05 · SQLite y PostgreSQL | Duplicar grupo/estudiante; mismo alumno en otro grupo | Duplicado rechazado, otro grupo permitido; no se deduce política de reingreso |
| U01-06 · ambos motores | NOT NULL/longitudes y fecha_revocacion opcional | Nulabilidad/PK/default se cumplen; límites VARCHAR se verifican realmente en PostgreSQL, no se atribuyen a SQLite si no los impone |
| U01-07 · PostgreSQL | Tipos temporales y valores explícitos | TIMESTAMP WITHOUT TIME ZONE; valor guardado sin convertir fuente ni inventar aceptación. No prueba de política de zona/applicabilidad |
| U01-08 · PostgreSQL aislado | Upgrade desde padre con filas en las 19 tablas | Solo aparecen las tres vacías; todas las filas/PK/FK/valores anteriores se mantienen; alembic_version avanza correctamente |
| U01-09 · PostgreSQL aislado | Inyectar error en creación de la tercera tabla | Transacción DDL revierte, no queda esquema parcial ni cabeza adelantada; las 19 permanecen |
| U01-10 · PostgreSQL, laboratorio exclusivo | Downgrade con las tres vacías | Retira solo sus tres tablas y objetos propios, en orden inverso; vuelve a cabeza anterior, conserva datos originales |
| U01-11 · PostgreSQL, laboratorio exclusivo | Intentar downgrade con una tabla nueva poblada | Rechazo antes de cualquier DROP, rollback sin pérdida de datos ni avance de versión |
| U01-12 · PostgreSQL, dos conexiones | Inserción concurrente de misma membresía | Una sola membresía confirmada, rechazo del duplicado y otra transacción utilizable tras rollback |
| U01-13 · migraciones/metadata | Upgrade desde cero y desde cabeza, comparación reflectada y ancestría | Una cabeza; diff ORM/DDL vacío; no reescritura de padres/merges ni diferencias en las 19 |
| U01-14 · regresión HTTP/SQL | Login, JWT, roles, resolver, Cases, Scheduling, 8A y Participation existente | Sin nuevas rutas ni aperturas de ingreso/evaluación; resultados anteriores conservados y errores sin filtración |

SQLite necesita PRAGMA foreign_keys=ON; no certifica locks, DDL transaccional, longitudes de VARCHAR ni semántica temporal PostgreSQL. APP/fakes pueden comprobar clasificación de errores, pero no prueban FK ni migración real. Los FK no deben probarse como rechazo de rol: por sí solos aceptan una cuenta existente aunque su rol no sea el esperado; no hay nuevo servicio de autorización en esta unidad.

### Laboratorio futuro

Usar el mecanismo de motor_postgresql_desechable de academic_identity_support.py: contenedor **nuevo** propio, labels/ID y puerto TCP verificados, tmpfs y sin volúmenes persistentes, sin URL compartida/.env. No basta pg_isready: esperar conexión SQLAlchemy y SELECT current_database() de la base esperada. Reutilizar diagnósticos redactados y finally que elimina exclusivamente ese contenedor.

El helper antiguo base_aislada de test_persistence.py permite SPS_IDENTITY_TEST_URL y schemas; **no es el laboratorio recomendado para estas nuevas pruebas**. No rellenar esa variable con la BD del equipo ni tomar una URL existente como autorización. Grupos que requieran otra configuración aislada se reportan aparte si no se habilitan; no se convierten sus omitidos en aprobados.

La prueba de migración usa una conexión validada en config.attributes, nunca get_engine implícito de la aplicación. Toda semilla de usuario/rol/caso es sintética del laboratorio, no backfill ni creación académica del sistema.

### Rollback seguro previsto

La revisión nueva no debe proponer borrado de datos como reversión ordinaria. El downgrade solo se ensaya en laboratorio exclusivo/quiescente:
- Bloquear las tres tablas dentro de una transacción PostgreSQL, comprobar **todas** vacías antes de retirar cualquiera y respetar dependencias.
- Si hay filas o referencias externas, abortar sin borrar ni usar CASCADE. Las comprobaciones sin bloqueo no bastan: podría entrar una fila entre comprobar y borrar.
- Si cumple, retirar consentimiento y grupo_estudiante antes de grupo_academico, con sus objetos propios; no tocar usuario ni identidad_academica.
- En ambiente con datos oficiales, detener despliegue/revertir código compatible y conservar tablas; preferir corrección aditiva. No recomendar downgrade base ni limpiar datos para conseguirlo.

Los efectos de locks, fallo DDL y guardas se verificarán en PostgreSQL; no se promete la misma atomicidad para SQLite. No se ejecuta ningún rollback en BD2-00.

## 11. Qué migraciones son aditivas y cuáles no están listas

| Grupo | Situación | Acción permitida tras aprobación |
|---|---|---|
| Cuatro tablas de acceso | Ya coinciden con ER | Reusar sin DDL; verificar esquema aplicado, no recrear |
| Las tres de U01 | Nombres libres en metadata y padres INTEGER disponibles | Aditivas vacías, sin backfill ni integración funcional; requieren preflight físico/laboratorio |
| Objetivos/personajes/relación/pistas | Nombres libres, pero padres INTEGER aún incompatibles/ausentes | Esperar adaptación de Cases; no cambiar FK a UUID por comodidad |
| Asignación/participación/intento/pasos/resultados | Faltan dependencias y contratos temporales/académicos | Reconciliar primero; después podrían ser CREATE aditivos, sin habilitar política inventada |
| Caso/opción/rúbrica/criterio/notificación | Homónimas con PK/FK/atributos incompatibles | Adaptación de código/datos y estrategia de namespace/corte antes de DDL; no ALTER cast ni reemplazo automático |
| Escenario/pregunta/nivel_rubrica | Equivalencia parcial, no renombre seguro | Adaptar relaciones y consumidores, verificar datos; no RENAME solo |
| Permiso extra/feedback pendientes | Clases con dependencias no resueltas | No integrar aún ni duplicar; resolver padres y granularidad del feedback |
| Diez tablas fuera del listado literal | Sus consumidores están activos | Conservar; ninguna revisión inicial las borra ni las declara parte del ER oficial |

## 12. Datos históricos que deben conservarse y verificarse

El inventario real debe hacerse **más adelante y con autorización** en copia/laboratorio. Para cada fuente: conteo, PK, relaciones, contenido, timestamps/precisión y referencias externas; emitir reporte de faltantes/ambiguos y mantener fuente íntegra.

| Fuente | Qué preservar | Cómo verificar correspondencia real, sin suponerla |
|---|---|---|
| usuario/rol/permiso | PK INTEGER, correo/hash/activo y permisos | Misma cuenta, no usuario nuevo; no exponer hashes/secretos en informe; FK y permisos actuales |
| identidad_academica | Dueño, sistema, UUID y ambigüedades | Asociación administrativa con evidencia; no unir por nombre/email ni cambiar propietarios |
| Caso y versiones | UUID estables, número/contenido/estado, todas las ediciones usadas | Cada sesión conserva la versión/rúbrica exactas; dos ediciones distintas no se fusionan |
| Contenido y rúbrica | Escenarios, preguntas, opciones/corrección/justificación, criterios/niveles/descriptores/valoraciones | Hashes y FK del grafo; certificar significado de puntajes/porcentajes, sin pérdida de precisión |
| Sesión/convocatoria | Espacio, responsable, horario, máximo, lugar/mensaje, UUID, hash/estado y JWT contextual | Padrón/cuenta autorizados y correspondencia caso/versión; UUID de estudiante no acredita matrícula |
| Notificación/auditoría | Destinatario, mensaje/canal/estado, eventos/fechas y vínculos | Dueño comprobado y origen preservado; desconocido no equivale a enviado/leído; no truncar tipo |
| Eventual legado de participación | Membresía/consentimiento/permisos, intentos/pasos/resultados y feedback | Inspección física previa: no se presume existente. Fuente de cada nota/duración y destinatario demostrados |

Si el backend no guarda un atributo obligatorio del ER, el manifiesto lo marca como no migrable hasta resolución; no usar cadena vacía, nivel cero, consentimiento ficticio, fecha actual o grupo genérico. No recalcular calificaciones históricas ni cambiar zona de un timestamp sin origen verificable.

Para U01 no se necesita este traslado. Verificar solamente que los datos anteriores quedan iguales y que las nuevas tablas siguen vacías. El proceso de poblarlas será otra unidad de trabajo autorizada.

## 13. Decisiones técnicas frente a aprobaciones académicas

| Decisión | Tipo / responsable | ¿Bloquea U01 vacío? |
|---|---|---|
| Mantener nombres/tipos/PK/FK/defaults de las tres tablas oficiales, Base compartida, no placeholders | Técnica, respaldada por ER; equipo revisa implementación | Sí debe cumplirse, no requiere inventar política |
| Ubicación de clases, nombres de constraints, registro y actualización estricta de pruebas | Técnica/equipo | Aprobar alcance técnico antes de codificar |
| Padre Alembic, cadena local completa, permisos y laboratorio autorizado | Técnica/operativa | Sí; no se ejecuta con cabeza desconocida o configuración del proyecto |
| Coexistencia temporal 19→22 y definición de conteo final | Usuario/equipo, R01 | Sí para aplicar en un ambiente; laboratorio aislado solo con autorización específica |
| Grupo/espacio, padrón, reingreso, convocatoria individual y fechas | Académica/negocio con equipo, R03/R07/R08 | No para tablas vacías; sí para poblarlas/abrir servicios |
| Consentimiento universal/no aplica, texto/vigencia/revocación | Académica/privacidad, R05 | No para tabla vacía; sí para aceptar evidencia y autorizar inicio |
| Versiones, porcentajes, fórmula/parcial/ausencia/consolidación | Académica con Cases/Evaluation, R02/R06 | No; no se toca calificación |
| Feedback individual y trazabilidad de entrega/auditoría | Académica y equipo, R04/R09 | No; no se implementan ni cambian notificaciones |
| RF-22 base/umbral/fronteras | Responsable académico, R07 | No para U01; **sí bloquea ingreso real**, sin tolerancia del cliente |

No hace falta resolver todas las preguntas académicas para preparar tres tablas vacías. Tampoco se consideran resueltas por haber aprobado el ER. Las restricciones actuales de seguridad/ingreso y calificación siguen cerradas donde corresponde.

### Aprobación mínima solicitada para una iteración posterior

1. Aceptar U01 acotada a esas tres tablas vacías, registro, revisión y pruebas, sin endpoints, datos ni vinculación de 8A.
2. Confirmar ubicación técnica y actualización de pruebas por el cambio real de inventario/cabeza; conservar la prueba histórica de identidad en laboratorio separado.
3. Aceptar que 22 integradas es estado transitorio con las diez adicionales existentes conservadas, no cumplimiento final de 28.
4. Revisar la cadena local/untracked y autorizar expresamente un laboratorio nuevo; **no autorizar por defecto la BD del proyecto ni migración de datos**.
5. Mantener los R académicos pendientes para sus operaciones dependientes.

Este listado no solicita ni supone permiso para ejecutar ahora. La aprobación de BD2-00 o su lectura no inicia la implementación automáticamente.

## 14. Qué choca con un esquema físico final de exactamente 28 tablas

- Agregar todas las entidades que faltan sin reconciliar las existentes no conduce a 28: hoy 19 comparten solo 9 nombres con el ER. Añadir los otros 19 nombres y conservar las actuales produciría **38 tablas de dominio**, además del control de migraciones, y las homónimas seguirían incompatibles.
- Un segundo schema con 28 copias más el backend antiguo preservaría fuentes durante un ensayo, pero **no sería un físico final de 28** ni autoriza duplicar usuarios. Solo puede ser transición/copia expresamente aprobada.
- Conservar definitivamente version_caso, convocatoria, identidad_academica u otra fuera de las 28 como tabla adicional sería incompatible con el conteo final estricto. Retirarlas sin adaptar sus consumidores, en cambio, rompe el backend. Esta decisión no se evade contando una vista como implementación ni moviendo tablas a otro schema para ocultarlas.
- Aprobar episodios, outbox, política o historial como tablas nuevas reabriría el ER: no forma parte de U01 ni se adopta del modelo de 40.
- Reducir a 28 borrando historia, fusionando versiones, anulando código individual, inventando correspondencias o quitando JWT es inaceptable y no está propuesto.
- El catálogo físico actual incluye además alembic_version cuando se aplican revisiones. El equipo debe explicitar si «28 físicas» significa **28 tablas académicas** excluyendo control de migraciones; si incluye literalmente toda tabla de usuario, 28 académicas + alembic_version son 29. No se mueve/borra esa tabla para falsear la cuenta.
- Añadir campos puntuales dentro de las 28 no cambia el número, pero sí puede cambiar el ER aprobado: cualquier ajuste de atributos/FK requiere aprobación antes de implementarlo, no se introduce aquí.

Por tanto U01 es un incremento compatible hacia el objetivo, no un certificado de factibilidad del corte final sin cambios de código. Si se exige que cada estado intermedio sea ya el esquema físico exacto de 28, esta unidad no se aplica en el ambiente existente: se limita a laboratorio mientras se decide el corte completo.

## 15. Criterios de aceptación de la primera unidad

Se podrá declarar terminada U01 únicamente cuando, en una iteración autorizada:
- Los tres modelos y la revisión existan y coincidan exactamente con sus bloques del ER; ninguna entidad/columna adicional.
- El inventario exacto sea las 19 anteriores + las tres nuevas; las dos pendientes permanezcan fuera. Ningún drop/alter de origen ni usuario/asociación sembrados.
- La cabeza única nueva tenga el padre revisado; las revisiones anteriores/merges sigan intactas.
- Upgrade y downgrade controlados, fallo DDL, FK/UQ y preservación se hayan comprobado en PostgreSQL efímero; resultados concretos diferenciados de SQLite/HTTP/fakes.
- Se hayan ejecutado regresiones específicas y luego la suite completa. El número de pruebas puede crecer; ningún caso previo se pierde por relajar controles o esconder fallos.
- Login, Cases, Scheduling, JWT/resolver y 8A mantengan sus contratos; no se habilite Participation ni política temporal/calificación por crear tablas.
- Haya reporte de archivos/diff, datos preservados, riesgos y omisiones. Un PostgreSQL omitido no se declara aprobado.

## 16. Evidencia y límites de BD2-00

En esta preparación solo se crea este documento. Se revisaron fuentes/modelos/metadata, dependencias, pruebas y AST Alembic; no se ejecutaron sus funciones de migración. No se ejecutan pytest, Docker ni conexiones, no se leen/modifican .env ni datos, no se instalan dependencias y no se cambian los ocho documentos previos de BD-1.2.

La línea base de **1061 aprobadas y 38 omitidas**, y las 199 específicas de 8A, permanece como resultado histórico del usuario. No se atribuye ejecución nueva ni se certifica que una migración aún no creada haya pasado pruebas.

Controles efectivos de BD2-00: matriz de 28 tablas completa, diez adicionales clasificadas y catorce escenarios futuros; conteo corregido de 144 columnas reales del ER y 14 de U01. Enlaces locales y whitespace correctos, git diff --check con salida 0, ER original/objetivo intactos. Los **247 archivos preexistentes** inventariados permanecen idénticos por SHA-256; el único archivo añadido es este documento, sin eliminaciones. No se genera nuevo DBML ni esquema físico. **BD-2 no comienza con esta entrega.**
