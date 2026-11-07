"""Inicialización operativa del primer administrador; nunca un registro HTTP.

Solo un operador con acceso al despliegue y a su configuración SQL puede usarlo.
No crea catálogos, permisos, vínculos académicos ni mecanismos de recuperación.
"""
import argparse
import getpass
import sys
import warnings
from typing import cast

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError

from app.modules.identity.domain.entities import Rol, normalizar_correo
from app.modules.identity.domain.errors import (
    ConflictoIdentidad, ErrorIdentidad, IntegracionPendiente, ReglaIdentidadInvalida,
)
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import RolORM, UsuarioORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy


class _RepositorioInicializacion(RepositorioUsuariosSQLAlchemy):
    def inicializar(self, *, correo, nombre, clave_hash):
        s = self.sesion
        if s.get_bind().dialect.name != 'postgresql' or s.connection().get_isolation_level() != 'READ COMMITTED':
            raise IntegracionPendiente()
        s.execute(text('SET LOCAL search_path = pg_catalog, public, pg_temp'))
        # Serializa comprobación de inexistencia + INSERT, incluso frente a otros
        # escritores normales de usuario. No depende de un SELECT sin filas.
        s.execute(text('LOCK TABLE public.usuario, public.rol IN SHARE ROW EXCLUSIVE MODE'))
        catalogo = s.scalars(select(RolORM).order_by(RolORM.id_rol)
            .with_for_update(read=True).execution_options(populate_existing=True)).all()
        # Exactamente la normalización de RepositorioUsuarios._contexto, también
        # para tabulaciones/saltos históricos. SQL trim no equivale a str.strip.
        roles = [r for r in catalogo if r.nombre.strip().upper() == Rol.ADMINISTRADOR.value]
        if len(roles) != 1:
            raise IntegracionPendiente()
        rol = roles[0]
        # Incluye inactivos: esta operación no reactiva ni recupera cuentas.
        if s.scalar(select(UsuarioORM.id_usuario).where(UsuarioORM.id_rol == rol.id_rol).limit(1)) is not None:
            raise ConflictoIdentidad()
        if self.obtener_por_correo(correo) is not None:
            raise ConflictoIdentidad()
        nuevo = UsuarioORM(id_rol=rol.id_rol, nombre=nombre, correo=correo,
                           clave_hash=clave_hash, activo=True)
        s.add(nuevo)
        s.flush()
        return self._contexto(nuevo)


def inicializar_primer_administrador(*, correo, nombre, clave, crear_sesion):
    """Operación interna de despliegue. La fábrica debe entregar Session nueva.

    Devuelve la identidad solo después del commit. No es un servicio disponible
    para clientes ni permite elegir rol, permisos, estado o UUID académicos.
    """
    if not isinstance(correo, str):
        raise ReglaIdentidadInvalida()
    correo = normalizar_correo(correo)
    if (len(correo) > 200 or not isinstance(nombre, str) or not nombre.strip()
            or len(nombre) > 120 or not isinstance(clave, str) or not 1 <= len(clave) <= 1024):
        raise ReglaIdentidadInvalida()
    clave_hash = obtener_hasheador().hash(clave)

    def nueva_sesion():
        s = crear_sesion()
        if s.in_transaction():
            # No cerrar ni revertir una transacción entregada por error.
            raise IntegracionPendiente()
        return s

    try:
        with UnidadTrabajoIdentitySQLAlchemy(usuarios=_RepositorioInicializacion, sesiones=nueva_sesion) as t:
            nuevo = cast(_RepositorioInicializacion, t.usuarios).inicializar(
                correo=correo, nombre=nombre.strip(), clave_hash=clave_hash)
            t.commit()
        return nuevo
    except IntegrityError:
        raise ConflictoIdentidad() from None
    except DBAPIError as error:
        if getattr(error.orig, 'sqlstate', None) in {'40001', '40P01', '55P03'}:
            raise ConflictoIdentidad() from None
        raise IntegracionPendiente() from None
    except SQLAlchemyError:
        raise IntegracionPendiente() from None


class _ArgumentosSeguros(argparse.ArgumentParser):
    def error(self, message):
        # argparse normalmente incluye el argumento inválido: podría ser una
        # contraseña que el operador intentó pasar por error. No reflejar argv.
        raise ValueError('Argumentos inválidos. Consulte --help.')


def main(argv=None):
    parser = _ArgumentosSeguros(description='Inicializar una sola vez el primer administrador. Sin ruta HTTP.')
    parser.add_argument('--correo', required=True)
    parser.add_argument('--nombre', required=True)
    parser.add_argument('--confirmar-base', required=True, help='Nombre exacto de la base configurada del despliegue.')
    try:
        args = parser.parse_args(argv)
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            raise ValueError('Se requiere una consola interactiva para leer la clave sin eco.')
        from app.core.config import get_settings
        from app.db.session import get_session_factory
        if args.confirmar_base != get_settings().postgres_db:
            raise ValueError('La base confirmada no coincide con la configuración.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            clave = getpass.getpass('Clave del administrador inicial: ')
            confirmacion = getpass.getpass('Repita la clave: ')
        if clave != confirmacion:
            raise ValueError('Las claves no coinciden.')
        try:
            fabrica = get_session_factory()
        except ValueError:
            raise IntegracionPendiente() from None
        nuevo = inicializar_primer_administrador(correo=args.correo, nombre=args.nombre,
            clave=clave, crear_sesion=fabrica)
        print(f'Administrador inicial creado. id_usuario={nuevo.id_usuario}')
        return 0
    except ConflictoIdentidad:
        print('Inicialización rechazada: ya existe administrador o el correo no está disponible.', file=sys.stderr)
        return 3
    except (ValueError, ReglaIdentidadInvalida, getpass.GetPassWarning):
        print('Entrada o consola inválida. No se inicializó el administrador.', file=sys.stderr)
        return 2
    except (ErrorIdentidad, SQLAlchemyError):
        print('Inicialización no disponible. Revise el catálogo y la configuración con el equipo.', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('Inicialización cancelada.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
