# ADR: identidad académica y acceso a convocatorias

> **Login integrado posteriormente:** búsqueda de cuenta, validador Scheduling y
> contexto de convocatoria ya tienen implementación y pruebas SQL/JWT; el ingreso
> temporal sigue cerrado. Estado vigente y reproducción del laboratorio:
> [LOGIN_ESTUDIANTIL_SCHEDULING.md](backend/app/modules/identity/LOGIN_ESTUDIANTIL_SCHEDULING.md).

> **Evolución autorizada en el incremento del resolver persistente:** el usuario
> pidió no imponer unicidad por usuario/sistema sin evidencia. El esquema implementado
> permite varios UUID por cuenta/sistema y usa PK(sistema,id_academico), con FK a
> usuario; resolver sigue exigiendo una única correspondencia. Esto sustituye la
> PK(id_usuario,sistema) y el límite 0..1 propuestos en los apartados históricos
> siguientes; no afirma una cardinalidad de negocio nueva. Estado, pruebas y límites:
> [PERSISTENCIA_IDENTIDAD_ACADEMICA.md](backend/app/modules/identity/PERSISTENCIA_IDENTIDAD_ACADEMICA.md).

**Estado: propuesta para aprobación; no autoriza despliegue ni cambios de datos.**
Fecha: 31 de octubre de 2026. Repositorio proyecto-nuclear-2.
Rama comprobada: feature/integracion-backend. HEAD: ee025d2.
Las tres fases locales sin commit forman parte del estado auditado.

## 1. Decisión recomendada y alcance

**Recomiendo A: asociación persistente de cuenta Identity con identidad personal
UUID por sistema**, con cero o una asociación por usuario y sistema. Esta última
es una **restricción de diseño propuesta**, no una cardinalidad demostrada por los
requisitos ni por datos históricos. Su aprobación permite implementar el registro;
su población exige verificar la titularidad de cada UUID. Las cuentas ambiguas
permanecerán sin asociación y sin acceso académico.

Mantener las membresías, convocatorias, sesiones, casos e intentos como entidades
separadas. No adoptar ahora un UUID global ni introducir contexto institucional
en la identidad sin una necesidad demostrada. No convertir INTEGER a UUID,
comparar IDs por su forma ni vincular personas automáticamente por correo/nombre.

La recomendación resuelve el diseño técnico preferido, sin presentar como hechos
las decisiones de negocio pendientes del apartado 10. Después de aprobar este ADR
se puede implementar el registro vacío y sus pruebas, sin activar login o ingreso
hasta completar sus contratos. No es necesario integrar Participation para ello.

## 2. Fuentes y hechos verificables

### 2.1 Código, contratos y esquema efectivos

Todos los enlaces son relativos a la raíz del repositorio.

| Evidencia | Clase/función y conclusión comprobada |
| --- | --- |
| [Cuenta y roles](backend/app/modules/identity/infrastructure/models.py) | UsuarioORM tiene PK INTEGER autoincremental, correo UNIQUE y una FK id_rol NOT NULL. No hay UUID personal ni tabla de mapeo. |
| [Dominio Identity](backend/app/modules/identity/domain/entities.py) | ContextoAcceso.id_usuario es str opaco; roles es frozenset; AccesoConvocatoria contiene id_usuario e id_convocatoria. El dominio admite varios roles, el ORM actual conserva uno. |
| [Repositorio Identity](backend/app/modules/identity/infrastructure/repositories.py) | id_entero valida la cadena decimal; obtener consulta usuario/rol/permisos y devuelve la PK como str. No existe búsqueda de cuenta por correo para el adaptador de login. |
| [Autenticación](backend/app/modules/identity/application/authentication.py) | ServicioAutenticacion.autenticar_estudiante valida dominio y pareja correo/código, llama ValidadorConvocatoria y después verifica cuenta, actividad, rol y correo antes de emitir JWT. |
| [Puertos](backend/app/modules/identity/application/ports.py) | ValidadorConvocatoria.validar(correo,codigo) devuelve AccesoConvocatoria o None. No implementa todavía la consulta académica. |
| [Composición HTTP](backend/app/modules/identity/api/dependencies.py) | construir_validador_convocatoria lanza IntegracionPendiente. obtener_usuario_actual verifica JWT, recarga usuario y exige presencia de convocatoria para estudiantes; NO consulta la convocatoria ni comprueba su retiro. |
| [JWT](backend/app/modules/identity/infrastructure/security.py) | TokensJWT firma HS256, exige issuer/audience/tiempos/tipo; sub viene del ID de usuario. convocatoria_id es una cadena validada sintácticamente, no un UUID resuelto. |
| [Resolver](backend/app/modules/identity/application/academic_identity.py) | ResolverIdentidadAcademica exige una proyección coherente, única y con UUID no nulo, para usuario y SistemaAcademico. La unicidad inversa es obligación del adaptador pendiente. |
| [Fábrica del resolver](backend/app/modules/identity/api/academic_dependencies.py) | construir_resolver_academico está cerrado. Las dependencias docente/estudiante son reales, pero solo hay correspondencias inyectadas en pruebas. |
| [Dominio Cases](backend/app/modules/cases/domain/entities/caso.py) | VersionCaso separa caso_id e id de versión; _nuevo_id genera UUID4 para entidades del caso. docente_creador_id se recibe, no se genera como identidad personal. |
| [ORM Cases](backend/app/modules/cases/infrastructure/models/caso.py) | CasoModel.docente_creador_id es UUID sin FK a usuario. VersionCasoModel.caso_id sí es FK a caso. |
| [Servicio Cases](backend/app/modules/cases/application/services/caso_service.py) y [repositorio](backend/app/modules/cases/infrastructure/repositories/caso_repository.py) | Operaciones reciben UUID docente y filtran propiedad del caso. No demuestran vínculo con Identity. |
| [ORM Scheduling](backend/app/modules/scheduling/infrastructure/models.py) | UUID de docente, estudiante y destinatario sin FK personal. ConvocatoriaModel tiene PK propia, FK a sesión y UNIQUE(sesion_id,estudiante_id). |
| [Generador de PK](backend/app/modules/cases/infrastructure/models/mixins.py) | uuid_pk usa UUID4 en la aplicación, también para las entidades Scheduling. No genera usuarios. |
| [Convocar](backend/app/modules/scheduling/application/crear_convocatoria.py) | crear_convocatoria recibe UUID estudiante, genera código aleatorio y guarda SHA-256; no consulta usuario Identity. |
| [Notificar](backend/app/modules/scheduling/application/crear_notificacion.py) | crear_notificacion compara destinatario con convocatoria.estudiante_id cuando hay convocatoria; no resuelve cuentas. |
| [Ingreso](backend/app/modules/scheduling/application/validar_ingreso.py) | validar_ingreso comprueba convocatoria/titular/código/estado/horario. Recibe tolerancia_minutos y calcula el límite con ella. |
| [Router Scheduling](backend/app/modules/scheduling/api/router.py) y [schemas](backend/app/modules/scheduling/api/schemas.py) | Identidades docentes/estudiantiles proceden del servidor; los IDs HTTP se contrastan. Sin embargo, tolerancia_minutos todavía procede del cuerpo, con default 15 y sin máximo. |
| [Base integrada](backend/app/db/models.py) y [Alembic](backend/alembic/env.py) | Una Base y 18 tablas registradas. Alembic acepta una conexión inyectada, útil para pruebas aisladas sin usar la configuración del equipo. |

