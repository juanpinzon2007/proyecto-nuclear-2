import json
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.scheduling.infrastructure.mail_models import DespachoCorreoModel
from app.modules.scheduling.infrastructure.models import NotificacionModel


def codigo_encolado(db, convocatoria_id):
    cifrado = db.scalars(
        select(DespachoCorreoModel.payload_cifrado)
        .join(NotificacionModel, NotificacionModel.id == DespachoCorreoModel.id_notificacion)
        .where(
            NotificacionModel.convocatoria_id == UUID(str(convocatoria_id)),
            NotificacionModel.tipo == "CONVOCATORIA",
        )
    ).one()
    clave = get_settings().scheduling_mail_encryption_key.get_secret_value()
    return json.loads(Fernet(clave.encode()).decrypt(cifrado))["codigo"]


def codigo_de_prueba(sesiones, convocatoria_id):
    with sesiones() as db:
        return codigo_encolado(db, convocatoria_id)
