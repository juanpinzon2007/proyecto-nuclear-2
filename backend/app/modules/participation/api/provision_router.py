"""Composición HTTP explícita de 8B; no instalada en app.main.

Contrato de integración condicionado a políticas del servidor. Validar ingreso
pertenece a Scheduling; estos dos casos de uso sí escriben en una única UoW.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.modules.participation.api.dependencies import crear_dependencia_vinculacion_8b
from app.modules.participation.api.errors import RutaParticipacion
from app.modules.participation.api.mappers import mapear_intento
from app.modules.participation.api.schemas import (
    VinculacionConvocatoriaSolicitud, InicioConvocatoriaSolicitud,
    VinculacionRespuesta, IntentoRespuesta, ErrorHTTP,
)
from app.modules.participation.infrastructure.provision import ServicioVinculacionSQLAlchemy


def crear_router_inicio_8b(*, crear_sesion, fechas, reloj,
                         politica_ingreso=None, politica_vinculacion=None,
                         politica_inicio=None, fuente_consentimiento=None) -> APIRouter:
    """El servidor aporta conexiones/reloj/políticas; None conserva el cierre.

    Puede incluirse en una app de integración sin modificar dependencias globales.
    No convierte una política sintética en política productiva ni abre notas.
    """
    dependencia = crear_dependencia_vinculacion_8b(crear_sesion=crear_sesion,
        fechas=fechas, reloj=reloj, politica_ingreso=politica_ingreso,
        politica_vinculacion=politica_vinculacion, politica_inicio=politica_inicio,
        fuente_consentimiento=fuente_consentimiento)
    Servicio = Annotated[ServicioVinculacionSQLAlchemy, Depends(dependencia)]
    router = APIRouter(prefix="/api/v1", route_class=RutaParticipacion,
        tags=["Participación — integración condicionada"],
        responses={c:{"model":ErrorHTTP} for c in (401,403,409,422,503)})

    @router.post("/convocatorias/{convocatoria_id}/participacion",
                 response_model=VinculacionRespuesta, status_code=201,
                 responses={200:{"model":VinculacionRespuesta,"description":"Participación existente autorizada"}})
    def vincular(convocatoria_id: UUID, solicitud: VinculacionConvocatoriaSolicitud,
                 respuesta: Response, servicio: Servicio):
        resultado = servicio.obtener_o_crear(convocatoria_id=convocatoria_id,
            id_asignacion=solicitud.id_asignacion,
            codigo_acceso=solicitud.codigo_acceso.get_secret_value())
        respuesta.status_code = 201 if resultado.creada else 200
        return VinculacionRespuesta(id_participacion=resultado.participacion.id_participacion,
            creada=resultado.creada, estado=resultado.participacion.estado)

    @router.post("/convocatorias/{convocatoria_id}/intentos",
                 response_model=IntentoRespuesta, status_code=201)
    def iniciar(convocatoria_id: UUID, solicitud: InicioConvocatoriaSolicitud, servicio: Servicio):
        return mapear_intento(servicio.iniciar_desde_convocatoria(
            convocatoria_id=convocatoria_id, id_asignacion=solicitud.id_asignacion,
            codigo_acceso=solicitud.codigo_acceso.get_secret_value(),
            id_consentimiento=solicitud.id_consentimiento,
            id_permiso_extra=solicitud.id_permiso_extra))

    return router
