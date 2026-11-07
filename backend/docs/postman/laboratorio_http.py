"""Servidor efímero para Postman. No cambia app.main ni lee .env.

Reutiliza preparación administrativa y políticas LAB del test integral existente.
No constituye un comando de despliegue productivo ni recuperación de cuentas.
"""
from contextlib import contextmanager, ExitStack
import argparse
import getpass
import json
import os
from pathlib import Path
import socket
import sys
from threading import Thread
from uuid import UUID
import time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
sys.dont_write_bytecode=True


@contextmanager
def fixture(function, *args):
    """Adaptación explícita del generador pytest existente; ejecuta su finally."""
    gen=function.__wrapped__(*args)
    try:
        value=next(gen)
        yield value
    finally:
        gen.close()


def settings_lab():
    # Solo proceso actual; no escribe configuración ni muestra credenciales SQL.
    for k in list(os.environ):
        if k.startswith(('POSTGRES_','IDENTITY_','PARTICIPATION_')) or k in (
            'DATABASE_URL','TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL'):
            del os.environ[k]
    os.environ['SPS_TEST_IDENTITY_MAPPING_DOCKER']='1'
    from app.core.config import Settings,get_settings
    Settings.model_config['env_file']=None
    get_settings.cache_clear()


def secretos_interactivos():
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise RuntimeError('Use consola interactiva; no se aceptan secretos por argumentos ni archivos.')
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        datos={}
        for key,label in [('clave_admin','Clave sintética del ADMIN LAB'),
                          ('clave_docente','Clave sintética del DOCENTE LAB'),
                          ('codigo_estudiante','Código sintético del ESTUDIANTE LAB'),
                          ('codigo_ajeno','Código sintético del ESTUDIANTE AJENO LAB')]:
            valor=getpass.getpass(label+': ')
            if not valor or len(valor)>256:raise RuntimeError('Entrada de laboratorio vacía o demasiado larga.')
            datos[key]=valor
    return datos


def preparar(secretos, stack):
    import pytest
    import sqlalchemy as sa
    from app.modules.identity.infrastructure.models import UsuarioORM as U
    from app.modules.identity.infrastructure.credentials import obtener_hasheador
    from app.modules.scheduling.infrastructure.models import ConvocatoriaModel
    from app.modules.scheduling.domain.access_codes import hash_codigo
    from tests.integration.test_cases_graph_authoring import pg_autoria
    from tests.integration.cases.conftest import payload_valido
    from tests.integration.test_lab_student_journey import recorrido_lab
    sesiones=stack.enter_context(fixture(pg_autoria))
    patch=pytest.MonkeyPatch();stack.callback(patch.undo)
    h=stack.enter_context(fixture(recorrido_lab,sesiones,payload_valido.__wrapped__(),patch,lambda *a:None))
    # Solo la DB propia recién creada. Claves/códigos elegidos por el operador
    # sustituyen los aleatorios de esa fixture; únicamente se guardan hashes.
    with sesiones.begin() as s:
        admin=s.scalar(sa.select(U).where(U.id_rol==3))
        docente=s.scalar(sa.select(U).where(U.id_rol==1))
        assert admin and docente and admin.correo.endswith('@universidad.test')
        admin.clave_hash=obtener_hasheador().hash(secretos['clave_admin'])
        docente.clave_hash=obtener_hasheador().hash(secretos['clave_docente'])
        for alumno,key in [(h.titular,'codigo_estudiante'),(h.ajeno,'codigo_ajeno')]:
            s.get(ConvocatoriaModel,UUID(alumno.convocatoria)).codigo_hash=hash_codigo(secretos[key])
        s.flush()
        recurso={'correo_admin':admin.correo,'correo_docente':docente.correo,
            'id_docente':str(docente.id_usuario),'correo_estudiante':h.titular.correo,'correo_ajeno':h.ajeno.correo,
            'estudiante_id':str(h.titular.uuid),'convocatoria_id':h.titular.convocatoria,
            'sesion_id':str(h.sesion),'version_id':str(h.version),'id_asignacion':str(h.aid)}
        from app.modules.cases.infrastructure.models import VersionCasoModel
        version=s.get(VersionCasoModel,h.version);recurso['caso_uuid']=str(version.caso_id)
        from app.modules.scheduling.infrastructure.models import SesionProgramadaModel
        sesion=s.get(SesionProgramadaModel,h.sesion)
        recurso['espacio_academico_id']=str(sesion.espacio_academico_id)
    return h,recurso


def serve(application,port,stack):
    import uvicorn
    sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.bind(('127.0.0.1',port));sock.listen(128)
    stack.callback(sock.close)
    server=uvicorn.Server(uvicorn.Config(application,host='127.0.0.1',port=port,
        access_log=False,log_level='critical',log_config=None))
    thread=Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
    def stop():
        server.should_exit=True;thread.join(timeout=15)
        if thread.is_alive():raise RuntimeError('Servidor LAB no cerró dentro del plazo.')
    thread.start();stack.callback(stop)
    limite=time.monotonic()+15
    while not server.started:
        if not thread.is_alive() or time.monotonic()>limite:raise RuntimeError('Servidor LAB no disponible.')
        time.sleep(.05)
    return sock.getsockname()[1]


def run(args):
    settings_lab()
    secretos=secretos_interactivos()
    with ExitStack() as stack:
        h,recurso=preparar(secretos,stack)
        from app.main import app
        serve(app,args.puerto,stack)
        serve(h.lab.app,args.puerto_lab,stack)
        print('LAB PostgreSQL17 propio. Reloj fijo y políticas sintéticas del test integral; NO productivo.')
        print('MAIN: http://127.0.0.1:'+str(args.puerto))
        print('AISLADA: http://127.0.0.1:'+str(args.puerto_lab))
        print('Recursos sintéticos (sin códigos, claves, JWT ni conexión SQL):')
        print(json.dumps(recurso,ensure_ascii=False,indent=2))
        print('Complete las variables locales de Postman con estos recursos y las entradas que eligió.')
        print('Mantenga esta consola abierta. Enter finaliza servidores y elimina únicamente el contenedor propio.')
        input()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puerto',type=int,default=8765)
    parser.add_argument('--puerto-lab',type=int,default=8766)
    args=parser.parse_args()
    if args.puerto==args.puerto_lab or not all(1024<=p<=65535 for p in (args.puerto,args.puerto_lab)):
        parser.error('Use dos puertos distintos entre 1024 y 65535.')
    try:run(args)
    except (KeyboardInterrupt,EOFError):print('Laboratorio detenido; limpieza del contexto ejecutada.')
    except Exception:
        # Las excepciones de drivers podrían contener secretos: no reflejarlas.
        print('No fue posible completar el laboratorio. Verifique Docker, postgres:17 local y puertos libres.',file=sys.stderr)
        raise SystemExit(1)
