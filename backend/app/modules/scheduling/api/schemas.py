"""Esquemas de entrada y salida del módulo scheduling."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProgramarSesionRequest(BaseModel):
    espacio_academico_id: UUID
    version_caso_id: UUID

    fecha_inicio: datetime
    fecha_fin: datetime

    tiempo_maximo_minutos: int = Field(gt=0)

    lugar: str | None = Field(default=None, max_length=255)
    mensaje_personalizado: str | None = None

    @model_validator(mode="after")
    def validar_fechas(self):
        if (
            self.fecha_inicio.utcoffset() is None
            or self.fecha_fin.utcoffset() is None
        ):
            raise ValueError(
                "Las fechas deben incluir zona horaria."
            )

        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError(
                "La fecha final debe ser posterior a la inicial."
            )

        return self


class CambiarEstadoRequest(BaseModel):
    accion: Literal["iniciar", "finalizar"]


class CrearConvocatoriaRequest(BaseModel):
    estudiante_id: UUID


class SesionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    espacio_academico_id: UUID
    version_caso_id: UUID
    docente_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    tiempo_maximo_minutos: int
    lugar: str | None
    mensaje_personalizado: str | None
    estado: str
    finalizado_en: datetime | None


class ConvocatoriaResponse(BaseModel):
    convocatoria_id: UUID
    codigo_acceso: str


class ConvocatoriaDetalleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sesion_id: UUID
    estudiante_id: UUID
    estado: str


class EspacioAcademicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str


class CrearEspacioAcademicoRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)


class ValidarIngresoRequest(BaseModel):
    convocatoria_id: UUID
    estudiante_id: UUID
    codigo_acceso: str
    tolerancia_minutos: int = Field(default=15, ge=0)


class NotificacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    convocatoria_id: UUID | None
    destinatario_id: UUID
    tipo: str
    canal: str
    mensaje: str
    estado: str
    creada_en: datetime


class NotificarCalificacionRequest(BaseModel):
    estudiante_id: UUID
    participacion_id: UUID
