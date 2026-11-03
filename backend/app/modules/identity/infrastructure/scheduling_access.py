"""Adaptador del monolito: solo lecturas Scheduling, sin HTTP circular ni ingreso.

Identity conserva cuentas/JWT; Scheduling conserva convocatoria/código y horario.
Autenticar la pareja correo/código no autoriza empezar una sesión académica.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.application.ports import ConsultaCuentaPorCorreo
from app.modules.identity.domain.entities import AccesoConvocatoria, Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.scheduling.domain.access_codes import hash_codigo, coincide_codigo
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel


class ValidadorConvocatoriaScheduling:
    def __init__(self, sesion: Session, usuarios: ConsultaCuentaPorCorreo, resolver: ResolverIdentidadAcademica) -> None:
        self.sesion = sesion
        self.usuarios = usuarios
        self.resolver = resolver

    def _consulta(self):
        return select(ConvocatoriaModel, SesionProgramadaModel.estado).outerjoin(
            SesionProgramadaModel, ConvocatoriaModel.sesion_id == SesionProgramadaModel.id,
        )

    @staticmethod
    def _vigente(convocatoria: ConvocatoriaModel, estado_sesion: str | None) -> bool:
        if estado_sesion not in {"SIN_INICIAR", "EN_CURSO", "FINALIZADO"}:
            raise IntegracionPendiente()
        if convocatoria.estado not in {"ACTIVA", "RETIRADA"}:
            raise IntegracionPendiente()
        # Una sesión finalizada impide empezar, no elimina la identidad para avisos.
        return convocatoria.estado == "ACTIVA"

    def validar(self, correo: str, codigo: str) -> AccesoConvocatoria | None:
        usuario = self.usuarios.obtener_por_correo(correo)
        if usuario is None or not usuario.activo or Rol.ESTUDIANTE not in usuario.roles:
            return None
        try:
            estudiante = self.resolver.resolver(id_usuario=usuario.id_usuario, sistema=SistemaAcademico.SCHEDULING)
        except AccesoDenegado:
            return None  # El login público no enumera cuentas/vínculos inexistentes.
        try:
            with self.sesion.no_autoflush:
                filas = self.sesion.execute(self._consulta().where(
                    ConvocatoriaModel.estudiante_id == estudiante,
                    ConvocatoriaModel.codigo_hash == hash_codigo(codigo),
                )).all()
            if len(filas) > 1:
                raise IntegracionPendiente()
            if not filas:
                return None
            convocatoria, estado = filas[0]
            if (convocatoria.estudiante_id != estudiante or not self._vigente(convocatoria, estado)
                    or not coincide_codigo(codigo, convocatoria.codigo_hash)):
                return None
            return AccesoConvocatoria(usuario.id_usuario, str(convocatoria.id))
        except SQLAlchemyError:
            raise IntegracionPendiente() from None

    def validar_contexto(self, *, id_usuario: str, contexto: str | None, solicitada: UUID) -> None:
        """Alcance vigente de operación académica; no aplica ventana temporal."""
        try:
            identificador = UUID(contexto) if contexto is not None else None
        except (ValueError, TypeError, AttributeError):
            raise AccesoDenegado() from None
        if identificador is None or str(identificador) != contexto or identificador != solicitada:
            raise AccesoDenegado()
        estudiante = self.resolver.resolver(id_usuario=id_usuario, sistema=SistemaAcademico.SCHEDULING)
        try:
            with self.sesion.no_autoflush:
                fila = self.sesion.execute(self._consulta().where(ConvocatoriaModel.id == identificador)).one_or_none()
            if fila is None or fila[0].estudiante_id != estudiante or not self._vigente(*fila):
                raise AccesoDenegado()
        except SQLAlchemyError:
            raise IntegracionPendiente() from None
