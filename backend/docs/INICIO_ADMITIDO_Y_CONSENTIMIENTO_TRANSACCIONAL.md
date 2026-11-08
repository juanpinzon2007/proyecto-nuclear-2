# Inicio interno: admisión y consentimiento en la misma UoW

6 de noviembre de 2026, America/Bogota. Rama feature/backend-continuidad,
HEAD 28be564 más cambios locales identificados por SHA-256. Sin nuevos commits.

## Diagnóstico del 401 anterior

Se conservaron log/JUnit de la relacionada anterior (668 aprobadas y un error de
preparación 401 en creación docente de espacio) y su general 2213/38 sin fallos.
Los metadatos anteriores acreditan un retroceso del reloj de pared de unas cinco
horas. No registraban la excepción de JWT o los claims causantes del rechazo:
**no es posible demostrar retrospectivamente la causa exacta de ese 401**.

Antes de modificar la integración se inspeccionaron las factories de tokens,
usuarios, configuración y fixtures: tokens por función, repositorios SQL y
restauración de overrides/cachés en finally. Se ejecutaron el nodo exacto (1
aprobado), las 21 pruebas HTTP de composición en orden inverso y la selección
relacionada completa (669 aprobadas). El 401 no se reprodujo ni se encontró una
contaminación demostrable. No se afirma haber descartado cualquier fallo intermitente.

Instrumentación solo en el proceso pytest: envoltura observacional de jwt.decode
que llama al original y propaga sus errores; registra clase de excepción y tiempo
monótono, sin tokens, secretos, claims ni datos de cuentas. Registra además la
diferencia entre reloj de pared y monótono. No altera leeway, firma, permisos o
credenciales. No se detectó salto temporal en las reproducciones ni en la general
final. Las pruebas negativas JWT siguen rechazando sus entradas. La causa histórica
permanece indeterminada; no se habilitan rutas nuevas como consecuencia del diagnóstico.

## Cambio mínimo y arquitectura

1. La dependencia HTTP existente autentica el JWT y recupera la cuenta real.
2. El coordinador conserva su UoW PostgreSQL READ COMMITTED y el advisory por
   convocatoria. Conserva locks de P existente, cuenta/rol/vínculos, matrícula,
   convocatoria, sesión, asignación, versión y rúbrica.
3. ConsultaVinculacionSQLAlchemy recibe AdmisionSQLAlchemy de esa misma Session.
   ConsultaIngresoSQLAlchemy reutiliza el validador de convocatoria y validar_ingreso.
   Scheduling exige concesión individual causal, convocatoria activa, matrícula
   vigente, sesión EN_CURSO, versión exacta y límites programados existentes.
   No se llama a una ventana de laboratorio en sustitución de una concesión.
4. La admisión ya incluye comprobación de matrícula; luego la consulta termina
   de verificar el puente de asignación/grupo/caso/versión. Se conserva el orden
   de locks existente: no se reordenan fuentes para aparentar otro orden lógico.
5. FuenteConsentimientoSQLAlchemy y exigir_aceptacion resuelven el documento
   seleccionado por el servidor y su evidencia explícita en la misma transacción.
   Las composiciones históricas con fuente provisional LAB permanecen identificadas
   como tales: no acreditan consentimiento institucional ni se configuran en producción.
6. Se reutilizan las políticas explícitas, grafo SQL, duración y ServicioInicio.
   Todas las condiciones de creación combinada se validan antes del INSERT P.
7. INSERT P conserva la FK histórica a la aceptación; INSERT I utiliza la misma
   aceptación. Solo la UoW existente confirma la operación completa.

AdmisionSQLAlchemy añade el argumento interno bloquear=False. Los dos escritores
lo instancian con True: bajo los locks previos, adquiere SHARE de la fila de
auditoría que acredita la concesión, antes de verificar su contenido. Protege esa
evidencia hasta commit sin modificarla. Las consultas conservan su valor anterior,
sin locks adicionales ni escrituras. No es otra autorización o UoW.

