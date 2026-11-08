"""Identidad/convocatorias SQL reales; sin política académica productiva.

Los positivos y fronteras inyectan una ventana SINTÉTICA explícita únicamente
para comprobar la mecánica temporal. No prueban RF-22 aprobado.
"""

from datetime import datetime, timedelta, timezone
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.scheduling.api.router import exigir_politica_ingreso_configurada, obtener_reloj_ingreso
from app.modules.scheduling.domain.ingress_policy import VentanaIngreso, PoliticaTemporalNoDisponible
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel, ConvocatoriaModel
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from tests.unit.scheduling.ingress_support import restaurar_utc_solo_fixture_sqlite
from .test_student_login_scheduling import login_sql, login, SECRETO  # noqa: F401
from .academic_identity_support import motor_identidades, cuentas_identidades, IDS  # noqa: F401


AHORA = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


@pytest.fixture
def ingreso_sql(login_sql):
    c = login_sql
    with c.sesiones.begin() as s:
        sesion = s.get(SesionProgramadaModel, c.sesion)
        sesion.estado = "EN_CURSO"
        sesion.fecha_inicio = AHORA - timedelta(minutes=10)
        sesion.fecha_fin = AHORA + timedelta(hours=1)
        # Ámbito real exclusivo de estas pruebas de ingreso. No añadirlo a la
        # fixture compartida de login: otras suites prueban sesiones sin asignar.
        docente = UsuarioORM(id_usuario=next(IDS),id_rol=1,nombre="Docente LAB",
            correo=f"docente-{uuid4().hex}@universidad.test",clave_hash="sin-login-en-fixture")
        s.add(docente); s.flush()
        grupo = GrupoAcademicoORM(id_profesor=docente.id_usuario,nombre="Grupo LAB ingreso",periodo="LAB")
        s.add(grupo); s.flush()
        caso = s.get(CasoModel,s.get(VersionCasoModel,sesion.version_caso_id).caso_id)
        if caso.id_caso is None: caso.id_caso = next(IDS)  # PK académica nueva SOLO del laboratorio SQLite.
        s.add(GrupoEstudianteORM(id_grupo=grupo.id_grupo,id_estudiante=c.propio,
            fecha_ingreso=AHORA.replace(tzinfo=None)-timedelta(days=1)))
        s.add(AsignacionCasoModel(id_grupo=grupo.id_grupo,id_caso=caso.id_caso,
            sesion_programada_id=sesion.id,version_caso_id=sesion.version_caso_id,
            apertura=sesion.fecha_inicio.replace(tzinfo=None),cierre=sesion.fecha_fin.replace(tzinfo=None),
            fecha_limite_ingreso=sesion.fecha_fin.replace(tzinfo=None),tiempo_maximo_min=sesion.tiempo_maximo_minutos))
    event.listen(c.sesiones, "loaded_as_persistent", restaurar_utc_solo_fixture_sqlite)
    c.app.dependency_overrides[obtener_reloj_ingreso] = lambda: SimpleNamespace(ahora=lambda: AHORA)
    # Solo contrato aislado anterior con política LAB; admisión real se acredita en main.
    from app.modules.scheduling.api.dependencies import obtener_admision
    c.app.dependency_overrides[obtener_admision] = lambda: None
    token = login(c).json()["access_token"]
    try:
        yield SimpleNamespace(**vars(c), token=token)
    finally:
        event.remove(c.sesiones, "loaded_as_persistent", restaurar_utc_solo_fixture_sqlite)


def solicitar(c, *, token=None, **cambios):
    cuerpo = dict(convocatoria_id=str(c.convocatoria), estudiante_id=str(c.uuid), codigo_acceso=c.codigo)
    cuerpo.update(cambios)
    return c.cliente.post("/scheduling/validar-ingreso", json=cuerpo,
                          headers={"Authorization": "Bearer " + (c.token if token is None else token)})


def ventana_fixture(c, *, cierre_incluido=True):
    ventana = VentanaIngreso(AHORA - timedelta(minutes=1), AHORA, True, cierre_incluido)
    c.app.dependency_overrides[exigir_politica_ingreso_configurada] = lambda: SimpleNamespace(
        obtener_ventana=lambda **_: ventana,
    )


def test_estudiante_valido_sigue_cerrado_sin_politica(ingreso_sql):
    c = ingreso_sql
    assert solicitar(c).status_code == 503


@pytest.mark.parametrize("credencial", ["ausente", "invalida", "vencida"])
def test_no_se_consulta_politica_sin_autenticacion(ingreso_sql, credencial):
    c = ingreso_sql
    politica = Mock(side_effect=AssertionError("No debe evaluar política"))
    c.app.dependency_overrides[exigir_politica_ingreso_configurada] = politica
    if credencial == "ausente":
        respuesta = c.cliente.post("/scheduling/validar-ingreso", json={
            "convocatoria_id": str(c.convocatoria), "estudiante_id": str(c.uuid), "codigo_acceso": c.codigo,
        })
    elif credencial == "invalida": respuesta = solicitar(c, token="invalido")
    else:
        claims = jwt.decode(c.token, options={"verify_signature": False})
        claims.update(iat=1000, nbf=1000, exp=1060)
        respuesta = solicitar(c, token=jwt.encode(claims, SECRETO, algorithm="HS256"))
    assert respuesta.status_code == 401
    politica.assert_not_called()


