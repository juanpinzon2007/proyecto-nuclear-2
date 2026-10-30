"""LEFT OUTER JOIN de las relaciones confirmadas por el DBML.

Solo consulta participaciones existentes autorizadas por el servidor. No afirma
que sean el padrón completo de convocados y no implementa aún LecturaReportes:
faltan ese contrato de Scheduling y el mapeo oficial de situacion de Participation.
Las tablas externas se reciben explícitamente; no se definen modelos ajenos.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Table, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.errors import IntegracionPendiente, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.models import UsuarioORM


@dataclass(frozen=True)
class TablasLecturaReporte:
    participacion: Table
    grupo_estudiante: Table
    resultado_participacion: Table

    def __post_init__(self) -> None:
        for tabla, nombre, columnas in (
            (self.participacion, "participacion", {"id_participacion", "id_asignacion", "id_grupo_estudiante"}),
            (self.grupo_estudiante, "grupo_estudiante", {"id_grupo_estudiante", "id_estudiante"}),
            (self.resultado_participacion, "resultado_participacion", {"id_participacion", "situacion", "nota_definitiva"}),
        ):
            if not isinstance(tabla, Table) or tabla.name != nombre or not columnas.issubset(tabla.c.keys()):
                raise IntegracionPendiente()


@dataclass(frozen=True)
class ResultadoReporteCrudo:
    id_estudiante: int
    id_participacion: int
    situacion: str | None
    nota: Decimal | None


class ConsultaResultadosReporteSQLAlchemy:
    def __init__(self, sesion: Session, tablas: TablasLecturaReporte) -> None:
        self.sesion = sesion
        self.tablas = tablas

    def sentencia(self, id_asignacion: int, participaciones_autorizadas: tuple[int, ...]):
        if type(id_asignacion) is not int or id_asignacion <= 0 or any(
            type(i) is not int or i <= 0 for i in participaciones_autorizadas
        ):
            raise ReglaIdentidadInvalida()
        p, ge, r = self.tablas.participacion, self.tablas.grupo_estudiante, self.tablas.resultado_participacion
        u = UsuarioORM.__table__
        fuente = p.join(ge, p.c.id_grupo_estudiante == ge.c.id_grupo_estudiante).join(
            u, ge.c.id_estudiante == u.c.id_usuario,
        ).outerjoin(r, r.c.id_participacion == p.c.id_participacion)
        return select(
            u.c.id_usuario.label("id_estudiante"), p.c.id_participacion,
            r.c.situacion, r.c.nota_definitiva.label("nota"),
        ).select_from(fuente).where(
            p.c.id_asignacion == id_asignacion,
            p.c.id_participacion.in_(participaciones_autorizadas),
        ).order_by(u.c.id_usuario, p.c.id_participacion)

    def consultar(self, id_asignacion: int, participaciones_autorizadas: tuple[int, ...]) -> tuple[ResultadoReporteCrudo, ...]:
        try:
            filas = self.sesion.execute(self.sentencia(id_asignacion, participaciones_autorizadas)).mappings()
            return tuple(ResultadoReporteCrudo(**fila) for fila in filas)
        except SQLAlchemyError:
            raise IntegracionPendiente() from None