Head leído mediante ScriptDirectory, sin ejecutar migraciones: **6867083574f6**.
Une 20261028_merge_access_cases y 36b9e0790539. Las raíces son
20261028_identity_access y c27a750108db. No hay identidad_academica en ese historial.

### 2.2 Requisitos y modelos de referencia: no confundirlos con el esquema vigente

- [DBML local](backend/app/modules/identity/reference/sps.dbml), bloques usuario,
  grupo_academico, grupo_estudiante, asignacion_caso y participacion: distingue
  cuenta, membresía y asignación. UNIQUE(id_grupo,id_estudiante) permite varias
  membresías del mismo usuario en grupos diferentes. No incluye convocatoria UUID.
- [Agile Inception](_referencias_locales/Agile%20Inception%20SPS.pdf), pp. 4, 6, 8-9:
  una persona puede asumir funciones distintas; acceso por correo/código y ámbito;
  RF-22 y vigencia/reutilización de códigos tienen precisiones pendientes.
- [Análisis de Sistemas](<_referencias_locales/Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf>),
  pp. 3-5: distingue autenticación y autorización; convocatoria vinculada a estudiante;
  el umbral tardío requiere acuerdo académico antes de implementarse.
- [Ingeniería de Software II](<_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf>),
  pp. 4, 7, 11, 27: RF-01, RN-08 y UC-03 vinculan código, estudiante, sesión y acceso;
  RN-20 mantiene pendiente la fórmula del umbral; el modelo propuesto incluye
  umbral_inicio y membresías de roles diferentes del ORM actual.

Las diferencias son materiales: el DBML tiene IDs INTEGER y participación por
asignación/membresía; Cases/Scheduling integrados usan UUID y convocatoria por
sesión/estudiante. No son dos nombres para un esquema idéntico. Un modelo de
referencia no demuestra una FK inexistente ni autoriza fusionar tablas.

No se inspeccionaron datos del equipo o de producción. No hay evidencia de
titularidad histórica ni cantidad de alias. Las fixtures que reutilizan un UUID
docente en caso y sesión demuestran compatibilidad de tipos, no origen común.

## 3. Tabla de identificadores y cardinalidades

En esta tabla, «demostrada» significa estructura efectiva de código/ORM; «referencia»
significa DBML/requisitos sin integración; «propuesta» no describe datos existentes.

