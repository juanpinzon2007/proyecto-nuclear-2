
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.cases.infrastructure.models.caso import VersionCasoModel
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
)


class ErrorProgramacion(ValueError):
    """Error en los datos de programacion de una sesion."""
    pass


def programar_sesion(
    db: Session,
    *,
    espacio_academico_id: UUID,
    version_caso_id: UUID,
    docente_id: UUID,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    tiempo_maximo_minutos: int,
    lugar: str | None = None,
    mensaje_personalizado: str | None = None,
) -> SesionProgramadaModel:

    # Validar fechas con zona horaria
    if fecha_inicio.utcoffset() is None or fecha_fin.utcoffset() is None:
        raise ErrorProgramacion(
            "Las fechas deben incluir zona horaria."
        )

    # Validar el rango de fechas
    if fecha_fin <= fecha_inicio:
        raise ErrorProgramacion(
            "La fecha final debe ser posterior a la inicial."
        )

    # Validar tiempo de participacion
    if tiempo_maximo_minutos <= 0:
        raise ErrorProgramacion(
            "El tiempo maximo debe ser mayor que cero."
        )

    # Comprobar que existe el espacio academico
    espacio = db.get(EspacioAcademicoModel, espacio_academico_id)

    if espacio is None:
        raise ErrorProgramacion(
            "El espacio academico no existe."
        )

    # Comprobar que existe la version del caso
    # Mismo bloqueo raíz que publicación/archivo; releer incluso si estaba en caché.
    # La transacción del llamador mantiene el bloqueo hasta commit/rollback.
    version = db.get(VersionCasoModel, version_caso_id, populate_existing=True, with_for_update=True)

    if version is None:
        raise ErrorProgramacion(
            "La version del caso no existe."
        )

    # Validar que la version del caso este en estado PUBLICADO (RF-04 / RF-18)
    estado_version = getattr(version, "estado", None)
    valor_estado = getattr(estado_version, "value", estado_version)
    if valor_estado != "PUBLICADO":
        raise ErrorProgramacion(
            "Solo se pueden programar versiones publicadas del caso."
        )

    # El tiempo no debe superar el estimado del caso
    if tiempo_maximo_minutos > version.tiempo_estimado_min:
        raise ErrorProgramacion(
            "El tiempo maximo supera el estimado del caso."
        )

    # Crear la sesion en estado inicial
    sesion = SesionProgramadaModel(
        espacio_academico_id=espacio_academico_id,
        version_caso_id=version_caso_id,
        docente_id=docente_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tiempo_maximo_minutos=tiempo_maximo_minutos,
        lugar=lugar,
        mensaje_personalizado=mensaje_personalizado,
        estado="SIN_INICIAR",
    )

    db.add(sesion)
    db.flush()

    return sesion
