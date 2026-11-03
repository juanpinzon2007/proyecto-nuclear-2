# B — Inventario exacto y modelo objetivo oficial de 28 tablas

**BD-1.2.** Fuente: [sps.dbml original](../../app/modules/identity/reference/sps.dbml). El [objetivo nuevo](ER_OBJETIVO_APROBADO_28_TABLAS.dbml) es una reproducción de sus definiciones, sin modificar atributos, nombres, tipos, defaults o relaciones.

Conteo verificado: **28 tablas, 156 columnas, 28 PK y 40 restricciones FK** (38 inline y 2 compuestas). Hay 19 UNIQUE adicionales a las PK. El archivo original no declara CHECK, acciones explícitas ON DELETE/UPDATE ni índices de rendimiento no únicos. Una PK implica NOT NULL aunque el DBML no lo repita. «NULL» a continuación expresa ausencia de NOT NULL en la fuente, no un cambio propuesto.

No se eliminan las tablas actuales de la implementación. Las definiciones aprobadas no son una certificación de que las 28 estén implementadas o aplicadas. La propuesta histórica de 40 no es fuente de este inventario.

## 1. Las 28 tablas, todos sus atributos y claves

### 1. rol

Atributos (3): `id_rol int NOT NULL PK`; `nombre varchar(40) NOT NULL`; `descripcion text NULL`.

PK: `id_rol`. UNIQUE adicionales: `(nombre)`.
FK salientes: ninguna.

### 2. permiso

Atributos (3): `id_permiso int NOT NULL PK`; `codigo varchar(80) NOT NULL`; `descripcion text NOT NULL`.

PK: `id_permiso`. UNIQUE adicionales: `(codigo)`.
FK salientes: ninguna.

### 3. rol_permiso

Atributos (3): `id_rol int NOT NULL`; `id_permiso int NOT NULL`; `indexes { NULL`.

PK: `id_rol, id_permiso`. UNIQUE adicionales: ninguna.
FK salientes: FK01 `rol_permiso.id_rol → rol.id_rol`; FK02 `rol_permiso.id_permiso → permiso.id_permiso`.

### 4. usuario

Atributos (6): `id_usuario int NOT NULL PK`; `id_rol int NOT NULL`; `nombre varchar(120) NOT NULL`; `correo varchar(200) NOT NULL`; `clave_hash varchar(255) NOT NULL`; `activo boolean NOT NULL DEFAULT true`.

PK: `id_usuario`. UNIQUE adicionales: `(correo)`.
FK salientes: FK03 `usuario.id_rol → rol.id_rol`.

### 5. grupo_academico

Atributos (4): `id_grupo int NOT NULL PK`; `id_profesor int NOT NULL`; `nombre varchar(120) NOT NULL`; `periodo varchar(30) NOT NULL`.

PK: `id_grupo`. UNIQUE adicionales: ninguna.
FK salientes: FK04 `grupo_academico.id_profesor → usuario.id_usuario`.

### 6. grupo_estudiante

Atributos (6): `id_grupo_estudiante int NOT NULL PK`; `id_grupo int NOT NULL`; `id_estudiante int NOT NULL`; `fecha_ingreso timestamp NOT NULL`; `activo boolean NOT NULL DEFAULT true`; `indexes { NULL`.

PK: `id_grupo_estudiante`. UNIQUE adicionales: `(id_grupo, id_estudiante)`.
FK salientes: FK05 `grupo_estudiante.id_grupo → grupo_academico.id_grupo`; FK06 `grupo_estudiante.id_estudiante → usuario.id_usuario`.

### 7. consentimiento

Atributos (5): `id_consentimiento int NOT NULL PK`; `id_estudiante int NOT NULL`; `version_texto varchar(30) NOT NULL`; `fecha_aceptacion timestamp NOT NULL`; `fecha_revocacion timestamp NULL`.

