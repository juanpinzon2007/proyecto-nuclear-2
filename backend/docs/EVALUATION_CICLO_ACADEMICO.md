# Ciclo académico de Evaluation — 8 de noviembre de 2026

Base: `f031907ac6efe46dbedd0ccd7b470d467bc0523b`, rama `feature/backend-continuidad`.
Código registrado en **app.main**, validado solamente con datos sintéticos y PostgreSQL17
nuevo/desechable. Ninguna migración se ha aplicado a bases permanentes.

## Contrato efectivo

- Reutiliza PREGUNTAS_100_V1 y su persistencia exacta. No hay otro calculador ni
  nueva ponderación. Los resultados técnicos siguen siendo no oficiales.
- Una evaluación se delimita por participación y asignación histórica: estudiante,
  sesión, grupo y versión de caso. Máximo Decimal de sus intentos autorizados;
  un caso diferente no se mezcla. En empate se referencia el menor ID solo para
  determinismo; se conservan todos los intentos y la nota no cambia.
- Toda repetición exige permiso individual verificable de un uso. `intentos_base`
  no sustituye ese permiso al consolidar. Las concesiones nuevas tienen capacidad
  uno. El guard SQL respeta la capacidad registrada de permisos históricos, pero
  una concesión histórica múltiple no se acepta como permiso individual actual
  para publicar. No se convierten ni se recalifican esos registros.
- Una convocatoria ACTIVA sin intentos queda pendiente hasta confirmación docente
  expresa de ausencia, con motivo/actor/fecha/revisión. Su cero no crea participación,
  consentimiento, selección ni intento ficticios. Tener un intento impide declarar
  ausencia. Rectificar agrega otra revisión; no borra la confirmación anterior.
- RETIRADA se excluye de notas y queda en el snapshot como antecedente.
- Provisional solo por configuración docente explícita, y solo cuando todos los
  intentos propios estén cerrados y tengan resultado técnico verificable. No se
  muestran aciertos/justificaciones mientras la sesión permanezca activa.
- Publicar requiere sesión FINALIZADO, cohorte activa íntegra y resuelta, revisión
  actual por SHA-256 y autorización docente explícita. Publicar de nuevo la misma
  revisión recupera el mismo ID; no repite auditoría ni avisos.
- Una corrección necesita otra revisión válida y otra autorización de publicación.
  Mientras esté pendiente, continúa vigente la última publicación. Las anteriores
  son inmutables y conservan el contenido/identificadores de su aprobación.

Fuente académica: `ProyectoNuclear-IngenieriaSoftwareII (1)`, RF-13/14/24/25/27;
fuente funcional posterior: instrucciones del usuario y confirmaciones explícitas
sobre ámbito por participación, retiradas y visibilidad (8/11). No se atribuye a
la institución una aprobación de consentimiento ni de políticas adicionales.

## Operaciones reales

Todas bajo `/scheduling`, JWT real, cuenta/rol y relaciones revalidadas en SQL.
No se conceden atribuciones implícitas a ADMINISTRADOR ni DOCENTE ADMINISTRADOR.

| Método/ruta relativa | Contrato |
|---|---|
| GET `/sesiones/{s}/evaluacion/consolidacion` | Revisión docente; pendientes, filas y hash, sin calcular resultados nuevos. |
| POST `/sesiones/{s}/evaluacion/convocatorias/{c}/ausencia` | Body `{motivo}` explícito. Confirma ausencia; todavía no publica. |
| POST `/sesiones/{s}/evaluacion/convocatorias/{c}/ausencia/rectificacion` | Body `{id_confirmacion,motivo}`. Revisión append-only. |
| PUT `/sesiones/{s}/evaluacion/visibilidad` | Body `{mostrar_provisional: boolean}` estricto; actor/fecha persistidos. |
| POST `/sesiones/{s}/evaluacion/publicaciones` | Body `{revision_sha256}` de la revisión; publicación manual atómica. |
| GET `/sesiones/{s}/evaluacion/publicaciones` | Última versión oficial, solo docente del ámbito autorizado. |
| GET `/convocatorias/{c}/resultado` | Estudiante titular del JWT y convocatoria; oficial vigente o provisional habilitado. |

Se reutiliza POST `/api/v1/identity/excepciones/repeticiones`, cuerpo original
`{id_sesion,id_estudiante}`: ahora devuelve permiso nativo; fecha original e ID
se conservan en replay. Concede permiso, **no inicia** un intento. Sesión EN_CURSO,
intentos anteriores cerrados, docente creador y ámbito persistente obligatorios.