El inicio directo sobre una P existente también exige PostgreSQL READ COMMITTED y
admisión SQL, además de su consentimiento/ámbito/políticas anteriores. No queda
como alternativa para saltar la concesión. Errores Identity/infraestructura de la
admisión se traducen a los errores de Participation existentes, sin cambiar HTTP.

## Garantías y límites

- Consultar admisión o aceptar en una petición previa no basta: se revalidan las
  condiciones bajo los locks de inicio. Retirar convocatoria o matrícula antes
  de iniciar hace que se rechace antes de INSERT P.
- La publicación concurrente de otra versión documental se serializa con la UoW.
  Una prueba comprueba un bloqueo PostgreSQL real mediante pg_stat_activity.
  Si el inicio precede a la selección nueva, P/I conservan la aceptación anterior;
  no se reescriben. Si la selección nueva ya se confirmó, la aceptación antigua
  se rechaza antes de P.
- Dos inicios simultáneos producen 201 y 409, una sola P y un solo I. Repetir la
  consulta/provisión autorizada de P devuelve 200 con la misma P; no se inventa
  recuperación automática del primer I ni idempotency-key. Cierre sigue idempotente.
- Un fallo inyectado después del INSERT I revierte también P; la aceptación
  HTTP previamente confirmada sobrevive, pues corresponde a otra transacción.
- No se añaden restricciones universales de admisión en P mediante SQL. La
  garantía nueva cubre escritores de servicio/UoW y sus locks; un escritor SQL
  privilegiado sigue pudiendo eludir reglas de aplicación. La prueba de P histórica
  sin concesión prepara ese estado en laboratorio y verifica que no puede iniciar.
- Se conserva el control de respuestas inmutables, las versiones históricas y
  las protecciones existentes. No se modifica ni invoca un cálculo oficial de notas.

## Pruebas y evidencias auténticas

| Ejecución nueva | Aprobadas | Omitidas | Fallidas | Errores | Advertencias |
|---|---:|---:|---:|---:|---:|
| Reproducción del nodo 401, antes del cambio | 1 | 0 | 0 | 0 | 1 |
| Composición HTTP en orden inverso, antes del cambio | 21 | 0 | 0 | 0 | 1 |
| Relacionada antes del cambio | 669 | 0 | 0 | 0 | 1 |
| Aceptación inicial nueva | 10 | 0 | 0 | 0 | 1 |
| Relacionada con expectativa antigua de proveedor | 678 | 0 | 1 | 0 | 1 |
| Prueba adaptada de proveedor fallido | 2 | 0 | 0 | 0 | 1 |
| Aceptación final nueva | 11 | 0 | 0 | 0 | 1 |
| Relacionada final | 680 | 0 | 0 | 0 | 1 |
| General final | 2224 | 38 | 0 | 0 | 1 |

No sumar ejecuciones solapadas. Aceptación final: 31.50 s; relacionada final:
346.19 s; general: 1094.21 s. Advertencia conocida Starlette/httpx. Las 38
omisiones son los 29 casos antiguos Identity y 9 Participation dependientes de
URLs externas, no resultados positivos. Las 11 nuevas pruebas sí ejecutan PG17.

El fallo intermedio fue DID NOT RAISE RuntimeError al probar un proveedor de ventana
que Scheduling no consulta al recibir admisión real. La prueba negativa se conserva
con sus dos escenarios: ahora falla la lectura SQL de la evidencia causal, o la
política de vinculación. Se comprueba rollback y ausencia de P/I. No se elimina,
omite ni debilita el objetivo; se registra la sustitución del contrato de entrada.

Los dos helpers anteriores de preparación de intentos/composición HTTP ya no
suponen que EN_CURSO concede permiso. Registran espera con registrar_espera y
congelan la concesión mediante el coordinador real de habilitación. Son preparación
administrativa LAB. Las nuevas aceptaciones además usan JWT real, espera y
habilitación docente HTTP en app.main, consentimiento HTTP en app aislada y
repositorios/modelos/relaciones SQL reales, sin mocks para reemplazarlos.

