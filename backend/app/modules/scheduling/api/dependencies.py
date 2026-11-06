"""Frontera HTTP del contexto académico; el permiso temporal sigue separado."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException

from app.modules.identity.api.dependencies import obtener_estudiante_actual, obtener_fabrica_validador_convocatoria
from app.modules.identity.api.errors import ERRORES
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.application.ports import ValidadorContextoConvocatoria
from app.modules.scheduling.api.schemas import ValidarIngresoRequest
from app.modules.scheduling.application.programming_access import AutorizacionEspacioProgramacion
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.modules.scheduling.infrastructure.admission import AdmisionSQLAlchemy


def obtener_admision(
    db: Annotated[Session, Depends(get_db)],
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
):
    return AdmisionSQLAlchemy(db,usuario)


def obtener_autorizacion_espacios_programacion(
    db: Annotated[Session, Depends(get_db)],
) -> AutorizacionEspacioProgramacion:
    """Consulta la asignación aprobada usando la misma Session del escritor."""
    from app.modules.scheduling.infrastructure.programming_access import AutorizacionEspacioSQLAlchemy
    return AutorizacionEspacioSQLAlchemy(db)


def exigir_contexto_convocatoria(
    datos: ValidarIngresoRequest,
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
    fabrica: Annotated[Callable[[], ValidadorContextoConvocatoria], Depends(obtener_fabrica_validador_convocatoria)],
) -> None:
    try:
        fabrica().validar_contexto(id_usuario=usuario.id_usuario, contexto=usuario.id_convocatoria,
                                  solicitada=datos.convocatoria_id)
    except (AccesoDenegado, IntegracionPendiente) as error:
        estado, codigo, mensaje = ERRORES[type(error)]
        raise HTTPException(estado, detail={"codigo": codigo, "mensaje": mensaje},
                            headers={"Cache-Control": "no-store"}) from None
