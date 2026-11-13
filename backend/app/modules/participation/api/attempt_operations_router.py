"""Operaciones explícitas del intento existente; sin inicio, PUT ni Evaluation."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Path
from app.modules.participation.api.dependencies import EstudianteAutenticado, obtener_estudiante_actual, obtener_facade_operaciones
from app.modules.participation.api.errors import RutaParticipacion
from app.modules.participation.api.mappers import mapear_intento
from app.modules.participation.api.schemas import IntentoRespuesta, SeleccionSolicitud, ErrorHTTP
from app.modules.participation.application.facade import ParticipacionFacade

router=APIRouter(route_class=RutaParticipacion,tags=['Participación — intento existente'],
    responses={codigo: {'model': ErrorHTTP} for codigo in (401,403,404,409,422,503)})
Estudiante=Annotated[EstudianteAutenticado,Depends(obtener_estudiante_actual)]
Facade=Annotated[ParticipacionFacade,Depends(obtener_facade_operaciones)]


@router.post('/attempts/{attempt_id}/decisions/{decision_id}',response_model=IntentoRespuesta,status_code=201)
def registrar_primera_decision(attempt_id:Annotated[int,Path(gt=0)],decision_id:UUID,
    solicitud:SeleccionSolicitud,estudiante:Estudiante,facade:Facade):
    return mapear_intento(facade.registrar_decision(id_estudiante=estudiante.id_estudiante,
        id_intento=attempt_id,id_decision=decision_id,id_opcion=solicitud.id_opcion,
        reflexion_estudiante=solicitud.reflexion_estudiante))


@router.post('/attempts/{attempt_id}/finish',response_model=IntentoRespuesta)
def finalizar_intento_existente(attempt_id:Annotated[int,Path(gt=0)],estudiante:Estudiante,facade:Facade):
    return mapear_intento(facade.finalizar(id_estudiante=estudiante.id_estudiante,id_intento=attempt_id))
