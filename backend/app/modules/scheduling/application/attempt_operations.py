"""Comprobaciones estructurales de operaciones sobre un intento existente.

La proyección NO es un permiso. No aplica RF-22 ni inventa una política de edición.
El llamador debe conservar la misma transacción durante la decisión y escritura.
"""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.scheduling.domain.state import ESTADOS
from app.modules.scheduling.domain.ingress_policy import fecha_utc, PoliticaTemporalNoDisponible
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel, ConvocatoriaModel


class OperacionSesionDenegada(ValueError):
    pass


class CondicionesOperacionNoDisponibles(Exception):
    pass


@dataclass(frozen=True)
class ContextoOperacionSesion:
    sesion_id: UUID
    convocatoria_id: UUID
    estudiante_id: UUID
    version_caso_id: UUID
    estado: str
    inicio: datetime
    fin: datetime
    operacion: str


def autorizar_respuesta_sesion(*, estado: str, inicio: datetime, fin: datetime,
                              ahora: datetime, operacion: str) -> None:
    """Límite de respuesta confirmado por el usuario: inicio <= ahora < fin.

    Solo para intentos ya iniciados. No es permiso de ingreso/RF-22 ni concesión
    de duración: Participation conserva su plazo individual histórico.
    Los datos deben proceder de consultar_operacion_sesion en la misma UoW.
    """
    if estado not in ESTADOS:
        raise CondicionesOperacionNoDisponibles()
    try:
        inicio, fin, ahora = fecha_utc(inicio), fecha_utc(fin), fecha_utc(ahora)
    except PoliticaTemporalNoDisponible:
        raise CondicionesOperacionNoDisponibles() from None
    if fin <= inicio:
        raise CondicionesOperacionNoDisponibles()
    if operacion != "RESPONDER" or estado != "EN_CURSO" or not inicio <= ahora < fin:
        raise OperacionSesionDenegada("La sesión no autoriza registrar respuestas en este instante.")


def consultar_operacion_sesion(db: Session, *, sesion_id: UUID, convocatoria_id: UUID,
                              estudiante_id: UUID, version_caso_id: UUID, operacion: str) -> ContextoOperacionSesion:
    """Relee y bloquea sesión/convocatoria en la Session del escritor.

    Devuelve estado conocido y fechas conscientes; no decide si un estado permite
    responder/modificar ni convierte la ventana de ingreso en ventana de edición.
    """
    if not db.in_transaction() or operacion not in {"RESPONDER", "MODIFICAR"}:
        raise CondicionesOperacionNoDisponibles()
    s, c = SesionProgramadaModel, ConvocatoriaModel
    with db.no_autoflush:
        fila = db.execute(select(s.id, s.version_caso_id, s.estado, s.fecha_inicio, s.fecha_fin,
            c.id.label("convocatoria_id"), c.estudiante_id, c.estado.label("estado_convocatoria"))
            .select_from(s).join(c, c.sesion_id == s.id)
            .where(s.id == sesion_id, c.id == convocatoria_id)
            .with_for_update(of=[s, c])).one_or_none()
    if (fila is None or fila.estudiante_id != estudiante_id or fila.version_caso_id != version_caso_id
            or fila.estado_convocatoria != "ACTIVA"):
        raise OperacionSesionDenegada("Operación no autorizada.")
    if fila.estado not in ESTADOS:
        raise CondicionesOperacionNoDisponibles()
    try:
        inicio, fin = fecha_utc(fila.fecha_inicio), fecha_utc(fila.fecha_fin)
    except PoliticaTemporalNoDisponible:
        raise CondicionesOperacionNoDisponibles() from None
    if fin <= inicio:
        raise CondicionesOperacionNoDisponibles()
    return ContextoOperacionSesion(fila.id, fila.convocatoria_id, fila.estudiante_id,
        fila.version_caso_id, fila.estado, inicio, fin, operacion)
