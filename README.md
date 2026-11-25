# SPS — Simulador de Psicología Social

Plataforma académica del Proyecto Nuclear 2 para crear casos, programar actividades,
registrar participaciones y evaluar estudiantes mediante rúbricas.

La aplicación incluye portales de administración, docencia y estudiantes, el
simulador, las calificaciones, la gestión de convocatorias y la trazabilidad
académica. El informe de auditoría documenta la validación local y el procedimiento
de prueba para Gmail. [Informe de auditoría](backend/docs/AUDITORIA_INTEGRAL_20261124.md)

## Arquitectura y tecnologías

Monolito modular con cuatro módulos internos y separación por capas:

| Capa | Responsabilidad futura | Dependencias |
| --- | --- | --- |
| API | Rutas HTTP y esquemas de entrada/salida | Application |
| Application | Casos de uso, fachadas y contratos | Domain |
| Domain | Entidades y reglas del dominio | Python, sin FastAPI ni SQLAlchemy |
| Infrastructure | Repositorios ORM y adaptadores externos | Contratos internos y componentes técnicos compartidos |

Infrastructure implementará los contratos internos; Application no importará
implementaciones concretas. `app/main.py` será el punto de composición de routers
y dependencias. Los módulos usarán contratos públicos acordados sin acceder a
repositorios o tablas privados de otros módulos. Los contratos se crearán cuando
exista una necesidad real. No hay microservicios por desarrollador.

Python 3.12 o superior (Docker usa 3.13), FastAPI, Uvicorn, SQLAlchemy 2.x,
Psycopg 3 síncrono, PostgreSQL 17, Pydantic Settings, Alembic, PyJWT y pwdlib/Argon2.
El frontend usa Angular y Angular Material y se sirve por Nginx en Docker.
Pytest y HTTPX se instalan con el extra `dev`.
Los rangos de versiones están en `backend/pyproject.toml`; aún no hay lockfile.

## Estructura

```text
proyecto-nuclear-2/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/                 # __init__.py, config.py
│   │   ├── db/                   # __init__.py, base.py, session.py
│   │   └── modules/
│   │       ├── __init__.py
│   │       ├── cases/
│   │       ├── participation/
│   │       ├── identity/
│   │       └── scheduling/
│   ├── tests/test_health.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/.gitkeep
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/README.md
├── worker/README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Cada módulo contiene un `__init__.py` y las carpetas `api/`, `application/`,
`domain/` e `infrastructure/`. Identity incorpora su implementación en esas capas;
los otros módulos conservan aquí su estructura inicial.

## Responsabilidades

| Módulo | Responsable / rama | Alcance | Patrones previstos |
| --- | --- | --- | --- |
| `cases` | Juan Andrés / `juan` | Casos, escenas, decisiones, opciones y rúbricas | Builder, Chain of Responsibility |
| `participation` | Martín / `martin` | Participaciones, intentos, decisiones registradas, progreso y evaluación con rúbricas | Facade, Strategy |
| `identity` | Alejandro / `alejandro` | Identidad, roles, permisos, seguridad, seguimiento y autorizaciones excepcionales | Proxy implementado; integración pendiente |
| `scheduling` | Maicol / `maicol` | Asignaciones, programación académica, estados, notificaciones y coordinación con Worker | State, Observer |

## Instalación y ejecución local

Desde la raíz del repositorio oficial, que contiene este README, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

No es necesario activar el entorno. La API responde en
`http://127.0.0.1:8000/health` con `{"status":"ok"}`; la documentación está en
`http://127.0.0.1:8000/docs`. La instalación editable permite importar `app` desde
la raíz sin modificar `PYTHONPATH`. En Linux/macOS usar `.venv/bin/python`.

Ejecutar las pruebas técnicas y de Identity, sin PostgreSQL ni `.env`:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -c backend/pyproject.toml
```

## Configuración y persistencia

Copiar `.env.example` a `.env` en la raíz y asignar `POSTGRES_PASSWORD` antes de
usar PostgreSQL o Compose. El ejemplo no contiene credenciales reales. Pydantic
carga ese archivo y prioriza las variables del proceso. Los campos adicionales
de Compose se ignoran. `/health` no abre conexiones.

- `app/core/config.py` centraliza la configuración. `URL.create` construye la URL
  y admite contraseñas con caracteres especiales sin concatenarlas.
- `app/db/base.py` contiene la única base declarativa. Los futuros modelos ORM
  vivirán en Infrastructure y heredarán de esta misma `Base`.
- `app/db/session.py` proporciona un único motor y fábrica de sesiones por
  proceso, creados bajo demanda. No duplicarlos en los módulos.
- Se usarán sesiones síncronas. Los futuros handlers con acceso bloqueante serán
  `def`. No compartir una sesión entre peticiones, hilos o tareas.
- `get_db` abre y cierra una sesión por petición. El futuro caso de uso delimitará
  la transacción con `commit` o `rollback`; cerrar la sesión descarta cambios
  pendientes. Los repositorios no harán commits independientes.
- No usar `Base.metadata.create_all`: los cambios de esquema pasarán por Alembic.

Para API local, `POSTGRES_HOST` apunta a un PostgreSQL accesible localmente.
Compose fuerza `POSTGRES_HOST=db` y el puerto interno 5432 para la API.
La BD de Compose no publica puertos al host. Si se requiere para desarrollo,
acordar un override local que publique solo `127.0.0.1:5432:5432`, sin incorporarlo
a la configuración de despliegue.

## Alembic compartido

Existe un único historial en `backend/alembic/versions`. La revisión
`20261028_identity_access` crea únicamente rol, permiso, rol_permiso y usuario.
No se aplica automáticamente ni crea tablas académicas de otros módulos.
Se puede inspeccionar sin conexión a PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini history
```

