from collections.abc import Callable

from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import IServicioExcepciones
from app.modules.identity.domain.entities import AutorizacionRepeticion, ContextoAcceso, Rol


class ProxyExcepciones:
    def __init__(self, real: Callable[[], IServicioExcepciones], autorizacion: ServicioAutorizacion) -> None:
        self._real = real
        self._autorizacion = autorizacion

    def autorizar_repeticion(self, contexto: ContextoAcceso, id_sesion: str,
                            id_estudiante: str) -> AutorizacionRepeticion:
        self._autorizacion.exigir_rol(contexto, Rol.DOCENTE)
        # El servicio verifica creador, participación previa y sesión bajo UoW.
        return self._real().autorizar_repeticion(contexto, id_sesion, id_estudiante)
