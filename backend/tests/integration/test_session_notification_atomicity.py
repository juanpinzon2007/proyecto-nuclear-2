"""Avisos internos atómicos con State y auditoría; PostgreSQL17 propio.

Sustituye la expectativa experimental de un pendiente outbox por rollback del
conjunto SQL. La preparación académica/JWT docente es de laboratorio.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import event, select, func

from app.modules.scheduling.application.cambiar_estado_y_publicar import cambiar_estado_y_publicar
from app.modules.scheduling.application.registrar_observadores import crear_gestor_eventos
from app.modules.scheduling.application.worker_cierre import cerrar_sesiones_vencidas
from app.modules.scheduling.domain.events import EventoAcademico
from app.modules.scheduling.infrastructure.models import (
    SesionProgramadaModel as S, EventoAuditoriaModel as A, NotificacionModel as N,
)
from tests.integration.test_participation_http_composition import integracion  # noqa: F401
from tests.integration.test_cases_graph_authoring import autor, pg_autoria, payload_valido  # noqa: F401


def cantidades(db, h):
    auditorias = db.scalar(select(func.count()).select_from(A).where(
        A.sesion_id == h.sesion, A.estado_nuevo == 'FINALIZADO'))
    avisos = db.scalar(select(func.count()).select_from(N).where(
        N.convocatoria_id == h.convocatoria, N.tipo == 'SESION_FINALIZADA'))
    return auditorias, avisos


@pytest.mark.parametrize('actor', ['docente', 'worker'])
def test_fallo_sql_revierte_transicion_auditoria_aviso_y_permite_reintento(integracion, actor):
    h = integracion
    motor = h.sesiones.kw['bind']
    with h.sesiones() as db:
        ahora = db.get(S, h.sesion).fecha_fin + timedelta(hours=24)

    def fallo(_, __, statement, ___, ____, _____):
        if statement.lstrip().startswith('INSERT INTO notificacion'):
            raise RuntimeError('Fallo SQL controlado de laboratorio')

    def ejecutar():
        if actor == 'docente':
            return h.client.post(f'/scheduling/sesiones/{h.sesion}/estado',
                headers=h.a.headers, json={'accion': 'finalizar'}).status_code
        return asyncio.run(cerrar_sesiones_vencidas(
            h.sesiones, crear_gestor_eventos(h.sesiones), ahora=ahora))

    event.listen(motor, 'before_cursor_execute', fallo)
    try:
        if actor == 'docente':
            assert ejecutar() == 500
        else:
            with pytest.raises(RuntimeError, match='Fallo SQL'):
                ejecutar()
    finally:
        event.remove(motor, 'before_cursor_execute', fallo)
    # Otra conexión: no hay cierre confirmado sin su aviso.
    with h.sesiones() as db:
        assert db.get(S, h.sesion).estado == 'EN_CURSO'
        assert cantidades(db, h) == (0, 0)
    assert ejecutar() == (200 if actor == 'docente' else 1)
    assert ejecutar() == (409 if actor == 'docente' else 0)
    with h.sesiones() as db:
        assert db.get(S, h.sesion).estado == 'FINALIZADO'
        assert cantidades(db, h) == (1, 1)


def test_replay_efimero_y_reintentos_sql_concurrentes_no_duplican(integracion):
    h = integracion
    assert h.client.post(f'/scheduling/sesiones/{h.sesion}/estado',
        headers=h.a.headers, json={'accion': 'finalizar'}).status_code == 200
    mensaje = EventoAcademico(tipo='sesion.finalizada', entidad_id=h.sesion)
    # publicar ya no despacha el efecto SQL fuera de su transacción.
    asyncio.run(crear_gestor_eventos(h.sesiones).publicar(mensaje))
    barrera = Barrier(2, timeout=15)

    def replay(_):
        with h.sesiones() as db:
            barrera.wait()
            crear_gestor_eventos(h.sesiones).preparar(mensaje, db)
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(replay, range(2)))
    with h.sesiones() as db:
        assert cantidades(db, h) == (1, 1)


def test_fallo_commit_revierte_tambien_aviso_ya_insertado(integracion):
    h = integracion
    gestor = crear_gestor_eventos(h.sesiones)
    with h.sesiones() as db:
        def fallo(_):
            # Los tres cambios se ven en la transacción, no en otra conexión.
            assert cantidades(db, h) == (1, 1)
            with h.sesiones() as otra:
                assert cantidades(otra, h) == (0, 0)
                assert otra.get(S, h.sesion).estado == 'EN_CURSO'
            raise RuntimeError('Commit de laboratorio rechazado')

        event.listen(db, 'before_commit', fallo)
        with pytest.raises(RuntimeError, match='Commit de laboratorio'):
            asyncio.run(cambiar_estado_y_publicar(db, sesion_id=h.sesion,
                accion='finalizar', gestor=gestor))
        event.remove(db, 'before_commit', fallo)
    with h.sesiones() as otra:
        assert cantidades(otra, h) == (0, 0)
        assert otra.get(S, h.sesion).estado == 'EN_CURSO'


def test_callback_efimero_fallido_no_pierde_aviso_sql_confirmado(integracion):
    h = integracion
    gestor = crear_gestor_eventos(h.sesiones)

    class FalloEfimero:
        async def notificar(self, mensaje):
            raise RuntimeError('Callback efimero de laboratorio')

    gestor.suscribir('sesion.finalizada', FalloEfimero())
    with h.sesiones() as db:
        with pytest.raises(RuntimeError, match='Callback efimero'):
            asyncio.run(cambiar_estado_y_publicar(db, sesion_id=h.sesion,
                accion='finalizar', gestor=gestor))
    with h.sesiones() as otra:
        assert cantidades(otra, h) == (1, 1)
        assert otra.get(S, h.sesion).estado == 'FINALIZADO'


def test_mensaje_sin_transicion_compatible_no_crea_avisos(integracion):
    h = integracion
    with h.sesiones() as db:
        with pytest.raises(ValueError, match='incompatible'):
            crear_gestor_eventos(h.sesiones).preparar(
                EventoAcademico(tipo='sesion.finalizada', entidad_id=h.sesion), db)
        db.rollback()
    with h.sesiones() as otra:
        assert cantidades(otra, h) == (0, 0)
