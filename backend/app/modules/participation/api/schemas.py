"""Contrato HTTP PROVISIONAL. No está registrado en la aplicación principal."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.evaluation import ModalidadEvaluacion

Identificador = Annotated[int, Field(strict=True, gt=0)]
ReferenciaCases = UUID | Identificador
DecimalTexto = Annotated[str, Field(pattern=r"^\d+(?:\.\d+)?$")]


class EsquemaHTTP(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class InicioIntentoSolicitud(EsquemaHTTP):
    id_consentimiento: Identificador
    id_permiso_extra: Identificador | None = None


class VinculacionConvocatoriaSolicitud(EsquemaHTTP):
    id_asignacion: Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
    codigo_acceso: SecretStr = Field(min_length=1, max_length=256)


class InicioConvocatoriaSolicitud(VinculacionConvocatoriaSolicitud):
    id_consentimiento: Identificador
    id_permiso_extra: Identificador | None = None


class VinculacionRespuesta(EsquemaHTTP):
    id_participacion: Identificador
    creada: bool
    estado: str


class SeleccionSolicitud(EsquemaHTTP):
    id_opcion: ReferenciaCases
    reflexion_estudiante: Annotated[str, Field(strict=True)] | None = None


class IntentoRespuesta(EsquemaHTTP):
    id_intento: Identificador
    id_participacion: Identificador
    numero_intento: Identificador
    estado: EstadoIntento
    inicio: datetime
    fin: datetime | None
    vence_en: datetime


class SeleccionRespuesta(EsquemaHTTP):
    id_decision: ReferenciaCases
    id_opcion: ReferenciaCases


class ProgresoRespuesta(EsquemaHTTP):
    intento: IntentoRespuesta
    decisiones_aplicables: list[ReferenciaCases] | None
    selecciones: list[SeleccionRespuesta]
    pendientes: list[ReferenciaCases] | None
    total_aplicable: Annotated[int, Field(ge=0)] | None
    respondidas: Annotated[int, Field(ge=0)]


class OpcionActualRespuesta(EsquemaHTTP):
    id: UUID
    texto: str


class PreguntaActualRespuesta(EsquemaHTTP):
    id: UUID
    enunciado: str
    opciones: list[OpcionActualRespuesta]


class EscenarioActualRespuesta(EsquemaHTTP):
    id_escenario: UUID | None
    contexto: str | None
    pregunta: PreguntaActualRespuesta | None
    recorrido_finalizado: bool
    respondidas: Annotated[int, Field(ge=0)]


class ReferenciaAcademicaRespuesta(EsquemaHTTP):
    id_caso: Identificador
    id_rubrica: Identificador
    version: str


class CriterioResultadoRespuesta(EsquemaHTTP):
    id_criterio: Identificador
    id_nivel: Identificador
    puntaje_obtenido: DecimalTexto


class ResultadoPendienteRespuesta(EsquemaHTTP):
    estado: Literal["PENDIENTE"] = "PENDIENTE"
    id_participacion: Identificador
    id_intento: Identificador | None
    codigo: Literal["EVALUACION_NO_CONFIRMADA"] = "EVALUACION_NO_CONFIRMADA"
    mensaje: str = "Todavía no hay una evaluación persistida y confirmada."


class ResultadoDefinitivoRespuesta(EsquemaHTTP):
    estado: Literal["DEFINITIVA"] = "DEFINITIVA"
    id_participacion: Identificador
    id_intento: Identificador | None
    modalidad: ModalidadEvaluacion
    referencia: ReferenciaAcademicaRespuesta
    nota_final: DecimalTexto
    politica_calculo: str
    criterios: list[CriterioResultadoRespuesta]


ResultadoRespuesta = Annotated[
    ResultadoPendienteRespuesta | ResultadoDefinitivoRespuesta,
    Field(discriminator="estado"),
]


class DetalleErrorHTTP(EsquemaHTTP):
    codigo: str
    mensaje: str
    campos: list[str] | None = None


class ErrorHTTP(EsquemaHTTP):
    detail: DetalleErrorHTTP
