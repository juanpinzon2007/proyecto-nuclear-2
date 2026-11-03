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
