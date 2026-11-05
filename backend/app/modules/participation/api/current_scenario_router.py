"""Única operación de Participation autorizada para el montaje principal."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.modules.participation.api.dependencies import (
    EstudianteAutenticado, obtener_estudiante_actual, obtener_consulta_escenario,
)
from app.modules.participation.api.errors import RutaParticipacion
from app.modules.participation.api.schemas import EscenarioActualRespuesta, ErrorHTTP


router = APIRouter(route_class=RutaParticipacion, tags=["Participación — lectura privada"],
    responses={codigo: {"model": ErrorHTTP} for codigo in (401, 403, 404, 409, 422, 503)})


@router.get("/attempts/{attempt_id}/current-scenario", response_model=EscenarioActualRespuesta,
            summary="Provisional: consulta privada del escenario actualmente habilitado")
def consultar_escenario_actual(
    attempt_id: Annotated[int, Path(gt=0)], request: Request,
    estudiante: Annotated[EstudianteAutenticado, Depends(obtener_estudiante_actual)],
    consulta: Annotated[object, Depends(obtener_consulta_escenario)],
):
    if request.query_params:
        raise HTTPException(422, detail={"codigo": "SOLICITUD_INVALIDA", "mensaje": "Esta consulta no admite parámetros."})
    return EscenarioActualRespuesta.model_validate(consulta.consultar(
        id_estudiante=estudiante.id_estudiante, id_intento=attempt_id))
