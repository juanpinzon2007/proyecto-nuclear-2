"""Lectura completa de cabecera; no simula el agregado ni un progreso sin pasos.

Reutiliza Identity/convocatoria sin aplicar RF-22 a una lectura de estado. No
compone Facade ni escritores y no devuelve permiso de continuación o evaluación.
"""
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel, RubricaModel
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import AccesoDenegado as AccesoIdentity, IntegracionPendiente
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.participation.application.dto import ResumenIntento
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente
from app.modules.participation.infrastructure.models import IntentoModel, ParticipacionModel
from app.modules.participation.infrastructure.queries import consultar_duracion_historica
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel


class ConsultaEstadoIntentoSQLAlchemy:
    def __init__(self, sesion: Session, *, fechas: FechasPersistencia) -> None:
        self.sesion = sesion
        self.fechas = fechas

    def consultar(self, *, usuario: ContextoAcceso, id_intento: int) -> ResumenIntento:
        if type(id_intento) is not int or not 0 < id_intento <= 2147483647:
            raise AccesoDenegado("Intento no disponible.")
        try:
            with self.sesion.no_autoflush:
                usuarios = RepositorioUsuariosSQLAlchemy(self.sesion)
                actual = usuarios.obtener(usuario.id_usuario)
                if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
                    raise AccesoDenegado("Intento no disponible.")
                resolver = ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(self.sesion))
                estudiante = resolver.resolver(id_usuario=actual.id_usuario, sistema=SistemaAcademico.SCHEDULING)
                i, p, m, a, c, s = IntentoModel, ParticipacionModel, GrupoEstudianteORM, AsignacionCasoModel, ConvocatoriaModel, SesionProgramadaModel
                v, caso, rubrica = VersionCasoModel, CasoModel, RubricaModel
                fila = self.sesion.execute(select(
                    i.id_intento, i.id_participacion, i.numero_intento, i.estado, i.inicio, i.fin, c.id.label("convocatoria_id"),
                ).select_from(i)
                    .join(p, p.id_participacion == i.id_participacion)
                    .join(m, m.id_grupo_estudiante == p.id_grupo_estudiante)
                    .join(a, (a.id_asignacion == p.id_asignacion) & (a.id_grupo == m.id_grupo))
                    .join(c, (c.id == p.convocatoria_id) & (c.sesion_id == a.sesion_programada_id))
                    .join(s, (s.id == c.sesion_id) & (s.version_caso_id == a.version_caso_id))
                    .join(v, v.id == a.version_caso_id)
                    .join(caso, (caso.id == v.caso_id) & (caso.id_caso == a.id_caso))
                    .join(rubrica, rubrica.version_caso_id == v.id)
                    .where(i.id_intento == id_intento, m.id_estudiante == id_entero(actual.id_usuario), c.estudiante_id == estudiante)
                ).one_or_none()
                if fila is None:
                    raise AccesoDenegado("Intento no disponible.")
                ValidadorConvocatoriaScheduling(self.sesion, usuarios, resolver).validar_contexto(
                    id_usuario=actual.id_usuario, contexto=usuario.id_convocatoria, solicitada=fila.convocatoria_id,
                )
                try:
                    estado = EstadoIntento(fila.estado)
                except ValueError:
                    raise MapeoPersistenciaPendiente("Estado persistido sin correspondencia aprobada.") from None
                inicio = self.fechas.desde_db(fila.inicio)
                fin = self.fechas.desde_db(fila.fin) if fila.fin is not None else None
                duracion = consultar_duracion_historica(self.sesion, fila.id_intento)
                return ResumenIntento(fila.id_intento, fila.id_participacion, fila.numero_intento,
                                     estado, inicio, fin, inicio + duracion)
        except AccesoIdentity:
            raise AccesoDenegado("Intento no disponible.") from None
        except (IntegracionPendiente, SQLAlchemyError):
            raise ReglaPendiente("La infraestructura de consulta no está disponible.") from None
