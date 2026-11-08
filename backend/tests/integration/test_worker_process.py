"""RF-19: proceso real, CLI y periodicidad; solo PostgreSQL17 desechable.

Las cuentas, el caso publicado y las relaciones provienen de fixtures académicas
de laboratorio. La sesión EN_CURSO y convocatoria auxiliares se preparan como
datos administrativos sintéticos; no acreditan un nuevo flujo docente productivo.
No se sustituyen worker, reloj, State, SQL ni Observer en los procesos hijos.
"""
import os
from pathlib import Path
import queue
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select, text

from app.modules.scheduling.infrastructure.models import (
    SesionProgramadaModel as S, ConvocatoriaModel as C,
    EventoAuditoriaModel as A, NotificacionModel as N,
)
from tests.integration.test_participation_http_composition import integracion  # noqa: F401
from tests.integration.test_cases_graph_authoring import autor, pg_autoria, payload_valido  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = (
    "from app.core.config import Settings,get_settings; "
    "Settings.model_config['env_file']=None; get_settings.cache_clear(); "
    "import runpy; runpy.run_module('app.modules.scheduling.infrastructure.worker_runner',run_name='__main__')"
)


def preparar(h):
    """Sesión vencida sin intentos ni resultados, solo dentro del laboratorio."""
    # Cerrar legítimamente la sesión auxiliar de la fixture HTTP; el único
    # candidato del experimento será el que se prepara a continuación.
    respuesta = h.client.post(f'/scheduling/sesiones/{h.sesion}/estado',
        headers=h.a.headers, json={'accion': 'finalizar'})
    assert respuesta.status_code == 200, respuesta.text
    with h.sesiones.begin() as db:
        original = db.get(S, h.sesion)
        fin = datetime.now(timezone.utc) - timedelta(hours=26)
        sesion = S(espacio_academico_id=original.espacio_academico_id,
            version_caso_id=original.version_caso_id, docente_id=original.docente_id,
            fecha_inicio=fin-timedelta(hours=1), fecha_fin=fin,
            tiempo_maximo_minutos=original.tiempo_maximo_minutos, estado='EN_CURSO')
        db.add(sesion)
        db.flush()
        convocatoria = C(sesion_id=sesion.id, estudiante_id=h.uuid_estudiante,
                         codigo_hash='hash-no-utilizable-laboratorio-worker', estado='ACTIVA')
        db.add(convocatoria)
        db.flush()
        return SimpleNamespace(sesiones=h.sesiones, sesion=sesion.id,
            convocatoria=convocatoria.id, version=h.version, estudiante=h.uuid_estudiante)


