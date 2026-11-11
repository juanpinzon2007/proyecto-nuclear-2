"""Perfil global DOCENTE mediante main, JWT y PostgreSQL 17 desechable."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

from app.db.session import get_engine
from app.modules.identity.infrastructure.models import UsuarioORM, RolPermisoORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from tests.integration.test_admin_teacher_directory import personal, headers, lab, inicializar  # noqa: F401
from tests.integration.test_admin_bootstrap import payload_valido  # noqa: F401
from tests.integration.test_main_teacher_followup import observar_lectura


URL = '/api/v1/identity/roles/docente/permisos'


def permisos_persistidos(h):
    with h.sesiones() as sesion:
        return sesion.execute(sa.select(RolPermisoORM.id_rol, RolPermisoORM.id_permiso)
            .order_by(RolPermisoORM.id_rol, RolPermisoORM.id_permiso)).all()


def test_perfil_global_revalida_tokens_existentes_y_persiste_entre_sesiones(personal, payload_valido):
    h = personal
    admin = headers(h, h.admin)
    docentes = [headers(h, cuenta) for cuenta in (h.docente, h.ajeno)]
    # Vínculos académicos sintéticos explícitos. El endpoint de permisos no los crea.
    with h.sesiones.begin() as sesion:
        sesion.add_all([IdentidadAcademicaORM(id_usuario=cuenta[0], sistema='CASES', id_academico=uuid4())
            for cuenta in (h.docente, h.ajeno)])
    with observar_lectura() as operaciones:
        inicial = h.cliente.get(URL, headers=admin)
    assert inicial.status_code == 200 and operaciones == []
    assert inicial.json() == dict(id_rol=1, rol='DOCENTE', permisos=['CREAR_CASOS'],
        permisos_disponibles=['CREAR_CASOS'], docentes_afectados=2, alcance='GLOBAL_ROL')
    for permisos in ([], ['CREAR_CASOS']):
        respuesta = h.cliente.put(URL, headers=admin, json={'permisos': permisos})
        assert respuesta.status_code == 200
        assert respuesta.json()['permisos'] == permisos
        for docente in docentes:
            actual = h.cliente.get('/api/v1/identity/me', headers=docente)
            assert actual.status_code == 200 and actual.json()['permisos'] == permisos
            crear = h.cliente.post('/api/v1/cases', headers=docente, json=payload_valido)
            assert crear.status_code == (201 if permisos else 403)
        assert permisos_persistidos(h) == ([(1, 1)] if permisos else [])
        assert h.cliente.put(URL, headers=admin, json={'permisos': permisos}).json() == respuesta.json()
    assert not any(campo in inicial.text for campo in ('clave', 'correo', 'access_token', 'id_academico'))


@pytest.mark.parametrize('actor,estado', [('anonimo', 401), ('invalido', 401),
    ('docente', 403), ('estudiante', 403), ('inactivo', 401)])
def test_rechazo_de_identidad_sin_escrituras(personal, actor, estado):
    h = personal
    auth = headers(h, h.admin)
    if actor == 'anonimo':
        auth = {}
    elif actor == 'invalido':
        auth = {'Authorization': 'Bearer invalido-LAB'}
    else:
        with h.sesiones.begin() as sesion:
            usuario = sesion.get(UsuarioORM, h.admin[0])
            if actor == 'inactivo':
                usuario.activo = False
            else:
                usuario.id_rol = 1 if actor == 'docente' else 2
    with observar_lectura() as operaciones:
        lectura = h.cliente.get(URL, headers=auth)
        escritura = h.cliente.put(URL, headers=auth, json={'permisos': []})
    assert lectura.status_code == escritura.status_code == estado
    assert operaciones == [] and permisos_persistidos(h) == [(1, 1)]


@pytest.mark.parametrize('body,query', [({'permisos': ['DESCONOCIDO']}, ''),
    ({'permisos': [], 'id_docente': '1'}, ''), ({'permisos': [], 'rol': 'ADMINISTRADOR'}, ''),
    ({'permisos': []}, '?id_docente=1')])
def test_contrato_rechaza_concesiones_individuales_o_catalogo_inexistente(personal, body, query):
    h = personal
    with observar_lectura() as operaciones:
        respuesta = h.cliente.put(URL + query, headers=headers(h, h.admin), json=body)
    assert respuesta.status_code == 422 and operaciones == []
    assert permisos_persistidos(h) == [(1, 1)]


def test_fallo_sql_revierte_retiro_y_permite_reintento(personal):
    h = personal
    auth = headers(h, h.admin)
    motor = get_engine()
    def fallar(conn, cursor, statement, *args):
        if statement.lstrip().upper().startswith('DELETE FROM ROL_PERMISO'):
            raise OperationalError('ESCRITURA_PRIVADA', {}, RuntimeError('SECRETO_LAB'))
    sa.event.listen(motor, 'after_cursor_execute', fallar)
    try:
        respuesta = h.cliente.put(URL, headers=auth, json={'permisos': []})
    finally:
        sa.event.remove(motor, 'after_cursor_execute', fallar)
    assert respuesta.status_code == 503
    assert 'SECRETO_LAB' not in respuesta.text and 'ESCRITURA_PRIVADA' not in respuesta.text
    assert permisos_persistidos(h) == [(1, 1)]
    assert h.cliente.put(URL, headers=auth, json={'permisos': []}).status_code == 200
    assert permisos_persistidos(h) == []


def test_actualizaciones_concurrentes_serializan_el_perfil_sin_duplicados(personal):
    h = personal
    auth = headers(h, h.admin)
    def configurar(permisos):
        return h.cliente.put(URL, headers=auth, json={'permisos': permisos})
    with ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(configurar, ([], ['CREAR_CASOS'])))
    assert all(r.status_code == 200 for r in respuestas)
    final = h.cliente.get(URL, headers=auth).json()['permisos']
    assert permisos_persistidos(h) == ([(1, 1)] if final else [])
    with ThreadPoolExecutor(max_workers=2) as pool:
        repetidas = list(pool.map(configurar, (['CREAR_CASOS'], ['CREAR_CASOS'])))
    assert all(r.status_code == 200 for r in repetidas)
    assert permisos_persistidos(h) == [(1, 1)]
