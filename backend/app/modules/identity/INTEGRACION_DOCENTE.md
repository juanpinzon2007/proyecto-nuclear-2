# Integración docente — primera fase técnica

**Documento histórico de la fase anterior.** La protección temporal descrita aquí
fue sustituida por cierre seguro y resolución por sistema. El estado vigente está
en [CONTRATO_IDENTIDAD_ACADEMICA.md](CONTRATO_IDENTIDAD_ACADEMICA.md).

Revisión: 31 de octubre de 2026. Rama `feature/integracion-backend`, base
`ee025d2`. No se modificaron persistencia, migraciones, identificadores,
contratos de Cases/Scheduling ni Participation.

## Diagnóstico verificado antes de editar

- `identity/api/dependencies.py::obtener_usuario_actual` exige Bearer, verifica
  con `TokensJWT` y consulta el usuario vigente; rechaza inexistentes, inactivos,
  IDs incoherentes y estudiantes sin contexto de convocatoria. No usa roles JWT.
- `TokensJWT` fija HS256, issuer, audience, token_type y claims temporales.
  Se reutiliza exactamente este componente, sin otro mecanismo de autenticación.
- `ContextoAcceso` es inmutable y expone `id_usuario: str`. `UsuarioORM` usa
  INTEGER; `RepositorioUsuariosSQLAlchemy` valida su representación decimal,
  consulta usuario, rol y permisos del catálogo, devuelve el ID como cadena
  y traduce fallos SQLAlchemy a `IntegracionPendiente`.
- `ServicioAutorizacion.exigir_rol` ya separa actividad y pertenencia al rol.
  Ser ADMINISTRADOR no implica DOCENTE. El rol docente tampoco autoriza por sí
  mismo acceso a un recurso ajeno o permisos específicos.
- Cases usa UUID en dominio, servicio, repositorio y `caso.docente_creador_id`.
  El repositorio filtra por ese UUID, pero el router lo recibe de X-Docente-Id.
  El servicio delega persistencia en CasoRepository, que controla sus commits.
- Scheduling usa `sesion_programada.docente_id` UUID sin FK a usuario; comprueba
  propiedad en operaciones de sesión y convocatoria. Sus operaciones docentes
  dependen de `obtener_docente_autenticado`, que siempre devuelve HTTP 503.
  Los casos de uso reciben Session y los routers/flujos controlan transacciones.
- No existe en modelos, repositorios ni migraciones una asociación demostrada
  entre usuario INTEGER y docente UUID. Tampoco existe una entidad docente UUID
  registrada que pueda consultarse como destino de una FK.
- `app/main.py` registra Cases, Identity y Scheduling, y las 18 tablas integradas
  mediante `app/db/models.py`. No registra Participation ni manejadores globales
  para errores de Identity. Identity usa `RutaIdentity`; Cases tiene traducción
  local de sus excepciones y Scheduling usa HTTPException.
- Historial inspeccionado: raíces `20261028_identity_access` y `c27a750108db`,
  merge `20261028_merge_access_cases`; Scheduling `36b9e0790539` depende de Cases;
  merge final `6867083574f6`. La integración del esquema no resuelve la identidad
  académica. No se crearon ni ejecutaron revisiones en esta fase.

## Implementación real

Se añadió **`obtener_docente_actual`** en `identity/api/dependencies.py`.
Es una dependencia API reutilizable que devuelve `ContextoAcceso`, nunca UUID.

Flujo:

1. FastAPI extrae credenciales con el HTTPBearer existente, sin error automático.
2. Invoca `obtener_usuario_actual` con las fábricas diferidas existentes. Sin token
   no abre repositorio ni necesita configurar JWT/BD.
3. Exige `Rol.DOCENTE` mediante `ServicioAutorizacion`. La fábrica de consulta de
   ámbito se proporciona, pero exigir rol no la invoca; no se inventa autorización
   académica ni se abre un servicio pendiente.