El DBML de Identity está conservado en su carpeta `reference/`. Importar
explícitamente los nuevos modelos aprobados en
`backend/alembic/env.py` para registrar su metadata. Solo entonces generar
migraciones con `revision --autogenerate -m "descripcion"` y aplicarlas con
`upgrade head`, usando el mismo prefijo de comando anterior. Autogenerate compara
con la BD configurada: revisar las operaciones y el SQL antes de aplicarlos.
Coordinar la secuencia entre ramas para evitar heads divergentes. No modificar
revisiones ya aplicadas por el equipo ni migrar automáticamente al iniciar FastAPI.

## Docker Compose

Requiere Docker con motor Linux activo y Compose v2. Preparar `.env` como se
indicó y ejecutar desde la raíz:

```powershell
docker compose config --quiet
docker compose up -d --wait db
docker compose build api frontend worker
docker compose run --rm --no-deps api alembic upgrade head
docker compose up -d --wait frontend worker
docker compose ps
```

La API se publica en `127.0.0.1:8000` por defecto; `API_PORT` y `API_BIND_HOST`
permiten configurarlo explícitamente para cada entorno. Para despliegue completo en un
servidor VPS con migración previa automática, rotación de logs y proxy HTTPS, consulta
[Guía de despliegue en VPS](docs/DESPLIEGUE_VPS.md) y `docker-compose.vps.yml`. PostgreSQL solo es
accesible por la red interna de Compose y persiste en `postgres_data`.
`down` conserva ese volumen. Cambiar variables de usuario o contraseña no cambia
una base ya inicializada en el volumen. La API espera a que PostgreSQL esté
saludable, aunque `/health` solo comprueba que el proceso HTTP funciona.
No se crean tablas académicas durante el arranque.

El frontend se abre en [SPS local](http://127.0.0.1:4200/login). En un entorno
aislado con datos sintéticos, configura `ACADEMIC_RUNTIME_SCOPE=LABORATORIO`
y deja el correo desactivado. El entorno académico real requiere un documento
de consentimiento con aprobación institucional y seleccionado para la asignación.

## Git y convenciones

Repositorio: https://github.com/juanpinzon2007/proyecto-nuclear-2.git

`main` es la rama estable. Esta preparación se hace en `main` por autorización
del líder. Los desarrollos posteriores van en las ramas individuales de la tabla.
Tras revisar e integrar esta base, cada integrante ejecutará con su árbol limpio
(sustituir `martin` por su rama asignada):

```powershell
git fetch origin
git switch martin
git merge origin/main
```

Trabajar en el módulo asignado y abrir Pull Requests hacia `main` con revisión
y la prueba técnica aprobada. Coordinar cambios a `core`, `db`, Compose,
dependencias y migraciones. No subir `.env`, entornos virtuales ni credenciales;
no usar force push. Esta entrega no ejecuta commit ni push.

Usar `snake_case` en archivos, funciones y variables; `PascalCase` en clases y
`UPPER_SNAKE_CASE` en constantes. Preferir imports absolutos `from app...`, sin
manipular `sys.path` en código de aplicación. Mantener dependencias hacia las
capas internas y evitar imports circulares. Compartir contratos necesarios y
componentes técnicos, sin colocar reglas de negocio en `core` o `db`.

## Decisiones pendientes

- Resolver las incompatibilidades del DBML con feedback individual y con los
  contratos actuales de repetición y convocatoria antes de integrar esas tablas.
- Acordar propiedad y contratos de rúbricas entre Cases y Participation.
- Definir integración de Identity y contratos públicos entre módulos.
- Acordar ejecución y comunicación del Worker con Scheduling.
- Fijar versiones de Angular/Node, lockfile y procedimiento de despliegue.
- Coordinar registro de routers y secuencia de migraciones compartidas.

Referencias: [sesiones SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[PostgreSQL/Psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)
y [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
