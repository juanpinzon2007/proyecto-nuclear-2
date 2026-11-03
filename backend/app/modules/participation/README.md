# Participación — dominio, Application, evaluación, API y preparación de persistencia

Contiene dominio, Application con Facade, evaluación con Strategy y el cuarto
incremento de API provisional. El router **no está registrado en main.py**.
La fase [8A](INTEGRACION_8A.md) conecta su dependencia de identidad con JWT, roles
y resolver SQL de Identity, y prepara una consulta interna de ingreso, versión
asignada y referencia de su rúbrica. No tiene ORM, escritores SQL, calificación
oficial ni composición real de la fachada. RF-22 y los vínculos del agregado
siguen pendientes. Los fakes solo existen en pruebas.
El quinto incremento añade consultas SQLAlchemy y una unidad de trabajo, todavía
sin escritores académicos ni esquema compartido definitivo conectado.
Las secciones siguientes conservan el historial de los incrementos; el estado
vigente y los límites de integración están en INTEGRACION_8A.md.

## Componentes

- `domain/entities.py`: `Participacion` relaciona una asignación con una membresía
  de estudiante (`id_grupo_estudiante` no equivale a `id_usuario`). `Intento`
  representa una ejecución con consentimiento y permiso extraordinario opcional.
  `PasoSimulacion` representa la selección actual de una decisión del intento.
  Las referencias son enteros; no se duplican usuarios, casos ni asignaciones.
- `domain/clock.py`: `Reloj` es un contrato pequeño. `RelojSistema` obtiene UTC
  del servidor. Las pruebas proporcionan un reloj fijo que puede adelantarse.
- `domain/errors.py`: errores de integridad y rechazo de edición que la futura
  Application podrá traducir a sus resultados; no dependen de HTTP.
- `application/ports.py`: contratos propuestos con Cases, Identity y Scheduling.
  Los Protocol no realizan validaciones reales ni constituyen autorización.
- `application/facade.py`: punto de entrada con seis operaciones públicas; solo
  delega en servicios especializados y exige dependencias explícitas.
- `application/services.py`: servicios de inicio, decisiones, progreso y cierre.
  Coordinan autorización, dominio y confirmación transaccional.
- `application/dto.py`: selección, recorrido y respuestas de Application sin
  corrección, justificaciones ni puntajes.
- `application/errors.py`: rechazo de permisos, reglas pendientes, recursos no
  disponibles y conflictos de actualización, sin dependencias de HTTP.
- `domain/evaluation.py`, `domain/estrategias_evaluacion.py` y
  `domain/calculador_rubrica.py`: valores, tres estrategias y matemáticas explícitas.
- `application/evaluation_service.py` y `application/evaluation_ports.py`: selección
  de estrategia, políticas externas y confirmación de evaluaciones sin duplicarlas.
- `tests/test_domain.py`: pruebas unitarias sin servicios externos ni BD.
- `tests/test_application.py` y `tests/fakes.py`: casos de uso y dobles aislados
  para los puertos. `tests/__init__.py` permite imports explícitos de esos dobles.

Los objetos son dataclasses inmutables. Registrar una nueva respuesta o cerrar devuelve
otro `Intento`; el llamador debe utilizar el valor devuelto. El original conserva
su contenido. Esto permite validar el nuevo estado antes de persistirlo en una
futura transacción; no sustituye el control de concurrencia en PostgreSQL.

## Reglas implementadas y respaldo

| Regla | Referencia revisada |
| --- | --- |
| Mantener una selección inmutable por pregunta e intento; rechazar modificación y eliminación | Aclaración posterior de Diana Ma Valencia: «No puede modificar nada si responde una vez ya»; sustituye la edición anterior de RF-10/RN-10/RN-11 |
| Guardar referencias, inicio y fin del intento | RF-12 y ER `intento`/`paso_simulacion` |
| Usar tiempo individual desde el servidor y conservar selecciones al vencer | RF-23; Software II, RNF-05 y RN-14 |
| Impedir edición después de finalizar o agotar el tiempo | RF-10/RF-23; UC-04 exige tiempo restante mayor que cero |
| Cierre repetido sin alterar fechas ni respuestas | UC-05: no duplicar efectos ante reintentos |
| No incluir puntajes, corrección ni justificaciones en estos objetos de resolución | RF-11/RF-14 |

El intento empieza `EN_CURSO`. `finalizar(reloj)` lo cierra como `FINALIZADO`
si todavía tiene tiempo. Al alcanzar el límite, `finalizar` o
`actualizar_vencimiento` lo cierran como `VENCIDO`, con `fin` igual al límite,
aunque la comprobación ocurra después. Antes del límite, actualizar el vencimiento
no cambia nada. Ninguna operación reabre un intento.

