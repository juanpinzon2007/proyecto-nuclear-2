# Contrato de identidad académica y cierre seguro

**Actualización posterior:** las dos rutas estudiantiles pendientes descritas en
esta fase ya tienen protección cerrada. Ver el estado vigente y el bloqueo de
persistencia en [SEGURIDAD_ESTUDIANTIL.md](SEGURIDAD_ESTUDIANTIL.md).

31 de octubre de 2026. Rama `feature/integracion-backend`, base `ee025d2`.
Se conservaron los cambios sin commit de la fase anterior. Ninguna modificación
de esquema, migración, .env, frontend o Participation. No se consultaron datos
de producción: los volúmenes, propietarios y conflictos reales siguen pendientes
de un inventario autorizado. La auditoría describe código, modelos y pruebas.

## Evidencia del significado y origen de identificadores

| Referencia | Origen y persistencia comprobados | Garantía actual |
| --- | --- | --- |
| usuario.id_usuario | Identity: INTEGER autoincremental; repositorio convierte a cadena decimal y JWT la usa como sub | PK real, roles del catálogo del servidor; no se genera un UUID de cuenta |
| caso.docente_creador_id | Antes: X-Docente-Id; router → CasoService → ConstructorCaso → VersionCaso → CasoRepository → caso | UUID sin FK a usuario ni registro docente; la cabecera no probaba propiedad |
| sesion_programada.docente_id | Dependencia docente (antes stub 503); programar_sesion copia el argumento al modelo | UUID sin generador de identidad personal ni FK a usuario |
| convocatoria.estudiante_id | CrearConvocatoriaRequest → router → crear_convocatoria | UUID aportado por el cliente; no valida cuenta Identity; UNIQUE(sesion_id,estudiante_id) no demuestra identidad |
| notificacion.destinatario_id | Convocatoria: copia estudiante_id; observador copia convocatoria.estudiante_id; calificación recibe estudiante_id | UUID del espacio Scheduling; crear_notificacion compara con estudiante de convocatoria cuando existe |

`uuid_pk()` de Cases y Scheduling genera UUID4 para PK de caso, versión, sesión,
convocatoria, etc. **No genera identidades de docentes ni estudiantes.** Las
fixtures sí generan UUID personales aleatorios, pero no son evidencia de un
registro institucional. No hay semilla/servicio productivo de asociación personal
en el backend inspeccionado.

La integración Scheduling importa VersionCasoModel y persiste su FK. El test
`tests/integration/scheduling/test_scheduling_endpoints.py` reutiliza el mismo
UUID docente al sembrar un caso y programar una sesión. Eso demuestra que los
tipos permiten compartirlo, NO que exista un espacio común real ni que sea una
regla de producción. `programar_sesion` comprueba caso publicado y tiempo; no
deduce identidad por el creador ni exige igualdad con ese creador. Que un docente
pueda programar un caso publicado ajeno sigue siendo una política aparte.

Identity tiene además modelos académicos pendientes con id_profesor INTEGER;
su metadata no integrada no resuelve los UUID de Cases/Scheduling. Sus servicios
de seguimiento/excepciones utilizan las cadenas de Identity, con adaptadores
académicos aún pendientes. Participation usa otros IDs enteros del ER y no se integra.

Las migraciones confirman INTEGER en usuario y UUID personales sin FK en Cases/
Scheduling. El único head inspeccionado es `6867083574f6`, que une las ramas de
Identity/Cases y Scheduling. No existe una tabla de asociaciones en las 18 tablas
registradas ni una revisión que proporcione equivalencia INTEGER/UUID.

**Conclusión:** hay compatibilidad representacional, pero no equivalencia
demostrada. No se puede adoptar automáticamente una asociación global uno a uno.

## Contrato propuesto e implementación independiente del esquema

`application/academic_identity.py` define una proyección inmutable
`VinculoAcademico(id_usuario, sistema, id_academico)`, el puerto de lectura
`ConsultaVinculosAcademicos` y `ResolverIdentidadAcademica`.
No define una entidad personal nueva ni un repositorio SQL ficticio.