| Identificador | Representa / tipo | Quién lo genera o entrega | Relaciones y cardinalidad |
| --- | --- | --- | --- |
| usuario.id_usuario / ContextoAcceso.id_usuario / JWT sub | Cuenta INTEGER / representación str | BD al alta Identity; JWT copia ID del repositorio | Demostrada: una PK por cuenta; un rol físico por usuario; correo único exacto. No demuestra una cuenta por persona institucional. |
| rol.id_rol y permiso.id_permiso | Catálogos INTEGER | BD / altas de catálogo | Demostrada: roles-permisos M:N mediante rol_permiso; no son identidad personal. |
| caso.docente_creador_id | Referencia personal docente UUID de Cases | Antes cabecera; ahora resolver cerrado | Demostrada: cada caso guarda un UUID; varios casos pueden compartirlo. Cuenta Identity ↔ UUID: no demostrada. |
| sesion_programada.docente_id | Responsable docente UUID de Scheduling | Resolver cerrado, pasado a programar_sesion | Demostrada: un responsable por sesión, potencialmente muchas sesiones por UUID. No impone igualdad con creador del caso. |
| convocatoria.estudiante_id | Referencia estudiantil UUID de Scheduling | Cuerpo de convocatoria, recibido por servicio; falta validar su registro personal | Demostrada: estudiante puede aparecer en varias sesiones; una convocatoria base por par sesión/UUID. No hay entidad personal que pruebe su significado global. |
| notificacion.destinatario_id | Destinatario UUID de Scheduling | Copiado del estudiante convocado o recibido por servicio de notificación | Demostrada: muchas notificaciones por UUID; FK opcional a convocatoria, no a cuenta. |
| grupo_estudiante.id_grupo_estudiante | Membresía INTEGER | DBML propone incremento | Referencia: grupo ↔ usuario M:N, un par grupo/estudiante único. No equivale a estudiante_id UUID. |
| grupo_academico.id_grupo | Grupo/periodo INTEGER | DBML propone incremento | Referencia: un profesor y muchas membresías/asignaciones. No equivale automáticamente a espacio_academico UUID. |
| espacio_academico.id | Catálogo académico UUID | uuid_pk al insertar | Demostrada: una sesión referencia un espacio, un espacio admite muchas sesiones. No registra membresía personal. |
| caso.id / VersionCaso.caso_id | Caso lógico UUID | Dominio _nuevo_id o default ORM UUID4 | Demostrada: un caso tiene varias versiones. No es UUID personal. |
| version_caso.id / VersionCaso.id | Versión de contenido UUID | Dominio/default ORM UUID4 | Demostrada: UNIQUE(caso_id,numero); muchas sesiones pueden referenciar una versión. |
| escenario/pregunta/opcion/rubrica/criterio/nivel IDs | Contenido UUID | Dominio/default ORM UUID4 | Demostrada: FK a sus agregados y orden/relaciones; no identifican personas. |
| sesion_programada.id | Ejecución programada UUID | Default ORM UUID4 | Demostrada: una versión, un espacio, un docente; varias convocatorias. |
| convocatoria.id | Vínculo individual estudiante/sesión UUID | Default ORM UUID4 al flush | Demostrada: PK propia distinta de estudiante_id; UNIQUE(sesion_id,estudiante_id). |
| AccesoConvocatoria.id_convocatoria / claim convocatoria_id | Contexto de acceso str | ValidadorConvocatoria debe entregarlo; hoy solo dobles de prueba | Hoy opaco y sin asociación productiva. Se propone que sea la representación canónica de convocatoria.id de Scheduling, nunca sesión/asignación/membresía. |
| notificacion.id / evento_auditoria.id | Aviso / evento UUID | Default ORM UUID4 | Demostrada: aviso y evento son entidades, no usuarios ni códigos de autorización. |
| JWT jti | Identificador del token | TokensJWT.emitir, UUID4 | Identifica una emisión; no identifica persona, sesión académica ni convocatoria. |
| asignacion_caso.id_asignacion | Programación de caso/grupo INTEGER | Referencia DBML; no productor integrado | No equiparar con sesion_programada.id ni convocatoria.id. |
| Participacion.id_participacion | Agregado INTEGER propio de Participation | Provisión externa pendiente; Facade exige que exista | Dominio exige asignación y membresía; DBML propone UNIQUE(asignación,membresía). No es ejecución UUID del PDF. |
| Intento.id_intento / PasoSimulacion.id_paso | Intento / selección INTEGER | Puertos nuevo_id_intento/nuevo_id_paso; producción pendiente | Dominio: varios intentos por participación y pasos por intento; IDs no son usuario, convocatoria o versión Cases UUID. |
| consentimiento y permisos extraordinarios IDs | Evidencia/permiso INTEGER | Identity/DBML, parte académica pendiente | No identifican personas; referencian cuentas/participaciones. No resolverlos como UUID personales. |
| identidad_academica.(id_usuario,sistema) | Asociación personal por módulo | Alta administrativa verificada, propuesta | Propuesta: usuario → 0..1 UUID por sistema; UUID → una cuenta en ese sistema. No inferida de requisitos. |

Cambiar de rol no debe cambiar la identidad propuesta. El soporte simultáneo de
roles del dominio frente al rol único del ORM es otro cambio de autorización;
no se implementará como parte del mapeo ni mediante dos cuentas inventadas.

## 4. Alternativas y decisión

| Alternativa | Ventajas | Incompatibilidades / coste | Migraciones necesarias y riesgos |
| --- | --- | --- | --- |
| **A. Por usuario y sistema, preferida** | Conserva INTEGER de Identity y UUID de cada módulo; satisface el puerto actual; permite valores iguales o distintos por sistema sin deducir equivalencias; despliegue aditivo | Añade una resolución y no convierte referencias existentes en FK personales por sí sola; 0..1 por sistema debe aprobarse; alias históricos requieren reconciliación | Nueva tabla de asociación, PK/FK/UNIQUE/CHECK; ninguna reescritura académica inicial. Vínculo equivocado transfiere ámbito: el alta necesita evidencia y auditoría. |
| B. UUID personal global | Una referencia común y menos resoluciones futuras | No existe registro global; no consta que los UUID docentes de ambos módulos coincidan ni que docente y estudiante usen el mismo origen | Nuevo registro global o columna en usuario, reconciliar y migrar referencias distintas en todos los módulos. Alto riesgo de unir personas o romper históricos; no elegir un UUID por coincidencia o precedencia. |
| C. Asociación por membresía/institución/contexto | Correcta si un ID externo identifica membresía o el sistema es multitenant; respeta la distinción del DBML | Los UUID actuales no se han demostrado IDs de membresía; no hay institución/tenant integrado ni contexto en el puerto de resolución actual | Integrar membresías y su FK/contexto; PK/UNIQUE contextual; cambiar puertos, JWT/recursos y consultas de ámbito. Usar un contexto aportado por cliente sin verificación sería una escalada de privilegios. |

Elegir **A**, manteniendo la membresía como autorización contextual separada.
No se justifica incorporar institución o grupo a todas las resoluciones actuales
solo porque exista una membresía en el modelo de referencia. Si el inventario
demuestra que UUID identifica membresía, detener la importación de esos registros
y revisar este ADR hacia C; no modificar silenciosamente el significado de A.

No se requiere que toda cuenta tenga asociaciones ni que todo UUID histórico se
importe de inmediato. Se puede habilitar una cuenta verificada y mantener las
demás cerradas. Esto permite implementar sin inventar la reconciliación pendiente.

## 5. Modelo propuesto, contrato e integridad

### 5.1 Tabla mínima `identidad_academica`, aún no creada

| Campo | Tipo / restricción propuesta |
| --- | --- |
| id_usuario | INTEGER NOT NULL, FK usuario.id_usuario, sin borrado en cascada |
| sistema | VARCHAR(16) NOT NULL; CHECK valores CASES o SCHEDULING |
| id_academico | UUID NOT NULL; CHECK distinto del UUID nulo; **sin default generador** |
| PK | (id_usuario,sistema) |
| UNIQUE | (sistema,id_academico) |

