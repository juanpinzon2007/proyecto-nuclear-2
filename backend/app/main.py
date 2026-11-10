
from fastapi import FastAPI

from app.core.config import get_settings
from app.db.models import registrar_modelos_integrados

from app.modules.cases.api.router import router as cases_router
from app.modules.identity.api.router import router as identity_router
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.participation.api.current_scenario_router import router as escenario_router
from app.modules.participation.api.progress_router import router as progreso_router
from app.modules.participation.api.attempt_operations_router import router as operaciones_router
from app.modules.identity.api.consent import router_principal as consentimiento_router
from app.modules.participation.api.provision_router import router_principal as inicio_router


# Registrar los modelos compartidos.
registrar_modelos_integrados()


# Crear la aplicación principal.
app = FastAPI(title=get_settings().app_name)


# Módulo de Casos - Juan Andrés.
app.include_router(cases_router)


# Módulo de Identidad - Alejandro.
app.include_router(identity_router)


# Módulo de Programación - Maicol.
app.include_router(scheduling_router)

# Operaciones del intento existente; el inicio condicionado se compone debajo.
app.include_router(escenario_router, prefix="/api/v1")
app.include_router(progreso_router, prefix="/api/v1")
app.include_router(operaciones_router, prefix="/api/v1")

# Composiciones explícitas: aprobaciones/políticas ausentes bloquean sin escribir.
# No se monta la provisión independiente ni un router general de Participation.
app.include_router(consentimiento_router)
app.include_router(inicio_router)


# Endpoint de salud de la aplicación.
@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}