def entorno(h, nombre=None):
    url = h.sesiones.kw['bind'].url
    assert url.host == '127.0.0.1' and url.database == 'sps_identity_test_resolver'
    env = {k:v for k,v in os.environ.items() if not k.startswith(
        ('POSTGRES_', 'IDENTITY_', 'PARTICIPATION_', 'PG')) and k not in
        ('DATABASE_URL', 'TEST_DATABASE_URL', 'SPS_IDENTITY_TEST_URL', 'SPS_PERSISTENCE_LAB_URL')}
    env.update(POSTGRES_HOST=url.host, POSTGRES_PORT=str(url.port),
        POSTGRES_DB=url.database, POSTGRES_USER=url.username, POSTGRES_PASSWORD=url.password,
        PYTHONPATH=str(ROOT/'backend'), PYTHONDONTWRITEBYTECODE='1',
        PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1', PGAPPNAME=nombre or 'rf19_worker_lab')
    return env


def iniciar(h, *opciones, env=None):
    return subprocess.Popen([sys.executable, '-B', '-c', LAUNCHER, *opciones],
        cwd=ROOT, env=env or entorno(h), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace')


def terminar(p):
    if p.poll() is None:
        p.terminate()  # Solo el proceso hijo creado por esta prueba.
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)


def una_revision(h, env=None):
    p = iniciar(h, '--once', env=env)
    try:
        salida, _ = p.communicate(timeout=40)
        return p.returncode, salida
    finally:
        terminar(p)


def comprobar(h, estado, cantidad):
    with h.sesiones() as db:
        fila = db.get(S, h.sesion)
        assert fila.estado == estado and fila.version_caso_id == h.version
        assert (fila.finalizado_en is not None) == (estado == 'FINALIZADO')
        auditorias = db.scalars(select(A).where(A.sesion_id == h.sesion)).all()
        avisos = db.scalars(select(N).where(N.convocatoria_id == h.convocatoria)).all()
        assert len(auditorias) == len(avisos) == cantidad
        if cantidad:
            assert auditorias[0].origen == 'WORKER'
            assert auditorias[0].estado_anterior == 'EN_CURSO'
            assert auditorias[0].estado_nuevo == 'FINALIZADO'
            assert avisos[0].tipo == 'SESION_FINALIZADA' and avisos[0].canal == 'INTERNA'
            assert avisos[0].destinatario_id == h.estudiante


def test_cli_real_cierra_y_segunda_ejecucion_no_duplica(integracion, record_property):
    h = preparar(integracion)
    codigo, salida = una_revision(h)
    assert codigo == 0 and 'Sesiones cerradas:' in salida
    record_property('primera_revision_salida', salida)
    comprobar(h, 'FINALIZADO', 1)
    codigo, salida = una_revision(h)
    assert codigo == 0 and 'Sesiones cerradas: 0' in salida
    record_property('segunda_revision_salida', salida)
    comprobar(h, 'FINALIZADO', 1)


def test_dos_procesos_bloqueados_en_postgresql_conservan_un_cierre(integracion, record_property):
    h = preparar(integracion)
    nombres = ['rf19_'+uuid4().hex for _ in range(2)]
    procesos = []
    try:
        with h.sesiones() as bloqueo:
            bloqueo.get(S, h.sesion, with_for_update=True)
            procesos = [iniciar(h, '--once', env=entorno(h, n)) for n in nombres]
            limite = monotonic()+25
            while True:
                with h.sesiones() as observacion:
                    esperando = observacion.scalar(text(
                        'SELECT count(*) FROM pg_stat_activity WHERE '
                        'application_name IN (:a,:b) AND wait_event_type=\'Lock\''),
                        {'a':nombres[0], 'b':nombres[1]})
                if esperando == 2:
                    break
                assert monotonic() < limite, 'Los dos procesos no alcanzaron el lock real'
                Event().wait(.05)
            bloqueo.rollback()
        for indice, p in enumerate(procesos):
            salida, _ = p.communicate(timeout=30)
            assert p.returncode == 0, salida
            record_property(f'proceso_{indice}_salida', salida)
        comprobar(h, 'FINALIZADO', 1)
    finally:
        for p in procesos:
            terminar(p)


def test_bucle_real_recupera_fallo_sql_en_siguiente_revision_sin_filtrar(integracion, record_property):
    h = preparar(integracion)
    # Trigger exclusivo de este PG desechable, nunca una migración productiva.
    engine = h.sesiones.kw['bind']
    with engine.begin() as c:
        c.exec_driver_sql("CREATE FUNCTION laboratorio_rf19_fallo() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'MARCADOR_PRIVADO_RF19'; END $$")
        c.exec_driver_sql("CREATE TRIGGER laboratorio_rf19_fallo BEFORE INSERT ON notificacion FOR EACH ROW WHEN (NEW.tipo='SESION_FINALIZADA') EXECUTE FUNCTION laboratorio_rf19_fallo()")
    p = iniciar(h)
    lineas = queue.Queue()
    salida = []

    def leer():
        for linea in p.stdout:
            lineas.put(linea)

    lector = Thread(target=leer, daemon=True)
    lector.start()

    def esperar(marca, timeout):
        limite = monotonic()+timeout
        while True:
            linea = lineas.get(timeout=max(.01, limite-monotonic()))
            salida.append(linea)
            assert 'MARCADOR_PRIVADO_RF19' not in linea and 'Traceback' not in linea
            if marca in linea:
                return
            assert monotonic() < limite, 'No se observó la revisión periódica'

    try:
        esperar('REVISION_FALLIDA', 25)
        comprobar(h, 'EN_CURSO', 0)
        with engine.begin() as c:
            c.exec_driver_sql('DROP TRIGGER laboratorio_rf19_fallo ON notificacion')
            c.exec_driver_sql('DROP FUNCTION laboratorio_rf19_fallo()')
        # Intervalo real de producción: 60 s, no mock ni aceleración del reloj.
        esperar('Sesiones cerradas:', 85)
        comprobar(h, 'FINALIZADO', 1)
        assert p.poll() is None
        record_property('bucle_real_salida', ''.join(salida))
    finally:
        terminar(p)
        lector.join(timeout=5)
        with engine.begin() as c:
            c.exec_driver_sql('DROP TRIGGER IF EXISTS laboratorio_rf19_fallo ON notificacion')
            c.exec_driver_sql('DROP FUNCTION IF EXISTS laboratorio_rf19_fallo()')


def test_cli_fallo_conexion_sale_no_cero_sin_exponer_configuracion(integracion, record_property):
    h = preparar(integracion)
    env = entorno(h)
    # Mismo servidor propio; DB inexistente, nunca otra base del equipo.
    env['POSTGRES_DB'] = 'rf19_inexistente_'+uuid4().hex
    codigo, salida = una_revision(h, env=env)
    assert codigo == 1 and 'REVISION_FALLIDA' in salida
    assert env['POSTGRES_PASSWORD'] not in salida
    assert env['POSTGRES_DB'] not in salida and 'Traceback' not in salida
    record_property('revision_fallida_salida', salida)
    comprobar(h, 'EN_CURSO', 0)
