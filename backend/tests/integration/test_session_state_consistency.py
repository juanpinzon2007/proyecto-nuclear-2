"""RF-19: State consulta el estado bloqueado, incluso con identity map obsoleto.

PostgreSQL17 desechable y routers reales. La emisión JWT docente pertenece a la
preparación explícita de laboratorio; no demuestra login docente productivo.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event, get_ident
from uuid import UUID

import pytest
from sqlalchemy import select, func, event

from app.db.session import get_session_factory
from app.modules.scheduling.application.cambiar_estado_sesion import cambiar_estado_sesion
from app.modules.scheduling.application.cambiar_estado_y_publicar import cambiar_estado_y_publicar
from app.modules.scheduling.application.registrar_observadores import crear_gestor_eventos
from app.modules.scheduling.application.worker_cierre import cerrar_sesiones_vencidas
from app.modules.scheduling.domain.state import TransicionInvalidaError
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, EventoAuditoriaModel as A, NotificacionModel as N
from tests.integration.test_session_programming_http import programacion, conceder, solicitar
from tests.integration.test_cases_graph_authoring import autor, pg_autoria, payload_valido  # noqa: F401
from tests.integration.test_participation_http_composition import integracion  # noqa: F401


@pytest.fixture
def fabrica_eventos_aislada(programacion):
    # La ruta de estados compone un Observer con su propia Session. Debe usar
    # el mismo laboratorio, no la configuración privada de app.db.session.
    app = programacion.client.app
    app.dependency_overrides[get_session_factory] = lambda: programacion.sesiones
    yield
    app.dependency_overrides.pop(get_session_factory)


def sesion_en_curso(h, body=None):
    respuesta = solicitar(h, body)
    assert respuesta.status_code == 201, respuesta.text
    identificador = UUID(respuesta.json()['id'])
    inicio = h.client.post(f'/scheduling/sesiones/{identificador}/estado',
        headers=h.a.headers, json={'accion': 'iniciar'})
    assert inicio.status_code == 200, inicio.text
    return identificador


def cierres(s, identificador):
    return s.scalar(select(func.count()).select_from(A).where(
        A.sesion_id == identificador, A.estado_nuevo == 'FINALIZADO'))


def test_estado_precargado_no_repite_cierre_http_ni_altera_fecha(programacion, fabrica_eventos_aislada):
    h = programacion
    conceder(h)
    identificador = sesion_en_curso(h)
    with h.sesiones() as obsoleta:
        precargada = obsoleta.get(S, identificador)
        assert precargada.estado == 'EN_CURSO'
        respuesta = h.client.post(f'/scheduling/sesiones/{identificador}/estado',
            headers=h.a.headers, json={'accion': 'finalizar'})
        assert respuesta.status_code == 200, respuesta.text
        with pytest.raises(TransicionInvalidaError):
            cambiar_estado_sesion(obsoleta, sesion_id=identificador, accion='finalizar')
        obsoleta.rollback()
    with h.sesiones() as otra:
        fila = otra.get(S, identificador)
        assert fila.estado == 'FINALIZADO'
        assert fila.finalizado_en == datetime.fromisoformat(respuesta.json()['finalizado_en'])
        assert cierres(otra, identificador) == 1
        assert fila.version_caso_id == h.version


def test_cierres_concurrentes_con_precarga_solo_una_transicion_y_auditoria(programacion, fabrica_eventos_aislada):
    h = programacion
    conceder(h)
    identificador = sesion_en_curso(h)
    barrera = Barrier(2, timeout=15)

    def cerrar(_):
        with h.sesiones() as s:
            precargada = s.get(S, identificador)
            assert precargada.estado == 'EN_CURSO'
            barrera.wait()
            try:
                cambiar_estado_sesion(s, sesion_id=identificador, accion='finalizar')
                s.commit()
                return 'cerrada'
            except TransicionInvalidaError:
                s.rollback()
                return 'conflicto'

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        assert sorted(ejecutor.map(cerrar, range(2))) == ['cerrada', 'conflicto']
    with h.sesiones() as s:
        assert s.get(S, identificador).estado == 'FINALIZADO'
        assert cierres(s, identificador) == 1


def test_rollback_de_cierre_conserva_estado_auditoria_y_version(programacion, fabrica_eventos_aislada):
    h = programacion
    conceder(h)
    identificador = sesion_en_curso(h)
    with h.sesiones() as s:
        cambiar_estado_sesion(s, sesion_id=identificador, accion='finalizar')
        assert cierres(s, identificador) == 1  # flush, todavía no confirmado.
        s.rollback()
    with h.sesiones() as otra:
        fila = otra.get(S, identificador)
        assert fila.estado == 'EN_CURSO' and fila.finalizado_en is None
        assert fila.version_caso_id == h.version and cierres(otra, identificador) == 0


def test_worker_frontera_24_horas_offset_y_no_repite_cierre(programacion, fabrica_eventos_aislada):
    h = programacion
    conceder(h)
    fin = datetime.fromisoformat(h.body['fecha_fin'])
    exacta = sesion_en_curso(h)
    posterior = sesion_en_curso(h, h.body | {'fecha_fin': (fin + timedelta(microseconds=1)).isoformat()})
    ahora = (fin + timedelta(hours=24)).astimezone(timezone(timedelta(hours=-5)))
    gestor = crear_gestor_eventos(h.sesiones)
    asyncio.run(cerrar_sesiones_vencidas(h.sesiones, gestor, ahora=ahora))
    with h.sesiones() as s:
        assert s.get(S, exacta).estado == 'FINALIZADO' and cierres(s, exacta) == 1
        assert s.get(S, posterior).estado == 'EN_CURSO' and cierres(s, posterior) == 0
        assert s.scalar(select(A.origen).where(A.sesion_id == exacta, A.estado_nuevo == 'FINALIZADO')) == 'WORKER'
    assert asyncio.run(cerrar_sesiones_vencidas(h.sesiones, gestor, ahora=ahora)) == 0


def test_lock_sin_refresco_demuestra_causa_del_identity_map(programacion, fabrica_eventos_aislada):
    h = programacion
    conceder(h)
    identificador = sesion_en_curso(h)
    with h.sesiones() as s:
        precargada = s.get(S, identificador)
        r = h.client.post(f'/scheduling/sesiones/{identificador}/estado',
            headers=h.a.headers, json={'accion': 'finalizar'})
        assert r.status_code == 200, r.text
        # Columna SQL real: no hidrata/actualiza la instancia del identity map.
        assert s.scalar(select(S.estado).where(S.id == identificador)) == 'FINALIZADO'
        bloqueada = s.get(S, identificador, with_for_update=True)
        assert bloqueada is precargada and bloqueada.estado == 'EN_CURSO'
        fresca = s.get(S, identificador, with_for_update=True, populate_existing=True)
        assert fresca is precargada and fresca.estado == 'FINALIZADO'
        assert cierres(s, identificador) == 1


def avisos_finales(s, h):
    return s.scalar(select(func.count()).select_from(N).where(
        N.convocatoria_id == h.convocatoria, N.tipo == 'SESION_FINALIZADA'))


def test_http_cierre_repetido_y_actor_ajeno_no_publican_otra_auditoria_o_aviso(integracion):
    h = integracion
    url = f'/scheduling/sesiones/{h.sesion}/estado'
    for headers, estado in [(h.a.ajeno, 403), (h.headers, 403), ({}, 401)]:
        assert h.client.post(url, headers=headers, json={'accion': 'finalizar'}).status_code == estado
    with h.sesiones() as s:
        assert cierres(s, h.sesion) == avisos_finales(s, h) == 0
    r = h.client.post(url, headers=h.a.headers, json={'accion': 'finalizar'})
    assert r.status_code == 200, r.text
    for accion in ('finalizar', 'iniciar'):
        assert h.client.post(url, headers=h.a.headers, json={'accion': accion}).status_code == 409
    with h.sesiones() as s:
        assert cierres(s, h.sesion) == avisos_finales(s, h) == 1
        assert s.get(S, h.sesion).version_caso_id == h.version


@pytest.mark.parametrize('ganador', ['docente', 'worker'])
def test_competencia_docente_worker_con_locks_reales_y_observer_unico(integracion, ganador):
    h = integracion
    motor = h.sesiones.kw['bind']
    candidatos = Event()
    docente_terminado = Event()
    worker_bloqueado = Event()
    docente_intenta_lock = Event()
    hilo_worker = {}
    with h.sesiones() as s:
        ahora = s.get(S, h.sesion).fecha_fin + timedelta(hours=24)

    def despues_sql(_, __, statement, ___, ____, _____):
        # Barrera DESPUÉS del SELECT real de candidatos, nunca filas simuladas.
        if (ganador == 'docente' and get_ident() == hilo_worker.get('id')
                and statement.partition('FROM')[0].strip() == 'SELECT sesion_programada.id'
                and 'FOR UPDATE' not in statement):
            candidatos.set()
            assert docente_terminado.wait(15)

    def antes_sql(_, __, statement, ___, ____, _____):
        if (ganador == 'worker' and get_ident() != hilo_worker.get('id')
                and 'sesion_programada' in statement and 'FOR UPDATE' in statement):
            docente_intenta_lock.set()

    def cerrar_worker():
        hilo_worker['id'] = get_ident()
        with h.sesiones() as s:
            precargada = s.get(S, h.sesion)
            assert precargada.estado == 'EN_CURSO'

            def antes_commit(_):
                if ganador == 'worker':
                    worker_bloqueado.set()
                    assert docente_intenta_lock.wait(15)

            event.listen(s, 'before_commit', antes_commit)
            gestor = crear_gestor_eventos(h.sesiones)
            return asyncio.run(cerrar_sesiones_vencidas(lambda: s, gestor, ahora=ahora))

    event.listen(motor, 'after_cursor_execute', despues_sql)
    event.listen(motor, 'before_cursor_execute', antes_sql)
    try:
        with ThreadPoolExecutor(max_workers=1) as ejecutor:
            futuro = ejecutor.submit(cerrar_worker)
            assert (candidatos if ganador == 'docente' else worker_bloqueado).wait(15)
            try:
                r = h.client.post(f'/scheduling/sesiones/{h.sesion}/estado',
                    headers=h.a.headers, json={'accion': 'finalizar'})
            finally:
                docente_terminado.set()
            assert r.status_code == (200 if ganador == 'docente' else 409), r.text
            assert futuro.result(timeout=30) == (0 if ganador == 'docente' else 1)
    finally:
        docente_terminado.set()
        event.remove(motor, 'after_cursor_execute', despues_sql)
        event.remove(motor, 'before_cursor_execute', antes_sql)
    with h.sesiones() as s:
        assert cierres(s, h.sesion) == avisos_finales(s, h) == 1
        auditoria = s.scalar(select(A).where(A.sesion_id == h.sesion, A.estado_nuevo == 'FINALIZADO'))
        assert auditoria.origen == ganador.upper()


def test_fallo_antes_de_commit_revierte_estado_auditoria_y_no_publica(integracion):
    h = integracion
    gestor = crear_gestor_eventos(h.sesiones)
    with h.sesiones() as s:
        def fallar(_):
            raise RuntimeError('Fallo técnico explícito de laboratorio antes del commit')
        event.listen(s, 'before_commit', fallar)
        with pytest.raises(RuntimeError, match='Fallo técnico'):
            asyncio.run(cambiar_estado_y_publicar(s, sesion_id=h.sesion, accion='finalizar', gestor=gestor))
        with h.sesiones() as otra:
            assert otra.get(S, h.sesion).estado == 'EN_CURSO'
            assert cierres(otra, h.sesion) == avisos_finales(otra, h) == 0
        event.remove(s, 'before_commit', fallar)
        asyncio.run(cambiar_estado_y_publicar(s, sesion_id=h.sesion, accion='finalizar', gestor=gestor))
        with pytest.raises(TransicionInvalidaError):
            asyncio.run(cambiar_estado_y_publicar(s, sesion_id=h.sesion, accion='finalizar', gestor=gestor))
    with h.sesiones() as s:
        assert cierres(s, h.sesion) == avisos_finales(s, h) == 1


def test_fallo_observer_postcommit_no_revierte_ni_republica_al_reintentar(integracion):
    from app.modules.scheduling.domain.events import GestorEventosAcademicos
    h = integracion
    intentos_entrega = []

    class ObservadorQueFalla:
        async def notificar(self, evento):
            intentos_entrega.append(evento)
            raise RuntimeError('Observer de laboratorio indisponible')

    gestor = GestorEventosAcademicos()
    gestor.suscribir('sesion.finalizada', ObservadorQueFalla())
    with h.sesiones() as s:
        with pytest.raises(RuntimeError, match='Observer de laboratorio'):
            asyncio.run(cambiar_estado_y_publicar(s, sesion_id=h.sesion, accion='finalizar', gestor=gestor))
        with pytest.raises(TransicionInvalidaError):
            asyncio.run(cambiar_estado_y_publicar(s, sesion_id=h.sesion, accion='finalizar', gestor=gestor))
    with h.sesiones() as s:
        assert s.get(S, h.sesion).estado == 'FINALIZADO' and cierres(s, h.sesion) == 1
    assert len(intentos_entrega) == 1
    # Callback efímero, no el Observer SQL de producción. Su fallo sigue siendo
    # posterior al commit. La atomicidad de los avisos SQL se acredita en
    # test_session_notification_atomicity.py, sin una cola ni reenvío de State.
