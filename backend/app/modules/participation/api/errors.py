"""Traducción HTTP local al router, sin cambiar handlers globales de FastAPI."""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.modules.participation.api.schemas import DetalleErrorHTTP, ErrorHTTP, ResultadoPendienteRespuesta
from app.modules.participation.application.errors import (
    AccesoDenegado, ConflictoActualizacion, ErrorAplicacionParticipacion,
    EvaluacionNoConfirmada, RecursoNoDisponible, ReglaPendiente,
)
from app.modules.participation.domain.errors import ErrorDominioParticipacion, IntentoNoEditable, RespuestaInmutable
from app.modules.participation.domain.evaluation import EvaluacionInconsistente, PoliticaEvaluacionPendiente


def _error(estado: int, codigo: str, mensaje: str, campos: list[str] | None = None) -> JSONResponse:
    cuerpo = ErrorHTTP(detail=DetalleErrorHTTP(codigo=codigo, mensaje=mensaje, campos=campos))
    return JSONResponse(status_code=estado, content=cuerpo.model_dump(mode="json", exclude_none=True))


class RutaParticipacion(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        original = super().get_route_handler()

        async def manejar(request: Request) -> Response:
            try:
                respuesta = await original(request)
            except EvaluacionNoConfirmada as error:
                cuerpo = ResultadoPendienteRespuesta(
                    id_participacion=error.id_participacion, id_intento=error.id_intento,
                )
                respuesta = JSONResponse(status_code=200, content=cuerpo.model_dump(mode="json"))
            except AccesoDenegado:
                respuesta = _error(403, "ACCESO_DENEGADO", "No tiene autorización para esta operación.")
            except RecursoNoDisponible:
                respuesta = _error(404, "RECURSO_NO_DISPONIBLE", "El recurso solicitado no está disponible.")
            except ConflictoActualizacion:
                respuesta = _error(409, "CONFLICTO_ACTUALIZACION", "El recurso cambió; vuelva a consultarlo.")
            except RespuestaInmutable:
                respuesta = _error(409, "RESPUESTA_INMUTABLE", "La respuesta registrada no puede modificarse ni eliminarse.")
            except IntentoNoEditable:
                respuesta = _error(409, "INTENTO_NO_EDITABLE", "El intento está cerrado o su tiempo se agotó.")
            except (ReglaPendiente, PoliticaEvaluacionPendiente):
                respuesta = _error(503, "INTEGRACION_O_POLITICA_PENDIENTE", "Faltan dependencias o reglas aprobadas para esta operación.")
            except EvaluacionInconsistente:
                respuesta = _error(409, "EVALUACION_NO_DISPONIBLE", "La evaluación no está disponible en el estado solicitado.")
            except ErrorDominioParticipacion:
                respuesta = _error(422, "REGLA_DOMINIO", "La solicitud no cumple las reglas del dominio.")
            except ErrorAplicacionParticipacion:
                respuesta = _error(409, "OPERACION_NO_PERMITIDA", "La operación no puede completarse en el estado actual.")
            except RequestValidationError as error:
                # No devolver input ni valores de campos desconocidos/privados.
                campos = sorted({".".join(map(str, e["loc"])) for e in error.errors()})
                respuesta = _error(422, "SOLICITUD_INVALIDA", "Revise los campos de la solicitud.", campos)
            except HTTPException as error:
                respuesta = JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers=error.headers)
            # Los errores inesperados se propagan: TestClient debe detectarlos y
            # el límite ASGI gestionará su 500 sin debug. No ocultar defectos aquí.
            respuesta.headers["Cache-Control"] = "no-store"
            return respuesta

        return manejar
