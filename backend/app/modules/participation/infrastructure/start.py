"""Inicio 8B sobre participación existente: una Facade, Session y transacción.

No provisiona participaciones, instala endpoints ni define RF-22. Las políticas
de ingreso y consentimiento/cupos son dependencias explícitas del servidor.
"""
from dataclasses import replace
from datetime import timedelta

from sqlalchemy import select, func

from app.modules.cases.application.published_version import consultar_version_publicada
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel, RubricaModel
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado as AccesoIdentity, IntegracionPendiente
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM, GrupoEstudianteORM, GrupoAcademicoORM
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente, RecursoNoDisponible
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.application.ports import CondicionesIntento
from app.modules.participation.application.services import ServicioInicio
from app.modules.participation.application.start_policy import CondicionesInicioIntento, PoliticaInicioIntento
from app.modules.participation.infrastructure.composition import _Alcance, CasesIntentoSQLAlchemy, SchedulingIntentoSQLAlchemy
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy
from app.modules.scheduling.application.validar_ingreso import validar_ingreso, ErrorIngreso
from app.modules.scheduling.domain.ingress_policy import PoliticaTemporalNoDisponible, fecha_utc
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C, SesionProgramadaModel as S


class _AlcanceInicio(_Alcance):
    def __init__(self, sesion, usuario, id_participacion, fechas):
        super().__init__(sesion, usuario, None, fechas)
        self.id_participacion = id_participacion

    def datos(self):
        fila = self.sesion().execute(select(P.id_participacion,P.id_grupo_estudiante,P.convocatoria_id,
            A.id_asignacion,A.id_caso,A.sesion_programada_id,A.version_caso_id)
            .join(A,A.id_asignacion==P.id_asignacion).where(P.id_participacion==self.id_participacion)).one_or_none()
        if fila is None:
            raise AccesoDenegado("Participación no disponible.")
        return fila


class IdentityInicioSQLAlchemy:
    def __init__(self, alcance):
        self.a = alcance

    def autorizar_acceso(self, *, id_estudiante, id_participacion):
        s, a = self.a.sesion(), self.a
        if (a.usuario is None or type(id_estudiante) is not int
                or str(id_estudiante) != a.usuario.id_usuario or id_participacion != a.id_participacion):
            raise AccesoDenegado("Participación no disponible.")
        # P ya está bloqueada por el repositorio, antes de contar sus intentos.
        u = s.execute(select(UsuarioORM).where(UsuarioORM.id_usuario==id_estudiante).with_for_update()).scalar_one_or_none()
        if u is None:
            raise AccesoDenegado("Participación no disponible.")
        s.execute(select(RolORM).where(RolORM.id_rol==u.id_rol).with_for_update(read=True)).all()
        actual = RepositorioUsuariosSQLAlchemy(s).obtener(str(id_estudiante))
        if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
            raise AccesoDenegado("Participación no disponible.")
        s.execute(select(IdentidadAcademicaORM).where(IdentidadAcademicaORM.id_usuario==id_estudiante).with_for_update(read=True)).all()
        fila = a.datos()
        m = s.execute(select(GrupoEstudianteORM).where(GrupoEstudianteORM.id_grupo_estudiante==fila.id_grupo_estudiante).with_for_update()).scalar_one()
        convocatoria = s.execute(select(C).where(C.id==fila.convocatoria_id).with_for_update()).scalar_one()
        sesion = s.execute(select(S).where(S.id==fila.sesion_programada_id).with_for_update()).scalar_one()
        asignacion = s.execute(select(A).where(A.id_asignacion==fila.id_asignacion).with_for_update()).scalar_one()
        if (not m.activo or m.id_estudiante != id_estudiante or m.id_grupo != asignacion.id_grupo
                or convocatoria.sesion_id != sesion.id or sesion.version_caso_id != asignacion.version_caso_id):
            raise AccesoDenegado("Vinculación no disponible.")
        try:
            usuarios = RepositorioUsuariosSQLAlchemy(s)
            resolver = ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s))
            ValidadorConvocatoriaScheduling(s,usuarios,resolver).validar_contexto(
                id_usuario=actual.id_usuario, contexto=a.usuario.id_convocatoria, solicitada=convocatoria.id)
        except AccesoIdentity:
            raise AccesoDenegado("Convocatoria no disponible.") from None
        except IntegracionPendiente:
            raise ReglaPendiente("La identidad académica no es verificable.") from None

    def autorizar_inicio(self, *, id_estudiante, id_participacion, id_grupo_estudiante,
                         id_consentimiento, id_permiso_extra):
        s = self.a.sesion()
        fila = self.a.datos()
        if (id_participacion,id_grupo_estudiante)!=(fila.id_participacion,fila.id_grupo_estudiante):
            raise AccesoDenegado("Participación no disponible.")
        consentimiento = s.execute(select(ConsentimientoORM).where(
            ConsentimientoORM.id_consentimiento==id_consentimiento).with_for_update(read=True)).scalar_one_or_none()
        if consentimiento is None or consentimiento.id_estudiante != id_estudiante or consentimiento.fecha_revocacion is not None:
            raise AccesoDenegado("Consentimiento no disponible o revocado.")
        permiso = None
        if id_permiso_extra is not None:
            permiso = s.execute(select(PermisoIntentoExtraORM).where(
                PermisoIntentoExtraORM.id_permiso_extra==id_permiso_extra).with_for_update(read=True)).scalar_one_or_none()
            if permiso is None or permiso.id_participacion != id_participacion:
                raise AccesoDenegado("Permiso no disponible.")
            propietario = s.scalar(select(GrupoAcademicoORM.id_profesor).join(A,A.id_grupo==GrupoAcademicoORM.id_grupo)
                .where(A.id_asignacion==fila.id_asignacion).with_for_update(read=True,of=GrupoAcademicoORM))
            profesor = s.execute(select(UsuarioORM).where(UsuarioORM.id_usuario==permiso.id_profesor)
                .with_for_update(read=True)).scalar_one_or_none()
            if (permiso.id_profesor != propietario or profesor is None or not profesor.activo
                    or permiso.cantidad_autorizada <= 0):
                raise AccesoDenegado("Permiso no disponible.")
            s.execute(select(RolORM).where(RolORM.id_rol==profesor.id_rol).with_for_update(read=True)).all()
            if Rol.DOCENTE not in RepositorioUsuariosSQLAlchemy(s).obtener(str(profesor.id_usuario)).roles:
                raise AccesoDenegado("Permiso no disponible.")
        # Solo datos del servidor; el proveedor decidirá aplicabilidad y cupos.
        self.consentimiento, self.permiso = consentimiento, permiso


