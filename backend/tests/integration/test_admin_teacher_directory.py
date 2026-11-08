"""RF03: main/JWT/roles SQL reales; PostgreSQL17 desechable.

Catálogo y vínculos son preparación LAB. Ningún override de autorización.
Las mutaciones SQL del catálogo simulan revocación de permisos desde servidor,
no prueban un endpoint de administración de roles (fuera del alcance).
"""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_engine
from app.modules.identity.api.dependencies import construir_tokens
from app.modules.identity.domain.errors import AccesoDenegado, NoAutenticado
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as V
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.teacher_directory import ConsultaDocentesSQLAlchemy
from tests.integration.test_admin_bootstrap import lab, inicializar  # noqa: F401
from tests.integration.test_main_teacher_followup import observar_lectura

URL = '/api/v1/identity/docentes'


@pytest.fixture
def personal(lab):
    from app.main import app
    import secrets
    inicial = inicializar(lab)
    clave = secrets.token_urlsafe(32)
    protegido = obtener_hasheador().hash(clave)
    cuentas = []
    with lab.sesiones.begin() as s:
        for rol in (1, 1, 2):
            u = U(id_rol=rol, nombre='Cuenta LAB', correo=f'cuenta-{uuid4().hex}@universidad.test',
                  clave_hash=protegido, activo=True)
            s.add(u); s.flush(); cuentas.append((u.id_usuario, u.correo))
    assert app.dependency_overrides == {}
    with TestClient(app) as cliente:
        yield SimpleNamespace(cliente=cliente, sesiones=lab.sesiones,
            admin=(int(inicial.id_usuario), lab.correo), clave_admin=lab.clave,
            docente=cuentas[0], ajeno=cuentas[1], estudiante=cuentas[2], clave=clave)


def headers(h, cuenta):
    respuesta = h.cliente.post('/api/v1/identity/auth/personal', json={
        'correo':cuenta[1], 'clave':h.clave_admin if cuenta == h.admin else h.clave})
    assert respuesta.status_code == 200
    return {'Authorization':'Bearer '+respuesta.json()['access_token']}


def test_listado_main_privado_paginado_sin_dml_hashes_ni_vinculos_academicos(personal):
    h = personal
    admin = headers(h, h.admin)
    with h.sesiones.begin() as s:
        # Un docente sin vínculos y otro con varios: no son concesiones de acceso.
        s.get(U, h.ajeno[0]).activo = False
        s.add_all([V(id_usuario=h.docente[0], sistema='CASES', id_academico=uuid4()),
                   V(id_usuario=h.docente[0], sistema='CASES', id_academico=uuid4()),
                   V(id_usuario=h.docente[0], sistema='SCHEDULING', id_academico=uuid4())])
    motor = get_engine()
    transacciones = []
    def comprobar(conn, cursor, statement, *args):
        if 'count(*)' in statement and 'usuario' in statement:
            transacciones.append((conn.exec_driver_sql('SHOW transaction_read_only').scalar(),
                                  conn.exec_driver_sql('SHOW transaction_isolation').scalar()))
    sa.event.listen(motor, 'before_cursor_execute', comprobar)
    try:
        with observar_lectura() as operaciones:
            primera = h.cliente.get(URL+'?limite=1', headers=admin)
            segunda = h.cliente.get(URL+'?limite=1&desplazamiento=1', headers=admin)
            vacia = h.cliente.get(URL+'?desplazamiento=200', headers=admin)
            with ThreadPoolExecutor(max_workers=2) as pool:
                repetidas = list(pool.map(lambda _: h.cliente.get(URL, headers=admin), range(2)))
    finally:
        sa.event.remove(motor, 'before_cursor_execute', comprobar)
    assert operaciones == []
    assert transacciones and all(t == ('on', 'repeatable read') for t in transacciones)
    assert primera.status_code == segunda.status_code == vacia.status_code == 200
    assert primera.headers['cache-control'] == 'no-store'
    assert primera.json()['total'] == segunda.json()['total'] == 2
    cuentas = primera.json()['docentes'] + segunda.json()['docentes']
    assert [d['id_usuario'] for d in cuentas] == [str(h.docente[0]), str(h.ajeno[0])]
    assert [d['activo'] for d in cuentas] == [True, False]
    assert all(set(d) == {'id_usuario', 'nombre', 'correo', 'activo'} for d in cuentas)
    assert vacia.json()['docentes'] == [] and vacia.json()['total'] == 2
    assert all(r.status_code == 200 for r in repetidas)
    assert repetidas[0].json() == repetidas[1].json()
    assert not any(x in primera.text for x in ('clave_hash', 'permisos', 'id_academico', 'access_token'))
    with h.sesiones() as s:  # Otra Session; lectura no cambió cuentas ni vínculos.
        assert s.scalar(sa.select(sa.func.count()).select_from(U)) == 4
        assert s.scalar(sa.select(sa.func.count()).select_from(V).where(V.id_usuario == h.docente[0])) == 3