No añadir FK a una tabla docente/estudiante inexistente. Tampoco añadir aún FK
desde caso/sesión/convocatoria: necesitan reconciliar huérfanos y una referencia
que incluya el sistema correcto. Sin esas FK, el mapeo **no demuestra** integridad
referencial de todos los registros históricos; sí permite resolver los verificados.

**Propietario:** Identity mantiene la relación entre cuenta y referencia personal;
Cases y Scheduling mantienen recursos, membresías y permisos de ámbito. El adaptador
de integración conecta contratos de lectura, no incorpora ORM externo al dominio.
Solo un proceso administrativo autorizado puede insertar asociaciones, con evidencia
de titularidad. No habrá endpoint público de alta, escritura en login ni upsert.

### 5.2 Resolución y escritura

Mantener `ConsultaVinculosAcademicos.obtener(id_usuario,sistema)` y
`ResolverIdentidadAcademica.resolver(...)`. La consulta SQL devuelve proyecciones
inmutables; el dominio no recibe modelos ORM. El ID de cuenta procede de Identity,
nunca de cabeceras/cuerpo como prueba de identidad.

| Caso | Resultado |
| --- | --- |
| Una asociación coherente y con unicidad inversa | UUID persistido exacto, sin generación ni conversión |
| Ninguna | AccesoDenegado, HTTP 403 en recurso autenticado |
| Varias, sistema/usuario erróneo, UUID nulo o titularidad inversa inconsistente | IntegracionPendiente, HTTP 503; no seleccionar la primera |
| Fallo SQL conocido | IntegracionPendiente sin detalles privados; rollback/cierre de la Session |
| Fallo inesperado | Propagar para observabilidad; respuesta genérica 500, nunca apertura |

El repositorio usará `id_entero` para convertir la representación canónica de la
PK propia de Identity, lo que NO es una equivalencia INTEGER/UUID. Validará sistema
antes de consultar y recuperará todas las filas relevantes, sin LIMIT 1 que oculte
ambigüedad. Las restricciones de BD deben impedir colisiones en ambas direcciones;
una comprobación inversa defensiva no sustituye UNIQUE.

Para altas, añadir un servicio interno `registrar_vinculo_verificado`: insertar
UUID histórico acreditado; rechazar reasignación. Repetir una importación con el
mismo par/UUID puede informar «ya existe» tras releer; una discrepancia es conflicto,
no actualización. No hacer commit en el repositorio; usar UoW/Session común.

Para una identidad **nueva**, proponer UUID4 generado una sola vez en un alta
administrativa explícita, persistido y confirmado antes de entregarse al módulo.
No generarlo durante resolución ni como fallback. La tabla no decide ese alta con
un default: distinguir así importar un UUID histórico y registrar uno nuevo.

### 5.3 Identidades históricas

1. Inventariar UUID distintos por columna, cuenta y evidencia de titularidad,
   usando exportación autorizada o copia anonimizada; no consultar producción aquí.
2. No unir UUID entre sistemas por igualdad de valor, correo o nombre. No confundir
   una convocatoria o membresía con un usuario.
3. Importar solo correspondencias verificadas y unívocas con registro de revisión.
   Sin evidencia: sin vínculo; no cuenta o UUID sustituto.
4. Varios UUID de un sistema para la misma cuenta: bloquear esa cuenta para ese
   sistema hasta resolver alias/migración específica. A no representa varios alias;
   cambiar una fila no traslada correctamente sus recursos ni preserva su historia.
5. Mantener asociaciones estables. Una rectificación exige análisis de referencias,
   responsable y auditoría; no debe haber un UPDATE administrativo genérico.

## 6. Login y convocatorias: flujo actual y flujo ejecutable propuesto

### 6.1 Estado actual

`POST /api/v1/identity/auth/estudiantes` es público porque es el intercambio inicial
de credenciales. `SolicitudLogin` acepta correo y código, **no** un id_usuario.
ServicioAutenticacion normaliza correo/dominio y llama al puerto de convocatoria.
La fábrica de ese puerto lanza IntegracionPendiente, por lo que el login real
no está integrado. Las pruebas de emisión usan validadores simulados.

`TokensJWT.emitir` copia `AccesoConvocatoria.id_convocatoria` al claim
`convocatoria_id`; no consulta Scheduling ni obtiene ese ID del cuerpo HTTP.
Hoy el valor depende de un adaptador inexistente: las cadenas de las pruebas no
demuestran que sea convocatoria.id. La verificación JWT comprueba forma/firma/tiempo,
pero no actividad de la convocatoria ni su relación actual con sub.

Scheduling exige JWT y resuelve el estudiante en `/validar-ingreso`. Después compara
ID solicitado con ID resuelto y comprueba convocatoria.estudiante_id y código.
Sin embargo, **no contrasta** esa convocatoria con la del claim: un token de una
convocatoria puede presentar otra del mismo estudiante si conoce su código. Esto
no demuestra suplantación de otra persona, pero deja sin definir el alcance del token.

### 6.2 Decisión de contrato propuesta para aprobación

- `sub` seguirá siendo la cuenta Identity, no el UUID académico.
- `convocatoria_id` estudiantil será **str(UUID canónico de ConvocatoriaModel.id)**.
  No usar id_sesion, id_asignacion, código, membresía ni UUID personal en ese claim.
- El token aporta contexto para operaciones sobre esa convocatoria; no hace vigente
  una convocatoria retirada. Las consultas de cuenta, como notificaciones propias,
  siguen comprobando titularidad de usuario, sin exigir una sesión en curso solo
  para leer avisos. No crear un control global que impida leer resultados tras cierre.
- El ingreso académico debe comparar convocatoria HTTP con la validada del JWT,
  comprobar propiedad y estado actuales y aplicar la política temporal del servidor.
  Distinta convocatoria: denegar; para cambiar de contexto, autenticarse con su código.
