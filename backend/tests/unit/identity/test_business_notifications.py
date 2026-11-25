"""Pruebas de notificaciones transaccionales de negocio por correo electrónico."""

from contextlib import contextmanager
import copy
import uuid

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.modules.cases.api.dependencies import exigir_permiso_creacion_configurado
from app.modules.cases.api.router import router as cases_router
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
from app.modules.identity.api.academic_dependencies import obtener_fabrica_sesiones_academicas
from app.modules.identity.api.dependencies import (
    construir_consulta_ambito,
    construir_repositorio_usuarios,
    obtener_fabrica_sesiones_login,
    obtener_fabrica_tokens,
    obtener_fabrica_usuarios,
    obtener_notificador_negocio,
    obtener_proxy_administracion,
)
from app.modules.identity.api.router import router as identity_router
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.services import ServicioAdministracionUsuarios
from app.modules.identity.infrastructure import business_notifications
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.models import PermisoORM, RolORM, RolPermisoORM, UsuarioORM, UsuarioPermisoORM
from app.modules.identity.infrastructure.onboarding_models import VerificacionPrimerIngresoORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.identity.infrastructure.teacher_directory import ConsultaDocentesSQLAlchemy
from app.modules.identity.infrastructure.unit_of_work import UnidadTrabajoIdentitySQLAlchemy
from app.modules.scheduling.api.router import router as scheduling_router
from app.modules.scheduling.infrastructure import mail_delivery
from app.modules.scheduling.infrastructure.mail_delivery import ConfiguracionCorreo


@pytest.fixture()
def entorno_negocio():
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
        UsuarioPermisoORM.__table__,
        IdentidadAcademicaORM.__table__,
        VerificacionPrimerIngresoORM.__table__,
        GrupoAcademicoORM.__table__,
        GrupoEstudianteORM.__table__,
        CasoModel.__table__,
        VersionCasoModel.__table__,
        EscenarioModel.__table__,
        PreguntaModel.__table__,
        OpcionRespuestaModel.__table__,
        RubricaModel.__table__,
        CriterioRubricaModel.__table__,
        NivelRubricaModel.__table__,
        ValoracionOpcionModel.__table__,
    ]
    Base.metadata.create_all(engine, tables=tablas)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)

    hasheador = obtener_hasheador()
    docente_cases_uuid = uuid.uuid4()
    docente_sched_uuid = uuid.uuid4()

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
                    id_usuario=1,
                    id_rol=3,
                    nombre="Admin SPS",
                    correo="admin@sps.edu.co",
                    clave_hash=hasheador.hash("Admin123456!"),
                    activo=True,
                ),
                UsuarioORM(
                    id_usuario=2,
                    id_rol=1,
                    nombre="Prof. Camila Ríos",
                    correo="camila.rios@sps.edu.co",
                    clave_hash=hasheador.hash("Docente123456!"),
                    activo=True,
                ),
            ]
        )
        s.flush()
        s.add_all(
            [
                IdentidadAcademicaORM(
                    sistema="CASES",
                    id_academico=docente_cases_uuid,
                    id_usuario=2,
                ),
                IdentidadAcademicaORM(
                    sistema="SCHEDULING",
                    id_academico=docente_sched_uuid,
                    id_usuario=2,
                ),
            ]
        )

    tokens = TokensJWT("clave-pruebas-notificaciones-negocio-" * 2, "sps-test", "sps-test")
    enviados: list[dict[str, str]] = []

    def _capturar_notificacion(*, correo: str, asunto: str, generar_cuerpo) -> None:
        enviados.append(
            {
                "correo": correo,
                "asunto": asunto,
                "cuerpo": generar_cuerpo("http://localhost:4200"),
            }
        )

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

    def _proxy_admin() -> ProxyAdministracionUsuarios:
        servicio = ServicioAdministracionUsuarios(
            lambda: UnidadTrabajoIdentitySQLAlchemy(
                usuarios=construir_repositorio_usuarios,
                sesiones=fabrica,
            ),
            hasheador.hash,
        )
        return ProxyAdministracionUsuarios(
            lambda: servicio,
            ServicioAutorizacion(construir_consulta_ambito),
            ConsultaDocentesSQLAlchemy(lambda: fabrica()),
        )

    app = FastAPI()
    app.include_router(identity_router)
    app.include_router(scheduling_router)
    app.include_router(cases_router)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[obtener_fabrica_sesiones_login] = lambda: _sesion_ctx
    app.dependency_overrides[obtener_fabrica_sesiones_academicas] = lambda: (lambda: fabrica())
    app.dependency_overrides[obtener_fabrica_tokens] = lambda: (lambda: tokens)
    app.dependency_overrides[obtener_fabrica_usuarios] = lambda: _ConsultaUsuarioTest
    app.dependency_overrides[obtener_proxy_administracion] = _proxy_admin
    app.dependency_overrides[exigir_permiso_creacion_configurado] = lambda: None
    app.dependency_overrides[obtener_notificador_negocio] = lambda: _capturar_notificacion

    with TestClient(app) as client:
        yield client, enviados

    engine.dispose()


