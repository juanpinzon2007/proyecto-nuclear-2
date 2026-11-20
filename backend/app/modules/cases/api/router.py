"""Router HTTP del módulo de casos; no conoce SQLAlchemy."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.identity.api.academic_dependencies import obtener_docente_cases
from app.modules.identity.api.dependencies import obtener_notificador_negocio
from app.modules.identity.infrastructure.business_notifications import (
    notificar_asignacion_rubrica_caso,
    notificar_creacion_caso,
    notificar_publicacion_caso,
    obtener_contacto_por_identidad,
    rubrica_cambio,
)

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
BaseDatosDep = Annotated[Session, Depends(get_db)]
NotificadorNegocioDep = Annotated[Callable[..., None] | None, Depends(obtener_notificador_negocio)]


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


def _notificar_publicacion_docente(
    db: Session,
    *,
    docente_id: uuid.UUID,
    version: VersionCaso,
    background_tasks: BackgroundTasks,
    notificador: Callable[..., None] | None,
) -> None:
    contacto = obtener_contacto_por_identidad(db, sistema="CASES", id_academico=docente_id)
    if contacto is None:
        return
    correo, nombre = contacto
    notificar_publicacion_caso(
        correo=correo,
        docente_nombre=nombre,
        caso_nombre=version.nombre,
        numero_version=version.numero,
        rubrica_nombre=version.rubrica.nombre if version.rubrica else None,
        background_tasks=background_tasks,
        notificador=notificador,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VersionResponse)
def crear_borrador(
    payload: CasoPayload, docente_id: DocenteDep,
    permiso: Annotated[None, Depends(exigir_permiso_creacion_configurado)], service: ServicioDep,
    db: BaseDatosDep, background_tasks: BackgroundTasks, notificador: NotificadorNegocioDep,
) -> VersionResponse:
    """Guarda un caso en BORRADOR, incluso incompleto."""
    try:
        version = service.crear_borrador(docente_id, payload)
    except ErrorDominioCaso as exc:
        raise _traducir(exc) from exc
    contacto = obtener_contacto_por_identidad(db, sistema="CASES", id_academico=docente_id)
    if contacto is not None:
        correo, nombre = contacto
        notificar_creacion_caso(
            correo=correo,
            docente_nombre=nombre,
            caso_nombre=version.nombre,
            total_escenarios=len(version.escenarios),
            rubrica_nombre=version.rubrica.nombre if version.rubrica else None,
            total_criterios=len(version.rubrica.criterios) if version.rubrica else 0,
            background_tasks=background_tasks,
            notificador=notificador,
        )
    return _respuesta(version)


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
    version_id: uuid.UUID, payload: CasoPayload, docente_id: DocenteDep, service: ServicioDep,
    db: BaseDatosDep, background_tasks: BackgroundTasks, notificador: NotificadorNegocioDep,
) -> VersionResponse:
    """Reemplaza la estructura de un BORRADOR (400 si está PUBLICADO o ARCHIVADO)."""
    try:
        antes = service.obtener(docente_id, version_id) if payload.rubric is not None else None
        actualizada = service.actualizar(docente_id, version_id, payload)
    except ErrorDominioCaso as exc:
        raise _traducir(exc) from exc
    if antes is not None and actualizada.rubrica is not None and rubrica_cambio(antes.rubrica, actualizada.rubrica):
        contacto = obtener_contacto_por_identidad(db, sistema="CASES", id_academico=docente_id)
        if contacto is not None:
            correo, nombre = contacto
            notificar_asignacion_rubrica_caso(
                correo=correo,
                docente_nombre=nombre,
                caso_nombre=actualizada.nombre,
                numero_version=actualizada.numero,
                rubrica_nombre=actualizada.rubrica.nombre,
                version_regla=actualizada.rubrica.version_regla,
                total_criterios=len(actualizada.rubrica.criterios),
                background_tasks=background_tasks,
                notificador=notificador,
            )
    return _respuesta(actualizada)


@router.post("/{version_id}/publish", response_model=VersionResponse,
             dependencies=[Depends(exigir_permiso_creacion_configurado)])
def publicar_caso(
    version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep,
    db: BaseDatosDep, background_tasks: BackgroundTasks, notificador: NotificadorNegocioDep,
) -> VersionResponse:
    """Valida el borrador con el Chain of Responsibility y lo publica."""
    try:
        version = service.publicar(docente_id, version_id)
    except (ErrorDominioCaso, GrafoNoDisponible) as exc:
        raise _traducir(exc) from exc
    _notificar_publicacion_docente(
        db, docente_id=docente_id, version=version, background_tasks=background_tasks, notificador=notificador
    )
    return _respuesta(version)


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


@router.post("/{version_id}/republish", response_model=VersionResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(exigir_permiso_creacion_configurado)])
def republicar_caso(
    version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep,
    db: BaseDatosDep, background_tasks: BackgroundTasks, notificador: NotificadorNegocioDep,
) -> VersionResponse:
    """Clona una versión archivada o publicada en una nueva versión y la publica sin mutar el histórico."""
    try:
        version = service.clonar_version(docente_id, version_id, publicar=True)
    except (ErrorDominioCaso, GrafoNoDisponible) as exc:
        raise _traducir(exc) from exc
    _notificar_publicacion_docente(
        db, docente_id=docente_id, version=version, background_tasks=background_tasks, notificador=notificador
    )
    return _respuesta(version)


@router.post("/{version_id}/clone", response_model=VersionResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(exigir_permiso_creacion_configurado)])
def clonar_caso(
    version_id: uuid.UUID, docente_id: DocenteDep, service: ServicioDep
) -> VersionResponse:
    """Crea un nuevo BORRADOR editable copiando escenarios, rúbrica y grafo de una versión existente."""
    try:
        return _respuesta(service.clonar_version(docente_id, version_id, publicar=False))
    except (ErrorDominioCaso, GrafoNoDisponible) as exc:
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