- Durante la transición, tokens antiguos con contexto opaco/no canónico no deben
  convertirse por suposición. Rechazar ese contexto en el acceso académico y pedir
  nueva autenticación. No es necesario cambiar la identidad de usuario ni crear JWT alternativo.

Esto es una propuesta nueva y explícita; todavía no está implementada ni probada
con Scheduling real. La forma en que se permite autenticar antes/después del horario
para consultar avisos requiere aprobar la separación de identidad y permiso de ingreso.

### 6.3 Adaptadores y consultas que faltan

Proponer `identity/infrastructure/scheduling_access.py::ValidadorConvocatoriaScheduling`
como adaptador del puerto existente, con servicios de lectura inyectados. No importar
ORM Scheduling desde el dominio Identity ni llamar al endpoint protegido por HTTP.

Algoritmo concreto para `validar(correo,codigo)`:

1. Obtener una cuenta existente por correo normalizado mediante una consulta de
   Identity nueva. El puerto actual RepositorioUsuarios no ofrece esa búsqueda:
   añadir `ConsultaCuentaPorCorreo.obtener_unica(correo) -> ContextoAcceso | None`
   y su implementación en infraestructura. Correo selecciona una cuenta; **no crea
   la asociación**. La credencial es la pareja correo/código de la convocatoria.
2. Detectar correos que colisionan al normalizar. El UNIQUE actual es sobre correo
   almacenado; no garantiza unicidad por casefold. Nunca seleccionar el primer usuario
   con LOWER(correo). Normalizar consistentemente y rechazar ambigüedad; revisar
   esas cuentas antes de plantear un índice normalizado en otra migración.
3. Exigir cuenta activa y rol ESTUDIANTE; resolver su UUID SCHEDULING desde el registro.
   Sin vínculo o cuenta: rechazo genérico; fallo de configuración/SQL: 503 sin secreto.
4. Consultar convocatorias de ese UUID y el hash del código usando un puerto de lectura
   de Scheduling. Su esquema actual guarda SHA-256 de un código aleatorio; reutilizar
   el algoritmo existente, no introducir ni registrar el código en claro.
5. Exigir un único candidato y estado ACTIVA; verificar el hash en el servicio.
   UNIQUE(sesion_id,estudiante_id) **no** prueba unicidad del código entre sesiones.
   Cero candidatos: rechazo; varios: error de integridad, nunca elegir el primero.
6. Cargar sesión asociada y aplicar las condiciones de autenticación que se aprueben.
   Para permiso de inicio, consultar separadamente el servicio/política de ingreso;
   autenticación no crea Participation ni elimina controles temporales.
7. Devolver `AccesoConvocatoria(str(usuario.id_usuario), str(convocatoria.id))`.
   ServicioAutenticacion conserva su comprobación final de cuenta/correo/rol y solo
   entonces TokensJWT emite el token con sub y contexto verificados.

En el adaptador, AccesoDenegado del mapeo se traduce a fallo genérico de credenciales
para el login público, sin revelar existencia de cuenta/vínculo. Los recursos ya
autenticados mantienen 403. Los errores operativos no se disfrazan de éxito o credenciales.

Definir en Scheduling una proyección de acceso y consulta por
`(id_estudiante_academico, hash_codigo)`; incluir convocatoria, propietario, sesión
y estado. Añadir un servicio de comprobación actual para `(usuario, convocatoria)`.
Usar Session por operación y lecturas coherentes; ningún commit de escritura ni
consumo de código se presupone. Si se aprueba código de un solo uso, requerirá un
flujo transaccional adicional, no una lectura que lo marque usado implícitamente.

Revalidar retiro y estado en cada acceso académico, no confiar solo en que el JWT
se emitió cuando la convocatoria era válida. Una carrera entre emisión y retiro
no debe permitir el ingreso posterior. Para una futura operación que realmente
inicie participación, esa comprobación deberá ser atómica con la escritura, fuera
del alcance actual. No introducir dependencias circulares: login público llama a
contratos internos, nunca a `/scheduling/validar-ingreso` que requiere un JWT previo.

Dependencias operativas adicionales: dominios institucionales configurados, clave
JWT fuerte/issuer/audience, usuarios y roles reales, asociaciones verificadas,
convocatorias persistidas, entrega institucional del código y control de intentos
de login. No se requiere ni propone mostrar códigos en logs o notificaciones públicas.

## 7. Horarios: vulnerabilidad y política confiable

`ValidarIngresoRequest.tolerancia_minutos` tiene default **15** y ge=0, sin máximo.
El router lo pasa directamente a validar_ingreso, que aplica:

```text
limite_actual = min(fecha_inicio + timedelta(minutes=tolerancia_minutos), fecha_fin)
denegar si ahora < fecha_inicio o ahora > limite_actual
```

**El cliente puede modificar una regla de autorización**, aunque tenga JWT y sea
el titular. Puede ampliar el umbral hasta el fin de la sesión; valores extremos
también pueden producir overflow y 500. No puede superar fecha_fin con un cálculo
válido, pero eso no hace seguro el parámetro. Es un análisis del código, no una
prueba de explotación ejecutada contra el equipo. El default 15 de implementación
no se considera una regla académica aprobada.

Mover el mismo default al servidor no resuelve RN-20: la base temporal y la fórmula
siguen pendientes. Proponer `PoliticaIngresoPort.obtener_limite(id_sesion) -> datetime`
con fecha consciente de zona, procedente de programación autorizada. El dominio
de Scheduling decide el permiso; Identity consume el resultado, no calcula minutos.
La política debe fallar con integración pendiente si no existe configuración suficiente.

**Fuente preferida cuando se apruebe RF-22:** guardar `limite_ingreso TIMESTAMPTZ`
por sesión, calculado/registrado por la programación autorizada. Columna inicialmente
nullable para filas antiguas, sin default ni relleno inventado. NULL deniega nuevas
validaciones de ingreso por configuración pendiente, sin cancelar registros existentes.
Es una revisión independiente de la tabla de identidad y no se implementa ahora.

