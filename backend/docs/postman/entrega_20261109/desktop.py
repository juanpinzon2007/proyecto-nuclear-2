"""Preparación Windows/Postman Desktop. SOLO laboratorio sintético, no despliegue."""
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass, field
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
from uuid import uuid4

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
sys.path.insert(0,str(OUT.parent))
sys.dont_write_bytecode=True
import laboratorio as principal
import laboratorio_publicacion as reportes
lab=principal.lab

ARCHIVOS={
    'principal':'Proyecto_Nuclear_entrega_20261109.postman_collection.json',
    'reportes':'Proyecto_Nuclear_reportes_oficiales.postman_collection.json',
    'worker':'Proyecto_Nuclear_worker_20261109.postman_collection.json',
}
ETIQUETAS={'principal':'RECORRIDO PRINCIPAL','reportes':'PUBLICACION Y REPORTES RF-16','worker':'WORKER RF-19'}


def comprobar_dependencias():
    faltan=[p for p in ('fastapi','sqlalchemy','psycopg','uvicorn','pytest','httpx','jwt','pwdlib','openpyxl','reportlab')
            if importlib.util.find_spec(p) is None]
    if faltan:
        raise RuntimeError('Faltan dependencias: '+', '.join(faltan)+'. Instale con .\\.venv\\Scripts\\python.exe -m pip install -e "./backend[dev]".')
    for args in (['docker','info','--format','{{.ServerVersion}}'],['docker','image','inspect','docker.io/library/postgres:17']):
        try:r=subprocess.run(args,capture_output=True,timeout=20)
        except (OSError,subprocess.TimeoutExpired):raise RuntimeError('Docker Engine no disponible; reanúdelo sin detener recursos ajenos.') from None
        if r.returncode:raise RuntimeError('Docker Engine o imagen postgres:17 no disponible; no se reutilizará una base existente.')


def puertos_ocupados():
    usados=[]
    for port in (8765,8766):
        with socket.socket() as s:
            try:s.bind(('127.0.0.1',port))
            except OSError:usados.append(port)
    return usados


def carpeta_privada():
    carpeta=Path(tempfile.mkdtemp(prefix='ProyectoNuclearPostman-')).resolve()
    try:
        if os.name=='nt':
            r=subprocess.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,text=True,errors='replace',check=True)
            sid=next(x for row in csv.reader(r.stdout.splitlines()) for x in row if re.fullmatch(r'S-1-[0-9-]+',x))
            r=subprocess.run(['icacls',str(carpeta),'/inheritance:r','/grant:r',f'*{sid}:(OI)(CI)F'],capture_output=True,check=True)
        else:carpeta.chmod(0o700)
    except Exception:
        carpeta.rmdir()  # Aún vacía y creada por este proceso; nunca borrado recursivo.
        raise RuntimeError('No se pudo restringir el acceso al Environment temporal.') from None
    return carpeta


@dataclass
class PreparacionDesktop:
    modo: str
    carpeta: Path
    environment: Path
    coleccion: Path
    nombre_environment: str
    nombre_coleccion: str
    primera_solicitud: str
    contexto: object=field(repr=False)
    def verificar_sql(self):
        import sqlalchemy as sa
        from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I, PasoSimulacionModel as Paso
        from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
        from app.modules.participation.infrastructure.academic_results_models import PublicacionEvaluacionModel as Pub
        if self.modo=='worker':return principal.estado_worker(self.contexto)
        c=self.contexto.c if self.modo=='reportes' else self.contexto
        sid=c.sesion
        cid=c.datos['convocatoria_id'] if self.modo=='reportes' else __import__('uuid').UUID(c.titular.convocatoria)
        with c.sesiones() as db:
            p=db.scalar(sa.select(P).where(P.convocatoria_id==cid));ids=db.scalars(sa.select(I.id_intento).where(I.id_participacion==p.id_participacion)).all() if p else []
            return dict(participaciones=db.scalar(sa.select(sa.func.count()).select_from(P).where(P.convocatoria_id==cid)),
                intentos=len(ids),respuestas=db.scalar(sa.select(sa.func.count()).select_from(Paso).where(Paso.id_intento.in_(ids))),
                resultados=db.scalar(sa.select(sa.func.count()).select_from(R).where(R.id_intento.in_(ids))),
                publicaciones=db.scalar(sa.select(sa.func.count()).select_from(Pub).where(Pub.sesion_id==sid)))

    def worker(self):
        if self.modo!='worker':raise RuntimeError('Worker solo habilitado en su propio laboratorio.')
        return principal.worker_una_vez(self.contexto)


