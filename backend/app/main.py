from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.identity.api.router import router as identity_router

app = FastAPI(title=get_settings().app_name)

app.include_router(identity_router)


@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}
