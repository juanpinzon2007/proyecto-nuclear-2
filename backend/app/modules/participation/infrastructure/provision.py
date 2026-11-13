"""Convocatoria → P → intento, reutilizando una única UoW PostgreSQL.

Opt-in del servidor: no registra rutas ni aporta estado/políticas por defecto.
"""
from types import SimpleNamespace
from uuid import UUID, uuid4
from datetime import timedelta
import json

from sqlalchemy import select, text

from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel, RubricaModel
from app.modules.identity.domain.errors import ReglaIdentidadInvalida
from app.modules.identity.domain.errors import AccesoDenegado as ConsentimientoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.consent import exigir_aceptacion
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente, ConflictoActualizacion
from app.modules.participation.application.provision_policy import CondicionesVinculacion, VinculacionParticipacion
from app.modules.participation.application.start_policy import CondicionesInicioIntento
from app.modules.participation.infrastructure.academic_context import ConsultaVinculacionSQLAlchemy
from app.modules.participation.infrastructure.cases_route import RecorridoCasesSQLAlchemy
from app.modules.participation.infrastructure.models import ParticipacionModel as P
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.start import preparar_inicio_en_uow
from app.modules.participation.infrastructure.start_policy_file import EvidenciaPoliticaInicio
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy
from app.modules.scheduling.domain.ingress_policy import fecha_utc, PoliticaTemporalNoDisponible
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel as C, SesionProgramadaModel as S, EventoAuditoriaModel,
)
from app.modules.scheduling.infrastructure.admission import AdmisionSQLAlchemy


