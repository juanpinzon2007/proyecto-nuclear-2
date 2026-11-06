"""Documentos SINTETICOS, evidencia SOLO LAB; PG17 nuevo, ninguna ruta oficial."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from threading import Barrier, Event
import time
from types import SimpleNamespace
from hashlib import sha256
from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import select, text, event, inspect, MetaData
from sqlalchemy.exc import IntegrityError

from app.modules.identity.infrastructure.consent_repository import RepositorioDocumentosConsentimientoSQLAlchemy as Repo, FuenteConsentimientoSQLAlchemy as Fuente
from app.modules.identity.infrastructure.consent_document_models import DocumentoConsentimientoVersionORM as D, SeleccionConsentimientoORM as S
from app.modules.identity.infrastructure.consent import ServicioConsentimientoSQLAlchemy
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.participation.application.errors import AccesoDenegado as ParticipacionDenegada
from app.modules.participation.infrastructure.models import ParticipacionModel as P
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.cases.infrastructure.models import VersionCasoModel
from app.modules.cases.domain.enums import EstadoCaso
from tests.integration.test_participation_provision import convocada, pg_grafo, servicio, argumentos, filas  # noqa: F401
from tests.integration.test_consent_before_provision import observar_p
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic

PARENT='20261105_waiting_admission'
HEAD='20261106_consent_versions'


def publicar(c,s,version='1'):
    texto=f'Texto {version} SINTETICO SOLO LAB, no aprobado institucionalmente.'
    return Repo(s).publicar(referencia=f'SQL-{c.datos["id_asignacion"]}-{version}',documento_id=f'DOC-LAB-{c.datos["id_asignacion"]}',version=version,
        original=texto.encode(),tipo_media='text/plain; charset=utf-8',texto=texto,
        autoridad_aprobadora='AUTORIDAD FICTICIA SOLO LAB',aprobado_en=c.ahora-timedelta(days=1),
        evidencia_aprobacion=b'EVIDENCIA SINTETICA NO INSTITUCIONAL',publicado_por=c.docente,
        publicado_en=c.ahora-timedelta(hours=1),vigente_desde=c.ahora-timedelta(hours=1))


def elegir(c,s,pk):
    Repo(s).seleccionar(id_asignacion=c.datos['id_asignacion'],id_version_documento=pk,
        seleccionado_por=c.docente,ahora=c.ahora)


def interno(c,s):
    return ServicioConsentimientoSQLAlchemy(s,fuente=Fuente(s),fechas=FechasPersistencia(timezone.utc),
        reloj=SimpleNamespace(ahora=lambda:c.ahora))


def aceptar(c,s):
    d=Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
    return interno(c,s).aceptar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],
        referencia_presentada=d.referencia,huella_presentada=d.huella,acepta=True)


@pytest.fixture
def documento(convocada):
    c=convocada
    with c.sesiones.begin() as s:
        c.documento=publicar(c,s);elegir(c,s,c.documento)
    return c


def test_documento_fuente_aceptacion_idempotente_y_vinculo_historico(documento):
    c=documento
    with c.sesiones.begin() as s:
        c.explicito=aceptar(c,s)
        assert aceptar(c,s)==c.explicito
    with c.sesiones() as s:
        d=Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
        fila=s.get(C,c.explicito)
        assert fila.id_version_documento==d.id_version_documento==c.documento
        assert fila.huella_aceptada==d.huella and fila.aceptacion_explicita is True
    vinculada=servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    with c.sesiones() as s:
        p=s.get(P,vinculada.participacion.id_participacion)
        assert p.id_consentimiento==c.explicito and p.id_asignacion==c.datos['id_asignacion']
        assert s.get(D,c.documento).sha256_original==sha256(d.texto.encode()).hexdigest()
    with c.sesiones.begin() as s:
        nuevo=publicar(c,s,'2');elegir(c,s,nuevo)
        anterior=Fuente(s).historico(f'SQL-{c.datos["id_asignacion"]}-1')
        assert anterior.id_version_documento==c.documento and not anterior.vigente
        assert Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora).version=='2'
    with c.sesiones() as s:
        assert s.get(P,vinculada.participacion.id_participacion).id_consentimiento==c.explicito
    with pytest.raises(IntegrityError),c.sesiones.begin() as s:
        s.get(P,vinculada.participacion.id_participacion).id_consentimiento=c.consentimiento


@pytest.mark.parametrize('problema',['ausente','legado','ajena','sustituida'])
def test_falta_evidencia_sql_rechaza_antes_del_insert_p(documento,problema):
    c=documento
    with c.sesiones.begin() as s:
        if problema=='ausente':s.delete(s.get(C,c.consentimiento))
        elif problema=='legado':
            viejo=s.get(C,c.consentimiento);viejo.version_texto=s.get(D,c.documento).referencia
            assert viejo.id_version_documento is None and viejo.aceptacion_explicita is None
        if problema!='ausente' and problema!='legado':c.explicito=aceptar(c,s)
        if problema=='ajena':
            from tests.integration.test_participation_persistence import contexto
            from tests.integration.test_attempt_state import principal
            otro=contexto(c.engine);c.usuario=principal(otro)
        if problema=='sustituida':elegir(c,s,publicar(c,s,'2'))
    with observar_p(c) as sql,pytest.raises((ParticipacionDenegada,IntegracionPendiente)):
        servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    assert sql==[] and filas(c)==([],[])


@pytest.mark.parametrize('operacion',['doc_update','doc_delete','hash_insert','aceptacion','publicacion_repetida'])
def test_sql_rechaza_evidencia_y_publicacion_inconsistentes(documento,operacion):
    c=documento
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    with pytest.raises(IntegrityError),c.sesiones.begin() as s:
        if operacion=='doc_update':s.get(D,c.documento).texto='Sustitución SQL'
        elif operacion=='doc_delete':s.delete(s.get(D,c.documento))
        elif operacion=='publicacion_repetida':publicar(c,s)
        elif operacion=='aceptacion':s.get(C,c.explicito).huella_aceptada='0'*64
        else:
            # DML directo con bytes reales y hash deliberadamente incompatible.
            datos=dict(s.execute(select(D.__table__).where(D.id_version_documento==c.documento)).mappings().one())
            datos.pop('id_version_documento');datos.update(referencia='BAD-LAB',version='BAD-LAB',sha256_original='0'*64)
            s.execute(D.__table__.insert().values(**datos))
    with c.sesiones() as s:assert s.get(D,c.documento).texto.startswith('Texto 1 ')


def test_selector_separado_no_actualiza_asignacion_archivada(documento):
    c=documento;escrituras=[]
    def observar(conn,cursor,statement,params,context,many):
        if statement.lstrip().lower().startswith('update asignacion_caso'):escrituras.append(statement)
    with c.sesiones.begin() as s:s.get(VersionCasoModel,c.version.id).estado=EstadoCaso.ARCHIVADO
    event.listen(c.engine,'before_cursor_execute',observar)
    try:
        with c.sesiones.begin() as s:
            nuevo=publicar(c,s,'2');elegir(c,s,nuevo)
            assert Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora).version=='2'
    finally:event.remove(c.engine,'before_cursor_execute',observar)
    assert escrituras==[]


def test_aceptaciones_sql_concurrentes_mismo_id(documento):
    c=documento;barrera=Barrier(2)
    def ejecutar(_):
        barrera.wait(timeout=10)
        with c.sesiones.begin() as s:return aceptar(c,s)
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(ejecutar,range(2)))
    assert ids[0]==ids[1]


def test_rollback_conserva_selector_y_no_persiste_aceptacion(documento):
    c=documento
    with pytest.raises(RuntimeError):
        with c.sesiones.begin() as s:
            nuevo=publicar(c,s,'2');elegir(c,s,nuevo);aceptar(c,s)
            raise RuntimeError('Fallo exclusivamente LAB')
    with c.sesiones() as s:
        assert Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora).version=='1'
        assert s.scalar(select(C.id_consentimiento).where(C.id_version_documento==c.documento)) is None


def test_revocacion_durante_intento_moderno_rechazada(documento):
    c=documento
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    from tests.integration.test_attempt_start import InicioLaboratorio
    resultado=servicio(c,crear_fuente_consentimiento=Fuente,politica_inicio=InicioLaboratorio(f'SQL-{c.datos["id_asignacion"]}-1')).iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=c.explicito)
    with c.sesiones() as s,pytest.raises(AccesoDenegado):
        interno(c,s).comprobar_revocacion(usuario=c.usuario,id_consentimiento=c.explicito)
    with pytest.raises(IntegrityError),c.sesiones.begin() as s:
        s.get(C,c.explicito).fecha_revocacion=c.ahora.replace(tzinfo=None)
    assert resultado is not None


def test_upgrade_downgrade_vacio_y_sin_tablas_productivas():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as s:
            cfg=config_alembic(s);command.upgrade(cfg,PARENT)
            antes=set(inspect(s).get_table_names())
            command.upgrade(cfg,HEAD)
            assert set(inspect(s).get_table_names())==antes|{'documento_consentimiento_version','seleccion_consentimiento'}
            assert s.scalar(text('SELECT count(*) FROM documento_consentimiento_version'))==0
            command.downgrade(cfg,PARENT)
            assert set(inspect(s).get_table_names())==antes
            command.upgrade(cfg,HEAD)


def test_downgrade_rechaza_perder_publicacion(documento):
    c=documento
    with pytest.raises(RuntimeError,match='evidencia documental'):
        with c.engine.begin() as s:command.downgrade(config_alembic(s),PARENT)
    with c.sesiones() as s:assert s.get(D,c.documento) is not None


def esperar_lock_real(c):
    limite=time.monotonic()+8
    while time.monotonic()<limite:
        with c.engine.connect() as control:
            if control.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND wait_event_type='Lock')")):
                return
        Event().wait(.02)
    raise AssertionError('No se observó la espera PostgreSQL real.')


def test_provision_gana_publicacion_espera_y_conserva_enlace(documento):
    c=documento;tomado=Event();liberar=Event()
    with c.sesiones.begin() as s:
        c.explicito=aceptar(c,s);nuevo=publicar(c,s,'2')
    def pausa(conn,cursor,statement,params,context,many):
        if statement.lstrip().lower().startswith('insert into participacion'):
            tomado.set();assert liberar.wait(15)
    def seleccionar():
        with c.sesiones.begin() as s:elegir(c,s,nuevo)
    event.listen(c.engine,'before_cursor_execute',pausa)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(lambda:servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c)))
            assert tomado.wait(10)
            b=pool.submit(seleccionar);esperar_lock_real(c)
            liberar.set();p=a.result(timeout=15);b.result(timeout=15)
    finally:liberar.set();event.remove(c.engine,'before_cursor_execute',pausa)
    with c.sesiones() as s:
        assert s.get(P,p.participacion.id_participacion).id_consentimiento==c.explicito
        assert Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora).version=='2'


def test_publicacion_gana_provision_revalida_y_no_inserta(documento):
    c=documento
    with c.sesiones.begin() as s:
        aceptar(c,s);nuevo=publicar(c,s,'2')
    with c.sesiones() as publicando,ThreadPoolExecutor(max_workers=1) as pool:
        elegir(c,publicando,nuevo)
        tarea=pool.submit(lambda:servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c)))
        esperar_lock_real(c);publicando.commit()
        with pytest.raises(ParticipacionDenegada):tarea.result(timeout=15)
    assert filas(c)==([],[])


def test_rollback_despues_insert_p_revierte_el_enlace(documento):
    c=documento
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    def fallar(conn,cursor,statement,params,context,many):
        if statement.lstrip().lower().startswith('insert into participacion'):raise RuntimeError('Fallo LAB tras INSERT')
    event.listen(c.engine,'after_cursor_execute',fallar)
    try:
        with pytest.raises(RuntimeError):servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    finally:event.remove(c.engine,'after_cursor_execute',fallar)
    assert filas(c)==([],[])
    with c.sesiones() as s:assert s.get(C,c.explicito).id_version_documento==c.documento


def test_fuente_sin_selector_y_documento_futuro_fallan_cerrados(convocada):
    c=convocada
    with c.sesiones() as s,pytest.raises(IntegracionPendiente):Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
    with c.sesiones.begin() as s:
        pk=publicar(c,s)
        with pytest.raises(IntegracionPendiente):
            Repo(s).seleccionar(id_asignacion=c.datos['id_asignacion'],id_version_documento=pk,
                seleccionado_por=c.docente,ahora=c.ahora-timedelta(days=3))


def test_upgrade_preserva_p_y_aceptacion_legadas_sin_inventar_enlace():
    from sqlalchemy.orm import sessionmaker
    from app.modules.identity.infrastructure.models import RolORM,UsuarioORM
    from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
    from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
    from app.modules.scheduling.domain.access_codes import hash_codigo
    from tests.integration.test_assignment_bridge import preparar,FECHA
    with motor_postgresql_desechable() as engine:
        with engine.begin() as c:
            command.upgrade(config_alembic(c),PARENT)
            c.execute(RolORM.__table__.insert(),[{'id_rol':1,'nombre':'DOCENTE'},{'id_rol':2,'nombre':'ESTUDIANTE'}])
        factory,version,valores=preparar(engine)
        with factory.begin() as c:
            alumno=UsuarioORM(id_rol=2,nombre='Alumno legado SOLO LAB',correo=f'{uuid4()}@fixture.test',clave_hash='sin-login')
            c.add(alumno);c.flush();academico=uuid4()
            c.add(IdentidadAcademicaORM(id_usuario=alumno.id_usuario,sistema='SCHEDULING',id_academico=academico))
            m=GrupoEstudianteORM(id_grupo=valores['id_grupo'],id_estudiante=alumno.id_usuario,fecha_ingreso=FECHA)
            a=AsignacionCasoModel(**valores);c.add_all([m,a]);c.flush()
            # Reflejo de la revisión ANTERIOR, sin añadir columnas auxiliares.
            meta=MetaData();meta.reflect(c.connection(),only=['consentimiento','convocatoria','participacion'])
            ct,cv,pt=[meta.tables[n] for n in ('consentimiento','convocatoria','participacion')]
            aceptacion=c.scalar(ct.insert().values(id_estudiante=alumno.id_usuario,version_texto='legado-no-verificado',fecha_aceptacion=FECHA).returning(ct.c.id_consentimiento))
            convocatoria=uuid4();c.execute(cv.insert().values(id=convocatoria,sesion_id=valores['sesion_programada_id'],estudiante_id=academico,codigo_hash=hash_codigo('CODIGO-SOLO-LAB'),estado='ACTIVA'))
            pk=c.scalar(pt.insert().values(id_asignacion=a.id_asignacion,id_grupo_estudiante=m.id_grupo_estudiante,convocatoria_id=convocatoria,estado='pendiente',fecha_registro=FECHA).returning(pt.c.id_participacion))
            antes_c=tuple(c.execute(select(ct).where(ct.c.id_consentimiento==aceptacion)).one())
            antes_p=tuple(c.execute(select(pt).where(pt.c.id_participacion==pk)).one())
        with engine.begin() as c:
            cfg=config_alembic(c);command.upgrade(cfg,HEAD)
            assert tuple(c.execute(select(ct).where(ct.c.id_consentimiento==aceptacion)).one())==antes_c
            assert tuple(c.execute(select(pt).where(pt.c.id_participacion==pk)).one())==antes_p
            assert c.scalar(text('SELECT id_consentimiento FROM participacion WHERE id_participacion=:p'),{'p':pk}) is None
            assert c.scalar(text('SELECT id_version_documento FROM consentimiento WHERE id_consentimiento=:p'),{'p':aceptacion}) is None
            assert c.scalar(text('SELECT count(*) FROM documento_consentimiento_version'))==0
            command.downgrade(cfg,PARENT)
            assert tuple(c.execute(select(ct).where(ct.c.id_consentimiento==aceptacion)).one())==antes_c
            assert tuple(c.execute(select(pt).where(pt.c.id_participacion==pk)).one())==antes_p


def test_p_existente_sin_intento_cambio_documento_conserva_historia_y_cierra_inicio(documento):
    from app.modules.participation.application.errors import ReglaPendiente
    c=documento
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    p=servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    with c.sesiones.begin() as s:elegir(c,s,publicar(c,s,'2'))
    with pytest.raises(ParticipacionDenegada):
        servicio(c,crear_fuente_consentimiento=Fuente).iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=c.explicito)
    recuperada=servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    assert not recuperada.creada and recuperada.participacion==p.participacion
    con,ints=filas(c);assert len(con)==1 and con[0]['id_consentimiento']==c.explicito and not ints


@pytest.mark.parametrize('ganador',['inicio','revocacion'])
def test_carrera_inicio_revocacion_aceptacion_sql(documento,ganador):
    from tests.integration.test_attempt_start import InicioLaboratorio
    c=documento
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    def iniciar():
        return servicio(c,crear_fuente_consentimiento=Fuente,politica_inicio=InicioLaboratorio(f'SQL-{c.datos["id_asignacion"]}-1')).iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=c.explicito)
    if ganador=='revocacion':
        with c.sesiones() as rev,ThreadPoolExecutor(max_workers=1) as pool:
            rev.get(C,c.explicito).fecha_revocacion=c.ahora.replace(tzinfo=None);rev.flush()
            a=pool.submit(iniciar);esperar_lock_real(c);rev.commit()
            with pytest.raises(ParticipacionDenegada):a.result(timeout=15)
        assert filas(c)[1]==[]
    else:
        tomado=Event();liberar=Event()
        def pausa(conn,cursor,statement,params,context,many):
            if statement.lstrip().lower().startswith('insert into intento'):
                tomado.set();assert liberar.wait(15)
        def revocar():
            with c.sesiones.begin() as rev:rev.get(C,c.explicito).fecha_revocacion=c.ahora.replace(tzinfo=None)
        event.listen(c.engine,'before_cursor_execute',pausa)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a=pool.submit(iniciar);assert tomado.wait(10)
                b=pool.submit(revocar);esperar_lock_real(c);liberar.set()
                a.result(timeout=15)
                with pytest.raises(IntegrityError):b.result(timeout=15)
        finally:liberar.set();event.remove(c.engine,'before_cursor_execute',pausa)
        assert len(filas(c)[1])==1
        with c.sesiones() as s:assert s.get(C,c.explicito).fecha_revocacion is None


def test_inicio_directo_existente_tampoco_elude_version_vigente(documento):
    from app.modules.participation.infrastructure.start import crear_facade_inicio_8b
    from tests.integration.test_attempt_start import IngresoLaboratorio,InicioLaboratorio
    c=documento
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    p=servicio(c,crear_fuente_consentimiento=Fuente).obtener_o_crear(**argumentos(c))
    with c.sesiones.begin() as s:elegir(c,s,publicar(c,s,'2'))
    facade=crear_facade_inicio_8b(usuario=c.usuario,id_participacion=p.participacion.id_participacion,
        reloj=SimpleNamespace(ahora=lambda:c.ahora),fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones,
        codigo_acceso=c.codigo,politica_ingreso=IngresoLaboratorio(),
        politica_inicio=InicioLaboratorio(f'SQL-{c.datos["id_asignacion"]}-1'))
    with pytest.raises(ParticipacionDenegada):
        facade.iniciar_intento(id_estudiante=c.alumno,id_participacion=p.participacion.id_participacion,id_consentimiento=c.explicito)
    assert filas(c)[1]==[]


def test_sql_no_convierte_aceptacion_legada_en_evidencia(documento):
    c=documento
    with pytest.raises(IntegrityError) as fallo,c.sesiones.begin() as s:
        vieja=s.get(C,c.consentimiento)
        vieja.id_version_documento=c.documento;vieja.aceptacion_explicita=True
        vieja.huella_aceptada=s.get(D,c.documento).sha256_texto
        vieja.version_texto=s.get(D,c.documento).referencia
    assert fallo.value.orig.sqlstate=='23514'
    with c.sesiones() as s:assert s.get(C,c.consentimiento).id_version_documento is None


def test_p_legada_no_se_reclasifica_por_presentar_aceptacion_nueva(documento):
    from tests.integration.test_participation_persistence import participacion, intento
    from app.modules.participation.application.errors import ReglaPendiente
    from app.modules.participation.infrastructure.start import crear_facade_inicio_8b
    from tests.integration.test_attempt_start import IngresoLaboratorio,InicioLaboratorio
    c=documento;pk=participacion(c)  # Forma legada admitida por transición; no prueba consentimiento.
    with c.sesiones.begin() as s:c.explicito=aceptar(c,s)
    f=crear_facade_inicio_8b(usuario=c.usuario,id_participacion=pk,reloj=SimpleNamespace(ahora=lambda:c.ahora),
        fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones,codigo_acceso=c.codigo,
        politica_ingreso=IngresoLaboratorio(),politica_inicio=InicioLaboratorio(f'SQL-{c.datos["id_asignacion"]}-1'))
    with pytest.raises(ReglaPendiente):f.iniciar_intento(id_estudiante=c.alumno,id_participacion=pk,id_consentimiento=c.explicito)
    with pytest.raises(IntegrityError):intento(c,pk,id_consentimiento=c.explicito)
    with c.sesiones() as s:assert s.get(P,pk).id_consentimiento is None
    assert filas(c)[1]==[]


@pytest.mark.parametrize('aislamiento',['REPEATABLE READ','SERIALIZABLE'])
def test_fuente_vigente_no_usa_snapshot_anterior_de_selector(documento,aislamiento,record_property):
    from sqlalchemy.orm import Session
    c=documento
    with c.engine.connect().execution_options(isolation_level=aislamiento) as connection,Session(bind=connection) as s:
        # Fijar una instantánea ANTES de que otro proceso confirme una selección.
        s.execute(text('SELECT count(*) FROM rol'))
        with c.sesiones.begin() as otro:elegir(c,otro,publicar(c,otro,'2'))
        with c.sesiones() as actual:
            assert Fuente(actual).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora).version=='2'
        with pytest.raises(IntegracionPendiente):
            anterior=Fuente(s).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
            record_property('version_devuelta_por_snapshot',anterior.version)
        s.rollback()