El sistema es CASES o SCHEDULING. Esta separación deliberada impide inferir que
dos UUID de igual tipo son la misma identidad. Tampoco obliga a que sean distintos:
si se verifica un vínculo común, ambas asociaciones podrán guardar el mismo UUID.
El contrato es técnico y provisional; el DDL y la responsabilidad institucional
deben aprobarse antes de construir su adaptador real.

La consulta devuelve todas las asociaciones verificadas para el usuario/sistema.
El resolver exige exactamente una, con mismo usuario, sistema enum válido y UUID
no nulo. No crea, convierte ni elige identificadores. Cero vínculos produce
AccesoDenegado (403); duplicados, datos inconsistentes o indisponibilidad declarada
producen IntegracionPendiente (503). Los errores inesperados se propagan (500),
sin apertura de acceso ni captura general.

El adaptador futuro debe garantizar también la unicidad inversa: un UUID no puede
corresponder a dos cuentas dentro del mismo sistema. El resolver no puede demostrar
esa propiedad global con una consulta aislada de un usuario: requiere restricciones
de BD e inventario previo. Las pruebas con mocks no acreditan esa integridad real.

## Protección aplicada ahora

`api/academic_dependencies.py` compone:

1. obtener_docente_actual: Bearer/JWT real, cuenta activa y rol vigente DOCENTE.
2. Fábrica diferida del resolver: solo se ejecuta tras autenticación/autorización.
3. Resolver con sistema explícito; posteriormente el módulo comprueba el recurso.

La fábrica de producción lanza IntegracionPendiente. No hay repositorio productivo
ni asociaciones de respaldo. Resultado sin configuración externa aprobada:

| Solicitud docente | Respuesta |
| --- | --- |
| Sin Bearer o token inválido | 401 con WWW-Authenticate Bearer |
| Cuenta inexistente/inactiva | 401 |
| Cuenta sin rol DOCENTE | 403 |
| Docente válido, sin adaptador configurado | 503 |
| Adaptador disponible, sin vínculo | 403 |
| Vínculo duplicado/inconsistente o fallo declarado | 503 |

Cases sustituye la cabecera por Depends(obtener_docente_cases) en sus seis rutas.
Se ejecuta antes de construir el servicio/Session académica. X-Docente-Id ya no es
parámetro de OpenAPI y, aunque se envíe, no afecta al UUID resuelto. La propiedad
sigue siendo comprobada por CasoService/CasoRepository: los casos ajenos dan 404.

Scheduling mantiene el nombre obtener_docente_autenticado como punto de composición,
pero delega en obtener_docente_scheduling. Sus operaciones docentes quedan cerradas
sin adaptador real. Además se protegieron las consultas de espacios y sesiones:
el listado filtra siempre por UUID resuelto y rechaza filtros ajenos; el detalle
de sesión compara propietario (403). Se preservan rutas, tipos de datos y cuerpos;
el cambio intencional de contrato es exigir seguridad, en vez de cabecera o acceso
anónimo. El anónimo pasa de 503 a 401 en las antiguas operaciones docentes.

La autenticación no concede permiso sobre cualquier recurso ni demuestra que un
destinatario enviado en un cuerpo sea un estudiante real. Notificaciones de
calificación, permisos específicos y convocatoria de estudiantes siguen necesitando
sus propios contratos de ámbito. No se inventaron esas políticas aquí.

**Riesgos pendientes:** GET /scheduling/notificaciones aún recibe un destinatario
del cliente; /validar-ingreso usa código/convocatoria/horario y no identidad JWT.
No están protegidos por esta dependencia docente. Se requiere un contrato de
identidad estudiantil/destinatario y revisión del acceso antes de exposición pública.
No se afirma que todo Scheduling esté integrado o listo para producción.

## Diseño persistente para aprobación, sin DDL ejecutado

Propuesta conservadora: tabla `identidad_academica` propiedad de Identity o de la
composición de integración, con:

- id_usuario INTEGER NOT NULL FK usuario.id_usuario.
- sistema identificando CASES/SCHEDULING, con valores controlados.
- id_academico UUID NOT NULL, distinto del UUID nulo.
- PRIMARY KEY(id_usuario,sistema).
- UNIQUE(sistema,id_academico).

