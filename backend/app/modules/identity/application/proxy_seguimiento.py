from collections.abc import Callable

from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import IServicioSeguimiento
from app.modules.identity.domain.entities import ContextoAcceso, DetalleParticipacion, FeedbackDocente, ResumenCaso, Rol


class ProxySeguimiento:
    """Misma interfaz que ServicioSeguimiento; autoriza antes de obtener/delegar."""

    def __init__(self, real: Callable[[], IServicioSeguimiento], autorizacion: ServicioAutorizacion) -> None:
        self._real = real
        self._autorizacion = autorizacion

    def listar_casos_realizados(self, contexto: ContextoAcceso) -> tuple[ResumenCaso, ...]:
        self._autorizacion.exigir_rol(contexto, Rol.DOCENTE)
        return self._real().listar_casos_realizados(contexto)

    def listar_participaciones(self, contexto: ContextoAcceso, id_caso: str):
        self._autorizacion.exigir_rol(contexto, Rol.DOCENTE)
        return self._real().listar_participaciones(contexto, id_caso)

    def consultar_participacion(self, contexto: ContextoAcceso, id_participacion: str) -> DetalleParticipacion:
        self._autorizacion.exigir_participacion(contexto, id_participacion)
        return self._real().consultar_participacion(contexto, id_participacion)

    def descargar_reporte(self, contexto: ContextoAcceso, id_sesion: str, *, formato=None, filtros=None):
        if formato is not None:
            # El lector oficial verifica sesión/caso/grupos en su propia snapshot RO.
            # El contrato CSV anterior conserva su guard de integración pendiente.
            self._autorizacion.exigir_rol(contexto, Rol.DOCENTE)
            return self._real().descargar_reporte(contexto, id_sesion, formato=formato, filtros=filtros)
        self._autorizacion.exigir_sesion(contexto, id_sesion)
        return self._real().descargar_reporte(contexto, id_sesion)

    def registrar_feedback(self, contexto: ContextoAcceso, id_participacion: str, texto: str) -> FeedbackDocente:
        self._autorizacion.exigir_participacion(contexto, id_participacion)
        return self._real().registrar_feedback(contexto, id_participacion, texto)
