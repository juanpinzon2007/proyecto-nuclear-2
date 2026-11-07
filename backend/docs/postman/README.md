# Postman — Proyecto Nuclear — preparación y verificación local

Base: `feature/backend-continuidad`, HEAD
`8e1c03400b47d571eb903e40f0175c3d1c3f1008`. Código productivo sin modificaciones.
Fecha local: 7 de noviembre de 2026, America/Bogota.

## Archivos importables y contrato

1. `Proyecto_Nuclear_main.postman_collection.json`: catálogo de app.main,
   formato Postman 2.1; 179 solicitudes agrupadas por Identity, Cases, Scheduling,
   Participation, seguimiento/notificaciones y técnico. Contiene positivas con
   precondiciones, ausencia de JWT, JWT inválido, rol incorrecto y body inválido.
   **No ejecutar este catálogo entero**: mezcla estados de recursos mutuamente
   excluyentes (borrador/publicado/archivado), pruebas negativas y escrituras.
2. `Proyecto_Nuclear_recorrido_LAB.postman_collection.json`: 30 pasos ordenados
   para ejecutar una vez sobre un laboratorio nuevo. Cada nombre distingue MAIN
   de LAB AISLADA y cada servidor tiene su URL propia.
3. `Proyecto_Nuclear_laboratorio.postman_environment.json`: sin credenciales,
   códigos, JWT válidos ni conexión SQL. Importar como Environment y seleccionarlo.
4. `INVENTARIO.md` y `inventario_endpoints.json`: inventario completo, incluyendo
   autenticación, rol, cuerpo/parametrización, esquemas, fuente y dependencias.
5. `openapi_main.json`: exportación de OpenAPI desde app.main. Es la fuente para
   estructuras HTTP; el generador añade notas de autorización/cierre extraídas
   de los routers, porque OpenAPI no documenta todos sus errores funcionales.

Hay **41 operaciones en OpenAPI** y cuatro rutas automáticas de documentación
con GET/HEAD: 49 combinaciones método/ruta en el inventario. No existe una ruta
Evaluation en main. No se encontró una colección Postman previa que reutilizar.
Se reutilizan routers, esquemas y preparación del test integral existente.

## Inicio seguro del laboratorio para Postman Desktop

Requisitos instalados: .venv existente, Docker Engine activo y la imagen
`postgres:17` ya descargada. No se instala software ni se hace docker pull.
Use dos puertos loopback libres. No use `uvicorn app.main:app` con .env del
proyecto: podría conectar una base persistente. Este lanzador fija el destino
al PostgreSQL propio creado por la fixture y desactiva lectura de .env solo en
su proceso.

Desde la raíz original del repositorio:

```powershell
git branch --show-current
git rev-parse HEAD
docker info --format '{{.ServerVersion}}'
docker image inspect postgres:17 --format '{{.Id}}'
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -B backend\docs\postman\laboratorio_http.py --puerto 8765 --puerto-lab 8766
```

La consola solicita **cuatro secretos sintéticos elegidos por el operador**, sin
eco: clave admin, clave docente, código estudiante titular y código ajeno. No usar
credenciales reales. No pasarlos por argv, tuberías, .env ni archivos. El lanzador
guarda solamente sus hashes en su base nueva y muestra únicamente correos .test,
UUID e IDs sintéticos. No muestra secretos, JWT o cadena SQL.

El lanzador reutiliza `pg_autoria`, `payload_valido` y `recorrido_lab` de
`test_lab_student_journey.py`. Prepara administrativamente roles, cuentas,
asociaciones UUID verificadas, grupo, matrícula, grant docente-espacio, asignación,
sesión, convocatorias, espera y admisión. El contenido, grafo y publicación del
caso se construyen mediante las APIs reales de esa fixture. Esta preparación
**no acredita un alta académica productiva íntegra por HTTP**.

La fuente de consentimiento es SINTÉTICA; el reloj es fijo y las políticas de
vinculación/inicio son las explícitas del laboratorio existente. La autenticación,
roles, repositorios, matrícula y titularidad son reales; no hay overrides de ellos.
Se usan dos servidores:

- `http://127.0.0.1:8765`: el mismo objeto app.main.app, con reloj de laboratorio.
- `http://127.0.0.1:8766`: app separada, solo consentimiento/provisión/inicio LAB.

Mantener abierta esa consola. **Enter** detiene los dos servidores y ejecuta el
finally de la fixture, que elimina solamente su contenedor por ID completo propio.
No usa volúmenes persistentes ni reutiliza contenedores existentes. Ctrl+C también
sale mediante los contextos; evitar cerrar forzosamente el proceso. Ante un cierre
forzoso, inspeccionar el recurso propio con el equipo; no aplicar limpieza global.

## Configuración privada de Postman y orden de ejecución

1. Importar las colecciones y el Environment desde los archivos anteriores.
2. Seleccionar el Environment LAB. Usar valores locales no compartidos; no sincronizar
   secretos. Si la versión de Postman permite Vault, introducirlos allí mediante su
   interfaz y referenciarlos desde los valores locales. `type: secret` oculta en la
   UI, pero **no cifra un archivo exportado**.