class SchedulingInicioSQLAlchemy(SchedulingIntentoSQLAlchemy):
    def __init__(self, alcance, identity, reloj, politica_ingreso, politica_inicio, codigo):
        super().__init__(alcance, None, reloj)
        self.identity, self.ingreso, self.politica, self.codigo = identity, politica_ingreso, politica_inicio, codigo
        self._inicio = None

    def obtener_condiciones(self, *, id_asignacion, id_grupo_estudiante):
        fila, s = self.a.datos(), self.a.sesion()
        if (id_asignacion,id_grupo_estudiante)!=(fila.id_asignacion,fila.id_grupo_estudiante):
            raise AccesoDenegado("Asignación no disponible.")
        if self.ingreso is None or self.politica is None:
            raise ReglaPendiente("Falta política explícita de ingreso y/o consentimiento/cupos.")
        # Locks de versión/rúbrica preservan la edición exacta, no la última.
        caso = s.execute(select(CasoModel).where(CasoModel.id_caso==fila.id_caso).with_for_update(read=True)).scalar_one()
        s.execute(select(VersionCasoModel).where(VersionCasoModel.id==fila.version_caso_id,
            VersionCasoModel.caso_id==caso.id).with_for_update(read=True)).scalar_one()
        s.execute(select(RubricaModel).where(RubricaModel.version_caso_id==fila.version_caso_id).with_for_update(read=True)).scalar_one()
        try:
            version = consultar_version_publicada(s,version_id=fila.version_caso_id)
        except CasoNoEncontradoError:
            raise RecursoNoDisponible("La versión asignada no está publicada.") from None
        if version.caso_id != caso.id:
            raise AccesoDenegado("Versión no disponible.")
        ruta = CasesIntentoSQLAlchemy(self.a,None).obtener_recorrido(id_caso=fila.id_caso,selecciones=())
        if not ruta.disponible:
            raise ReglaPendiente("El recorrido de la versión no es ejecutable.")
        sesion = s.get(S,fila.sesion_programada_id)
        asignacion = s.get(A,id_asignacion)
        if (type(asignacion.tiempo_maximo_min) is not int or asignacion.tiempo_maximo_min <= 0
                or asignacion.tiempo_maximo_min != sesion.tiempo_maximo_minutos):
            raise ReglaPendiente("La duración de asignación y sesión no es inequívoca.")
        self.version, self.asignacion = version, asignacion
        return CondicionesIntento(fila.id_caso,timedelta(minutes=asignacion.tiempo_maximo_min))

    def autorizar_nuevo_intento(self, *, id_asignacion, id_grupo_estudiante, numero_intento, id_permiso_extra):
        fila, s = self.a.datos(), self.a.sesion()
        if (id_asignacion,id_grupo_estudiante)!=(fila.id_asignacion,fila.id_grupo_estudiante):
            raise AccesoDenegado("Asignación no disponible.")
        permiso = self.identity.permiso
        if id_permiso_extra != (permiso.id_permiso_extra if permiso else None):
            raise AccesoDenegado("Permiso no disponible.")
        usos = s.scalar(select(func.count()).select_from(I).where(I.id_permiso_extra==id_permiso_extra)) if permiso else 0
        if permiso and usos >= permiso.cantidad_autorizada:
            raise AccesoDenegado("El permiso ya fue consumido.")
        consent, asignacion, version = self.identity.consentimiento, self.asignacion, self.version
        self._inicio = CondicionesInicioIntento(fila.id_participacion,id_entero(self.a.usuario.id_usuario),
            fila.sesion_programada_id,version.version_id,version.rubrica_id,version.version_regla,
            asignacion.estado,self.a.fechas.desde_db(asignacion.apertura),self.a.fechas.desde_db(asignacion.cierre),
            self.a.fechas.desde_db(asignacion.fecha_limite_ingreso),self.reloj.ahora(),
            consent.version_texto,self.a.fechas.desde_db(consent.fecha_aceptacion),numero_intento,
            asignacion.intentos_base,id_permiso_extra,permiso.cantidad_autorizada if permiso else None,usos)
        self._transaccion_inicio = s.get_transaction()
        self.validar_instante_inicio(instante=self._inicio.ahora)

    def validar_instante_inicio(self, *, instante):
        s = self.a.sesion()
        if self._inicio is None or not s.in_transaction() or s.get_transaction() is not self._transaccion_inicio:
            raise ReglaPendiente("El inicio exige autorización en esta misma transacción.")
        fila = self.a.datos()
        convocatoria = s.get(C,fila.convocatoria_id)
        class Instante:
            def ahora(self): return instante
        try:
            validar_ingreso(s,convocatoria_id=convocatoria.id,estudiante_id=convocatoria.estudiante_id,
                codigo_acceso=self.codigo,politica=self.ingreso,reloj=Instante())
            condiciones = replace(self._inicio,ahora=fecha_utc(instante))
            if condiciones.aceptado_en > condiciones.ahora:
                raise AccesoDenegado("La aceptación es posterior al inicio.")
            if self.identity.permiso and self.a.fechas.desde_db(self.identity.permiso.fecha_autorizacion) > condiciones.ahora:
                raise AccesoDenegado("El permiso es posterior al inicio.")
            if self.politica.autorizar(condiciones) is not None:
                raise ReglaPendiente("Contrato de política de inicio inválido.")
        except ErrorIngreso:
            raise AccesoDenegado("Ingreso no autorizado.") from None
        except PoliticaTemporalNoDisponible:
            raise ReglaPendiente("La ventana de ingreso no está aprobada/configurada.") from None


