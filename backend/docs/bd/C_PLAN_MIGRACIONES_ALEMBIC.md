# C — Plan seguro hacia el ER oficial de 28 tablas

**BD-1.2. Plan, no migraciones.** El objetivo es [ER_OBJETIVO_APROBADO_28_TABLAS.dbml](ER_OBJETIVO_APROBADO_28_TABLAS.dbml), no el DBML histórico de 40. No se ejecuta DDL, pytest, Docker, conexiones ni modificación de datos.

## 1. Cadena local comprobada, no estado aplicado

```text
20261028_identity_access ───────────┐
                                  ├─20261028_merge_access_cases─┐
c27a750108db───────────────────────┘                            │
       └─36b9e0790539───────────────────────────────────────────┤
                                                               └─6867083574f6
                                                                    └─20261031_academic_identity
```

Seis revisiones, dos merges, dos raíces históricas y una cabeza local: **20261031_academic_identity**. Las cuatro revisiones con DDL describen 19 tablas, no las 28 oficiales. La cabeza de identidad académica sigue sin seguimiento Git; no se presume aplicada. No reescribir revisiones anteriores ni usar stamp para ocultar diferencias.

Los identificadores P0–P9 siguientes son hitos de diseño, no nuevos revision IDs. Tras aprobación se derivarán revisiones aditivas de la cabeza reconciliada, con una sola cabeza y sin recrear las cuatro tablas de acceso.

## 2. Reglas comunes de seguridad

- No alterar in situ caso/opción/rúbrica/criterio/notificación UUID para convertirlos en INTEGER. Son estructuras homónimas incompatibles, no una migración de tipo sencilla.
- Decidir R01 antes de cualquier DDL: un namespace de ensayo puede evitar colisiones, pero añade coexistencia física temporal y requiere autorización. Si no se permite, trabajar sobre una copia aislada, no en la base compartida.
- Identidad es única: no duplicar cuentas/roles como nuevos propietarios para facilitar importaciones. Reutilizar las PK de usuario existentes verificadas.
- Expandir primero y mantener lectores/escritores actuales sin cambios hasta aprobar los adaptadores. No escribir simultáneamente dos modelos académicos divergentes sin contrato de consistencia/transacción.
- Backfill solo con correspondencias y fuentes verificadas. Un manifiesto de migración puede registrar tabla/UUID fuente, versión, PK destino INTEGER y evidencia/hash; es artefacto de traslado, no un repositorio productivo de autorización.
- Generar una nueva PK INTEGER para una entidad destino es creación de identidad interna documentada, no una equivalencia personal INTEGER/UUID. Nunca convertir usuario a UUID, reutilizar un UUID histórico para otra persona ni perder procedencia.
- Si contratos externos necesitan conservar UUID después del corte, un manifiesto externo estático por sí solo **no** basta como resolver productivo. Acordar campos de procedencia dentro de las 28 o conservar temporalmente fuente/adaptador, con autorización.
- No eliminar columnas ni tablas actuales en este plan ejecutable inicial. El retiro posterior de estructuras adicionales necesita aprobación separada, datos conciliados y consumidores migrados.

## 3. Hitos en orden de dependencias

### P0 — Aprobaciones y ensayo de reconciliación

**Depende de:** R01 y responsables de R02–R09 identificados.

Comparar esquema aplicado y alembic_version únicamente en una copia/laboratorio autorizado en fase posterior. Inventariar datos, claves, zona temporal, versiones, alias, roster, comentarios y referencias externas. No hay tal conexión en esta revisión.

Preparar mapeos y casos de incompatibilidad; si falta grupo, aceptación, rúbrica o dueño, reportar y detener esa fila. No crear usuarios, membresías o calificaciones para llenar vacíos.

Pruebas futuras: inspección/reflection y round-trip de la copia antes/después; verificar origen y conteos, no solo filas insertadas. Rollback de esta preparación es descartar únicamente el laboratorio propio; nunca limpiar fuentes compartidas.

### P1 — Reutilizar acceso; grupos, membresías y consentimiento

**Depende de:** P0; R05/R08 para habilitar operaciones.

Conservar rol, permiso, rol_permiso y usuario si su esquema físico corresponde al ya declarado. No ejecutar CREATE sobre ellas sin inspección de la revisión aplicada. Preparar grupo_academico → grupo_estudiante y consentimiento, con PK/FK/UNIQUE originales.

Backfill desde padrón autorizado; no deducir grupo de espacio, inscripción de convocatoria o aceptación de login. Conservar UNIQUE(grupo,estudiante), fecha_ingreso/activo y la aplicabilidad del consentimiento sin imponer otra política.

Pruebas futuras: usuario inexistente, duplicado de membresía, consentimiento ajeno/revocado y rechazo del inicio si falta aplicabilidad. Rollback: conservar evidencia y detener operaciones; DROP de nuevas tablas solo admisible en laboratorio desechable sin datos útiles, nunca como reversión automática en el equipo.

### P2 — Contenido de Cases y rúbrica oficial

**Depende de:** P0/P1 y R02/R06.

