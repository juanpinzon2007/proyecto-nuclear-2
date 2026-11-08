> Actualización vigente: sala de espera y admisión aprobadas por el equipo.
> Se registran solicitudes propias antes de habilitar y se congela el conjunto
> elegible en la transacción docente SIN_INICIAR → EN_CURSO. EN_CURSO sin concesión
> individual rechaza con 403. No hay tolerancia anticipada ni tardía ni presencia
> online inferida. Las afirmaciones anteriores sobre falta de señal de admisión
> quedan como historia; se conserva el cierre del inicio por consentimiento oficial.
> Contrato, migración y evidencia: `backend/docs/SALA_ESPERA_ADMISION_DISENO.md`.

---

> Regla definitiva: sin anticipación ni tolerancia tardía. EN_CURSO no basta para
> comprobar oportunidad; falta señal de apertura/cierre de admisión o equivalente
> aprobado. Se conserva 503, sin intervalos inventados ni igualdad de timestamps.
> Ver `backend/docs/CONSENTIMIENTO_E_INICIO_INTERNO.md` para el contrato pendiente.

# Corrección vigente RF-22: ingreso solo después de habilitación

**La anticipación de diez minutos fue descartada por corrección del requisito.**
Se exige EN_CURSO persistido tras habilitación efectiva; la hora programada no
habilita. No hay tolerancia anticipada ni posterior nueva. El proveedor temporal
productivo sigue cerrado si falta una regla completa. Contrato y evidencia:
[RF22_INGRESO_ANTICIPADO.md](../../../docs/RF22_INGRESO_ANTICIPADO.md) (nombre histórico).
Registro: [DECISIONES_FUNCIONALES_RF22.md](../../../docs/DECISIONES_FUNCIONALES_RF22.md).

---

## Notas históricas: la autorización anticipada citada abajo queda sustituida

# Fase 7: contrato temporal seguro, política académica pendiente

> Antecedente histórico. La decisión funcional posterior del equipo autoriza
> validar ingreso desde diez minutos antes del inicio programado, sin autorizar
> inicio de simulación ni definir tolerancia posterior. Implementación actual,
> límites y pruebas: [RF22_INGRESO_ANTICIPADO.md](../../../docs/RF22_INGRESO_ANTICIPADO.md).
> Las afirmaciones siguientes sobre ausencia de toda política describen Fase 7.

Rama feature/integracion-backend. Se conservan las fases anteriores sin commit y
la carpeta evidencias. No se modificaron .env, ORM, migraciones, identificadores,
Worker o Participation. No se consultaron datos del equipo ni producción.

**Resultado:** el cliente ya no puede indicar tolerancia, hora o ventana. Existe
un contrato temporal inyectable y comprobable, pero NO una regla RF-22 aprobada.
El ingreso real continúa cerrado cuando se necesita esa política.

## 1. Diagnóstico y respaldo documental

Se inspeccionaron router/schemas, validar_ingreso, SesionProgramadaModel, State,
programar_sesion, worker_cierre, dependencias estudiantiles Identity, JWT y
ValidadorConvocatoriaScheduling. El servicio anterior calculaba
min(inicio + tolerancia_del_cuerpo, fin), con default 15; ese valor no era una regla
académica aprobada. También convertía timestamps sin zona a UTC por suposición.

Fuentes locales contrastadas, páginas del PDF:

- [Agile Inception](../../../../_referencias_locales/Agile%20Inception%20SPS.pdf),
  pp. 8-9: RF-19/RF-20 y reglas de ingreso tardío pendientes de precisión.
- [Análisis de Sistemas](<../../../../_referencias_locales/Entrega 1 Proyecto Nuclear Análisis de sistemas  (1).pdf>),
  pp. 4-5: sesión/convocatoria y RF-22, cuya base debe acordarse académicamente.
- [Ingeniería de Software II](<../../../../_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf>),
  pp. 5 y 7: RF-20/RF-22 y RN-20, que explícitamente deja pendiente la fórmula.

