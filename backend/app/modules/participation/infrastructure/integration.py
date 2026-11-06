"""Lectura integrada sobre una Session ajena; sin commits, escrituras ni HTTP.

No implementa SchedulingPort ni RepositorioParticipacion: sus identificadores y
garantías de inicio no están resueltos. Esta consulta no debe usarse como permiso
reutilizable ni seguida de una escritura de intento en otra transacción.
El llamador conserva la responsabilidad de rollback/cierre de la Session.
"""

from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.cases.application.published_version import ConsultaVersionPublicada, consultar_version_publicada
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import AccesoDenegado as AccesoIdentity, IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.participation.application.errors import AccesoDenegado, RecursoNoDisponible, ReglaPendiente
from app.modules.participation.application.integration_ports import ContextoIngresoParticipacion
from app.modules.scheduling.application.validar_ingreso import ErrorIngreso, validar_ingreso
from app.modules.scheduling.domain.ingress_policy import PoliticaIngreso, PoliticaTemporalNoDisponible, RelojIngreso


class ConsultaIngresoSQLAlchemy:
    def __init__(
        self, sesion: Session, *, politica: PoliticaIngreso, reloj: RelojIngreso,
        consulta_version: ConsultaVersionPublicada | None = None,
        admision=None,
    ) -> None:
        self.sesion = sesion
        self.politica = politica
        self.reloj = reloj
        self.admision = admision
        # Composición interna del servidor; nunca una opción elegida desde HTTP.
        self._consulta_version = consultar_version_publicada if consulta_version is None else consulta_version

    def consultar(
        self, *, usuario: ContextoAcceso, convocatoria_id: UUID, codigo_acceso: str,
    ) -> ContextoIngresoParticipacion:
        # Ni siquiera volcar cambios pendientes de una Session prestada al leer.
        with self.sesion.no_autoflush:
            return self._consultar(usuario, convocatoria_id, codigo_acceso)

    def _consultar(
        self, usuario: ContextoAcceso, convocatoria_id: UUID, codigo_acceso: str,
    ) -> ContextoIngresoParticipacion:
        try:
            # Releer cuenta/rol: no tomar roles de datos entregados por el llamador.
            usuarios = RepositorioUsuariosSQLAlchemy(self.sesion)
            actual = usuarios.obtener(usuario.id_usuario)
            if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
                raise AccesoDenegado("La cuenta no está autorizada para el ingreso.")
            resolver = ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(self.sesion))
            ValidadorConvocatoriaScheduling(self.sesion, usuarios, resolver).validar_contexto(
                id_usuario=actual.id_usuario, contexto=usuario.id_convocatoria, solicitada=convocatoria_id,
            )
            estudiante = resolver.resolver(id_usuario=actual.id_usuario, sistema=SistemaAcademico.SCHEDULING)
            # Scheduling conserva todas las reglas de código, estado y horario.
            sesion = validar_ingreso(
                self.sesion, convocatoria_id=convocatoria_id, estudiante_id=estudiante,
                codigo_acceso=codigo_acceso, politica=self.politica, reloj=self.reloj,admision=self.admision,
            )
            version = self._consulta_version(self.sesion, version_id=sesion.version_caso_id)
            return ContextoIngresoParticipacion(
                estudiante_scheduling_id=estudiante, convocatoria_id=convocatoria_id,
                sesion_id=sesion.id, caso_id=version.caso_id, version_caso_id=version.version_id,
                numero_version=version.numero, tiempo_maximo=timedelta(minutes=sesion.tiempo_maximo_minutos),
                rubrica_id=version.rubrica_id, version_regla=version.version_regla,
            )
        except (AccesoIdentity, ErrorIngreso):
            raise AccesoDenegado("Ingreso no autorizado.") from None
        except CasoNoEncontradoError:
            raise RecursoNoDisponible("La versión asignada no está disponible.") from None
        except (IntegracionPendiente, PoliticaTemporalNoDisponible, SQLAlchemyError):
            raise ReglaPendiente("La política o infraestructura de ingreso no está disponible.") from None
