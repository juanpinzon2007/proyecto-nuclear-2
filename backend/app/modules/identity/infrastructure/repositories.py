"""Repositorios síncronos sobre la Session común. Nunca hacen commit propio."""

import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.entities import (
    AutorizacionesDocente, ContextoAcceso, DatosAltaDocente, Rol, normalizar_correo,
)
from app.modules.identity.domain.errors import (
    ConflictoIdentidad, IntegracionPendiente, RecursoNoDisponible, ReglaIdentidadInvalida,
)
from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM


def id_entero(identificador: str) -> int:
    if not isinstance(identificador, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", identificador):
        raise ReglaIdentidadInvalida()
    valor = int(identificador)
    if valor > 2_147_483_647:
        raise ReglaIdentidadInvalida()
    return valor


class RepositorioUsuariosSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def _permisos_rol(self, id_rol: int) -> frozenset[str]:
        return frozenset(self.sesion.scalars(
            select(PermisoORM.codigo).join(RolPermisoORM, RolPermisoORM.id_permiso == PermisoORM.id_permiso)
            .where(RolPermisoORM.id_rol == id_rol)
        ))

    def _contexto(self, usuario: UsuarioORM) -> ContextoAcceso:
        rol = self.sesion.get(RolORM, usuario.id_rol)
        if rol is None:
            raise IntegracionPendiente()
        try:
            rol_acceso = Rol(rol.nombre.strip().upper())
        except ValueError:
            # No convertir un nombre de catálogo desconocido en otro rol.
            raise IntegracionPendiente() from None
        return ContextoAcceso(str(usuario.id_usuario), usuario.correo, frozenset({rol_acceso}),
                             self._permisos_rol(usuario.id_rol), usuario.activo)

    def obtener(self, id_usuario: str) -> ContextoAcceso | None:
        try:
            identificador = id_entero(id_usuario)
        except ReglaIdentidadInvalida:
            return None
        try:
            usuario = self.sesion.get(UsuarioORM, identificador, populate_existing=True)
            return self._contexto(usuario) if usuario is not None else None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def obtener_por_correo(self, correo: str) -> ContextoAcceso | None:
        normalizado = normalizar_correo(correo)
        try:
            # El UNIQUE actual no cubre strip/casefold. Leer solo IDs/correos y
            # comparar con la misma normalización Python, también para Unicode.
            # Un índice normalizado requerirá reconciliación/migración posterior.
            candidatos = []
            with self.sesion.no_autoflush:
                for identificador, guardado in self.sesion.execute(select(UsuarioORM.id_usuario, UsuarioORM.correo)):
                    try:
                        coincide = normalizar_correo(guardado) == normalizado
                    except ReglaIdentidadInvalida:
                        continue
                    if coincide:
                        candidatos.append(identificador)
            if len(candidatos) > 1:
                raise IntegracionPendiente()
            return self.obtener(str(candidatos[0])) if candidatos else None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def obtener_para_escritura(self, id_usuario: str) -> ContextoAcceso | None:
        """Locks compartidos de cuenta y rol, retenidos por la UoW existente.

        FOR SHARE bloquea UPDATE de activo/id_rol y renombrado del rol hasta el
        commit/rollback. populate_existing evita la identidad ORM precargada.
        Solo lo usa la administración escritora, no las consultas READ ONLY.
        """
        identificador = id_entero(id_usuario)
        try:
            with self.sesion.no_autoflush:
                usuario = self.sesion.get(UsuarioORM, identificador,
                    with_for_update={'read': True}, populate_existing=True)
                if usuario is None:
                    return None
                self.sesion.get(RolORM, usuario.id_rol,
                    with_for_update={'read': True}, populate_existing=True)
                return self._contexto(usuario)
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def permisos_existentes(self, permisos: frozenset[str]) -> bool:
        if any(not p.strip() or len(p) > 80 for p in permisos):
            return False
        if not permisos:
            return True
        try:
            encontrados = frozenset(self.sesion.scalars(select(PermisoORM.codigo).where(PermisoORM.codigo.in_(permisos))))
            return encontrados == permisos
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def _rol_confirmado(self, autorizaciones: AutorizacionesDocente) -> RolORM:
        if len(autorizaciones.roles) != 1:
            raise ReglaIdentidadInvalida()
        nombre = next(iter(autorizaciones.roles)).value
        rol = self.sesion.scalars(select(RolORM).where(func.upper(func.trim(RolORM.nombre)) == nombre)).one_or_none()
        if rol is None:
            raise IntegracionPendiente()
        # El ER solo admite permisos del rol. No editar rol_permiso para conceder
        # excepciones a un docente ni afectar a todos los usuarios de su rol.
        if self._permisos_rol(rol.id_rol) != autorizaciones.permisos:
            raise ReglaIdentidadInvalida()
        return rol

    def crear_docente(self, correo: str, autorizaciones: AutorizacionesDocente,
                      *, datos: DatosAltaDocente | None = None) -> ContextoAcceso:
        if datos is None:
            # nombre y clave_hash son NOT NULL; no fabricar valores sustitutos.
            raise ReglaIdentidadInvalida()
        correo = normalizar_correo(correo)
        if len(correo) > 200 or not datos.nombre.strip() or len(datos.nombre) > 120:
            raise ReglaIdentidadInvalida()
        if not datos.clave_hash or len(datos.clave_hash) > 255:
            raise ReglaIdentidadInvalida()
        try:
            rol = self._rol_confirmado(autorizaciones)
            usuario = UsuarioORM(id_rol=rol.id_rol, nombre=datos.nombre.strip(), correo=correo,
                                 clave_hash=datos.clave_hash)
            self.sesion.add(usuario)
            self.sesion.flush()
            return self._contexto(usuario)
        except IntegrityError:
            raise ConflictoIdentidad() from None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def asignar_autorizaciones(self, id_docente: str, autorizaciones: AutorizacionesDocente) -> ContextoAcceso:
        identificador = id_entero(id_docente)
        try:
            usuario = self.sesion.get(UsuarioORM, identificador)
            if usuario is None or Rol.DOCENTE not in self._contexto(usuario).roles:
                raise RecursoNoDisponible()
            usuario.id_rol = self._rol_confirmado(autorizaciones).id_rol
            self.sesion.flush()
            return self._contexto(usuario)
        except IntegrityError:
            raise ConflictoIdentidad() from None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None
