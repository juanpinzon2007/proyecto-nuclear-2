# BD2-02B — Resultado del ER oficial en PostgreSQL desechable

**Fecha de informe: 2026-11-01. Rama: feature/integracion-backend. Resultado: viable estructuralmente en PostgreSQL 17; compatibilidad funcional con el backend actual NO demostrada.**

## 1. Qué se ejecutó

Desde el DBML original se generó [er28_experimental.sql](er28_experimental.sql) y se creó el esquema literal completo en una base nueva y aislada. No se importaron los modelos productivos ni se ejecutó el backend o su cadena Alembic allí. Los scripts son experimentales y están exclusivamente en esta carpeta.

La fuente conserva SHA-256 fb6ab07cfdfee38ba59e1acc879335ec0b377150acc3474b4a817a9eece229d7. El generador verifica ese hash y los conteos antes de crear el laboratorio; no cambió el original ni el objetivo académico.

| Elemento | Original / esperado | Catálogo PostgreSQL observado |
|---|---:|---:|
| Tablas de usuario, todos los schemas | 28 | 28, todas en public |
| Columnas reales | 144 | 144 |
| PK | 28 | 28 |
| FK | 40 | 40, incluidas las dos compuestas |
| UNIQUE adicionales | 19 | 19 |
| Índices | Soporte de 28 PK + 19 UQ | 47 únicos; ninguno no único adicional |
| CHECK / triggers de usuario | Ninguno declarado | 0 / 0 |

Se verificó cada columna: orden, tipo, longitud, precisión/escala, nulabilidad, default e identidad. Cada FK se comparó por columnas ordenadas, padre y clave destino; acciones NO ACTION/MATCH SIMPLE y no diferible. No hay tablas auxiliares, vistas que sustituyan entidades ni alembic_version. Las secuencias de identidad no son tablas.

Inventario legible: [INVENTARIO_EJECUTADO.md](INVENTARIO_EJECUTADO.md). Catálogo y resultados completos: [evidencia final](evidencia_6942afe5800a40b6836f2e43b3e74793.json).

## 2. Pruebas ejecutadas, no solo análisis

Una fila estrictamente sintética se insertó en cada tabla siguiendo dependencias. Todo el grafo Cases pudo referenciar padres INTEGER: caso, escena, personaje, asociación personaje/escena, criterio/decisión, opción, objetivo y pista. Esto era imposible en la metadata vigente sin adaptación, pero funciona al construir el ER aislado con sus padres reales.

| Grupo de probes | Cantidad | Resultado final |
|---|---:|---|
| FK con referencia inexistente | 40 | Rechazo SQLSTATE 23503 |
| FK compuestas con IDs existentes que no forman el par | 2 | Rechazo 23503: opción/decisión y nivel/criterio |
| UNIQUE | 19 | Duplicados rechazados con 23505 |
| NOT NULL, incluidas PK | 131 | NULL explícito rechazado con 23502 |
| Inserción válida que debe revertirse | 1 | 00000, revertida |
| Ambigüedades de ámbito que el esquema permite | 5 | 00000, aceptadas y revertidas |
| Total | **198** | **198 observaciones satisfechas, 0 discrepancias** |

Dos UNIQUE (opción/decisión y nivel/criterio) incluyen la PK y no pueden violarse independientemente de ella. Su presencia/índice se comprobó en catálogo; los dos probes de duplicado pueden ser rechazados por la PK. No se afirma haber aislado esas UQ de la PK. Son necesarias como claves candidatas exactas de las FK compuestas y no se propone eliminarlas.

Los 13 campos nullable se poblaron con NULL en la fixture inicial. Ningún probe persistió datos adicionales: al finalizar siguió habiendo exactamente una fila sintética por cada tabla y el inventario era idéntico al anterior a las pruebas.

