from collections.abc import Callable

from app.modules.identity.application.ports import ConsultaAmbitoAcademico
from app.modules.identity.domain.entities import ContextoAcceso, Rol, validar_id
from app.modules.identity.domain.errors import AccesoDenegado, NoAutenticado


class ServicioAutorizacion:
    def __init__(self, academia: Callable[[], ConsultaAmbitoAcademico]) -> None:
        self._academia = academia

    @staticmethod
    def exigir_rol(contexto: ContextoAcceso, rol: Rol) -> None:
        if not contexto.activo:
            raise NoAutenticado()
        if rol not in contexto.roles:
            raise AccesoDenegado()

    def exigir_permiso(self, contexto: ContextoAcceso, codigo: str) -> None:
        """RF-02: comprobar permisos específicos del catálogo persistido."""
        if not contexto.activo:
            raise NoAutenticado()
        if codigo not in contexto.permisos:
            raise AccesoDenegado()

    def exigir_participacion(self, contexto: ContextoAcceso, id_participacion: str) -> None:
        self.exigir_rol(contexto, Rol.DOCENTE)
        validar_id(id_participacion)
        if self._academia().puede_consultar_participacion(contexto.id_usuario, id_participacion) is not True:
            raise AccesoDenegado()

    def exigir_sesion(self, contexto: ContextoAcceso, id_sesion: str) -> None:
        self.exigir_rol(contexto, Rol.DOCENTE)
        validar_id(id_sesion)
        if self._academia().puede_consultar_sesion(contexto.id_usuario, id_sesion) is not True:
            raise AccesoDenegado()
