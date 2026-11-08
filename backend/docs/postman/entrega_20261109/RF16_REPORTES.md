# RF-16: demostración de reportes oficiales

Colección adicional de la entrega: `Proyecto_Nuclear_reportes_oficiales.postman_collection.json`.
Reutiliza la publicación explícita existente y agrega dos descargas y tres rechazos.
El recorrido estudiantil de 32 pasos y el Worker se conservan; no ejecutar toda la
entrega sobre la misma base ni mezclar el resultado 100 de ese recorrido con este
laboratorio de publicación 33.33. Los datos previos son fixtures administrativas,
no evidencia de consentimiento o inicio productivo autorizados.

## PowerShell, desde la raíz original del repositorio

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
.\.venv\Scripts\python.exe -B backend/docs/postman/laboratorio_publicacion.py --puerto 8765
```

Docker Engine debe estar disponible. El script existente elimina el uso de .env,
crea PostgreSQL17 nuevo con puerto efímero y expone solo app.main en loopback.
Solicita una clave y un código sintéticos en entrada oculta. No usar credenciales
reales ni reutilizar una base permanente. La consola muestra recursos de laboratorio,
no los secretos. Enter detiene el servidor y elimina solo su contenedor propio.

Importar el environment de esta carpeta y la colección RF-16; duplicar el environment
como LOCAL. Copiar base_url, correos de laboratorio, sesion_id, version_id y convocatoria_id
mostrados por el script. Completar clave_docente y codigo_estudiante solo en valores
locales; no exportarlos ni tomar capturas de login/Authorization. Establecer
laboratorio_confirmado=true y permitir_escrituras_laboratorio=true, solo para el LAB.
Las variables de publicación se capturan al ejecutar las solicitudes.

## Orden exacto: una iteración sobre laboratorio nuevo

| Paso / nombre de solicitud | HTTP | Captura |
|---|---|---|
| MAIN — login docente | 200 | No capturar JWT |
| MAIN — login estudiante | 200 | No capturar JWT |
| MAIN — login docente ajeno | 200 | No capturar JWT |
| 1 — revisar cohorte y capturar hash | 200 | Cohorte publicable y nota 33.33, aún no publicada |
| 2 — autorizar publicación completa | 200 | Id/versión/oficial=true; autorización expresa |
| 3 — reintento de misma publicación | 200 | Mismo id sin duplicación |
| 4 — lectura oficial docente | 200 | Versión/huella; captura variables de procedencia |
| 5 — consulta privada titular | 200 | Resultado propio, sin secretos |
| 6 — docente ajeno rechazado | 403 | JSON de error |
| 7 — sin autenticación | 401 | JSON de error |
| RF16 — descargar XLSX | 200 | MIME, Content-Disposition, X-Publicacion-* y Tests |
| RF16 — descargar PDF | 200 | Mismas cabeceras y Tests |
| RF16 — rechazo sin JWT | 401 | Sin archivo adjunto |
| RF16 — rechazo docente ajeno | 403 | Sin archivo adjunto |
| RF16 — rechazo estudiante | 403 | Sin archivo adjunto |

En las dos descargas, usar **Send and Download** (o menú de descarga de la respuesta)
y guardar `RF16_Oficial.xlsx` y `RF16_Oficial.pdf` en una carpeta local de evidencias.
Abrir Excel: Resultados debe mostrar PARCIAL, nota numérica 33.33 y un intento;
Publicacion identifica la fuente. Abrir PDF: misma publicación, misma nota y fecha.
Tomar capturas sin cabeceras Authorization ni environment secreto. Nunca editar
notas en Excel y presentarlas como otra publicación oficial.

pm.test configurados: HTTP, MIME, archivo no vacío, descarga adjunta, publicación
exacta (id/versión/huella), no-store, rechazos y ausencia de archivo en errores.
No se afirma ejecución de Postman Runner cuando solo se ejecutó Python/HTTP.
Una descarga anterior a publicar debe devolver 404, no un resultado técnico.
Filtros opcionales: `estado=PARCIAL`, `id_estudiante=<INTEGER>`, `id_grupo=<INTEGER>`,
`version_publicacion=1`; las selecciones ajenas se rechazan. Estado AUSENTE sin
filas produce un archivo con encabezados/mensaje, no ausencias inferidas.
