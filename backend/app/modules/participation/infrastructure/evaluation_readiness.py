"""Instantánea interna autorizada de sesión completa; sin publicación ni escrituras."""
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G, GrupoEstudianteORM as M
from app.modules.cases.infrastructure.models import CasoModel as Caso, VersionCasoModel as V, RubricaModel
from app.modules.participation.application.evaluation_readiness import (
    IntentoParaRevision, ConvocatoriaParaRevision, PreparacionEvaluacionSesion,
)
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I, PasoSimulacionModel
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.infrastructure.queries import (
    LecturasParticipacionSQLAlchemy, TablasLecturaParticipacion, consultar_duracion_historica,
)
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.participation.infrastructure.result_repository import RepositorioResultadosTecnicosSQLAlchemy
from app.modules.participation.infrastructure.composition import _Alcance
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C, SesionProgramadaModel as S


class ConsultaPreparacionEvaluacionSQLAlchemy:
    def __init__(self, *, usuario, crear_sesion, fechas):
        self.usuario, self.crear_sesion, self.fechas = usuario, crear_sesion, fechas

    def consultar(self, *, id_sesion: UUID) -> PreparacionEvaluacionSesion:
        if not isinstance(id_sesion, UUID):
            raise AccesoDenegado()
        return self._lectura(lambda s: self._consultar(s, id_sesion))

    def _lectura(self, operacion):
        """Una única instantánea propia, sin efectos de escritura."""
        try:
            s = self.crear_sesion()
            if s.in_transaction():
                # No cerrar ni revertir una transacción que no es nuestra.
                raise IntegracionPendiente()
            with s:
                if s.get_bind().dialect.name != 'postgresql':
                    raise IntegracionPendiente()
                # Antes de la primera lectura. Una nueva Session por operación;
                # cerrar revierte la transacción, nunca confirma ni hace flush.
                s.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
                s.execute(text('SET TRANSACTION READ ONLY'))
                with s.no_autoflush:
                    return operacion(s)
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def _consultar(self, s, id_sesion):
        actual = RepositorioUsuariosSQLAlchemy(s).obtener(self.usuario.id_usuario)
        if actual is None or not actual.activo or Rol.DOCENTE not in actual.roles:
            raise AccesoDenegado()
        resolver = ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s))
        docente = resolver.resolver(id_usuario=actual.id_usuario, sistema=SistemaAcademico.SCHEDULING)
        creador = resolver.resolver(id_usuario=actual.id_usuario, sistema=SistemaAcademico.CASES)
        sesion = s.get(S, id_sesion)
        if sesion is None or sesion.docente_id != docente:
            raise AccesoDenegado()
        version = s.get(V, sesion.version_caso_id)
        caso = s.get(Caso, version.caso_id) if version is not None else None
        if caso is None or caso.docente_creador_id != creador:
            raise AccesoDenegado()
        rubrica = s.scalars(select(RubricaModel).where(RubricaModel.version_caso_id == version.id)).one_or_none()
        if (rubrica is None or not rubrica.version_regla.strip()
                or sesion.estado not in {'SIN_INICIAR', 'EN_CURSO', 'FINALIZADO'}):
            raise IntegracionPendiente()
        asignaciones = s.scalars(select(A).where(A.sesion_programada_id == id_sesion)).all()
        if not asignaciones:
            raise IntegracionPendiente()
        for a in asignaciones:
            grupo = s.get(G, a.id_grupo)
            if (grupo is None or grupo.id_profesor != id_entero(actual.id_usuario)
                    or a.id_caso != caso.id_caso or a.version_caso_id != version.id):
                raise IntegracionPendiente()
        convocatorias = s.scalars(select(C).where(C.sesion_id == id_sesion).order_by(C.id)).all()
        participaciones = s.scalars(select(P).where(P.id_asignacion.in_(a.id_asignacion for a in asignaciones))).all()
        por_convocatoria = {p.convocatoria_id: p for p in participaciones}
        if (len(por_convocatoria) != len(participaciones)
                or not set(por_convocatoria).issubset({c.id for c in convocatorias})):
            raise IntegracionPendiente()
        filas = []
        for c in convocatorias:
            propietario = s.scalar(select(IA.id_usuario).where(
                IA.sistema == SistemaAcademico.SCHEDULING.value, IA.id_academico == c.estudiante_id))
            if propietario is None:
                raise IntegracionPendiente()
            if resolver.resolver(id_usuario=str(propietario), sistema=SistemaAcademico.SCHEDULING) != c.estudiante_id:
                raise IntegracionPendiente()
            if c.estado not in {'ACTIVA', 'RETIRADA'}:
                raise IntegracionPendiente()
            matriculas = s.scalars(select(M).where(M.id_estudiante == propietario,
                M.id_grupo.in_(a.id_grupo for a in asignaciones))).all()
            pendientes = []
            if c.estado == 'RETIRADA':
                pendientes.append('TRATAMIENTO_RETIRO_PENDIENTE')
            p = por_convocatoria.get(c.id)
            if p is None:
                if len(matriculas) != 1:
                    pendientes.append('MATRICULA_NO_INEQUIVOCA')
            else:
                m = next((m for m in matriculas if m.id_grupo_estudiante == p.id_grupo_estudiante), None)
                a = next(a for a in asignaciones if a.id_asignacion == p.id_asignacion)
                if m is None or m.id_grupo != a.id_grupo:
                    raise IntegracionPendiente()
            intentos = s.scalars(select(I).where(I.id_participacion == p.id_participacion)
                .order_by(I.numero_intento, I.id_intento)).all() if p is not None else []
            if not intentos:
                pendientes.append('SIN_INTENTOS_REQUIERE_REVISION_DOCENTE')
            if len(intentos) > 1:
                pendientes.append('CONSOLIDACION_REPETICIONES_PENDIENTE')
            detalle = []
            for i in intentos:
                if i.estado not in {'EN_CURSO', 'FINALIZADO', 'VENCIDO'}:
                    raise IntegracionPendiente()
                rid = s.scalar(select(R.id_resultado).where(R.id_intento == i.id_intento))
                if i.estado == 'EN_CURSO':
                    if rid is not None:
                        raise IntegracionPendiente()
                    pendientes.append('INTENTO_SIN_CIERRE_PERSISTIDO')
                elif rid is None:
                    pendientes.append('RESULTADO_NO_CALCULADO')
                else:
                    # Reutiliza reproducción, huellas y FK históricas; no basta
                    # encontrar una cabecera para declarar válido un resultado.
                    tecnico = self._resultado_tecnico(s, i.id_intento)
                    if tecnico.id_resultado != rid or tecnico.datos.id_participacion != p.id_participacion:
                        raise IntegracionPendiente()
                    pendientes.append('RESULTADO_TECNICO_NO_OFICIAL' if tecnico.ambito=='TECNICO' else 'RESULTADO_LABORATORIO_NO_OFICIAL')
                detalle.append(IntentoParaRevision(i.id_intento, i.numero_intento, i.estado, rid))
            filas.append(ConvocatoriaParaRevision(c.id, propietario, c.estado,
                p.id_participacion if p is not None else None, tuple(detalle), tuple(dict.fromkeys(pendientes))))
        pendientes = ['MAPEO_Y_AGREGACION_ACADEMICA_PENDIENTES',
                      'CONSOLIDACION_Y_PUBLICACION_OFICIAL_NO_CONFIGURADAS',
                      'CORTE_PADRON_ACADEMICO_PENDIENTE']
        if sesion.estado != 'FINALIZADO':
            pendientes.append('SESION_NO_FINALIZADA')
        if not convocatorias:
            pendientes.append('SIN_CONVOCATORIAS')
        return PreparacionEvaluacionSesion(id_sesion, version.id, rubrica.id,
            rubrica.version_regla, sesion.estado, tuple(filas), tuple(pendientes))

    def _resultado_tecnico(self, s, id_intento):
        alcance = _Alcance(lambda: s, self.usuario, id_intento, self.fechas)
        lector = LecturasParticipacionSQLAlchemy(s,
            TablasLecturaParticipacion(P.__table__, I.__table__, PasoSimulacionModel.__table__),
            fechas=self.fechas, estados={e.value: e for e in EstadoIntento},
            duracion_historica=consultar_duracion_historica)
        return RepositorioResultadosTecnicosSQLAlchemy(s, alcance=alcance,
            fechas=self.fechas, lecturas=lector).obtener_tecnico(id_intento=id_intento)
