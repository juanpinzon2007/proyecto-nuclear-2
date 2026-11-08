"""Lectura pura principal; el router aislado conserva su progreso con persistencia."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Request, HTTPException
from app.modules.participation.api.dependencies import EstudianteAutenticado, obtener_estudiante_actual, obtener_consulta_progreso
from app.modules.participation.api.errors import RutaParticipacion
from app.modules.participation.api.mappers import mapear_progreso
from app.modules.participation.api.schemas import ProgresoRespuesta

router = APIRouter(route_class=RutaParticipacion, tags=["Participación — lectura privada"])


@router.get('/attempts/{attempt_id}/progress', response_model=ProgresoRespuesta)
def consultar_progreso_privado(attempt_id: Annotated[int, Path(gt=0)], request: Request,
    estudiante: Annotated[EstudianteAutenticado, Depends(obtener_estudiante_actual)],
    consulta: Annotated[object, Depends(obtener_consulta_progreso)]):
    if request.query_params:
        raise HTTPException(422, detail={"codigo": "SOLICITUD_INVALIDA", "mensaje": "Esta consulta no admite parámetros."})
    return mapear_progreso(consulta.consultar(id_estudiante=estudiante.id_estudiante,id_intento=attempt_id))
