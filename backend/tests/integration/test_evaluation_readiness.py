"""Preparación interna real PG17. Ninguna política LAB equivale a nota oficial."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import timezone, timedelta
import json
from threading import Event
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.modules.identity.application.academic_identity import VinculoAcademico, SistemaAcademico
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Vinculos
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.identity.infrastructure.models import UsuarioORM as U
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.cases.infrastructure.models import CasoModel
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.evaluation_readiness import ConsultaPreparacionEvaluacionSQLAlchemy
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
from tests.integration.test_evaluation_result_storage import pg_resultados, c, evaluar  # noqa: F401
from tests.integration.test_participation_persistence import FECHA, intento


@pytest.fixture
def revision(c):
    # Datos sintéticos existentes; asociaciones administrativas explícitas a sus
    # propietarios de fixture, sin conversión de enteros ni backfill productivo.
    with c.sesiones.begin() as s:
        sesion = s.get(S, c.sesion)
        caso = s.get(CasoModel, c.version.caso_id)
        vinculos = Vinculos(s)
        for sistema, identificador in ((SistemaAcademico.CASES, caso.docente_creador_id),
                                      (SistemaAcademico.SCHEDULING, sesion.docente_id)):
            vinculos.agregar_verificado(VinculoAcademico(str(c.docente), sistema, identificador))
    with c.sesiones() as s:
        c.actor = RepositorioUsuariosSQLAlchemy(s).obtener(str(c.docente))
    return c


def consulta(c, **kw):
    return ConsultaPreparacionEvaluacionSQLAlchemy(**(dict(usuario=c.actor,
        crear_sesion=c.sesiones, fechas=FechasPersistencia(timezone.utc)) | kw))


def cerrar_sesion_fixture(c):
    # Preparación interna LAB, después de convocar. No acredita un cierre HTTP.
    with c.sesiones.begin() as s:
        sesion = s.get(S, c.sesion)
        sesion.estado = 'FINALIZADO'
        sesion.finalizado_en = (FECHA + timedelta(hours=1)).replace(tzinfo=timezone.utc)


def otro_convocado(c, *, retirado=False, matricula=True):
    with c.sesiones.begin() as s:
        u = U(id_rol=2, nombre='Alumno LAB revisión', correo=f'{uuid4().hex}@fixture.test', clave_hash='sin-login-LAB')
        s.add(u); s.flush()
        ident = uuid4()
        Vinculos(s).agregar_verificado(VinculoAcademico(str(u.id_usuario), SistemaAcademico.SCHEDULING, ident))
        if matricula:
            a = s.get(A, c.datos['id_asignacion'])
            s.add(M(id_grupo=a.id_grupo, id_estudiante=u.id_usuario, fecha_ingreso=FECHA))
        cid = crear_convocatoria(s, sesion_id=c.sesion, estudiante_id=ident).convocatoria_id
        if retirado:
            s.flush(); s.get(C, cid).estado = 'RETIRADA'
        return cid


@contextmanager
def solo_lectura(c):
    operaciones = []; configuraciones = []
    def sql(conn, cursor, sentencia, *args):
        prefijo = sentencia.lstrip().lower()
        if prefijo.startswith(('insert ', 'update ', 'delete ', 'truncate ', 'merge ', 'create ', 'alter ', 'drop ')):
            operaciones.append(prefijo.split()[0])
        if prefijo.startswith('set transaction read only'):
            configuraciones.append((conn.get_isolation_level(), True))
    def commit(conn): operaciones.append('commit')
    def flush(s, *args): operaciones.append('flush')
    sa.event.listen(c.engine, 'before_cursor_execute', sql)
    sa.event.listen(c.engine, 'commit', commit)
    sa.event.listen(c.sesiones.class_, 'before_flush', flush)
    try:
        yield
        assert operaciones == []
        assert configuraciones and all(x == ('REPEATABLE READ', True) for x in configuraciones)
    finally:
        sa.event.remove(c.engine, 'before_cursor_execute', sql)
        sa.event.remove(c.engine, 'commit', commit)
        sa.event.remove(c.sesiones.class_, 'before_flush', flush)


def test_sesion_completa_incluye_sin_participacion_y_retirada_sin_inferir_ausencias(revision):
    c = revision
    sin_p = otro_convocado(c)
    retirada = otro_convocado(c, retirado=True)
    sin_m = otro_convocado(c, matricula=False)
    cerrar_sesion_fixture(c)
    with solo_lectura(c):
        a = consulta(c).consultar(id_sesion=c.sesion)
        assert consulta(c).consultar(id_sesion=c.sesion) == a
    filas = {f.id_convocatoria: f for f in a.convocatorias}
    assert len(filas) == len(a.convocatorias) == 4
    assert filas[sin_p].id_participacion is None and filas[sin_p].intentos == ()
    assert filas[sin_p].pendientes == ('SIN_INTENTOS_REQUIERE_REVISION_DOCENTE',)
    assert 'TRATAMIENTO_RETIRO_PENDIENTE' in filas[retirada].pendientes
    assert 'MATRICULA_NO_INEQUIVOCA' in filas[sin_m].pendientes
    assert not a.publicable and 'CORTE_PADRON_ACADEMICO_PENDIENTE' in a.pendientes
    with c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(P).where(P.convocatoria_id.in_([sin_p, retirada, sin_m]))) == 0


def test_resultado_tecnico_se_reproduce_no_se_consolida_ni_expone_nota(revision):
    c = revision; tecnico = evaluar(c)
    cerrar_sesion_fixture(c)
    with solo_lectura(c):
        a = consulta(c).consultar(id_sesion=c.sesion)
    assert (a.version_caso_id, a.rubrica_id, a.version_regla) == (c.version.id, c.version.rubrica.id, c.version.rubrica.version_regla)
    f = a.convocatorias[0]
    assert f.intentos[0].id_resultado_tecnico == tecnico.id_resultado
    assert f.pendientes == ('RESULTADO_LABORATORIO_NO_OFICIAL',)
    assert not a.publicable
    documento = json.dumps(asdict(a), default=str)
    assert all(x not in documento for x in ('nota_final', 'puntaje', 'procedencia', 'es_correcta', 'justificacion', '@', 'codigo_hash'))


@pytest.mark.parametrize('problema', ['ajeno', 'estudiante', 'inactivo', 'sin_vinculo', 'ambiguo', 'administrador_sin_docente'])
def test_autorizacion_persistente_no_confia_en_roles_del_contexto(revision, problema):
    c = revision; actor = c.actor
    with c.sesiones.begin() as s:
        if problema == 'estudiante': actor = replace(c.actor, id_usuario=str(c.alumno))
        elif problema == 'inactivo': s.get(U, c.docente).activo = False
        elif problema == 'sin_vinculo': s.execute(sa.delete(IA).where(IA.id_usuario == c.docente))
        elif problema == 'ambiguo':
            Vinculos(s).agregar_verificado(VinculoAcademico(str(c.docente), SistemaAcademico.SCHEDULING, uuid4()))
        elif problema == 'administrador_sin_docente':
            from app.modules.identity.infrastructure.models import RolORM
            if s.get(RolORM, 3) is None: s.add(RolORM(id_rol=3, nombre='ADMINISTRADOR')); s.flush()
            s.get(U, c.docente).id_rol = 3
        else:
            u = U(id_rol=1, nombre='Ajeno LAB', correo=f'{uuid4().hex}@fixture.test', clave_hash='sin-login-LAB')
            s.add(u); s.flush(); actor = replace(c.actor, id_usuario=str(u.id_usuario))
            for sistema in (SistemaAcademico.CASES, SistemaAcademico.SCHEDULING):
                Vinculos(s).agregar_verificado(VinculoAcademico(str(u.id_usuario), sistema, uuid4()))
    with solo_lectura(c), pytest.raises((AccesoDenegado, IntegracionPendiente)):
        consulta(c, usuario=actor).consultar(id_sesion=c.sesion)


def test_sesion_inexistente_y_grupo_fuera_del_ambito_no_devuelven_datos(revision):
    from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM
    c = revision
    with pytest.raises(AccesoDenegado): consulta(c).consultar(id_sesion=uuid4())
    with c.sesiones.begin() as s:
        grupo = s.get(GrupoAcademicoORM, s.get(A, c.datos['id_asignacion']).id_grupo)
        grupo.id_profesor = c.alumno  # Inconsistencia sintética permitida por FK; no conceder acceso.
    with pytest.raises(IntegracionPendiente): consulta(c).consultar(id_sesion=c.sesion)


def test_lecturas_concurrentes_conservan_resultado_y_no_escriben(revision):
    c = revision; evaluar(c)
    with solo_lectura(c), ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(consulta(c).consultar, id_sesion=c.sesion)
        b = pool.submit(consulta(c).consultar, id_sesion=c.sesion)
        assert a.result(timeout=10) == b.result(timeout=10)


def test_ningun_intento_se_elije_ni_se_vence_al_consultar(revision):
    c = revision
    with c.sesiones.begin() as s:
        permiso = PermisoIntentoExtraORM(id_participacion=c.pk, id_profesor=c.docente,
            cantidad_autorizada=1, justificacion='Solo fixture, no política oficial', fecha_autorizacion=FECHA)
        s.add(permiso); s.flush(); permiso_id = permiso.id_permiso_extra
    segundo = intento(c, c.pk, numero_intento=2, id_permiso_extra=permiso_id)
    with solo_lectura(c): a = consulta(c).consultar(id_sesion=c.sesion)
    f = a.convocatorias[0]
    assert [i.id_intento for i in f.intentos] == [c.ik, segundo]
    assert f.intentos[1].estado == 'EN_CURSO'
    assert 'CONSOLIDACION_REPETICIONES_PENDIENTE' in f.pendientes
    assert 'INTENTO_SIN_CIERRE_PERSISTIDO' in f.pendientes and not a.publicable
    with c.sesiones() as s: assert s.get(I, segundo).estado == 'EN_CURSO'


def test_rollback_y_snapshot_concurrente_no_mezclan_estados(revision):
    c = revision
    with c.engine.connect() as conn:
        tx = conn.begin()
        conn.execute(sa.update(C).where(C.id == c.datos['convocatoria_id']).values(estado='RETIRADA'))
        tx.rollback()
    preparada = Event(); continuar = Event()
    def interceptar(conn, cursor, sentencia, *args):
        if sentencia.lstrip().startswith('SELECT convocatoria.') and 'ORDER BY' in sentencia:
            preparada.set(); assert continuar.wait(10)
    sa.event.listen(c.engine, 'before_cursor_execute', interceptar)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            futuro = pool.submit(consulta(c).consultar, id_sesion=c.sesion)
            assert preparada.wait(10)
            with c.sesiones.begin() as s:
                s.get(C, c.datos['convocatoria_id']).estado = 'RETIRADA'
            continuar.set()
            a = futuro.result(timeout=10)
    finally:
        continuar.set(); sa.event.remove(c.engine, 'before_cursor_execute', interceptar)
    assert a.convocatorias[0].estado == 'ACTIVA'
    assert consulta(c).consultar(id_sesion=c.sesion).convocatorias[0].estado == 'RETIRADA'


def test_fallo_sql_no_devuelve_informe_parcial_y_recupera(revision):
    c = revision
    def fallar(conn, cursor, sentencia, *args):
        if sentencia.lstrip().startswith('SELECT convocatoria.'):
            conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(c.engine, 'before_cursor_execute', fallar)
    try:
        with pytest.raises(IntegracionPendiente): consulta(c).consultar(id_sesion=c.sesion)
    finally: sa.event.remove(c.engine, 'before_cursor_execute', fallar)
    assert len(consulta(c).consultar(id_sesion=c.sesion).convocatorias) == 1
