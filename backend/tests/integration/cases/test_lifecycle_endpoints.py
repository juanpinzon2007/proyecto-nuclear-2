"""Pruebas de integración: consulta, edición y archivo de casos."""

import copy
from tests.integration.cases.conftest import configurar_final_unica_escena
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models import (
    EscenarioModel,
    OpcionRespuestaModel,
    VersionCasoModel,
)

URL = "/api/v1/cases"


def _crear(client: TestClient, payload: dict[str, Any], headers: dict[str, str]) -> str:
    respuesta = client.post(URL, json=payload, headers=headers)
    assert respuesta.status_code == 201
    return str(respuesta.json()["version_id"])


def _publicar(client: TestClient, version_id: str, headers: dict[str, str]) -> None:
    configurar_final_unica_escena(client, version_id, headers)
    assert client.post(f"{URL}/{version_id}/publish", headers=headers).status_code == 200


def _contar(session: Session, modelo: type) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(modelo)) or 0


def _estado(session: Session, version_id: str) -> EstadoCaso:
    session.expire_all()
    version = session.get(VersionCasoModel, uuid.UUID(version_id))
    assert version is not None
    return version.estado


# --- GET ---------------------------------------------------------------------


def test_listar_devuelve_solo_casos_del_docente(
    otro_docente_headers,
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    propio_1 = _crear(client, payload_valido, headers)
    propio_2 = _crear(client, payload_valido, headers)
    _crear(client, payload_valido, otro_docente_headers)

    respuesta = client.get(URL, headers=headers)

    assert respuesta.status_code == 200
    ids = {c["version_id"] for c in respuesta.json()}
    assert ids == {propio_1, propio_2}
    assert set(respuesta.json()[0]) == {
        "version_id",
        "caso_id",
        "numero",
        "nombre",
        "tiempo_estimado_min",
        "estado",
        "creado_en",
    }


def test_listar_sin_casos_devuelve_lista_vacia(
    client: TestClient, headers: dict[str, str]
) -> None:
    assert client.get(URL, headers=headers).json() == []


def test_detalle_incluye_escenarios_preguntas_opciones_y_rubrica(
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)

    respuesta = client.get(f"{URL}/{version_id}", headers=headers)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == version_id
    assert cuerpo["estado"] == "BORRADOR"
    assert cuerpo["nombre"] == "Conformidad grupal"
    opciones = cuerpo["escenarios"][0]["preguntas"][0]["opciones"]
    assert [o["es_correcta"] for o in opciones] == [True, False]
    criterio = cuerpo["rubrica"]["criterios"][0]
    assert criterio["nombre"] == "Análisis"
    assert set(opciones[0]["valoraciones"]) == {criterio["id"]}


def test_detalle_de_otro_docente_o_inexistente_devuelve_404(
    otro_docente_headers,
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)
    otro = otro_docente_headers

    assert client.get(f"{URL}/{version_id}", headers=otro).status_code == 404
    assert client.get(f"{URL}/{uuid.uuid4()}", headers=headers).status_code == 404


# --- PUT ---------------------------------------------------------------------


def test_editar_borrador_reemplaza_estructura_sin_dejar_huerfanos(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    version_id = _crear(client, payload_valido, headers)
    nuevo = copy.deepcopy(payload_valido)
    nuevo["case"]["nombre"] = "Nombre editado"
    segundo = copy.deepcopy(nuevo["scenarios"][0])
    segundo["orden"] = 2
    nuevo["scenarios"].append(segundo)
    nuevo["rubric"]["nombre"] = "Rúbrica editada"

    respuesta = client.put(f"{URL}/{version_id}", json=nuevo, headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "caso_id": respuesta.json()["caso_id"],
        "version_id": version_id,
        "estado": "BORRADOR",
    }
    detalle = client.get(f"{URL}/{version_id}", headers=headers).json()
    assert detalle["nombre"] == "Nombre editado"
    assert [e["orden"] for e in detalle["escenarios"]] == [1, 2]
    assert detalle["rubrica"]["nombre"] == "Rúbrica editada"
    # 2 escenarios y 4 opciones: nada de la estructura anterior queda huérfano.
    assert _contar(db_session, EscenarioModel) == 2
    assert _contar(db_session, OpcionRespuestaModel) == 4


def test_editar_borrador_puede_quedar_incompleto(
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)
    incompleto = copy.deepcopy(payload_valido)
    incompleto["scenarios"] = []
    del incompleto["rubric"]

    assert client.put(f"{URL}/{version_id}", json=incompleto, headers=headers).status_code == 200
    detalle = client.get(f"{URL}/{version_id}", headers=headers).json()
    assert detalle["escenarios"] == []
    assert detalle["rubrica"] is None


def test_editar_con_payload_inconsistente_devuelve_400_y_conserva_original(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    version_id = _crear(client, payload_valido, headers)
    roto = copy.deepcopy(payload_valido)
    roto["case"]["nombre"] = "No debe guardarse"
    roto["scenarios"].append(copy.deepcopy(roto["scenarios"][0]))  # orden duplicado

    assert client.put(f"{URL}/{version_id}", json=roto, headers=headers).status_code == 400

    detalle = client.get(f"{URL}/{version_id}", headers=headers).json()
    assert detalle["nombre"] == "Conformidad grupal"
    assert len(detalle["escenarios"]) == 1
    assert _contar(db_session, OpcionRespuestaModel) == 2


@pytest.mark.parametrize("estado_final", ["PUBLICADO", "ARCHIVADO"])
def test_editar_publicado_o_archivado_devuelve_400(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
    estado_final: str,
) -> None:
    version_id = _crear(client, payload_valido, headers)
    _publicar(client, version_id, headers)
    if estado_final == "ARCHIVADO":
        assert client.post(f"{URL}/{version_id}/archive", headers=headers).status_code == 200
    nuevo = copy.deepcopy(payload_valido)
    nuevo["case"]["nombre"] = "Intento de edición"

    respuesta = client.put(f"{URL}/{version_id}", json=nuevo, headers=headers)

    assert respuesta.status_code == 400
    assert "BORRADOR" in respuesta.json()["detail"]["errores"][0]
    assert _estado(db_session, version_id) is EstadoCaso(estado_final)
    db_session.expire_all()
    version = db_session.get(VersionCasoModel, uuid.UUID(version_id))
    assert version is not None
    assert version.nombre == "Conformidad grupal"


def test_editar_inexistente_o_de_otro_docente_devuelve_404(
    otro_docente_headers,
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)
    otro = otro_docente_headers

    assert client.put(f"{URL}/{version_id}", json=payload_valido, headers=otro).status_code == 404
    assert client.put(f"{URL}/{uuid.uuid4()}", json=payload_valido, headers=headers).status_code == 404


# --- ARCHIVE -----------------------------------------------------------------


def test_archivar_publicado_pasa_a_archivado(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    version_id = _crear(client, payload_valido, headers)
    _publicar(client, version_id, headers)

    respuesta = client.post(f"{URL}/{version_id}/archive", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ARCHIVADO"
    assert _estado(db_session, version_id) is EstadoCaso.ARCHIVADO


def test_archivar_borrador_devuelve_400(
    client: TestClient,
    db_session: Session,
    payload_valido: dict[str, Any],
    headers: dict[str, str],
) -> None:
    version_id = _crear(client, payload_valido, headers)

    respuesta = client.post(f"{URL}/{version_id}/archive", headers=headers)

    assert respuesta.status_code == 400
    assert "PUBLICADA" in respuesta.json()["detail"]["errores"][0]
    assert _estado(db_session, version_id) is EstadoCaso.BORRADOR


def test_archivar_dos_veces_devuelve_400(
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)
    _publicar(client, version_id, headers)
    assert client.post(f"{URL}/{version_id}/archive", headers=headers).status_code == 200

    assert client.post(f"{URL}/{version_id}/archive", headers=headers).status_code == 400


def test_archivado_no_puede_republicarse(
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)
    _publicar(client, version_id, headers)
    client.post(f"{URL}/{version_id}/archive", headers=headers)

    assert client.post(f"{URL}/{version_id}/publish", headers=headers).status_code == 400


def test_archivar_inexistente_o_de_otro_docente_devuelve_404(
    otro_docente_headers,
    client: TestClient, payload_valido: dict[str, Any], headers: dict[str, str]
) -> None:
    version_id = _crear(client, payload_valido, headers)
    _publicar(client, version_id, headers)
    otro = otro_docente_headers

    assert client.post(f"{URL}/{version_id}/archive", headers=otro).status_code == 404
    assert client.post(f"{URL}/{uuid.uuid4()}/archive", headers=headers).status_code == 404