PK: `id_consentimiento`. UNIQUE adicionales: ninguna.
FK salientes: FK07 `consentimiento.id_estudiante → usuario.id_usuario`.

### 8. caso

Atributos (7): `id_caso int NOT NULL PK`; `id_profesor int NOT NULL`; `titulo varchar(160) NOT NULL`; `introduccion_teorica text NOT NULL`; `estado varchar(20) NOT NULL DEFAULT 'borrador'`; `fecha_creacion timestamp NOT NULL`; `fecha_validacion timestamp NULL`.

PK: `id_caso`. UNIQUE adicionales: ninguna.
FK salientes: FK08 `caso.id_profesor → usuario.id_usuario`.

### 9. objetivo_aprendizaje

Atributos (5): `id_objetivo int NOT NULL PK`; `id_caso int NOT NULL`; `descripcion text NOT NULL`; `orden int NOT NULL`; `indexes { NULL`.

PK: `id_objetivo`. UNIQUE adicionales: `(id_caso, orden)`.
FK salientes: FK09 `objetivo_aprendizaje.id_caso → caso.id_caso`.

### 10. escena

Atributos (7): `id_escena int NOT NULL PK`; `id_caso int NOT NULL`; `titulo varchar(160) NOT NULL`; `contexto text NOT NULL`; `orden int NOT NULL`; `tipo varchar(30) NOT NULL`; `indexes { NULL`.

PK: `id_escena`. UNIQUE adicionales: `(id_caso, orden)`.
FK salientes: FK10 `escena.id_caso → caso.id_caso`.

### 11. personaje

Atributos (4): `id_personaje int NOT NULL PK`; `id_caso int NOT NULL`; `nombre varchar(100) NOT NULL`; `descripcion text NULL`.

PK: `id_personaje`. UNIQUE adicionales: ninguna.
FK salientes: FK11 `personaje.id_caso → caso.id_caso`.

### 12. personaje_escena

Atributos (3): `id_personaje int NOT NULL`; `id_escena int NOT NULL`; `indexes { NULL`.

PK: `id_personaje, id_escena`. UNIQUE adicionales: ninguna.
FK salientes: FK12 `personaje_escena.id_personaje → personaje.id_personaje`; FK13 `personaje_escena.id_escena → escena.id_escena`.

### 13. decision

Atributos (6): `id_decision int NOT NULL PK`; `id_escena int NOT NULL`; `id_criterio int NOT NULL`; `enunciado text NOT NULL`; `orden int NOT NULL`; `indexes { NULL`.

PK: `id_decision`. UNIQUE adicionales: `(id_escena, orden)`.
FK salientes: FK14 `decision.id_escena → escena.id_escena`; FK15 `decision.id_criterio → criterio_rubrica.id_criterio`.

### 14. opcion_respuesta

Atributos (8): `id_opcion int NOT NULL PK`; `id_decision int NOT NULL`; `id_escena_destino int NULL`; `texto text NOT NULL`; `es_correcta boolean NOT NULL`; `justificacion_teorica text NOT NULL`; `orden int NOT NULL`; `indexes { NULL`.

PK: `id_opcion`. UNIQUE adicionales: `(id_decision, orden)`; `(id_opcion, id_decision)`.
FK salientes: FK16 `opcion_respuesta.id_decision → decision.id_decision`; FK17 `opcion_respuesta.id_escena_destino → escena.id_escena`.

### 15. pista

Atributos (3): `id_pista int NOT NULL PK`; `id_decision int NOT NULL`; `texto text NOT NULL`.

PK: `id_pista`. UNIQUE adicionales: ninguna.
FK salientes: FK18 `pista.id_decision → decision.id_decision`.

### 16. rubrica

Atributos (4): `id_rubrica int NOT NULL PK`; `id_caso int NOT NULL`; `nombre varchar(120) NOT NULL`; `nota_maxima decimal(4,2) NOT NULL`.

PK: `id_rubrica`. UNIQUE adicionales: `(id_caso)`.
FK salientes: FK19 `rubrica.id_caso → caso.id_caso`.

