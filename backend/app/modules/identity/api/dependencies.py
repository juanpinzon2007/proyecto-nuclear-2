"""Composición cerrada por defecto, sin usuarios, códigos ni repositorios ficticios."""

from collections.abc import Callable, Generator
from contextlib import ExitStack
from dataclasses import replace
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import (
    ConsultaAmbitoAcademico, IServicioAdministracion, IServicioExcepciones,
    IServicioSeguimiento, RepositorioUsuarios, ValidadorConvocatoria,
)
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.proxy_excepciones import ProxyExcepciones
from app.modules.identity.application.proxy_seguimiento import ProxySeguimiento
from app.modules.identity.application.services import ServicioAdministracionUsuarios, ServicioSeguimiento
from app.modules.identity.api.errors import ERRORES
from app.modules.identity.domain.entities import ContextoAcceso, FeedbackDocente, Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente, NoAutenticado
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.identity.infrastructure.credentials import obtener_hasheador, CredencialesPersonalSQLAlchemy
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling


bearer = HTTPBearer(auto_error=False)


def construir_tokens() -> TokensJWT:
    configuracion = get_settings()
    try:
        return TokensJWT(
            configuracion.identity_jwt_secret.get_secret_value() if configuracion.identity_jwt_secret else "",
            configuracion.identity_jwt_issuer, configuracion.identity_jwt_audience,
            configuracion.identity_jwt_minutes,
        )
    except ValueError:
        raise IntegracionPendiente() from None


def construir_repositorio_usuarios(sesion: Session) -> RepositorioUsuarios:
    return RepositorioUsuariosSQLAlchemy(sesion)


def construir_validador_convocatoria(sesion: Session) -> ValidadorConvocatoriaScheduling:
    return ValidadorConvocatoriaScheduling(
        sesion, RepositorioUsuariosSQLAlchemy(sesion),
        ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(sesion)),
    )


def construir_consulta_ambito() -> ConsultaAmbitoAcademico:
    raise IntegracionPendiente()


def construir_seguimiento(*, usuario, crear_sesion) -> IServicioSeguimiento:
    from app.modules.identity.infrastructure.followup import ConsultaSeguimientoSQLAlchemy
    from app.modules.participation.infrastructure.individual_feedback import crear_servicio_feedback_individual
    return ServicioSeguimiento(ConsultaSeguimientoSQLAlchemy(usuario=usuario,crear_sesion=crear_sesion),
        None,crear_servicio_feedback_individual(usuario=usuario,crear_sesion=crear_sesion))


def construir_excepciones() -> IServicioExcepciones:
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    from app.modules.participation.infrastructure.codecs import FechasPersistencia
    from app.modules.identity.infrastructure.repetition import crear_servicio_repeticion
    zona=get_settings().participation_timestamp_zone
    try:
        if not zona:raise ValueError()
        fechas=FechasPersistencia(ZoneInfo(zona))
        return crear_servicio_repeticion(sesiones=obtener_fabrica_sesiones_seguimiento(),fechas=fechas)
    except (ValueError,ZoneInfoNotFoundError):raise IntegracionPendiente() from None


def construir_administracion() -> IServicioAdministracion:
    def unidad_trabajo() -> UnidadTrabajoIdentitySQLAlchemy:
        try:
            sesiones = get_session_factory()
        except (ValueError, SQLAlchemyError):
            raise IntegracionPendiente() from None
        return UnidadTrabajoIdentitySQLAlchemy(usuarios=construir_repositorio_usuarios, sesiones=sesiones)
    return ServicioAdministracionUsuarios(unidad_trabajo, obtener_hasheador().hash)


def obtener_fabrica_tokens() -> Callable[[], TokensJWT]:
    return construir_tokens


def obtener_fabrica_usuarios() -> Generator[Callable[[], RepositorioUsuarios], None, None]:
    # Apertura diferida: una solicitud sin Bearer sigue respondiendo 401 sin BD.
    with ExitStack() as recursos:
        def construir() -> RepositorioUsuarios:
            try:
                sesion = recursos.enter_context(get_session_factory()())
                return construir_repositorio_usuarios(sesion)
            except (ValueError, SQLAlchemyError):
                raise IntegracionPendiente() from None
        yield construir


def obtener_usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
    usuarios: Annotated[Callable[[], RepositorioUsuarios], Depends(obtener_fabrica_usuarios)],
) -> ContextoAcceso:
    if credenciales is None or credenciales.scheme.casefold() != "bearer":
        raise NoAutenticado()
    identidad = tokens().verificar(credenciales.credentials)
    usuario = usuarios().obtener(identidad.id_usuario)
    if usuario is None or not usuario.activo or usuario.id_usuario != identidad.id_usuario:
        raise NoAutenticado()
    # Roles/permisos actuales vienen del repositorio, nunca de claims del cliente.
    # La cuenta puede consultar su identidad/avisos sin una sesión académica.
    # Las operaciones de convocatoria exigen contexto y vigencia por separado.
    return replace(usuario, id_convocatoria=identidad.id_convocatoria)