Hechos del código y reglas conservadas:

| Aspecto | Estado verificado |
| --- | --- |
| Identidad | JWT vigente de Identity, usuario activo y rol estudiantil del repositorio |
| Identidad académica | Resolver SQL unívoco; sin asociación o ambigüedad no hay ingreso |
| Contexto | Claim de convocatoria canónico, igualdad con lo solicitado, titularidad y ACTIVA comprobados en servidor |
| Código | Hash y comparación de Scheduling existentes, sin devolver secretos |
| Estado de sesión | Solo EN_CURSO; SIN_INICIAR y FINALIZADO rechazan |
| Programación | fecha_fin > fecha_inicio, fechas con zona en programación; ORM declara DateTime(timezone=True) |
| Límite exterior | La mecánica conserva la restricción anterior de no permitir una ventana anterior al inicio ni posterior al fin programados |
| Worker RF-19 | Cierra sesiones EN_CURSO cuando el fin lleva al menos 24 horas vencido; ese retraso de cierre NO es tolerancia de ingreso |
| Convocatoria expirada | No existe estado EXPIRADA ni fecha propia de expiración en el ORM; no se inventó uno. RETIRADA se rechaza y el ingreso exige la ventana de la sesión |

El login identifica al estudiante para consultar su cuenta/avisos; no inicia
participación ni concede ingreso temporal por sí solo. No se reintrodujo una
condición global de sesión en curso para /me o notificaciones propias.

## 2. Implementación de producción

### Contrato y mecánica

Nuevo `domain/ingress_policy.py`:

- `PoliticaIngreso.obtener_ventana(id_sesion,inicio,fin)` recibe datos del servidor
  y entrega una `VentanaIngreso`; no recibe el comando HTTP.
- `VentanaIngreso` conserva apertura, cierre e inclusividad de ambos extremos,
  todos explícitos. No fija una fórmula, minutos o inclusión por defecto.
- Normaliza instantes conscientes de zona a UTC. Una fecha naive, intervalo
  invertido o flags que no sean booleanos se rechazan como configuración insuficiente.
- `PoliticaIngresoNoConfigurada` siempre lanza PoliticaTemporalNoDisponible.
  Es la única implementación productiva actual; no hay tolerancia oculta en Settings.
- `RelojIngreso` permite pruebas deterministas. `RelojServidor` usa hora UTC del
  servidor. No se reutilizó ni se acopló el reloj de Participation.

`application/validar_ingreso.py` ahora exige política y reloj inyectados. Conserva
convocatoria/código/propietario y estado. Valida las fechas y que la ventana devuelta
esté contenida en la programación; después lee el reloj una sola vez y evalúa esa
ventana. No infiere zona de timestamps naive, no inventa minutos y no escribe datos.

Esta API interna cambia intencionalmente: ya no acepta tolerancia_minutos ni un
argumento temporal opcional obtenido del cliente. No se mantuvo un fallback al
cálculo anterior. Los consumidores del repositorio fueron actualizados.

### HTTP y orden de comprobación

`ValidarIngresoRequest` solo admite convocatoria_id, estudiante_id y codigo_acceso,
con extra=forbid. Enviar tolerancia_minutos, ahora, fecha_inicio o ventana da 422.
No se ignora silenciosamente el intento de manipular el tiempo. Es un cambio
intencional del contrato de seguridad para los clientes anteriores.

El router inyecta la fuente temporal cerrada y el reloj, manteniendo Identity,
resolver, contexto y verificación del estudiante. Ya no aborta antes de todas las
validaciones con un stub 503: las prohibiciones conocidas se comprueban primero.

| Condición | Resultado esperado |
| --- | --- |
| JWT ausente, inválido o vencido | 401 |
| Identidad/convocatoria ajena o retirada, contexto no autorizado | 403 |
| Parámetro HTTP temporal extra con credenciales válidas | 422 |
| Sesión no iniciada/finalizada o código incorrecto | 403 |
| Sesión en curso y credenciales válidas, sin política suficiente | 503 |
| Datos temporales incoherentes o fallo SQL declarado | 503 sin diagnóstico privado |
| Error inesperado de la política | Propaga para diagnóstico; HTTP genérico 500, sin acceso |