### 17. criterio_rubrica

Atributos (4): `id_criterio int NOT NULL PK`; `id_rubrica int NOT NULL`; `nombre varchar(120) NOT NULL`; `peso_porcentaje decimal(5,2) NOT NULL`.

PK: `id_criterio`. UNIQUE adicionales: ninguna.
FK salientes: FK20 `criterio_rubrica.id_rubrica → rubrica.id_rubrica`.

### 18. nivel_criterio

Atributos (5): `id_nivel int NOT NULL PK`; `id_criterio int NOT NULL`; `nombre varchar(80) NOT NULL`; `logro_porcentaje decimal(5,2) NOT NULL`; `indexes { NULL`.

PK: `id_nivel`. UNIQUE adicionales: `(id_nivel, id_criterio)`; `(id_criterio, nombre)`.
FK salientes: FK21 `nivel_criterio.id_criterio → criterio_rubrica.id_criterio`.

### 19. asignacion_caso

Atributos (10): `id_asignacion int NOT NULL PK`; `id_grupo int NOT NULL`; `id_caso int NOT NULL`; `apertura timestamp NOT NULL`; `cierre timestamp NOT NULL`; `fecha_limite_ingreso timestamp NOT NULL`; `intentos_base int NOT NULL DEFAULT 1`; `tiempo_maximo_min int NOT NULL`; `codigo_acceso_hash varchar(255) NOT NULL`; `estado varchar(20) NOT NULL DEFAULT 'programada'`.

PK: `id_asignacion`. UNIQUE adicionales: ninguna.
FK salientes: FK22 `asignacion_caso.id_grupo → grupo_academico.id_grupo`; FK23 `asignacion_caso.id_caso → caso.id_caso`.

### 20. participacion

Atributos (6): `id_participacion int NOT NULL PK`; `id_asignacion int NOT NULL`; `id_grupo_estudiante int NOT NULL`; `estado varchar(20) NOT NULL DEFAULT 'pendiente'`; `fecha_registro timestamp NOT NULL`; `indexes { NULL`.

PK: `id_participacion`. UNIQUE adicionales: `(id_asignacion, id_grupo_estudiante)`.
FK salientes: FK24 `participacion.id_asignacion → asignacion_caso.id_asignacion`; FK25 `participacion.id_grupo_estudiante → grupo_estudiante.id_grupo_estudiante`.

### 21. permiso_intento_extra

Atributos (6): `id_permiso_extra int NOT NULL PK`; `id_participacion int NOT NULL`; `id_profesor int NOT NULL`; `cantidad_autorizada int NOT NULL DEFAULT 1`; `justificacion text NOT NULL`; `fecha_autorizacion timestamp NOT NULL`.

PK: `id_permiso_extra`. UNIQUE adicionales: ninguna.
FK salientes: FK26 `permiso_intento_extra.id_participacion → participacion.id_participacion`; FK27 `permiso_intento_extra.id_profesor → usuario.id_usuario`.

### 22. intento

Atributos (9): `id_intento int NOT NULL PK`; `id_participacion int NOT NULL`; `id_consentimiento int NOT NULL`; `id_permiso_extra int NULL`; `numero_intento int NOT NULL`; `estado varchar(20) NOT NULL`; `inicio timestamp NOT NULL`; `fin timestamp NULL`; `indexes { NULL`.

PK: `id_intento`. UNIQUE adicionales: `(id_participacion, numero_intento)`.
FK salientes: FK28 `intento.id_participacion → participacion.id_participacion`; FK29 `intento.id_consentimiento → consentimiento.id_consentimiento`; FK30 `intento.id_permiso_extra → permiso_intento_extra.id_permiso_extra`.

### 23. paso_simulacion

