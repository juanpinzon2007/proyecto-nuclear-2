> Incremento interno posterior: CONSENTIMIENTO_VERSIONADO_IMPLEMENTACION.md
> implementa registro documental y selector SQL separado, evidencia y enlace P→C.
> La fuente no se configura por defecto ni publica el borrador. Los controles y
> resultados de las secciones siguientes son históricos; no hubo aprobación institucional.

---

> Actualización vigente: sala de espera y admisión aprobadas por el equipo.
> Se registran solicitudes propias antes de habilitar y se congela el conjunto
> elegible en la transacción docente SIN_INICIAR → EN_CURSO. EN_CURSO sin concesión
> individual rechaza con 403. No hay tolerancia anticipada ni tardía ni presencia
> online inferida. Las afirmaciones anteriores sobre falta de señal de admisión
> quedan como historia; se conserva el cierre del inicio por consentimiento oficial.
> Contrato, migración y evidencia: `SALA_ESPERA_ADMISION_DISENO.md` (backend/docs).

---

# Consentimiento versionado e inicio desde convocatoria: incremento interno

5 de noviembre de 2026, America/Bogota. Rama `feature/backend-continuidad`,
base `33981c8` más cambios locales. Sin commits, migraciones ni despliegue.

## Resultado y límite de producción

Se implementó la mecánica interna de aceptación/consulta y se corrigió la
validación previa al INSERT de participación. **No hay documento oficial ni
fuente productiva de consentimiento; tampoco existe una señal operativa aprobada
para distinguir ingreso oportuno de tardío.** Provisión/inicio y aceptación siguen
fuera de main. Las fuentes y políticas positivas son exclusivamente de pruebas.

El borrador `BORRADOR_CONSENTIMIENTO_INFORMADO.md` es un entregable separado,
NO aprobado, sin identificador/versión/vigencia oficial y no referenciado desde
la configuración o el código. No se utiliza para simular una aceptación real.

## Decisiones y estructuras

Se conservan las decisiones del equipo: aceptación antes de crear P; una aceptación
sirve mientras siga vigente su versión; cambio de versión exige otra aceptación
para una nueva P; no revocación durante ejecución. No se define repetición,
ingreso tardío, fórmula de evaluación ni consecuencias académicas por no aceptar.

| Dato o garantía | Implementación actual | Límite |
|---|---|---|
| Documento/versión/contenido | DocumentoConsentimiento inmutable, referencia estable <=30 y huella SHA-256 del texto UTF-8 | La fuente oficial falta; no se inventa una versión institucional ni un hash de un PDF no disponible |
| Vigencia/ámbito | Puerto FuenteConsentimiento.vigente(id_asignacion,ahora), fuente de servidor | No elegir MAX(version_texto), una fila legada o la versión propuesta por el cliente. Fuente inmutable y recuperación histórica son obligaciones del futuro adaptador |
| Titular | ServicioConsentimientoSQLAlchemy revalida cuenta/rol ESTUDIANTE/activo y bloquea cuenta/rol | Contexto viene del servidor; no hay endpoint nuevo que acepte un student_id como credencial |
| Aceptación explícita | aceptar exige acepta is True y coincidencia con referencia/huella de la definición del servidor | No se infiere de login o matrícula; no acredita retrospectivamente la voluntad de registros legados |
| Persistencia | Tabla existente consentimiento: estudiante FK, version_texto usado como referencia estable, fecha_aceptacion de reloj servidor | No se añaden columnas ni se guarda el documento en esa etiqueta. Definiciones históricas deben conservarse por fuente confiable externa |
| Consulta vigente | Selección propia, referencia actual, no revocada, fecha no futura; ambigüedad rechazada | Una consulta de vigencia no sustituye una consulta histórica ni demuestra por sí sola procedencia de una fila antigua |
| Duplicados de aceptación | Serialización por cuenta; segundo registro de misma referencia falla cerrado sin duplicar | No se impone UNIQUE académico nuevo ni se promete idempotencia transparente: legado/duplicado exige conciliación |
| Antes de crear P | exigir_aceptacion en _obtener_o_crear antes de agregar_participacion | Funciona para P nueva; recuperar una existente no reescribe su historia ni fuerza por sí mismo nueva aceptación |
| Relación con ejecución | intento.id_consentimiento existente | P no tiene FK propia al consentimiento; sin I no conserva un enlace directo al registro usado. No inventar una relación inexistente |
| No revocación en ejecución | comprobar_revocacion bloquea/revalida titular y consentimiento y rechaza I persistido EN_CURSO | Es guard interno de la UoW prestada, no un nuevo flujo de revocación. No modifica fechas. No protege SQL directo ni atribuye esa garantía al guard BD207 existente |

ServicioConsentimientoSQLAlchemy usa Session prestada y NO hace commit. El llamador
debe confirmar o revertir su UoW. No se compone una fuente por defecto. Ningún fake
se incorpora al runtime; FuenteConsentimientoLaboratorio vive en tests.
Las aceptaciones nuevas se prueban con definiciones sintéticas explícitas; las
filas previas no se reclasifican como aceptaciones explícitas verificadas.

