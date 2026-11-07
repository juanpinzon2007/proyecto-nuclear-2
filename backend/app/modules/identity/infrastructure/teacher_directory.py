"""Lectura privada en una instantánea PostgreSQL, sin commit ni autoflush."""
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.application.teacher_directory import CuentaDocente, PaginaDocentes
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente, NoAutenticado, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.models import RolORM, UsuarioORM as U


class ConsultaDocentesSQLAlchemy:
    def __init__(self, crear_sesion: Callable[[], Session]):
        self._crear_sesion = crear_sesion

    def consultar(self, contexto: ContextoAcceso, *, limite: int, desplazamiento: int) -> PaginaDocentes:
        if type(limite) is not int or not 1 <= limite <= 100 or type(desplazamiento) is not int or desplazamiento < 0:
            raise ReglaIdentidadInvalida()
        if not contexto.activo:
            raise NoAutenticado()
        if Rol.ADMINISTRADOR not in contexto.roles:
            raise AccesoDenegado()
        try:
            pk = int(contexto.id_usuario)
        except (ValueError, TypeError):
            raise NoAutenticado() from None
        if not 0 < pk <= 2147483647:
            raise NoAutenticado()
        try:
            with self._crear_sesion() as sesion:
                # Sesión exclusiva de esta consulta. Nunca reutiliza cambios pendientes.
                if sesion.in_transaction() or sesion.new or sesion.dirty or sesion.deleted:
                    raise IntegracionPendiente()
                if sesion.get_bind().dialect.name != 'postgresql':
                    raise IntegracionPendiente()
                sesion.autoflush = False
                sesion.connection(execution_options={
                    'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True,
                })
                actor = sesion.execute(select(U.activo, RolORM.nombre).join(
                    RolORM, RolORM.id_rol == U.id_rol).where(U.id_usuario == pk)).one_or_none()
                if actor is None or not actor.activo:
                    raise NoAutenticado()
                if actor.nombre.strip().upper() != Rol.ADMINISTRADOR.value:
                    raise AccesoDenegado()
                # Misma normalización que RepositorioUsuarios._contexto; sin JOIN
                # con vínculos académicos y sin cargar hashes de cuentas docentes.
                roles = [id_rol for id_rol, nombre in sesion.execute(select(RolORM.id_rol, RolORM.nombre))
                         if nombre.strip().upper() == Rol.DOCENTE.value]
                filtro = U.id_rol.in_(roles)
                total = sesion.scalar(select(func.count()).select_from(U).where(filtro))
                filas = sesion.execute(select(U.id_usuario, U.nombre, U.correo, U.activo).where(filtro)
                    .order_by(U.id_usuario).offset(desplazamiento).limit(limite)).all()
                return PaginaDocentes(tuple(CuentaDocente(str(f.id_usuario), f.nombre, f.correo, f.activo)
                                            for f in filas), total, limite, desplazamiento)
                # Cierre de Session revierte la transacción lectora, nunca commit.
        except (SQLAlchemyError, ValueError):
            raise IntegracionPendiente() from None