def _login_personal(client: TestClient, correo: str, clave: str) -> dict[str, str]:
    r = client.post("/api/v1/identity/auth/personal", json={"correo": correo, "clave": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _payload_caso_base(*, con_rubrica: bool, sufijo_escena: str = "inicial") -> dict[str, object]:
    payload: dict[str, object] = {
        "case": {
            "nombre": "Dilema de Obediencia",
            "desarrolloSituacional": "Desarrollo situacional.",
            "contextoHistoria": "Contexto histórico.",
            "tiempoEstimadoMin": 40,
        },
        "scenarios": [
            {
                "orden": 1,
                "contextoSituacional": f"Escenario {sufijo_escena}.",
                "questions": [
                    {
                        "orden": 1,
                        "enunciado": "¿Cuál es la decisión ética?",
                        "options": [
                            {
                                "orden": 1,
                                "texto": "Opción A",
                                "esCorrecta": True,
                                "justificacion": "Fundamento ético.",
                                "valoraciones": {"Juicio": 5} if con_rubrica else {},
                            },
                            {
                                "orden": 2,
                                "texto": "Opción B",
                                "esCorrecta": False,
                                "justificacion": "Presión grupal.",
                                "valoraciones": {"Juicio": 1} if con_rubrica else {},
                            },
                        ],
                    }
                ],
            }
        ],
        "rubric": None,
    }
    if con_rubrica:
        payload["rubric"] = {
            "nombre": "Rúbrica Clínica Ética",
            "versionRegla": "1.0",
            "criterios": [
                {
                    "nombre": "Juicio",
                    "peso": 100,
                    "niveles": [
                        {"nombre": "Sobresaliente", "puntaje": 5, "descriptor": "Argumentación sólida."}
                    ],
                }
            ],
        }
    return payload


def test_registro_estudiante_y_docente_envia_notificacion_por_correo(entorno_negocio):
    client, enviados = entorno_negocio
    admin_hdr = _login_personal(client, "admin@sps.edu.co", "Admin123456!")

    r_est = client.post(
        "/api/v1/identity/usuarios",
        headers=admin_hdr,
        json={
            "nombre": "Sofía Vargas",
            "correo": "sofia.vargas@gmail.com",
            "rol": "ESTUDIANTE",
            "clave": "ClaveEst2026!",
            "activo": True,
            "crear_identidades_academicas": True,
        },
    )
    assert r_est.status_code == 201, r_est.text
    assert len(enviados) == 1
    assert enviados[0]["correo"] == "sofia.vargas@gmail.com"
    assert "Cuenta estudiantil registrada" in enviados[0]["asunto"]
    assert "primer inicio de sesión" in enviados[0]["cuerpo"]
    assert "http://localhost:4200" in enviados[0]["cuerpo"]

    r_doc = client.post(
        "/api/v1/identity/docentes",
        headers=admin_hdr,
        json={
            "correo": "nuevo.docente@gmail.com",
            "nombre": "Prof. Andrés Mejía",
            "clave": "ClaveDoc2026!",
        },
    )
    assert r_doc.status_code == 201, r_doc.text
    assert len(enviados) == 2
    assert enviados[1]["correo"] == "nuevo.docente@gmail.com"
    assert "docente registrada" in enviados[1]["asunto"]
    assert "Prof. Andrés Mejía" in enviados[1]["cuerpo"]


def test_matricula_estudiante_en_grupo_envia_notificacion_con_detalles_del_grupo(entorno_negocio):
    client, enviados = entorno_negocio
    admin_hdr = _login_personal(client, "admin@sps.edu.co", "Admin123456!")
    docente_hdr = _login_personal(client, "camila.rios@sps.edu.co", "Docente123456!")

    r_est = client.post(
        "/api/v1/identity/usuarios",
        headers=admin_hdr,
        json={
            "nombre": "Mateo Pardo",
            "correo": "mateo.pardo@gmail.com",
            "rol": "ESTUDIANTE",
            "clave": "ClaveEst2026!",
            "activo": True,
            "crear_identidades_academicas": True,
        },
    )
    assert r_est.status_code == 201
    est_id = int(r_est.json()["id_usuario"])
    enviados.clear()

    r_grupo = client.post(
        "/scheduling/grupos",
        headers=docente_hdr,
        json={"nombre": "Psicología Social IV", "periodo": "2026-2"},
    )
    assert r_grupo.status_code == 201, r_grupo.text
    grupo_id = r_grupo.json()["id_grupo"]

    r_mat = client.post(
        f"/scheduling/grupos/{grupo_id}/estudiantes",
        headers=docente_hdr,
        json={"id_usuario": est_id},
    )
    assert r_mat.status_code == 200, r_mat.text
    assert len(enviados) == 1
    aviso = enviados[0]
    assert aviso["correo"] == "mateo.pardo@gmail.com"
    assert "Psicología Social IV" in aviso["asunto"]
    assert "2026-2" in aviso["cuerpo"]
    assert "Prof. Camila Ríos" in aviso["cuerpo"]


def test_docente_crea_caso_asigna_rubrica_y_publica_envia_notificaciones(entorno_negocio):
    client, enviados = entorno_negocio
    docente_hdr = _login_personal(client, "camila.rios@sps.edu.co", "Docente123456!")

    # 1. Crear borrador sin rúbrica
    r_crear = client.post(
        "/api/v1/cases",
        headers=docente_hdr,
        json=_payload_caso_base(con_rubrica=False),
    )
    assert r_crear.status_code == 201, r_crear.text
    version_id = r_crear.json()["version_id"]
    assert len(enviados) == 1
    assert enviados[0]["correo"] == "camila.rios@sps.edu.co"
    assert "Caso creado en SPS" in enviados[0]["asunto"]
    assert "sin rúbrica asignada" in enviados[0]["cuerpo"]

    # 2. Editar borrador todavía sin rúbrica -> no dispara aviso de rúbrica
    r_edit_sin = client.put(
        f"/api/v1/cases/{version_id}",
        headers=docente_hdr,
        json=_payload_caso_base(con_rubrica=False, sufijo_escena="actualizado"),
    )
    assert r_edit_sin.status_code == 200, r_edit_sin.text
    assert len(enviados) == 1

    # 3. Asignar rúbrica al borrador -> dispara aviso de rúbrica asignada
    payload_con_rubrica = _payload_caso_base(con_rubrica=True, sufijo_escena="con rúbrica")
    r_edit_rub = client.put(
        f"/api/v1/cases/{version_id}",
        headers=docente_hdr,
        json=payload_con_rubrica,
    )
    assert r_edit_rub.status_code == 200, r_edit_rub.text
    assert len(enviados) == 2
    assert "Rúbrica asignada al caso 'Dilema de Obediencia'" in enviados[1]["asunto"]
    assert "Rúbrica Clínica Ética" in enviados[1]["cuerpo"]
    assert "1 criterio(s)" in enviados[1]["cuerpo"]

    # 4. Guardar edición sin modificar la rúbrica -> no duplica aviso de rúbrica
    solo_texto = copy.deepcopy(payload_con_rubrica)
    solo_texto["scenarios"][0]["contextoSituacional"] = "Escenario ajustado sin cambiar rúbrica."  # type: ignore[index]
    r_edit_igual = client.put(
        f"/api/v1/cases/{version_id}",
        headers=docente_hdr,
        json=solo_texto,
    )
    assert r_edit_igual.status_code == 200, r_edit_igual.text
    assert len(enviados) == 2

    # 5. Configurar grafo mínimo y publicar caso -> dispara notificación de publicación
    detalle = client.get(f"/api/v1/cases/{version_id}", headers=docente_hdr).json()
    escena = detalle["escenarios"][0]
    r_grafo = client.put(
        f"/api/v1/cases/{version_id}/graph",
        headers=docente_hdr,
        json={
            "escenario_inicial_id": escena["id"],
            "transiciones": [
                {"opcion_id": o["id"], "tipo": "FIN"} for o in escena["preguntas"][0]["opciones"]
            ],
        },
    )
    assert r_grafo.status_code == 200, r_grafo.text

    r_pub = client.post(f"/api/v1/cases/{version_id}/publish", headers=docente_hdr)
    assert r_pub.status_code == 200, r_pub.text
    assert len(enviados) == 3
    assert "Caso publicado en SPS: Dilema de Obediencia (v1)" in enviados[2]["asunto"]
    assert "Rúbrica Clínica Ética" in enviados[2]["cuerpo"]

    # 6. Republicar versión -> dispara notificación de publicación v2
    r_repub = client.post(f"/api/v1/cases/{version_id}/republish", headers=docente_hdr)
    assert r_repub.status_code == 201, r_repub.text
    assert len(enviados) == 4
    assert "Caso publicado en SPS: Dilema de Obediencia (v2)" in enviados[3]["asunto"]

    # 7. Crear borrador con rúbrica desde el inicio -> menciona la rúbrica en el aviso de creación
    r_crear_rub = client.post(
        "/api/v1/cases",
        headers=docente_hdr,
        json=_payload_caso_base(con_rubrica=True),
    )
    assert r_crear_rub.status_code == 201, r_crear_rub.text
    assert len(enviados) == 5
    assert "También quedó asignada la rúbrica \"Rúbrica Clínica Ética\"" in enviados[4]["cuerpo"]


def test_correos_reservados_test_no_intentan_smtp_real(monkeypatch):
    enviados_reales: list[str] = []

    monkeypatch.setattr(business_notifications, "configuracion_correo", lambda: object())
    monkeypatch.setattr(
        business_notifications,
        "enviar_correo_directo",
        lambda *, destinatario, asunto, generar_cuerpo: enviados_reales.append(destinatario),
    )

    business_notifications.notificar_registro_usuario(
        correo="estudiante@universidad.test",
        nombre="Prueba",
        rol="ESTUDIANTE",
    )
    assert enviados_reales == []

    business_notifications.notificar_registro_usuario(
        correo="estudiante.real@gmail.com",
        nombre="Estudiante Real",
        rol="ESTUDIANTE",
    )
    assert enviados_reales == ["estudiante.real@gmail.com"]


def test_enviar_smtp_convocatoria_incluye_texto_claro_codigo_y_url(monkeypatch):
    capturados: list[dict[str, str]] = []

    monkeypatch.setattr(
        mail_delivery,
        "enviar_mensaje_smtp",
        lambda config, *, destinatario, asunto, cuerpo, message_id=None, codigo=None, transporte=None: capturados.append(
            {"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo, "codigo": codigo}
        ),
    )

    config = ConfiguracionCorreo(
        host="smtp.gmail.com",
        puerto=587,
        tls="STARTTLS",
        remitente="emisor@gmail.com",
        url_publica="http://localhost:4200",
        clave=Fernet.generate_key(),
    )
    mail_delivery.enviar_smtp(
        config,
        id_notificacion=uuid.uuid4(),
        payload={
            "tipo": "CONVOCATORIA",
            "correo": "alumno@gmail.com",
            "caso": "Dilema de Obediencia",
            "inicio": "2026-11-20T14:00:00+00:00",
            "mensaje": "Por favor conectarse 10 minutos antes.",
            "codigo": "SPS-9988-XY",
        },
    )

    assert len(capturados) == 1
    msg = capturados[0]
    assert msg["destinatario"] == "alumno@gmail.com"
    assert "Convocatoria académica SPS" in msg["asunto"]
    assert "Has sido convocado por tu docente a un caso de simulación en SPS." in msg["cuerpo"]
    assert "Caso: Dilema de Obediencia" in msg["cuerpo"]
    assert "Código individual: SPS-9988-XY" in msg["cuerpo"]
    assert "URL: http://localhost:4200" in msg["cuerpo"]
    assert msg["codigo"] == "SPS-9988-XY"


def test_plantilla_html_escapa_datos_y_destaca_el_codigo_del_sistema():
    from app.modules.scheduling.infrastructure.mail_templates import renderizar_correo

    url = "https://sps.universidad.test/login"
    html = renderizar_correo(
        "Convocatoria <SPS>",
        "Hola Ana & Luis,\n<b>Mensaje docente</b>\nCódigo individual: 123456",
        url,
        codigo="123456",
    )
    assert "Convocatoria &lt;SPS&gt;" in html
    assert "Hola Ana &amp; Luis," in html
    assert "&lt;b&gt;Mensaje docente&lt;/b&gt;" in html
    assert "[if mso]" in html
    assert "https://sps.universidad.test/logo-sps.png" in html
    assert f'href="{url}"' in html
    assert ">123456</p>" in html
    sin_codigo = renderizar_correo("Aviso", "Código individual: 123456", url)
    assert ">123456</p>" not in sin_codigo