Atributos (9): `id_paso int NOT NULL PK`; `id_intento int NOT NULL`; `id_decision int NOT NULL`; `id_opcion int NOT NULL`; `numero_paso int NOT NULL`; `registrado_en timestamp NOT NULL`; `tiempo_segundos int NOT NULL`; `reflexion_estudiante text NULL`; `indexes { NULL`.

PK: `id_paso`. UNIQUE adicionales: `(id_intento, numero_paso)`.
FK salientes: FK31 `paso_simulacion.id_intento → intento.id_intento`; FK39 `paso_simulacion.(id_opcion, id_decision) → opcion_respuesta.(id_opcion, id_decision)`.

### 24. resultado_intento

Atributos (5): `id_resultado int NOT NULL PK`; `id_intento int NOT NULL`; `nota_final decimal(4,2) NOT NULL`; `fecha_calculo timestamp NOT NULL`; `comentario_automatico text NULL`.

PK: `id_resultado`. UNIQUE adicionales: `(id_intento)`.
FK salientes: FK32 `resultado_intento.id_intento → intento.id_intento`.

### 25. resultado_criterio

Atributos (6): `id_resultado_criterio int NOT NULL PK`; `id_resultado int NOT NULL`; `id_criterio int NOT NULL`; `id_nivel int NOT NULL`; `puntaje_obtenido decimal(5,2) NOT NULL`; `indexes { NULL`.

PK: `id_resultado_criterio`. UNIQUE adicionales: `(id_resultado, id_criterio)`.
FK salientes: FK33 `resultado_criterio.id_resultado → resultado_intento.id_resultado`; FK40 `resultado_criterio.(id_nivel, id_criterio) → nivel_criterio.(id_nivel, id_criterio)`.

### 26. resultado_participacion

Atributos (6): `id_resultado_participacion int NOT NULL PK`; `id_participacion int NOT NULL`; `situacion varchar(20) NOT NULL`; `nota_definitiva decimal(4,2) NOT NULL`; `fecha_calculo timestamp NOT NULL`; `observacion text NULL`.

PK: `id_resultado_participacion`. UNIQUE adicionales: `(id_participacion)`.
FK salientes: FK34 `resultado_participacion.id_participacion → participacion.id_participacion`.

### 27. retroalimentacion_docente

Atributos (5): `id_retroalimentacion int NOT NULL PK`; `id_asignacion int NOT NULL`; `id_profesor int NOT NULL`; `texto text NOT NULL`; `fecha_registro timestamp NOT NULL`.

PK: `id_retroalimentacion`. UNIQUE adicionales: `(id_asignacion)`.
FK salientes: FK35 `retroalimentacion_docente.id_asignacion → asignacion_caso.id_asignacion`; FK36 `retroalimentacion_docente.id_profesor → usuario.id_usuario`.

### 28. notificacion

Atributos (8): `id_notificacion int NOT NULL PK`; `id_usuario int NOT NULL`; `id_asignacion int NULL`; `tipo varchar(40) NOT NULL`; `mensaje text NOT NULL`; `fecha_creacion timestamp NOT NULL`; `fecha_envio timestamp NULL`; `fecha_lectura timestamp NULL`.

PK: `id_notificacion`. UNIQUE adicionales: ninguna.
FK salientes: FK37 `notificacion.id_usuario → usuario.id_usuario`; FK38 `notificacion.id_asignacion → asignacion_caso.id_asignacion`.

## 2. Las 40 relaciones y sus cardinalidades reales

«Padres por fila hija» cuenta la referencia de una fila; «hijas por padre» muestra lo permitido por FK/UNIQUE. Ninguna FK exige que un padre tenga hijos. Las relaciones opcionales no se convierten en obligatorias por la interpretación de la aplicación.

