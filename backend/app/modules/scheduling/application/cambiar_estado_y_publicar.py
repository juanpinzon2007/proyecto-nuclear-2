
"""Integra cambios de estado, persistencia y eventos académicos."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.scheduling.application.cambiar_estado_sesion import (
    cambiar_estado_sesion,
)
from app.modules.scheduling.domain.events import (
    EventoAcademico,
    GestorEventosAcademicos,
)
from app.modules.scheduling.infrastructure.models import (
    SesionProgramadaModel,
)
from app.modules.scheduling.infrastructure.admission import congelar_admisiones


async def cambiar_estado_y_publicar(
    db: Session,
    *,
    sesion_id: UUID,
    accion: str,
    gestor: GestorEventosAcademicos,
    origen: str = "DOCENTE",
) -> SesionProgramadaModel:
    """Confirma estado, auditoría y avisos SQL; luego callbacks efímeros."""

    try:
        # 1. Validar el cambio con State y registrar auditoría.
        sesion = cambiar_estado_sesion(
            db,
            sesion_id=sesion_id,
            accion=accion,
            origen=origen,
        )
        if accion=='iniciar' and origen=='DOCENTE':
            congelar_admisiones(db,sesion_id=sesion_id)

        # 2. Preparar el evento correspondiente.
        tipos_evento = {
            "EN_CURSO": "sesion.iniciada",
            "FINALIZADO": "sesion.finalizada",
        }

        tipo = tipos_evento[sesion.estado]
        identificador = sesion.id
        evento = EventoAcademico(tipo=tipo, entidad_id=identificador)

        # Efectos internos en la MISMA transacción y bajo el lock de State.
        gestor.preparar(evento, db)

        # 3. Confirmar el estado y la auditoría en PostgreSQL.
        db.commit()

    except Exception:
        # Si falla la operación de base de datos,
        # no publicamos ningún evento.
        db.rollback()
        raise

    # 4. Publicar solamente después del commit.
    await gestor.publicar(evento)

    return sesion
