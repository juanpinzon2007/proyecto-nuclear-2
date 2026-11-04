"""Router HTTP del módulo de casos; no conoce SQLAlchemy."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from app.modules.identity.api.academic_dependencies import obtener_docente_cases

from app.modules.cases.api.dependencies import get_caso_service, exigir_permiso_creacion_configurado
from app.modules.cases.api.schemas.caso_responses import (
    CasoDetalleResponse,
    CasoResumenResponse,
    VersionResponse,
    GrafoResponse,
)
from app.modules.cases.api.schemas.caso_schemas import CasoPayload, GrafoSolicitud
from app.modules.cases.application.graph import GrafoNoDisponible
from app.modules.cases.application.services.caso_service import CasoService
from app.modules.cases.domain.entities.caso import VersionCaso
from app.modules.cases.domain.exceptions import (
    CasoInvalidoError,
    CasoNoEncontradoError,
    ErrorConstruccionCaso,
    ErrorDominioCaso,
    ErrorPersistenciaCaso,
)

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

ServicioDep = Annotated[CasoService, Depends(get_caso_service)]
# Identidad del servidor, sin cabecera alternativa. Cerrado sin resolver real.
DocenteDep = Annotated[uuid.UUID, Depends(obtener_docente_cases)]


def _traducir(exc: ErrorDominioCaso | GrafoNoDisponible) -> HTTPException:
    """Traduce excepciones del dominio a respuestas HTTP."""
    if isinstance(exc, GrafoNoDisponible):
        return HTTPException(422, detail={"errores": [str(exc)]})
    if isinstance(exc, CasoNoEncontradoError):
        return HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CasoInvalidoError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, detail={"errores": exc.errores})
    if isinstance(exc, ErrorConstruccionCaso):
        return HTTPException(status.HTTP_400_BAD_REQUEST, detail={"errores": [str(exc)]})
    if isinstance(exc, ErrorPersistenciaCaso):
        return HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al guardar el caso."
        )
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error inesperado.")


def _respuesta(version: VersionCaso) -> VersionResponse:
    return VersionResponse(caso_id=version.caso_id, version_id=version.id, estado=version.estado)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VersionResponse)
def crear_borrador(
    payload: CasoPayload, docente_id: DocenteDep,
    permiso: Annotated[None, Depends(exigir_permiso_creacion_configurado)], service: ServicioDep,
) -> VersionResponse:
    """Guarda un caso en BORRADOR, incluso incompleto."""
    try:
        return _respuesta(service.crear_borrador(docente_id, payload))
    except ErrorDominioCaso as exc:
        raise _traducir(exc) from exc


@router.get("", response_model=list[CasoResumenResponse])
def listar_casos(docente_id: DocenteDep, service: ServicioDep) -> list[CasoResumenResponse]:
    """Lista resumida de los casos del docente."""
    return [CasoResumenResponse.model_validate(r) for r in service.listar(docente_id)]


@router.get("/{version_id}", response_model=CasoDetalleResponse)
def obtener_caso(
    version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep
) -> CasoDetalleResponse:
    """Detalle completo: escenarios, preguntas, opciones y rúbrica."""
    try:
        return CasoDetalleResponse.model_validate(service.obtener(docente_id, version_id))
    except ErrorDominioCaso as exc:
        raise _traducir(exc) from exc


@router.put("/{version_id}", response_model=VersionResponse,
            dependencies=[Depends(exigir_permiso_creacion_configurado)])
def editar_borrador(
    version_id: uuid.UUID, payload: CasoPayload, docente_id: DocenteDep, service: ServicioDep
) -> VersionResponse:
    """Reemplaza la estructura de un BORRADOR (400 si está PUBLICADO o ARCHIVADO)."""
    try:
        return _respuesta(service.actualizar(docente_id, version_id, payload))
    except ErrorDominioCaso as exc:
        raise _traducir(exc) from exc


@router.post("/{version_id}/publish", response_model=VersionResponse,
             dependencies=[Depends(exigir_permiso_creacion_configurado)])
def publicar_caso(
    version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep
) -> VersionResponse:
    """Valida el borrador con el Chain of Responsibility y lo publica."""
    try:
        return _respuesta(service.publicar(docente_id, version_id))
    except (ErrorDominioCaso, GrafoNoDisponible) as exc:
        raise _traducir(exc) from exc


@router.post("/{version_id}/archive", response_model=VersionResponse,
             dependencies=[Depends(exigir_permiso_creacion_configurado)])
def archivar_caso(
    version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep
) -> VersionResponse:
    """Archiva un caso PUBLICADO para evitar nuevas programaciones."""
    try:
        return _respuesta(service.archivar(docente_id, version_id))
    except ErrorDominioCaso as exc:
        raise _traducir(exc) from exc


@router.get("/{version_id}/graph", response_model=GrafoResponse)
def consultar_grafo(version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep):
    """Detalle de la configuración propia, incluso del borrador incompleto."""
    try:
        return GrafoResponse.model_validate(service.consultar_recorrido(docente_id, version_id))
    except (ErrorDominioCaso, GrafoNoDisponible) as exc:
        raise _traducir(exc) from exc


@router.put("/{version_id}/graph", response_model=GrafoResponse,
            dependencies=[Depends(exigir_permiso_creacion_configurado)])
def configurar_grafo(version_id: uuid.UUID, solicitud: GrafoSolicitud,
                     docente_id: DocenteDep, service: ServicioDep):
    """Reemplazo completo y atómico de un recorrido ejecutable del borrador."""
    try:
        return GrafoResponse.model_validate(service.configurar_recorrido(
            docente_id, version_id, inicial_id=solicitud.escenario_inicial_id,
            transiciones=tuple((t.opcion_id, t.tipo, t.destino_id) for t in solicitud.transiciones),
        ))
    except (ErrorDominioCaso, GrafoNoDisponible) as exc:
        raise _traducir(exc) from exc
