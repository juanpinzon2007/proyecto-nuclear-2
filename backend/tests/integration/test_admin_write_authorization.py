"""RF03 MAIN/JWT/PG17: revocación real después del Proxy, antes de la escritura."""
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
import sqlalchemy as sa

from app.modules.identity.application.services import ServicioAdministracionUsuarios
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolPermisoORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.db.session import get_engine
from tests.integration.test_admin_teacher_directory import personal, headers, lab, inicializar  # noqa: F401


@pytest.mark.parametrize('operacion', ['crear_docente', 'asignar_autorizaciones'])
@pytest.mark.parametrize('revocacion,estado', [('activo', 401), ('rol', 403)])
def test_revocacion_confirmada_tras_proxy_impide_escritura(personal, monkeypatch, operacion, revocacion, estado):
    h = personal; auth = headers(h, h.admin)
    original = getattr(ServicioAdministracionUsuarios, operacion)
    with h.sesiones() as s:
        count = s.scalar(sa.select(sa.func.count()).select_from(U))
        grants = s.execute(sa.select(RolPermisoORM.id_rol, RolPermisoORM.id_permiso)).all()

    def revocar(self, contexto, *args, **kwargs):
        # Barrera controlada de planificación: JWT y Proxy ya validaron. La
        # revocación ocurre en otra transacción real; no se simula autorización.
        with h.sesiones.begin() as s:
            actor = s.get(U, h.admin[0])
            if revocacion == 'activo':
                actor.activo = False
            else:
                actor.id_rol = 1
        return original(self, contexto, *args, **kwargs)

    monkeypatch.setattr(ServicioAdministracionUsuarios, operacion, revocar)
    body = dict(roles=['DOCENTE'], permisos=['CREAR_CASOS'])
    if operacion == 'crear_docente':
        body.update(correo=f'nuevo-{uuid4().hex}@universidad.test', nombre='Docente LAB', clave='Solo laboratorio, no credencial productiva')
        response = h.cliente.post('/api/v1/identity/docentes', headers=auth, json=body)
    else:
        response = h.cliente.put(f'/api/v1/identity/docentes/{h.docente[0]}/autorizaciones', headers=auth, json=body)
    assert response.status_code == estado
    assert 'clave_hash' not in response.text and 'roles' not in response.json()
    with h.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(U)) == count
        assert s.get(U, h.docente[0]).id_rol == 1
        assert s.execute(sa.select(RolPermisoORM.id_rol, RolPermisoORM.id_permiso)).all() == grants


def test_sesion_precargada_relee_cuenta_revocada(personal):
    h = personal
    with h.sesiones() as first:
        cached = first.get(U, h.admin[0]); assert cached.activo
        with h.sesiones.begin() as second:
            second.get(U, h.admin[0]).activo = False
        actual = RepositorioUsuariosSQLAlchemy(first).obtener_para_escritura(str(h.admin[0]))
        assert actual.activo is False


def test_revocacion_concurrente_espera_commit_de_operacion_autorizada(personal, monkeypatch):
    h = personal; auth = headers(h, h.admin)
    entered, release, revoking = Event(), Event(), Event(); pid = []
    original = RepositorioUsuariosSQLAlchemy.crear_docente

    def pause(self, *args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(RepositorioUsuariosSQLAlchemy, 'crear_docente', pause)
    body = dict(correo=f'concurrente-{uuid4().hex}@universidad.test', nombre='Docente LAB',
        clave='Solo laboratorio concurrencia', roles=['DOCENTE'], permisos=['CREAR_CASOS'])

    def revoke():
        with h.sesiones.begin() as s:
            s.execute(sa.text("SET LOCAL lock_timeout='8s'"))
            pid.append(s.scalar(sa.text('SELECT pg_backend_pid()'))); revoking.set()
            s.execute(sa.update(U).where(U.id_usuario == h.admin[0]).values(activo=False))

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(h.cliente.post, '/api/v1/identity/docentes', headers=auth, json=body)
        try:
            assert entered.wait(10)
            revoker = pool.submit(revoke); assert revoking.wait(5)
            blocked = False; limit = monotonic() + 3
            while monotonic() < limit:
                with h.sesiones() as observer:
                    blocked = bool(observer.scalar(sa.text('SELECT pg_blocking_pids(:pid)'), {'pid': pid[0]}))
                if blocked: break
                sleep(0.02)
            assert blocked and not revoker.done()
        finally:
            release.set()
        assert writer.result(timeout=10).status_code == 201
        revoker.result(timeout=10)
    assert h.cliente.get('/api/v1/identity/me', headers=auth).status_code == 401
    with h.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(U).where(U.correo == body['correo'])) == 1


def test_fallo_sql_despues_insert_revierte_alta_y_permite_reintento(personal):
    h = personal; auth = headers(h, h.admin); engine = get_engine()
    body = dict(correo=f'rollback-{uuid4().hex}@universidad.test', nombre='Docente LAB',
        clave='Solo laboratorio rollback', roles=['DOCENTE'], permisos=['CREAR_CASOS'])

    def fail(conn, cursor, statement, *args):
        if statement.lstrip().lower().startswith('insert into usuario'):
            conn.exec_driver_sql('SELECT 1/0')

    sa.event.listen(engine, 'after_cursor_execute', fail)
    try:
        response = h.cliente.post('/api/v1/identity/docentes', headers=auth, json=body)
        assert response.status_code == 503 and 'SELECT' not in response.text
    finally:
        sa.event.remove(engine, 'after_cursor_execute', fail)
    with h.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(U).where(U.correo == body['correo'])) == 0
    assert h.cliente.post('/api/v1/identity/docentes', headers=auth, json=body).status_code == 201
