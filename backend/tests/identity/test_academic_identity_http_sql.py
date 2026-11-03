"""Routers, JWT, repositorios Identity/mapeo/Cases y consultas Scheduling reales.

Solo se inyectan configuración JWT de prueba y fábricas de Session del laboratorio.
No se sustituye obtener_usuario_actual, rol, resolver ni servicios académicos.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.modules.identity.api import dependencies, academic_dependencies
from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Repo
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.cases.api.router import router as cases_router
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel, SesionProgramadaModel, NotificacionModel
from .academic_identity_support import motor_identidades, cuentas_identidades  # noqa: F401


@pytest.fixture
def http_sql(cuentas_identidades, monkeypatch):
    c = cuentas_identidades
    monkeypatch.setattr(dependencies, "get_session_factory", lambda: c.sesiones)
    monkeypatch.setattr(academic_dependencies, "get_session_factory", lambda: c.sesiones)
    tokens = TokensJWT("clave-exclusiva-http-sql-laboratorio-" * 2, "sql-test", "sql-client")
    app = FastAPI(debug=False)
    app.include_router(cases_router)
    app.include_router(scheduling_router)
    app.dependency_overrides[dependencies.obtener_fabrica_tokens] = lambda: lambda: tokens
    def db():
        with c.sesiones() as s:
            yield s
    app.dependency_overrides[get_db] = db
    with c.sesiones.begin() as s:
        for sistema in SistemaAcademico:
            Repo(s).agregar_verificado(VinculoAcademico(str(c.propio), sistema, c.uuid))
        casos = [CasoModel(docente_creador_id=docente) for docente in (c.uuid, uuid4())]
        s.add_all(casos)
        s.flush()
        versiones = [VersionCasoModel(caso_id=caso.id, numero=1, nombre="Caso laboratorio",
                                      desarrollo_situacional="desarrollo", contexto_historia="contexto",
                                      tiempo_estimado_min=30, estado=EstadoCaso.BORRADOR) for caso in casos]
        espacio = EspacioAcademicoModel(nombre="Espacio laboratorio")
        s.add_all([*versiones, espacio])
        s.flush()
        for version in versiones:
            version.estado=EstadoCaso.PUBLICADO
        s.flush()
        ahora = datetime.now(timezone.utc)
        sesiones = [SesionProgramadaModel(espacio_academico_id=espacio.id, version_caso_id=v.id,
                                          docente_id=caso.docente_creador_id,
                                          fecha_inicio=ahora - timedelta(minutes=5),
                                          fecha_fin=ahora + timedelta(hours=1), tiempo_maximo_minutos=15,
                                          estado="EN_CURSO") for caso, v in zip(casos, versiones)]
        s.add_all(sesiones)
        s.add_all([NotificacionModel(destinatario_id=destinatario, tipo="CALIFICACION", canal="INTERNA",
                                    mensaje=mensaje, estado="PENDIENTE") for destinatario, mensaje in
                   ((c.uuid, "Aviso propio"), (uuid4(), "Aviso privado ajeno"))])
        s.flush()
        propio, ajeno = (v.id for v in versiones)
        sesion_propia, sesion_ajena = (v.id for v in sesiones)
    with TestClient(app) as cliente:
        yield SimpleNamespace(**vars(c), app=app, cliente=cliente, tokens=tokens,
                              caso=propio, caso_ajeno=ajeno, sesion=sesion_propia, sesion_ajena=sesion_ajena)
    app.dependency_overrides.clear()


def headers(c):
    return {"Authorization": "Bearer " + c.tokens.emitir(str(c.propio), str(uuid4()))}


def estudiante(c):
    with c.sesiones.begin() as s:
        s.get(UsuarioORM, c.propio).id_rol = 2


def test_docente_casos_propios_y_rechazo_ajenos_sin_header_confiable(http_sql):
    c = http_sql
    h = headers(c) | {"X-Docente-Id": str(uuid4())}
    respuesta = c.cliente.get("/api/v1/cases", headers=h)
    assert respuesta.status_code == 200
    assert {v["version_id"] for v in respuesta.json()} == {str(c.caso)}
    assert c.cliente.get(f"/api/v1/cases/{c.caso}", headers=h).status_code == 200
    assert c.cliente.get(f"/api/v1/cases/{c.caso_ajeno}", headers=h).status_code == 404


def test_docente_sesiones_propias_y_ajenas(http_sql):
    c = http_sql
    h = headers(c)
    respuesta = c.cliente.get("/scheduling/sesiones", headers=h)
    assert respuesta.status_code == 200
    assert {v["id"] for v in respuesta.json()} == {str(c.sesion)}
    assert c.cliente.get(f"/scheduling/sesiones/{c.sesion_ajena}", headers=h).status_code == 403


def test_estudiante_solo_sus_notificaciones_con_repositorios_reales(http_sql):
    c = http_sql
    estudiante(c)
    respuesta = c.cliente.get(f"/scheduling/notificaciones?destinatario_id={c.uuid}", headers=headers(c))
    assert respuesta.status_code == 200
    assert [v["mensaje"] for v in respuesta.json()] == ["Aviso propio"]
    assert c.cliente.get(f"/scheduling/notificaciones?destinatario_id={uuid4()}", headers=headers(c)).status_code == 403
    assert c.cliente.get("/api/v1/cases", headers=headers(c)).status_code == 403


@pytest.mark.parametrize("token", [None, "invalido"])
def test_sin_jwt_verificable_no_accede_a_mapeos(http_sql, token):
    c = http_sql
    consultas = []
    def registrar(conn, cursor, sentencia, parametros, contexto, multiples):
        consultas.append(sentencia)
    event.listen(c.engine, "before_cursor_execute", registrar)
    try:
        h = {} if token is None else {"Authorization": "Bearer " + token}
        assert c.cliente.get("/api/v1/cases", headers=h).status_code == 401
    finally:
        event.remove(c.engine, "before_cursor_execute", registrar)
    assert consultas == []


def test_usuario_sin_vinculo_y_rol_actual_desde_sql(http_sql):
    c = http_sql
    h = {"Authorization": "Bearer " + c.tokens.emitir(str(c.ajeno))}
    assert c.cliente.get("/api/v1/cases", headers=h).status_code == 403
    with c.sesiones.begin() as s:
        s.get(UsuarioORM, c.propio).activo = False
    assert c.cliente.get("/api/v1/cases", headers=headers(c)).status_code == 401


def test_ambiguedad_persistida_no_se_resuelve_con_cabecera(http_sql):
    c = http_sql
    with c.sesiones.begin() as s:
        Repo(s).agregar_verificado(VinculoAcademico(str(c.propio), SistemaAcademico.CASES, uuid4()))
    assert c.cliente.get("/api/v1/cases", headers=headers(c) | {"X-Docente-Id": str(c.uuid)}).status_code == 503


def test_fabrica_sesion_falla_cerrada_sin_conectar_equipo(http_sql):
    c = http_sql
    def fallo():
        raise SQLAlchemyError("detalle privado")
    c.app.dependency_overrides[academic_dependencies.obtener_fabrica_sesiones_academicas] = lambda: fallo
    respuesta = c.cliente.get("/api/v1/cases", headers=headers(c))
    assert respuesta.status_code == 503 and "privado" not in respuesta.text


def test_no_habilita_creacion_sin_permiso_especifico(http_sql):
    c = http_sql
    assert c.cliente.post("/api/v1/cases", json={}, headers=headers(c)).status_code == 503


def test_no_habilita_ingreso_con_tolerancia_cliente(http_sql):
    c = http_sql
    estudiante(c)
    respuesta = c.cliente.post("/scheduling/validar-ingreso", headers=headers(c), json={
        "convocatoria_id": str(uuid4()), "estudiante_id": str(c.uuid),
        "codigo_acceso": "codigo-de-prueba", "tolerancia_minutos": 99999,
    })
    assert respuesta.status_code == 422


def test_dependencias_cierran_sesiones_y_revierten_lecturas(http_sql):
    c = http_sql
    eventos = []
    def rollback(conexion):
        eventos.append("rollback")
    event.listen(c.engine, "rollback", rollback)
    try:
        assert c.cliente.get("/api/v1/cases", headers=headers(c)).status_code == 200
    finally:
        event.remove(c.engine, "rollback", rollback)
    # Sesión Identity, sesión del resolver y sesión académica no quedan abiertas.
    assert len(eventos) >= 3
    if hasattr(c.engine.pool, "checkedout"):
        assert c.engine.pool.checkedout() == 0
