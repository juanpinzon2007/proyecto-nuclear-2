"""Esquemas de entrada y salida del módulo scheduling."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator, SecretStr


class ProgramarSesionRequest(BaseModel):
    espacio_academico_id: UUID
    version_caso_id: UUID

    fecha_inicio: datetime
    fecha_fin: datetime

    tiempo_maximo_minutos: int = Field(gt=0)

    lugar: str | None = Field(default=None, max_length=255)
    mensaje_personalizado: str | None = None
    grupo_id: int | None = Field(default=None, gt=0, strict=True)
    estudiantes_ids: list[UUID] | None = Field(default=None, min_length=1)
    fecha_limite_ingreso: datetime | None = None

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

        seleccion = (self.grupo_id, self.estudiantes_ids, self.fecha_limite_ingreso)
        if any(valor is not None for valor in seleccion):
            if any(valor is None for valor in seleccion):
                raise ValueError("Grupo, estudiantes y fecha límite deben proporcionarse juntos.")
            if len(set(self.estudiantes_ids)) != len(self.estudiantes_ids):
                raise ValueError("La selección contiene estudiantes duplicados.")
            if self.fecha_limite_ingreso.utcoffset() is None:
                raise ValueError("La fecha límite debe incluir zona horaria.")
            if not self.fecha_inicio <= self.fecha_limite_ingreso <= self.fecha_fin:
                raise ValueError("La fecha límite debe estar entre inicio y fin de la sesión.")

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


class ConvocatoriaAsignadaResponse(ConvocatoriaResponse):
    estudiante_id: UUID


class SesionConAsignacionResponse(SesionResponse):
    id_asignacion: int
    convocatorias: list[ConvocatoriaAsignadaResponse]


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
    model_config = ConfigDict(extra="forbid")
    convocatoria_id: UUID
    estudiante_id: UUID
    codigo_acceso: str


class SolicitudEspera(BaseModel):
    model_config = ConfigDict(extra='forbid')
    codigo_acceso: SecretStr = Field(min_length=1,max_length=256)


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
