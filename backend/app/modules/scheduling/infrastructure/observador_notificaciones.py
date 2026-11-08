
"""Observador de notificaciones de sesiones académicas."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.scheduling.application.crear_notificacion import (
    crear_notificacion,
)
from app.modules.scheduling.domain.events import EventoAcademico
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    EventoAuditoriaModel,
    NotificacionModel,
    SesionProgramadaModel,
)


class ObservadorNotificaciones:
    """Avisos internos atómicos; no abre Session, no hace commit ni envía correo.

    State solo permite una entrada a cada estado por sesión. El lock compartido
    serializa sus efectos; no protege SQL arbitrario ni entregas externas.
    """

    MENSAJES = {
        "sesion.iniciada": (
            "SESION_INICIADA",
            "La sesión académica a la que fuiste convocado "
            "ha comenzado.",
        ),
        "sesion.finalizada": (
            "SESION_FINALIZADA",
            "La sesión académica a la que fuiste convocado "
            "ha finalizado.",
        ),
    }

    ESTADOS = {"sesion.iniciada": "EN_CURSO", "sesion.finalizada": "FINALIZADO"}

    def preparar(self, evento: EventoAcademico, transaccion: Session) -> None:
        if evento.tipo not in self.MENSAJES:
            return
        db = transaccion
        sesion = db.get(SesionProgramadaModel, evento.entidad_id,
                        with_for_update=True, populate_existing=True)
        estado = self.ESTADOS[evento.tipo]
        if sesion is None or sesion.estado != estado:
            raise ValueError("Evento incompatible con el estado de la sesión.")
        auditorias = db.scalar(select(func.count()).select_from(EventoAuditoriaModel).where(
            EventoAuditoriaModel.sesion_id == evento.entidad_id,
            EventoAuditoriaModel.tipo == "CAMBIO_ESTADO",
            EventoAuditoriaModel.estado_nuevo == estado,
        ))
        if auditorias != 1:
            raise ValueError("El evento requiere una transición auditada inequívoca.")

        tipo, mensaje = self.MENSAJES[evento.tipo]
        convocatorias = db.scalars(select(ConvocatoriaModel).where(
            ConvocatoriaModel.sesion_id == evento.entidad_id,
            ConvocatoriaModel.estado == "ACTIVA",
        ).order_by(ConvocatoriaModel.id)).all()
        for convocatoria in convocatorias:
            existente = db.scalar(select(NotificacionModel.id).where(
                NotificacionModel.convocatoria_id == convocatoria.id,
                NotificacionModel.destinatario_id == convocatoria.estudiante_id,
                NotificacionModel.tipo == tipo,
                NotificacionModel.canal == "INTERNA",
            ).limit(1))
            if existente is None:
                crear_notificacion(db, destinatario_id=convocatoria.estudiante_id,
                                   convocatoria_id=convocatoria.id, tipo=tipo,
                                   canal="INTERNA", mensaje=mensaje)