3. Copiar a las variables los recursos mostrados por el lanzador: `correo_admin`,
   `correo_docente`, `correo_estudiante`, `correo_ajeno`, `id_docente`,
   `estudiante_id` (UUID), `convocatoria_id`, `sesion_id`, `version_id`,
   `caso_uuid`, `id_asignacion`, `espacio_academico_id`.
4. Introducir localmente los cuatro secretos elegidos: `clave_admin`,
   `clave_docente`, `codigo_estudiante`, `codigo_ajeno`.
5. Solo tras confirmar que las dos URLs son las de ese laboratorio propio, poner
   `laboratorio_confirmado=true` y `permitir_escrituras_laboratorio=true`.
   Estas barreras del cliente reducen errores del operador; **no prueban el
   aislamiento de una base ni reemplazan autorización del servidor**.
6. Abrir Runner de **Proyecto Nuclear — recorrido integral LAB — NO productivo**.
   Ejecutar los 30 pasos en su orden, una iteración, sin concurrencia del Runner.
   `RECORRIDO.md` contiene el orden exacto y estado esperado de cada paso.
7. Tokens e IDs encadenados se mantienen con `pm.variables` en el ámbito local
   de esa ejecución. No se guardan con `pm.environment.set`, no se imprimen y
   no forman parte del Environment distribuido.
8. Para pruebas individuales del catálogo, proporcionar tokens solo en valores
   locales privados después del login correspondiente. El ámbito temporal del
   Runner no persiste entre botones Send independientes. No exportar esos valores.
9. Guardar capturas de estado/Tests con Authorization, cuerpos de login y códigos
   ocultos. Desactivar persistencia de cuerpos de respuesta en Runner cuando esté
   disponible. Un reporte externo puede conservar bodies de login: revisarlo y
   redactarlo antes de compartir. No publicar resultados de ejecución en workspaces.
10. Finalizar el laboratorio con Enter. Reabrirlo para repetir el recorrido: un
    intento finalizado o una autorización consumida no son fixtures reiniciables.

Los scripts fallan si falta una variable, si las URLs no son loopback con puerto
explícito o si las escrituras no están confirmadas. Un HTTP distinto del exacto
esperado falla el test; 503 no se acepta como sustituto de 200. Las operaciones
bloqueadas tienen su expectativa 503 explícita y no se consideran éxitos funcionales.

## Uso del catálogo por módulo

- **Identity**: login estudiantil por correo/código; personal por correo/clave;
  /me; alta, listado y autorizaciones de docentes. Solo ADMINISTRADOR para estas
  tres últimas, con cuenta activa/rol vigente en SQL. No existe bootstrap HTTP.
- **Cases**: DOCENTE y vínculo CASES; escrituras además CREAR_CASOS. Para una prueba
  positiva de autoría crear un **borrador nuevo**, copiar su version_id, editarlo,
  leer sus escenarios/opciones, configurar todos los destinos en `grafo_body`,
  publicar y finalmente archivar cuando corresponda. La versión publicada por la
  fixture es histórica: editarla debe rechazarse, no esperar un PUT 200 sobre ella.
  Para una escena de una pregunta, `grafo_body` puede declarar su ID como inicial
  y FIN para **todas** sus opciones. No inventar vínculos UUID ni omitir opciones.
- **Scheduling**: docente SCHEDULING, propiedad de sesión y grant docente-espacio
  para programar. /espacios es el catálogo global docente en el código actual;
  no se afirma que filtre por grant. Las nuevas sesiones necesitan su asignación
  académica persistida antes de convocar alumnos; no existe una API de grant o
  matrícula que deba inventarse. Las pruebas de retiro, habilitación, archivo y
  cambio de estado alteran el fixture: ejecutarlas en recursos/laboratorios nuevos.
  `accion=finalizar` es el ejemplo del catálogo; no repetirlo sobre una sesión cerrada.
- **Participation**: las cuatro operaciones del intento existente, solo titular,
  con contexto vigente y versión histórica. POST decisions es inmutable; una
  segunda selección devuelve 409. PUT de decisiones no está montado (405).
- **Seguimiento/notificaciones**: ámbito docente persistente, feedback individual
  editable y consulta del estudiante después del cierre; avisos internos propios.
  Notificación persistida no equivale a correo enviado por un proveedor externo.

El catálogo es completo en cobertura de rutas, **no una batería certificada de
aceptación de todos los estados**. Las solicitudes positivas requieren recursos
y estados indicados. Los datos de correo/fechas, grafo, caso y permisos pueden
editarse como entradas sintéticas, manteniendo sus contratos. Ningún UUID público
se obtiene convirtiendo un INTEGER. `id_intento`/`id_participacion` son enteros;
`caso_uuid`, versión, opción y estudiante SCHEDULING son UUID de su sistema.

## Bloqueos y superficies que no deben confundirse

