"""Modelos de respuesta (lectura) del módulo de casos."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.modules.cases.domain.enums import EstadoCaso


class _Respuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OpcionResponse(_Respuesta):
    id: uuid.UUID
    orden: int
    texto: str
    es_correcta: bool
    justificacion: str
    valoraciones: dict[uuid.UUID, Decimal]


class PreguntaResponse(_Respuesta):
    id: uuid.UUID
    orden: int
    enunciado: str
    opciones: list[OpcionResponse]


class EscenarioResponse(_Respuesta):
    id: uuid.UUID
    orden: int
    contexto_situacional: str
    preguntas: list[PreguntaResponse]


class NivelResponse(_Respuesta):
    id: uuid.UUID
    nombre: str
    puntaje: Decimal
    descriptor: str


class CriterioResponse(_Respuesta):
    id: uuid.UUID
    nombre: str
    peso: Decimal
    niveles: list[NivelResponse]


class RubricaResponse(_Respuesta):
    id: uuid.UUID
    nombre: str
    version_regla: str
    criterios: list[CriterioResponse]


class CasoDetalleResponse(_Respuesta):
    id: uuid.UUID
    caso_id: uuid.UUID
    numero: int
    nombre: str
    desarrollo_situacional: str
    contexto_historia: str
    tiempo_estimado_min: int
    estado: EstadoCaso
    escenarios: list[EscenarioResponse]
    rubrica: RubricaResponse | None


class CasoResumenResponse(_Respuesta):
    version_id: uuid.UUID
    caso_id: uuid.UUID
    numero: int
    nombre: str
    tiempo_estimado_min: int
    estado: EstadoCaso
    creado_en: datetime


class VersionResponse(_Respuesta):
    """Respuesta de las operaciones de escritura."""

    caso_id: uuid.UUID
    version_id: uuid.UUID
    estado: EstadoCaso


class TransicionResponse(_Respuesta):
    opcion_id: uuid.UUID
    tipo: str | None
    destino_id: uuid.UUID | None
    texto: str


class PreguntaGrafoResponse(_Respuesta):
    id: uuid.UUID
    enunciado: str
    opciones: list[TransicionResponse]


class EscenaGrafoResponse(_Respuesta):
    id: uuid.UUID
    inicial: bool
    contexto: str
    preguntas: list[PreguntaGrafoResponse]


class GrafoResponse(_Respuesta):
    version_id: uuid.UUID
    escenas: list[EscenaGrafoResponse]

