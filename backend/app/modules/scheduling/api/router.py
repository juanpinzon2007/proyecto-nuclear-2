
"""Rutas REST del módulo de programación académica."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db, get_session_factory
from app.modules.scheduling.api.schemas import (
    ProgramarSesionRequest,
    CambiarEstadoRequest,
    SesionResponse,
)
from app.modules.scheduling.application.programar_sesion import (
    ErrorProgramacion,
    programar_sesion,
)
from app.modules.scheduling.application.cambiar_estado_y_publicar import (
    cambiar_estado_y_publicar,
)
from app.modules.scheduling.application.registrar_observadores import (
    crear_gestor_eventos,
)
from app.modules.scheduling.domain.state import (
    TransicionInvalidaError,
)
from app.modules.scheduling.infrastructure.models import (
    SesionProgramadaModel,
)


router = APIRouter(
    prefix="/scheduling",
    tags=["Scheduling"],
)


def obtener_docente_autenticado() -> UUID:
    """
    Pendiente: conectar con el módulo de identidad.

    Por seguridad, se bloquean las operaciones hasta que
    exista una dependencia JWT real y validada.
    """
    raise HTTPException(
        status_code=503,
        detail="Autenticación docente pendiente de integración.",
    )


Docente = Annotated[
    UUID,
    Depends(obtener_docente_autenticado),
]

BaseDatos = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "/sesiones",
    response_model=SesionResponse,
    status_code=201,
)
def crear_sesion(
    datos: ProgramarSesionRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """Programa una sesión académica."""

    try:
        sesion = programar_sesion(
            db,
            docente_id=docente_id,
            **datos.model_dump(),
        )

        db.commit()
        db.refresh(sesion)
        return sesion

    except ErrorProgramacion as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


@router.post(
    "/sesiones/{sesion_id}/estado",
    response_model=SesionResponse,
)
async def actualizar_estado(
    sesion_id: UUID,
    datos: CambiarEstadoRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """Inicia o finaliza una sesión de su docente."""

    sesion = db.get(
        SesionProgramadaModel,
        sesion_id,
        with_for_update=True,
    )

    if sesion is None:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Sesión no encontrada.",
        )

    if sesion.docente_id != docente_id:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para modificar esta sesión.",
        )

    gestor = crear_gestor_eventos(
        get_session_factory()
    )

    try:
        return await cambiar_estado_y_publicar(
            db,
            sesion_id=sesion_id,
            accion=datos.accion,
            gestor=gestor,
            origen="DOCENTE",
        )

    except TransicionInvalidaError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error