Los errores SQL esperados se ejecutan bajo SAVEPOINT y se captura SQLSTATE antes del rollback; el programa exige una respuesta por prueba y el estado exacto esperado. ON_ERROR_STOP se desactiva solo en ese lote para observar errores previstos, no para ocultarlos. La creación del esquema usa ON_ERROR_STOP=1 y transacción. Los estados y una cola de errores PostgreSQL reales están en el JSON.

### Historial íntegro de intentos

| Evidencia / contenedor propio | Resultado |
|---|---|
| [f163cc…](evidencia_f163cc91723c496a9ac770682d90f430.json), 302ce31569fe51c3d73f647e2e1153d1c705343011dcd4349aea1d07c0b2c8e1 | Detenido antes de SQL por inspección incompleta de tmpfs; eliminado |
| [cacf81…](evidencia_cacf81a7704a4621bcbf6f38d2b6e4c1.json), 2c98511b9e09f05faee7b6a7b448720ea767e3a19df953d2efb9cc59a49551eb | Inventario exacto; 195/196 probes coincidentes, una fixture chocó con UQ de feedback antes de su FK; eliminado |
| [ec85c0…](evidencia_ec85c047dd9b47bdadd6101348abb0d8.json), f187524eb8bff339ce14c61eb462efed4803d7620e6c8777d64035872ec69216 | 196/196; eliminado |
| [9ca8d9…](evidencia_9ca8d9e46e8e43cebd7ad670efd4e243.json), 3153c2eb963353607e84726a7e8d16a54f40c0ef1230fe26e93184f26a2f6f31 | Añadidos pares FK con IDs existentes: 198/198; eliminado |
| [6942af… final](evidencia_6942afe5800a40b6836f2e43b3e74793.json), bb35c3e040df1fdee6dddf43c49cca1a6dec2f4a69f469274932d42850917562 | Reforzado inventario de todos los schemas: 198/198; eliminado y ausencia verificada |

Docker expone --tmpfs mediante HostConfig.Tmpfs y no necesariamente en Mounts. El primer guard exigía Mounts no vacío y detuvo el ensayo; se corrigió la inspección y además se verificó el montaje **real** tmpfs en /proc/self/mountinfo. No se omitió un control de aislamiento.

La prueba de profesor de feedback reutilizaba una asignación que ya tenía comentario UNIQUE, produciendo 23505 antes del 23503 buscado. Se preparó otra asignación sintética válida dentro del SAVEPOINT para aislar la FK. **El SQL del esquema y el ER no cambiaron para corregir la fixture.** También se corrigieron rutas y lectura CRLF del generador antes de ejecutar SQL.

## 3. Aislamiento y eliminación demostrados

Laboratorio final:
- ID completo: bb35c3e040df1fdee6dddf43c49cca1a6dec2f4a69f469274932d42850917562.
- Nombre: sps-er28-lab-92afb762c79d482eb21aa4787ce1ada6.
- Imagen: postgres:17, ID sha256:3b0cda93be7c8dba2ed484d19393d93845dc3dafb88973e248ba8e6d99d784e1.
- PostgreSQL real: server_version_num=170011 (17.11), base er28_experiment y rol er28_lab.
- NetworkMode=none, ningún puerto publicado y ningún bind/volumen persistente. Configuración tmpfs y montaje real de /var/lib/postgresql/data comprobados.
- TCP se usó **solo dentro** del contenedor, con psql -h 127.0.0.1. No se utilizó socket de inicialización como prueba de disponibilidad ni se abrió puerto del host.
- Contraseña generada en memoria y transferida por entorno efímero a Docker/psql; no .env, URL del proyecto, credenciales reales ni secretos en archivos.
- docker rm --force **de ese ID propio** terminó con código 0; la inspección posterior devolvió código 1 con No such. cleanup=removed_verified.

Los cinco contenedores de los intentos anteriores también tienen eliminación verificada. No se accedió a contenedores existentes, no hubo compose, prune o limpieza global. No se conectó a bases del equipo, desarrollo o producción.