Si se aprueba primero una política institucional uniforme, un adaptador de configuración
del servidor puede suministrar el límite mientras no exista la columna. Debe registrar
versión y fuente y no admitir fallback de cuerpo HTTP. No inventar un límite temporal
en Settings para ocultar falta de decisión académica.

En la siguiente API, retirar tolerancia_minutos del comando público y rechazarlo
si se envía (422), en vez de ignorarlo silenciosamente; anunciar el cambio HTTP.
Reloj del servidor inyectable y una sola referencia temporal por decisión. Probar
fronteras exactas solo después de aprobar su inclusividad: ahora la igualdad con
el límite se acepta, pero eso es código observado, no aprobación académica.

Notificaciones propias no deben depender de esa ventana. El tiempo máximo del
intento tampoco es tolerancia de ingreso: no reutilizar tiempo_maximo_minutos.

## 8. Plan exacto de implementación y migración, posterior a aprobación

| Orden / entrega | Acción y archivos previstos | Criterio para continuar |
| --- | --- | --- |
| 1. Aprobar A y semántica | Acta/este ADR: cuenta personal, 0..1 por sistema, propietario Identity y excepción de alias | Si los UUID son membresías o varias identidades válidas por sistema, revisar hacia C antes del DDL |
| 2. Modelo aditivo | `identity/infrastructure/academic_identity_models.py::IdentidadAcademicaORM`, heredando Base; tabla y restricciones del apartado 5 | Sin ORM de compañeros duplicado, sin default UUID, sin cascadas de borrado |
| 3. Repositorios | `identity/infrastructure/academic_identity_repository.py`: ConsultaVinculosAcademicosSQLAlchemy y registro interno de vínculo verificado; usar misma Session | Lectura íntegra, validación INTEGER de cuenta, conflictos sin upsert/commit propio y prueba de unicidad inversa |
| 4. Registro y revisión | Añadir importación explícita en `app/db/models.py`; crear **una** revisión `identity_academic_mapping` en `backend/alembic/versions/` | Leer heads al implementarla; down_revision será 6867083574f6 solo si sigue siendo el head único. Si cambió, rebasar la revisión, no crear otro head deliberadamente |
| 5. Contenido de upgrade | Crear identidad_academica con FK/PK/UNIQUE/CHECK nombrados; no INSERT/UPDATE sobre cuentas o referencias antiguas | Revisión manual: ningún drop/alter destructivo de tablas existentes, sin backfill ni secretos |
| 6. Downgrade de laboratorio | Revertir solo la tabla nueva en una base desechable, y volver a subir | No ejecutar esa reversión sobre vínculos reales; en despliegue usar desactivación del adaptador para volver a 503 sin perder datos |
| 7. Validación aislada | Nueva fixture PostgreSQL por contenedor y tests del apartado 9; comparar metadata/head tras upgrade | Head único, tipos/FK/índices correctos, cero diferencias inesperadas y prueba de conservar datos previos del laboratorio |
| 8. Reconciliación separada | Proceso interno `registrar_vinculo_verificado` con manifiesto revisado y evidencia; sin endpoint público | Importar solo vinculaciones unívocas, sin reasignar ni cambiar UUID de casos/sesiones |
| 9. Login | Añadir consulta de cuenta por correo, puertos de lectura Scheduling y ValidadorConvocatoriaScheduling; componer en dependencies.py | Login completo probado con vínculo y convocatoria persistidos; cero mocks en ese recorrido de integración PostgreSQL |
| 10. Alcance JWT | Validar contexto canónico de convocatoria y su relación actual en servicio académico; mantener JWT de Identity | Token de convocatoria A no permite ingreso a B; retiro posterior se rechaza; avisos propios siguen accesibles según política aprobada |
| 11. Política temporal | Nuevo puerto/adaptador Scheduling, revisión separada si se adopta limite_ingreso; cambiar schema público y programación autorizada | Valor/umbral aprobado, nunca procedente del estudiante; pruebas con reloj inyectado |
| 12. Activación | Sustituir fábricas cerradas por adaptadores reales, sin overrides productivos | No habilitar ingreso si falta política; no llamar al login por un endpoint protegido; regresión completa sin interpretar skips como éxitos |

La asociación vacía puede incorporarse sin esperar reglas de horarios, pero no
activa la integración funcional. Permisos específicos docentes, ámbito para convocar
y notificar calificaciones, y enrolamiento estudiantil requieren validación propia;
una asociación personal no concede esos permisos.

En particular, `obtener_docente_actual` exige rol, pero el router Cases no exige
todavía un permiso específico de creación. RF-02 exige ese permiso: antes de
habilitar POST /cases, componer `ServicioAutorizacion.exigir_permiso` con el código
real del catálogo aprobado. No asumir que un nombre usado en fixtures exista en
producción. Probar docente con y sin permiso, además de propiedad de recurso.

Actualizar `test_schema_integration.py`: el nuevo conjunto integrado tendría 19
tablas; conservar las comprobaciones de FK resueltas y exclusión de Participation.
No «arreglar» pruebas quitando integridad ni registrando tablas académicas falsas.

## 9. Pruebas necesarias y protocolo PostgreSQL aislado

### 9.1 Matriz de aceptación, todavía por implementar donde corresponda

