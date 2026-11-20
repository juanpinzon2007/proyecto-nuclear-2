"""Pruebas de flujo completo de verificación por correo únicamente en primer inicio de sesión estudiantil."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.modules.identity.api.dependencies import (
    obtener_fabrica_sesiones_login,
    obtener_fabrica_tokens,
    obtener_fabrica_usuarios,
    obtener_remitente_codigo_primer_ingreso,
)
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.api.users_management_router import router as users_admin_router
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM, UsuarioPermisoORM
from app.modules.identity.infrastructure.onboarding import MAX_INTENTOS_CODIGO_PRIMER_INGRESO
from app.modules.identity.infrastructure.onboarding_models import VerificacionPrimerIngresoORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.security import TokensJWT


@pytest.fixture()
def entorno_onboarding():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk_on(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tablas_identidad = [
        RolORM.__table__,
        PermisoORM.__table__,
        RolPermisoORM.__table__,
        UsuarioORM.__table__,
        UsuarioPermisoORM.__table__,
        IdentidadAcademicaORM.__table__,
        VerificacionPrimerIngresoORM.__table__,
    ]
    Base.metadata.create_all(engine, tables=tablas_identidad)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)

    hasheador = obtener_hasheador()
    with fabrica.begin() as s:
        s.add_all(
            [
                RolORM(id_rol=1, nombre="DOCENTE"),
                RolORM(id_rol=2, nombre="ESTUDIANTE"),
                RolORM(id_rol=3, nombre="ADMINISTRADOR"),
            ]
        )
        s.flush()
        s.add(
            UsuarioORM(
                id_usuario=1,
                id_rol=3,
                nombre="Admin Demo",
                correo="admin@sps.edu.co",
                clave_hash=hasheador.hash("Admin123456!"),
                activo=True,
            )
        )

    tokens = TokensJWT("clave-pruebas-primer-ingreso-otp-" * 2, "sps-test", "sps-test")
    correos_enviados: list[dict[str, str]] = []

    app = FastAPI()
    app.include_router(identity_router)
    app.include_router(users_admin_router, prefix="/api/v1/identity")

    @contextmanager
    def _sesion_ctx():
        db = fabrica()
        try:
            yield db
        finally:
            db.close()

    def _override_get_db():
        db = fabrica()
        try:
            yield db
        finally:
            db.close()

    class _ConsultaUsuarioTest:
        def obtener(self, id_usuario: str):
            with fabrica() as db:
                return RepositorioUsuariosSQLAlchemy(db).obtener(id_usuario)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[obtener_fabrica_sesiones_login] = lambda: _sesion_ctx
    app.dependency_overrides[obtener_fabrica_tokens] = lambda: lambda: tokens
    app.dependency_overrides[obtener_fabrica_usuarios] = lambda: _ConsultaUsuarioTest
    app.dependency_overrides[obtener_remitente_codigo_primer_ingreso] = (
        lambda: lambda *, correo, nombre, codigo: correos_enviados.append(
            {"correo": correo, "nombre": nombre, "codigo": codigo}
        )
    )

    with TestClient(app) as client:
        yield client, fabrica, tokens, correos_enviados

    engine.dispose()


def test_primer_ingreso_requiere_codigo_correo_una_sola_vez(entorno_onboarding):
    client, fabrica, tokens, correos = entorno_onboarding

    # 1. Admin inicia sesión y crea al estudiante nuevo
    login_admin = client.post(
        "/api/v1/identity/auth/personal",
        json={"correo": "admin@sps.edu.co", "clave": "Admin123456!"},
    )
    assert login_admin.status_code == 200, login_admin.text
    admin_hdr = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

    r_est = client.post(
        "/api/v1/identity/usuarios",
        headers=admin_hdr,
        json={
            "nombre": "Laura Estudiante",
            "correo": "laura.est@unihumboldt.edu.co",
            "rol": "ESTUDIANTE",
            "clave": "ClaveInicial2026!",
            "activo": True,
            "crear_identidades_academicas": True,
        },
    )
    assert r_est.status_code == 201, r_est.text
    assert r_est.json()["primer_ingreso_verificado"] is False
    assert len(correos) == 0

    # /auth/personal conserva su regla estricta: rechaza cuentas de estudiante
    assert (
        client.post(
            "/api/v1/identity/auth/personal",
            json={"correo": "laura.est@unihumboldt.edu.co", "clave": "ClaveInicial2026!"},
        ).status_code
        == 401
    )

    # Contraseña errónea nunca envía OTP
    assert (
        client.post(
            "/api/v1/identity/auth/estudiantes/acceso",
            json={"correo": "laura.est@unihumboldt.edu.co", "clave": "ClaveMala!"},
        ).status_code
        == 401
    )
    assert len(correos) == 0

    # 2. Primer inicio de sesión correcto envía código al correo y exige verificar
    r_acc1 = client.post(
        "/api/v1/identity/auth/estudiantes/acceso",
        json={"correo": "laura.est@unihumboldt.edu.co", "clave": "ClaveInicial2026!"},
    )
    assert r_acc1.status_code == 200, r_acc1.text
    datos1 = r_acc1.json()
    assert datos1["requiere_verificacion"] is True
    assert datos1["access_token"] is None
    assert len(correos) == 1
    codigo_enviado = correos[0]["codigo"]
    assert len(codigo_enviado) == 6 and codigo_enviado.isdigit()

    # Código incorrecto devuelve 401
    r_bad = client.post(
        "/api/v1/identity/auth/estudiantes/verificar-primer-ingreso",
        json={"correo": "laura.est@unihumboldt.edu.co", "codigo": "000000" if codigo_enviado != "000000" else "999999"},
    )
    assert r_bad.status_code == 401

    # 3. Código correcto verifica al estudiante permanentemente y entrega JWT
    r_ok = client.post(
        "/api/v1/identity/auth/estudiantes/verificar-primer-ingreso",
        json={"correo": "laura.est@unihumboldt.edu.co", "codigo": codigo_enviado},
    )
    assert r_ok.status_code == 200, r_ok.text
    tok = r_ok.json()["access_token"]
    assert tokens.verificar(tok).id_convocatoria is None
    me = client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["roles"] == ["ESTUDIANTE"]

    # No puede reutilizar el mismo código después de verificar
    assert (
        client.post(
            "/api/v1/identity/auth/estudiantes/verificar-primer-ingreso",
            json={"correo": "laura.est@unihumboldt.edu.co", "codigo": codigo_enviado},
        ).status_code
        == 401
    )

    # 4. Segundo inicio de sesión entra directo SIN código ni envío de correo adicional
    r_acc2 = client.post(
        "/api/v1/identity/auth/estudiantes/acceso",
        json={"correo": "laura.est@unihumboldt.edu.co", "clave": "ClaveInicial2026!"},
    )
    assert r_acc2.status_code == 200, r_acc2.text
    assert r_acc2.json()["requiere_verificacion"] is False
    assert r_acc2.json()["access_token"] is not None
    assert len(correos) == 1  # No se envió ningún otro correo

    # En consola Admin ahora aparece como verificado
    listado = client.get("/api/v1/identity/usuarios", headers=admin_hdr).json()["usuarios"]
    laura = next(u for u in listado if u["correo"] == "laura.est@unihumboldt.edu.co")
    assert laura["primer_ingreso_verificado"] is True


def test_codigo_bloqueado_tras_max_intentos_o_vencimiento(entorno_onboarding):
    client, fabrica, _, correos = entorno_onboarding
    login_admin = client.post(
        "/api/v1/identity/auth/personal",
        json={"correo": "admin@sps.edu.co", "clave": "Admin123456!"},
    )
    admin_hdr = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
    r_est = client.post(
        "/api/v1/identity/usuarios",
        headers=admin_hdr,
        json={
            "nombre": "Mateo Limite",
            "correo": "mateo.lim@unihumboldt.edu.co",
            "rol": "ESTUDIANTE",
            "clave": "ClaveInicial2026!",
            "activo": True,
        },
    )
    uid = int(r_est.json()["id_usuario"])

    client.post(
        "/api/v1/identity/auth/estudiantes/acceso",
        json={"correo": "mateo.lim@unihumboldt.edu.co", "clave": "ClaveInicial2026!"},
    )
    codigo = correos[-1]["codigo"]
    malo = "000001" if codigo != "000001" else "000002"

    for _ in range(MAX_INTENTOS_CODIGO_PRIMER_INGRESO):
        assert (
            client.post(
                "/api/v1/identity/auth/estudiantes/verificar-primer-ingreso",
                json={"correo": "mateo.lim@unihumboldt.edu.co", "codigo": malo},
            ).status_code
            == 401
        )

    # Incluso con el código original queda invalidado tras agotar intentos
    assert (
        client.post(
            "/api/v1/identity/auth/estudiantes/verificar-primer-ingreso",
            json={"correo": "mateo.lim@unihumboldt.edu.co", "codigo": codigo},
        ).status_code
        == 401
    )

    # Reenviar genera un nuevo código válido; probar también expiración temporal
    client.post(
        "/api/v1/identity/auth/estudiantes/acceso",
        json={"correo": "mateo.lim@unihumboldt.edu.co", "clave": "ClaveInicial2026!"},
    )
    codigo_nuevo = correos[-1]["codigo"]
    with fabrica.begin() as s:
        fila = s.scalar(select(VerificacionPrimerIngresoORM).where(VerificacionPrimerIngresoORM.id_usuario == uid))
        fila.expira_en = datetime.now(UTC) - timedelta(seconds=5)

    assert (
        client.post(
            "/api/v1/identity/auth/estudiantes/verificar-primer-ingreso",
            json={"correo": "mateo.lim@unihumboldt.edu.co", "codigo": codigo_nuevo},
        ).status_code
        == 401
    )