## 4. Ambigüedades observadas del original

Estas aceptaciones son hallazgos reales del motor, **no aprobaciones académicas** ni defectos corregidos:

| Sonda aceptada | Lo que falta controlar |
|---|---|
| Opción con escena destino de otro caso | La FK valida existencia, no mismo caso |
| Decisión con criterio de la rúbrica de otro caso | El ámbito decisión/criterio/rúbrica no está cerrado por las FK simples |
| Personaje de otro caso enlazado con escena existente | La asociación no verifica pertenencia al mismo caso |
| Intento con consentimiento de otro usuario y repetición sin permiso extra | Las FK individuales no unen titular ni hacen cumplir RF-25 |
| Varios pasos de la misma decisión en el mismo intento | Solo hay UNIQUE(intento,número), no una respuesta vigente única por decisión; requiere contrato de historial/proyección |

La cuarta sonda combina dos hechos en una inserción aceptada, no pretende medir dos validadores separados. El catálogo también confirma ausencia de CHECK para estados/horarios/ponderaciones. El experimento no valida roles, vigencia de consentimiento, fórmula de rúbrica ni cambios de ruta; esas son responsabilidades de aplicación o decisiones de integridad por aprobar. No se añadieron triggers/CHECK para simular que estuvieran resueltas.

## 5. Comparación estática con el backend vigente

Se revisaron los archivos existentes sin ejecutarlos contra el laboratorio:
- [Caso/versión/escenario/pregunta/opción](../../../app/modules/cases/infrastructure/models/caso.py).
- [Rúbricas/criterios/niveles/valoración](../../../app/modules/cases/infrastructure/models/rubrica.py).
- [Contratos y rutas Cases](../../../app/modules/cases/api/router.py), [CasoService](../../../app/modules/cases/application/services/caso_service.py), [repositorio](../../../app/modules/cases/infrastructure/repositories/caso_repository.py).
- [Scheduling ORM](../../../app/modules/scheduling/infrastructure/models.py) y [programar_sesion](../../../app/modules/scheduling/application/programar_sesion.py).
- [8A](../../../app/modules/participation/application/integration_ports.py), [adaptador](../../../app/modules/participation/infrastructure/integration.py) y [ports INTEGER previos](../../../app/modules/participation/application/ports.py).

| Área | Compatible / adaptable | Incompatibilidad confirmada estáticamente |
|---|---|---|
| Identity y BD2-01 | Las cuatro tablas de acceso y tres de organización/consentimiento tienen estructura oficial compatible | Eso no certifica políticas de matrícula/consentimiento ni autoriza duplicar cuentas |
| Caso | Puede representarse contenido como caso oficial INTEGER | ORM espera caso.id UUID y contenido en version_caso; no existe caso.id_caso en el vigente |
| Versionamiento | Backend conserva edición exacta y rúbrica por versión | ER no tiene version_caso; una sola fila caso no puede sustituir dos ediciones distintas sin una decisión |
| Escena/decisión | Texto, orden, opciones y explicaciones tienen función cercana | escenario/pregunta UUID no equivalen directamente a escena/decisión INTEGER; faltan título/tipo y criterio directo |
| Rúbrica | Se guardan criterios/niveles y puntajes | peso/puntaje actuales no prueban porcentaje/logro; valoracion_opcion admite varios criterios frente a uno por decisión |
| API Cases | Es posible diseñar adaptadores posteriores | Las rutas principales consumen version_id UUID y devuelven caso_id/versión UUID; no cambiar a entero silenciosamente |
| Scheduling | Selecciona versión publicada concreta | FK sesión→version_caso.id y datos de espacio/convocatoria no existen con esa forma en las 28 |
| Participation | Dominio previo ya utiliza INTEGER; 8A preserva referencias | 8A transporta convocatoria/sesión/caso/versión/rúbrica UUID. El laboratorio no crea ese puente ni inicia intentos |
| Tipos/retención | Nuevas PK INTEGER legítimas pueden generarse para entidades destino | No hay cast UUID→INTEGER que preserve identidad; timestamps con zona del backend y sin zona del ER requieren contrato explícito |
| Conteo | El ER literal sí produce 28 tablas de usuario sin auxiliares en este ensayo | Las 22 integradas del backend no pasan a ser estas 28 automáticamente; control Alembic añadiría su propia tabla si se usara |

