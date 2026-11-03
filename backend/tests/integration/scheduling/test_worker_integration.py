"""Pruebas de integración del Worker de cierre automático y observadores."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models.caso import CasoModel, VersionCasoModel
from app.modules.scheduling.application.registrar_observadores import (
    crear_gestor_eventos,
)
from app.modules.scheduling.application.worker_cierre import (
    cerrar_sesiones_vencidas,
)
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
    ConvocatoriaModel,
    NotificacionModel,
    EventoAuditoriaModel,
)


@pytest.mark.anyio
async def test_worker_cierra_sesiones_vencidas_en_bd(
    session_factory: sessionmaker[Session],
    docente_id: uuid.UUID,
):
    ahora = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    # 1. Preparar datos en base de datos
    with session_factory() as db:
        espacio = EspacioAcademicoModel(nombre="Laboratorio de Psicología")
        db.add(espacio)

        caso = CasoModel(docente_creador_id=docente_id)
        db.add(caso)
        db.flush()

        version = VersionCasoModel(
            caso_id=caso.id,
            numero=1,
            nombre="Caso Obediencia",
            desarrollo_situacional="Desarrollo",
            contexto_historia="Contexto",
            tiempo_estimado_min=60,
            estado=EstadoCaso.BORRADOR,
        )
        db.add(version)
        db.flush()
        version.estado=EstadoCaso.PUBLICADO
        db.flush()

        # Sesión vencida (terminó hace 26 horas)
        sesion_vencida = SesionProgramadaModel(
            espacio_academico_id=espacio.id,
            version_caso_id=version.id,
            docente_id=docente_id,
            fecha_inicio=ahora - timedelta(hours=30),
            fecha_fin=ahora - timedelta(hours=26),
            tiempo_maximo_minutos=40,
            estado="EN_CURSO",
        )
        db.add(sesion_vencida)
        db.flush()

        # Convocatoria para el estudiante en la sesión vencida
        estudiante_id = uuid.uuid4()
        convocatoria = ConvocatoriaModel(
            sesion_id=sesion_vencida.id,
            estudiante_id=estudiante_id,
            codigo_hash="hash_de_prueba",
            estado="ACTIVA",
        )
        db.add(convocatoria)

        # Sesión reciente (terminó hace solo 2 horas - NO debe cerrarse)
        sesion_reciente = SesionProgramadaModel(
            espacio_academico_id=espacio.id,
            version_caso_id=version.id,
            docente_id=docente_id,
            fecha_inicio=ahora - timedelta(hours=4),
            fecha_fin=ahora - timedelta(hours=2),
            tiempo_maximo_minutos=40,
            estado="EN_CURSO",
        )
        db.add(sesion_reciente)

        db.commit()

        sesion_vencida_id = sesion_vencida.id
        sesion_reciente_id = sesion_reciente.id

    # 2. Ejecutar el worker con el gestor de eventos y observador real
    gestor = crear_gestor_eventos(session_factory)

    cerradas = await cerrar_sesiones_vencidas(
        session_factory=session_factory,
        gestor=gestor,
        ahora=ahora,
    )

    assert cerradas == 1

    # 3. Verificar estado en base de datos
    with session_factory() as db:
        vencida_db = db.get(SesionProgramadaModel, sesion_vencida_id)
        assert vencida_db.estado == "FINALIZADO"
        assert vencida_db.finalizado_en is not None

        reciente_db = db.get(SesionProgramadaModel, sesion_reciente_id)
        assert reciente_db.estado == "EN_CURSO"
        assert reciente_db.finalizado_en is None

        # 4. Verificar evento de auditoría generado por el WORKER
        evento = db.scalar(
            select(EventoAuditoriaModel).where(
                EventoAuditoriaModel.sesion_id == sesion_vencida_id,
                EventoAuditoriaModel.origen == "WORKER",
            )
        )
        assert evento is not None
        assert evento.estado_anterior == "EN_CURSO"
        assert evento.estado_nuevo == "FINALIZADO"

        # 5. Verificar que el observador generó la notificación SESION_FINALIZADA
        notificacion = db.scalar(
            select(NotificacionModel).where(
                NotificacionModel.destinatario_id == estudiante_id,
                NotificacionModel.tipo == "SESION_FINALIZADA",
            )
        )
        assert notificacion is not None
        assert notificacion.canal == "INTERNA"
        assert notificacion.estado == "PENDIENTE"