## Orden corregido y contratos internos ampliados

La misma UoW y los mismos servicios de Participation conservan los locks de
convocatoria/P/cuenta/matrícula/sesión/asignación y las referencias exactas.
Tras acreditar identidad, contexto, ingreso y vínculo académico, para P nueva:

1. Resolver la definición vigente desde fuente del servidor y validar aceptación
   propia/no revocada/no futura; si es ambigua o falta fuente, rechazar.
2. Rechazar permiso adicional para una P aún inexistente (su FK exige P previa).
3. En el flujo combinado, comprobar grafo ejecutable y duración consistente;
   consultar la MISMA política de inicio con datos bloqueados antes de crear P.
4. Aplicar política existente de vinculación/estado; recién entonces agregar P.
5. Reutilizar preparar_inicio_en_uow y ServicioInicio para revalidar y registrar I;
   un solo commit o rollback completo. La cuenta/aceptación se mantienen bloqueadas.

Una política de inicio ausente se rechaza antes de crear P. El contrato existente
CondicionesInicioIntento admite id_participacion=None exclusivamente en esta
prevalidación, porque todavía no hay PK: no se fabrica ni se reserva un ID.
La política es una consulta sin efectos/consumo; se evalúa de nuevo con la PK real
antes de registrar el intento. La persistencia/consumo de permisos existente
continúa transaccional, sin repeticiones automáticas.

Se añade fuente_consentimiento=None a ServicioVinculacionSQLAlchemy y a las
fábricas de dependencia/router de integración. Es una dependencia privada del
servidor, no un parámetro HTTP. Sin ella no se crea una P nueva. El cuerpo y las
rutas HTTP conservan sus contratos; no se habilitan en main. Provisión interna
independiente también exige aceptación antes de crear, sin conceder permiso de I.

Las validaciones fallidas de consentimiento y política se comprueban observando
las instrucciones SQL: **ningún INSERT P**, no solo una tabla vacía tras rollback.
Las condiciones que cambien o errores posteriores se revalidan y revierten todo.

## RF-22 definitivo y mecanismo mínimo pendiente

Solo puede ingresar con habilitación docente real persistida EN_CURSO; SIN_INICIAR
y FINALIZADO rechazan. No hay anticipación ni tolerancia tardía. Fecha programada
no habilita. EN_CURSO y su auditoría no identifican una etapa de admisión abierta:
dos solicitudes a instantes distintos pueden observar el mismo estado y relaciones,
sin que exista una regla objetiva para clasificar su oportunidad.

No se implementa igualdad exacta con creado_en, una ventana implícita ni permiso
durante todo EN_CURSO. `POST /scheduling/validar-ingreso` conserva 503 cuando falta
esa prueba, sin DML/flush/commit/P/I. Los positivos con IngresoLaboratorio siguen
marcados como pruebas mecánicas; no acreditan RF-22 productivo.

Propuesta mínima, **pendiente de decisión funcional y persistencia aprobada**:
una etapa de admisión con señales explícitas de apertura/cierre del servidor,
causadas por operaciones docentes autorizadas y vinculadas a esa habilitación.
Se debe definir qué hecho cierra la admisión y cuándo se considera recibida una
solicitud. No se propone una cantidad de minutos. Verificar estado EN_CURSO más
esa señal, y no reutilizar convocatoria.ACTIVA (también habilita identidad/avisos),
mensajes libres o estado de intento como una señal inventada. No se implementa
una columna, un evento ni un endpoint nuevo para ese mecanismo sin aprobarlo.

## Pruebas ejecutadas y disponibilidad HTTP

| Ejecución actual | Aprobadas | Omitidas | Fallidas/errores | Advertencias |
|---|---:|---:|---:|---:|
| Focalizada inicial | 24 | 0 | 0 | 1 |
| Relacionada final | 582 | 0 | 0 | 1 |
| General final | 2126 | 38 | 0 | 1 |

No sumar ejecuciones solapadas. Relacionada 182.32 s. General 874.69 s, terminó
2026-11-05 20:31:56 America/Bogota (2026-11-06T01:31:56Z). Advertencia conocida de
Starlette/TestClient-httpx; omisiones: 29 Identity y 9 Participation antiguas
condicionadas a configuración/URL, no dadas por aprobadas. Fuente estable durante
pytest; el único artefacto adicional de la general es evidencia experimental BD2-04.

`test_consent_before_provision.py` acredita PG17 real, aceptación persistida y
recuperación desde otra Session, voluntad explícita, cambio de versión, identidad
ajena real, guard de revocación, errores antes del INSERT, rollback y concurrencia.
El HTTP nuevo usa la aplicación aislada existente con JWT real. La regresión
incluye 30 casos RF-22 sobre main, habilitación docente real y ausencia de DML,
y los recorridos previos de 8A/8B. No se afirma que aceptación o inicio estén
probados como operaciones productivas de main: sus rutas siguen ausentes.