La comparación de contratos es estática. No se intentó arrancar FastAPI, usar JWT ni conectar los repositorios actuales a este esquema. **No hay demostración de compatibilidad funcional.**

## 6. Estrategia recomendada y autorizaciones siguientes

El ensayo elimina el bloqueo de factibilidad SQL: el ER se puede materializar literalmente. No elimina la incompatibilidad de identidad, versiones y granularidad del backend.

Recomendación concreta: mantener intacto el backend y aprobar primero la representación del caso/edición destino. Después diseñar un adaptador de lectura de Cases que conserve los UUID públicos y la edición exacta; ensayarlo con datos sintéticos en otro incremento aislado. No intercambiar repositorios productivos aún ni migrar datos del equipo.

Decisiones necesarias:
1. Aceptar cada edición como caso oficial independiente o aprobar una representación alternativa dentro de las 28; nunca fusionar ediciones ni perder su rúbrica.
2. Si hay que conservar UUID lógico/versión y otros atributos, aprobar campos de procedencia/compatibilidad dentro de tablas existentes. Mantener 28 entidades no autoriza por sí solo cambiar el ER.
3. Resolver criterio único por decisión frente a valoración multicriterio antes de trasladar evaluaciones. No sumar/reducir datos de origen para aparentar equivalencia.
4. Definir verificaciones de mismo caso, titularidad y repetición como reglas de servicio/constraints explícitas; las cinco sondas aceptadas no son rutas de acceso autorizadas.
5. Reconciliar después Scheduling/convocatoria/8A y la salida de estructuras de soporte, con correspondencias verificadas y sin borrar fuentes.

Si se exige a la vez conservar exactamente todos los atributos/relaciones originales, retirar todo soporte y mantener todos los contratos actuales sin pérdida, la compatibilidad no está demostrada y hay diferencias sin destino literal. No se oculta esa condición almacenando relaciones en textos/JSON o inventando UUID.

No se amplía a 40, no se cambia la cabeza 20261101_er28_base_academica y no se modifica Base.metadata productivo (22 según su estado previo). La suite del backend no se ejecutó: **1114 aprobadas/38 omitidas permanece como antecedente**, separado de los 198 probes SQL experimentales.

## 7. Archivos y cierre

Archivos nuevos únicamente en backend/docs/bd/laboratorio_er28/: generador, SQL experimental, ejecutor de pruebas, cinco evidencias JSON, inventario ejecutado, README e informe. No se modificaron archivos previos, ER, ORM, Alembic, .env, BD2-01, 8A ni los siete patrones. Sin commit/push/merge/cambio de rama.

Las [instrucciones de reproducción](README.md) detallan las conversiones DBML→PostgreSQL y los límites. El cierre comprueba hashes de archivos preexistentes, hashes de código/SQL registrados en la evidencia final, enlaces y git diff --check.

Resultado del cierre: los 254 archivos preexistentes registrados conservan sus hashes, incluidos los cuatro documentos locales ignorados por Git. Las once altas están exclusivamente en la carpeta autorizada. Coinciden los tres hashes de artefactos ejecutados y el del DBML original con la evidencia final. Los enlaces locales resuelven correctamente; ambos scripts superan el análisis sintáctico. `git diff --check` y la comprobación de espacios de los once archivos nuevos no presentan incidencias. La rama sigue siendo `feature/integracion-backend`.

**Viabilidad estructural confirmada; compatibilidad funcional pendiente. BD2-02C y BD2-03 no comenzaron.**
