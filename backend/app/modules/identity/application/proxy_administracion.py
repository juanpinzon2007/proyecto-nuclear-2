from collections.abc import Callable

from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import IServicioAdministracion
from app.modules.identity.domain.entities import AutorizacionesDocente, ContextoAcceso, Rol


class ProxyAdministracionUsuarios:
    def __init__(self, real: Callable[[], IServicioAdministracion], autorizacion: ServicioAutorizacion) -> None:
        self._real = real
        self._autorizacion = autorizacion

    def crear_docente(self, contexto: ContextoAcceso, correo: str,
                      autorizaciones: AutorizacionesDocente, *, nombre: str | None = None,
                      clave: str | None = None) -> ContextoAcceso:
        self._autorizacion.exigir_rol(contexto, Rol.ADMINISTRADOR)
        if nombre is not None or clave is not None:
            return self._real().crear_docente(contexto, correo, autorizaciones, nombre=nombre, clave=clave)
        return self._real().crear_docente(contexto, correo, autorizaciones)

    def asignar_autorizaciones(self, contexto: ContextoAcceso, id_docente: str,
                              autorizaciones: AutorizacionesDocente) -> ContextoAcceso:
        self._autorizacion.exigir_rol(contexto, Rol.ADMINISTRADOR)
        return self._real().asignar_autorizaciones(contexto, id_docente, autorizaciones)