@pytest.mark.parametrize('caso,esperado', [
    ('anonimo', 401), ('invalido', 401), ('expirado', 401), ('inactivo', 401),
    ('docente', 403), ('estudiante', 403), ('compuesto_no_aprobado', 503),
])
def test_listado_no_admite_identidad_o_rol_no_autorizados(personal, caso, esperado):
    h = personal
    auth = headers(h, h.admin)
    if caso == 'anonimo': auth = {}
    elif caso == 'invalido': auth = {'Authorization': 'Bearer invalido-LAB'}
    elif caso == 'expirado':
        token = auth['Authorization'].split()[1]
        claims = jwt.decode(token, options={'verify_signature': False})
        claims['iat'] -= 1800; claims['nbf'] = claims['iat']; claims['exp'] -= 1800
        auth = {'Authorization': 'Bearer '+jwt.encode(claims, construir_tokens()._secreto, algorithm='HS256')}
    else:
        with h.sesiones.begin() as s:
            u = s.get(U, h.admin[0])
            if caso == 'inactivo': u.activo = False
            elif caso == 'compuesto_no_aprobado':
                s.add(RolORM(id_rol=19, nombre='DOCENTE ADMINISTRADOR')); s.flush(); u.id_rol = 19
            else: u.id_rol = 1 if caso == 'docente' else 2
    with observar_lectura() as operaciones:
        respuesta = h.cliente.get(URL, headers=auth | {'X-Docente-Id': str(h.admin[0])})
    assert respuesta.status_code == esperado
    assert operaciones == [] and 'docentes' not in respuesta.json().get('detail', {})
    assert h.docente[1] not in respuesta.text and h.ajeno[1] not in respuesta.text


def test_limites_y_fallo_de_infraestructura_no_exponen_datos(personal):
    h = personal; auth = headers(h, h.admin)
    for query in ('limite=0', 'limite=101', 'limite=abc', 'desplazamiento=-1'):
        assert h.cliente.get(URL+'?'+query, headers=auth).status_code == 422
    def fallar(conn, cursor, statement, *args):
        if 'count(*)' in statement and 'usuario' in statement:
            raise OperationalError('CONSULTA_PRIVADA', {}, RuntimeError('SECRETO_LAB'))
    motor = get_engine(); sa.event.listen(motor, 'before_cursor_execute', fallar)
    try:
        with observar_lectura() as operaciones:
            respuesta = h.cliente.get(URL, headers=auth)
    finally: sa.event.remove(motor, 'before_cursor_execute', fallar)
    assert respuesta.status_code == 503 and operaciones == []
    assert 'CONSULTA_PRIVADA' not in respuesta.text and 'SECRETO_LAB' not in respuesta.text
    assert h.cliente.get(URL, headers=auth).status_code == 200


@pytest.mark.parametrize('cambio', ['rol', 'inactivo', 'eliminado'])
def test_lector_revalida_contexto_previamente_acreditado_en_otra_sesion(personal, cambio):
    h = personal
    with h.sesiones() as s:
        contexto = RepositorioUsuariosSQLAlchemy(s).obtener(str(h.admin[0]))
    with h.sesiones.begin() as s:
        u = s.get(U, h.admin[0])
        if cambio == 'rol': u.id_rol = 1
        elif cambio == 'inactivo': u.activo = False
        else: s.delete(u)
    with pytest.raises(AccesoDenegado if cambio == 'rol' else NoAutenticado):
        ConsultaDocentesSQLAlchemy(h.sesiones).consultar(contexto, limite=25, desplazamiento=0)


def test_alta_existente_se_refleja_sin_otra_escritura_al_consultar(personal):
    h = personal; auth = headers(h, h.admin)
    # Clave aleatoria solo en memoria; no forma parte de la evidencia.
    import secrets
    correo = f'alta-{uuid4().hex}@universidad.test'
    alta = h.cliente.post(URL, headers=auth, json=dict(nombre='Docente LAB', correo=correo,
        clave=secrets.token_urlsafe(32), roles=['DOCENTE'], permisos=['CREAR_CASOS']))
    assert alta.status_code == 201
    with observar_lectura() as operaciones:
        respuesta = h.cliente.get(URL, headers=auth)
    assert respuesta.status_code == 200 and respuesta.json()['total'] == 3 and operaciones == []
    assert respuesta.json()['docentes'][-1]['id_usuario'] == alta.json()['id_usuario']
    with h.sesiones() as s:
        assert s.get(U, int(alta.json()['id_usuario'])).correo == correo
