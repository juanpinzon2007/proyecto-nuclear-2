"""Lectura docente de un resultado existente, bajo la autorización de preparación."""
from uuid import UUID
from dataclasses import dataclass
from app.modules.participation.infrastructure.result_repository import ResultadoTecnico
from app.modules.identity.domain.errors import AccesoDenegado, RecursoNoDisponible, IntegracionPendiente
from app.modules.participation.domain.evaluation import EvaluacionInconsistente, PoliticaEvaluacionPendiente
from app.modules.participation.application.errors import ErrorAplicacionParticipacion
from app.modules.participation.infrastructure.evaluation_readiness import ConsultaPreparacionEvaluacionSQLAlchemy


@dataclass(frozen=True)
class ResultadoDocenteAutorizado:
    id_sesion: UUID
    id_convocatoria: UUID
    id_participacion: int
    resultado: ResultadoTecnico


class ConsultaResultadoDocenteSQLAlchemy(ConsultaPreparacionEvaluacionSQLAlchemy):
    def consultar_resultado(self, *, id_sesion: UUID, id_intento: int):
        if not isinstance(id_sesion, UUID) or type(id_intento) is not int or id_intento <= 0:
            raise AccesoDenegado()
        try:
            return self._lectura(lambda s: self._resultado_autorizado(s, id_sesion, id_intento))
        except (EvaluacionInconsistente, PoliticaEvaluacionPendiente, ErrorAplicacionParticipacion):
            raise IntegracionPendiente() from None

    def _resultado_autorizado(self, s, id_sesion, id_intento):
        # Mismo ámbito completo de sesión/caso/grupos/matrícula. Ningún ID del
        # cliente permite saltar a otro intento. Conserva antecedentes retirados.
        revision = self._consultar(s, id_sesion)
        if any('MATRICULA_NO_INEQUIVOCA' in f.pendientes for f in revision.convocatorias):
            raise IntegracionPendiente()
        filas = [(f, i) for f in revision.convocatorias for i in f.intentos if i.id_intento == id_intento]
        if len(filas) != 1:
            raise AccesoDenegado()
        fila, intento = filas[0]
        if intento.id_resultado_tecnico is None:
            raise RecursoNoDisponible()
        resultado = self._resultado_tecnico(s, id_intento)
        if resultado.datos.id_participacion != fila.id_participacion:
            raise IntegracionPendiente()
        return ResultadoDocenteAutorizado(id_sesion, fila.id_convocatoria, fila.id_participacion, resultado)