El caso de ventana válida puede devolver 200 con un adaptador autorizado futuro;
hoy solo se verifica con fuentes sintéticas en pruebas. No existe configuración
de producción que habilite ese caso en este incremento.

## 3. Decisiones pendientes y fuente futura

El responsable académico debe definir:

1. Referencia del retraso: inicio programado, inicio real u otra condición aprobada.
2. Límite/fórmula y alcance de la regla: institucional, por sesión o excepción.
3. Inclusión o exclusión exacta de los extremos y zona de referencia al programar.
4. Autoridad para registrar/cambiar la regla y efecto de reprogramar o cerrar sesión.
5. Vigencia/rotación/reutilización de códigos, si se necesita algo adicional a ACTIVA.

Solo entonces implementar el adaptador del puerto sobre programación autorizada o
configuración académica versionada del servidor. No basta mover «15» a una variable
de entorno: no resuelve la base de cálculo pendiente. Si se decide persistir un
límite en sesión, su migración debe ser otro incremento revisado, sin completar
filas antiguas con una regla inventada. Si la regla aprobada contradice los límites
externos actuales, revisar explícitamente el contrato antes de habilitarla.

No implementar aquí un estado nuevo de convocatoria, una tolerancia por usuario,
excepciones de acceso, membresías o un inicio de Participation.

## 4. Pruebas y significado de los positivos

Nuevas suites:

- `tests/unit/scheduling/test_ingress_policy.py`: 22 pruebas de mecánica con
  Session doble, ventanas sintéticas y reloj fijo. Extremos incluidos/excluidos,
  microsegundo exterior, mismo instante con offsets distintos, misma hora local
  con otro offset, naive, intervalo/configuración inválidos, falta de política,
  estados/recurso inexistente y una lectura del reloj después de la política.
- `tests/identity/test_ingress_temporal_sql.py`: 24 casos con SQLite y los mismos
  24 con PostgreSQL real. Reutilizan login, JWT, usuarios, resolver y convocatorias
  persistidas; no sustituyen autenticación, titularidad ni contexto. Cubren JWT
  ausente/inválido/vencido, convocatoria ajena/inexistente/retirada, otro estudiante,
  código incorrecto, sesión no iniciada/finalizada, manipulación HTTP, falta de
  política y OpenAPI. Las fronteras/positivos inyectan una ventana SINTÉTICA; los
  fallos de infraestructura se provocan con dobles identificados.

**No se declara un ingreso académico aprobado:** los positivos de ventana miden
la implementación matemática y su composición con SQL/JWT. No demuestran qué
ventana debe permitir el profesor ni satisfacen la aprobación pendiente de RF-22.

SQLite pierde el offset en DateTime incluso con timezone=True. Las fixtures que
escriben sus propias fechas UTC lo restauran explícitamente al leer, solo en tests.
Producción rechaza naive y PostgreSQL se prueba con sus fechas conscientes de zona
reales. No se usó SQLite para afirmar semántica temporal de PostgreSQL.

Se actualizaron las fixtures antiguas de ingreso para entregar fuentes sintéticas
explícitas, no valores HTTP. Las pruebas de login/contexto dejaron de enviar el
campo eliminado. Dos expectativas de flujo anteriores cambiaron de 503 a 403
porque su sesión SIN_INICIAR ya se rechaza por esa regla conocida: ahora se exige
también el mensaje «La sesión no está en curso». No se eliminaron los escenarios;
una sesión EN_CURSO sin política sigue exigiendo 503 en su prueba independiente.

## 5. Resultados ejecutados

