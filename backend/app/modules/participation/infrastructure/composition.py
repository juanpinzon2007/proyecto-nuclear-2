"""Composición interna 8B por operación. Nunca instalada en la dependencia HTTP.

Una Facade compuesta aquí consume una única UoW; crear otra por cada operación.
No hay Session global, políticas sintéticas ni implementación alternativa de JWT.
"""
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.application.simulation_structure import consultar_estructura_version, validar_opcion_version
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.application.integration_ports import RecorridoVersionCases, AutorizacionEdicionIntento, CondicionesEdicionIntento
from app.modules.participation.domain.clock import Reloj
from app.modules.participation.infrastructure.attempt_state import ConsultaEstadoIntentoSQLAlchemy
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import IntentoModel, ParticipacionModel
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy
from app.modules.participation.infrastructure.cases_route import RecorridoCasesSQLAlchemy
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from app.modules.scheduling.application.attempt_operations import (
    consultar_operacion_sesion, autorizar_respuesta_sesion, OperacionSesionDenegada, CondicionesOperacionNoDisponibles,
)


class _Alcance:
    def __init__(self,sesion,usuario,id_intento,fechas):
        self.sesion=sesion
        self.usuario=usuario
        self.id_intento=id_intento
        self.fechas=fechas

    def datos(self):
        i,p,a=IntentoModel,ParticipacionModel,AsignacionCasoModel
        fila=self.sesion().execute(select(i.id_participacion,p.id_grupo_estudiante,p.convocatoria_id,a.id_asignacion,a.id_caso,
            a.sesion_programada_id,a.version_caso_id).select_from(i).join(p,p.id_participacion==i.id_participacion)
            .join(a,a.id_asignacion==p.id_asignacion).where(i.id_intento==self.id_intento)).one_or_none()
        if fila is None:
            raise AccesoDenegado("Intento no disponible.")
        return fila


class IdentityIntentoSQLAlchemy:
    def __init__(self,alcance):
        self.a=alcance

    def autorizar_acceso(self,*,id_estudiante,id_participacion):
        if type(id_estudiante) is not int or id_estudiante!=id_entero(self.a.usuario.id_usuario) or self.a.datos().id_participacion!=id_participacion:
            raise AccesoDenegado("Intento no disponible.")
        s=self.a.sesion(); p,m,c,u,r=ParticipacionModel,GrupoEstudianteORM,ConvocatoriaModel,UsuarioORM,RolORM
        fila=s.execute(select(u.id_usuario,u.id_rol).select_from(p).join(m,m.id_grupo_estudiante==p.id_grupo_estudiante)
            .join(c,c.id==p.convocatoria_id).join(u,u.id_usuario==m.id_estudiante).join(r,r.id_rol==u.id_rol)
            .where(p.id_participacion==id_participacion,u.id_usuario==id_estudiante)
            .with_for_update(of=[u,c,m])).one_or_none()
        if fila is None:
            raise AccesoDenegado("Intento no disponible.")
        s.execute(select(r.id_rol).where(r.id_rol==fila.id_rol).with_for_update(read=True)).one()
        ConsultaEstadoIntentoSQLAlchemy(s,fechas=self.a.fechas).consultar(usuario=self.a.usuario,id_intento=self.a.id_intento)

    def autorizar_inicio(self,**_):
        raise ReglaPendiente("Inicio no habilitado: faltan políticas y composición de provisión.")


class AutorizacionRespuestaScheduling:
    """Adaptación sin estado de la regla confirmada de Scheduling, no de RF-22."""
    def autorizar(self, condiciones: CondicionesEdicionIntento) -> None:
        try:
            autorizar_respuesta_sesion(estado=condiciones.estado_sesion,
                inicio=condiciones.inicio_sesion, fin=condiciones.fin_sesion,
                ahora=condiciones.ahora, operacion=condiciones.operacion)
        except OperacionSesionDenegada:
            raise AccesoDenegado("La sesión no permite responder en este instante.") from None
        except CondicionesOperacionNoDisponibles:
            raise ReglaPendiente("Las fechas o el estado de Scheduling no son verificables.") from None


_AUTORIZACION_RESPUESTA = AutorizacionRespuestaScheduling()


