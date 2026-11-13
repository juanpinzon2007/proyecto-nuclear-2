"""API de consentimiento SQL con composición explícita y aprobación externa.

El servidor aporta conexión, reloj y zona explícitos. No existe fuente documental
sintética/default ni ruta de publicación, selección o revocación.
"""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import Field, StrictBool

from app.modules.identity.api.dependencies import obtener_estudiante_actual
from app.modules.identity.api.errors import RutaIdentity
from app.modules.identity.api.schemas import EsquemaIdentity
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.infrastructure.consent_access import ConsentimientoEstudiantilSQLAlchemy


IdEntero = Annotated[int, Field(gt=0, le=2147483647)]
Huella = Annotated[str, Field(strict=True, pattern=r'^[0-9a-f]{64}$')]
Referencia = Annotated[str, Field(strict=True, min_length=1, max_length=30)]


class AceptarConsentimiento(EsquemaIdentity):
    id_version_documento: Annotated[int, Field(strict=True, gt=0, le=2147483647)]
    referencia: Referencia
    huella: Huella
    acepta: StrictBool


class DocumentoRespuesta(EsquemaIdentity):
    id_version_documento: IdEntero
    referencia: str
    documento_id: str
    version: str
    texto: str
    huella: Huella


class AceptacionRespuesta(EsquemaIdentity):
    aceptado: bool
    id_version_documento: IdEntero
    referencia: str
    huella: Huella
    id_consentimiento: IdEntero | None
    fecha_aceptacion: datetime | None


def crear_router_consentimiento(*, crear_sesion, fechas, reloj, dependencia_servicio=None) -> APIRouter:
    def dependencia(usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)]):
        return ConsentimientoEstudiantilSQLAlchemy(usuario=usuario, crear_sesion=crear_sesion,
            fechas=fechas, reloj=reloj)

    Servicio = Annotated[ConsentimientoEstudiantilSQLAlchemy, Depends(dependencia_servicio or dependencia)]
    router = APIRouter(prefix='/api/v1/identity', tags=['consentimiento — composición explícita'],
        route_class=RutaIdentity, responses={c:{'description':d} for c,d in (
            (401,'JWT ausente o inválido'),(403,'Operación denegada'),(409,'Documento no vigente o distinto'),
            (422,'Solicitud inválida'),(503,'Documento o integración no disponible'))})
    base = '/convocatorias/{convocatoria_id}/asignaciones/{id_asignacion}/consentimiento'

    @router.get(base, response_model=DocumentoRespuesta)
    def consultar(convocatoria_id: UUID, id_asignacion: IdEntero, servicio: Servicio):
        return servicio.ejecutar(convocatoria_id=convocatoria_id, id_asignacion=id_asignacion, operacion='documento')

    @router.get(base+'/aceptacion', response_model=AceptacionRespuesta)
    def estado(convocatoria_id: UUID, id_asignacion: IdEntero, servicio: Servicio):
        return servicio.ejecutar(convocatoria_id=convocatoria_id, id_asignacion=id_asignacion, operacion='estado')

    @router.post(base+'/aceptacion', response_model=AceptacionRespuesta)
    def aceptar(convocatoria_id: UUID, id_asignacion: IdEntero, solicitud: AceptarConsentimiento, servicio: Servicio):
        return servicio.ejecutar(convocatoria_id=convocatoria_id, id_asignacion=id_asignacion,
            operacion='aceptar', solicitud=solicitud)

    return router


from app.modules.identity.api.consent_dependencies import obtener_servicio_consentimiento

router_principal = crear_router_consentimiento(crear_sesion=None, fechas=None, reloj=None,
    dependencia_servicio=obtener_servicio_consentimiento)
