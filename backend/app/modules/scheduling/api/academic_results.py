"""Autorización explícita de resultados: ninguna publicación al cerrar un intento."""
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,StrictBool
from app.core.config import get_settings
from app.modules.identity.api.errors import RutaIdentity
from app.modules.identity.api.dependencies import obtener_estudiante_actual,obtener_fabrica_sesiones_seguimiento
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.participation.infrastructure.academic_cycle import CicloAcademicoSQL
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.domain.clock import RelojSistema
from app.modules.scheduling.api.evaluation_readiness import obtener_consulta_preparacion


class Entrada(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Motivo(Entrada):
    motivo:Annotated[str,Field(min_length=1,max_length=4000)]
class Rectificacion(Motivo):
    id_confirmacion:UUID
class Visibilidad(Entrada):
    mostrar_provisional:StrictBool
class Publicar(Entrada):
    revision_sha256:Annotated[str,Field(pattern='^[0-9a-f]{64}$')]


def docente(base=Depends(obtener_consulta_preparacion)):
    return CicloAcademicoSQL(usuario=base.usuario,crear_sesion=base.crear_sesion,fechas=base.fechas,reloj=RelojSistema())

def estudiante(usuario=Depends(obtener_estudiante_actual),sesiones=Depends(obtener_fabrica_sesiones_seguimiento)):
    try:
        zona=get_settings().participation_timestamp_zone
        if zona is None or not zona.strip():raise ValueError()
        fechas=FechasPersistencia(ZoneInfo(zona))
    except (ValueError,ZoneInfoNotFoundError):raise IntegracionPendiente() from None
    return CicloAcademicoSQL(usuario=usuario,crear_sesion=sesiones,fechas=fechas,reloj=RelojSistema())


def sin_parametros(request:Request):
    if request.query_params:raise HTTPException(422,detail='Esta operación no admite parámetros.',headers={'Cache-Control':'no-store'})

router=APIRouter(route_class=RutaIdentity,tags=['Consolidación académica'],dependencies=[Depends(sin_parametros)])

@router.get('/sesiones/{sesion_id}/evaluacion/consolidacion')
def revisar(sesion_id:UUID,servicio=Depends(docente)):
    return servicio.revisar(id_sesion=sesion_id)

@router.post('/sesiones/{sesion_id}/evaluacion/convocatorias/{convocatoria_id}/ausencia')
def ausencia(sesion_id:UUID,convocatoria_id:UUID,datos:Motivo,servicio=Depends(docente)):
    return servicio.ausencia(id_sesion=sesion_id,convocatoria_id=convocatoria_id,motivo=datos.motivo)

@router.post('/sesiones/{sesion_id}/evaluacion/convocatorias/{convocatoria_id}/ausencia/rectificacion')
def rectificar(sesion_id:UUID,convocatoria_id:UUID,datos:Rectificacion,servicio=Depends(docente)):
    return servicio.ausencia(id_sesion=sesion_id,convocatoria_id=convocatoria_id,motivo=datos.motivo,rectificar_id=datos.id_confirmacion)

@router.put('/sesiones/{sesion_id}/evaluacion/visibilidad')
def visibilidad(sesion_id:UUID,datos:Visibilidad,servicio=Depends(docente)):
    return servicio.visibilidad(id_sesion=sesion_id,mostrar_provisional=datos.mostrar_provisional)

@router.post('/sesiones/{sesion_id}/evaluacion/publicaciones')
def publicar(sesion_id:UUID,datos:Publicar,servicio=Depends(docente)):
    return servicio.publicar(id_sesion=sesion_id,revision_sha256=datos.revision_sha256)

@router.get('/sesiones/{sesion_id}/evaluacion/publicaciones')
def consultar_publicacion(sesion_id:UUID,servicio=Depends(docente)):
    return servicio.consultar_publicacion(id_sesion=sesion_id)

@router.get('/convocatorias/{convocatoria_id}/resultado')
def resultado_propio(convocatoria_id:UUID,servicio=Depends(estudiante)):
    return servicio.estudiante(convocatoria_id=convocatoria_id)
