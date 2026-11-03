"""Autenticación → rol docente → resolución académica, cerrada sin adaptador real."""

from collections.abc import Callable, Generator
from contextlib import ExitStack
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session_factory

from app.modules.identity.api.dependencies import obtener_docente_actual, obtener_estudiante_actual
from app.modules.identity.api.errors import ERRORES
from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica, SistemaAcademico
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy


def construir_resolver_academico(sesion: Session) -> ResolverIdentidadAcademica:
    return ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(sesion))


def obtener_fabrica_sesiones_academicas() -> Callable[[], Session]:
    # No abre motor/sesión antes de autenticar. Se sustituye solo en tests aislados.
    return lambda: get_session_factory()()


def obtener_fabrica_resolver_academico(
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_academicas)],
) -> Generator[Callable[[], ResolverIdentidadAcademica], None, None]:
    with ExitStack() as recursos:
        def construir() -> ResolverIdentidadAcademica:
            try:
                sesion = recursos.enter_context(sesiones())
                return construir_resolver_academico(sesion)
            except (ValueError, SQLAlchemyError):
                raise IntegracionPendiente() from None
        yield construir


DocenteActual = Annotated[ContextoAcceso, Depends(obtener_docente_actual)]
EstudianteActual = Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)]
FabricaResolver = Annotated[Callable[[], ResolverIdentidadAcademica], Depends(obtener_fabrica_resolver_academico)]


def _resolver(usuario: ContextoAcceso, sistema: SistemaAcademico, fabrica: Callable[[], ResolverIdentidadAcademica]) -> UUID:
    try:
        return fabrica().resolver(id_usuario=usuario.id_usuario, sistema=sistema)
    except (AccesoDenegado, IntegracionPendiente) as error:
        estado, codigo, mensaje = ERRORES[type(error)]
        raise HTTPException(estado, detail={"codigo": codigo, "mensaje": mensaje},
                            headers={"Cache-Control": "no-store"}) from None


def obtener_docente_cases(docente: DocenteActual, fabrica: FabricaResolver) -> UUID:
    return _resolver(docente, SistemaAcademico.CASES, fabrica)


def obtener_docente_scheduling(docente: DocenteActual, fabrica: FabricaResolver) -> UUID:
    return _resolver(docente, SistemaAcademico.SCHEDULING, fabrica)


def obtener_estudiante_scheduling(estudiante: EstudianteActual, fabrica: FabricaResolver) -> UUID:
    return _resolver(estudiante, SistemaAcademico.SCHEDULING, fabrica)
