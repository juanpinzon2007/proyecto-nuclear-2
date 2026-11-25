"""Prueba integral end-to-end contra PostgreSQL 17 real cubriendo RF-01..RF-27 sin overrides ni mocks."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel
from tests.integration.test_admin_bootstrap import inicializar, lab  # noqa: F401
from tests.scheduling_mail_support import codigo_de_prueba


def _login_personal(client: TestClient, correo: str, clave: str) -> dict[str, str]:
    r = client.post("/api/v1/identity/auth/personal", json={"correo": correo, "clave": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _login_estudiante(client: TestClient, correo: str, codigo: str) -> dict[str, str]:
    r = client.post("/api/v1/identity/auth/estudiantes", json={"correo": correo, "codigo_convocatoria": codigo})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_flujo_completo_admin_docente_estudiante_y_rubrica_ponderada(lab, monkeypatch, cola_convocatorias):
    inicializar(lab)
    monkeypatch.setenv("IDENTITY_INSTITUTIONAL_DOMAINS", '["universidad.test"]')
    monkeypatch.setenv("PARTICIPATION_TIMESTAMP_ZONE", "America/Bogota")
    monkeypatch.setenv("ACADEMIC_RUNTIME_SCOPE", "LABORATORIO")
    get_settings.cache_clear()

    with TestClient(app) as client:
        h_admin = _login_personal(client, lab.correo, lab.clave)

        # RF-03: Admin crea Docente con permiso individual CREAR_CASOS + crea Estudiante con UUID automáticos
        clave_doc = "DocentePass2026!"
        r_doc = client.post(
            "/api/v1/identity/usuarios",
            headers=h_admin,
            json={
                "nombre": "Dra. Elena Torres",
                "correo": "elena.torres@universidad.test",
                "rol": "DOCENTE",
                "clave": clave_doc,
                "activo": True,
                "permisos_individuales": {"CREAR_CASOS": True},
                "crear_identidades_academicas": True,
            },
        )
        assert r_doc.status_code == 201, r_doc.text
        doc_info = r_doc.json()
        assert "CREAR_CASOS" in doc_info["permisos_efectivos"]
        assert doc_info["identidad_cases"] and doc_info["identidad_scheduling"]

        r_est = client.post(
            "/api/v1/identity/usuarios",
            headers=h_admin,
            json={
                "nombre": "Mateo Estudiante",
                "correo": "mateo.est@universidad.test",
                "rol": "ESTUDIANTE",
                "activo": True,
                "crear_identidades_academicas": True,
            },
        )
        assert r_est.status_code == 201, r_est.text
        est_info = r_est.json()
        est_uid = int(est_info["id_usuario"])

        # RF-02: Admin bloqueado de rutas exclusivas docentes? Probamos endpoint de casos con admin -> 403
        assert client.get("/api/v1/cases", headers=h_admin).status_code == 403

        # Login Docente y validación de permisos efectivos en /me
        h_doc = _login_personal(client, "elena.torres@universidad.test", clave_doc)
        me_doc = client.get("/api/v1/identity/me", headers=h_doc).json()
        assert "CREAR_CASOS" in me_doc["permisos"]

        # RF-04: Crear Espacio y autorizar explícitamente + Crear Grupo + Matricular Estudiante
        esp = client.post("/scheduling/espacios", headers=h_doc, json={"nombre": "Sala Bioética 1"}).json()
        r_aut = client.post(f"/scheduling/espacios/{esp['id']}/autorizar", headers=h_doc)
        assert r_aut.status_code == 200, r_aut.text

        grp = client.post(
            "/scheduling/grupos",
            headers=h_doc,
            json={"nombre": "Grupo Piloto", "periodo": "2026-2"},
        ).json()
        r_mat = client.post(
            f"/scheduling/grupos/{grp['id_grupo']}/estudiantes",
            headers=h_doc,
            json={"id_usuario": est_uid},
        )
        assert r_mat.status_code == 200, r_mat.text
        assert len(r_mat.json()["estudiantes"]) == 1

        # RF-05..09, RF-17: Crear caso con Rúbrica Ponderada RUBRICA_V1 (60% + 40% = 100%)
        payload_caso = {
            "case": {
                "nombre": "Dilema Clínico Ponderado",
                "desarrolloSituacional": "Paciente solicita reserva de diagnóstico genético.",
                "contextoHistoria": "Hospital Universitario.",
                "tiempoEstimadoMin": 30,
            },
            "rubric": {
                "nombre": "Rúbrica Ponderada Bioética",
                "versionRegla": "RUBRICA_V1",
                "criterios": [
                    {
                        "nombre": "Confidencialidad",
                        "peso": 60,
                        "niveles": [
                            {"nombre": "Inicial", "puntaje": 0, "descriptor": "Sin resguardo"},
                            {"nombre": "Sobresaliente", "puntaje": 80, "descriptor": "Resguardo estricto"},
                        ],
                    },
                    {
                        "nombre": "Comunicación",
                        "peso": 40,
                        "niveles": [
                            {"nombre": "Inicial", "puntaje": 0, "descriptor": "Deficiente"},
                            {"nombre": "Sobresaliente", "puntaje": 80, "descriptor": "Empática"},
                        ],
                    },
                ],
            },
            "scenarios": [
                {
                    "orden": 1,
                    "contextoSituacional": "Escena 1: Entrevista inicial.",
                    "questions": [
                        {
                            "orden": 1,
                            "enunciado": "¿Cómo respondes al familiar?",
                            "options": [
                                {
                                    "orden": 1,
                                    "texto": "Resguardar secreto profesional y ofrecer cita conjunta.",
                                    "esCorrecta": True,
                                    "justificacion": "Cumple el principio ético de confidencialidad.",
                                    "valoraciones": {"Confidencialidad": 100, "Comunicación": 100},
                                },
                                {
                                    "orden": 2,
                                    "texto": "Entregar historia clínica al familiar sin permiso.",
                                    "esCorrecta": False,
                                    "justificacion": "Viola reserva clínica.",
                                    "valoraciones": {"Confidencialidad": 0, "Comunicación": 50},
                                },
                            ],
                        }
                    ],
                },
                {
                    "orden": 2,
                    "contextoSituacional": "Escena 2: Cierre de plan.",
                    "questions": [
                        {
                            "orden": 1,
                            "enunciado": "¿Qué seguimiento propones?",
                            "options": [
                                {
                                    "orden": 1,
                                    "texto": "Acordar acompañamiento psicológico y entrega directa.",
                                    "esCorrecta": True,
                                    "justificacion": "Acompañamiento integral.",
                                    "valoraciones": {"Confidencialidad": 100, "Comunicación": 100},
                                },
                                {
                                    "orden": 2,
                                    "texto": "Cerrar caso sin indicaciones.",
                                    "esCorrecta": False,
                                    "justificacion": "Omite deber de cuidado.",
                                    "valoraciones": {"Confidencialidad": 0, "Comunicación": 0},
                                },
                            ],
                        }
                    ],
                },
            ],
        }
        v_creada = client.post("/api/v1/cases", headers=h_doc, json=payload_caso)
        assert v_creada.status_code == 201, v_creada.text
        vid = v_creada.json()["version_id"]

        detalle = client.get(f"/api/v1/cases/{vid}", headers=h_doc).json()
        e1, e2 = detalle["escenarios"][0], detalle["escenarios"][1]
        q1, q2 = e1["preguntas"][0], e2["preguntas"][0]
        r_grafo = client.put(
            f"/api/v1/cases/{vid}/graph",
            headers=h_doc,
            json={
                "escenario_inicial_id": e1["id"],
                "transiciones": [
                    {"opcion_id": q1["opciones"][0]["id"], "tipo": "ESCENA", "destino_id": e2["id"]},
                    {"opcion_id": q1["opciones"][1]["id"], "tipo": "ESCENA", "destino_id": e2["id"]},
                    {"opcion_id": q2["opciones"][0]["id"], "tipo": "FIN"},
                    {"opcion_id": q2["opciones"][1]["id"], "tipo": "FIN"},
                ],
            },
        )
        assert r_grafo.status_code == 200, r_grafo.text
        assert client.post(f"/api/v1/cases/{vid}/publish", headers=h_doc).status_code == 200

        # RF-18, RF-20, RF-21: Programar sesión + Editar lugar (dispara notificación CAMBIO_SESION) + Iniciar sesión
        ahora = datetime.now(UTC)
        r_ses = client.post(
            "/scheduling/sesiones",
            headers=h_doc,
            json={
                "espacio_academico_id": esp["id"],
                "version_caso_id": vid,
                "fecha_inicio": (ahora - timedelta(minutes=2)).isoformat(),
                "fecha_fin": (ahora + timedelta(hours=2)).isoformat(),
                "tiempo_maximo_minutos": 20,
                "lugar": "Aula Virtual A",
                "grupo_id": grp["id_grupo"],
                "estudiantes_ids": [est_info["identidad_scheduling"]],
                "fecha_limite_ingreso": (ahora + timedelta(minutes=30)).isoformat(),
            },
        )
        assert r_ses.status_code == 201, r_ses.text
        ses_data = r_ses.json()
        sesion_id = ses_data["id"]
        conv_info = ses_data["convocatorias"][0]
        conv_id = conv_info["convocatoria_id"]
        codigo_acceso = codigo_de_prueba(lab.sesiones, conv_id)

        # Actualizar lugar -> notifica cambio RF-21
        assert client.patch(f"/scheduling/sesiones/{sesion_id}", headers=h_doc, json={"lugar": "Sala Clínica 2"}).status_code == 200
        # Iniciar sesión
        assert client.post(f"/scheduling/sesiones/{sesion_id}/estado", headers=h_doc, json={"accion": "iniciar"}).status_code == 200

        # RF-01: Login estudiante + portal mis-convocatorias + consentimiento
        h_est = _login_estudiante(client, "mateo.est@universidad.test", codigo_acceso)
        mis = client.get("/scheduling/mis-convocatorias", headers=h_est).json()
        assert len(mis) == 1 and mis[0]["caso_nombre"] == "Dilema Clínico Ponderado"
        assert any("Sala Clínica 2" in n for n in mis[0]["notificaciones_recientes"])

        ruta_consentimiento = f"/api/v1/simulacion/convocatorias/{conv_id}/consentimiento"
        with monkeypatch.context() as entorno:
            entorno.setenv("ACADEMIC_RUNTIME_SCOPE", "PRODUCCION")
            entorno.delenv("IDENTITY_CONSENT_APPROVAL_MANIFEST", raising=False)
            get_settings.cache_clear()
            assert client.get(ruta_consentimiento, headers=h_est).status_code == 503
            assert client.post(ruta_consentimiento, headers=h_est).status_code == 503
            with lab.sesiones() as s:
                assert s.scalar(sa.text("SELECT count(*) FROM documento_consentimiento_version")) == 0
        get_settings.cache_clear()
        assert client.post(ruta_consentimiento, headers=h_est).status_code == 201

        # RF-22: Simular reloj fuera de mitad de tiempo (>10 min en sesión de 20 min) moviendo fecha_inicio atrás
        with lab.sesiones.begin() as s:
            ses_row = s.get(SesionProgramadaModel, UUID(sesion_id))
            ses_row.fecha_inicio = ahora - timedelta(minutes=15)
        r_tarde = client.post(f"/api/v1/simulacion/convocatorias/{conv_id}/iniciar", headers=h_est)
        assert r_tarde.status_code == 403
        assert "mitad del tiempo" in r_tarde.text

        # Restaurar ventana válida dentro de 50% (hace 2 min) y participar
        with lab.sesiones.begin() as s:
            ses_row = s.get(SesionProgramadaModel, UUID(sesion_id))
            ses_row.fecha_inicio = ahora - timedelta(minutes=2)

        r_in = client.post(f"/api/v1/simulacion/convocatorias/{conv_id}/iniciar", headers=h_est)
        assert r_in.status_code == 200, r_in.text
        intento_id = r_in.json()["id_intento"]

        # RF-10: Elegir opción INCORRECTA en P1, luego avanzar a P2, luego VOLVER y MODIFICAR P1 a CORRECTA
        r_ws1 = client.put(
            f"/api/v1/simulacion/intentos/{intento_id}/borradores/{q1['id']}",
            headers=h_est,
            json={"id_opcion": q1["opciones"][1]["id"], "reflexion_estudiante": "Duda inicial"},
        )
        assert r_ws1.status_code == 200
        assert client.put(
            f"/api/v1/simulacion/intentos/{intento_id}/borradores/{q2['id']}",
            headers=h_est,
            json={"id_opcion": q2["opciones"][0]["id"], "reflexion_estudiante": "Plan completo"},
        ).status_code == 200

        r_mod = client.put(
            f"/api/v1/simulacion/intentos/{intento_id}/borradores/{q1['id']}",
            headers=h_est,
            json={"id_opcion": q1["opciones"][0]["id"], "reflexion_estudiante": "Corrección ética"},
        )
        assert r_mod.status_code == 200
        assert r_mod.json()["cambios_realizados"] >= 3

        # RF-12, RF-13, RF-14: Entrega definitiva -> evalúa rúbrica ponderada -> 100.00 pts
        r_env = client.post(f"/api/v1/simulacion/intentos/{intento_id}/enviar", headers=h_est, json={"permitir_parcial": False})
        assert r_env.status_code == 200, r_env.text
        res_data = r_env.json()
        assert res_data["nota_final"] == 100.0
        assert res_data["aciertos"] == 2
        assert len(res_data["criterios"]) == 2
        assert res_data["preguntas"][0]["justificacion_elegida"] == "Cumple el principio ético de confidencialidad."

        # Intentar repetir SIN permiso -> 409; luego docente autoriza repetición RF-25 y permite 2do intento
        assert client.post(f"/api/v1/simulacion/convocatorias/{conv_id}/iniciar", headers=h_est).status_code == 409
        r_rep = client.post(
            "/api/v1/identity/excepciones/repeticiones",
            headers=h_doc,
            json={"id_sesion": sesion_id, "id_estudiante": str(est_uid)},
        )
        assert r_rep.status_code == 201, r_rep.text
        r_in2 = client.post(f"/api/v1/simulacion/convocatorias/{conv_id}/iniciar", headers=h_est)
        assert r_in2.status_code == 200, r_in2.text
        intento2_id = r_in2.json()["id_intento"]
        assert client.post(f"/api/v1/simulacion/intentos/{intento2_id}/enviar", headers=h_est, json={"permitir_parcial": True}).status_code == 200

        # RF-15, RF-26: Seguimiento docente muestra nombres reales, notas y permite feedback
        r_seg = client.get("/api/v1/identity/seguimiento/casos", headers=h_doc)
        assert r_seg.status_code == 200 and len(r_seg.json()) == 1
        caso_seg_id = r_seg.json()[0]["id_caso"]
        parts = client.get(f"/api/v1/identity/seguimiento/casos/{caso_seg_id}/participaciones", headers=h_doc).json()
        assert parts[0]["nombre_estudiante"] == "Mateo Estudiante"
        assert parts[0]["nota_final"] == 100.0
        part_id = parts[0]["id_participacion"]
        assert client.post(
            f"/api/v1/identity/seguimiento/participaciones/{part_id}/feedback",
            headers=h_doc,
            json={"texto": "Excelente rectificación ética en el primer escenario."},
        ).status_code == 201

        # RF-19, RF-27: Finalizar sesión, consolidar, publicar y enviar notificación oficial de calificación
        assert client.post(f"/scheduling/sesiones/{sesion_id}/estado", headers=h_doc, json={"accion": "finalizar"}).status_code == 200
        cons = client.get(f"/scheduling/sesiones/{sesion_id}/evaluacion/consolidacion", headers=h_doc).json()
        assert cons["publicable"] is True
        r_pub = client.post(
            f"/scheduling/sesiones/{sesion_id}/evaluacion/publicaciones",
            headers=h_doc,
            json={"revision_sha256": cons["revision_sha256"]},
        )
        assert r_pub.status_code == 200, r_pub.text

        r_not = client.post(
            "/scheduling/calificaciones/notificar",
            headers=h_doc,
            json={"estudiante_id": est_info["identidad_scheduling"], "participacion_id": conv_id},
        )
        assert r_not.status_code == 200, r_not.text

        # RF-16: Descargar reporte XLSX y PDF
        assert client.get(f"/api/v1/identity/seguimiento/sesiones/{sesion_id}/reporte?formato=xlsx", headers=h_doc).status_code == 200
        assert client.get(f"/api/v1/identity/seguimiento/sesiones/{sesion_id}/reporte?formato=pdf", headers=h_doc).status_code == 200
