"""Pruebas unitarias/repositorio en SQLite para clonación, republicación y edición preservando grafo."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.modules.cases.application.services.caso_service import CasoService
from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.entities.caso import VersionCaso
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import CasoInvalidoError, ErrorPersistenciaCaso
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion
from app.modules.cases.infrastructure.models import (
    CasoModel,
    CriterioRubricaModel,
    EscenarioModel,
    NivelRubricaModel,
    OpcionRespuestaModel,
    PreguntaModel,
    RubricaModel,
    ValoracionOpcionModel,
    VersionCasoModel,
)
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository

_TABLAS_CASES = [
    m.__table__
    for m in (
        CasoModel,
        VersionCasoModel,
        RubricaModel,
        CriterioRubricaModel,
        NivelRubricaModel,
        EscenarioModel,
        PreguntaModel,
        OpcionRespuestaModel,
        ValoracionOpcionModel,
    )
]


@pytest.fixture
def sesion_cases() -> Session:
    engine = create_engine("sqlite:///:memory:")
    for tabla in _TABLAS_CASES:
        tabla.create(bind=engine, checkfirst=True)
    with Session(engine) as session:
        yield session


def _servicio(session: Session) -> tuple[CasoService, CasoRepository]:
    repo = CasoRepository(session)
    return CasoService(repo, ConstructorCaso, construir_cadena_publicacion(), repo), repo


def _sembrar_version(session: Session, caso_academico: VersionCaso) -> tuple[CasoService, CasoRepository]:
    svc, repo = _servicio(session)
    repo.guardar(caso_academico)
    return svc, repo


def test_archivar_y_republicar_crea_nueva_version_publicada(
    sesion_cases: Session, caso_academico: VersionCaso
) -> None:
    svc, repo = _sembrar_version(sesion_cases, caso_academico)
    docente = caso_academico.docente_creador_id
    v1_id = caso_academico.id

    e0, e1 = caso_academico.escenarios[0], caso_academico.escenarios[1]
    svc.configurar_recorrido(
        docente,
        v1_id,
        inicial_id=e0.id,
        transiciones=(
            (e0.preguntas[0].opciones[0].id, "ESCENA", e1.id),
            (e0.preguntas[0].opciones[1].id, "ESCENA", e1.id),
            (e1.preguntas[0].opciones[0].id, "FIN", None),
            (e1.preguntas[0].opciones[1].id, "FIN", None),
        ),
    )
    svc.publicar(docente, v1_id)
    svc.archivar(docente, v1_id)

    clon_borrador = svc.clonar_version(docente, v1_id, publicar=False)
    assert clon_borrador.numero == 2
    assert clon_borrador.estado is EstadoCaso.BORRADOR
    assert clon_borrador.id != v1_id
    assert clon_borrador.caso_id == caso_academico.caso_id
    assert len(clon_borrador.escenarios) == 2

    republicado = svc.clonar_version(docente, v1_id, publicar=True)
    assert republicado.numero == 3
    assert republicado.estado is EstadoCaso.PUBLICADO
    grafo = repo.obtener_recorrido(republicado)
    assert grafo.validar_ejecutable() == republicado.escenarios[0].id
    assert repo.obtener_version(v1_id, docente).estado is EstadoCaso.ARCHIVADO


def test_republicar_invalido_hace_rollback(sesion_cases: Session, caso_sin_rubrica: VersionCaso) -> None:
    svc, repo = _sembrar_version(sesion_cases, caso_sin_rubrica)
    docente = caso_sin_rubrica.docente_creador_id

    with pytest.raises(CasoInvalidoError):
        svc.clonar_version(docente, caso_sin_rubrica.id, publicar=True)

    versiones = repo.listar_por_docente(docente)
    assert len(versiones) == 1


def test_actualizar_borrador_con_grafo_lo_preserva_sin_error(
    sesion_cases: Session, caso_academico: VersionCaso
) -> None:
    svc, repo = _sembrar_version(sesion_cases, caso_academico)
    docente = caso_academico.docente_creador_id
    v1_id = caso_academico.id
    e0, e1 = caso_academico.escenarios[0], caso_academico.escenarios[1]
    svc.configurar_recorrido(
        docente,
        v1_id,
        inicial_id=e0.id,
        transiciones=(
            (e0.preguntas[0].opciones[0].id, "ESCENA", e1.id),
            (e0.preguntas[0].opciones[1].id, "ESCENA", e1.id),
            (e1.preguntas[0].opciones[0].id, "FIN", None),
            (e1.preguntas[0].opciones[1].id, "FIN", None),
        ),
    )

    with pytest.raises(ErrorPersistenciaCaso, match="descartaría"):
        repo.reemplazar(caso_academico)

    caso_academico.nombre = "Conformidad grupal actualizada"
    caso_academico.rubrica.criterios[0].peso = Decimal(70)
    caso_academico.rubrica.criterios[1].peso = Decimal(30)
    repo.reemplazar(caso_academico, preservar_grafo=True)

    actualizado = repo.obtener_version(v1_id, docente)
    assert actualizado is not None
    assert actualizado.nombre == "Conformidad grupal actualizada"
    assert repo.obtener_recorrido(actualizado).validar_ejecutable() == actualizado.escenarios[0].id