@pytest.mark.parametrize("estado", ["SIN_INICIAR", "FINALIZADO"])
def test_estado_sesion_impide_ingreso_sin_regla_temporal_inventada(ingreso_sql, estado):
    c = ingreso_sql
    with c.sesiones.begin() as s: s.get(SesionProgramadaModel, c.sesion).estado = estado
    assert solicitar(c).status_code == 403


@pytest.mark.parametrize("problema", ["ajena", "inexistente", "retirada", "otro_estudiante", "codigo"])
def test_convocatoria_y_titularidad_se_rechazan_antes_de_politica(ingreso_sql, problema):
    c = ingreso_sql
    cambios = {}
    if problema == "ajena": cambios["convocatoria_id"] = str(c.convocatoria_ajena)
    elif problema == "inexistente":
        inexistente = uuid4()
        cambios["convocatoria_id"] = str(inexistente)
        cambios["token"] = c.tokens.emitir(str(c.propio), str(inexistente))
    elif problema == "retirada":
        with c.sesiones.begin() as s: s.get(ConvocatoriaModel, c.convocatoria).estado = "RETIRADA"
    elif problema == "otro_estudiante": cambios["estudiante_id"] = str(uuid4())
    else: cambios["codigo_acceso"] = "incorrecto"
    assert solicitar(c, **cambios).status_code == 403


@pytest.mark.parametrize("campo,valor", [
    ("tolerancia_minutos", 1000000), ("ahora", "2099-01-01T00:00:00Z"),
    ("fecha_inicio", "2000-01-01T00:00:00Z"), ("ventana", {"cierre": "2099"}),
])
def test_http_no_permite_definir_tiempo_o_tolerancia(ingreso_sql, campo, valor):
    c = ingreso_sql
    respuesta = solicitar(c, **{campo: valor})
    assert respuesta.status_code == 422 and c.codigo not in respuesta.text


@pytest.mark.parametrize("incluido", [True, False])
def test_frontera_sql_solo_con_ventana_sintetica_de_prueba(ingreso_sql, incluido):
    c = ingreso_sql
    ventana_fixture(c, cierre_incluido=incluido)
    respuesta = solicitar(c)
    assert respuesta.status_code == (200 if incluido else 403)
    with c.sesiones() as s:
        assert s.get(SesionProgramadaModel, c.sesion).estado == "EN_CURSO"


@pytest.mark.parametrize("instante", [AHORA-timedelta(minutes=2), AHORA+timedelta(microseconds=1)])
def test_antes_o_despues_de_ventana_sintetica_no_autoriza(ingreso_sql, instante):
    c = ingreso_sql
    ventana_fixture(c)
    c.app.dependency_overrides[obtener_reloj_ingreso] = lambda: SimpleNamespace(ahora=lambda: instante)
    assert solicitar(c).status_code == 403


def test_offset_del_reloj_no_amplia_ventana(ingreso_sql):
    c = ingreso_sql
    ventana_fixture(c)
    c.app.dependency_overrides[obtener_reloj_ingreso] = lambda: SimpleNamespace(
        ahora=lambda: AHORA.astimezone(timezone(timedelta(hours=-5))),
    )
    assert solicitar(c).status_code == 200


@pytest.mark.parametrize("fallo", ["politica", "repositorio", "inesperado"])
def test_fallos_no_conceden_acceso(ingreso_sql, fallo):
    c = ingreso_sql
    def obtener(**_):
        if fallo == "inesperado": raise RuntimeError("detalle privado")
        raise PoliticaTemporalNoDisponible()
    c.app.dependency_overrides[exigir_politica_ingreso_configurada] = lambda: SimpleNamespace(obtener_ventana=obtener)
    if fallo == "repositorio":
        db = Mock(spec=Session)
        db.no_autoflush = nullcontext()
        db.get.side_effect = SQLAlchemyError("detalle SQL privado")
        c.app.dependency_overrides[get_db] = lambda: db
    if fallo == "inesperado":
        with pytest.raises(RuntimeError): solicitar(c)
        with TestClient(c.app, raise_server_exceptions=False) as cliente:
            copia = SimpleNamespace(**{**vars(c), "cliente": cliente})
            respuesta = solicitar(copia)
        assert respuesta.status_code == 500
    else: respuesta = solicitar(c)
    assert respuesta.status_code in {500, 503} and "privado" not in respuesta.text


def test_openapi_ya_no_ofrece_tolerancia_del_estudiante(ingreso_sql):
    schema = ingreso_sql.app.openapi()["components"]["schemas"]["ValidarIngresoRequest"]
    assert "tolerancia_minutos" not in schema["properties"] and schema["additionalProperties"] is False