4. Devuelve el contexto recuperado del servidor. Ignora cabeceras/query de identidad.
5. Traduce solo NoAutenticado, AccesoDenegado e IntegracionPendiente mediante el
   catálogo HTTP existente: 401 con WWW-Authenticate Bearer, 403 y 503; mensajes
   genéricos y Cache-Control no-store para esos rechazos.

La llamada a obtener_usuario_actual ocurre dentro de la frontera que traduce
errores. Si se usara únicamente Depends(obtener_usuario_actual), su excepción
ocurriría antes de entrar a la nueva función y requeriría RutaIdentity o un
manejador adicional. Esta composición permite reutilizarla con routers normales
sin cambiar main.py ni duplicar verificación JWT o reglas del dominio.

Errores inesperados se propagan: no hay captura general ni acceso de respaldo.
Se verifica tanto la propagación en TestClient como HTTP 500 genérico con debug
desactivado. No se garantiza un esquema JSON para errores inesperados.

Uso futuro, después de resolver la identidad académica:

```python
# Ejemplo conceptual, no endpoint registrado.
# contexto = Depends(obtener_docente_actual)
# docente_id = resolver_uuid_academico(contexto.id_usuario)
# servicio.operacion(docente_id=docente_id, ...)
```

No se creó todavía ese resolver ni un repositorio vacío que aparente resolverlo.
La dependencia no emite tokens, no inicia sesión y no resuelve el flujo de login
docente, que debe utilizar un mecanismo de Identity aprobado por el equipo.

## Límites y riesgos que continúan abiertos

**No se declara integración completa.** La nueva dependencia no está conectada a
Cases ni sustituye el stub UUID de Scheduling. Conectarla sin un UUID demostrado
dejaría operaciones parcialmente funcionales o asignaría propiedad incorrecta.

Cases conserva una vulnerabilidad preexistente: su cabecera puede elegir otro
docente y el router está registrado en main.py. La prueba de caracterización
documenta esa aceptación; NO demuestra seguridad. No se debe exponer públicamente
ese contrato temporal. Sustituirlo por rechazo cerrado cambiaría su comportamiento
HTTP; en esta fase se conserva según el alcance solicitado. La nueva dependencia
sí rechaza cabeceras sin Bearer y no acepta suplantar el sujeto con un JWT válido.

Scheduling conserva 503 en operaciones docentes aun con un JWT válido. Sus rutas
de consulta de espacios/sesiones, notificaciones y validar-ingreso no usan ese
stub docente: no se deben describir como protegidas por la nueva dependencia.
Su ámbito, identidad destinataria y política de acceso requieren revisión antes
de una exposición pública. No se cambiaron reglas académicas ni esas rutas aquí.

No convertir `"7"` mediante UUID(int=7), UUID5, hashes, un UUID aleatorio por
petición, correo, claims o cabeceras. Ninguno demuestra propiedad de registros
académicos existentes. No se cambia INTEGER por UUID ni viceversa.

## Propuesta persistente para segunda fase, pendiente de aprobación

Opción preferida si Cases y Scheduling comparten la misma identidad docente:
una asociación explícita, propiedad de Identity/integración, con `id_usuario`
INTEGER PK/FK a usuario y `docente_id` UUID NOT NULL UNIQUE. El destino UUID es
una identidad académica externa; no inventar FK a una tabla docente inexistente.
Si se aprueba un registro docente UUID independiente, entonces podrá añadirse
su FK real. Confirmar primero si la cardinalidad uno a uno es válida y si ambos
módulos usan el mismo espacio de identificadores; si no, se requiere distinguir
el sistema destino y adaptar cada consumidor por separado.

Alternativa: columna nullable UUID UNIQUE de identidad académica en usuario,
si el equipo aprueba que Identity sea dueño de esa identidad. Reduce una tabla,
pero introduce una responsabilidad académica en el modelo de cuenta y exige
resolver usuarios que no son docentes. No se adopta automáticamente.

Para cualquiera de las opciones:

1. Inventariar UUID docentes existentes en Cases/Scheduling y sus propietarios
   con evidencia institucional. Revisar manualmente ambigüedades y duplicados.
   No emparejar automáticamente por correo ni crear cuentas de producción.
