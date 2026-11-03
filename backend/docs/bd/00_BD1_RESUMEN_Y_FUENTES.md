# BD-1.2 — Objetivo oficial: 28 tablas

**Corrección de rumbo · 1 de noviembre de 2026 · solo documentación.**

La instrucción vigente del usuario establece que el profesor aprobó el ER de **28 tablas**. Ese es el único modelo objetivo de esta entrega. La propuesta de 40 tablas no fue autorizada y queda retirada como objetivo. No se amplía el sistema por inferencia.

## 1. Modelo objetivo y entregables

| Archivo | Función vigente |
|---|---|
| [ER_OBJETIVO_APROBADO_28_TABLAS.dbml](ER_OBJETIVO_APROBADO_28_TABLAS.dbml) | Nuevo objetivo: reproduce exactamente las definiciones del original, sin tablas/atributos/relaciones adicionales |
| [A — Correspondencia](A_CONCILIACION_ER_ORM.md) | Matriz de las 28, 19 integradas, dos modelos pendientes y diez nombres actuales fuera del listado |
| [B — Inventario](B_MODELO_RELACIONAL_Y_RESTRICCIONES.md) | Todos los 156 atributos, 28 PK, 40 FK/cardinalidades y 19 UNIQUE; inventario ORM separado |
| [C — Plan](C_PLAN_MIGRACIONES_ALEMBIC.md) | Hitos P0–P9, dependencias, backfill, pruebas y rollback sin ejecutar |
| [D — Decisiones](D_DECISIONES_Y_RIESGOS.md) | Incompatibilidades demostradas, alternativas de transición y R01–R09 por aprobar |
| [E — RF](E_TRAZABILIDAD_RF.md) | Cobertura de los 27 requisitos y límites del ER exacto |
| [PROYECTO_NUCLEAR_ER_PROPUESTO.dbml](PROYECTO_NUCLEAR_ER_PROPUESTO.dbml) | **ANTECEDENTE NO APROBADO** de 40/73; solo trazabilidad, nunca fuente de migraciones |

Este resumen es el octavo archivo de la carpeta. Se actualizan los seis Markdown y se añade un rótulo de antecedente al antiguo DBML sin modificar sus definiciones; se crea solo el nuevo DBML de 28. Ningún archivo del backend o ER original cambia.

## 2. Hechos comprobados y separación de planos

| Plano | Resultado |
|---|---|
| Modelo académico oficial | 28 tablas, 156 columnas, 28 PK, 40 FK (38 simples inline y 2 compuestas) y 19 UNIQUE adicionales |
| Original conservado | backend/app/modules/identity/reference/sps.dbml; SHA-256 fb6ab07cfdfee38ba59e1acc879335ec0b377150acc3474b4a817a9eece229d7 |
| Objetivo entregado | Copia estructural exacta del original con preámbulo documental nuevo; no incorpora correcciones no aprobadas del modelo de 40 |
| ORM integrado actual | 19 tablas: Identity 5, Cases 9, Scheduling 5; 92 columnas/19 PK/18 FK/9 UNIQUE/6 CHECK/17 índices explícitos no únicos |
| ORM adicional pendiente | permiso_intento_extra y retroalimentacion_docente en academic_metadata aparte, con FK aún no resolubles. No son productivas por estar declaradas |
| Matriz funcional de las 28 | 4 fieles, 11 parciales y 13 sin tabla ORM productiva. No es diferencia aritmética 28−19 |
| Coincidencia literal | 9 nombres comunes; 10 nombres integrados no figuran entre las 28, de los cuales 3 son renombres parciales |
| Migraciones disponibles | Seis revisiones locales, cuatro con DDL que describen 19 tablas; una cabeza 20261031_academic_identity, archivo sin seguimiento al auditar |
| Esquema físico PostgreSQL | **No verificado**. No conexión, reflexión ni revisión aplicada comprobadas |

Rama verificada: feature/integracion-backend. Los cambios locales y 8A se conservan; no se hace commit, push, merge, reset ni cambio de rama.

## 3. Conclusiones ejecutivas

**Implementar las definiciones oficiales como único esquema físico y conservar sin cambios el backend actual es incompatible.** El código espera UUID, version_caso, sesión y convocatoria; el objetivo tiene INTEGER y asignación/membresía. Reemplazar tablas homónimas rompería columnas, FK, consultas, contexto del JWT y referencias académicas. D lo demuestra con clases/archivos.

La dirección recomendada sigue siendo el objetivo de 28, con adaptación posterior explícita de los consumidores. Mantener provisionalmente el backend no convierte sus tablas adicionales en ampliación aprobada. Una coexistencia de transición puede ensayarse solo si se autoriza y con salida definida; no es un objetivo final de 40 ni una operación permitida por esta fase.

Los 27 RF no necesitan 27 tablas nuevas. Ocho tienen soporte estructural directo, quince parcial, tres conflictos de integración/granularidad/alcance y uno política pendiente, según E. Esto **no** es un porcentaje de implementación ni pruebas aprobadas. El ER exacto tiene conflictos con código individual, feedback individual, ciertos campos de programación y versionado. Se plantean ajustes puntuales dentro de las mismas 28 entidades para aprobación, sin incluirlos silenciosamente en el DBML.

Se conservan en el objetivo incluso los puntos que antes se habían cambiado: consentimiento NOT NULL, UNIQUE de matrícula, participación por asignación/membresía con default pendiente y feedback por asignación UNIQUE. Su presencia oficial no aprueba políticas académicas pendientes; una incompatibilidad se documenta y se bloquea, no se «arregla» con consentimiento ficticio, nueva tabla o nota cero.