| Contrato | Positivos | Negativos / inesperados | Evidencia requerida |
| --- | --- | --- | --- |
| Resolución A | UUID histórico recuperado exacto; UUID igual o distinto entre sistemas; ID estable tras reinicio | Sin vínculo; rol no autorizado; cadena entera inválida; sistema desconocido; UUID nulo; filas discordantes; error SQL y excepción inesperada | Unitarias del resolver y SQLAlchemy; PostgreSQL con restricciones reales |
| Registro de vínculos | Insertar vínculo verificado; repetir manifiesto idéntico sin reasignar | Misma cuenta/sistema con otro UUID; UUID del sistema para otra cuenta; usuario inexistente; carrera entre dos insertadores; rollback tras fallo | PostgreSQL con dos conexiones y Session/UoW reales; sin upsert que esconda conflicto |
| Login correo/código | Cuenta existente + vínculo + única convocatoria ACTIVA; emitir sub y convocatoria canónicos | Correo desconocido/normalización ambigua; código de otro usuario; cero/varias coincidencias; retirado/inactivo; SQL caído; no secreto en errores/logs | Unitarias con puertos simulados, HTTP ASGI y recorrido PostgreSQL sin mocks de repositorios |
| Contexto JWT | Token de A accede a A cuando está permitido | Token A con solicitud B; contexto no canónico; token manipulado/vencido; retiro después de emisión; cambio de rol/actividad | JWT real, base y lectura de convocatoria actuales; no sustituir dependencias de autorización en esta prueba |
| Titularidad de recursos | Casos/sesiones propios y notificaciones del usuario resuelto | X-Docente-Id/X-Estudiante-Id; cuerpo/query de otra persona; recurso ajeno; resolver indisponible | HTTP ASGI; luego HTTP con PostgreSQL real. TestClient no es una prueba de red |
| Política de ingreso | Límite aprobado y servidor inyectado; minutos de navegador no participan | Configuración ausente; reloj sin zona; antes/después y frontera exacta; envío de tolerancia_minutos; overflow; cambios de política concurrentes | Unitarias deterministas y HTTP; PostgreSQL si se persiste limite_ingreso |
| Migración | Upgrade desde head actual y desde BD vacía; ida/vuelta de INTEGER/UUID; datos previos intactos | Otra cabeza; FK/UNIQUE/CHECK inválidos; rollback/reaplicación solo en laboratorio; diff metadata inesperado | PostgreSQL efímero, Alembic real, sin create_all como sustituto del historial |

Datos previos de laboratorio: sembrar cuenta, caso y sesión con referencias de
prueba en el head antiguo; guardar sus valores y conteos; aplicar la nueva revisión
y comprobarlos idénticos. No usar datos reales del equipo para esa demostración.

### 9.2 Cómo ejecutar la migración de prueba sin tocar bases del equipo

Este protocolo es **futuro y no se ejecutó en esta tarea**:

1. Crear un contenedor PostgreSQL 17 **nuevo**, con nombre exclusivo, sin volumen
   persistente, contraseña aleatoria solo de laboratorio y puerto dinámico ligado
   a 127.0.0.1. Base `sps_identity_test_adr`. No usar el servicio db de Compose.
2. Esperar pg_isready. Obtener el puerto de ese contenedor y construir URL explícita
   `postgresql+psycopg://.../sps_identity_test_adr`. Pasarla solo al proceso de prueba
   mediante una variable dedicada `SPS_IDENTITY_EPHEMERAL_URL`; no editar .env.
3. La fixture nueva debe validar driver, host, nombre exacto de base, contenedor
   creado por ese runner y `SELECT current_database()`. Comprobar BD recién creada
   sin tablas de aplicación; abortar ante cualquier discrepancia, sin limpiar/reutilizar.
4. Crear engine de prueba desde esa URL, nunca get_engine() compartido. Con una
   conexión explícita, configurar Alembic `Config(backend/alembic.ini)` y
   `config.attributes['connection'] = conexion`. El env.py existente soporta esa
   inyección y no necesita conectarse a la configuración del equipo.
5. Ejecutar `command.upgrade(config, head_anterior)`, sembrar fixtures, después
   `command.upgrade(config, head_nuevo)` y las verificaciones del cuadro anterior.
   Usar conexión/proceso nuevo para comprobar persistencia tras commit. Probar
   concurrencia con dos conexiones; no afirmar que mocks prueban bloqueos.
6. Para otra prueba de ciclo completo, crear otro contenedor desechable y ejecutar
   upgrade desde vacío, downgrade de la revisión nueva y upgrade. Evitar DDL de
   limpieza sobre un servidor compartido. No ejecutar DROP SCHEMA ni borrar filas
   existentes para «preparar» una base ajena.
7. Cerrar conexiones/engine y eliminar **solo el contenedor creado por el runner**.
   Destruir su almacenamiento efímero termina la prueba. No emitir contraseñas/URL
   en logs ni detener el contenedor db del proyecto.

No reutilizar sin cambios `tests/identity/test_persistence.py::base_aislada` para
este protocolo: su rama PostgreSQL usa una BD indicada externamente y CREATE/DROP
SCHEMA. Tampoco usar fixtures Cases/Scheduling que hacen create_all/drop_all para
acreditar una migración. Se requiere un runner/fixture específico por contenedor.

Futuros comandos, solo cuando existan los archivos y el runner descritos:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_academic_identity_repository.py backend/tests/integration/test_student_login_scheduling.py backend/tests/unit/scheduling/test_ingress_policy.py -q -rs --tb=short
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/identity/test_academic_identity_postgresql.py -q -rs --tb=short
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

### 9.3 Evidencia actual y límites

Estado previo ejecutado y documentado: **776 passed, 38 skipped, 0 failed y una
advertencia Starlette/httpx**. No se volvió a ejecutar pytest aquí: este encargo
solo crea el ADR y prohíbe ejecutar migraciones; parte de la suite existente las
ejecuta contra SQLite. Los resultados previos no prueban los contratos propuestos.

Las pruebas actuales de identidad/resolver usan JWT real con consultas simuladas;
las funcionales Cases/Scheduling usan SQLite si no está configurada una URL de
PostgreSQL. Las 38 omitidas continúan sin verificar. No se ejecutaron PostgreSQL,
contenedores, migraciones ni datos de prueba en esta tarea. Solo se leyeron código,
metadata y grafo Alembic, y se contrastaron los PDF locales.

## 10. Preguntas de negocio que sí requieren aprobación