Orden: caso → objetivo_aprendizaje/escena/personaje → rubrica → criterio_rubrica → nivel_criterio → decision → opcion_respuesta → pista/personaje_escena. Las tablas de contenido nuevas en el destino usan INTEGER y los nombres oficiales; no se renombran las actuales para aparentarlo.

Preservar cada contenido/version/rúbrica usado por sesiones e intentos. Si se aprueba una fila caso independiente por edición, conservar todas las ediciones y un mapeo explícito; sin ese acuerdo no colapsar versiones. Introducción, título/tipo de escena, criterio y escala no se rellenan con valores ficticios.

Crear PK/FK/UQ originales. Guardas de mismo caso y publicación, índices de consulta y CHECK técnicos se proponen para revisión, sin entidades nuevas. No sustituir valoracion_opcion multicriterio sin R06.

Pruebas futuras: opción/decisión correctas, destino/personaje de otro caso, rúbrica de la edición exacta, dos versiones diferentes y rechazo de pérdida de datos/precisión. Rollback: fuente intacta y aplicación actual aún operativa; no borrar el contenido importado si ya se referenció académicamente.

### P3 — Asignación y programación conciliadas

**Depende de:** grupos y caso de P1/P2; R03/R07.

Crear asignacion_caso del ER con grupo/caso INTEGER, fechas, tiempo, intentos y hash; no reemplazarla automáticamente por sesión/convocatoria. Las estructuras actuales de Scheduling siguen intactas durante transición autorizada.

No copiar sesión a asignación sin decidir relación espacio/grupo, matrícula, tiempo estimado/máximo, lugar/mensaje y granularidad de código. Si hay estudiantes de varios grupos o sin membresía demostrada, no construir una asignación genérica.

La ventana RF-22 no se obtiene de una tolerancia enviada por HTTP; sin aprobación no se habilita ingreso. Diferenciar apertura/cierre programados, fin individual y cierre real. Si se aprueban ajustes de columnas dentro de las 28, actualizar DBML y plan **antes** de codificarlos.

Pruebas futuras: docente/titularidad, sesión finalizada, retiro, umbral ausente, fechas/fronteras y clave de otro estudiante. Rollback: mantener sesión/convocatoria y JWT existentes; no invalidar tokens por retirar tablas de las que dependen.

### P4 — Participación original y permiso excepcional

**Depende de:** P1/P3 y definición de convocatoria dentro de R03.

Crear participacion con UNIQUE(asignación,membresía), default pendiente y FK originales. No importar la propuesta P1 de una fila por convocatoria de BD-1.1 como si estuviera aprobada. Preparar permiso_intento_extra con profesor usuario y participación real.

Integrar una sola definición de la clase pendiente; no duplicar la tabla ni promover FK NULLTYPE sin dependencias. El permiso se comprueba contra el creador verificado del caso y se consume bajo bloqueo.

Backfill únicamente de relaciones demostradas; una participación contenedor no equivale a intento, ausencia o consentimiento. Pruebas futuras: dueño/membresía ajenos, duplicado, autorización de creador y consumo concurrente. Rollback: fuentes intactas, conservar cualquier permiso o participación ya usado; desactivar nuevas escrituras antes de retirar adaptadores.

### P5 — Intentos, decisiones y tiempo individual

**Depende de:** P2/P4; R05/R07/R08.

Crear intento después de consentimiento/permiso; crear paso_simulacion después de intento/opción/decisión. Conservar FK compuesta opción/decisión y UNIQUE(intento,número). Índice parcial de un activo, CHECK temporales/estados y guardas de cerrado son propuestas técnicas sobre las tablas existentes, sujetas a revisión.

El ER no almacena duración del intento. Reconstruir inicio + asignación.tiempo_maximo_min solo si ese valor queda históricamente estable; si el negocio necesita editarlo, proponer campo de duración/plazo en intento para aprobación, sin tabla nueva. No usar configuración nueva para recalcular plazos antiguos.

Elegir selección vigente o registro de cambios en paso_simulacion: el ER permite varios registros de una decisión. Para historial, registrar número secuencial y proyectar última por decisión; requiere adaptar repositorio/DTO y reglas de ruta. No se crea historial_decision de la propuesta no aprobada.

Una sola UoW revalida Identity/asignación/membresía/código/consentimiento/cupo bajo orden de locks acordado y lee reloj después de bloquear. Snapshot 8A informativo no es permiso de escritura.

Pruebas futuras PostgreSQL con dos conexiones: doble inicio/cupo, retiro/cierre concurrente, guardar vs vencer/finalizar, rollback sin respuesta parcial, fin repetido idempotente y paso conservado al vencer. Rollback: impedir nuevas escrituras conservando lecturas/cierres; no borrar respuestas para volver a un modelo anterior.

### P6 — Resultados y ausencia sin registros ficticios

**Depende de:** P5 y política R06.

Crear resultado_intento → resultado_criterio, y resultado_participacion para consolidado/ausencia. Conservar UNIQUE por intento/participación y FK nivel/criterio. En la ausencia no crear intento, selección ni nivel cero artificial.

