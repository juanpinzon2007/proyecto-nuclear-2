"""Dependencias FastAPI del módulo de casos (único lugar que ensambla infraestructura)."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.cases.application.services.caso_service import CasoService
from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.identity.api.dependencies import obtener_docente_actual, construir_consulta_ambito
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.domain.errors import AccesoDenegado


def exigir_permiso_creacion_configurado(
    usuario: Annotated[ContextoAcceso, Depends(obtener_docente_actual)],
) -> None:
    """CREAR_CASOS debe venir del catálogo/rol persistido, nunca del cliente.

    No siembra permisos ni deduce autoría del simple rol DOCENTE. Se reutiliza
    el código del contrato de Identity y su autorizador existente.
    """
    try:
        ServicioAutorizacion(construir_consulta_ambito).exigir_permiso(usuario, "CREAR_CASOS")
    except AccesoDenegado:
        raise HTTPException(403, detail="No tiene permiso de autoría de casos.") from None


def get_caso_service(db: Annotated[Session, Depends(get_db)]) -> CasoService:
    repositorio = CasoRepository(db)
    return CasoService(
        repositorio=repositorio,
        fabrica_constructor=ConstructorCaso,
        cadena_validacion=construir_cadena_publicacion(),
        recorridos=repositorio,
    )