`FINALIZADO` solo expresa cierre voluntario: no significa que se respondieron
todas las decisiones. `VENCIDO` expresa agotamiento individual: no asigna nota,
no determina ausencia y no cierra la asignación académica. Son estados internos
de este incremento; su representación definitiva en el campo ER `estado` debe
coordinarse antes de la persistencia. El catálogo de estados de `Participacion`
todavía no se fija: se conserva el texto proporcionado, sin transiciones propias.

La edición comprueba también la hora aunque el estado siga `EN_CURSO`, por lo
que no necesita que un Worker haya marcado previamente el vencimiento.
`actualizar_vencimiento` es una operación invocable, no un temporizador autónomo.

## Integridad y tiempo

Se validan identificadores enteros positivos, duración positiva, fechas con zona,
referencias del paso al intento, selecciones y números de paso sin duplicados,
y coherencia temporal al reconstruir objetos. Se normalizan fechas a UTC.
El reloj no puede retroceder respecto al inicio o al último registro confirmado.
El instante exacto del límite ya no es editable, pues no queda tiempo restante.

`tiempo_maximo` es un dato recibido de Scheduling y conservado en este objeto
de dominio. `vence_en` se deriva de inicio más duración; no se añade una columna
al ER. Su recuperación estable tras reinicios necesita acordarse al integrar
persistencia, especialmente si la programación puede cambiar después del inicio.

Los pasos se mantienen como selecciones actuales: modificar conserva `id_paso`
y `numero_paso`, sustituye la opción/reflexión y actualiza la hora del registro.
El número de paso indica orden local de primera selección, sin decidir el recorrido.
En este incremento `tiempo_segundos` mide segundos enteros desde el inicio hasta
el último guardado, calculados por el servidor. Esta interpretación técnica debe
confirmarse al mapear el campo homónimo del ER; no es una regla de calificación.
Los identificadores de pasos se reciben del llamador; este dominio no genera IDs.

## Integraciones y decisiones pendientes

- **Cases:** conectar validación de opciones, consulta del recorrido aplicable y
  autorización de cambios que conserven los demás pasos. Acordar qué ocurre con
  respuestas posteriores cuando una opción cambia de escena. No se eliminan ni
  invalidan otras selecciones automáticamente; sin política resuelta se rechaza
  la operación. Sigue pendiente el mapeo de decisiones a niveles/puntajes.
- **Identity:** conectar las autorizaciones de inicio y acceso, comprobar titularidad,
  consentimiento y pertenencia del permiso extraordinario. Los IDs por sí solos
  no acreditan ninguna autorización. No se implementa autenticación alternativa.
- **Scheduling:** conectar condiciones reales de asignación y membresía, estado,
  ventana autorizada y duración. Acordar control de cantidad de intentos y consumo
  de permisos extraordinarios. No se inventa el umbral de ingreso tardío ni se
  implementan convocatorias o cierre general de asignaciones.
- **Historial:** la selección actual editable no es un historial completo de cambios.
  Si se requiere auditoría de cada edición o revisitas del recorrido, acordar cómo
  persistirla sin inventar nuevas tablas ni sobrescribir resultados académicos.
- **Evaluación:** pendientes fórmula parcial, redondeo, consolidación de intentos,
  resultados y conservación de la versión de la rúbrica. El motor admite cálculos
  con parámetros explícitos, pero todavía no calcula notas oficiales de SPS.
- **Persistencia:** pendientes repositorios, transacción, restricciones y bloqueos
  para evitar carreras entre guardado y cierre. La idempotencia comprobada aquí
  es local al objeto; no demuestra idempotencia de peticiones concurrentes.

`ParticipacionFacade` coordina los ports y estas operaciones sin delegar al
navegador el reloj ni la autorización. Las futuras estrategias de evaluación
consumirán las selecciones conservadas sin introducir fórmulas en `Intento`.

## Segundo incremento: flujo de Application

### 1. Inicio

`iniciar_intento` recibe estudiante, participación existente, consentimiento y
permiso extraordinario opcional. La unidad de trabajo recupera la participación;
Identity autoriza acceso e inicio. Si existe un intento en curso no se duplica:
hay que recuperarlo o procesar su vencimiento. Scheduling proporciona duración
y autoriza el número siguiente según las condiciones académicas aprobadas.
El número secuencial no constituye por sí solo autorización de repetición.
El dominio obtiene el inicio del reloj inyectado. Se agrega el objeto y se
confirma antes de devolver su resumen. No se crean convocatorias ni se asigna
un estado nuevo a la participación.

### 2. Selección o modificación