Solo guardar lista_para_persistir; pendiente no es cero. Escala decimal del ER y redondeo oficial deben ser compatibles; no dejar que PostgreSQL redondee silenciosamente una nota no certificada. Guardar evidencia suficiente por cadena hacia contenido/rúbrica estables; referencias de política adicionales en las mismas tablas requieren aprobación si se necesitan.

Detalle de ceros por pregunta puede reconstruirse únicamente con universo/regla/contenido inmutables aprobados. Si se exige evidencia relacional persistida que el ER no soporta, detener ese detalle y acordar ajuste dentro de las 28; no guardar JSON opaco ni crear una tabla adicional por defecto.

Pruebas futuras: resultado duplicado, criterio ajeno, nota pendiente no insertada, ausencia sin intento, carrera inicio/ausencia, precisión y consolidación sin regla. Rollback: resultados definitivos se preservan; corrección aditiva, no eliminación/recalificación automática.

### P7 — Feedback y notificaciones conciliados

**Depende de:** asignación/usuario y, para individual, R04/R09.

retroalimentacion_docente original se asocia a asignación UNIQUE: no implementa RF-26 individual solo por existir. Puede prepararse fiel al ER, pero no habilitar escritura individual sin resolver esa incompatibilidad. No copiar comentario de grupo a todos los estudiantes.

notificacion original es INTEGER/usuario/asignación, distinto del ORM actual UUID/convocatoria. Mantener envíos, destinatarios y mensajes actuales como fuente hasta verificar su correspondencia. Falta fecha_envio/lectura verificada significa desconocido, no aviso ya entregado. No truncar tipo de 60 a 40 caracteres sin conciliación.

Plan de entrega durable e idempotencia con las mismas 28 puede requerir columnas adicionales aprobadas en notificacion; no crear evento_salida ni eliminar evento_auditoria existentes por conteo. No reconstruir código desde hash ni persistirlo en claro.

Pruebas futuras: dueño correcto, comentario sin destinatario no distribuido, rollback no envía, reintento sin duplicado y fallo de transporte/clave sin apertura de acceso. Rollback: conservar mensajes y cola; no reiniciar envíos históricos automáticamente.

### P8 — Adaptadores, contratos y regresión por recorrido

**Depende de:** correspondencias R01–R09 aprobadas y escritores/lectores del destino.

Modificar en fase posterior, de forma explícita, los adaptadores de Identity/Cases/Scheduling y puertos/DTO necesarios. Facade, Strategy y los otros patrones conservan responsabilidades; no trasladar SQL/negocio al router ni sustituir JWT.

La API y contratos UUID actuales necesitan estrategia de compatibilidad si se retiran las tablas que los sostienen. Un alias de tabla o cast no conserva UUID originales. Probar login → titularidad → programación → intento → selección → cierre → resultado con referencias verificadas, sin asumir que 8A ya es compatible.

Ejecutar después las pruebas específicas, suite completa y concurrencia/migración del laboratorio autorizado. Línea base histórica: 1061 aprobadas/38 omitidas; no afirmar nueva ejecución ni esconder incompatibilidades modificando expectativas sin revisión.

### P9 — Corte y eventual retiro, solo con nueva autorización

**Depende de:** P8, inventario físico, conciliación total y aprobación separada de datos/contratos.

Comprobar que todos los consumidores y referencias históricas tienen destino; comparar PK/FK/UNIQUE, conteos, precisión, instantes y procedencia. Verificar que el schema final aprobado contiene las 28 entidades o la variante de columnas aprobada dentro de ellas, sin tablas encubiertas.

Este plan no contiene DROP ejecutable de las adicionales. Si persiste dependencia de version_caso/convocatoria/identidad_academica u otra, detener el corte y explicar incompatibilidad. El retiro físico solo se diseñará tras aprobación específica y respaldo/recuperación verificados. Mantener 28 como objetivo no justifica perder historia.

## 4. Archivos potenciales de una iteración autorizada

Prefijo backend/app/modules/ salvo indicación contraria:

| Área | Archivos/contratos que requerirían revisión, no modificados aquí |
|---|---|
| Identity | infrastructure/models.py, academic_models.py, academic_identity_models.py/repository; autenticación y academic_dependencies.py/scheduling_access.py |
| Cases | infrastructure/models/caso.py, rubrica.py, registro __init__; repositorios; published_version.py y contratos UUID/versión |
| Scheduling | infrastructure/models.py y repositorios; servicios de programación/convocatoria/validar_ingreso, State y políticas inyectadas |
| Participation | domain/entities.py, application/ports.py/evaluation_ports.py, dto.py y servicios; adaptadores/models/repositorios futuros y unit_of_work.py; API provisional solo con revisión contractual |
| Integración | backend/app/db/models.py; backend/alembic/versions/ solo después de aprobación; pruebas del laboratorio y regresión |

No se generan estos archivos ni revisiones en BD-1.2. El plan anterior de 40 no sirve para autogenerar migraciones de este objetivo.
