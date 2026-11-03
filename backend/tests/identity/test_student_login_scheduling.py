"""Login HTTP ASGI con JWT y persistencia real SQLite/PostgreSQL efímero.

Solo se inyectan configuración y Session del laboratorio. Sin mocks de usuarios,
convocatorias, resolver o servicios en las pruebas de recorrido positivo.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.modules.identity.api import dependencies, academic_dependencies
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Repo
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.cases.api.router import router as cases_router
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel, RubricaModel
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.scheduling.api.dependencies import exigir_contexto_convocatoria
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
from app.modules.scheduling.application.crear_notificacion import crear_notificacion
from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel, SesionProgramadaModel, ConvocatoriaModel
from .academic_identity_support import motor_identidades, cuentas_identidades  # noqa: F401


SECRETO = "clave-exclusiva-login-scheduling-lab-" * 2
BASE = "/api/v1/identity"


@pytest.fixture
def login_sql(cuentas_identidades, monkeypatch):
    c = cuentas_identidades
    monkeypatch.setattr(dependencies, "get_session_factory", lambda: c.sesiones)
    monkeypatch.setattr(academic_dependencies, "get_session_factory", lambda: c.sesiones)
    tokens = TokensJWT(SECRETO, "login-sql-test", "login-sql-client")
    propio, ajeno = c.uuid, uuid4()
    with c.sesiones.begin() as s:
        for identificador, referencia in ((c.propio, propio), (c.ajeno, ajeno)):
            s.get(UsuarioORM, identificador).id_rol = 2
            Repo(s).agregar_verificado(VinculoAcademico(str(identificador), SistemaAcademico.SCHEDULING, referencia))
        caso = CasoModel(docente_creador_id=uuid4())
        espacio = EspacioAcademicoModel(nombre="Laboratorio login")
        s.add_all([caso, espacio]); s.flush()
        version = VersionCasoModel(caso_id=caso.id, numero=1, nombre="Caso login", desarrollo_situacional="d",
                                   contexto_historia="c", tiempo_estimado_min=30, estado=EstadoCaso.BORRADOR)
        s.add(version); s.flush()
        # Cargar referencia antes de congelar; no hay bypass de triggers en fixtures.
        s.add(RubricaModel(version_caso_id=version.id,nombre="Referencia de laboratorio",
                          version_regla="regla-lab-8a-v1"))
        s.flush()
        version.estado=EstadoCaso.PUBLICADO
        s.flush()
        ahora = datetime.now(timezone.utc)
        sesion = SesionProgramadaModel(espacio_academico_id=espacio.id, version_caso_id=version.id,
                                       docente_id=caso.docente_creador_id, fecha_inicio=ahora + timedelta(hours=1),
                                       fecha_fin=ahora + timedelta(hours=2), tiempo_maximo_minutos=20)
        s.add(sesion); s.flush()
        convocada = crear_convocatoria(s, sesion_id=sesion.id, estudiante_id=propio)
        otra = crear_convocatoria(s, sesion_id=sesion.id, estudiante_id=ajeno)
        crear_notificacion(s, destinatario_id=propio, tipo="CONVOCATORIA", canal="INTERNA",
                          mensaje="Aviso propio", convocatoria_id=convocada.convocatoria_id)
        crear_notificacion(s, destinatario_id=ajeno, tipo="CONVOCATORIA", canal="INTERNA",
                          mensaje="Aviso ajeno privado", convocatoria_id=otra.convocatoria_id)
        id_sesion = sesion.id
    app = FastAPI(debug=False)
    app.include_router(identity_router)
    app.include_router(scheduling_router)
    app.include_router(cases_router)
    app.dependency_overrides[dependencies.obtener_fabrica_tokens] = lambda: lambda: tokens
    app.dependency_overrides[dependencies.obtener_dominios_login] = lambda: ("universidad.test",)
    def db():
        with c.sesiones() as s:
            yield s
    app.dependency_overrides[get_db] = db

    # Sonda exclusiva del laboratorio: prueba el contrato de contexto sin abrir ingreso.
    @app.post("/sonda-contexto")
    def sonda(contexto: Annotated[None, Depends(exigir_contexto_convocatoria)]):
        return {"autorizado": True}

    with TestClient(app) as cliente:
        yield SimpleNamespace(**vars(c), app=app, cliente=cliente, tokens=tokens, codigo=convocada.codigo_acceso,
                              codigo_ajeno=otra.codigo_acceso, convocatoria=convocada.convocatoria_id,
                              convocatoria_ajena=otra.convocatoria_id, sesion=id_sesion,
                              correo=f"cuenta{c.propio}@universidad.test")
    app.dependency_overrides.clear()


def login(c, **cambios):
    return c.cliente.post(BASE + "/auth/estudiantes", json={
        "correo": c.correo, "codigo_convocatoria": c.codigo, **cambios,
    })


def contexto(c, token, convocatoria=None):
    return c.cliente.post("/sonda-contexto", headers={"Authorization": "Bearer " + token}, json={
        "convocatoria_id": str(convocatoria or c.convocatoria), "estudiante_id": str(c.uuid),
        "codigo_acceso": c.codigo,
    })


def test_flujo_login_autorizado_jwt_y_notificaciones_reales(login_sql):
    c = login_sql
    respuesta = login(c, correo="  " + c.correo.upper() + "  ")
    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    token = respuesta.json()["access_token"]
    identidad = c.tokens.verificar(token)
    assert identidad.id_usuario == str(c.propio) and identidad.id_convocatoria == str(c.convocatoria)
    claims = jwt.decode(token, SECRETO, algorithms=["HS256"], issuer="login-sql-test", audience="login-sql-client")
    assert set(claims) == {"sub", "iss", "aud", "iat", "nbf", "exp", "jti", "token_type", "convocatoria_id"}
    assert c.codigo not in str(claims) and c.correo not in str(claims)
    h = {"Authorization": "Bearer " + token}
    assert c.cliente.get(BASE + "/me", headers=h).json()["id_usuario"] == str(c.propio)
    avisos = c.cliente.get(f"/scheduling/notificaciones?destinatario_id={c.uuid}", headers=h)
    assert avisos.status_code == 200 and [a["mensaje"] for a in avisos.json()] == ["Aviso propio"]
    assert contexto(c, token).status_code == 200
    assert contexto(c, token, c.convocatoria_ajena).status_code == 403
    # Resolver contexto no activa ni crea participación o sesión.
    ingreso = c.cliente.post("/scheduling/validar-ingreso", headers=h, json={
        "convocatoria_id": str(c.convocatoria), "estudiante_id": str(c.uuid),
        "codigo_acceso": c.codigo,
    })
    assert ingreso.status_code == 403
    assert ingreso.json()["detail"] == "La sesión no está en curso."
    assert c.cliente.post("/api/v1/cases", headers=h, json={}).status_code == 403


@pytest.mark.parametrize("problema", ["codigo", "correo", "ajena", "inactivo", "docente", "retirada"])
def test_login_rechaza_credenciales_o_titularidad_invalidas(login_sql, problema):
    c = login_sql
    cambios = {}
    if problema == "codigo": cambios["codigo_convocatoria"] = "incorrecto"
    elif problema == "correo": cambios["correo"] = "no-existe@universidad.test"
    elif problema == "ajena": cambios["codigo_convocatoria"] = c.codigo_ajeno
    else:
        with c.sesiones.begin() as s:
            if problema == "inactivo": s.get(UsuarioORM, c.propio).activo = False
            elif problema == "docente": s.get(UsuarioORM, c.propio).id_rol = 1
            else: s.get(ConvocatoriaModel, c.convocatoria).estado = "RETIRADA"
    respuesta = login(c, **cambios)
    assert respuesta.status_code == 401 and "access_token" not in respuesta.text
    assert c.codigo not in respuesta.text and c.codigo_ajeno not in respuesta.text


def test_convocatoria_inexistente_para_codigo_no_otorga_token(login_sql):
    c = login_sql
    assert login(c, codigo_convocatoria="codigo-sin-convocatoria").status_code == 401


def test_usuario_sin_asociacion_no_enumera_su_cuenta(login_sql):
    c = login_sql
    with c.sesiones.begin() as s:
        usuario = UsuarioORM(id_usuario=c.ajeno + 1000000, id_rol=2, nombre="Fixture sin vínculo",
                             correo=f"sin-vinculo{c.ajeno}@universidad.test", clave_hash="fixture")
        s.add(usuario)
        correo = usuario.correo
    assert login(c, correo=correo).status_code == 401


def test_asociacion_ambigua_no_elige_un_uuid_por_codigo(login_sql):
    c = login_sql
    with c.sesiones.begin() as s:
        Repo(s).agregar_verificado(VinculoAcademico(str(c.propio), SistemaAcademico.SCHEDULING, uuid4()))
    assert login(c).status_code == 503


def test_colision_de_correos_normalizados_no_elige_primero(login_sql):
    c = login_sql
    with c.sesiones.begin() as s:
        s.get(UsuarioORM, c.ajeno).correo = c.correo.upper()
    assert login(c).status_code == 503


def test_dos_convocatorias_con_mismo_codigo_no_eligen_primera(login_sql):
    c = login_sql
    with c.sesiones.begin() as s:
        original = s.get(SesionProgramadaModel, c.sesion)
        segunda = SesionProgramadaModel(espacio_academico_id=original.espacio_academico_id,
                                        version_caso_id=original.version_caso_id, docente_id=original.docente_id,
                                        fecha_inicio=original.fecha_inicio, fecha_fin=original.fecha_fin,
                                        tiempo_maximo_minutos=20)
        s.add(segunda); s.flush()
        s.add(ConvocatoriaModel(sesion_id=segunda.id, estudiante_id=c.uuid,
                               codigo_hash=s.get(ConvocatoriaModel, c.convocatoria).codigo_hash))
    assert login(c).status_code == 503


@pytest.mark.parametrize("estado", ["SIN_INICIAR", "EN_CURSO", "FINALIZADO"])
def test_autenticacion_no_inventa_ventana_de_ingreso(login_sql, estado):
    c = login_sql
    with c.sesiones.begin() as s: s.get(SesionProgramadaModel, c.sesion).estado = estado
    assert login(c).status_code == 200


def test_retirar_convocatoria_revoca_alcance_pero_no_identidad(login_sql):
    c = login_sql
    token = login(c).json()["access_token"]
    with c.sesiones.begin() as s: s.get(ConvocatoriaModel, c.convocatoria).estado = "RETIRADA"
    assert contexto(c, token).status_code == 403
    assert c.cliente.get(BASE + "/me", headers={"Authorization": "Bearer " + token}).status_code == 200


@pytest.mark.parametrize("alteracion", ["expirado", "firma", "manipulado"])
def test_jwt_no_valido_no_autoriza(login_sql, alteracion):
    c = login_sql
    token = login(c).json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    if alteracion == "expirado":
        claims.update(iat=1000, nbf=1000, exp=1060)
        token = jwt.encode(claims, SECRETO, algorithm="HS256")
    elif alteracion == "firma": token = jwt.encode(claims, "otra-clave-prueba-" * 3, algorithm="HS256")
    else:
        partes = token.split(".")
        claims["convocatoria_id"] = str(c.convocatoria_ajena)
        partes[1] = jwt.encode(claims, SECRETO, algorithm="HS256").split(".")[1]
        token = ".".join(partes)
    assert c.cliente.get(BASE + "/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_sin_contexto_no_impide_identidad_avisos_pero_deniega_alcance(login_sql):
    c = login_sql
    token = c.tokens.emitir(str(c.propio))
    h = {"Authorization": "Bearer " + token}
    assert c.cliente.get(BASE + "/me", headers=h).status_code == 200
    assert c.cliente.get(f"/scheduling/notificaciones?destinatario_id={c.uuid}", headers=h).status_code == 200
    assert contexto(c, token).status_code == 403


def test_cliente_no_puede_elegir_claims_en_login(login_sql):
    c = login_sql
    assert login(c, id_convocatoria=str(c.convocatoria_ajena)).status_code == 422


def test_token_de_una_convocatoria_no_autoriza_otra_del_mismo_estudiante(login_sql):
    c = login_sql
    token = login(c).json()["access_token"]
    with c.sesiones.begin() as s:
        original = s.get(SesionProgramadaModel, c.sesion)
        segunda = SesionProgramadaModel(espacio_academico_id=original.espacio_academico_id,
                                        version_caso_id=original.version_caso_id, docente_id=original.docente_id,
                                        fecha_inicio=original.fecha_inicio, fecha_fin=original.fecha_fin,
                                        tiempo_maximo_minutos=20)
        s.add(segunda); s.flush()
        otra = crear_convocatoria(s, sesion_id=segunda.id, estudiante_id=c.uuid)
        otra_id, otro_codigo = otra.convocatoria_id, otra.codigo_acceso
    assert contexto(c, token, otra_id).status_code == 403
    nuevo = login(c, codigo_convocatoria=otro_codigo).json()["access_token"]
    assert contexto(c, nuevo, otra_id).status_code == 200


def test_busqueda_correo_usa_casefold_tambien_para_unicode(login_sql):
    c = login_sql
    correo = f"Straße{c.propio}@universidad.test"
    with c.sesiones.begin() as s:
        s.get(UsuarioORM, c.propio).correo = correo
    assert login(c, correo=correo.casefold()).status_code == 200


def test_fallo_fabrica_sesion_login_no_concede_acceso(login_sql):
    c = login_sql
    def fallo(): raise SQLAlchemyError("detalle SQL privado")
    c.app.dependency_overrides[dependencies.obtener_fabrica_sesiones_login] = lambda: fallo
    respuesta = login(c)
    assert respuesta.status_code == 503 and "privado" not in respuesta.text


def test_sin_dominios_configurados_no_abre_sesion(login_sql):
    c = login_sql
    c.app.dependency_overrides[dependencies.obtener_dominios_login] = lambda: ()
    def inesperado(): raise AssertionError("No debe abrir Session")
    c.app.dependency_overrides[dependencies.obtener_fabrica_sesiones_login] = lambda: inesperado
    assert login(c).status_code == 503


def test_contrasenas_existentes_siguen_verificandose_sin_cambio_de_flujo():
    hasheador = obtener_hasheador()
    clave = "clave-exclusiva-regresion-no-productiva"
    guardado = hasheador.hash(clave)
    assert hasheador.verify(clave, guardado)
    assert not hasheador.verify("incorrecta", guardado)
