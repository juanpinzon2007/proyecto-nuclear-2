"""Dependencias FastAPI del módulo de casos (único lugar que ensambla infraestructura)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.cases.application.services.caso_service import CasoService
from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository


def get_caso_service(db: Annotated[Session, Depends(get_db)]) -> CasoService:
    return CasoService(
        repositorio=CasoRepository(db),
        fabrica_constructor=ConstructorCaso,
        cadena_validacion=construir_cadena_publicacion(),
    )