2. Aprobar dueño, cardinalidad, restricciones, altas, bajas y auditoría. Nuevos
   UUID solo se asignan al crear un vínculo aprobado y persistido, no al autenticar.
3. Definir un puerto de resolución en Application del consumidor o en el contrato
   de integración acordado; su adaptador SQL devuelve únicamente asociaciones
   existentes. Ausencia/ambigüedad no concede acceso; indisponibilidad produce 503.
4. Crear una migración revisada aparte de esta fase, sobre el head vigente y
   validada en PostgreSQL de prueba. No ejecutar DDL al arrancar ni alterar .env.
5. Componer autenticación → rol DOCENTE → resolución persistente → autorización
   sobre el recurso. Reemplazar X-Docente-Id y el stub Scheduling de forma conjunta
   con pruebas positivas/negativas de propiedad; no mantener cabecera como fallback.
6. Probar un usuario con registros propios/ajenos, revocación, falta de vínculo,
   caída del resolver y unicidad real. Solo después habilitar los contratos seguros.

Participation permanece fuera del alcance. Sus IDs y dependencias requieren su
propia integración posterior; no se reutiliza este vínculo por semejanza de nombres.

## Evidencia de pruebas

Archivo nuevo: `backend/tests/integration/test_docente_identity.py`, 23 casos.
No se modificaron pruebas anteriores ni fixtures de otros módulos.

Se prueban Bearer ausente/incorrecto, JWT malformado, firma inválida, vencimiento,
roles falsos en claims, usuario inexistente/inactivo/discordante, estudiante,
administrador, docente válido, revocación entre solicitudes, suplantación por
cabeceras/query, fallos de fábricas y repositorio, excepción inesperada, ausencia
de configuración sin token y conservación de los contratos Cases/Scheduling.

La suite usa HTTP **ASGI en proceso con TestClient**, verificación y emisión JWT
reales y ServicioAutorizacion real. Solo se sustituyen las fábricas y el repositorio
de usuarios (Mock); las pruebas de conservación sustituyen el servicio Cases y
la Session Scheduling. Las rutas de sonda existen únicamente en pruebas. No es
una prueba de red con Uvicorn ni de PostgreSQL o resolución UUID persistente.

Resultados ejecutados:

| Ejecución | Aprobadas | Fallidas | Omitidas | Advertencias |
| --- | ---: | ---: | ---: | ---: |
| Baseline completo antes de editar | 667 | 0 | 38 | 1 |
| Nuevas + identity/test_http.py + scheduling/test_api_security.py | 63 | 0 | 0 | 1 |
| Suite completa después | 690 | 0 | 38 | 1 |

Comando específico:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests/integration/test_docente_identity.py backend/tests/identity/test_http.py backend/tests/unit/scheduling/test_api_security.py -q -rs --tb=short
```

Comando completo:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests backend/app/modules/participation/tests -q -rs --tb=short
```

Las 38 omitidas son 29 de persistencia Identity (incluidas las de esquema que
reutilizan su fixture), tres de conexión Participation y seis de su laboratorio.
No se habilitaron sus variables ni se ejecutaron migraciones. Las integraciones
existentes de Cases/Scheduling usan SQLite en memoria al faltar TEST_DATABASE_URL;
sus resultados NO acreditan compatibilidad PostgreSQL. La advertencia conocida
proviene de Starlette/httpx; no se instalaron dependencias.

## Resumen del cambio

Un archivo de producción modificado: `identity/api/dependencies.py` añade una
dependencia; dos archivos nuevos: esta explicación y la suite de 23 pruebas.
Cases, Scheduling, Participation, main.py, Base, configuración global y Alembic
permanecen intactos. No hubo cambio de rama, merge, commit, push ni PR.

Próximo paso: aprobar el vínculo persistente y el procedimiento de reconciliación
con Alejandro, Juan Andrés y Maicol. Después implementar y probar el resolver
contra PostgreSQL independiente antes de sustituir las dependencias temporales.