Archivo: tests/integration/test_admitted_start.py. Los 11 escenarios acreditan:
recorrido de login/aceptación/espera/habilitación/inicio/respuestas/progreso/cierre;
no admitido; retirada tras consulta positiva; matrícula inválida; aceptación ausente,
antigua o ajena; concurrencia; P preexistente sin admisión; rollback; cambio documental
concurrente e historial. Se comprueba persistencia desde otra Session y cero resultados.

Evidencias: evidencias/inicio_admitido_20261106T155628Z/, con comandos, HEAD, hashes,
JUnit, logs y diagnostico_jwt.json. Se conserva también toda la evidencia anterior.
Fuentes estables durante cada corrida. Configuración de pytest sin .env/URLs
externas; exclusivamente contenedores nuevos postgres:17, puertos efímeros y tmpfs,
eliminados por el fixture usando su ID propio. Sin limpieza global de Docker.

Reproducción PowerShell desde la carpeta original:

```powershell
.\.venv\Scripts\python.exe evidencias\inicio_admitido_20261106T155628Z\ejecutar_validacion.py casos
```

Grupos adicionales: focal, total, repeticion y orden (inverso). No editar fuentes
mientras se ejecutan. Los reportes identifican código local mediante hashes, no
únicamente el HEAD confirmado.

## Registro real en main y bloqueos

Main conserva GET current-scenario, GET progress, POST decisions y POST finish
bajo /api/v1/attempts/{attempt_id}. También conserva POST /scheduling/validar-ingreso,
POST /scheduling/convocatorias/{convocatoria_id}/espera y GET de admision.
No se registra la aceptación de consentimiento ni provisión/inicio desde convocatoria.
No se activa una ruta general de Participation, PUT público ni notas oficiales.

El documento institucional y el proceso autorizado de publicación/selección siguen
pendientes. Los datos documentales y las políticas de inicio/provisión de las
pruebas son SOLO LAB; no se instalan como valores productivos. Una huella o autoridad
escrita en metadatos no demuestra una aprobación auténtica. El borrador permanece
NO APROBADO. Las políticas obligatorias de inicio deben componerse explícitamente
por el servidor; no se inventan repetición, recuperación o vencimiento.
RF-12 sigue PARCIAL. RF-22 se conserva en su estado previo, con nueva evidencia de
integración transaccional; no se cambia otro RF/RNF por inferencia.

## Archivos del incremento

Runtime (sin cambios a ORM ni migraciones):

- app/modules/participation/infrastructure/academic_context.py
- app/modules/participation/infrastructure/provision.py
- app/modules/participation/infrastructure/start.py
- app/modules/scheduling/infrastructure/admission.py

Pruebas (rutas bajo backend): test_attempt_start.py, test_participation_http_composition.py,
test_participation_provision.py y el nuevo tests/integration/test_admitted_start.py.
Documentación: este informe, la fila/evidencia RF-12 de la matriz vigente y el
nuevo CHECKPOINT_INICIO_ADMITIDO_20261106.json. Los documentos anteriores son historia
preservada; la falta de composición interna de admisión queda sustituida por este informe.

Se verificaron al inicio las 33 rutas/tamaños/SHA del manifiesto anterior. El nuevo
manifiesto identifica los cambios legítimos posteriores y propone dos bloques con
rutas exactas, sin staging ni commits: núcleo de persistencia/transacción y API/aceptación
HTTP. Incluye el manifiesto anterior como referencia histórica. Excluye evidencias
temporales, respaldos, .env, ZIP, Word, cachés y arrastres ajenos. No borra esos archivos.

Una cabeza Alembic 20261106_consent_versions y 33 tablas metadata, sin cambios de
esquema de este incremento. No se aplicaron migraciones a bases permanentes.
Git permanece en HEAD 28be564, feature/backend-continuidad; refs, stash, .env y
archivos previos preservados. Las ocho fuentes Python coinciden con la general final.

Siguiente paso: obtener documento/proceso institucional autorizados y revisar la
configuración de inicio obligatoria antes de decidir el montaje productivo. No
activar el inicio ni otra fase como consecuencia de esta aceptación técnica.
