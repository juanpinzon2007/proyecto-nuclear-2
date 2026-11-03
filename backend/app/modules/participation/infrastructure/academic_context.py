"""Vinculación de lectura BD2-06 sobre estructuras autorizadas, sin escrituras.

Compone 8A para identidad/convocatoria/horario/Cases y acredita una asignación
explícita por relaciones reales. No implementa IdentityPort ni SchedulingPort de
inicio: la fotografía puede cambiar y debe revalidarse dentro de la futura UoW.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.cases.application.published_version import ConsultaVersionPublicada
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel, RubricaModel
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import ReglaIdentidadInvalida
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.application.integration_ports import ContextoVinculadoParticipacion
from app.modules.participation.infrastructure.integration import ConsultaIngresoSQLAlchemy
from app.modules.scheduling.domain.ingress_policy import PoliticaIngreso, RelojIngreso
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel


class ConsultaVinculacionSQLAlchemy:
    def __init__(
        self, sesion: Session, *, politica: PoliticaIngreso, reloj: RelojIngreso,
        consulta_version: ConsultaVersionPublicada | None = None,
    ) -> None:
        self.sesion = sesion
        self._ingreso = ConsultaIngresoSQLAlchemy(
            sesion, politica=politica, reloj=reloj, consulta_version=consulta_version,
        )

    def consultar(
        self, *, usuario: ContextoAcceso, convocatoria_id: UUID,
        codigo_acceso: str, id_asignacion: int,
    ) -> ContextoVinculadoParticipacion:
        try:
            # Adaptación de la MISMA PK por el contrato real de Identity,
            # nunca una conversión INTEGER/UUID ni una identidad del cliente.
            cuenta = id_entero(usuario.id_usuario)
        except ReglaIdentidadInvalida:
            raise AccesoDenegado("Vinculación académica no disponible.") from None
        if type(id_asignacion) is not int or not 0 < id_asignacion <= 2147483647:
            raise AccesoDenegado("Vinculación académica no disponible.")
        try:
            with self.sesion.no_autoflush:
                ingreso = self._ingreso.consultar(
                    usuario=usuario, convocatoria_id=convocatoria_id, codigo_acceso=codigo_acceso,
                )
                a, m = AsignacionCasoModel, GrupoEstudianteORM
                c, v, s, r, convocada = CasoModel, VersionCasoModel, SesionProgramadaModel, RubricaModel, ConvocatoriaModel
                filas = self.sesion.execute(
                    select(a.id_asignacion, a.id_grupo, a.id_caso, m.id_grupo_estudiante)
                    .select_from(a)
                    .join(m, m.id_grupo == a.id_grupo)
                    .join(c, c.id_caso == a.id_caso)
                    .join(v, (v.id == a.version_caso_id) & (v.caso_id == c.id))
                    .join(s, (s.id == a.sesion_programada_id) & (s.version_caso_id == v.id))
                    .join(convocada, convocada.sesion_id == s.id)
                    .join(r, r.version_caso_id == v.id)
                    .where(
                        a.id_asignacion == id_asignacion,
                        m.id_estudiante == cuenta, m.activo.is_(True),
                        convocada.id == convocatoria_id, convocada.estado == "ACTIVA",
                        convocada.estudiante_id == ingreso.estudiante_scheduling_id,
                        s.id == ingreso.sesion_id, s.estado == "EN_CURSO",
                        c.id == ingreso.caso_id, v.id == ingreso.version_caso_id,
                        v.numero == ingreso.numero_version, v.estado == "PUBLICADO",
                        r.id == ingreso.rubrica_id, r.version_regla == ingreso.version_regla,
                    )
                ).all()
                if not filas:
                    # Igual respuesta para inexistencia, datos ajenos o incompatibles.
                    raise AccesoDenegado("Vinculación académica no disponible.")
                if len(filas) != 1:
                    raise ReglaPendiente("La vinculación académica no es inequívoca.")
                fila = filas[0]
                return ContextoVinculadoParticipacion(
                    ingreso=ingreso, id_usuario=cuenta,
                    id_grupo_estudiante=fila.id_grupo_estudiante, id_grupo=fila.id_grupo,
                    id_asignacion=fila.id_asignacion, id_caso_academico=fila.id_caso,
                )
        except SQLAlchemyError:
            raise ReglaPendiente("La infraestructura de vinculación no está disponible.") from None