@contextmanager
def preparar(modo):
    if modo not in ARCHIVOS:raise ValueError('Modo de laboratorio inválido.')
    comprobar_dependencias()
    # Solo afecta a este proceso: elimina conexiones heredadas y deshabilita .env.
    lab.settings_lab()
    carpeta=carpeta_privada();propios=[]
    try:
        with ExitStack() as stack:
            claves={k:secrets.token_urlsafe(32) for k in ('clave_admin','clave_docente','codigo_estudiante','codigo_ajeno')}
            h,recursos=(reportes.preparar(claves,stack) if modo=='reportes' else principal.preparar(claves,stack))
            from app.main import app
            # Puerto 0: el sistema reserva uno libre, sin cerrar ni sustituir otro servidor.
            recursos['base_url']='http://127.0.0.1:'+str(lab.serve(app,0,stack))
            recursos['base_url_laboratorio']=''
            if modo=='principal':recursos['base_url_laboratorio']='http://127.0.0.1:'+str(lab.serve(h.lab.app,0,stack))
            ident=uuid4().hex
            template=json.loads((OUT/'Proyecto_Nuclear_entrega_20261109.postman_environment.json').read_text(encoding='utf-8'))
            valores={x['key']:dict(x) for x in template['values']}
            datos={**recursos,**claves,'laboratorio_confirmado':'true','permitir_escrituras_laboratorio':'true',
                'laboratorio_modo':modo,'laboratorio_id':ident,'paso_'+modo:'0'}
            for k,v in datos.items():
                valores.setdefault(k,dict(key=k,type='default',enabled=True))
                valores[k]['value']=str(v)
            for k,v in valores.items():
                if any(t in k for t in ('token','clave','codigo')):v['type']='secret'
                if k.startswith('token_'):v['value']=''
            nombre='NUCLEAR LAB — '+ETIQUETAS[modo]+' — '+ident[:8]
            environment=dict(id=ident,name=nombre,values=list(valores.values()),_postman_variable_scope='environment')
            coleccion=json.loads((OUT/ARCHIVOS[modo]).read_text(encoding='utf-8'))
            assert coleccion['info']['schema'].endswith('/collection/v2.1.0/collection.json')
            envfile=carpeta/'Environment_ACTIVO.postman_environment.json'
            colfile=carpeta/ARCHIVOS[modo]
            for path,data in ((envfile,environment),(colfile,coleccion)):
                with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
                propios.append(path)
            yield PreparacionDesktop(modo,carpeta,envfile,colfile,nombre,coleccion['info']['name'],coleccion['item'][0]['name'],h)
    finally:
        # Solo nuestros dos archivos exactos; conservar descargas/capturas añadidas por el usuario.
        for p in propios:
            if p.parent.resolve()!=carpeta:raise RuntimeError('Ruta temporal fuera del laboratorio propio.')
            p.unlink(missing_ok=True)
        try:carpeta.rmdir()
        except OSError:pass


def ejecutar(modo):
    usados=puertos_ocupados()
    if usados:print('Puertos ya ocupados: '+', '.join(map(str,usados))+'. Se conservarán; se usarán otros libres.')
    print('Preparando '+ETIQUETAS[modo]+'; PostgreSQL17 nuevo. No cerrar esta consola.')
    with preparar(modo) as p:
        print('\nIMPORTAR EN POSTMAN DESKTOP estos dos archivos (mismo laboratorio):')
        print(str(p.coleccion));print(str(p.environment))
        print('ENVIRONMENT A SELECCIONAR: '+p.nombre_environment)
        print('COLECCIÓN: '+p.nombre_coleccion)
        print('PRIMER SEND: '+p.primera_solicitud)
        if os.getenv('NUCLEAR_POSTMAN_QA')=='1':
            print('NUCLEAR_DESKTOP_READY '+json.dumps(dict(modo=p.modo,environment=str(p.environment),coleccion=str(p.coleccion),nombre_environment=p.nombre_environment,primera=p.primera_solicitud)),flush=True)
        print('Continuar en orden. No copiar variables, claves ni tokens. No compartir/exportar el Environment.')
        print('Importar otro JSON NO cambia el Environment ya seleccionado: seleccione el nombre indicado.')
        print('Datos y políticas sintéticos. MAIN y LAB se distinguen en cada solicitud; no acredita inicio productivo.')
        while True:
            try:accion=input('\nw = Worker (solo opción 3); i = abrir carpeta; q = cerrar y limpiar este laboratorio: ').strip().lower()
            except EOFError:break
            if accion=='q':break
            if accion=='d' and os.getenv('NUCLEAR_POSTMAN_QA')=='1':
                print('NUCLEAR_LAB_VERIFICACION '+json.dumps(p.verificar_sql()),flush=True);continue
            if accion=='i':
                if os.name=='nt':os.startfile(str(p.carpeta))
                else:print(str(p.carpeta))
            elif accion=='w':
                if p.modo!='worker':print('No corresponde a este modo. Elija opción 3 en una ejecución independiente.');continue
                r=p.worker()
                if os.getenv('NUCLEAR_POSTMAN_QA')=='1':print('NUCLEAR_WORKER_RESULT '+json.dumps(r,ensure_ascii=False),flush=True)
                print(r['salida'].strip())
                print('Comprobación PostgreSQL propia: '+json.dumps(r['despues'],ensure_ascii=False))
    print('Laboratorio propio cerrado. Environment temporal eliminado; los servidores/recursos ajenos se conservaron.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--modo',choices=list(ARCHIVOS),required=True)
    try:ejecutar(parser.parse_args().modo)
    except KeyboardInterrupt:print('Interrumpido: se ejecutó la limpieza de recursos propios.')
    except Exception as error:
        # No imprimir traceback, entorno, claves o cadenas SQL.
        print('No se completó el laboratorio. '+(str(error) if type(error) is RuntimeError else 'Revise dependencias/Docker y guía; no se muestran datos privados.'),file=sys.stderr)
        raise SystemExit(1)