## 4. Fuentes y jerarquía

1. Instrucción vigente del usuario: modelo aprobado de 28 entidades, sin autorización de ampliarlo a 40.
2. [DBML original](../../app/modules/identity/reference/sps.dbml) y [modelo ER.png](<../../../_referencias_locales/modelo ER.png>): referencia académica. El DBML determina los atributos y relaciones reproducidos.
3. [ProyectoNuclear-IngenieriaSoftwareII (1).pdf](<../../../_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf>): RF-01…27 páginas 4–5, RN página 7; RN-20 pendiente, RN-21/22 propuestas. Las propuestas alternativas de páginas posteriores no sustituyen el ER confirmado.
4. [Agile Inception SPS.pdf](<../../../_referencias_locales/Agile Inception SPS.pdf>) y [Entrega 1](<../../../_referencias_locales/Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf>): contexto académico ya revisado, no autorización de ampliar entidades o fijar fórmulas.
5. Código/modelos/migraciones locales: evidencia del backend existente, no de aprobación académica ni esquema aplicado.

Fuentes técnicas:
- [Base y registro integrado](../../app/db/models.py).
- [Identity ORM](../../app/modules/identity/infrastructure/models.py), [mapa de alias](../../app/modules/identity/infrastructure/academic_identity_models.py), [académicos pendientes](../../app/modules/identity/infrastructure/academic_models.py).
- [Cases](../../app/modules/cases/infrastructure/models/caso.py), [rúbrica](../../app/modules/cases/infrastructure/models/rubrica.py), [consulta publicada](../../app/modules/cases/application/published_version.py).
- [Scheduling ORM](../../app/modules/scheduling/infrastructure/models.py), [validar ingreso](../../app/modules/scheduling/application/validar_ingreso.py), [política temporal](../../app/modules/scheduling/POLITICA_TEMPORAL_INGRESO.md).
- [ADR histórico](../../../ADR_IDENTIDAD_ACADEMICA.md), [contrato de identidad](../../app/modules/identity/CONTRATO_IDENTIDAD_ACADEMICA.md), [persistencia del resolver](../../app/modules/identity/PERSISTENCIA_IDENTIDAD_ACADEMICA.md), [login Scheduling](../../app/modules/identity/LOGIN_ESTUDIANTIL_SCHEDULING.md).
- [8A](../../app/modules/participation/INTEGRACION_8A.md), [contrato UUID de lectura](../../app/modules/participation/application/integration_ports.py), [adaptador](../../app/modules/participation/infrastructure/integration.py).
- [Dominio Participation](../../app/modules/participation/domain/entities.py), [ports](../../app/modules/participation/application/ports.py), [evaluación](../../app/modules/participation/domain/evaluation.py), [ports evaluación](../../app/modules/participation/application/evaluation_ports.py), [Alembic](../../alembic/versions/).

La enmienda inicial del ADR prevalece sobre su cuerpo histórico: hoy se almacenan 0..N alias por usuario/sistema y se resuelve exactamente uno. Se conserva ese comportamiento actual; el objetivo de 28 no inventa una correspondencia UUID/INTEGER ni ordena borrar el mapa.

## 5. Orden y aprobaciones antes de BD-2

Orden de diseño: decidir transición → reutilizar acceso → grupos/matrícula/consentimiento → contenido/rúbrica/decisiones → asignación → participación/permiso → intentos/pasos → resultados → feedback/notificaciones → adaptar contratos → verificar y solo después evaluar corte.

Aprobar expresamente R01–R09 según el alcance del primer incremento: coexistencia temporal frente a esquema único; versiones/PK; programación y código individual; feedback; consentimiento; evaluación; tiempo/RF-22; matrícula/rutas/historia; procedencia/contratos/entrega. No son nueve autorizaciones genéricas: D especifica quién debe resolver cada pregunta y qué bloquea.

No se usa el plan de BD-1.1 para autogenerar nuevas migraciones. La clave de propietario/puente que ya existe se conserva, pero su evolución debe reevaluarse respecto del objetivo oficial y no autoriza campos del modelo no aprobado.

## 6. Verificaciones y límites de BD-1.2

- Conteo y extracción estática del original, todas sus columnas y relaciones; hash preservado.
- Inspección de metadata en memoria, con creación de motores y conexiones expresamente bloqueadas. Los NULLTYPE de dos FK pendientes se reportan, no se compilan como tipos ficticios.
- Grafo Alembic leído por AST; ninguna revisión ejecutada.
- Comparación estructural del objetivo contra el original: las mismas 28 entidades/156 columnas/PK/FK/UQ/defaults; las definiciones son idénticas.
- Comprobación estática propia, no importación real en dbdiagram ni DDL PostgreSQL ejecutado. No demuestra integridad de datos físicos.
- Controles efectivos: objetivo de 28 tablas/156 columnas/28 PK/40 FK idéntico al original; matriz de 28 y RF de 27 completos; enlaces locales y whitespace sin incidencias; git diff --check con salida 0. Solo siete documentos previos modificados y un DBML nuevo; 239 archivos preexistentes fuera del alcance idénticos por SHA-256, sin eliminaciones. El DBML de 40 conserva sus definiciones y solo recibe el rótulo de antecedente no aprobado.
- **No se ejecutan pytest ni Docker ni conexiones.** Línea base histórica: 1061 aprobadas, 38 omitidas, 0 fallos/errores y advertencia conocida de Starlette/httpx. Las omitidas no son aprobadas; 199 específicas de 8A son otro antecedente, no resultado nuevo.

No se declara completada la base ni los 27 RF. **BD-2 no comenzó.**