| Relación | Columnas hijas | Clave padre | Padres por fila hija | Hijas por padre |
|---|---|---|---|---|
| FK01 | `rol_permiso.id_rol` | `rol.id_rol` | 1 | 0..N |
| FK02 | `rol_permiso.id_permiso` | `permiso.id_permiso` | 1 | 0..N |
| FK03 | `usuario.id_rol` | `rol.id_rol` | 1 | 0..N |
| FK04 | `grupo_academico.id_profesor` | `usuario.id_usuario` | 1 | 0..N |
| FK05 | `grupo_estudiante.id_grupo` | `grupo_academico.id_grupo` | 1 | 0..N |
| FK06 | `grupo_estudiante.id_estudiante` | `usuario.id_usuario` | 1 | 0..N |
| FK07 | `consentimiento.id_estudiante` | `usuario.id_usuario` | 1 | 0..N |
| FK08 | `caso.id_profesor` | `usuario.id_usuario` | 1 | 0..N |
| FK09 | `objetivo_aprendizaje.id_caso` | `caso.id_caso` | 1 | 0..N |
| FK10 | `escena.id_caso` | `caso.id_caso` | 1 | 0..N |
| FK11 | `personaje.id_caso` | `caso.id_caso` | 1 | 0..N |
| FK12 | `personaje_escena.id_personaje` | `personaje.id_personaje` | 1 | 0..N |
| FK13 | `personaje_escena.id_escena` | `escena.id_escena` | 1 | 0..N |
| FK14 | `decision.id_escena` | `escena.id_escena` | 1 | 0..N |
| FK15 | `decision.id_criterio` | `criterio_rubrica.id_criterio` | 1 | 0..N |
| FK16 | `opcion_respuesta.id_decision` | `decision.id_decision` | 1 | 0..N |
| FK17 | `opcion_respuesta.id_escena_destino` | `escena.id_escena` | 0..1 | 0..N |
| FK18 | `pista.id_decision` | `decision.id_decision` | 1 | 0..N |
| FK19 | `rubrica.id_caso` | `caso.id_caso` | 1 | 0..1 |
| FK20 | `criterio_rubrica.id_rubrica` | `rubrica.id_rubrica` | 1 | 0..N |
| FK21 | `nivel_criterio.id_criterio` | `criterio_rubrica.id_criterio` | 1 | 0..N |
| FK22 | `asignacion_caso.id_grupo` | `grupo_academico.id_grupo` | 1 | 0..N |
| FK23 | `asignacion_caso.id_caso` | `caso.id_caso` | 1 | 0..N |
| FK24 | `participacion.id_asignacion` | `asignacion_caso.id_asignacion` | 1 | 0..N |
| FK25 | `participacion.id_grupo_estudiante` | `grupo_estudiante.id_grupo_estudiante` | 1 | 0..N |
| FK26 | `permiso_intento_extra.id_participacion` | `participacion.id_participacion` | 1 | 0..N |
| FK27 | `permiso_intento_extra.id_profesor` | `usuario.id_usuario` | 1 | 0..N |
| FK28 | `intento.id_participacion` | `participacion.id_participacion` | 1 | 0..N |
| FK29 | `intento.id_consentimiento` | `consentimiento.id_consentimiento` | 1 | 0..N |
| FK30 | `intento.id_permiso_extra` | `permiso_intento_extra.id_permiso_extra` | 0..1 | 0..N |
| FK31 | `paso_simulacion.id_intento` | `intento.id_intento` | 1 | 0..N |
| FK32 | `resultado_intento.id_intento` | `intento.id_intento` | 1 | 0..1 |
| FK33 | `resultado_criterio.id_resultado` | `resultado_intento.id_resultado` | 1 | 0..N |
| FK34 | `resultado_participacion.id_participacion` | `participacion.id_participacion` | 1 | 0..1 |
| FK35 | `retroalimentacion_docente.id_asignacion` | `asignacion_caso.id_asignacion` | 1 | 0..1 |
| FK36 | `retroalimentacion_docente.id_profesor` | `usuario.id_usuario` | 1 | 0..N |
| FK37 | `notificacion.id_usuario` | `usuario.id_usuario` | 1 | 0..N |
| FK38 | `notificacion.id_asignacion` | `asignacion_caso.id_asignacion` | 0..1 | 0..N |
| FK39 | `paso_simulacion.(id_opcion, id_decision)` | `opcion_respuesta.(id_opcion, id_decision)` | 1 | 0..N |
| FK40 | `resultado_criterio.(id_nivel, id_criterio)` | `nivel_criterio.(id_nivel, id_criterio)` | 1 | 0..N |

