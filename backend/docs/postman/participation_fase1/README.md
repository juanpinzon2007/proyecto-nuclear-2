# RF-12, RF-23 y RF-25: composición main condicionada

Colección importable: `Proyecto_Nuclear_fase1.postman_collection.json`. Environment sin valores secretos: `Proyecto_Nuclear_fase1.postman_environment.json`. Guía detallada: `backend/docs/PARTICIPATION_FASE1_MAIN_CONDICIONADO.md`.

Desde la raíz del repositorio, ejecute **una carpeta por laboratorio**, en PowerShell:

```powershell
.\preparar-participation-fase1.ps1 -RF CONTROL
# Para comprobar los mecanismos con políticas explícitas SOLO LAB:
.\preparar-participation-fase1.ps1 -RF RF-12
.\preparar-participation-fase1.ps1 -RF RF-23
.\preparar-participation-fase1.ps1 -RF RF-25
```

El preparador imprime las dos rutas de importación y el nombre exacto del Environment. Seleccione ese entorno nuevo y ejecute únicamente la carpeta indicada, en orden. Los valores privados temporales no deben exportarse, sincronizarse ni mostrarse en capturas. `q` limpia exclusivamente los recursos propios. Para RF-23 use `t` antes de RELOJ LAB; se adelanta el reloj inyectado, no los timestamps PostgreSQL.

CONTROL verifica el cierre sin políticas productivas. Los otros tres recorridos usan app.main real con JWT y PostgreSQL17, pero inyectan políticas explícitas LAB; no acreditan aprobación integral ni disponibilidad productiva. No se habilitan notas.

La ejecución automatizada Newman comprobó 79 solicitudes y 291 aserciones: CONTROL 4/12, RF-12 25/97, RF-23 18/61 y RF-25 32/121. Evidencia: `evidencias/participation_fase1_20261109T215053Z/newman_1/`. No se ejecutó la interfaz gráfica de Postman. RF-12/RF-23/RF-25 conservan BLOQUEADO.

Para una captura auténtica muestre nombre de solicitud, método/URL, HTTP, respuesta sintética y Test Results. Oculte tokens, códigos, contraseñas y Authorization; no capture cuerpos de login. Se requieren capturas manuales: documento y aceptación, inicio 201 y duplicado 409, respuesta inmutable, progreso/cierre, permiso y consumo único, y controles 503 sin políticas.

`matriz_fase1.csv` relaciona las 79 solicitudes con sus aserciones y evidencias nominales, sin convertir aceptación técnica en aprobación integral.
