"""Composición cerrada por defecto, sin usuarios, códigos ni repositorios ficticios."""

from collections.abc import Callable, Generator
from contextlib import ExitStack
from dataclasses import replace
from typing import Annotated

from fastapi import Depends
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
from app.modules.identity.application.services import ServicioAdministracionUsuarios
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import IntegracionPendiente, NoAutenticado
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy


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


def construir_validador_convocatoria() -> ValidadorConvocatoria:
    # Pendiente de contrato RF-20 de Scheduling; Identity no genera convocatorias.
    raise IntegracionPendiente()


def construir_consulta_ambito() -> ConsultaAmbitoAcademico:
    raise IntegracionPendiente()


def construir_seguimiento() -> IServicioSeguimiento:
    # Requiere lectura académica, LEFT JOIN público y UoW de Feedback_Docente.
    raise IntegracionPendiente()


def construir_excepciones() -> IServicioExcepciones:
    # Requiere UoW común y contrato transaccional con Cases/Participation/Scheduling.
    raise IntegracionPendiente()


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
    if Rol.ESTUDIANTE in usuario.roles and identidad.id_convocatoria is None:
        raise NoAutenticado()
    return replace(usuario, id_convocatoria=identidad.id_convocatoria)


def obtener_fabrica_autenticacion(
    usuarios: Annotated[Callable[[], RepositorioUsuarios], Depends(obtener_fabrica_usuarios)],
) -> Callable[[], ServicioAutenticacion]:
    def construir() -> ServicioAutenticacion:
        return ServicioAutenticacion(
            usuarios(), construir_validador_convocatoria(),
            construir_tokens(), get_settings().identity_institutional_domains,
        )
    return construir


def obtener_proxy_seguimiento() -> ProxySeguimiento:
    return ProxySeguimiento(construir_seguimiento, ServicioAutorizacion(construir_consulta_ambito))


def obtener_proxy_excepciones() -> ProxyExcepciones:
    return ProxyExcepciones(construir_excepciones, ServicioAutorizacion(construir_consulta_ambito))


def obtener_proxy_administracion() -> ProxyAdministracionUsuarios:
    return ProxyAdministracionUsuarios(construir_administracion, ServicioAutorizacion(construir_consulta_ambito))
