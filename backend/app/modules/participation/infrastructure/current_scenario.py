"""Consulta sin commit ni cambios de estado, sobre la UoW y autoridad existentes."""
from sqlalchemy.exc import SQLAlchemyError

from app.modules.participation.application.dto import selecciones_de
from app.modules.participation.application.errors import ReglaPendiente
from app.modules.participation.application.services import _cargar_autorizado
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.errors import IntentoNoEditable
from app.modules.participation.infrastructure.cases_route import RecorridoCasesSQLAlchemy
from app.modules.participation.infrastructure.composition import (
    _Alcance, IdentityIntentoSQLAlchemy, SchedulingIntentoSQLAlchemy,
    AutorizacionRespuestaScheduling,
)
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy


class ConsultaEscenarioActualSQLAlchemy:
    def __init__(self, *, usuario, crear_sesion, fechas, reloj):
        self.usuario, self.crear_sesion, self.fechas, self.reloj = usuario, crear_sesion, fechas, reloj

    def consultar(self, *, id_estudiante: int, id_intento: int):
        try:
            trabajo = UnidadTrabajoSQLAlchemy(
                lambda s: RepositorioParticipacionSQLAlchemy(s, fechas=self.fechas),
                crear_sesion=self.crear_sesion)
            alcance = _Alcance(lambda: trabajo.sesion, self.usuario, id_intento, self.fechas)
            with trabajo:
                intento, participacion = _cargar_autorizado(trabajo.repositorio,
                    IdentityIntentoSQLAlchemy(alcance), id_estudiante, id_intento)
                if intento.estado != EstadoIntento.EN_CURSO:
                    raise IntentoNoEditable("El contenido activo no está disponible.")
                scheduling = SchedulingIntentoSQLAlchemy(alcance, AutorizacionRespuestaScheduling(), self.reloj)
                scheduling.validar_edicion(id_asignacion=participacion.id_asignacion,
                    id_grupo_estudiante=participacion.id_grupo_estudiante, operacion="RESPONDER")
                # El reloj se vuelve a consultar DESPUÉS de adquirir los locks;
                # no reutilizar una hora anterior a una espera concurrente.
                instante = intento._exigir_editable(self.reloj)
                scheduling.validar_instante_registro(instante=instante)
                # La identidad y Scheduling han revalidado las relaciones de esta
                # misma transacción. Nunca se busca la última edición publicada.
                return RecorridoCasesSQLAlchemy(alcance.sesion).obtener_actual(
                    version_id=alcance.datos().version_caso_id, selecciones=selecciones_de(intento))
                # Salida sin commit: la UoW revierte/cierra y libera los locks.
        except SQLAlchemyError:
            raise ReglaPendiente("La consulta no está disponible.") from None
