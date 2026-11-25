"""Pruebas de recuperación de contraseña por correo y configuración STARTTLS para Gmail."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.modules.identity.api.dependencies import (
    obtener_fabrica_autenticacion_personal,
    obtener_fabrica_sesiones_login,
    obtener_fabrica_tokens,
    obtener_remitente_codigo_recuperacion,
)
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.infrastructure.credentials import (
    CredencialesPersonalSQLAlchemy,
    obtener_hasheador,
)
from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM
from app.modules.identity.infrastructure.password_recovery import MAX_INTENTOS_CODIGO_RECUPERACION
from app.modules.identity.infrastructure.password_reset_models import RecuperacionContrasenaORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.scheduling.infrastructure import mail_delivery


@pytest.fixture()
def entorno_recovery():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk_on(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tablas = [
        RolORM.__table__,
        PermisoORM.__table__,
        RolPermisoORM.__table__,
        UsuarioORM.__table__,
        RecuperacionContrasenaORM.__table__,
    ]
    Base.metadata.create_all(engine, tables=tablas)
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
        s.add_all(
            [
                UsuarioORM(
                    id_usuario=10,
                    id_rol=1,
                    nombre="Docente Prueba",
                    correo="docente@sps.edu.co",
                    clave_hash=hasheador.hash("ClaveVieja123!"),
                    activo=True,
                ),
                UsuarioORM(
                    id_usuario=11,
                    id_rol=2,
                    nombre="Estudiante Inactivo",
                    correo="inactivo@gmail.com",
                    clave_hash=hasheador.hash("ClaveVieja123!"),
                    activo=False,
                ),
            ]
        )

    tokens = TokensJWT("clave-pruebas-recuperacion-otp-" * 2, "sps-test", "sps-test")
    correos_enviados: list[dict[str, str]] = []

    app = FastAPI()
    app.include_router(identity_router)

    @contextmanager
    def _sesion_ctx():
        db = fabrica()
        try:
            yield db
        finally:
            db.close()

    def _auth_personal():
        def _build():
            db = fabrica()
            return ServicioAutenticacion(
                RepositorioUsuariosSQLAlchemy(db),
                None,
                tokens,
                (),
                credenciales_personal=CredencialesPersonalSQLAlchemy(db),
            )

        return _build

    app.dependency_overrides[obtener_fabrica_sesiones_login] = lambda: _sesion_ctx
    app.dependency_overrides[obtener_fabrica_tokens] = lambda: lambda: tokens
    app.dependency_overrides[obtener_fabrica_autenticacion_personal] = _auth_personal
    app.dependency_overrides[obtener_remitente_codigo_recuperacion] = (
        lambda: lambda *, correo, nombre, codigo: correos_enviados.append(
            {"correo": correo, "nombre": nombre, "codigo": codigo}
        )
    )

    with TestClient(app) as client:
        yield client, fabrica, correos_enviados

    engine.dispose()


def test_recuperacion_contrasena_completa_y_anti_enumeracion(entorno_recovery):
    client, _, correos = entorno_recovery

    # Correo inexistente o inactivo no revela existencia ni envía código
    r_no = client.post(
        "/api/v1/identity/auth/recuperar-contrasena/solicitar",
        json={"correo": "nadie@gmail.com"},
    )
    r_inact = client.post(
        "/api/v1/identity/auth/recuperar-contrasena/solicitar",
        json={"correo": "inactivo@gmail.com"},
    )
    assert r_no.status_code == 200 and r_inact.status_code == 200
    assert len(correos) == 0

    # Solicitud válida envía OTP de 6 dígitos
    r_sol = client.post(
        "/api/v1/identity/auth/recuperar-contrasena/solicitar",
        json={"correo": "docente@sps.edu.co"},
    )
    assert r_sol.status_code == 200
    assert len(correos) == 1
    codigo = correos[0]["codigo"]
    assert len(codigo) == 6 and codigo.isdigit()
    repetida = client.post(
        "/api/v1/identity/auth/recuperar-contrasena/solicitar",
        json={"correo": "docente@sps.edu.co"},
    )
    assert repetida.json() == r_sol.json() == r_no.json()
    assert len(correos) == 1

    # Código incorrecto falla con 401 y no cambia la contraseña
    r_bad = client.post(
        "/api/v1/identity/auth/recuperar-contrasena/confirmar",
        json={
            "correo": "docente@sps.edu.co",
            "codigo": "000000" if codigo != "000000" else "999999",
            "nueva_clave": "ClaveNueva456!",
        },
    )
    assert r_bad.status_code == 401

    # Confirmar con código válido actualiza contraseña y limpia OTP
    r_ok = client.post(
        "/api/v1/identity/auth/recuperar-contrasena/confirmar",
        json={
            "correo": "docente@sps.edu.co",
            "codigo": codigo,
            "nueva_clave": "ClaveNueva456!",
        },
    )
    assert r_ok.status_code == 200, r_ok.text

    # Código no se puede reutilizar
    assert (
        client.post(
            "/api/v1/identity/auth/recuperar-contrasena/confirmar",
            json={"correo": "docente@sps.edu.co", "codigo": codigo, "nueva_clave": "OtraClave789!"},
        ).status_code
        == 401
    )

    # Clave anterior falla; clave nueva ingresa
    assert (
        client.post(
            "/api/v1/identity/auth/personal",
            json={"correo": "docente@sps.edu.co", "clave": "ClaveVieja123!"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/identity/auth/personal",
            json={"correo": "docente@sps.edu.co", "clave": "ClaveNueva456!"},
        ).status_code
        == 200
    )


def test_recuperacion_bloquea_tras_max_intentos_y_expiracion(entorno_recovery):
    client, fabrica, correos = entorno_recovery
    client.post(
        "/api/v1/identity/auth/recuperar-contrasena/solicitar",
        json={"correo": "docente@sps.edu.co"},
    )
    codigo = correos[-1]["codigo"]
    malo = "111111" if codigo != "111111" else "222222"

    for _ in range(MAX_INTENTOS_CODIGO_RECUPERACION):
        assert (
            client.post(
                "/api/v1/identity/auth/recuperar-contrasena/confirmar",
                json={"correo": "docente@sps.edu.co", "codigo": malo, "nueva_clave": "ClaveNueva456!"},
            ).status_code
            == 401
        )

    assert (
        client.post(
            "/api/v1/identity/auth/recuperar-contrasena/confirmar",
            json={"correo": "docente@sps.edu.co", "codigo": codigo, "nueva_clave": "ClaveNueva456!"},
        ).status_code
        == 401
    )

    # Reenvío después de la pausa y expiración.
    with fabrica.begin() as s:
        fila = s.scalar(select(RecuperacionContrasenaORM).where(RecuperacionContrasenaORM.id_usuario == 10))
        fila.solicitado_en = datetime.now(UTC) - timedelta(minutes=2)
    client.post(
        "/api/v1/identity/auth/recuperar-contrasena/solicitar",
        json={"correo": "docente@sps.edu.co"},
    )
    assert len(correos) == 2
    codigo2 = correos[-1]["codigo"]
    with fabrica.begin() as s:
        fila = s.scalar(select(RecuperacionContrasenaORM).where(RecuperacionContrasenaORM.id_usuario == 10))
        fila.expira_en = datetime.now(UTC) - timedelta(seconds=10)

    assert (
        client.post(
            "/api/v1/identity/auth/recuperar-contrasena/confirmar",
            json={"correo": "docente@sps.edu.co", "codigo": codigo2, "nueva_clave": "ClaveNueva456!"},
        ).status_code
        == 401
    )


def test_configuracion_correo_permite_gmail_starttls_con_url_local(monkeypatch):
    settings = Settings(
        _env_file=None,
        scheduling_mail_enabled=True,
        scheduling_mail_host="smtp.gmail.com",
        scheduling_mail_port=587,
        scheduling_mail_tls="STARTTLS",
        scheduling_mail_from="proyecto.sps@gmail.com",
        scheduling_mail_username="proyecto.sps@gmail.com",
        scheduling_mail_password=SecretStr("abcd efgh ijkl mnop"),
        scheduling_mail_encryption_key=SecretStr(Fernet.generate_key().decode()),
        scheduling_mail_public_url="http://localhost:4200",
    )
    monkeypatch.setattr(mail_delivery, "get_settings", lambda: settings)
    cfg = mail_delivery.configuracion_correo()
    assert cfg is not None
    assert cfg.host == "smtp.gmail.com"
    assert cfg.tls == "STARTTLS"
    assert cfg.url_publica == "http://localhost:4200"
    assert cfg.password == "abcdefghijklmnop"

    settings.scheduling_mail_public_url = "http://inseguro.example.com"
    from app.modules.identity.domain.errors import IntegracionPendiente

    with pytest.raises(IntegracionPendiente):
        mail_delivery.configuracion_correo()