En main permanecen los logins estudiantil/personal de Identity, el cambio docente
de estado y validar-ingreso de Scheduling, y las cuatro operaciones acreditadas
de intentos existentes: escenario, progreso, primera decisión inmutable y cierre.
NO se añaden rutas de consentimiento, /convocatorias/{id}/participacion,
/convocatorias/{id}/intentos ni resultados oficiales.

Evidencias/JUnit/comandos/huellas: `evidencias/consentimiento_inicio_20261106T010714Z/`.
Finales: `pruebas_focal_20261106T011316Z`, `pruebas_total_20261106T011709Z`.
Ejecutor reproducible: `C:\Python313\python.exe -B evidencias/consentimiento_inicio_20261106T010714Z/ejecutar_validacion.py focal`
(o `total`). Desactiva lectura de .env/URLs externas; postgres:17 nuevo, tmpfs,
puerto local efímero, eliminación únicamente de su contenedor. Sin instalaciones.

## Bloqueos y criterios de aceptación productiva

- Documento oficial exacto, autoridad, referencia/version/vigencia y ámbito;
  fuente productiva que preserve definiciones inmutables y gestione cambios de
  versión coherentemente con la transacción. No existe todavía ni se sustituye
  por una fuente LAB o por este borrador.
- Procedencia verificable de aceptaciones: esquema actual no tiene huella ni
  evidencia explícita separada. El servicio prueba el acto en registros LAB;
  no puede certificar registros legados. Antes de producción debe aprobarse cómo
  conservar esa evidencia y resolver duplicados/historia. No se impone unicidad
  ni se completan filas antiguas con datos inventados.
- P carece de referencia al consentimiento. Si se exige conservar cuál aceptación
  justificó P antes de existir I, proponer y aprobar esa referencia; el enlace de
  I no resuelve el caso sin ejecución. No se cambia ORM/ER/migraciones aquí.
- El guard interno de revocación no protege escritores que lo eludan. Para SQL
  directo se necesita revisar explícitamente los guards de consentimiento/I y
  su carrera con un nuevo inicio. El guard histórico actual NO incluye esa fecha.
  No se crea mecanismo público de revocación ni se altera historia.
- Falta señal operativa de oportunidad RF-22 y demás políticas de inicio/provisión
  y repetición aplicables. Consentimiento nunca autoriza ingreso o inicio temprano.

RF-12 y RF-22 permanecen PARCIAL; los otros estados de la matriz no cambian.
Hay avance técnico probado, no inicio productivo. No se tocaron fórmulas de
Evaluation, tablas, migraciones, DBML, .env, bases permanentes ni ramas originales.
No se creó commit. El siguiente incremento debe aprobar documento/fuente y señal
de admisión antes de registrar rutas; no se inicia automáticamente.

## Archivos de este incremento

Modificados respecto al estado inicial protegido:

- `backend/app/modules/participation/api/HTTP.md`
- `backend/app/modules/participation/api/dependencies.py`
- `backend/app/modules/participation/api/provision_router.py`
- `backend/app/modules/participation/application/start_policy.py`
- `backend/app/modules/participation/infrastructure/provision.py`
- `backend/app/modules/scheduling/POLITICA_TEMPORAL_INGRESO.md`
- `backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md`
- `backend/docs/CONSENTIMIENTO_CONTRATO_Y_CHECKPOINT_20261105.md`
- `backend/docs/DECISIONES_FUNCIONALES_RF22.md`
- `backend/docs/FASE_9B_INICIO_DESDE_CONVOCATORIA.md`
- `backend/docs/RF22_INGRESO_ANTICIPADO.md`
- `backend/tests/integration/test_participation_http_composition.py`
- `backend/tests/integration/test_participation_provision.py`

Nuevos de implementación/documentación:

- `backend/app/modules/identity/application/consent.py`
- `backend/app/modules/identity/infrastructure/consent.py`
- `backend/docs/BORRADOR_CONSENTIMIENTO_INFORMADO.md`
- `backend/docs/CONSENTIMIENTO_E_INICIO_INTERNO.md`
- `backend/tests/integration/consent_support.py`
- `backend/tests/integration/test_consent_before_provision.py`

Artefacto BD2-04 generado por la general, preservado y excluido de cualquier
selección de código/checkpoint:

- `backend/docs/bd/laboratorio_bd2_04/evidencia_b3e33deb29a44465950d3ba2dc674b2c.json`

Los cambios anteriores ajenos a esta lista se cotejan por SHA-256 y se conservan.
El manifiesto histórico de 34 archivos no se reescribe; delta y estado Git completo
quedan en la carpeta de evidencia.


### Actualización posterior: señal de admisión implementada

La sala de espera ya fue aprobada por el equipo e implementada en Scheduling;
la propuesta anterior sobre esa señal queda sustituida por
SALA_ESPERA_ADMISION_DISENO.md (32 aceptaciones; general 2158/38, sin fallos).
La falta de fuente oficial de consentimiento permanece. No se aprueba ni publica
el borrador, no se abren rutas de creación/inicio de Participation. RF-22 figura
implementado en su alcance de admisión; RF-12 sigue parcial. No confundir ambos.
