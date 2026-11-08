# RF-19: operación del worker independiente

5 de noviembre de 2026, America/Bogota. Base local `33981c8`, sin commits nuevos.

## Selección previa y criterios de aceptación

Se reutiliza la matriz de 27 RF y 14 RNF de
`AUDITORIA_COBERTURA_BACKEND_20261105.md`, sin una auditoría nueva.

| Prioridad | Candidato parcial | Impacto, dependencias y decisión |
|---|---|---|
| 1 | RF-19: cierre automático operativo | Contrato definido (+24 h, solo EN_CURSO), servicio/State/Observer y perfil Docker worker existentes. Riesgo bajo y sin dependencia del inicio estudiantil. Seleccionado: acreditar proceso independiente y recuperación periódica, corregir logging de errores y manejo de salida del CLI. |
| 2 | RF-03: administración docente real | Alto impacto en la autoría de extremo a extremo. Reutiliza Proxy/repositorios/HTTP, pero falta contrato de login administrativo y el alcance de permisos sigue siendo por rol. No inventar autenticación ni concesiones individuales. No implementable completamente en este incremento. |
| 3 | RF-21: correo de convocatorias | Alto impacto en login estudiantil. Avisos internos y retiro ya funcionan; faltan proveedor/remitente/URL y entrega recuperable del código que solo tiene hash. No guardar códigos en claro ni simular envío. No implementable completamente sin ese contrato técnico. |

No hay tres RF parciales listos para completar sin dependencias: los dos últimos
no requieren nuevas fórmulas académicas, pero sí contratos técnicos ausentes.
RF-20 comparte el bloqueo de correo; RF-27 el de publicación oficial.

Criterios del incremento seleccionado, definidos antes de cambiar código:

1. Ejecutar el módulo real `worker_runner --once` en otro proceso, con configuración
   exclusiva de PostgreSQL17 desechable y sin leer `.env` en el laboratorio.
2. Verificar desde otra Session estado, fecha, auditoría WORKER y aviso interno;
   una segunda ejecución no repite el cierre.
3. Dos procesos concurrentes deben conservar una sola transición/auditoría/aviso.
4. Acreditar dos revisiones periódicas reales con el intervalo existente de 60 s:
   fallo SQL controlado, rollback y recuperación posterior sin reiniciar el worker.
5. No volcar texto/SQL/parámetros de excepciones en logs del runner. `--once` con
   error termina con código no cero; opciones CLI inválidas no arrancan el bucle.
6. Preservar la regla +24 h, State, locks, atomicidad de avisos, autorizaciones
   HTTP y todos los bloqueos académicos. Sin tablas, migraciones ni servicios nuevos.

El perfil Docker `worker` ya existe en `docker-compose.yml`; se reutiliza, no se
arranca contra la base del equipo. La aceptación del proceso Python no certifica
por sí sola la imagen Docker ni un despliegue institucional permanente.

## Implementación y resultados

El cambio de código productivo queda en `scheduling/infrastructure/worker_runner.py`.
No se sustituye el servicio de cierre: el CLI valida sus opciones, `--once` devuelve
1 si falla y el bucle periódico conserva el reintento de 60 s. Los errores solo
registran `REVISION_FALLIDA` y su clase; no imprimen SQL, argumentos ni traceback.
La regla académica y los callbacks existentes no cambian.

Pruebas nuevas:

- `tests/unit/scheduling/test_worker_runner.py`: opción CLI inválida e interrupción
  controlada, dos pruebas con dobles de orquestación, no de persistencia.
- `tests/integration/test_worker_process.py`: revisión real y repetición,
  competencia de dos procesos comprobando `pg_stat_activity`, fallo SQL/rollback
  y recuperación en el siguiente ciclo real, y error de conexión con salida segura.
  Son cuatro pruebas PG17 sin sustituir los componentes críticos.

| Ejecución | Resultado actual |
|---|---|
| Focal `pruebas_casos_20261105T200215Z` | 6 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 80.88 s |
| Relacionada `pruebas_focal_20261105T200444Z` | 162 aprobadas, 0 omitidas/fallos/errores, 1 advertencia; 116.54 s |

No se suman ejecuciones solapadas. La advertencia es Starlette/TestClient/httpx.
La general histórica 2023/38 no se volvió a ejecutar; no se modifican contratos
compartidos, modelos, servicios académicos ni endpoints.

El JUnit de la relacionada conserva salidas reales de los hijos: revisión 1 y
revisión 0, procesos concurrentes 1/0, error SQL saneado seguido de cierre después
de 60 s y salida no cero ante base inexistente. Los errores se provocaron solo en
el servidor nuevo del laboratorio. El trigger de fallo fue creado y retirado por
la propia prueba; no es una migración ni una protección productiva nueva.

Para reproducir sin tocar bases permanentes, desde la raíz del repositorio:

```powershell
$env:SPS_TEST_IDENTITY_MAPPING_DOCKER = '1'
& C:\Python313\python.exe -B .\evidencias\rf19_worker_20261105T195818Z\ejecutar_validacion.py casos
& C:\Python313\python.exe -B .\evidencias\rf19_worker_20261105T195818Z\ejecutar_validacion.py focal
```

El ejecutor elimina URLs externas del entorno del proceso pytest y desactiva
su lectura de `.env`. Los hijos reciben exclusivamente el servidor/puerto/base
del contenedor propio; el ejemplo NO lanza el worker contra la configuración
permanente. Comandos, hashes de fuentes, consola y JUnit están en el paquete de
evidencia. Cada repetición conserva su propia carpeta.

## Alcance de disponibilidad y límites

RF-19 queda implementado en alcance funcional: API docente en main y cierre
automático en el módulo ejecutable existente. El perfil Docker `worker` sigue
siendo optativo; no se inicia dentro de FastAPI. No se desplegó en servidores
permanentes ni se acreditó supervisión institucional, imagen Docker o SLA.
Una parada forzada del hijo de laboratorio solo verifica limpieza; no se presenta
como garantía de apagado ordenado por SIGTERM en Windows o contenedores.

No se cambia el bloqueo de inicio desde convocatoria, repetición, RF-22 ni notas
oficiales. RF-03 y RF-21 siguen pendientes de sus contratos técnicos. El siguiente
paso de mayor impacto es acordar el mecanismo de autenticación de personal antes
de implementar login administrativo/docente; no se inicia aquí.
