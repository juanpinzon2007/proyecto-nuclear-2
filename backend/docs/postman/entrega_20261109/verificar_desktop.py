"""QA opcional del lanzador PowerShell real + Newman por Send. Sin datos productivos."""
import argparse
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
from threading import Thread
import time
from uuid import uuid4

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]


def lineas(p,q):
    try:
        for line in p.stdout:q.put(line)
    finally:q.put(None)


def marcador(q,tag,timeout=90):
    fin=time.monotonic()+timeout
    while time.monotonic()<fin:
        try:line=q.get(timeout=min(2,fin-time.monotonic()))
        except queue.Empty:continue
        if line is None:raise RuntimeError('El lanzador terminó antes de '+tag)
        if tag in line:return json.loads(line.split(tag,1)[1])
    raise RuntimeError('Tiempo agotado esperando '+tag)


def verificar(modo,newman,carpeta):
    carpeta.mkdir(parents=True,exist_ok=False)
    ps=shutil.which('pwsh') or shutil.which('powershell')
    if not ps:raise RuntimeError('PowerShell no disponible')
    numero={'principal':'1','reportes':'2','worker':'3'}[modo]
    env=os.environ.copy();env.update(NUCLEAR_POSTMAN_QA='1',PYTHONIOENCODING='utf-8')
    p=subprocess.Popen([ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'preparar-postman.ps1'),'-Opcion',numero],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
    q=queue.Queue();t=Thread(target=lineas,args=(p,q),daemon=True);t.start();pasos=[];workers=[];ready=None;guardas=[]
    try:
        ready=marcador(q,'NUCLEAR_DESKTOP_READY ',timeout=180)
        p.stdin.write('d\n');p.stdin.flush();antes=marcador(q,'NUCLEAR_LAB_VERIFICACION ')
        entorno=json.loads(Path(ready['environment']).read_text(encoding='utf-8'))
        assert entorno['name']==ready['nombre_environment'] and all(x['value']=='' for x in entorno['values'] if x['key'].startswith('token_'))
        node=shutil.which('node');nenv=os.environ.copy();nenv['NUCLEAR_NEWMAN_MODULE']=str(newman)
        n=subprocess.Popen([node,str(OUT/'verificar_send.cjs'),ready['coleccion'],ready['environment'],str(carpeta)],env=nenv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
        try:
            for line in n.stdout:
                if not line.startswith('{'):continue  # Avisos de Node no son respuestas HTTP.
                evento=json.loads(line)
                if evento['tipo']=='worker':
                    p.stdin.write('w\n');p.stdin.flush();w=marcador(q,'NUCLEAR_WORKER_RESULT ',timeout=60);workers.append(w)
                    n.stdin.write(json.dumps({'ok':w['codigo']==0})+'\n');n.stdin.flush()
                elif evento['tipo']=='guarda':guardas.append(evento);assert evento['bloqueada_sin_http']
                elif evento['tipo']=='request':
                    pasos.append(evento);print(modo,evento['paso'],evento['http'],'pm.test:',len(evento['pruebas']),'fallos:',len(evento['fallos']),flush=True)
                elif evento['tipo']=='fin':fin=evento
                elif evento['tipo']=='fatal':raise RuntimeError(evento['mensaje'])
            assert n.wait(timeout=30)==0
        finally:
            if n.poll() is None:n.terminate();n.wait(timeout=10)  # Únicamente el hijo creado aquí.
        assert len(pasos)=={'principal':32,'reportes':15,'worker':4}[modo]
        assert len(guardas)==fin['guardas']==2
        assert fin['fallos']==0 and all(not x['fallos'] and x['pruebas'] and all(a['aprobada'] for a in x['pruebas']) for x in pasos)
        p.stdin.write('d\n');p.stdin.flush();despues=marcador(q,'NUCLEAR_LAB_VERIFICACION ')
        if modo=='principal':
            assert antes==dict(participaciones=0,intentos=0,respuestas=0,resultados=0,publicaciones=0),antes
            assert despues==dict(participaciones=1,intentos=1,respuestas=2,resultados=1,publicaciones=0),despues
        elif modo=='reportes':
            assert antes['publicaciones']==0 and despues['publicaciones']==1
            xs=[x for x in pasos if 'archivo' in x];assert len(xs)==2
            assert xs[0]['cabeceras']['X-Publicacion-Id']==xs[1]['cabeceras']['X-Publicacion-Id']==str(fin['variables']['publicacion_id'])
            from openpyxl import load_workbook
            from pypdf import PdfReader
            assert load_workbook(carpeta/'RF16_Oficial.xlsx')['Resultados']['H2'].value==33.33
            assert '33.33' in ''.join(pg.extract_text() for pg in PdfReader(carpeta/'RF16_Oficial.pdf').pages)
        else:
            assert antes['estado']=='EN_CURSO' and despues['estado']=='FINALIZADO'
            assert len(workers)==2 and 'Sesiones cerradas: 1' in workers[0]['salida'] and 'Sesiones cerradas: 0' in workers[1]['salida']
            assert despues['auditorias']==despues['avisos_sesion']==1 and despues['resultados_tecnicos_totales']==0
        resultado=dict(modo=modo,preparacion='PowerShell real -Opcion '+numero,environment_generado=True,importacion_gui_realizada=False,ejecutor='Newman 6.2.3; runtime independiente por solicitud, solo Environment persiste',pasos=pasos,guardas=guardas,antes=antes,despues=despues,worker=workers,fin=fin,aprobado=True)
        (carpeta/'resultado.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        # Conservar evidencia sanitaria de fallos; no guardar Environment/JWT ni bodies.
        (carpeta/'fallo.json').write_text(json.dumps(dict(modo=modo,pasos=pasos,aprobado=False),ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        if p.poll() is None:
            p.stdin.write('q\n');p.stdin.flush()
            try:p.wait(timeout=45)
            except subprocess.TimeoutExpired:raise RuntimeError('No finalizó el lanzador propio; revisar PID '+str(p.pid))
        if ready:assert not Path(ready['environment']).exists(),'Environment temporal no eliminado'
    assert p.returncode==0
    return resultado


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--newman',type=Path,required=True);parser.add_argument('--evidencias',type=Path,required=True);parser.add_argument('--modo',choices=['principal','reportes','worker'],required=True)
    a=parser.parse_args();r=verificar(a.modo,a.newman,a.evidencias)
    print(json.dumps(dict(modo=a.modo,solicitudes=len(r['pasos']),aserciones=r['fin']['aserciones'],aprobado=True)))
