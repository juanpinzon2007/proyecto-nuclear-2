"""Persistencia nativa del DBML, sin adaptar la concesión antigua por suposición."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.errors import ConflictoIdentidad, IntegracionPendiente, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM


@dataclass(frozen=True)
class NuevoPermisoIntentoExtra:
    id_participacion: int
    id_profesor: int
    cantidad_autorizada: int
    justificacion: str
    fecha_autorizacion: datetime


class RepositorioPermisosExtraSQLAlchemy:
    """No implementa RepositorioAutorizaciones.guardar(AutorizacionRepeticion).

    El llamador debe verificar creador/estado y resolver la participación en la
    misma transacción. No consume cupos ni crea intentos. La fecha debe llegar
    como timestamp sin zona conforme al DBML; su política temporal sigue pendiente.
    """

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def agregar(self, datos: NuevoPermisoIntentoExtra) -> int:
        if not isinstance(datos.fecha_autorizacion, datetime) or datos.fecha_autorizacion.tzinfo is not None:
            raise ReglaIdentidadInvalida()
        if (type(datos.id_participacion) is not int or type(datos.id_profesor) is not int
                or type(datos.cantidad_autorizada) is not int or not isinstance(datos.justificacion, str)):
            raise ReglaIdentidadInvalida()
        try:
            sentencia = insert(PermisoIntentoExtraORM.__table__).values(
                id_participacion=datos.id_participacion, id_profesor=datos.id_profesor,
                cantidad_autorizada=datos.cantidad_autorizada, justificacion=datos.justificacion,
                fecha_autorizacion=datos.fecha_autorizacion,
            )
            return self.sesion.execute(sentencia.returning(PermisoIntentoExtraORM.id_permiso_extra)).scalar_one()
        except IntegrityError:
            raise ConflictoIdentidad() from None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None