def _obtener_usuario_con_rol(
    credenciales: HTTPAuthorizationCredentials | None,
    tokens: Callable[[], TokensJWT],
    usuarios: Callable[[], RepositorioUsuarios],
    rol: Rol,
) -> ContextoAcceso:
    """Frontera HTTP común, sin duplicar JWT ni exigir RutaIdentity al consumidor."""
    try:
        usuario = obtener_usuario_actual(credenciales, tokens, usuarios)
        ServicioAutorizacion(construir_consulta_ambito).exigir_rol(usuario, rol)
        return usuario
    except (NoAutenticado, AccesoDenegado, IntegracionPendiente) as error:
        estado, codigo, mensaje = ERRORES[type(error)]
        cabeceras = {"Cache-Control": "no-store"}
        if estado == 401:
            cabeceras["WWW-Authenticate"] = "Bearer"
        raise HTTPException(
            status_code=estado, detail={"codigo": codigo, "mensaje": mensaje}, headers=cabeceras,
        ) from None


def obtener_docente_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
    usuarios: Annotated[Callable[[], RepositorioUsuarios], Depends(obtener_fabrica_usuarios)],
) -> ContextoAcceso:
    """Usuario activo con rol DOCENTE del servidor; no resuelve UUID académico."""
    return _obtener_usuario_con_rol(credenciales, tokens, usuarios, Rol.DOCENTE)


def obtener_estudiante_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
    usuarios: Annotated[Callable[[], RepositorioUsuarios], Depends(obtener_fabrica_usuarios)],
) -> ContextoAcceso:
    """Exige ESTUDIANTE vigente; no convierte contexto académico en identidad."""
    return _obtener_usuario_con_rol(credenciales, tokens, usuarios, Rol.ESTUDIANTE)


def obtener_fabrica_sesiones_login() -> Callable[[], Session]:
    return lambda: get_session_factory()()


def obtener_dominios_login() -> tuple[str, ...]:
    return get_settings().identity_institutional_domains


def obtener_fabrica_autenticacion(
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
    dominios: Annotated[tuple[str, ...], Depends(obtener_dominios_login)],
) -> Generator[Callable[[], ServicioAutenticacion], None, None]:
    with ExitStack() as recursos:
        def construir() -> ServicioAutenticacion:
            if not dominios or not all(d.strip() for d in dominios):
                raise IntegracionPendiente()
            emisor = tokens()  # Validar configuración JWT antes de abrir Session.
            try:
                sesion = recursos.enter_context(sesiones())
            except (ValueError, SQLAlchemyError):
                raise IntegracionPendiente() from None
            return ServicioAutenticacion(RepositorioUsuariosSQLAlchemy(sesion),
                                         construir_validador_convocatoria(sesion), emisor, dominios)
        yield construir


def obtener_fabrica_autenticacion_personal(
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
) -> Generator[Callable[[], ServicioAutenticacion], None, None]:
    with ExitStack() as recursos:
        def construir() -> ServicioAutenticacion:
            emisor = tokens()
            try:
                sesion = recursos.enter_context(sesiones())
            except (ValueError, SQLAlchemyError):
                raise IntegracionPendiente() from None
            return ServicioAutenticacion(RepositorioUsuariosSQLAlchemy(sesion), None, emisor, (),
                credenciales_personal=CredencialesPersonalSQLAlchemy(sesion))
        yield construir


def obtener_fabrica_validador_convocatoria(
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
) -> Generator[Callable[[], ValidadorConvocatoriaScheduling], None, None]:
    with ExitStack() as recursos:
        def construir() -> ValidadorConvocatoriaScheduling:
            try:
                return construir_validador_convocatoria(recursos.enter_context(sesiones()))
            except (ValueError, SQLAlchemyError):
                raise IntegracionPendiente() from None
        yield construir


def obtener_fabrica_sesiones_seguimiento() -> Callable[[], Session]:
    def crear():
        try:
            return get_session_factory()()
        except (ValueError, SQLAlchemyError):
            raise IntegracionPendiente() from None
    return crear


def obtener_proxy_seguimiento(
    usuario: Annotated[ContextoAcceso, Depends(obtener_usuario_actual)],
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_seguimiento)],
) -> ProxySeguimiento:
    from app.modules.identity.infrastructure.followup import ConsultaSeguimientoSQLAlchemy
    return ProxySeguimiento(lambda:construir_seguimiento(usuario=usuario,crear_sesion=sesiones),
        ServicioAutorizacion(lambda:ConsultaSeguimientoSQLAlchemy(usuario=usuario,crear_sesion=sesiones)))


def obtener_proxy_excepciones() -> ProxyExcepciones:
    return ProxyExcepciones(construir_excepciones, ServicioAutorizacion(construir_consulta_ambito))


def obtener_consulta_feedback_estudiantil(
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_seguimiento)],
) -> Callable[..., FeedbackDocente]:
    """Compone la lectura individual existente; no concede acceso por la URL."""
    from functools import partial
    from app.modules.participation.infrastructure.individual_feedback import consultar_feedback_individual
    return partial(consultar_feedback_individual, usuario=usuario, crear_sesion=sesiones)


def obtener_proxy_administracion() -> ProxyAdministracionUsuarios:
    from app.modules.identity.infrastructure.teacher_directory import ConsultaDocentesSQLAlchemy
    return ProxyAdministracionUsuarios(construir_administracion, ServicioAutorizacion(construir_consulta_ambito),
        ConsultaDocentesSQLAlchemy(obtener_fabrica_sesiones_seguimiento()))
