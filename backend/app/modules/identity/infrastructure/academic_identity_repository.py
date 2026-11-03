"""Consulta y registro interno de vínculos, sobre Session ajena y sin commits.

Solo un proceso administrativo autorizado debe llamar agregar_verificado con
evidencia externa. Este repositorio no certifica esa evidencia ni expone un API.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.domain.errors import ConflictoIdentidad, IntegracionPendiente, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.repositories import id_entero


class RepositorioIdentidadAcademicaSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def obtener(self, *, id_usuario: str, sistema: SistemaAcademico) -> tuple[VinculoAcademico, ...]:
        try:
            identificador = id_entero(id_usuario)
            if not isinstance(sistema, SistemaAcademico):
                raise ReglaIdentidadInvalida()
            with self.sesion.no_autoflush:
                filas = self.sesion.scalars(select(IdentidadAcademicaORM).where(
                    IdentidadAcademicaORM.id_usuario == identificador,
                    IdentidadAcademicaORM.sistema == sistema.value,
                ).order_by(IdentidadAcademicaORM.id_academico)).all()
            vinculos = tuple(VinculoAcademico(str(f.id_usuario), SistemaAcademico(f.sistema), f.id_academico)
                             for f in filas)
            if any(v.id_usuario != id_usuario or v.sistema != sistema
                   or not isinstance(v.id_academico, UUID) or v.id_academico.int == 0 for v in vinculos):
                raise IntegracionPendiente()
            return vinculos
        except (SQLAlchemyError, ReglaIdentidadInvalida, ValueError, TypeError, AttributeError):
            raise IntegracionPendiente() from None

    def agregar_verificado(self, vinculo: VinculoAcademico) -> None:
        """Inserta sin reasignación/upsert. El llamador controla commit/rollback."""
        if (not isinstance(vinculo, VinculoAcademico) or not isinstance(vinculo.sistema, SistemaAcademico)
                or not isinstance(vinculo.id_academico, UUID) or vinculo.id_academico.int == 0):
            raise ReglaIdentidadInvalida()
        identificador = id_entero(vinculo.id_usuario)
        try:
            self.sesion.add(IdentidadAcademicaORM(
                id_usuario=identificador, sistema=vinculo.sistema.value, id_academico=vinculo.id_academico,
            ))
            self.sesion.flush()
        except IntegrityError:
            raise ConflictoIdentidad() from None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None