`registrar_decision` y `modificar_decision` recuperan el intento y autorizan su
titularidad. El dominio comprueba vencimiento; si ya venció, se conserva ese
cierre antes de comunicar `IntentoNoEditable`, sin guardar la selección pedida.
Si está cerrado, no se llama a Cases ni se generan nuevas escrituras.

Scheduling valida que la asignación todavía permita editar. Cases valida
pertenencia de opción/decisión y autoriza explícitamente conservar los demás
pasos tras el cambio propuesto. Una política de ramificación pendiente bloquea
el cambio; no se decide cómo borrar o invalidar respuestas.

Después, el dominio vuelve a comprobar el reloj al generar el intento actualizado.
Esto rechaza una selección si el tiempo se agotó mientras respondían las
dependencias. En ese caso no se guarda la selección; el vencimiento se puede
conservar con `procesar_vencimiento` en una llamada posterior.
El repositorio guarda el nuevo objeto con el estado anterior esperado, nunca
el objeto original inmutable. Los IDs de nuevos pasos los proporciona el repositorio.

### 3. Progreso

`consultar_progreso` autoriza al solicitante, comprueba el vencimiento y solicita
a Cases el recorrido a partir de las selecciones actuales. Devuelve decisiones
aplicables, selecciones y pendientes. `total_aplicable` es `None` si Cases no
conoce aún el total del recorrido; no hay un porcentaje deducido de todo el caso.
Si la ruta excluye respuestas conservadas, se comunica `ReglaPendiente` en lugar
de ocultarlas o decidir su tratamiento. No se devuelven campos de evaluación.
Una consulta que detecta vencimiento lo guarda solo si completa correctamente
la operación; un fallo de Cases deja la transacción sin confirmar.

### 4. Cierre

`finalizar` cierra voluntariamente, o por vencimiento si ya no queda tiempo.
`procesar_vencimiento` solo cierra si se alcanzó el límite individual. Ambas
operaciones exigen autorización de acceso, conservan todas las selecciones y
delegan estado/fechas al dominio. No requieren reautorizar el ingreso ni consultar
Cases para cerrar, de modo que una asignación cerrada no impide conservar el
cierre individual. El proceso invocable de vencimiento aún requiere un usuario
autorizado; no añade una vía privilegiada ni un Worker.

Si el intento ya estaba cerrado, no hay nueva escritura ni commit. Este cierre
no clasifica el resultado como COMPLETO/INCOMPLETO/AUSENTE y no calcula notas.
El tercer incremento añade una evaluación explícita posterior al cierre
confirmado; no modifica esa operación ni la hace depender de una rúbrica disponible.

## Ampliaciones mínimas de puertos en esta entrega

Se mantienen las firmas anteriores. Se añaden contratos de consumo propuestos,
sin editar los módulos de los compañeros ni afirmar que ya los implementan:

| Puerto | Métodos nuevos | Motivo |
| --- | --- | --- |
| Cases | `obtener_recorrido`, `validar_cambio_conservando_pasos` | Progreso contextual y rechazo explícito de cambios sin política de ramificación |
| Scheduling | `autorizar_nuevo_intento`, `validar_edicion`, `obtener_id_caso` | Separar ingreso, edición y consulta del caso después del cierre |
| Persistencia local | `RepositorioParticipacion` | Leer y guardar agregados inmutables, generar IDs y comprobar estado esperado |
| Transacción local | `UnidadTrabajo` y su fábrica | Confirmar una operación completa o descartar cambios |

No se amplía Identity: se consumen `autorizar_acceso` y `autorizar_inicio`.
El adaptador de Scheduling deberá resolver cómo coordina cupos y consumo de
permisos extraordinarios con Identity, sin delegar esa política a la fachada.
`obtener_id_caso` consulta el vínculo académico sin modificar la duración ya
conservada en el intento. La estabilidad/versionado de ese vínculo sigue pendiente.

## Transacciones, errores y límites de lo probado

Cada llamada abre una unidad de trabajo nueva. Un guardado solo se confirma con
`commit`; las excepciones de dependencias o almacenamiento se propagan y los
cambios locales sin confirmar se descartan. No se devuelven éxitos ficticios ni
se reemplazan errores externos por autorizaciones permisivas. Los adaptadores
deben implementar el contrato de commit atómico y propagar fallos.

La implementación real deberá serializar el inicio sobre la participación y las
ediciones/cierres sobre el intento, con bloqueos o garantía equivalente. Guardar
recibe el agregado previo esperado para impedir sobrescrituras obsoletas. Esto
no obliga a añadir columnas al ER: el mecanismo SQL se acordará posteriormente.
Las pruebas comprueban estas obligaciones mediante una unidad de trabajo falsa
con copias y confirmación; no demuestran concurrencia ni integración PostgreSQL.

