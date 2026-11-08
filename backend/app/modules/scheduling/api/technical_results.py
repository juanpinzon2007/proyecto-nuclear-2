"""Resultado técnico privado del docente: proyección de datos ya persistidos."""
import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import Field, ValidationError

from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.scheduling.api.evaluation_readiness import (
    EsquemaPreparacion, obtener_consulta_preparacion,
)
from app.modules.participation.infrastructure.evaluation_readiness import ConsultaPreparacionEvaluacionSQLAlchemy
from app.modules.participation.infrastructure.teacher_result import ConsultaResultadoDocenteSQLAlchemy


class PreguntaTecnicaRespuesta(EsquemaPreparacion):
    pregunta_id: UUID
    opcion_id: UUID
    puntaje: Decimal
    numero_paso: Annotated[int, Field(gt=0)]


class CriterioTecnicoRespuesta(EsquemaPreparacion):
    criterio_id: UUID
    suma_puntajes: Decimal | None = None
    preguntas_evaluables: Annotated[int, Field(gt=0)] | None = None
    numerador: Annotated[str, Field(pattern=r'^\d+$')] | None = None
    denominador: Annotated[str, Field(pattern=r'^[1-9]\d*$')] | None = None
    nivel_id: UUID | None = None
    puntaje_obtenido: Decimal | None = None


class ResultadoTecnicoRespuesta(EsquemaPreparacion):
    id_sesion: UUID
    id_convocatoria: UUID
    id_participacion: Annotated[int, Field(gt=0)]
    id_intento: Annotated[int, Field(gt=0)]
    id_resultado: Annotated[int, Field(gt=0)]
    version_caso_id: UUID
    rubrica_id: UUID
    version_regla: str
    modalidad: Literal['COMPLETA', 'PARCIAL']
    ambito: Literal['TECNICO', 'LABORATORIO']
    oficial: Literal[False]
    fecha_calculo: datetime
    nota_final: Decimal
    procedencia_sha256: str
    preguntas_exigidas: Annotated[int, Field(gt=0)] | None = None
    preguntas_respondidas: Annotated[int, Field(ge=0)] | None = None
    pendientes_con_cero: Annotated[int, Field(ge=0)] | None = None
    suma_puntajes: Decimal | None = None
    preguntas: tuple[PreguntaTecnicaRespuesta, ...]
    criterios: tuple[CriterioTecnicoRespuesta, ...]

    @classmethod
    def desde_lectura(cls, lectura):
        r=lectura.resultado
        try:
            doc=json.loads(r.procedencia)
            exacto=doc.get('exacto') if r.ambito=='TECNICO' else None
            fuente=doc['rubrica'] if exacto is not None else doc['fuente_rubrica']
            comunes=dict(id_sesion=lectura.id_sesion,id_convocatoria=lectura.id_convocatoria,
                id_participacion=lectura.id_participacion,id_intento=r.datos.id_intento,
                id_resultado=r.id_resultado,version_caso_id=fuente['version_id'],
                rubrica_id=fuente['rubrica_id'],version_regla=fuente['version_regla'],
                modalidad=r.datos.modalidad.value,ambito=r.ambito,oficial=False,
                fecha_calculo=r.fecha_calculo,nota_final=r.datos.nota_final,procedencia_sha256=r.sha256)
            if exacto is not None:
                return cls(**comunes,preguntas_exigidas=exacto['preguntas_exigidas'],
                    preguntas_respondidas=exacto['preguntas_respondidas'],
                    pendientes_con_cero=exacto['preguntas_pendientes'],suma_puntajes=Decimal(exacto['suma_puntajes']),
                    preguntas=tuple(PreguntaTecnicaRespuesta(**q) for q in exacto['preguntas']),
                    criterios=tuple(CriterioTecnicoRespuesta(criterio_id=c['criterio_id'],
                        suma_puntajes=Decimal(c['suma_puntajes']),preguntas_evaluables=c['preguntas_evaluables'],
                        numerador=str(c['numerador']),denominador=str(c['denominador'])) for c in exacto['criterios']))
            return cls(**comunes,preguntas=(),criterios=tuple(CriterioTecnicoRespuesta(
                criterio_id=c.id_criterio,nivel_id=c.id_nivel,puntaje_obtenido=c.puntaje_obtenido) for c in r.datos.criterios))
        except (KeyError, TypeError, ValueError, ValidationError):
            raise IntegracionPendiente() from None


def obtener_consulta_resultado(
    base: Annotated[ConsultaPreparacionEvaluacionSQLAlchemy, Depends(obtener_consulta_preparacion)],
) -> ConsultaResultadoDocenteSQLAlchemy:
    return ConsultaResultadoDocenteSQLAlchemy(usuario=base.usuario,crear_sesion=base.crear_sesion,fechas=base.fechas)


# Se incluye en el router Scheduling ya registrado en main; no monta Participation.
from app.modules.identity.api.errors import RutaIdentity
router=APIRouter(prefix='/sesiones',route_class=RutaIdentity,tags=['Resultados técnicos docentes'])


@router.get('/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico',
    response_model=ResultadoTecnicoRespuesta,response_model_exclude_none=True,
    summary='Resultado técnico persistido, privado y no oficial',
    responses={401:{'description':'Autenticación inválida'},403:{'description':'Fuera del ámbito docente'},
        404:{'description':'Resultado aún no disponible'},503:{'description':'Configuración o integridad no acreditadas'}})
def consultar_resultado(sesion_id:UUID,id_intento:Annotated[int,Path(gt=0)],request:Request,
    consulta:Annotated[ConsultaResultadoDocenteSQLAlchemy,Depends(obtener_consulta_resultado)]):
    if request.query_params:
        raise HTTPException(422,detail={'codigo':'SOLICITUD_INVALIDA','mensaje':'Esta consulta no admite parámetros.'},
            headers={'Cache-Control':'no-store'})
    return ResultadoTecnicoRespuesta.desde_lectura(consulta.consultar_resultado(id_sesion=sesion_id,id_intento=id_intento))