Las FK compuestas garantizan opción/decisión y nivel/criterio, respectivamente. No existe FK independiente de paso.id_decision ni de resultado_criterio.id_criterio: sus valores se verifican mediante el par referenciado, no mediante una relación inventada.

## 3. Qué no garantiza por sí solo el ER

1. Que profesor/estudiante tenga el rol vigente o permiso adecuado: los FK a usuario no implementan JWT ni autorización.
2. Que personaje y escena, escena destino, criterio de decisión y rúbrica pertenezcan al mismo caso; las FK simples permiten cruces. Los servicios y, si se aprueban, triggers de integridad deben impedirlos sin añadir entidades.
3. Que consentimiento pertenezca al usuario de grupo_estudiante, o permiso extra a la misma participación del intento. Debe comprobarse por la cadena de relaciones bajo la transacción.
4. Una respuesta vigente por pregunta, un solo intento EN_CURSO, estados válidos, fechas coherentes, cupos o inmutabilidad: no hay CHECK/índices parciales para ello en el DBML original.
5. Identidad de convocatoria, espacio académico, versión o UUID históricos de la implementación. No hay columnas que los almacenen como tales.
6. Identidad/versión de fórmula, precisión interna, reintentos de entrega, auditoría o detalle individual de ausencia. Un campo de texto no sustituye esas relaciones estructuradas sin decisión explícita.

Se pueden proponer índices, guardas y CHECK sobre las mismas 28 tablas, documentados/revisados antes de DDL. No están dibujados ni se afirman existentes. No se agregan columnas para «resolver» estos puntos en el objetivo sin autorización.

## 4. Inventario ORM actual, separado del objetivo

Lectura en memoria con creación de motores y conexiones bloqueadas; no se ejecutan revisiones. Tipos expresados para PostgreSQL, no leídos de una base física. Las dos columnas NULLTYPE pendientes se informan como no resueltas, sin asignarles tipos ficticios.

