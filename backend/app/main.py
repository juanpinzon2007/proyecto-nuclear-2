
from fastapi import FastAPI

from app.core.config import get_settings
from app.db.models import registrar_modelos_integrados

from app.modules.cases.api.router import router as cases_router
from app.modules.identity.api.router import router as identity_router
from app.modules.scheduling.api.router import router as scheduling_router


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


# Endpoint de salud de la aplicación.
@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}