| Ejecución final | Aprobadas | Fallidas | Omitidas | Advertencias |
| --- | ---: | ---: | ---: | ---: |
| Nuevas suites temporales, con laboratorio | 70 | 0 | 0 | 1 |
| Nuevas suites + login SQL/JWT, con laboratorio | 121 | 0 | 0 | 1 |
| Completa sin laboratorios habilitados | 882 | 0 | 113 | 1 |
| Completa con laboratorios de identidad habilitados | 957 | 0 | 38 | 1 |

La primera ejecución completa detectó dos expectativas anteriores 503/403; se
corrigieron como se explica arriba y se volvió a validar. No se consideran como
aprobadas las pruebas omitidas. La advertencia conocida es Starlette/httpx.

La comparación con la línea base sin laboratorios (836/89) es: 46 nuevas aprobadas
(22 mecánicas + 24 SQLite) y 24 nuevas PostgreSQL omitidas por opt-in. Con opt-in
se ejecutan las 70 nuevas; las 38 omitidas antiguas pertenecen a otras conexiones
no habilitadas. No se instalaron dependencias.

Comando específico, con Docker activo e imagen postgres:17 ya disponible:

```powershell
$env:SPS_TEST_IDENTITY_MAPPING_DOCKER = "1"
try {
    .\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/unit/scheduling/test_ingress_policy.py backend/tests/identity/test_ingress_temporal_sql.py backend/tests/identity/test_student_login_scheduling.py -q -rs --tb=short
} finally {
    Remove-Item Env:SPS_TEST_IDENTITY_MAPPING_DOCKER
}
```

Suite completa ejecutada, tanto sin opt-in como con ese opt-in:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Los laboratorios PostgreSQL son contenedores nuevos sps-resolver-lab-* con datos
tmpfs y puerto local dinámico. Solo allí se aplican migraciones existentes para
preparar fixtures; se destruyen al finalizar. No se ejecutó ninguna migración en
bases compartidas ni se tocó sps o los contenedores existentes del equipo.

Alembic conserva una cabeza: 20261031_academic_identity. No hay revisión nueva,
cambios ORM ni columnas de política temporal en este incremento.

## 6. Archivos y resumen del diff de esta fase

Producción:

- `scheduling/domain/ingress_policy.py` (nuevo): ventana, puerto, reloj y falta
  de configuración; sin reglas académicas concretas.
- `scheduling/application/validar_ingreso.py`: elimina tolerancia/cálculo implícito
  y fechas naive; valida fuente temporal explícita con reloj inyectado.
- `scheduling/api/schemas.py`: elimina tolerancia y prohíbe parámetros extra.
- `scheduling/api/router.py`: inyecta fuente/reloj y traduce los fallos esperados.

Pruebas nuevas: las dos suites temporales y `tests/unit/scheduling/ingress_support.py`.
Adaptaciones: test_validar_ingreso, test_api_endpoints, fixture/test funcional
Scheduling, test_student_identity_security y las pruebas SQL/JWT anteriores que
enviaban el campo eliminado. Las comprobaciones de autorización permanecen.

El diff Git acumulado incluye las fases previas; este informe no las atribuye a
la política temporal. No se modificó lógica de Identity, Worker, Cases, persistencia
o Participation en esta fase. No hubo cambio de rama, commit, push, merge o PR.

## 7. Próximo paso antes de Participation

Primero aprobar RF-22 y su fuente autorizada, implementar el adaptador de ventana
y sustituir la fuente cerrada. Verificar escenarios académicos reales en laboratorio
con reglas aprobadas; entonces podrá habilitarse el endpoint de ingreso.

Después coordinar el vínculo entre convocatoria UUID y asignación/membresía INTEGER
de Participation. La autorización, ventana, estado y cupo deben revalidarse de
forma atómica con el inicio real del intento; este endpoint solo consulta/valida
y no constituye una reserva ni garantiza permiso para un inicio posterior.

No usar el retraso de cierre del Worker o tiempo_maximo_minutos del intento como
tolerancia. No iniciar Participation para eludir la política pendiente.
