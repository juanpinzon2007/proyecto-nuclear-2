from tests.unit.scheduling.ingress_support import politica_fixture
from app.modules.scheduling.api.dependencies import exigir_contexto_convocatoria
from app.modules.identity.api.academic_dependencies import obtener_fabrica_sesiones_academicas
"""HTTP ASGI y JWT reales; sin PostgreSQL ni asociaciones productivas.

El servicio validar_ingreso y el resolver son reales. Session, usuarios y consulta
de vínculos son mocks, salvo donde se prueba el repositorio de usuarios real
con una Session que falla. Las identidades son fixtures explícitas.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from tests.integration.test_docente_identity import entorno, SECRETO  # noqa: F401
from app.db.session import get_db
from app.modules.identity.api.academic_dependencies import obtener_fabrica_resolver_academico
from app.modules.identity.application.academic_identity import (
    ConsultaVinculosAcademicos, ResolverIdentidadAcademica, SistemaAcademico, VinculoAcademico,
)
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.scheduling.api.router import router, exigir_politica_ingreso_configurada
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel


PROPIO = UUID("a199b9f7-051e-40df-b1f8-9a7fb321bac2")
AJENO = UUID("d988b0f5-a0d1-4b4d-b909-9c8be80397ca")
CONVOCATORIA = UUID("bb96e17f-4c17-422d-9df5-dd9c0e2eb1cf")
SESION = UUID("ee624fca-c363-4bae-80fd-cb69764167a7")
CODIGO = "codigo-exclusivo-de-pruebas"


@pytest.fixture
def estudiante(entorno):
    entorno.repo.obtener.return_value = replace(entorno.usuario, roles=frozenset({Rol.ESTUDIANTE}))
    entorno.app.include_router(router)
    entorno.app.dependency_overrides[exigir_politica_ingreso_configurada] = lambda: politica_fixture(15)
    entorno.app.dependency_overrides[exigir_contexto_convocatoria] = lambda: None
    db = Mock(spec=Session)
    consulta = Mock(spec=ConsultaVinculosAcademicos)
    consulta.obtener.return_value = (VinculoAcademico("7", SistemaAcademico.SCHEDULING, PROPIO),)
    resolver = ResolverIdentidadAcademica(consulta)
    entorno.app.dependency_overrides[obtener_fabrica_resolver_academico] = lambda: lambda: resolver
    entorno.app.dependency_overrides[get_db] = lambda: db
    ahora = datetime.now(timezone.utc)
    sesion = SimpleNamespace(
        id=SESION, espacio_academico_id=AJENO, version_caso_id=AJENO,
        docente_id=AJENO, fecha_inicio=ahora - timedelta(minutes=5),
        fecha_fin=ahora + timedelta(hours=1), tiempo_maximo_minutos=30,
        lugar=None, mensaje_personalizado=None, estado="EN_CURSO", finalizado_en=None,
    )
    convocatoria = SimpleNamespace(estudiante_id=PROPIO, sesion_id=SESION,
                                  estado="ACTIVA", codigo_hash=hashlib.sha256(CODIGO.encode()).hexdigest())
    db.get.side_effect = lambda modelo, identificador: (
        convocatoria if modelo is ConvocatoriaModel and identificador == CONVOCATORIA
        else sesion if modelo is SesionProgramadaModel and identificador == SESION else None
    )
    db.scalars.return_value.all.return_value = []
    return SimpleNamespace(**vars(entorno), db=db, consulta=consulta,
                           sesion=sesion, convocatoria=convocatoria)


def headers(e):
    return {"Authorization": "Bearer " + e.tokens.emitir("7", "convocatoria-fixture")}


def solicitar(e, operacion, cabeceras=None, id_solicitado=PROPIO, **cambios):
    if operacion == "notificaciones":
        return e.cliente.get(f"/scheduling/notificaciones?destinatario_id={id_solicitado}", headers=cabeceras)
    cuerpo = dict(convocatoria_id=str(CONVOCATORIA), estudiante_id=str(id_solicitado),
                  codigo_acceso=CODIGO)
    cuerpo.update(cambios)
    return e.cliente.post("/scheduling/validar-ingreso", json=cuerpo, headers=cabeceras)


@pytest.mark.parametrize("operacion", ["notificaciones", "ingreso"])
@pytest.mark.parametrize("problema", ["ausente", "invalido", "vencido", "inactivo", "inexistente", "docente", "sin_convocatoria"])
def test_autenticacion_y_rol_obligatorios(estudiante, operacion, problema):
    cabeceras = headers(estudiante)
    if problema == "ausente":
        cabeceras = {"X-Estudiante-Id": str(PROPIO), "X-Role": "ESTUDIANTE"}
    elif problema == "invalido":
        cabeceras = {"Authorization": "Bearer invalido"}
    elif problema == "vencido":
        claims = jwt.decode(estudiante.tokens.emitir("7", "conv"), options={"verify_signature": False})
        claims.update(iat=1000, nbf=1000, exp=1060)
        cabeceras = {"Authorization": "Bearer " + jwt.encode(claims, SECRETO, algorithm="HS256")}
    elif problema == "inactivo":
        estudiante.repo.obtener.return_value = replace(estudiante.repo.obtener.return_value, activo=False)
    elif problema == "inexistente":
        estudiante.repo.obtener.return_value = None
    elif problema == "docente":
        estudiante.repo.obtener.return_value = estudiante.usuario
    else:
        cabeceras = {"Authorization": "Bearer " + estudiante.tokens.emitir("7")}
    if problema == "sin_convocatoria":
        if operacion == "ingreso":
            estudiante.app.dependency_overrides.pop(exigir_politica_ingreso_configurada)
        respuesta = solicitar(estudiante, operacion, cabeceras)
        assert respuesta.status_code == (200 if operacion == "notificaciones" else 503)
        if operacion == "notificaciones":
            estudiante.db.scalars.assert_called_once()
        return
    respuesta = solicitar(estudiante, operacion, cabeceras)
    assert respuesta.status_code == (403 if problema == "docente" else 401)
    if respuesta.status_code == 401:
        assert respuesta.headers["www-authenticate"] == "Bearer"
    estudiante.consulta.obtener.assert_not_called()
    assert estudiante.db.mock_calls == []


@pytest.mark.parametrize("operacion", ["notificaciones", "ingreso"])
@pytest.mark.parametrize("problema", ["sesion_no_disponible", "sin_vinculo", "duplicado", "usuario_ajeno", "otro_sistema", "fallo"])
def test_sin_correspondencia_verificada_no_consulta_bd(estudiante, operacion, problema):
    if problema == "sesion_no_disponible":
        del estudiante.app.dependency_overrides[obtener_fabrica_resolver_academico]
        estudiante.app.dependency_overrides[obtener_fabrica_sesiones_academicas] = lambda: Mock(side_effect=SQLAlchemyError("sin laboratorio"))
    elif problema == "fallo":
        estudiante.consulta.obtener.side_effect = IntegracionPendiente("detalle privado")
    else:
        estudiante.consulta.obtener.return_value = {
            "sin_vinculo": (),
            "duplicado": (VinculoAcademico("7", SistemaAcademico.SCHEDULING, PROPIO),) * 2,
            "usuario_ajeno": (VinculoAcademico("8", SistemaAcademico.SCHEDULING, PROPIO),),
            "otro_sistema": (VinculoAcademico("7", SistemaAcademico.CASES, PROPIO),),
        }[problema]
    respuesta = solicitar(estudiante, operacion, headers(estudiante))
    assert respuesta.status_code == (403 if problema == "sin_vinculo" else 503)
    assert "privado" not in respuesta.text
    assert estudiante.db.mock_calls == []


@pytest.mark.parametrize("operacion", ["notificaciones", "ingreso"])
def test_alterar_identificador_http_no_suplanta(estudiante, operacion):
    respuesta = solicitar(estudiante, operacion, headers(estudiante), AJENO)
    assert respuesta.status_code == 403
    assert estudiante.db.mock_calls == []


def test_notificaciones_filtra_por_estudiante_del_servidor(estudiante):
    notif = SimpleNamespace(id=CONVOCATORIA, convocatoria_id=CONVOCATORIA,
                           destinatario_id=PROPIO, tipo="CONVOCATORIA", canal="INTERNA",
                           mensaje="Mensaje propio", estado="PENDIENTE", creada_en=datetime.now(timezone.utc))
    estudiante.db.scalars.return_value.all.return_value = [notif]
    respuesta = solicitar(estudiante, "notificaciones", headers(estudiante))
    assert respuesta.status_code == 200
    assert respuesta.json()[0]["destinatario_id"] == str(PROPIO)
    assert respuesta.headers["cache-control"] == "no-store"
    sentencia = estudiante.db.scalars.call_args.args[0]
    assert PROPIO in sentencia.compile().params.values()
    estudiante.consulta.obtener.assert_called_once_with(id_usuario="7", sistema=SistemaAcademico.SCHEDULING)


def test_ingreso_correcto_usa_servicio_real_y_no_confia_en_headers(estudiante):
    cabeceras = {**headers(estudiante), "X-Estudiante-Id": str(AJENO)}
    respuesta = solicitar(estudiante, "ingreso", cabeceras)
    assert respuesta.status_code == 200 and respuesta.json()["id"] == str(SESION)
    assert respuesta.headers["cache-control"] == "no-store"
    estudiante.db.get.assert_any_call(ConvocatoriaModel, CONVOCATORIA)
    estudiante.db.commit.assert_not_called()


@pytest.mark.parametrize("problema", ["codigo", "titular_convocatoria", "retirada", "sesion_cerrada", "antes", "tarde", "convocatoria_inexistente"])
def test_conserva_reglas_de_convocatoria_codigo_y_horario(estudiante, problema):
    cambios = {}
    if problema == "codigo":
        cambios["codigo_acceso"] = "incorrecto"
    elif problema == "titular_convocatoria":
        estudiante.convocatoria.estudiante_id = AJENO
    elif problema == "retirada":
        estudiante.convocatoria.estado = "RETIRADA"
    elif problema == "sesion_cerrada":
        estudiante.sesion.estado = "FINALIZADO"
    elif problema == "antes":
        estudiante.sesion.fecha_inicio = datetime.now(timezone.utc) + timedelta(hours=1)
        estudiante.sesion.fecha_fin = estudiante.sesion.fecha_inicio + timedelta(hours=1)
    elif problema == "tarde":
        estudiante.sesion.fecha_inicio = datetime.now(timezone.utc) - timedelta(hours=1)
    else:
        cambios["convocatoria_id"] = str(AJENO)
    assert solicitar(estudiante, "ingreso", headers(estudiante), **cambios).status_code == 403
    estudiante.db.commit.assert_not_called()


@pytest.mark.parametrize("operacion", ["notificaciones", "ingreso"])
def test_fallo_sql_del_repositorio_identity_cierra_acceso(estudiante, operacion):
    sesion = Mock(spec=Session)
    sesion.get.side_effect = SQLAlchemyError("detalle SQL privado")
    estudiante.fabrica_usuarios.return_value = RepositorioUsuariosSQLAlchemy(sesion)
    respuesta = solicitar(estudiante, operacion, headers(estudiante))
    assert respuesta.status_code == 503 and "privado" not in respuesta.text
    estudiante.consulta.obtener.assert_not_called()
    assert estudiante.db.mock_calls == []


@pytest.mark.parametrize("operacion", ["notificaciones", "ingreso"])
def test_fallo_inesperado_no_se_oculta_ni_devuelve_datos(estudiante, operacion):
    estudiante.consulta.obtener.side_effect = RuntimeError("detalle privado")
    with pytest.raises(RuntimeError, match="privado"):
        solicitar(estudiante, operacion, headers(estudiante))
    with TestClient(estudiante.app, raise_server_exceptions=False) as cliente:
        copia = SimpleNamespace(**{**vars(estudiante), "cliente": cliente})
        respuesta = solicitar(copia, operacion, headers(estudiante))
    assert respuesta.status_code == 500 and "privado" not in respuesta.text
    assert estudiante.db.mock_calls == []


def test_openapi_exige_bearer_para_ambas_rutas(estudiante):
    rutas = estudiante.app.openapi()["paths"]
    assert rutas["/scheduling/notificaciones"]["get"]["security"] == [{"HTTPBearer": []}]
    assert rutas["/scheduling/validar-ingreso"]["post"]["security"] == [{"HTTPBearer": []}]
