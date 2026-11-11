"""Composición principal: ninguna aprobación documental implícita o de LAB."""
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException
from app.core.config import get_settings
from app.modules.identity.api.dependencies import obtener_estudiante_actual, obtener_fabrica_sesiones_seguimiento
from app.modules.identity.application.consent import PoliticaAprobacionConsentimiento
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.consent_approval import PoliticaConsentimientoAtestado
from app.modules.identity.infrastructure.consent_access import ConsentimientoEstudiantilSQLAlchemy
from app.modules.participation.domain.clock import RelojSistema
from app.modules.participation.infrastructure.codecs import FechasPersistencia


def obtener_aprobacion_consentimiento() -> PoliticaAprobacionConsentimiento:
    try:
        return PoliticaConsentimientoAtestado.desde_settings(get_settings())
    except IntegracionPendiente:
        raise HTTPException(503, detail={"codigo": "APROBACION_CONSENTIMIENTO_PENDIENTE",
            "mensaje": "No hay un proveedor autorizado de aprobación documental."},
            headers={"Cache-Control": "no-store"}) from None


def obtener_fechas_consentimiento():
    try:
        zona = get_settings().participation_timestamp_zone
        if zona is None or not zona.strip():
            raise ValueError()
        return FechasPersistencia(ZoneInfo(zona))
    except (ValueError, ZoneInfoNotFoundError):
        raise IntegracionPendiente() from None


def obtener_reloj_consentimiento():
    return RelojSistema()


def obtener_servicio_consentimiento(
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
    aprobacion: Annotated[PoliticaAprobacionConsentimiento, Depends(obtener_aprobacion_consentimiento)],
    fechas: Annotated[FechasPersistencia, Depends(obtener_fechas_consentimiento)],
    reloj: Annotated[RelojSistema, Depends(obtener_reloj_consentimiento)],
    sesiones: Annotated[object, Depends(obtener_fabrica_sesiones_seguimiento)],
):
    if not callable(getattr(aprobacion, "autorizar", None)):
        raise IntegracionPendiente()
    return ConsentimientoEstudiantilSQLAlchemy(usuario=usuario, crear_sesion=sesiones,
        fechas=fechas, reloj=reloj, politica_aprobacion=aprobacion)
