
from fastapi import FastAPI

from app.core.config import get_settings

from app.modules.cases.api.router import (
    router as cases_router,
)
from app.modules.scheduling.api.router import (
    router as scheduling_router,
)


app = FastAPI(title=get_settings().app_name)

# Rutas de casos académicos
app.include_router(cases_router)

# Rutas de programación y ciclo de vida
app.include_router(scheduling_router)


@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}