class SchedulingIntentoSQLAlchemy:
    def __init__(self,alcance,autorizacion,reloj):
        self.a,self.autorizacion,self.reloj=alcance,autorizacion,reloj
        self._verificar_registro=None
        self._transaccion_registro=None

    def obtener_id_caso(self,*,id_asignacion):
        fila=self.a.datos()
        if fila.id_asignacion!=id_asignacion:
            raise AccesoDenegado("Asignación no disponible.")
        return fila.id_caso

    def validar_edicion(self,*,id_asignacion,id_grupo_estudiante,operacion="RESPONDER"):
        self._verificar_registro=None
        self._transaccion_registro=None
        fila=self.a.datos()
        if (fila.id_asignacion,fila.id_grupo_estudiante)!=(id_asignacion,id_grupo_estudiante):
            raise AccesoDenegado("Asignación no disponible.")
        s=self.a.sesion()
        if s.scalar(select(GrupoEstudianteORM.activo).where(GrupoEstudianteORM.id_grupo_estudiante==id_grupo_estudiante)) is not True:
            raise AccesoDenegado("Matrícula no habilitada.")
        estudiante=ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(s)).resolver(
            id_usuario=self.a.usuario.id_usuario,sistema=SistemaAcademico.SCHEDULING)
        try:
            datos=consultar_operacion_sesion(s,sesion_id=fila.sesion_programada_id,convocatoria_id=fila.convocatoria_id,
                estudiante_id=estudiante,version_caso_id=fila.version_caso_id,operacion=operacion)
        except OperacionSesionDenegada:
            raise AccesoDenegado("Operación de sesión no autorizada.") from None
        except CondicionesOperacionNoDisponibles:
            raise ReglaPendiente("Las condiciones de Scheduling no están disponibles.") from None
        # RF-25: una sesión finalizada no permite seguir participando. Esta
        # prohibición no puede relajarse mediante una política de edición.
        if datos.estado == "FINALIZADO":
            raise AccesoDenegado("La sesión está finalizada.")
        if self.autorizacion is None:
            raise ReglaPendiente("Falta autorización de Scheduling para editar el intento existente.")
        def verificar(ahora):
            resultado=self.autorizacion.autorizar(CondicionesEdicionIntento(id_asignacion,id_grupo_estudiante,
                datos.sesion_id,datos.estado,datos.inicio,datos.fin,ahora,datos.operacion))
            if resultado is not None:
                raise ReglaPendiente("Contrato de autorización de edición inválido.")
        verificar(self.reloj.ahora())
        self._verificar_registro=verificar
        self._transaccion_registro=s.get_transaction()

    def validar_instante_registro(self,*,instante):
        s=self.a.sesion()
        if (self._verificar_registro is None or self._transaccion_registro is None
                or not s.in_transaction() or self._transaccion_registro is not s.get_transaction()):
            raise ReglaPendiente("La respuesta exige autorización en esta misma transacción.")
        self._verificar_registro(instante)

    def obtener_condiciones(self,**_):
        raise ReglaPendiente("Inicio productivo no habilitado.")

    def autorizar_nuevo_intento(self,**_):
        raise ReglaPendiente("No existe una política de nuevos intentos configurada.")


