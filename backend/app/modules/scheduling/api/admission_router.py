"""Espera escritora y comprobante privado; no crea P/I ni expone contenido."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import get_db
from app.modules.identity.api.dependencies import obtener_estudiante_actual
from app.modules.identity.api.errors import RutaIdentity
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.scheduling.api.schemas import SolicitudEspera
from app.modules.scheduling.domain.ingress_policy import RelojServidor, PoliticaTemporalNoDisponible
from app.modules.scheduling.infrastructure.admission import contexto_admision,registrar_espera

router=APIRouter(prefix='/convocatorias',tags=['Admisión'],route_class=RutaIdentity)
Usuario=Annotated[ContextoAcceso,Depends(obtener_estudiante_actual)]
DB=Annotated[Session,Depends(get_db)]


def obtener_reloj_espera():return RelojServidor()


def comprobante(c,s):
    return dict(convocatoria_id=str(c.id),sesion_id=str(s.id),
        version_caso_id=str(c.espera_version_caso_id or s.version_caso_id),
        solicitada=c.espera_registrada_en is not None,admitida=c.admision_evento_id is not None,
        estado_sesion=s.estado)


def fallo(error):
    if isinstance(error,AccesoDenegado):estado=403
    elif isinstance(error,SQLAlchemyError) and getattr(error.orig,'sqlstate',None)=='55P03':estado=409
    else:estado=503
    raise HTTPException(estado,detail='Admisión no disponible; reintente ante conflicto.' if estado==409
        else 'Admisión no disponible.',headers={'Cache-Control':'no-store'}) from None


@router.post('/{convocatoria_id}/espera',status_code=201)
def esperar(convocatoria_id:UUID,solicitud:SolicitudEspera,usuario:Usuario,db:DB,
            respuesta:Response,reloj=Depends(obtener_reloj_espera)):
    try:
        with db.no_autoflush:
            c,s,creada=registrar_espera(db,usuario=usuario,convocatoria_id=convocatoria_id,
                codigo=solicitud.codigo_acceso.get_secret_value(),reloj=reloj)
            resultado=comprobante(c,s)
        db.commit()
        respuesta.status_code=201 if creada else 200
        respuesta.headers['Cache-Control']='no-store'
        return resultado
    except (AccesoDenegado,IntegracionPendiente,SQLAlchemyError,PoliticaTemporalNoDisponible) as e:
        db.rollback();fallo(e)


@router.get('/{convocatoria_id}/admision')
def consultar(convocatoria_id:UUID,usuario:Usuario,db:DB,respuesta:Response):
    try:
        with db.no_autoflush:
            c,s=contexto_admision(db,usuario,convocatoria_id)
            resultado=comprobante(c,s)
        respuesta.headers['Cache-Control']='no-store'
        return resultado
    except (AccesoDenegado,IntegracionPendiente,SQLAlchemyError) as e:fallo(e)
