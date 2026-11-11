"""RF-04 en main con JWT y PostgreSQL 17 propios.

Los catálogos, grupos, matrículas y concesiones son preparación administrativa
explícita. Caso, publicación, sesión, asignación y convocatorias usan la API real.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from pydantic import ValidationError

from app.core.config import get_settings
from app.db.session import get_engine
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G, GrupoEstudianteORM as M
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM
from app.modules.scheduling.api.schemas import ProgramarSesionRequest
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel as C, DocenteEspacioAcademicoModel as Grant,
    NotificacionModel as N, SesionProgramadaModel as S,
)
from tests.integration.test_admin_teacher_directory import personal, lab, inicializar, headers  # noqa: F401
from tests.integration.test_admin_bootstrap import payload_valido  # noqa: F401
from tests.integration.cases.conftest import configurar_final_unica_escena
from tests.integration.test_main_teacher_followup import observar_lectura


def solicitud_base():
    inicio = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    return dict(espacio_academico_id=str(uuid4()), version_caso_id=str(uuid4()),
        fecha_inicio=inicio.isoformat(), fecha_fin=(inicio + timedelta(hours=1)).isoformat(),
        tiempo_maximo_minutos=30, grupo_id=1, estudiantes_ids=[str(uuid4())],
        fecha_limite_ingreso=(inicio + timedelta(minutes=30)).isoformat())


@pytest.mark.parametrize('problema', ['grupo_ausente', 'estudiantes_ausentes', 'fecha_ausente',
    'duplicados', 'fecha_sin_zona', 'fecha_anterior', 'fecha_posterior'])
def test_seleccion_exige_trio_completo_fechas_explicitas_y_estudiantes_unicos(problema):
    datos = solicitud_base()
    if problema in {'grupo_ausente', 'estudiantes_ausentes', 'fecha_ausente'}:
        datos.pop({'grupo_ausente': 'grupo_id', 'estudiantes_ausentes': 'estudiantes_ids',
                   'fecha_ausente': 'fecha_limite_ingreso'}[problema])
    elif problema == 'duplicados':
        datos['estudiantes_ids'] *= 2
    else:
        datos['fecha_limite_ingreso'] = {
            'fecha_sin_zona': '2030-01-01T12:30:00',
            'fecha_anterior': '2030-01-01T11:59:59Z',
            'fecha_posterior': '2030-01-01T13:00:01Z',
        }[problema]
    with pytest.raises(ValidationError):
        ProgramarSesionRequest.model_validate(datos)


@pytest.mark.parametrize('frontera', ['fecha_inicio', 'fecha_fin'])
def test_limite_explicito_admite_fronteras_del_horario_sin_inventar_tolerancias(frontera):
    datos = solicitud_base()
    datos['fecha_limite_ingreso'] = datos[frontera]
    assert ProgramarSesionRequest.model_validate(datos).fecha_limite_ingreso.isoformat().startswith('2030-01-01T')


@pytest.fixture
def asignable(personal, payload_valido, monkeypatch):
    h = personal
    monkeypatch.setenv('PARTICIPATION_TIMESTAMP_ZONE', 'UTC')
    monkeypatch.setenv('IDENTITY_INSTITUTIONAL_DOMAINS', '["universidad.test"]')
    get_settings.cache_clear()
    auth = headers(h, h.docente)
    otro = headers(h, h.ajeno)
    estudiante_uuid = uuid4()
    with h.sesiones.begin() as sesion:
        for cuenta in (h.docente, h.ajeno):
            sesion.add_all([IA(id_usuario=cuenta[0], sistema='CASES', id_academico=uuid4()),
                IA(id_usuario=cuenta[0], sistema='SCHEDULING', id_academico=uuid4())])
        sesion.add(IA(id_usuario=h.estudiante[0], sistema='SCHEDULING', id_academico=estudiante_uuid))
        grupo = G(id_profesor=h.docente[0], nombre='Grupo propio RF04 LAB', periodo='LAB')
        ajeno = G(id_profesor=h.ajeno[0], nombre='Grupo ajeno RF04 LAB', periodo='LAB')
        sesion.add_all([grupo, ajeno])
        sesion.flush()
        matricula = M(id_grupo=grupo.id_grupo, id_estudiante=h.estudiante[0],
            fecha_ingreso=datetime(2026, 1, 1))
        sesion.add(matricula)
        sesion.flush()
        gid, ajeno_gid, mid = grupo.id_grupo, ajeno.id_grupo, matricula.id_grupo_estudiante
    caso = h.cliente.post('/api/v1/cases', headers=auth, json=payload_valido)
    assert caso.status_code == 201
    version = caso.json()['version_id']
    configurar_final_unica_escena(h.cliente, version, auth)
    assert h.cliente.post(f'/api/v1/cases/{version}/publish', headers=auth).status_code == 200
    espacio = h.cliente.post('/scheduling/espacios', headers=auth, json={'nombre': 'Espacio RF04 LAB'})
    assert espacio.status_code == 201
    espacio_id = UUID(espacio.json()['id'])
    with h.sesiones.begin() as sesion:
        sesion.add(Grant(id_docente=h.docente[0], espacio_academico_id=espacio_id))
    datos = solicitud_base() | dict(espacio_academico_id=str(espacio_id), version_caso_id=version,
        grupo_id=gid, estudiantes_ids=[str(estudiante_uuid)], mensaje_personalizado='Mensaje RF04 LAB')
    return SimpleNamespace(h=h, auth=auth, otro=otro, datos=datos, grupo=gid, grupo_ajeno=ajeno_gid,
        matricula=mid, estudiante=estudiante_uuid, espacio=espacio_id, version=UUID(version))


def cantidades(h):
    with h.sesiones() as sesion:
        return tuple(sesion.scalar(sa.select(sa.func.count()).select_from(modelo))
                     for modelo in (S, A, C, N))


def programar(h, datos=None, auth=None):
    return h.h.cliente.post('/scheduling/sesiones', headers=h.auth if auth is None else auth,
        json=h.datos if datos is None else datos)


def test_crea_sesion_asignacion_y_convocatorias_misma_transaccion_sin_admision(asignable, record_property):
    h = asignable
    motor = get_engine()
    transacciones = []
    commits = []
    def registrar(conn, cursor, sql, *args):
        if sql.lstrip().lower().startswith(('insert into sesion_programada', 'insert into asignacion_caso',
                                           'insert into convocatoria', 'insert into notificacion')):
            transacciones.append(conn.scalar(sa.text('SELECT txid_current()')))
    def confirmar(conn):
        commits.append(True)
    sa.event.listen(motor, 'after_cursor_execute', registrar)
    sa.event.listen(motor, 'commit', confirmar)
    try:
        respuesta = programar(h)
    finally:
        sa.event.remove(motor, 'after_cursor_execute', registrar)
        sa.event.remove(motor, 'commit', confirmar)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.headers['cache-control'] == 'no-store'
    datos = respuesta.json()
    sid = UUID(datos['id'])
    assert datos['estado'] == 'SIN_INICIAR' and datos['version_caso_id'] == str(h.version)
    assert len(datos['convocatorias']) == 1
    codigo = datos['convocatorias'][0]['codigo_acceso']
    cid = UUID(datos['convocatorias'][0]['convocatoria_id'])
    assert len(transacciones) == 4 and len(set(transacciones)) == len(commits) == 1
    with h.h.sesiones() as sesion:
        asignacion = sesion.get(A, datos['id_asignacion'])
        version = sesion.get(VersionCasoModel, h.version)
        assert asignacion.id_caso == sesion.get(CasoModel, version.caso_id).id_caso
        assert asignacion.sesion_programada_id == sid and asignacion.version_caso_id == h.version
        assert asignacion.id_grupo == h.grupo and asignacion.intentos_base == 1 and asignacion.estado == 'programada'
        assert asignacion.fecha_limite_ingreso == datetime(2030, 1, 1, 12, 30)
        convocatoria = sesion.get(C, cid)
        assert convocatoria.sesion_id == sid and convocatoria.estudiante_id == h.estudiante
        assert convocatoria.codigo_hash != codigo and convocatoria.admision_evento_id is None
        aviso = sesion.scalar(sa.select(N).where(N.convocatoria_id == cid))
        assert aviso.destinatario_id == h.estudiante and codigo not in aviso.mensaje
    recuperada = h.h.cliente.get(f'/scheduling/sesiones/{sid}', headers=h.auth)
    assert recuperada.status_code == 200
    assert 'convocatorias' not in recuperada.json() and codigo not in recuperada.text
    listado = h.h.cliente.get(f'/scheduling/sesiones/{sid}/convocatorias', headers=h.auth)
    assert listado.status_code == 200 and len(listado.json()) == 1 and codigo not in listado.text
    login = h.h.cliente.post('/api/v1/identity/auth/estudiantes', json={
        'correo': h.h.estudiante[1], 'codigo_convocatoria': codigo})
    assert login.status_code == 200
    record_property('persistencia', 'sesion, asignacion, convocatoria y aviso confirmados en una transaccion; otra Session verifica referencias')


@pytest.mark.parametrize('actor,estado', [('anonimo', 401), ('docente_ajeno', 403), ('estudiante', 403)])
def test_identidad_ajena_no_produce_asociaciones(asignable, actor, estado):
    h = asignable
    auth = {} if actor == 'anonimo' else h.otro
    if actor == 'estudiante':
        auth = headers(h.h, h.h.admin)
        with h.h.sesiones.begin() as sesion:
            sesion.get(U, h.h.admin[0]).id_rol = 2
    with observar_lectura() as operaciones:
        respuesta = programar(h, auth=auth)
    assert respuesta.status_code == estado and operaciones == []
    assert cantidades(h.h) == (0, 0, 0, 0)


@pytest.mark.parametrize('problema', ['grupo_ajeno', 'estudiante_ajeno', 'matricula_inactiva',
    'cuenta_inactiva', 'identidad_ambigua', 'espacio_sin_permiso'])
def test_seleccion_exige_relaciones_academicas_vigentes(asignable, problema):
    h = asignable
    datos = h.datos.copy()
    with h.h.sesiones.begin() as sesion:
        if problema == 'grupo_ajeno':
            datos['grupo_id'] = h.grupo_ajeno
        elif problema == 'estudiante_ajeno':
            datos['estudiantes_ids'] = [str(uuid4())]
        elif problema == 'matricula_inactiva':
            sesion.get(M, h.matricula).activo = False
        elif problema == 'cuenta_inactiva':
            sesion.get(U, h.h.estudiante[0]).activo = False
        elif problema == 'identidad_ambigua':
            sesion.add(IA(id_usuario=h.h.estudiante[0], sistema='SCHEDULING', id_academico=uuid4()))
        else:
            sesion.delete(sesion.get(Grant, (h.h.docente[0], h.espacio)))
    with observar_lectura() as operaciones:
        respuesta = programar(h, datos)
    assert respuesta.status_code == (503 if problema == 'identidad_ambigua' else 403)
    assert operaciones == [] and cantidades(h.h) == (0, 0, 0, 0)


def test_fallo_sql_revierte_sesion_asignacion_convocatorias_y_avisos(asignable):
    h = asignable
    motor = get_engine()
    def fallar(conn, cursor, sql, *args):
        if sql.lstrip().lower().startswith('insert into notificacion'):
            conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(motor, 'after_cursor_execute', fallar)
    try:
        respuesta = programar(h)
    finally:
        sa.event.remove(motor, 'after_cursor_execute', fallar)
    assert respuesta.status_code == 503
    assert cantidades(h.h) == (0, 0, 0, 0)
    assert programar(h).status_code == 201
    assert cantidades(h.h) == (1, 1, 1, 1)


def test_post_repetidos_crean_sesiones_independientes_sin_duplicar_su_seleccion(asignable):
    h = asignable
    with ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(lambda _: programar(h), range(2)))
    assert all(r.status_code == 201 for r in respuestas)
    assert len({r.json()['id'] for r in respuestas}) == 2
    assert cantidades(h.h) == (2, 2, 2, 2)
    with h.h.sesiones() as sesion:
        filas = sesion.execute(sa.select(C.sesion_id, sa.func.count()).group_by(C.sesion_id)).all()
        assert len(filas) == 2 and all(cantidad == 1 for _, cantidad in filas)


def test_seleccion_multiple_convoca_solo_estudiantes_del_grupo_elegido(asignable):
    h = asignable
    otro_uuid = uuid4()
    with h.h.sesiones.begin() as sesion:
        estudiante = U(id_rol=2, nombre='Segundo estudiante RF04 LAB',
            correo=f'seleccion-{uuid4().hex}@universidad.test', clave_hash='sin-login-personal-LAB')
        sesion.add(estudiante)
        sesion.flush()
        sesion.add_all([IA(id_usuario=estudiante.id_usuario, sistema='SCHEDULING', id_academico=otro_uuid),
            M(id_grupo=h.grupo, id_estudiante=estudiante.id_usuario, fecha_ingreso=datetime(2026, 1, 1))])
    datos = h.datos | {'estudiantes_ids': [str(h.estudiante), str(otro_uuid)]}
    respuesta = programar(h, datos)
    assert respuesta.status_code == 201
    assert cantidades(h.h) == (1, 1, 2, 2)
    assert {c['estudiante_id'] for c in respuesta.json()['convocatorias']} == {str(h.estudiante), str(otro_uuid)}
    assert len({c['codigo_acceso'] for c in respuesta.json()['convocatorias']}) == 2


def test_revocacion_de_matricula_concurrente_impide_insertar(asignable):
    h = asignable
    esperando = Event()
    motor = get_engine()
    def observar(conn, cursor, sql, *args):
        if 'grupo_estudiante' in sql and 'FOR SHARE' in sql:
            esperando.set()
    sa.event.listen(motor, 'before_cursor_execute', observar)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with h.h.sesiones() as escritora:
                escritora.execute(sa.update(M).where(M.id_grupo_estudiante == h.matricula).values(activo=False))
                futuro = pool.submit(programar, h)
                try:
                    assert esperando.wait(timeout=10)
                    escritora.commit()
                    assert futuro.result(timeout=15).status_code == 403
                finally:
                    escritora.rollback()
    finally:
        sa.event.remove(motor, 'before_cursor_execute', observar)
    assert cantidades(h.h) == (0, 0, 0, 0)


def test_zona_obligatoria_ausente_no_deja_sesion_parcial(asignable, monkeypatch):
    h = asignable
    monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE')
    get_settings.cache_clear()
    with observar_lectura() as operaciones:
        respuesta = programar(h)
    assert respuesta.status_code == 503 and operaciones == []
    assert cantidades(h.h) == (0, 0, 0, 0)


@pytest.mark.parametrize('cambio', ['inactivo', 'rol', 'nombre_rol'])
def test_programador_revalida_cuenta_precargada_antes_de_cualquier_insert(asignable, cambio):
    from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
    from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
    from app.modules.scheduling.infrastructure.programming_access import (
        AutorizacionEspacioSQLAlchemy, programar_sesion_autorizada,
    )
    h = asignable
    with h.h.sesiones() as sesion:
        precargada = sesion.get(U, h.h.docente[0])
        rol_precargado = sesion.get(RolORM, precargada.id_rol)
        contexto = RepositorioUsuariosSQLAlchemy(sesion).obtener(str(precargada.id_usuario))
        docente_id = sesion.scalar(sa.select(IA.id_academico).where(
            IA.id_usuario == precargada.id_usuario, IA.sistema == 'SCHEDULING'))
        with h.h.sesiones.begin() as otra:
            actual = otra.get(U, precargada.id_usuario)
            if cambio == 'inactivo':
                actual.activo = False
            elif cambio == 'rol':
                actual.id_rol = 2
            else:
                otra.get(RolORM, actual.id_rol).nombre = 'CATALOGO_REVOCADO_LAB'
        # Conserva deliberadamente la identidad ORM anterior en esta Session.
        assert precargada.activo and precargada.id_rol == 1
        assert rol_precargado.nombre == 'DOCENTE'
        datos = ProgramarSesionRequest.model_validate(h.datos).model_dump()
        for campo in ('grupo_id', 'estudiantes_ids', 'fecha_limite_ingreso'):
            datos.pop(campo)
        with observar_lectura() as operaciones:
            with pytest.raises(IntegracionPendiente if cambio == 'nombre_rol' else AccesoDenegado):
                programar_sesion_autorizada(sesion, usuario=contexto, docente_id=docente_id,
                    autorizacion_espacio=AutorizacionEspacioSQLAlchemy(sesion), **datos)
        assert operaciones == []
    assert cantidades(h.h) == (0, 0, 0, 0)