| Pregunta concreta | Responsable a coordinar | Efecto de no resolverla |
| --- | --- | --- |
| ¿Una cuenta representa a la misma persona para sus funciones docente/estudiante y debe tener un único UUID por sistema? ¿Los UUID históricos son personales o de una membresía? | Alejandro, Juan Andrés y Maicol con responsable de datos | No aprobar DDL cardinal de A ni importar vínculos ambiguos; si son membresías, evaluar C |
| ¿Quién acredita titularidad, autoriza altas nuevas y rectifica asociaciones históricas? | Responsable institucional y administrador autorizado | No poblar por inferencia ni habilitar cuentas sin evidencia |
| ¿Está permitido autenticar con una convocatoria antes del inicio o después del cierre para consultar avisos/resultados? | Responsable académico con Identity/Scheduling | No confundir identidad con permiso de iniciar ni reutilizar ciegamente EN_CURSO del ingreso como regla de login |
| ¿El token estudiantil autoriza un solo contexto de convocatoria, como recomienda este ADR, y cambiar exige otro código? | Equipo responsable del contrato HTTP y académico | No activar el nuevo alcance JWT sin aceptación; hoy el claim no es una comprobación de ámbito |
| ¿Cuál es el origen temporal del umbral RF-22, su valor/fórmula, zona, inclusividad y autoridad que puede cambiarlo? ¿Cambiar horario recalcula el límite? | Responsable académico y Maicol | No habilitar ingreso con default 15, cero o valor del cliente; política pendiente falla cerrado |
| ¿Vigencia, rotación, reutilización y límite de intentos fallidos del código? | Responsable académico y seguridad Identity | No implementar consumo único ni reemisión por suposición; definir pruebas y control de abuso |
| ¿Cuándo puede crearse una cuenta estudiantil y quién verifica sus datos institucionales? | Administración / responsable de roster | No crear usuarios ni mapeos desde login o convocar un UUID cualquiera como si fuese cuenta verificada |

No requieren una pregunta de negocio adicional: usar la Base existente, exigir
FK/UNIQUE, no permitir headers como identidad, inyectar reloj, impedir commits
parciales o probar en PostgreSQL aislado. Son decisiones técnicas recomendadas.
La simultaneidad de roles es una capacidad de cuenta distinta: su eventual cambio
del ORM no se debe introducir de forma encubierta en esta migración.

## 11. Archivos previstos para la siguiente iteración

Paths relativos a `backend/`; los nombres nuevos son plan, no archivos existentes.

| Archivo | Cambio exacto previsto |
| --- | --- |
| app/modules/identity/infrastructure/academic_identity_models.py | Nuevo modelo IdentidadAcademicaORM con restricciones de A |
| app/modules/identity/infrastructure/academic_identity_repository.py | Lectura del puerto y registro interno de vínculos sin commits propios |
| app/modules/identity/application/academic_identity.py | Mantener contrato; documentar cardinalidad aprobada y errores de registro |
| app/modules/identity/application/ports.py | Añadir ConsultaCuentaPorCorreo, sin mover ORM ni inventar equivalencias |
| app/modules/identity/infrastructure/repositories.py | Implementar búsqueda única normalizada de cuenta; detectar colisiones |
| app/modules/identity/infrastructure/scheduling_access.py | Adaptador ValidadorConvocatoriaScheduling con contratos internos inyectados |
| app/modules/identity/api/dependencies.py | Componer sesiones reales, lectura de usuario y validador; conservar JWT y rol |
| app/modules/identity/api/academic_dependencies.py | Componer resolver SQL después de validar integración; sin overrides productivos |
| app/modules/identity/infrastructure/security.py | Mantener firma/verificador; formalizar contexto canónico si se aprueba, sin nuevo JWT |
| app/modules/cases/api/dependencies.py y api/router.py | Exigir permiso específico de creación con catálogo real antes de habilitar la escritura; conservar resolución y propiedad |
| app/modules/scheduling/application/access_ports.py | Proyecciones/puertos de convocatoria vigente y política de límite, sin dependencia del dominio Identity |
| app/modules/scheduling/application/access_service.py | Verificar convocatoria/titular/estado/contexto y acceso en lectura coherente |
| app/modules/scheduling/infrastructure/access_repository.py | Consultas reales de convocatoria por UUID personal/hash; sin elegir candidatos arbitrarios |
| app/modules/scheduling/application/validar_ingreso.py | Recibir límite autorizado y reloj en vez de tolerancia elegida por cliente |
| app/modules/scheduling/api/router.py y api/schemas.py | Contexto JWT de convocatoria, retiro de tolerancia pública y contrato HTTP anunciado |
| app/modules/scheduling/infrastructure/models.py | Solo en entrega temporal posterior: limite_ingreso nullable, sin default inventado |
| app/db/models.py | Registrar modelo de asociación en Base común |
| alembic/versions/<revision>_identity_academic_mapping.py | Una revisión aditiva de asociación; sin semillas de usuarios o vínculos |
| alembic/versions/<revision>_scheduling_ingress_limit.py | Revisión temporal separada, únicamente tras aprobar RF-22 |
| tests/identity/test_academic_identity_repository.py | Mapping, conflictos, errores y rollback; SQLite etiquetado como tal |
| tests/identity/test_academic_identity_postgresql.py | Runner/fixture de contenedor efímero, migración e integridad PostgreSQL |
| tests/integration/test_student_login_scheduling.py | Recorrido de login y acceso con contexto persistido y JWT real |
| tests/unit/scheduling/test_ingress_policy.py | Reloj y límites aprobados; ausencia de política y parámetros manipulados |
| tests/integration/test_schema_integration.py | Nuevo head/19 tablas, FK completas y ausencia de integración de Participation |
| tests/integration/test_student_identity_security.py y pruebas Scheduling relacionadas | Añadir alcance de convocatoria y nuevo contrato temporal sin quitar casos de seguridad existentes |

No modificar `main.py` para crear esquemas ni añadir endpoints de alta de vínculos
en este incremento. No hay cambios previstos de frontend o Participation aquí;
sus contratos necesitarán coordinación posterior. No se implementó ninguno de
estos archivos en esta tarea: el único entregable nuevo es este ADR.
