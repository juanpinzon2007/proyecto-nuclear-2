"""Composición cerrada por defecto, sin usuarios, códigos ni repositorios ficticios."""

from collections.abc import Callable
from dataclasses import replace
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.ports import (
    ConsultaAmbitoAcademico, IServicioAdministracion, IServicioExcepciones,
    IServicioSeguimiento, RepositorioUsuarios, ValidadorConvocatoria,
)
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.proxy_excepciones import ProxyExcepciones
from app.modules.identity.application.proxy_seguimiento import ProxySeguimiento
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import IntegracionPendiente, NoAutenticado
from app.modules.identity.infrastructure.security import TokensJWT


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


def construir_repositorio_usuarios() -> RepositorioUsuarios:
    # Pendiente de ER. El adaptador futuro recibirá la Session común de app.db.
    raise IntegracionPendiente()


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
    raise IntegracionPendiente()


def obtener_fabrica_tokens() -> Callable[[], TokensJWT]:
    return construir_tokens


def obtener_fabrica_usuarios() -> Callable[[], RepositorioUsuarios]:
    return construir_repositorio_usuarios


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


def obtener_fabrica_autenticacion() -> Callable[[], ServicioAutenticacion]:
    def construir() -> ServicioAutenticacion:
        return ServicioAutenticacion(
            construir_repositorio_usuarios(), construir_validador_convocatoria(),
            construir_tokens(), get_settings().identity_institutional_domains,
        )
    return construir


def obtener_proxy_seguimiento() -> ProxySeguimiento:
    return ProxySeguimiento(construir_seguimiento, ServicioAutorizacion(construir_consulta_ambito))


def obtener_proxy_excepciones() -> ProxyExcepciones:
    return ProxyExcepciones(construir_excepciones, ServicioAutorizacion(construir_consulta_ambito))


def obtener_proxy_administracion() -> ProxyAdministracionUsuarios:
    return ProxyAdministracionUsuarios(construir_administracion, ServicioAutorizacion(construir_consulta_ambito))
