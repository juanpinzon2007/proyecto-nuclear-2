# SPS — Frontend (Simulador de Psicología Social)

Aplicación web cliente construida en **Angular 21** con **Angular Material** y componentes autónomos (*Standalone Components*), diseñada para interactuar con el backend FastAPI del proyecto sin requerir alteraciones en los contratos del servidor.

---

## 🚀 Arquitectura y Características

1. **Proxy de Desarrollo Seguro (`proxy.conf.json`)**:
   - Reenvía automáticamente `/api` y `/scheduling` hacia `http://localhost:8000`.
   - Evita problemas de CORS en desarrollo sin modificar el código de la API.
2. **Autenticación e Interceptor JWT**:
   - Soporte para **Login de Personal** (Docente / Administrador) vía `/api/v1/identity/auth/personal`.
   - Soporte para **Login de Estudiante** (Correo + Código de Convocatoria) vía `/api/v1/identity/auth/estudiantes`.
   - Interceptor HTTP que inyecta el token Bearer en cada petición y maneja respuestas 401 de forma centralizada.
   - Guards de ruta (`authGuard`, `rolGuard`, `invitadoGuard`) para protección de pantallas por rol.

---

## 📱 Módulos Implementados

| Módulo / Pantalla | Ruta | Rol | Funcionalidad Principal |
|---|---|---|---|
| **Login Unificado** | `/login` | Público | Pestañas independientes para acceso de Personal Docente/Admin y Estudiantes con código. |
| **Gestión de Casos** | `/casos` | DOCENTE / ADMIN | Listar casos, crear borradores, publicar y archivar versiones de simulación. |
| **Detalle de Caso** | `/casos/:id` | DOCENTE / ADMIN | Visualización de escenas, decisiones situacionales, opciones con justificaciones y criterios de rúbrica. |
| **Grafo de Transiciones** | `/casos/:id/grafo` | DOCENTE / ADMIN | Inspección y auditoría de escenas, escena inicial y destinos de cada opción. |
| **Programación Académica**| `/programacion` | DOCENTE / ADMIN | Gestión de espacios académicos, programación de sesiones y control de estado (iniciar / finalizar). |
| **Convocatorias** | `/programacion/:id/convocatorias` | DOCENTE / ADMIN | Asignación de estudiantes por UUID y generación de códigos individuales de acceso. |
| **Evaluación y Consolidación** | `/programacion/:id/evaluacion` | DOCENTE / ADMIN | Preparación de sesión, cálculo de resultados técnicos por rúbrica, consolidación y publicación oficial. |
| **Seguimiento Docente** | `/seguimiento` | DOCENTE / ADMIN | Listado de casos con participación, auditoría de respuestas y descarga de reportes oficiales en Excel (XLSX) o PDF. |
| **Detalle de Participación** | `/seguimiento/participaciones/:id` | DOCENTE / ADMIN | Consulta de decisiones registradas, reflexiones del estudiante y envío de retroalimentación docente. |
| **Administración** | `/administracion/docentes` | ADMIN | Creación de docentes, autorizaciones de roles/permisos institucionales y excepciones de repetición. |
| **Portal del Estudiante** | `/estudiante` | ESTUDIANTE | Verificación de admisión en sala de espera, aceptación de consentimiento informado e inicio de simulación. |
| **Simulador de Decisiones**| `/estudiante/simulador/:id` | ESTUDIANTE | Interfaz interactiva de avance paso a paso: contexto de la escena, opciones de decisión, reflexión y finalización. |

---

## 🛠️ Instrucciones de Ejecución

### 1. Iniciar el Backend (Terminal 1)
```powershell
# Desde la raíz del repositorio
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 2. Iniciar el Frontend (Terminal 2)
```powershell
# Entrar a la carpeta frontend
cd frontend

# Iniciar el servidor de desarrollo Angular con el proxy activo
npm start
```

La aplicación se abrirá en **`http://localhost:4200`** conectada automáticamente a la API en el puerto 8000.

### 3. Compilación para Producción
```powershell
cd frontend
npm run build
```
Genera los artefactos optimizados en `dist/sps-frontend/browser`.