| Operación | app.main | Estado |
|---|---|---|
| GET escenario/progreso; POST decisión/cierre | Sí | Intento existente propio y condiciones persistentes |
| Espera y comprobante de admisión | Sí, /scheduling | Sesión/convocatoria/matrícula y reglas vigentes |
| Consentimiento y aceptación | No | Solo servidor LAB; documento sintético |
| Provisión e inicio desde convocatoria | No | Solo LAB con políticas explícitas; no habilita inicio productivo |
| Reporte oficial por sesión | Ruta registrada | 503 mientras no exista consolidación oficial |
| Notificar calificación | Ruta registrada | 503, sin publicación ni aviso de nota |
| Autorizar repetición Identity | Ruta registrada | 503 por composición académica pendiente |
| Evaluation/resultados oficiales | Sin rutas | No se añade carpeta de endpoints ficticios |

El cierre no genera automáticamente una nota. No se habilitan consentimiento,
inicio, repetición o resultados en main ni se aprueban políticas mediante el LAB.

## Validaciones realizadas y límites

- `VALIDACION.json`: estructura JSON, cobertura de las 40 operaciones + documentación,
  variables declaradas, secretos exportados vacíos y sintaxis JavaScript mediante
  Node. No equivale a validación oficial de Postman ni importación en Desktop.
- Se ejecutan seis comprobaciones ASGI/TestClient sin PostgreSQL: health/OpenAPI
  200 y cuatro rechazos 401 sin token. Se bloquea Engine.connect para acreditar
  que estas comprobaciones no intentan SQL; no se sustituye autorización.
- `resultado_http_*.json`: ejecución TCP Python/httpx del recorrido guardado,
  PostgreSQL17 nuevo, JWT real y persistencia consultada desde otra Session.
  **No ejecuta los scripts pm.test**: estos siguen pendientes en Postman Desktop.
- Postman CLI y Newman no están instalados. No se instalaron. Postman Desktop
  está disponible para importación manual. La descarga del esquema oficial fue
  rechazada por HTTP; no se declara validación contra ese esquema remoto.
- Docker inicialmente no respondía; el usuario lo reanudó antes del recorrido TCP.
- Primera comprobación estática: su detector confundió cierres JSON con llaves de
  variables; se corrigió el detector. Primer recorrido TCP: 27 estados HTTP correctos,
  pero se detuvo al exigir cero commits para feedback. Su consulta existente usa
  `with s.begin()`: no realiza DML pero confirma la lectura. El verificador ahora
  informa ese commit expresamente, sin modificar el backend. Ambas situaciones
  están diferenciadas de un fallo funcional del producto; el JSON inicial se conserva.
- No se ejecutó la suite general; no hay cambios productivos. La advertencia
  existente de Starlette/httpx se conserva y no se instala otra dependencia.

Reproducción de preparación/verificación, sin Postman CLI:

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -B backend\docs\postman\generar_colecciones.py
.\.venv\Scripts\python.exe -B backend\docs\postman\validar_preparacion.py
# Crea y elimina SU PostgreSQL; no usar el laboratorio interactivo simultáneamente.
.\.venv\Scripts\python.exe -B backend\docs\postman\verificar_laboratorio.py
```

Si el equipo instala por separado Newman, ejecutar sobre un laboratorio nuevo,
con credenciales inyectadas por un mecanismo seguro fuera del repositorio. No
pasarlas como `--env-var clave=...` visible en historial/listado de procesos. No
se proporciona un comando con secretos inventados ni se instala un CLI aquí.

Antes de compartir: los JSON distribuidos siempre deben mantener secretos vacíos.
No exportar el entorno utilizado ni respuestas de login. Conservar los archivos
históricos, stash y .env; este incremento solo crea archivos bajo esta carpeta.


## Incremento: preparación académica docente privada

Colección adicional `Proyecto_Nuclear_preparacion_docente.postman_collection.json`:
7 solicitudes ordenadas (login docente/estudiante, preparación autorizada y cuatro
rechazos). `GET /scheduling/sesiones/{sesion_id}/evaluacion/preparacion` ya está en
app.main; solo DOCENTE con ámbito de sesión/caso/grupos y matrículas ciertas.
No devuelve rúbricas ni notas, publicable siempre false, sin DML/flush/commit.

Para capturas y precondiciones, leer `../PREPARACION_ACADEMICA_DOCENTE_HTTP.md`.
El Environment y recorrido integral de 30 pasos permanecen iguales. Las cifras de
RESULTADOS.md y VALIDACION.json pertenecen a la preparación histórica anterior;
no son la aceptación de la nueva ruta. Las siete comprobaciones actuales sin SQL
(incluyen el rechazo 401 de esta ruta) se guardan en evidencia nueva, sin sobrescribir
los JSON históricos. El validador acepta --salida y rechaza archivos ya existentes.

```powershell
$salidaPostman = "evidencias/postman_validacion_$(Get-Date -Format yyyyMMdd_HHmmss).json"
.\.venv\Scripts\python.exe -B backend\docs\postman\validar_preparacion.py --salida $salidaPostman
```

Los pm.test requieren ejecución manual en Desktop; Node solo comprueba sintaxis.
La regresión Backend de este nuevo incremento se registra en el informe HTTP,
no se atribuye a la ejecución histórica del catálogo.
