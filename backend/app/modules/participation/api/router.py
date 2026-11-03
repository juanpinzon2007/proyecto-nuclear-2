"""Rutas PROVISIONALES, sin registrar en main.py hasta acordar contratos y seguridad."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from app.modules.participation.api.dependencies import (
    EstudianteAutenticado, obtener_estudiante_actual, obtener_facade,
)
from app.modules.participation.api.errors import RutaParticipacion
from app.modules.participation.api.mappers import mapear_intento, mapear_progreso, mapear_resultado
from app.modules.participation.api.schemas import (
    ErrorHTTP, InicioIntentoSolicitud, IntentoRespuesta, ProgresoRespuesta,
    ResultadoRespuesta, SeleccionSolicitud,
)
from app.modules.participation.application.facade import ParticipacionFacade

IdRuta = Annotated[int, Path(gt=0)]
IdDecisionRuta = UUID | IdRuta
Estudiante = Annotated[EstudianteAutenticado, Depends(obtener_estudiante_actual)]
Facade = Annotated[ParticipacionFacade, Depends(obtener_facade)]

router = APIRouter(
    prefix="/api/v1", tags=["Participación — contrato provisional"], route_class=RutaParticipacion,
    responses={
        401: {"model": ErrorHTTP, "description": "Identidad no autenticada por el adaptador real"},
        403: {"model": ErrorHTTP, "description": "Operación no autorizada"},
        404: {"model": ErrorHTTP, "description": "Recurso no disponible"},
        409: {"model": ErrorHTTP, "description": "Estado incompatible o conflicto"},
        422: {"model": ErrorHTTP, "description": "Solicitud inválida o regla de dominio"},
        500: {"description": "Fallo inesperado gestionado por ASGI, sin detalles privados con debug desactivado"},
        503: {"model": ErrorHTTP, "description": "Integración o política pendiente"},
    },
)


@router.post("/participations/{participation_id}/attempts", response_model=IntentoRespuesta, status_code=201,
             summary="Provisional: iniciar intento de una participación existente")
def iniciar_intento(participation_id: IdRuta, solicitud: InicioIntentoSolicitud, estudiante: Estudiante, facade: Facade):
    return mapear_intento(facade.iniciar_intento(
        id_estudiante=estudiante.id_estudiante, id_participacion=participation_id,
        id_consentimiento=solicitud.id_consentimiento, id_permiso_extra=solicitud.id_permiso_extra,
    ))


@router.post("/attempts/{attempt_id}/decisions/{decision_id}", response_model=IntentoRespuesta, status_code=201,
             summary="Provisional: registrar una selección nueva")
def registrar_decision(attempt_id: IdRuta, decision_id: IdDecisionRuta, solicitud: SeleccionSolicitud, estudiante: Estudiante, facade: Facade):
    return mapear_intento(facade.registrar_decision(
        id_estudiante=estudiante.id_estudiante, id_intento=attempt_id, id_decision=decision_id,
        id_opcion=solicitud.id_opcion, reflexion_estudiante=solicitud.reflexion_estudiante,
    ))


@router.put("/attempts/{attempt_id}/decisions/{decision_id}", response_model=IntentoRespuesta,
            deprecated=True, summary="Provisional: operación rechazada; respuestas inmutables")
def modificar_decision(attempt_id: IdRuta, decision_id: IdDecisionRuta, solicitud: SeleccionSolicitud, estudiante: Estudiante, facade: Facade):
    return mapear_intento(facade.modificar_decision(
        id_estudiante=estudiante.id_estudiante, id_intento=attempt_id, id_decision=decision_id,
        id_opcion=solicitud.id_opcion, reflexion_estudiante=solicitud.reflexion_estudiante,
    ))


@router.get("/attempts/{attempt_id}/progress", response_model=ProgresoRespuesta,
            summary="Provisional: progreso según el recorrido aplicable")
def consultar_progreso(attempt_id: IdRuta, estudiante: Estudiante, facade: Facade):
    return mapear_progreso(facade.consultar_progreso(id_estudiante=estudiante.id_estudiante, id_intento=attempt_id))


@router.post("/attempts/{attempt_id}/finish", response_model=IntentoRespuesta,
             summary="Provisional: finalizar sin calcular ni publicar una nota")
def finalizar(attempt_id: IdRuta, estudiante: Estudiante, facade: Facade):
    return mapear_intento(facade.finalizar(id_estudiante=estudiante.id_estudiante, id_intento=attempt_id))


@router.get("/participations/{participation_id}/attempts/{attempt_id}/result", response_model=ResultadoRespuesta,
            summary="Provisional: leer evaluación pendiente o definitiva confirmada")
def consultar_resultado(participation_id: IdRuta, attempt_id: IdRuta, estudiante: Estudiante, facade: Facade):
    return mapear_resultado(facade.consultar_evaluacion(
        id_estudiante=estudiante.id_estudiante, id_participacion=participation_id, id_intento=attempt_id,
    ))


@router.get("/participations/{participation_id}/absence-result", response_model=ResultadoRespuesta,
            summary="Provisional: lectura de ausencia sin inventar un intento")
def consultar_ausencia(participation_id: IdRuta, estudiante: Estudiante, facade: Facade):
    return mapear_resultado(facade.consultar_evaluacion(
        id_estudiante=estudiante.id_estudiante, id_participacion=participation_id, id_intento=None,
    ))
