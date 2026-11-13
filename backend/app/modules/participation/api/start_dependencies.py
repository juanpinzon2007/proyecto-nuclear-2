"""Inicio principal condicionado: puertos obligatorios, sin políticas por defecto."""
from typing import Annotated
from fastapi import Depends
from app.core.config import get_settings
from app.modules.identity.api.dependencies import obtener_estudiante_actual
from app.modules.identity.api.consent_dependencies import obtener_aprobacion_consentimiento
from app.modules.identity.application.consent import PoliticaAprobacionConsentimiento
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
from app.modules.participation.api.dependencies import (
    obtener_fechas_escenario, obtener_reloj_escenario, obtener_fabrica_sesiones_escenario,
)
from app.modules.participation.application.errors import ReglaPendiente
from app.modules.participation.application.start_policy import PoliticaInicioIntento
from app.modules.participation.application.provision_policy import PoliticaVinculacionParticipacion
from app.modules.participation.infrastructure.provision import ServicioVinculacionSQLAlchemy
from app.modules.participation.infrastructure.start_policy_file import (
    cargar_politicas_inicio, PoliticaInicioArchivo, PoliticaVinculacionArchivo,
)
from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada


def _politicas_configuradas():
    settings = get_settings()
    return cargar_politicas_inicio(
        archivo=getattr(settings, "participation_start_policy_file", None),
        huella=getattr(settings, "participation_start_policy_sha256", None),
        ambito=getattr(settings, "academic_runtime_scope", None))


def obtener_politica_inicio() -> PoliticaInicioIntento:
    return PoliticaInicioArchivo(_politicas_configuradas())


def obtener_politica_vinculacion() -> PoliticaVinculacionParticipacion:
    return PoliticaVinculacionArchivo(_politicas_configuradas())


def obtener_servicio_inicio(
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
    inicio: Annotated[PoliticaInicioIntento, Depends(obtener_politica_inicio)],
    vinculacion: Annotated[PoliticaVinculacionParticipacion, Depends(obtener_politica_vinculacion)],
    aprobacion: Annotated[PoliticaAprobacionConsentimiento, Depends(obtener_aprobacion_consentimiento)],
    fechas: Annotated[object, Depends(obtener_fechas_escenario)],
    reloj: Annotated[object, Depends(obtener_reloj_escenario)],
    sesiones: Annotated[object, Depends(obtener_fabrica_sesiones_escenario)],
):
    if any(not callable(getattr(p, "autorizar", None)) for p in (inicio, vinculacion, aprobacion)):
        raise ReglaPendiente("Los proveedores obligatorios no implementan el contrato de autorización.")
    # Este sentinel no concede una ventana: el coordinador exige la concesión
    # real de AdmisionSQLAlchemy en su misma UoW, sin tolerancias inventadas.
    return ServicioVinculacionSQLAlchemy(usuario=usuario, crear_sesion=sesiones,
        fechas=fechas, reloj=reloj, politica_ingreso=PoliticaIngresoNoConfigurada(),
        politica_inicio=inicio, politica_vinculacion=vinculacion,
        crear_fuente_consentimiento=lambda s: FuenteConsentimientoSQLAlchemy(s, politica_aprobacion=aprobacion))
