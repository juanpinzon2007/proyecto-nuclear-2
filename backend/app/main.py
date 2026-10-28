from fastapi import FastAPI

from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name)

# Incorporar aquí los routers públicos de los módulos cuando se implementen.


@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}
