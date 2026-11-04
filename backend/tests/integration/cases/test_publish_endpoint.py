"""Pruebas de integración del flujo desdoblado: borrador (POST /cases) y publicación."""

import copy
from tests.integration.cases.conftest import configurar_final_unica_escena
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.cases.domain.entities.caso import (
    Escenario,
    OpcionRespuesta,
    Pregunta,
    VersionCaso,
)
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import ErrorPersistenciaCaso
from app.modules.cases.infrastructure.models import (
    CasoModel,
    OpcionRespuestaModel,
    ValoracionOpcionModel,
    VersionCasoModel,
)
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository

URL_CREAR = "/api/v1/cases"


def _url_publicar(version_id: str | uuid.UUID) -> str:
    return f"{URL_CREAR}/{version_id}/publish"


def _filas_totales(session: Session) -> int:
    return sum(
        session.scalar(select(func.count()).select_from(tabla)) or 0
        for tabla in Base.metadata.sorted_tables
    )


def _estado_en_bd(session: Session, version_id: str) -> EstadoCaso:
    session.expire_all()
    version = session.get(VersionCasoModel, uuid.UUID(version_id))
    assert version is not None
    return version.estado


# --- POST /api/v1/cases (borrador) -------------------------------------------


def test_crear_borrador_completo_persiste_jerarquia_en_borrador(
    docente_id,
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    respuesta = client.post(URL_CREAR, json=payload_valido, headers=headers)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "BORRADOR"
    version = db_session.get(VersionCasoModel, uuid.UUID(cuerpo["version_id"]))
    assert version is not None
    assert version.estado is EstadoCaso.BORRADOR
    assert version.caso.docente_creador_id == docente_id
    assert len(version.escenarios[0].preguntas[0].opciones) == 2
    assert version.rubrica is not None
    assert db_session.scalar(select(func.count()).select_from(ValoracionOpcionModel)) == 2


def test_crear_borrador_incompleto_se_guarda_sin_ejecutar_cor(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    """Sin escenarios, sin rúbrica y tiempo 0: el CoR lo rechazaría, el borrador no."""
    payload = copy.deepcopy(payload_valido)
    payload["scenarios"] = []
    del payload["rubric"]
    payload["case"]["tiempoEstimadoMin"] = 0

    respuesta = client.post(URL_CREAR, json=payload, headers=headers)

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "BORRADOR"
    assert _estado_en_bd(db_session, respuesta.json()["version_id"]) is EstadoCaso.BORRADOR


def test_crear_borrador_con_orden_duplicado_devuelve_400_sin_registros(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    payload = copy.deepcopy(payload_valido)
    payload["scenarios"].append(copy.deepcopy(payload["scenarios"][0]))  # mismo orden

    respuesta = client.post(URL_CREAR, json=payload, headers=headers)

    assert respuesta.status_code == 400
    assert _filas_totales(db_session) == 0


def test_crear_borrador_rechaza_campo_desconocido_y_falta_de_token(
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    con_extra = {**payload_valido, "x": 1}
    assert client.post(URL_CREAR, json=con_extra, headers=headers).status_code == 422
    assert client.post(URL_CREAR, json=payload_valido).status_code == 401


# --- POST /api/v1/cases/{id}/publish -----------------------------------------


def test_flujo_borrador_y_luego_publicacion_exitosa(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    version_id = client.post(URL_CREAR, json=payload_valido, headers=headers).json()["version_id"]

    configurar_final_unica_escena(client, version_id, headers)
    respuesta = client.post(_url_publicar(version_id), headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "PUBLICADO"
    assert _estado_en_bd(db_session, version_id) is EstadoCaso.PUBLICADO


def test_publicar_borrador_incompleto_devuelve_400_y_sigue_en_borrador(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    payload = copy.deepcopy(payload_valido)
    del payload["rubric"]
    payload["scenarios"][0]["questions"][0]["options"][1]["justificacion"] = ""
    version_id = client.post(URL_CREAR, json=payload, headers=headers).json()["version_id"]

    respuesta = client.post(_url_publicar(version_id), headers=headers)

    assert respuesta.status_code == 400
    errores = respuesta.json()["detail"]["errores"]
    assert "El caso no tiene rúbrica asociada." in errores
    assert any("carece de justificación" in e for e in errores)
    assert _estado_en_bd(db_session, version_id) is EstadoCaso.BORRADOR


def test_publicar_dos_veces_devuelve_400(
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = client.post(URL_CREAR, json=payload_valido, headers=headers).json()["version_id"]
    configurar_final_unica_escena(client, version_id, headers)
    assert client.post(_url_publicar(version_id), headers=headers).status_code == 200

    segunda = client.post(_url_publicar(version_id), headers=headers)

    assert segunda.status_code == 400
    assert "BORRADOR" in segunda.json()["detail"]["errores"][0]


def test_publicar_version_inexistente_devuelve_404(
    client: TestClient, headers: dict[str, str]
) -> None:
    assert client.post(_url_publicar(uuid.uuid4()), headers=headers).status_code == 404


def test_publicar_borrador_de_otro_docente_devuelve_404(
    otro_docente_headers,
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    version_id = client.post(URL_CREAR, json=payload_valido, headers=headers).json()["version_id"]
    otro = otro_docente_headers

    assert client.post(_url_publicar(version_id), headers=otro).status_code == 404
    assert _estado_en_bd(db_session, version_id) is EstadoCaso.BORRADOR


# --- Repositorio --------------------------------------------------------------


def test_repositorio_hace_rollback_si_falla_a_mitad(db_session: Session) -> None:
    """Dos opciones con el mismo orden violan la unicidad: nada debe quedar guardado."""
    version = VersionCaso("n", "d", "c", 30, uuid.uuid4())
    pregunta = Pregunta(orden=1, enunciado="q")
    pregunta.opciones = [
        OpcionRespuesta(orden=1, texto="a", es_correcta=True, justificacion="j"),
        OpcionRespuesta(orden=1, texto="b", es_correcta=False, justificacion="j"),
    ]
    version.escenarios.append(Escenario(orden=1, contexto_situacional="x", preguntas=[pregunta]))

    try:
        CasoRepository(db_session).guardar(version)
    except ErrorPersistenciaCaso:
        pass
    else:  # pragma: no cover
        raise AssertionError("Se esperaba ErrorPersistenciaCaso")

    assert db_session.scalar(select(func.count()).select_from(CasoModel)) == 0
    assert db_session.scalar(select(func.count()).select_from(OpcionRespuestaModel)) == 0


def test_repositorio_roundtrip_conserva_valoraciones(
    docente_id,
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    cuerpo = client.post(URL_CREAR, json=payload_valido, headers=headers).json()

    version = CasoRepository(db_session).obtener_version(
        uuid.UUID(cuerpo["version_id"]), docente_id
    )

    assert version is not None
    assert version.rubrica is not None
    criterio_id = version.rubrica.criterios[0].id
    opciones = version.escenarios[0].preguntas[0].opciones
    assert [set(o.valoraciones) for o in opciones] == [{criterio_id}, {criterio_id}]