class CasesIntentoSQLAlchemy:
    def __init__(self,alcance,recorrido:RecorridoVersionCases|None):
        self.a=alcance
        self.recorrido=recorrido if recorrido is not None else RecorridoCasesSQLAlchemy(alcance.sesion)

    def validar_opcion(self,*,id_caso,id_decision,id_opcion):
        fila=self.a.datos()
        if fila.id_caso!=id_caso or not isinstance(id_decision,UUID) or not isinstance(id_opcion,UUID):
            raise AccesoDenegado("Selección no disponible.")
        try:
            validar_opcion_version(self.a.sesion(),version_id=fila.version_caso_id,pregunta_id=id_decision,opcion_id=id_opcion)
        except CasoNoEncontradoError:
            raise AccesoDenegado("Selección no disponible.") from None

    def obtener_recorrido(self,*,id_caso,selecciones):
        fila=self.a.datos()
        if fila.id_caso!=id_caso:
            raise AccesoDenegado("Caso no disponible.")
        for seleccion in selecciones:
            self.validar_opcion(id_caso=id_caso,id_decision=seleccion.id_decision,id_opcion=seleccion.id_opcion)
        try:
            estructura=consultar_estructura_version(self.a.sesion(),version_id=fila.version_caso_id)
        except CasoNoEncontradoError:
            raise ReglaPendiente("La estructura de la edición no está disponible.") from None
        if self.recorrido is None:
            return RecorridoAplicable((),False,disponible=False)
        ruta=self.recorrido.obtener(version_id=fila.version_caso_id,selecciones=selecciones)
        if not isinstance(ruta,RecorridoAplicable):
            raise ReglaPendiente("Contrato de recorrido inválido.")
        identificadores={p.id for p in estructura.preguntas}
        for decision in ruta.decisiones:
            if not isinstance(decision,UUID) or decision not in identificadores:
                raise ReglaPendiente("El recorrido contiene una pregunta ajena.")
        return ruta

    def validar_cambio_conservando_pasos(self,*,id_caso,selecciones,propuesta):
        self.validar_opcion(id_caso=id_caso,id_decision=propuesta.id_decision,id_opcion=propuesta.id_opcion)
        if self.recorrido is None:
            raise ReglaPendiente("Cases debe autorizar el punto del recorrido y la conservación de las respuestas.")
        ruta=self.obtener_recorrido(id_caso=id_caso,selecciones=selecciones)
        if not ruta.disponible:
            raise ReglaPendiente("Cases no acredita el punto del recorrido y la conservación de las respuestas.")
        if propuesta.id_decision not in ruta.decisiones:
            raise AccesoDenegado("La pregunta está fuera del recorrido autorizado.")
        if any(s.id_decision not in ruta.decisiones for s in selecciones):
            raise ReglaPendiente("El recorrido excluye respuestas conservadas.")
        resultado=self.recorrido.validar_cambio(version_id=self.a.datos().version_caso_id,selecciones=selecciones,propuesta=propuesta)
        if resultado is not None:
            raise ReglaPendiente("Contrato de autorización de cambio inválido.")
        # Verificar también el efecto de la opción propuesta. Validar solo la
        # ruta previa permite conservar respuestas que la nueva rama excluye.
        # No se borran ni invalidan pasos: falta una política para hacerlo.
        propuestas=tuple(propuesta if s.id_decision==propuesta.id_decision else s for s in selecciones)
        if not any(s.id_decision==propuesta.id_decision for s in selecciones):
            propuestas=(*propuestas,propuesta)
        posterior=self.obtener_recorrido(id_caso=id_caso,selecciones=propuestas)
        if not posterior.disponible:
            raise ReglaPendiente("El recorrido posterior al cambio no está disponible.")
        if any(s.id_decision not in posterior.decisiones for s in propuestas):
            raise ReglaPendiente("El cambio de recorrido excluye respuestas que deben conservarse.")


def crear_facade_8b(*,usuario:ContextoAcceso,id_intento:int,
                   reloj:Reloj,fechas:FechasPersistencia,crear_sesion:Callable[[],Session],
                   autorizacion_edicion:AutorizacionEdicionIntento|None=_AUTORIZACION_RESPUESTA,
                   recorrido:RecorridoVersionCases|None=None)->ParticipacionFacade:
    """Una sola operación, adaptadores SQL reales sobre la misma UoW.

    Scheduling autoriza por defecto RESPONDER en la ventana confirmada, usando
    datos bloqueados. None explícito conserva el rechazo por dependencia ausente.
    No modifica obtener_facade HTTP ni obtiene políticas/Session desde .env.
    """
    trabajo=UnidadTrabajoSQLAlchemy(lambda s:RepositorioParticipacionSQLAlchemy(s,fechas=fechas),crear_sesion=crear_sesion)
    alcance=_Alcance(lambda:trabajo.sesion,usuario,id_intento,fechas)
    return ParticipacionFacade(fabrica=lambda:trabajo,identity=IdentityIntentoSQLAlchemy(alcance),
        cases=CasesIntentoSQLAlchemy(alcance,recorrido),scheduling=SchedulingIntentoSQLAlchemy(alcance,autorizacion_edicion,reloj),reloj=reloj)
