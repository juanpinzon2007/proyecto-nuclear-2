"""RF-15: lecturas acotadas; RF-26 reutiliza el escritor individual existente.

No consolida intentos, clasifica ausencias ni lee resultados LAB como notas.
Cada operación revalida el ámbito dentro de su propia transacción.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.modules.identity.domain.entities import (
    Rol, ResumenCaso, ResumenParticipacion, DetalleParticipacion,
    IntentoSeguimiento, RespuestaSeguimiento,
)
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M, GrupoAcademicoORM as G
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM as F
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I, PasoSimulacionModel as Paso
from app.modules.participation.infrastructure.individual_feedback import AmbitoFeedbackIndividual
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as Conv
from app.modules.cases.infrastructure.models import CasoModel as C, VersionCasoModel as V
from app.modules.cases.application.simulation_structure import validar_opcion_version
from app.modules.cases.application.answer_feedback import consultar_explicaciones_seleccionadas
from app.modules.cases.domain.exceptions import ErrorDominioCaso


class ConsultaSeguimientoSQLAlchemy:
    def __init__(self, *, usuario, crear_sesion):
        self.usuario, self.crear_sesion = usuario, crear_sesion

    def _operar(self, consulta):
        try:
            with self.crear_sesion() as s:
                with s.begin():
                    return consulta(s)
        except (SQLAlchemyError, ErrorDominioCaso):
            raise IntegracionPendiente() from None

    def _docente(self, s, identificador):
        if identificador != self.usuario.id_usuario:
            raise AccesoDenegado()
        actual=RepositorioUsuariosSQLAlchemy(s).obtener(identificador)
        if actual is None or not actual.activo or Rol.DOCENTE not in actual.roles:
            raise AccesoDenegado()
        resolver=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s))
        return (id_entero(identificador),
                resolver.resolver(id_usuario=identificador,sistema=SistemaAcademico.CASES),
                resolver.resolver(id_usuario=identificador,sistema=SistemaAcademico.SCHEDULING))

    def _filas(self, s, id_docente, id_caso=None):
        u,cases,scheduling=self._docente(s,id_docente)
        if id_caso is not None and s.scalar(select(C.id).where(C.id==id_caso,C.docente_creador_id==cases)) is None:
            raise AccesoDenegado()
        consulta=(select(P.id_participacion,M.id_estudiante,C.id.label('id_caso'),V.id.label('version_id'),
            V.nombre,P.convocatoria_id,S.id.label('sesion_id'),P.estado)
            .select_from(P).join(M,M.id_grupo_estudiante==P.id_grupo_estudiante)
            .join(A,(A.id_asignacion==P.id_asignacion)&(A.id_grupo==M.id_grupo))
            .join(G,G.id_grupo==A.id_grupo)
            .join(S,(S.id==A.sesion_programada_id)&(S.version_caso_id==A.version_caso_id))
            .join(Conv,(Conv.id==P.convocatoria_id)&(Conv.sesion_id==S.id))
            .join(V,V.id==A.version_caso_id).join(C,(C.id==V.caso_id)&(C.id_caso==A.id_caso))
            .where(G.id_profesor==u,C.docente_creador_id==cases,S.docente_id==scheduling)
            .order_by(C.id,V.numero,P.id_participacion))
        if id_caso is not None:consulta=consulta.where(C.id==id_caso)
        filas=s.execute(consulta).all()
        for f in filas:
            AmbitoFeedbackIndividual(s,self.usuario).autorizar(id_docente,str(f.id_participacion))
        return filas

    def puede_consultar_participacion(self, id_docente, id_participacion):
        def consultar(s):
            AmbitoFeedbackIndividual(s,self.usuario).autorizar(id_docente,id_participacion)
            return True
        return self._operar(consultar)

    def puede_consultar_sesion(self, id_docente, id_sesion):
        # RF-16 exige roster/consolidación oficial; no se abre por integrar RF-15.
        raise IntegracionPendiente()

    def listar_casos_realizados(self, id_docente):
        def consultar(s):
            casos={}
            for f in self._filas(s,id_docente):
                casos[(f.id_caso,f.version_id)]=ResumenCaso(str(f.id_caso),f.nombre,str(f.version_id))
            return tuple(casos.values())
        return self._operar(consultar)

    def listar_participaciones(self, id_docente, id_caso):
        try:caso=UUID(id_caso)
        except (ValueError,TypeError,AttributeError):raise ReglaIdentidadInvalida() from None
        return self._operar(lambda s:tuple(ResumenParticipacion(str(f.id_participacion),str(f.id_estudiante),
            str(f.id_caso),str(f.version_id),str(f.convocatoria_id),str(f.sesion_id),f.estado)
            for f in self._filas(s,id_docente,caso)))

    def consultar_participacion(self, id_docente, id_participacion):
        def consultar(s):
            AmbitoFeedbackIndividual(s,self.usuario).autorizar(id_docente,id_participacion)
            p=s.get(P,id_entero(id_participacion));a=s.get(A,p.id_asignacion)
            v=s.get(V,a.version_caso_id);m=s.get(M,p.id_grupo_estudiante)
            intentos=[];respuestas=[]
            for i in s.scalars(select(I).where(I.id_participacion==p.id_participacion).order_by(I.numero_intento,I.id_intento)):
                if i.estado not in ('EN_CURSO','FINALIZADO','VENCIDO'):raise IntegracionPendiente()
                pasos=s.scalars(select(Paso).where(Paso.id_intento==i.id_intento).order_by(Paso.numero_paso)).all()
                for paso in pasos:
                    validar_opcion_version(s,version_id=v.id,pregunta_id=paso.id_decision,opcion_id=paso.id_opcion)
                explicaciones={}
                if i.estado!='EN_CURSO':
                    explicaciones={(e.pregunta_id,e.opcion_id):e.justificacion for e in
                        consultar_explicaciones_seleccionadas(s,version_id=v.id,
                            selecciones=tuple((p.id_decision,p.id_opcion) for p in pasos))}
                respuestas.extend(RespuestaSeguimiento(str(p.id_decision),str(p.id_opcion),
                    explicaciones.get((p.id_decision,p.id_opcion)),str(i.id_intento),p.numero_paso,
                    p.reflexion_estudiante) for p in pasos)
                intentos.append(IntentoSeguimiento(str(i.id_intento),i.numero_intento,i.estado,i.inicio,i.fin,len(pasos)))
            feedback=s.scalar(select(F.texto).where(F.id_participacion==p.id_participacion))
            return DetalleParticipacion(str(p.id_participacion),str(m.id_estudiante),str(v.caso_id),
                tuple(respuestas),feedback,tuple(intentos),str(v.id),str(p.convocatoria_id),
                str(a.sesion_programada_id),p.estado)
        return self._operar(consultar)
