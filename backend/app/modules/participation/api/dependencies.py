from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.modules.participation.application.facade import ParticipacionFacade


class EstudianteAutenticado(BaseModel):
    """Identidad que debe construir el adaptador del servidor, nunca el cliente."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    id_estudiante: Annotated[int, Field(strict=True, gt=0)]


def obtener_estudiante_actual() -> EstudianteAutenticado:
    # Sin lectura de student_id, correo, headers de identidad ni JWT alternativo.
    raise HTTPException(status_code=503, detail={
        "codigo": "SEGURIDAD_NO_CONFIGURADA",
        "mensaje": "La integración real de identidad todavía no está configurada.",
    })


def obtener_facade(
    estudiante: Annotated[EstudianteAutenticado, Depends(obtener_estudiante_actual)],
) -> ParticipacionFacade:
    # La identidad se exige incluso antes de componer los futuros adaptadores.
    raise HTTPException(status_code=503, detail={
        "codigo": "INTEGRACION_NO_CONFIGURADA",
        "mensaje": "Los adaptadores reales de Participación todavía no están configurados.",
    })