Cardinalidad: una cuenta tiene cero o una asociación por sistema; dentro de ese
sistema el UUID se vincula a una sola cuenta. Se proponen identidades personales,
no una asociación diferente por rol: cambiar de rol no cambia el UUID. Si el equipo
confirma varios perfiles personales por cuenta, esta cardinalidad NO es suficiente
y debe revisarse antes de migrar. La PK y UNIQUE impedirán ambigüedad, no probarán
que una asociación es correcta: el alta necesita evidencia y autorización.

No hay FK desde UUID hacia una tabla docente inexistente. Las referencias actuales
caso/sesion/convocatoria/notificacion no se modificarían inicialmente. Para añadir
integridad referencial desde esas tablas al registro, habría que diseñar claves
compuestas con sistema, o registros por módulo; requiere otra aprobación, reconciliar
huérfanos y revisar las FK con el equipo. No prometer esa integridad con una FK simple.

Alternativa si se demuestra una identidad común global: registro único con
usuario INTEGER PK/FK y UUID UNIQUE, sin sistema. Es más simple, pero hoy no hay
evidencia suficiente para elegirla. Otra alternativa es normalizar todas las
referencias a INTEGER; afecta contratos públicos y datos, por lo que se descarta
para este incremento.

### Alta y recuperación

Usuarios antiguos sin asociación conservan su cuenta, roles y autenticación; sus
operaciones académicas quedan denegadas hasta reconciliación, sin altas automáticas.
No usar login, cabeceras, correo ni un JWT para elegir un UUID histórico.

Para identidades realmente nuevas, propuesta de regla explícita: en un alta
académica autorizada y auditada, verificar cuenta, sistema y ausencia de vínculo;
generar UUID4 una sola vez en el servidor e insertarlo bajo la misma transacción.
Devolverlo solo tras commit. Ante carrera/UNIQUE, releer o rechazar; nunca sustituir
un vínculo existente. Las futuras peticiones solo recuperan el valor persistido.
Esta regla es una propuesta: NO existe código de generación/alta en este incremento.

Las asociaciones históricas importan el UUID existente verificado, sin generar
reemplazos. Una misma persona con varios UUID históricos en un sistema no puede
resolverse eligiendo uno arbitrariamente: requiere una decisión de consolidación
o un contrato de alias aprobado con análisis de todas las referencias.

## Plan de migración propuesto, no ejecutado

1. Aprobar dueño y cardinalidad; obtener exportación de prueba autorizada o copia
   anonimizada. Inventariar DISTINCT UUID de caso.docente_creador_id,
   sesion_programada.docente_id, convocatoria.estudiante_id y
   notificacion.destinatario_id; separar sistemas, cuentas y evidencia institucional.
2. Detectar usuarios/UUID sin propietario, UUID compartidos indebidamente, varias
   cuentas por persona y múltiples UUID por cuenta. Un caso y una sesión con UUID
   idéntico son un indicio, no prueba de titularidad. Mantener ambiguos sin vínculo.
3. Aprobar en revisión las asociaciones y conservar evidencia auditada. No poblar
   desde cabeceras históricas sin verificar ni emparejar automáticamente por correo.
4. Tras aprobación, crear una revisión Alembic nueva sobre el head vigente;
   crear solo la tabla acordada e importar vínculos verificados en una operación
   controlada aparte. No alterar ni borrar UUID de las tablas académicas existentes.
5. Implementar consulta SQL usando la Session compartida. Añadir pruebas PostgreSQL
   independientes para FK, unicidad en ambos sentidos, commit/rollback, concurrencia
   y persistencia estable; no habilitar el adaptador basándose solo en mocks.
6. Validar ida/vuelta y propiedad en endpoints con cuentas/vínculos reales de prueba;
   verificar docentes sin asociación y revocación. Activar el constructor real solo
   cuando no existan ambigüedades para las cuentas habilitadas. Nunca fallback por header.
7. Añadir FK académicas únicamente después de demostrar cobertura de referencias.
   Revertir la activación debe volver al 503 cerrado; el rollback de datos requiere
   conservar registro de lo importado. No borrar referencias académicas al quitar vínculos.

