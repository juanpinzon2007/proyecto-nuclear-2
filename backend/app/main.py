
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import registrar_modelos_integrados
from app.db.session import get_db

from app.modules.cases.api.router import router as cases_router
from app.modules.identity.api.router import router as identity_router
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.participation.api.current_scenario_router import router as escenario_router
from app.modules.participation.api.progress_router import router as progreso_router
from app.modules.participation.api.attempt_operations_router import router as operaciones_router
from app.modules.identity.api.consent import router_principal as consentimiento_router
from app.modules.participation.api.provision_router import router_principal as inicio_router
from app.modules.participation.api.interactive_router import router as simulacion_interactiva_router


# Registrar los modelos compartidos.
registrar_modelos_integrados()


# Crear la aplicación principal.
app = FastAPI(title=get_settings().app_name)
logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def error_de_solicitud(_request: Request, error: RequestValidationError):
    mensajes = {
        "missing": "Este campo es obligatorio.",
        "extra_forbidden": "La solicitud contiene un campo desconocido.",
        "json_invalid": "El cuerpo de la solicitud debe ser JSON válido.",
        "string_too_short": "El texto es demasiado corto.",
        "string_too_long": "El texto es demasiado largo.",
    }
    detalle = []
    for dato in error.errors():
        tipo = dato["type"]
        # Los mensajes de algunos validadores y el valor de entrada pueden contener datos privados.
        ubicacion = dato["loc"][:-1] if tipo == "extra_forbidden" else dato["loc"]
        detalle.append({"loc": list(ubicacion), "msg": mensajes.get(tipo, "Revisa el formato de este campo."), "type": tipo})
    return JSONResponse(status_code=422, content={"detail": detalle})


@app.exception_handler(SQLAlchemyError)
async def error_de_persistencia(_request: Request, error: SQLAlchemyError):
    logger.warning("PERSISTENCIA_NO_DISPONIBLE tipo=%s", type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": "La operación no está disponible temporalmente."},
                        headers={"Cache-Control": "no-store"})


@app.middleware("http")
async def agregar_cabeceras_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    if request.url.path.startswith(("/api/v1/", "/scheduling/")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


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
app.include_router(simulacion_interactiva_router, prefix="/api/v1")


# Endpoint de salud de la aplicación.
@app.get("/health", tags=["technical"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["technical"])
def ready(db: Session = Depends(get_db)):
    """Comprueba una conexión real antes de declarar lista la API."""
    db.execute(text("SELECT 1"))
    return JSONResponse(content={"status": "ready"}, headers={"Cache-Control": "no-store"})
