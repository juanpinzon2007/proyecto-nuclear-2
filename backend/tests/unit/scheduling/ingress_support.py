"""Fuentes SINTÉTICAS solo de prueba; no representan una regla RF-22 aprobada."""

from datetime import timedelta, timezone
from types import SimpleNamespace

from app.modules.scheduling.domain.ingress_policy import VentanaIngreso
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel


def politica_fixture(minutos):
    return SimpleNamespace(obtener_ventana=lambda *, id_sesion, inicio, fin: VentanaIngreso(
        inicio, min(inicio + timedelta(minutes=minutos), fin), True, True,
    ))


def restaurar_utc_solo_fixture_sqlite(sesion, instancia):
    # Las filas de estas fixtures se escriben explícitamente en UTC; SQLite pierde
    # el offset. La producción NO adopta esta interpretación automática.
    if sesion.get_bind().dialect.name == "sqlite" and isinstance(instancia, SesionProgramadaModel):
        for campo in ("fecha_inicio", "fecha_fin"):
            valor = getattr(instancia, campo)
            if valor.tzinfo is None:
                setattr(instancia, campo, valor.replace(tzinfo=timezone.utc))