Impacto sobre datos existentes: este cambio de código no reescribe ninguna fila;
sí cierra acceso previamente permitido por cabecera y consultas anónimas de sesión.
No se conoce cuántas cuentas quedarán sin vínculo: no se accedió a producción.
La migración propuesta es aditiva, pero vincular mal un UUID transferiría propiedad
de todos sus casos/sesiones, por lo que reconciliar es un requisito de seguridad.

Participation necesitará adaptadores propios: no se transforma su id_estudiante,
membresía, participación o intento entero en estos UUID. El contexto Identity puede
ser común, pero los identificadores académicos de cada módulo deben resolverse de
forma explícita. No se implementó nada de Participation.

## Pruebas y cambios de fixtures

Se añadieron 44 casos en `tests/integration/test_academic_identity_security.py`:
las quince rutas docentes rechazan solo cabecera; JWT y rol; constructor ausente;
vínculo ausente, duplicado, usuario/sistema discordante, UUID inválido/nulo y caída;
cabecera ajena ignorada; propiedad y filtro de sesiones; separación entre sistemas;
excepción inesperada y contrato OpenAPI.

Las pruebas Cases existentes se mantienen, incluido rechazo de casos ajenos con
404. Sus fixtures ahora emiten JWT reales y usan dos asociaciones explícitas de
prueba con el resolver real, en lugar de autenticación por header. No se debilitaron
asserts de negocio ni se saltaron tests. Las pruebas Scheduling de consultas se
adaptaron al contexto docente; otras fixtures antiguas siguen sustituyendo la
dependencia UUID para aislar negocio, y no prueban autenticación real.

La caracterización de la fase anterior que esperaba aceptación de X-Docente-Id
ahora exige 401 y que el servicio no se invoque. Es un cambio intencional de contrato
de seguridad, no una forma de esconder un fallo.

Resultados ejecutados en esta fase:

| Suite | Passed | Failed | Skipped | Warnings |
| --- | ---: | ---: | ---: | ---: |
| Específica inicial (antes de ampliar consultas de sesiones) | 93 | 0 | 0 | 1 |
| Específica final: seguridad nueva, fase anterior, Cases y Scheduling | 191 | 0 | 0 | 1 |
| Completa: backend/tests + participation/tests | 734 | 0 | 38 | 1 |

Comando específico final:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/integration/test_academic_identity_security.py backend/tests/integration/test_docente_identity.py backend/tests/integration/cases backend/tests/unit/scheduling backend/tests/integration/scheduling -q -rs --tb=short
```

Comando completo:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Los 38 skipped siguen SIN comprobarse. No se habilitaron variables PostgreSQL ni
se ejecutaron migraciones. Los tests nuevos son HTTP ASGI con JWT, autorización y
resolver reales, pero consulta de vínculos, servicio Cases y Session simulados.
Los tests funcionales antiguos Cases/Scheduling ejecutan repositorios con SQLite
en memoria al faltar TEST_DATABASE_URL. Ninguna de esas pruebas demuestra el nuevo
registro persistente en PostgreSQL. Advertencia conocida de Starlette/httpx.

## Archivos y decisión humana requerida

Producción: dos archivos nuevos en Identity (`application/academic_identity.py`,
`api/academic_dependencies.py`); routers Cases/Scheduling modificados. La dependencia
obtener_docente_actual anterior se conserva. Documentación: este documento y enlace
de vigencia desde INTEGRACION_DOCENTE.md. Pruebas: archivo nuevo de seguridad,
fixture y dos archivos funcionales Cases, dos unitarios Scheduling y actualización
de la caracterización anterior. No cambios de modelos ni Alembic.

**Se necesita aprobación del equipo** sobre identidad global frente a asociaciones
por sistema, cardinalidad, dueño del registro, fuente de verdad para reconciliar y
procedimiento de alta/rectificación. Hasta entonces el contrato de lectura se puede
probar y las rutas permanecer seguras y cerradas, pero el mapeo persistente y la
integración funcional completa NO están terminados. No se ejecutó commit, push,
merge, PR ni cambio de rama.