def crear_facade_inicio_8b(*, usuario, id_participacion, reloj, fechas, crear_sesion,
                         codigo_acceso, politica_ingreso=None, politica_inicio: PoliticaInicioIntento | None=None):
    """Solo inicio sobre P existente; no cambia las dependencias HTTP por defecto.

    El servidor aporta políticas y código a validar. El código nunca concede
    identidad: se exige además contexto JWT, cuenta, matrícula y titularidad SQL.
    Una nueva Facade/UoW por solicitud; sin commit en los adaptadores.
    """
    trabajo = UnidadTrabajoSQLAlchemy(lambda s:RepositorioParticipacionSQLAlchemy(s,fechas=fechas),crear_sesion=crear_sesion)
    alcance = _AlcanceInicio(lambda:trabajo.sesion,usuario,id_participacion,fechas)
    identity = IdentityInicioSQLAlchemy(alcance)
    scheduling = SchedulingInicioSQLAlchemy(alcance,identity,reloj,politica_ingreso,politica_inicio,codigo_acceso)
    return ParticipacionFacade(fabrica=lambda:trabajo,identity=identity,scheduling=scheduling,
        cases=CasesIntentoSQLAlchemy(alcance,None),reloj=reloj)


def preparar_inicio_en_uow(*, trabajo, usuario, id_participacion, reloj, fechas,
                           codigo_acceso, politica_ingreso, politica_inicio,
                           id_consentimiento, id_permiso_extra=None):
    """Conecta el mismo ServicioInicio y adaptadores a la UoW del coordinador.

    No abre Session, no entra otra UoW y no confirma la transacción prestada.
    """
    alcance = _AlcanceInicio(lambda:trabajo.sesion,usuario,id_participacion,fechas)
    identity = IdentityInicioSQLAlchemy(alcance)
    scheduling = SchedulingInicioSQLAlchemy(alcance,identity,reloj,politica_ingreso,politica_inicio,codigo_acceso)
    servicio = ServicioInicio(lambda:trabajo,identity,scheduling,reloj)
    return servicio.preparar(trabajo=trabajo,id_estudiante=id_entero(usuario.id_usuario),
        id_participacion=id_participacion,id_consentimiento=id_consentimiento,id_permiso_extra=id_permiso_extra)