class ServicioVinculacionSQLAlchemy:
    def __init__(self, *, usuario, reloj, fechas, crear_sesion,
                 politica_ingreso=None, politica_vinculacion=None, politica_inicio=None,
                 fuente_consentimiento=None, crear_fuente_consentimiento=None):
        self.usuario, self.reloj, self.fechas = usuario, reloj, fechas
        self.crear_sesion = crear_sesion
        self.ingreso, self.vinculacion, self.inicio = politica_ingreso, politica_vinculacion, politica_inicio
        self.fuente_consentimiento = fuente_consentimiento
        self.crear_fuente_consentimiento = crear_fuente_consentimiento

    def _unidad(self):
        return UnidadTrabajoSQLAlchemy(lambda s:RepositorioParticipacionSQLAlchemy(s,fechas=self.fechas),
            crear_sesion=self.crear_sesion)

    def _obtener_o_crear(self, trabajo, *, convocatoria_id, id_asignacion, codigo_acceso,
                        id_consentimiento=None, id_permiso_extra=None, iniciar=False):
        if self.usuario is None or not isinstance(convocatoria_id,UUID):
            raise AccesoDenegado("Vinculación no disponible.")
        try:
            cuenta = id_entero(self.usuario.id_usuario)
        except ReglaIdentidadInvalida:
            raise AccesoDenegado("Vinculación no disponible.") from None
        if type(id_asignacion) is not int or not 0 < id_asignacion <= 2147483647:
            raise AccesoDenegado("Vinculación no disponible.")
        if self.ingreso is None or self.vinculacion is None:
            raise ReglaPendiente("Falta política de ingreso y/o provisión de participación.")
        s, repo = trabajo.sesion, trabajo.repositorio
        if s.get_bind().dialect.name != "postgresql" or s.connection().get_isolation_level() != "READ COMMITTED":
            raise ReglaPendiente("La provisión exige una UoW PostgreSQL READ COMMITTED.")
        # Serializa también la ausencia de P. El hash solo es clave de lock,
        # nunca un identificador académico ni una conversión UUID/INTEGER.
        s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:clave,0))"),
            {"clave":"participation.convocatoria:"+str(convocatoria_id)})
        existente = repo.obtener_por_convocatoria(convocatoria_id)
        # Con P existente se conserva el orden P → cuenta del inicio anterior.
        u = s.execute(select(UsuarioORM).where(UsuarioORM.id_usuario==cuenta).with_for_update()).scalar_one_or_none()
        if u is None:
            raise AccesoDenegado("Vinculación no disponible.")
        s.execute(select(RolORM).where(RolORM.id_rol==u.id_rol).with_for_update(read=True)).all()
        s.execute(select(IdentidadAcademicaORM).where(IdentidadAcademicaORM.id_usuario==cuenta).with_for_update(read=True)).all()
        matriculas = s.execute(select(M).join(A,A.id_grupo==M.id_grupo).where(
            A.id_asignacion==id_asignacion,M.id_estudiante==cuenta).with_for_update(of=M)).scalars().all()
        if len(matriculas) != 1:
            raise AccesoDenegado("Matrícula no disponible.")
        convocatoria = s.execute(select(C).where(C.id==convocatoria_id).with_for_update()).scalar_one_or_none()
        if convocatoria is None:
            raise AccesoDenegado("Convocatoria no disponible.")
        s.execute(select(S).where(S.id==convocatoria.sesion_id).with_for_update()).scalar_one()
        asignacion = s.execute(select(A).where(A.id_asignacion==id_asignacion).with_for_update()).scalar_one()
        caso = s.execute(select(CasoModel).where(CasoModel.id_caso==asignacion.id_caso).with_for_update(read=True)).scalar_one()
        s.execute(select(VersionCasoModel).where(VersionCasoModel.id==asignacion.version_caso_id).with_for_update(read=True)).all()
        s.execute(select(RubricaModel).where(RubricaModel.version_caso_id==asignacion.version_caso_id).with_for_update(read=True)).all()
        try:
            instante = fecha_utc(self.reloj.ahora())
        except PoliticaTemporalNoDisponible:
            raise ReglaPendiente("El reloj del servidor no es verificable.") from None
        # Se acredita el contexto DESPUÉS de bloquear sus fuentes, en la misma
        # Session. El instante del registro es el que Scheduling autoriza.
        contexto = ConsultaVinculacionSQLAlchemy(s,politica=self.ingreso,
            admision=AdmisionSQLAlchemy(s,self.usuario,bloquear=True),
            reloj=SimpleNamespace(ahora=lambda:instante)).consultar(usuario=self.usuario,
                convocatoria_id=convocatoria_id,codigo_acceso=codigo_acceso,id_asignacion=id_asignacion)
        if contexto.ingreso.caso_id != caso.id:
            raise AccesoDenegado("Caso no disponible.")
        if existente and (existente.id_asignacion,existente.id_grupo_estudiante) != (
                contexto.id_asignacion,contexto.id_grupo_estudiante):
            raise ConflictoActualizacion("La convocatoria ya tiene otra vinculación.")
        # No se reutiliza otra P solo porque coincida asignación/matrícula:
        # podría pertenecer a una convocatoria distinta. Nunca se reasigna.
        otra = s.scalar(select(P.id_participacion).where(P.id_asignacion==contexto.id_asignacion,
            P.id_grupo_estudiante==contexto.id_grupo_estudiante))
        if otra is not None and (existente is None or otra != existente.id_participacion):
            raise ConflictoActualizacion("La matrícula ya tiene otra participación para esta asignación.")
        if existente is None:
            # Antes del primer INSERT/flush de P. La matrícula no es aceptación;
            # no escoger una versión desde HTTP ni desde una etiqueta histórica.
            try:
                aceptacion=exigir_aceptacion(s,id_estudiante=cuenta,id_asignacion=id_asignacion,
                    id_consentimiento=id_consentimiento,ahora=instante,fechas=self.fechas,
                    fuente=(self.crear_fuente_consentimiento(s) if self.crear_fuente_consentimiento is not None else self.fuente_consentimiento))
            except ConsentimientoDenegado:
                raise AccesoDenegado("Consentimiento no disponible para crear participación.") from None
            except IntegracionPendiente:
                raise ReglaPendiente("Falta fuente de consentimiento vigente inequívoca.") from None
            if id_permiso_extra is not None:
                # Un permiso adicional pertenece a una P existente por FK.
                raise AccesoDenegado("Permiso no disponible para una participación nueva.")
            if iniciar:
                # La MISMA política existente recibe datos de servidor antes de
                # tener una PK de P. None expresa aún no creada; no se inventa ID.
                ingreso=contexto.ingreso
                if not RecorridoCasesSQLAlchemy(lambda:s).obtener(
                        version_id=ingreso.version_caso_id,selecciones=()).disponible:
                    raise ReglaPendiente("El recorrido de la versión no es ejecutable.")
                if (type(asignacion.tiempo_maximo_min) is not int or asignacion.tiempo_maximo_min<=0
                        or timedelta(minutes=asignacion.tiempo_maximo_min)!=ingreso.tiempo_maximo):
                    raise ReglaPendiente("La duración asignada no es inequívoca.")
                condiciones=CondicionesInicioIntento(None,cuenta,convocatoria.sesion_id,
                    ingreso.version_caso_id,ingreso.rubrica_id,ingreso.version_regla,
                    asignacion.estado,self.fechas.desde_db(asignacion.apertura),
                    self.fechas.desde_db(asignacion.cierre),self.fechas.desde_db(asignacion.fecha_limite_ingreso),
                    instante,aceptacion.version_texto,self.fechas.desde_db(aceptacion.fecha_aceptacion),
                    1,asignacion.intentos_base,None,None,0)
                if self.inicio.autorizar(condiciones) is not None:
                    raise ReglaPendiente("Contrato de política de inicio inválido.")
        estado = self.vinculacion.autorizar(CondicionesVinculacion(contexto,instante,asignacion.estado,
            self.fechas.desde_db(asignacion.apertura),self.fechas.desde_db(asignacion.cierre),
            self.fechas.desde_db(asignacion.fecha_limite_ingreso),existente))
        if type(estado) is not str or not estado.strip() or len(estado)>20:
            raise ReglaPendiente("La política no aporta un estado inicial válido.")
        if existente is not None:
            if iniciar:
                id_historico=s.scalar(select(P.id_consentimiento).where(P.id_participacion==existente.id_participacion))
                if id_historico is not None and id_historico!=id_consentimiento:
                    raise AccesoDenegado("No sustituir consentimiento histórico al iniciar.")
                if id_historico is not None:
                    from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM
                    historico=s.get(ConsentimientoORM,id_historico)
                    if historico.id_version_documento is not None:
                        try:
                            exigir_aceptacion(s,id_estudiante=cuenta,id_asignacion=id_asignacion,
                                id_consentimiento=id_historico,ahora=instante,fechas=self.fechas,
                                fuente=(self.crear_fuente_consentimiento(s) if self.crear_fuente_consentimiento is not None else self.fuente_consentimiento))
                        except ConsentimientoDenegado:
                            raise AccesoDenegado("Consentimiento histórico no vigente o revocado.") from None
                        except IntegracionPendiente:
                            raise ReglaPendiente("Cambio de consentimiento: inicio histórico cerrado.") from None
            return VinculacionParticipacion(existente,False)
        nueva = repo.agregar_participacion(id_asignacion=contexto.id_asignacion,
            id_grupo_estudiante=contexto.id_grupo_estudiante,convocatoria_id=convocatoria_id,
            estado=estado,fecha_registro=instante,id_consentimiento=aceptacion.id_consentimiento)
        return VinculacionParticipacion(nueva,True)

    def obtener_o_crear(self, *, convocatoria_id, id_asignacion, codigo_acceso):
        with self._unidad() as trabajo:
            resultado = self._obtener_o_crear(trabajo,convocatoria_id=convocatoria_id,
                id_asignacion=id_asignacion,codigo_acceso=codigo_acceso)
            trabajo.commit()
            return resultado

    def iniciar_desde_convocatoria(self, *, convocatoria_id, id_asignacion,
                                  codigo_acceso, id_consentimiento, id_permiso_extra=None):
        if self.inicio is None:
            raise ReglaPendiente("Falta política de inicio.")
        with self._unidad() as trabajo:
            vinculo = self._obtener_o_crear(trabajo,convocatoria_id=convocatoria_id,
                id_asignacion=id_asignacion,codigo_acceso=codigo_acceso,
                id_consentimiento=id_consentimiento,id_permiso_extra=id_permiso_extra,iniciar=True)
            crear_fuente = self.crear_fuente_consentimiento
            if crear_fuente is None and self.fuente_consentimiento is not None:
                crear_fuente = lambda s:self.fuente_consentimiento
            resultado = preparar_inicio_en_uow(trabajo=trabajo,usuario=self.usuario,
                id_participacion=vinculo.participacion.id_participacion,reloj=self.reloj,fechas=self.fechas,
                codigo_acceso=codigo_acceso,politica_ingreso=self.ingreso,politica_inicio=self.inicio,
                id_consentimiento=id_consentimiento,id_permiso_extra=id_permiso_extra,
                crear_fuente_consentimiento=crear_fuente)
            evidencia = getattr(self.inicio, "evidencia", None)
            if evidencia is not None:
                if not callable(evidencia):
                    raise ReglaPendiente("La evidencia de política de inicio es inválida.")
                try:
                    descriptor = evidencia()
                except Exception:
                    raise ReglaPendiente("La evidencia de política de inicio no es verificable.") from None
                if not isinstance(descriptor, EvidenciaPoliticaInicio):
                    raise ReglaPendiente("La evidencia de política de inicio es incompleta.")
                convocatoria = trabajo.sesion.get(C, convocatoria_id)
                datos = descriptor.model_dump() | dict(id_intento=resultado.id_intento,
                    id_participacion=resultado.id_participacion)
                trabajo.sesion.add(EventoAuditoriaModel(id=uuid4(),sesion_id=convocatoria.sesion_id,
                    tipo="INICIO_INTENTO_POLITICA",origen="SISTEMA",creado_en=resultado.inicio,
                    descripcion=json.dumps(datos,sort_keys=True,ensure_ascii=False)))
            trabajo.commit()
            return resultado
