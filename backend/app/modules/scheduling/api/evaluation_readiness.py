"""Proyección docente privada del lector existente; no calcula ni publica notas."""
from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.api.dependencies import obtener_docente_actual, obtener_fabrica_sesiones_seguimiento
from app.modules.identity.api.errors import RutaIdentity
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.participation.application.evaluation_readiness import PreparacionEvaluacionSesion
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.evaluation_readiness import ConsultaPreparacionEvaluacionSQLAlchemy


class EsquemaPreparacion(BaseModel):
    model_config = ConfigDict(extra='forbid')


class IntentoPreparacionRespuesta(EsquemaPreparacion):
    id_intento: Annotated[int, Field(gt=0)]
    numero: Annotated[int, Field(gt=0)]
    estado: Literal['EN_CURSO', 'FINALIZADO', 'VENCIDO']
    resultado_tecnico_disponible: bool


class ConvocatoriaPreparacionRespuesta(EsquemaPreparacion):
    id_convocatoria: UUID
    id_estudiante: Annotated[int, Field(gt=0)]
    estado: Literal['ACTIVA', 'RETIRADA']
    id_participacion: Annotated[int, Field(gt=0)] | None
    intentos: tuple[IntentoPreparacionRespuesta, ...]
    pendientes: tuple[str, ...]


class PreparacionSesionRespuesta(EsquemaPreparacion):
    id_sesion: UUID
    version_caso_id: UUID
    estado_sesion: Literal['SIN_INICIAR', 'EN_CURSO', 'FINALIZADO']
    convocatorias: tuple[ConvocatoriaPreparacionRespuesta, ...]
    pendientes: tuple[str, ...]
    publicable: Literal[False]

    @classmethod
    def desde_lectura(cls, datos: PreparacionEvaluacionSesion):
        # El lector interno puede conservar diagnósticos de convocatorias sin
        # matrícula cierta. No exponer IDs de esos alumnos en la superficie HTTP.
        if datos.publicable or any('MATRICULA_NO_INEQUIVOCA' in f.pendientes for f in datos.convocatorias):
            raise IntegracionPendiente()
        try:
            return cls(id_sesion=datos.id_sesion, version_caso_id=datos.version_caso_id,
                estado_sesion=datos.estado_sesion, publicable=False, pendientes=datos.pendientes,
                convocatorias=tuple(ConvocatoriaPreparacionRespuesta(
                    id_convocatoria=f.id_convocatoria, id_estudiante=f.id_estudiante,
                    estado=f.estado, id_participacion=f.id_participacion, pendientes=f.pendientes,
                    intentos=tuple(IntentoPreparacionRespuesta(id_intento=i.id_intento, numero=i.numero,
                        estado=i.estado, resultado_tecnico_disponible=i.id_resultado_tecnico is not None)
                        for i in f.intentos)) for f in datos.convocatorias))
        except ValidationError:
            raise IntegracionPendiente() from None


def obtener_consulta_preparacion(
    usuario: Annotated[ContextoAcceso, Depends(obtener_docente_actual)],
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_seguimiento)],
) -> ConsultaPreparacionEvaluacionSQLAlchemy:
    try:
        zona = get_settings().participation_timestamp_zone
        if zona is None or not zona.strip():
            raise ValueError('Zona histórica requerida')
        fechas = FechasPersistencia(ZoneInfo(zona))
    except (ValueError, ZoneInfoNotFoundError):
        raise IntegracionPendiente() from None
    return ConsultaPreparacionEvaluacionSQLAlchemy(usuario=usuario, crear_sesion=sesiones, fechas=fechas)


router = APIRouter(prefix='/sesiones', route_class=RutaIdentity, tags=['Preparación académica docente'],
    responses={401:{'description':'JWT ausente/inválido o cuenta inactiva'},
               403:{'description':'Docente sin ámbito o recurso no accesible'},
               503:{'description':'Integridad, matrícula o configuración no acreditadas'}})


@router.get('/{sesion_id}/evaluacion/preparacion', response_model=PreparacionSesionRespuesta,
            summary='Preparación privada; sin notas ni permiso de publicación')
def consultar_preparacion(sesion_id: UUID, request: Request,
    consulta: Annotated[ConsultaPreparacionEvaluacionSQLAlchemy, Depends(obtener_consulta_preparacion)]):
    if request.query_params:
        raise HTTPException(422, detail={'codigo':'SOLICITUD_INVALIDA',
            'mensaje':'Esta consulta no admite parámetros.'},headers={'Cache-Control':'no-store'})
    return PreparacionSesionRespuesta.desde_lectura(consulta.consultar(id_sesion=sesion_id))