Errores: 401 autenticación, 403 ámbito/rol, 404 resultado no disponible,
409 estado/revisión incompatible, 422 body inválido, 503 integración/fuente no
acreditable. Sin cache. Ninguna operación acepta notas del cliente.

## Datos e integridad

Migración `20261108_academic_publication`, padre `20261107_question_results`:

- `ausencia_academica`: confirmación/rectificación verificable por convocatoria.
- `publicacion_evaluacion`: versión autorizada de sesión y documento/huella histórica.
- `resultado_participacion`: snapshot oficial por publicación/convocatoria; referencia
  al resultado técnico elegido o a una ausencia confirmada. ID participación nullable
  solo para no inventar una participación de quien no participó.
- Tres columnas nullable de visibilidad en sesión y FK causal nullable en notificación.
- UQ publicación/versión, publicación/convocatoria y aviso/publicación/convocatoria;
  FK reales, checks de nota/origen y triggers de contexto, inmutabilidad y completitud.
- Guard adicional de consumo de permiso: bloquea participación y permiso antes de
  comprobar usos. Protege INSERT SQL concurrentes; no altera permisos históricos.

36 → **39 tablas físicas**. Se mantienen las 28 entidades del DBML académico original
sin modificar ese archivo: las ampliaciones son persistencia técnica/histórica explícita,
no una afirmación de que el esquema físico sigue teniendo exactamente 28 tablas.

Cambio, auditoría y aviso INTERNA comparten UoW. Una falla SQL revierte el conjunto;
el cálculo y el cierre del intento siguen independientes. No hay envío SMTP, outbox ni
promesa de entrega externa exactamente una vez. Los locks serializan las operaciones;
un deadlock/serialización produce conflicto recuperable y rollback, no otro resultado.
Los GET usan Session propia REPEATABLE READ / READ ONLY, sin flush/commit/DML.
RBAC es aplicación con verificación PostgreSQL; los triggers no sustituyen los permisos
operativos del usuario SQL ni protegen contra un superusuario que los deshabilite.

Downgrade solo en vacío: rechaza borrar historia/configuración académica. Aplicar
esquema antes de desplegar este código; el ORM actual necesita las columnas nuevas.
Para reversión operativa puede mantenerse el esquema compatible y volver al código
previo; no se autoriza borrar historia. Guardas y migraciones anteriores intactas.

## Evidencias y compatibilidad

`tests/integration/test_academic_cycle_http.py`: 20 aceptaciones PG17/main/JWT,
ausencias sin intentos, rectificación, cohortes retiradas, publicación idempotente,
max entre intentos propios, permiso de un uso, privacidad, lectura sin DML,
concurrencia, rollback, inmutabilidad, subida/bajada y TCP real para Postman.

Correcciones de compatibilidad demostradas durante la general:

1. Worker separado no importaba el destino de la nueva FK: NoReferencedTableError.
   Se registra el metadata compartido antes de su sesión, sin cambiar State/horarios.
2. Mocks del antiguo contrato void ahora devuelven None expresamente, no un Mock
   tomado como ID. Las aserciones de autorización y commit se conservan.
3. Fixtures históricas incorporan solo columnas nullable auxiliares del ORM actual;
   no estampan migraciones nuevas ni simulan sus guards. Head nuevo se compara sin filtros.
4. Inventarios y prueba TRUNCATE incluyen las nuevas dependencias. La consulta de
   reporte sigue sin inferir ausencias ni escribir resultados, aunque la tabla ya exista.

20 focalizadas actuales aprobadas. Relacionada de correcciones: 212 aprobadas.
General anterior a la última validación adversarial: 2435 aprobadas, 38 omitidas,
cero fallos/errores, en cuatro grupos disjuntos. No sumar esas suites solapadas.
El resultado general de la versión final se registra en
`evidencias/implementacion_academica_20261108/RESUMEN_GENERAL_FINAL.json` y sus JUnit/logs.
Se conservan los fallos intermedios (incluida general 2425/38/10) y sus fuentes.
Las omisiones son las históricas por configuración externa; no acreditan esos tests.

## Sustentación reproducible