| Tabla y estado | Clase | Columnas actuales (?: permite NULL) | PK / UNIQUE / FK |
|---|---|---|---|
| rol (integrada) | RolORM | `id_rol: INTEGER`; `nombre: VARCHAR(40)`; `descripcion?: TEXT` | PK (id_rol); UQ (nombre); FK ninguna |
| permiso (integrada) | PermisoORM | `id_permiso: INTEGER`; `codigo: VARCHAR(80)`; `descripcion: TEXT` | PK (id_permiso); UQ (codigo); FK ninguna |
| rol_permiso (integrada) | RolPermisoORM | `id_rol: INTEGER`; `id_permiso: INTEGER` | PK (id_rol,id_permiso); UQ ninguna; FK (id_permiso)→permiso.id_permiso; (id_rol)→rol.id_rol |
| usuario (integrada) | UsuarioORM | `id_usuario: INTEGER`; `id_rol: INTEGER`; `nombre: VARCHAR(120)`; `correo: VARCHAR(200)`; `clave_hash: VARCHAR(255)`; `activo: BOOLEAN` | PK (id_usuario); UQ (correo); FK (id_rol)→rol.id_rol |
| identidad_academica (integrada) | IdentidadAcademicaORM | `sistema: VARCHAR(16)`; `id_academico: UUID`; `id_usuario: INTEGER` | PK (sistema,id_academico); UQ ninguna; FK (id_usuario)→usuario.id_usuario |
| caso (integrada) | CasoModel | `id: UUID`; `docente_creador_id: UUID`; `creado_en: TIMESTAMP WITH TIME ZONE` | PK (id); UQ ninguna; FK ninguna |
| version_caso (integrada) | VersionCasoModel | `id: UUID`; `caso_id: UUID`; `numero: INTEGER`; `nombre: VARCHAR(160)`; `desarrollo_situacional: TEXT`; `contexto_historia: TEXT`; `tiempo_estimado_min: INTEGER`; `estado: VARCHAR(20)` | PK (id); UQ (caso_id,numero); FK (caso_id)→caso.id DELETE CASCADE |
| escenario (integrada) | EscenarioModel | `id: UUID`; `version_caso_id: UUID`; `orden: INTEGER`; `contexto_situacional: TEXT` | PK (id); UQ (version_caso_id,orden); FK (version_caso_id)→version_caso.id DELETE CASCADE |
| pregunta (integrada) | PreguntaModel | `id: UUID`; `escenario_id: UUID`; `orden: INTEGER`; `enunciado: TEXT` | PK (id); UQ (escenario_id,orden); FK (escenario_id)→escenario.id DELETE CASCADE |
| opcion_respuesta (integrada) | OpcionRespuestaModel | `id: UUID`; `pregunta_id: UUID`; `orden: INTEGER`; `texto: TEXT`; `es_correcta: BOOLEAN`; `justificacion: TEXT` | PK (id); UQ (pregunta_id,orden); FK (pregunta_id)→pregunta.id DELETE CASCADE |
| rubrica (integrada) | RubricaModel | `id: UUID`; `version_caso_id: UUID`; `nombre: VARCHAR(120)`; `version_regla: VARCHAR(20)` | PK (id); UQ (version_caso_id); FK (version_caso_id)→version_caso.id DELETE CASCADE |
| criterio_rubrica (integrada) | CriterioRubricaModel | `id: UUID`; `rubrica_id: UUID`; `nombre: VARCHAR(120)`; `peso: NUMERIC(5, 2)` | PK (id); UQ ninguna; FK (rubrica_id)→rubrica.id DELETE CASCADE |
| nivel_rubrica (integrada) | NivelRubricaModel | `id: UUID`; `criterio_id: UUID`; `nombre: VARCHAR(80)`; `puntaje: NUMERIC(5, 2)`; `descriptor: TEXT` | PK (id); UQ ninguna; FK (criterio_id)→criterio_rubrica.id DELETE CASCADE |
| valoracion_opcion (integrada) | ValoracionOpcionModel | `opcion_id: UUID`; `criterio_id: UUID`; `puntaje: NUMERIC(5, 2)` | PK (opcion_id,criterio_id); UQ ninguna; FK (opcion_id)→opcion_respuesta.id DELETE CASCADE; (criterio_id)→criterio_rubrica.id DELETE CASCADE |
| espacio_academico (integrada) | EspacioAcademicoModel | `id: UUID`; `nombre: VARCHAR(160)` | PK (id); UQ ninguna; FK ninguna |
| sesion_programada (integrada) | SesionProgramadaModel | `id: UUID`; `espacio_academico_id: UUID`; `version_caso_id: UUID`; `docente_id: UUID`; `fecha_inicio: TIMESTAMP WITH TIME ZONE`; `fecha_fin: TIMESTAMP WITH TIME ZONE`; `tiempo_maximo_minutos: INTEGER`; `lugar?: VARCHAR(255)`; `mensaje_personalizado?: TEXT`; `estado: VARCHAR(20)`; `finalizado_en?: TIMESTAMP WITH TIME ZONE` | PK (id); UQ ninguna; FK (version_caso_id)→version_caso.id; (espacio_academico_id)→espacio_academico.id |
| convocatoria (integrada) | ConvocatoriaModel | `id: UUID`; `sesion_id: UUID`; `estudiante_id: UUID`; `codigo_hash: VARCHAR(255)`; `estado: VARCHAR(20)` | PK (id); UQ (sesion_id,estudiante_id); FK (sesion_id)→sesion_programada.id |
| notificacion (integrada) | NotificacionModel | `id: UUID`; `convocatoria_id?: UUID`; `destinatario_id: UUID`; `tipo: VARCHAR(60)`; `canal: VARCHAR(20)`; `mensaje: TEXT`; `estado: VARCHAR(20)`; `creada_en: TIMESTAMP WITH TIME ZONE` | PK (id); UQ ninguna; FK (convocatoria_id)→convocatoria.id |
| evento_auditoria (integrada) | EventoAuditoriaModel | `id: UUID`; `sesion_id: UUID`; `tipo: VARCHAR(80)`; `estado_anterior?: VARCHAR(20)`; `estado_nuevo?: VARCHAR(20)`; `origen: VARCHAR(30)`; `descripcion?: TEXT`; `creado_en: TIMESTAMP WITH TIME ZONE` | PK (id); UQ ninguna; FK (sesion_id)→sesion_programada.id |
| permiso_intento_extra (pendiente) | PermisoIntentoExtraORM | `id_permiso_extra: INTEGER`; `id_participacion: NULLTYPE: FK externa no resuelta`; `id_profesor: INTEGER`; `cantidad_autorizada: INTEGER`; `justificacion: TEXT`; `fecha_autorizacion: TIMESTAMP WITHOUT TIME ZONE` | PK (id_permiso_extra); UQ ninguna; FK (id_participacion)→participacion.id_participacion; (id_profesor)→usuario.id_usuario |
| retroalimentacion_docente (pendiente) | RetroalimentacionDocenteORM | `id_retroalimentacion: INTEGER`; `id_asignacion: NULLTYPE: FK externa no resuelta`; `id_profesor: INTEGER`; `texto: TEXT`; `fecha_registro: TIMESTAMP WITHOUT TIME ZONE` | PK (id_retroalimentacion); UQ (id_asignacion); FK (id_profesor)→usuario.id_usuario; (id_asignacion)→asignacion_caso.id_asignacion |