No hay dependencias por defecto ni composición con fakes fuera de pruebas. Antes
de exponer HTTP deberán conectarse los adaptadores reales y la identidad validada
por el servidor. Los ejemplos de permisos, rutas y cupos de los fakes son datos
de prueba y no sustituyen las políticas académicas oficiales.

## Pruebas

Desde la raíz del repositorio, con el entorno y el extra `dev` instalados:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/app/modules/participation/tests backend/tests -c backend/pyproject.toml -q
```

Se incluyen explícitamente las dos ubicaciones porque la configuración global
actual solo descubre `backend/tests`. No se cambia esa configuración en esta etapa.
Las pruebas verifican estados, registro/modificación, límite exacto de tiempo,
conservación de respuestas, cierre repetido y reconstrucción de datos inválidos.
Los ejemplos numéricos de IDs y tiempos son datos de prueba, no políticas académicas.

## Tercer incremento: Strategy y evaluación

La explicación, ejemplos matemáticos, contratos y límites están en
[EVALUACION.md](EVALUACION.md). La fachada admite un `ServicioEvaluacion` explícito;
sin configurarlo rechaza las nuevas operaciones con `ReglaPendiente`.

Flujo: `finalizar`/`procesar_vencimiento` → `evaluar_intento` →
`consultar_evaluacion`. La evaluación devuelve una confirmación sin nota; la
lectura académica solo recupera un resultado previamente persistido y confirmado.
Un fallo de cálculo o almacenamiento no revierte el cierre ni genera un segundo
resultado definitivo. Una política pendiente no se guarda como nota oficial.

`evaluar_ausencia` requiere participación convocada, confirmación de condiciones
de cierre y ningún intento. Conserva ceros por decisión sin crear intentos; su
persistencia definitiva está bloqueada hasta acordar el detalle ausente en el ER.

No hay adaptadores reales ni políticas académicas oficiales configuradas.

## Cuarto incremento: API y contratos HTTP

El contrato para revisión del equipo está en [api/HTTP.md](api/HTTP.md).
`api/router.py`, `schemas.py`, `dependencies.py`, `mappers.py` y `errors.py`
preparan rutas provisionales, validación Pydantic, respuestas sin filtraciones y
traducción local de errores. Las dependencias están cerradas por defecto y los
únicos overrides están en `tests/test_api.py`, sobre una aplicación aislada.

Se añade `EvaluacionNoConfirmada` en Application, compatible con su excepción base,
para distinguir una evaluación pendiente de un recurso inexistente. Se lanza
solo tras verificar autorización y cierre. No cambia el cálculo ni la persistencia.

No se crea otro sistema de autenticación ni se acepta `student_id` del cliente.
No se calculan notas en GET ni se expone una evaluación antes de su confirmación.
El contrato sigue pendiente de aprobación de rutas y conexión real con el equipo.

## Quinto incremento: persistencia independiente y propuesta de mapeo

La inspección, claves foráneas, restricciones propuestas, código disponible y
limitaciones están en [infrastructure/PERSISTENCIA.md](infrastructure/PERSISTENCIA.md).
No aparecieron modelos ORM ni migraciones compartidas; Alembic sigue sin revisiones.

Se preparan `UnidadTrabajoSQLAlchemy`, `LecturasParticipacionSQLAlchemy`, codecs
temporales/Decimal y `MapeoPersistenciaPendiente`. No se crean tablas ni otra Base.
Las consultas reciben tablas existentes y mapeos explícitos; no implementan aún
el puerto completo de escritura ni reconstruyen resultados académicos incompletos.

El router sigue sin registrar y sus dependencias cerradas. Las pruebas PostgreSQL
son opt-in y no crean tablas; sin conexión configurada quedan omitidas. Compilar
SQL y usar Session sin conexión no equivale a verificar persistencia o concurrencia.

## Evidencia de pruebas funcionales HTTP

[QA_ENDPOINTS.md](QA_ENDPOINTS.md) registra la matriz ejecutada de los siete
endpoints, el escenario completo, el defecto corregido, las omisiones y los
comandos de reproducción. Se genera desde JUnit mediante
`tests/generate_qa_report.py`. El entorno aislado está en `tests/http_support.py`;
no hay fakes conectados a la aplicación principal.

Los errores inesperados del router ya no se ocultan con una captura general:
TestClient los propaga y el límite HTTP sin debug conserva un 500 genérico.
Se mantienen todas las pruebas anteriores y se amplía la comprobación de estado,
repositorios, rollback, seguridad y estrategias reales.
