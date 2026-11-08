from functools import lru_cache
from secrets import token_urlsafe

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.entities import ContextoAcceso, normalizar_correo
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero


@lru_cache
def obtener_hasheador() -> PasswordHash:
    return PasswordHash.recommended()


@lru_cache
def _hash_descarte() -> str:
    # Solo trabajo de verificación ante cuenta inexistente; no es una cuenta,
    # contraseña predeterminada ni credencial persistida.
    return obtener_hasheador().hash(token_urlsafe(32))


class CredencialesPersonalSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion
        self.usuarios = RepositorioUsuariosSQLAlchemy(sesion)

    def validar(self, correo: str, clave: str) -> ContextoAcceso | None:
        try:
            with self.sesion.no_autoflush:
                cuenta = self.usuarios.obtener_por_correo(correo)
                if cuenta is None:
                    obtener_hasheador().verify(clave, _hash_descarte())
                    return None
                # Mantener cuenta/hash/rol estables hasta terminar la solicitud.
                fila = self.sesion.get(UsuarioORM, id_entero(cuenta.id_usuario),
                    with_for_update={"read": True}, populate_existing=True)
                if fila is None:
                    obtener_hasheador().verify(clave, _hash_descarte())
                    return None
                self.sesion.get(RolORM, fila.id_rol, with_for_update={"read": True}, populate_existing=True)
                actual = self.usuarios.obtener(str(fila.id_usuario))
                if actual is None or normalizar_correo(actual.correo) != correo:
                    return None
                try:
                    coincide = obtener_hasheador().verify(clave, fila.clave_hash)
                except UnknownHashError:
                    # El mensaje de esta excepción contiene el hash; no propagarlo.
                    obtener_hasheador().verify(clave, _hash_descarte())
                    return None
                return actual if coincide else None
        except SQLAlchemyError:
            raise IntegracionPendiente() from None