Las 19 integradas suman 92 columnas, 19 PK, 18 FK, 9 UNIQUE, 6 CHECK y 17 índices explícitos no únicos. Los 6 CHECK pertenecen a identidad_academica (2), sesion_programada (3) y convocatoria (1); no validan los campos que aún faltan en el ER objetivo. Los índices implícitos de PK/UNIQUE no se cuentan como explícitos.

## 5. Interpretación de límites sin cambiar el ER

- Consentimiento: el objetivo conserva intento.id_consentimiento NOT NULL porque es lo que contiene el ER oficial. Eso no demuestra que D03 haya aprobado su obligación universal. Si el negocio permite «no aplica», hay incompatibilidad que exige R05; no crear aceptación o documento ficticios. El estado actual bloquea ese caso, no lo resuelve.
- Matrícula: se conserva UNIQUE(grupo,estudiante), fecha_ingreso y activo. No hay fecha_retiro ni episodios. No se adopta la modificación M2 de BD-1.1. Reingreso/historia necesitan decisión R08.
- Participación: se conserva asignación/membresía y default literal 'pendiente', no convocatoria ni estado nullable. Ese default no es autorización ni aprobación del catálogo RN-22 completo.
- Tiempo: timestamps originales son sin zona. El dominio usa fechas con zona; la conversión para nuevos datos debe ser explícita y reversible en instantes UTC. Fechas legadas sin origen horario verificable no se convierten suponiendo una zona.
- Resultado: sin fila definitiva significa pendiente, no nota cero. resultado_participacion puede existir sin intento para ausencia; resultado_criterio no puede representar detalle de ausencia sin crear un intento/nivel, lo cual está prohibido. Ver R06.
- Historial: paso_simulacion permite varias filas de una decisión con distinto número. Un contrato append-only y proyección de la última selección podría conservar cambios sin tabla nueva, pero el repositorio y DTO actuales representan selección vigente; esa evolución no está implementada ni aprobada automáticamente.
