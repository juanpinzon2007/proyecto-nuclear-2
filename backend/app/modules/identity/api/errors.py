from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.modules.identity.domain.errors import (
    AccesoDenegado, ConflictoIdentidad, ErrorIdentidad, IntegracionPendiente,
    NoAutenticado, RecursoNoDisponible, ReglaIdentidadInvalida,
)


ERRORES = {
    NoAutenticado: (401, "NO_AUTENTICADO", "Credenciales ausentes o inválidas."),
    AccesoDenegado: (403, "ACCESO_DENEGADO", "No tiene autorización para esta operación."),
    RecursoNoDisponible: (404, "RECURSO_NO_DISPONIBLE", "Recurso no disponible."),
    ConflictoIdentidad: (409, "CONFLICTO_IDENTIDAD", "La operación no es válida en el estado actual."),
    ReglaIdentidadInvalida: (422, "REGLA_IDENTIDAD", "La solicitud no cumple las reglas de identidad."),
    IntegracionPendiente: (503, "INTEGRACION_IDENTITY_PENDIENTE", "La configuración o integración requerida todavía no está disponible."),
}


class RutaIdentity(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejar(request: Request) -> Response:
            try:
                respuesta = await original(request)
            except RequestValidationError as error:
                respuesta = JSONResponse(status_code=422, content={"detail": {
                    "codigo": "SOLICITUD_INVALIDA", "mensaje": "Revise los campos de la solicitud.",
                    "campos": [list(e["loc"]) for e in error.errors()],
                }})
            except ErrorIdentidad as error:
                estado, codigo, mensaje = ERRORES[type(error)]
                respuesta = JSONResponse(status_code=estado, content={"detail": {"codigo": codigo, "mensaje": mensaje}})
                if estado == 401:
                    respuesta.headers["WWW-Authenticate"] = "Bearer"
            respuesta.headers["Cache-Control"] = "no-store"
            return respuesta

        return manejar
