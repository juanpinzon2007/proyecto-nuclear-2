# Demostración local en Postman Desktop

Desde la raíz del repositorio en PowerShell, con Docker Desktop activo, la imagen postgres:17 y las dependencias de desarrollo del backend instaladas en .venv, ejecuta:

```powershell
.\.venv\Scripts\python.exe backend/docs/postman/cobertura_27rf/multirrequisito/selector_local.py
```

Mantén la consola abierta. En Postman importa Nuclear-MULTI.postman_collection.json de esta carpeta y el entorno privado que el selector genera en %LOCALAPPDATA%\NuclearStandLocal\Nuclear-MULTI.postman_environment.json. Selecciona **Nuclear - todas las carpetas (local)**.

1. Abre **Nuclear - probar cualquier requisito** y elige la carpeta que corresponda.
2. Empieza con la solicitud 01 y pulsa **Send**. La primera petición prepara los datos en PostgreSQL local.
3. Abre **Test Results** y continúa en orden. Al cambiar de carpeta, comienza otra vez desde su primera solicitud.

El selector escucha en 127.0.0.1:18647. Cada requisito usa datos sintéticos y el flujo de correo usa un receptor SMTP local. Conserva el archivo del entorno solo en tu equipo.

El archivo verificaciones.csv recoge las aserciones de las ejecuciones locales aprobadas por carpeta, incluidos los reintentos tras las correcciones. Para regenerar la colección unificada tras cambiar la maestra, ejecuta generar.py.
