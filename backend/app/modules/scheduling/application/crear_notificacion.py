
"""Servicio de creación de notificaciones académicas."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    NotificacionModel,
)


class ErrorNotificacion(ValueError):
    """Error al crear una notificación académica."""
    pass


TIPOS_PERMITIDOS = {
    "CONVOCATORIA",
    "CONVOCATORIA_RETIRADA",
    "SESION_INICIADA",
    "SESION_FINALIZADA",
    "CALIFICACION",
    "RETROALIMENTACION",
}

CANALES_PERMITIDOS = {
    "CORREO",
    "INTERNA",
}


def crear_notificacion(
    db: Session,
    *,
    destinatario_id: UUID,
    tipo: str,
    canal: str,
    mensaje: str,
    convocatoria_id: UUID | None = None,
) -> NotificacionModel:
    """Crea una notificación pendiente en PostgreSQL."""

    # 1. Validar el tipo.
    if tipo not in TIPOS_PERMITIDOS:
        raise ErrorNotificacion(
            "Tipo de notificación no permitido."
        )

    # 2. Validar el canal.
    if canal not in CANALES_PERMITIDOS:
        raise ErrorNotificacion(
            "Canal de notificación no permitido."
        )

    # 3. Validar el mensaje.
    if not mensaje or not mensaje.strip():
        raise ErrorNotificacion(
            "El mensaje no puede estar vacío."
        )

    # 4. Una notificación de convocatoria
    # debe estar asociada a una convocatoria.
    if tipo == "CONVOCATORIA" and convocatoria_id is None:
        raise ErrorNotificacion(
            "La notificación requiere una convocatoria."
        )

    # 5. Verificar la convocatoria si fue indicada.
    if convocatoria_id is not None:
        convocatoria = db.get(
            ConvocatoriaModel,
            convocatoria_id,
        )

        if convocatoria is None:
            raise ErrorNotificacion(
                "La convocatoria no existe."
            )

        if convocatoria.estudiante_id != destinatario_id:
            raise ErrorNotificacion(
                "El destinatario no pertenece a la convocatoria."
            )

    # 6. Crear la notificación.
    notificacion = NotificacionModel(
        convocatoria_id=convocatoria_id,
        destinatario_id=destinatario_id,
        tipo=tipo,
        canal=canal,
        mensaje=mensaje.strip(),
        estado="PENDIENTE",
    )

    # 7. Registrar dentro de la transacción.
    db.add(notificacion)
    db.flush()

    return notificacion
