# Backend integrado en develop

## Instalación local

Requiere Python 3.12 o posterior, PostgreSQL 17 y Node.js para Newman. Desde la raíz del checkout, en PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e './backend[dev]'
Copy-Item .env.example .env
```

El operador debe completar su archivo privado antes de conectar una base. `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` identifican la base autorizada. `IDENTITY_JWT_SECRET` debe ser aleatoria y permanecer privada. Configurar los dominios institucionales y `PARTICIPATION_TIMESTAMP_ZONE` explícitamente según la convención de los datos históricos. La plantilla contiene los nombres de las restantes variables.

Con una base nueva y autorizada, comprobar la cadena y aplicar las migraciones de forma controlada.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic heads
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

El despliegue debe respaldar su base antes de migrar. La validación de esta integración utiliza exclusivamente bases desechables. Los comandos anteriores describen la instalación del equipo y requieren la autorización correspondiente sobre la base elegida.

`GET /health`, `/docs` y `/openapi.json` permiten comprobar el arranque y los contratos reales. El worker opcional está en el perfil `worker` de Docker Compose. El correo requiere proveedor y claves externos. La configuración de consentimiento e inicio exige archivos confiables, huellas y ámbito del servidor. La ausencia de aprobación o política obligatoria conserva el bloqueo seguro. Un paquete LABORATORIO no autoriza producción.

## Postman Desktop y Newman

Importar los dos archivos de `backend/docs/postman/cobertura_27rf/`.

- `Proyecto_Nuclear_27RF.postman_collection.json`, colección final compatible con Desktop 12.36.2.
- `Proyecto_Nuclear_27RF.postman_environment.json`, plantilla sin secretos.

La colección conserva 27 carpetas, 576 solicitudes y 1152 eventos. Su huella SHA-256 es `71fc56a393b38c42342a60404809f74c34989b5f7f62c48917215c5eaee49e00`. La compatibilidad Desktop modifica una expresión equivalente del encabezado inválido de RF-01-06. Los resultados de Newman se registran separadamente de una ejecución del Runner de Desktop.

Cada carpeta requiere su propio laboratorio. Prepararlo desde la raíz del checkout con Docker Engine disponible.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf RF-07 --preparar
```

Importar y seleccionar el environment privado temporal que muestra el preparador. Ejecutar solo la carpeta elegida, en orden. Escribir `q` para cerrar el laboratorio. RF-19 requiere `w` antes de sus pasos 16 y 17. RF-20 y RF-21 requieren `m` tras los pasos 13 y 15. Mantener credenciales sintéticas y tokens fuera de capturas y archivos compartidos.

Para ejecución automatizada, instalar Newman en una carpeta local de herramientas y proporcionar la ruta al módulo.

```powershell
$Herramientas = Join-Path $env:LOCALAPPDATA 'NuclearQA'
npm install --prefix $Herramientas newman@6.2.3
$Salida = Join-Path (Get-Location) ('evidencias/integracion_' + (Get-Date -Format yyyyMMddTHHmmss))
.\.venv\Scripts\python.exe -B backend/docs/postman/cobertura_27rf/ejecutar_rf.py --rf todos --evidencias $Salida --newman (Join-Path $Herramientas 'node_modules/newman')
```

Los preparadores crean datos académicos sintéticos mediante fixtures administrativas y políticas explícitas de laboratorio. La ejecución de las rutas de la aplicación principal conserva JWT y autorizaciones reales. Las superficies se identifican en cada solicitud y resultado. La validación técnica conserva el dictamen académico de 19 RF con contrato original y ocho con alcance MVP.

## Angular

Usar la API real descrita por `/openapi.json`. En desarrollo, configurar un proxy de Angular hacia `http://127.0.0.1:8000`, conservando las rutas `/api` y `/scheduling`. La API actual no concede CORS universal. En despliegue, acordar origen o proxy inverso del equipo.

El login devuelve el JWT. Enviar `Authorization: Bearer <token>` y revalidar cada recurso mediante el servidor. Los contratos de navegación y resultados están en `RF10_CONTRATO_ANGULAR.md` y `RF14_CONTRATO_ANGULAR.md`. Un 503 por configuración pendiente debe mostrarse como bloqueo. Las decisiones registradas son inmutables. La finalización, evaluación técnica y publicación oficial son operaciones diferenciadas.

## Límites académicos y externos

RF-10 ejecuta una pregunta por escena y grafos sin ciclos alcanzables, con respuestas inmutables. RF-12 mantiene pendiente la aprobación institucional del consentimiento y la conciliación del resultado al cierre. RF-13 conserva el motor por pregunta y la evaluación explícita docente, sujetos a conciliación con UC-05. RF-14 difiere la explicación durante la sesión activa. RF-21 acredita SMTP local, con recepción institucional externa pendiente. RF-22 usa admisión causal y requiere conciliación del umbral original. RF-23 conserva vencimiento efectivo y transición mediante comando. RF-24 requiere conciliar la representación de ausencias y la evaluación posterior. La integración en develop no modifica estos límites ni acredita cumplimiento académico integral de los ocho RF.
