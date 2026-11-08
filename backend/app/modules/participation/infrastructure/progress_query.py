"""Progreso efectivo sin DML/commit; no sustituye ServicioProgreso ni ServicioCierre."""
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.participation.application.dto import selecciones_de
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.application.progress import proyectar_progreso
from app.modules.participation.application.services import _cargar_autorizado
from app.modules.participation.infrastructure.composition import _Alcance, IdentityIntentoSQLAlchemy, CasesIntentoSQLAlchemy
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy


class ConsultaProgresoSQLAlchemy:
    def __init__(self, *, usuario, crear_sesion, fechas, reloj):
        self.usuario, self.crear_sesion, self.fechas, self.reloj = usuario, crear_sesion, fechas, reloj

    def consultar(self, *, id_estudiante, id_intento):
        try:
            trabajo = UnidadTrabajoSQLAlchemy(lambda s: RepositorioParticipacionSQLAlchemy(s, fechas=self.fechas),
                crear_sesion=self.crear_sesion)
            alcance = _Alcance(lambda: trabajo.sesion, self.usuario, id_intento, self.fechas)
            with trabajo, trabajo.sesion.no_autoflush:
                intento, participacion = _cargar_autorizado(trabajo.repositorio,
                    IdentityIntentoSQLAlchemy(alcance), id_estudiante, id_intento)
                if trabajo.sesion.scalar(select(GrupoEstudianteORM.activo).where(
                    GrupoEstudianteORM.id_grupo_estudiante == participacion.id_grupo_estudiante)) is not True:
                    raise AccesoDenegado("Matrícula no habilitada.")
                # Solo una copia de dominio: el vencimiento efectivo NO se guarda.
                efectivo = intento.actualizar_vencimiento(self.reloj)
                ruta = CasesIntentoSQLAlchemy(alcance, None).obtener_recorrido(
                    id_caso=alcance.datos().id_caso, selecciones=selecciones_de(efectivo))
                return proyectar_progreso(efectivo, ruta)
        except SQLAlchemyError:
            raise ReglaPendiente("La consulta de progreso no está disponible.") from None