En PowerShell, desde el repositorio original:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
& .\.venv\Scripts\python.exe -B backend\docs\postman\laboratorio_publicacion.py --puerto 8765
```

Docker Engine activo e imagen postgres:17 instalada. El helper crea PG nuevo, no usa
.env, solicita secretos **sintéticos** sin eco y monta app.main en loopback. Prepara
administrativamente una sesión finalizada y un intento VENCIDO con resultado 33.33;
no acredita inicio/consentimiento/cierre docente productivos. Enter limpia solo el
servidor/contenedor propios.

Importar `Proyecto_Nuclear_publicacion_academica.postman_collection.json` y el
environment sin secretos. Completar localmente los recursos impresos, clave/código
sintéticos, `laboratorio_confirmado=true` y `permitir_escrituras_laboratorio=true`.
Ejecutar **solo esa colección**, una iteración: tres logins, revisión, publicación,
replay, lectura docente, lectura titular, ajeno 403 y anónimo 401. En Send manual,
colocar tokens únicamente en valores locales privados: pm.variables encadena el Runner.
No capturar/exportar respuestas de login ni cabeceras Authorization.

Capturas: revisión publicable/hash; POST versión 1 oficial; replay mismo ID;
GET titular 33.33; docente ajeno 403; anónimo 401. El catálogo general no es un Runner
integral. CLI/Newman ausentes: sintaxis/estructura verificadas y HTTP TCP Python real,
**no** ejecución pm.test de Postman. Se mantienen los seis artefactos de entrega originales.

## Límites y continuidad

RF-13 y RF-24 siguen PARCIAL: el cierre voluntario anterior a FIN carece de clasificación
académica aprobada; se rechaza su cálculo/publicación. No se transforma en vencimiento.
RF-14 y RF-25 avanzan de BLOQUEADO a PARCIAL: consulta real/configuración y permiso
nativo disponibles; faltan generalización a cierres pendientes e inicio productivo
extra seguro. Casos diferentes no comparten evaluación sin vínculo aprobado.
RF-27 queda IMPLEMENTADO para avisos internos de publicación/feedback; correo externo
sigue siendo una dependencia diferente de RF-21. RF-16 continúa BLOQUEADO para
exportación oficial: no se han añadido Excel/PDF en este lote.

Inicio/consentimiento/provisión no están registrados en main. Falta fuente oficial
institucional publicada de consentimiento y composición productiva acreditada;
no se sustituye por el borrador ni por políticas LAB. Recorridos multipregunta/ciclos
siguen cerrados. DOCENTE ADMINISTRADOR y permisos individuales requieren definición.

RF-19 original dice “un día después del fin previsto” (PDF p.4); se conserva +24h.
Agile Inception especifica Python/FastAPI; no se cambia a Django por una referencia
anterior. Angular corresponde al frontend. No se acreditan rendimiento, disponibilidad
ni los 14 RNF íntegros sin mediciones/despliegue representativos.

Siguiente lote recomendado: RF-16 Excel/PDF privados desde la última publicación,
reutilizando el snapshot oficial y su autorización. Antes, presentar este bloque para
revisión; no comenzar otros módulos ni declarar el backend completo.


## Cierre de validación del lote

General final: **2436 aprobadas, 38 omitidas, 0 fallidas y 0 errores**. Son 2474
casos de 114 módulos, distribuidos en cuatro grupos de archivos disjuntos. La
agregación verificó por módulo la cobertura de la suite completa; no se suman las
20 focalizadas ni las 212 relacionadas. Cuatro ocurrencias de la misma advertencia
conocida de Starlette (un proceso por grupo). Logs, JUnit originales y agregado:
RESUMEN_GENERAL_FINAL.json / junit_general_final.xml. Código/pruebas estables durante
las ejecuciones, sin skips/xfails nuevos. Se preservan todos los diagnósticos rojos.

La preparación docente v1 conserva su DTO conservador (publicable=false): no es la
nueva revisión para autorizar publicación. Utilizar `/evaluacion/consolidacion` y
su hash para el comando explícito. No interpretar los diagnósticos antiguos como
una autorización para publicar o como sustituto de la nueva revisión.


Aceptación repetible desde PowerShell (solo proceso hijo, sin .env ni URLs externas):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
$validacion = @'
import os
for k in list(os.environ):
    if k.startswith(('POSTGRES_','IDENTITY_','PARTICIPATION_')) or k in ('DATABASE_URL','TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL'):
        del os.environ[k]
os.environ.update(SPS_TEST_IDENTITY_MAPPING_DOCKER='1',SPS_TEST_POSTGRESQL='0')
from app.core.config import Settings,get_settings
Settings.model_config['env_file']=None
get_settings.cache_clear()
import pytest
raise SystemExit(pytest.main(['-c','backend/pyproject.toml','backend/tests/integration/test_academic_cycle_http.py','-q','-rs','-p','no:cacheprovider']))
'@
& .\.venv\Scripts\python.exe -B -c $validacion
```

Para repetir la general, sustituir el archivo por `backend/tests` y `backend/app/modules/participation/tests`; no habilitar las variables de bases externas. Los cuatro comandos finales y su partición están en `ejecucion.json` y `particiones_general.json`.
