"""RF-25: conecta Proxy/Servicio existentes con permiso nativo, sin conceder un inicio."""
from uuid import UUID
from dataclasses import replace
from sqlalchemy import select,func
from sqlalchemy.exc import SQLAlchemyError
from app.modules.identity.domain.entities import CondicionesRepeticion
from app.modules.identity.domain.errors import AccesoDenegado,ConflictoIdentidad,IntegracionPendiente,ReglaIdentidadInvalida
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy,id_entero
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM as E
from app.modules.identity.infrastructure.academic_repositories import RepositorioPermisosExtraSQLAlchemy,NuevoPermisoIntentoExtra
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy
from app.modules.identity.application.services import ServicioExcepciones
from app.modules.participation.infrastructure.individual_feedback import AmbitoFeedbackIndividual
from app.modules.participation.infrastructure.models import ParticipacionModel as P,IntentoModel as I
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S


class RepeticionSQL:
    def __init__(self,s,fechas):self.s,self.fechas,self.pid=s,fechas,None
    def condiciones_repeticion(self,id_docente,id_sesion,id_estudiante):
        try:sid=UUID(id_sesion);alumno=id_entero(id_estudiante)
        except (ValueError,TypeError):raise ReglaIdentidadInvalida() from None
        pids=self.s.scalars(select(P.id_participacion).join(M,M.id_grupo_estudiante==P.id_grupo_estudiante)
            .join(A,A.id_asignacion==P.id_asignacion).where(A.sesion_programada_id==sid,M.id_estudiante==alumno)).all()
        if len(pids)>1:raise IntegracionPendiente()
        pid=pids[0] if pids else None
        if pid is None:raise ConflictoIdentidad()
        actual=RepositorioUsuariosSQLAlchemy(self.s).obtener(id_docente)
        if actual is None:raise AccesoDenegado()
        AmbitoFeedbackIndividual(self.s,actual).autorizar(id_docente,str(pid))
        estados=self.s.scalars(select(I.estado).where(I.id_participacion==pid).order_by(I.id_intento).with_for_update()).all()
        sesion=self.s.get(S,sid)
        if not estados or any(e not in {'FINALIZADO','VENCIDO'} for e in estados) or sesion.estado!='EN_CURSO':
            raise ConflictoIdentidad()
        self.pid=pid
        return CondicionesRepeticion(True,True,False)
    def guardar(self,a):
        if self.pid is None:raise AccesoDenegado()
        # P bloqueada: solicitudes repetidas recuperan el único permiso pendiente.
        permisos=self.s.scalars(select(E).where(E.id_participacion==self.pid).order_by(E.id_permiso_extra)).all()
        pendientes=[p for p in permisos if self.s.scalar(select(func.count()).select_from(I).where(I.id_permiso_extra==p.id_permiso_extra))==0]
        if len(pendientes)>1:raise IntegracionPendiente()
        if pendientes:
            p=pendientes[0]
            if p.id_profesor!=id_entero(a.id_docente_autorizador) or p.cantidad_autorizada!=1:raise ConflictoIdentidad()
            return replace(a,id_permiso_extra=p.id_permiso_extra,fecha_autorizacion=self.fechas.desde_db(p.fecha_autorizacion))
        return RepositorioPermisosExtraSQLAlchemy(self.s).agregar(NuevoPermisoIntentoExtra(self.pid,id_entero(a.id_docente_autorizador),1,
            f'Autorización expresa RF-25 por API para participación {self.pid}; solo esta evaluación histórica.',
            self.fechas.hacia_db(a.fecha_autorizacion,sin_offset=True)))


class UnidadRepeticion(UnidadTrabajoIdentitySQLAlchemy):
    def commit(self):
        try:super().commit()
        except SQLAlchemyError as e:
            if getattr(e.orig,'sqlstate',None) in {'23505','40P01','40001'}:raise ConflictoIdentidad() from None
            raise IntegracionPendiente() from None
    def __exit__(self,tipo,error,traceback):
        super().__exit__(tipo,error,traceback)
        if isinstance(error,SQLAlchemyError):raise IntegracionPendiente() from None


def crear_servicio_repeticion(*,sesiones,fechas):
    def unidad():
        compartido={}
        def adapter(s):
            if 'a' not in compartido:compartido['a']=RepeticionSQL(s,fechas)
            return compartido['a']
        return UnidadRepeticion(usuarios=RepositorioUsuariosSQLAlchemy,academia=adapter,autorizaciones=adapter,sesiones=sesiones)
    return ServicioExcepciones(unidad)
