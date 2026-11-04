"""Pruebas de integración de los endpoints y base de datos de Scheduling."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models.caso import CasoModel, VersionCasoModel
from app.modules.cases.infrastructure.models.rubrica import RubricaModel
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
    ConvocatoriaModel,
    NotificacionModel,
    EventoAuditoriaModel,
    DocenteEspacioAcademicoModel,
)


def _crear_caso_publicado(db: Session, docente_id: uuid.UUID) -> VersionCasoModel:
    caso = CasoModel(docente_creador_id=docente_id,id_caso=1)
    db.add(caso)
    db.flush()

    version = VersionCasoModel(
        caso_id=caso.id,
        numero=1,
        nombre="Caso Psicología Social - Obediencia",
        desarrollo_situacional="Experimento sobre la influencia de la autoridad.",
        contexto_historia="Contexto investigativo universitario.",
        tiempo_estimado_min=60,
        estado=EstadoCaso.BORRADOR,
    )
    db.add(version)
    db.flush()
    # La asignación real exige una rúbrica de esta versión. Crear en borrador:
    # los guards históricos impiden añadirla después de publicar.
    db.add(RubricaModel(version_caso_id=version.id,nombre='Rúbrica técnica LAB',version_regla='laboratorio'))
    db.flush()
    version.estado=EstadoCaso.PUBLICADO
    db.flush()
    db.commit()
    return version


def test_flujo_completo_programacion_y_ciclo_vida(
    client: TestClient,
    db_session: Session,
    docente_id: uuid.UUID,
    cabeceras_estudiante,
    ambito_convocatoria,
):
    # 1. Crear Espacio Académico
    espacio = EspacioAcademicoModel(nombre="Laboratorio de Psicología Social")
    db_session.add(espacio)
    db_session.commit()

    # 2. Crear Caso con versión publicada
    version = _crear_caso_publicado(db_session, docente_id)
    db_session.add(DocenteEspacioAcademicoModel(id_docente=6,espacio_academico_id=espacio.id))
    db_session.commit()

    # 3. Programar Sesión Académica
    ahora = datetime.now(timezone.utc)
    inicio = ahora + timedelta(hours=1)
    fin = ahora + timedelta(hours=3)

    resp_sesion = client.post(
        "/scheduling/sesiones",
        json={
            "espacio_academico_id": str(espacio.id),
            "version_caso_id": str(version.id),
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "tiempo_maximo_minutos": 45,
            "lugar": "Módulo B, Sala 204",
            "mensaje_personalizado": "Puntualidad requerida para el experimento.",
        },
    )
    assert resp_sesion.status_code == 201
    datos_sesion = resp_sesion.json()
    sesion_id = uuid.UUID(datos_sesion["id"])
    assert datos_sesion["estado"] == "SIN_INICIAR"
    assert datos_sesion["tiempo_maximo_minutos"] == 45

    # 4. Consultar sesión programada
    resp_get = client.get(f"/scheduling/sesiones/{sesion_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == str(sesion_id)

    # 5. Convocar a un estudiante
    estudiante_id = uuid.uuid4()
    ambito_convocatoria(db_session,db_session.get(SesionProgramadaModel,sesion_id),docente_id,estudiante_id)
    headers_estudiante = cabeceras_estudiante(estudiante_id)
    resp_conv = client.post(
        f"/scheduling/sesiones/{sesion_id}/convocatorias",
        json={"estudiante_id": str(estudiante_id)},
    )
    assert resp_conv.status_code == 201
    datos_conv = resp_conv.json()
    convocatoria_id = uuid.UUID(datos_conv["convocatoria_id"])
    codigo_acceso = datos_conv["codigo_acceso"]
    assert len(codigo_acceso) > 10

    # Verificar convocatoria en BD con código hasheado
    conv_bd = db_session.get(ConvocatoriaModel, convocatoria_id)
    assert conv_bd is not None
    assert conv_bd.estado == "ACTIVA"
    assert conv_bd.codigo_hash == hashlib.sha256(codigo_acceso.encode()).hexdigest()

    # Verificar que se creó la notificación inicial de convocatoria
    notifs = db_session.scalars(
        select(NotificacionModel).where(NotificacionModel.destinatario_id == estudiante_id)
    ).all()
    assert any(n.tipo == "CONVOCATORIA" for n in notifs)

    # 6. Iniciar la sesión (SIN_INICIAR -> EN_CURSO)
    resp_iniciar = client.post(
        f"/scheduling/sesiones/{sesion_id}/estado",
        json={"accion": "iniciar"},
    )
    assert resp_iniciar.status_code == 200
    assert resp_iniciar.json()["estado"] == "EN_CURSO"

    # Verificar auditoría
    eventos = db_session.scalars(
        select(EventoAuditoriaModel).where(EventoAuditoriaModel.sesion_id == sesion_id)
    ).all()
    assert any(e.estado_nuevo == "EN_CURSO" and e.origen == "DOCENTE" for e in eventos)

    # 7. Validar ingreso de estudiante con hora dentro del rango
    # Para validar ingreso, la fecha debe ser dentro de la ventana
    sesion_obj = db_session.get(SesionProgramadaModel, sesion_id)
    sesion_obj.fecha_inicio = ahora - timedelta(minutes=5)
    sesion_obj.fecha_fin = ahora + timedelta(hours=1)
    db_session.commit()

    resp_ingreso = client.post(
        "/scheduling/validar-ingreso",
        headers=headers_estudiante,
        json={
            "convocatoria_id": str(convocatoria_id),
            "estudiante_id": str(estudiante_id),
            "codigo_acceso": codigo_acceso,
        },
    )
    assert resp_ingreso.status_code == 200
    assert resp_ingreso.json()["id"] == str(sesion_id)

    # 8. Validar ingreso con código erróneo es rechazado
    resp_ingreso_malo = client.post(
        "/scheduling/validar-ingreso",
        headers=headers_estudiante,
        json={
            "convocatoria_id": str(convocatoria_id),
            "estudiante_id": str(estudiante_id),
            "codigo_acceso": "codigo_completamente_falso",
        },
    )
    assert resp_ingreso_malo.status_code == 403

    # 9. Finalizar la sesión (EN_CURSO -> FINALIZADO)
    resp_fin = client.post(
        f"/scheduling/sesiones/{sesion_id}/estado",
        json={"accion": "finalizar"},
    )
    assert resp_fin.status_code == 200
    assert resp_fin.json()["estado"] == "FINALIZADO"
    assert resp_fin.json()["finalizado_en"] is not None

    # 10. Notificar calificación al estudiante
    participacion_id = uuid.uuid4()
    resp_calif = client.post(
        "/scheduling/calificaciones/notificar",
        json={
            "estudiante_id": str(estudiante_id),
            "participacion_id": str(participacion_id),
        },
    )
    assert resp_calif.status_code == 201
    assert resp_calif.json()["tipo"] == "CALIFICACION"
