"""HTTP TCP real desde las solicitudes guardadas. NO ejecuta pm.test.

Los tokens/códigos no se exportan. Python verifica estados y algunas invariantes;
la semántica del sandbox Postman se acredita únicamente ejecutando Postman.
"""
from contextlib import ExitStack
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
import laboratorio_http as lab


def expand(s,v):
    def repl(m):
        if m[1] not in v or v[m[1]]=='':raise ValueError('Variable de laboratorio incompleta: '+m[1])
        return str(v[m[1]])
    return re.sub(r'\{\{([^{}]+)\}\}',repl,s)


def main():
    lab.settings_lab()
    import httpx
    import sqlalchemy as sa
    from app.modules.participation.infrastructure.models import IntentoModel, PasoSimulacionModel
    from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
    collection=json.loads((OUT/'Proyecto_Nuclear_recorrido_LAB.postman_collection.json').read_text(encoding='utf-8'))
    values={x['key']:x['value'] for x in json.loads((OUT/'Proyecto_Nuclear_laboratorio.postman_environment.json').read_text(encoding='utf-8'))['values']}
    credentials={k:secrets.token_urlsafe(32) for k in ('clave_admin','clave_docente','codigo_estudiante','codigo_ajeno')}
    steps=[];result={'fecha_utc':datetime.now(timezone.utc).isoformat(),'medio':'Python/httpx TCP; NO Postman/Newman','pasos':steps,'aprobado':False}
    try:
        with ExitStack() as stack:
            h,resources=lab.preparar(credentials,stack)
            from app.main import app
            main_port=lab.serve(app,0,stack);isolated_port=lab.serve(h.lab.app,0,stack)
            values.update(resources);values.update(credentials)
            values.update(base_url='http://127.0.0.1:'+str(main_port),base_url_laboratorio='http://127.0.0.1:'+str(isolated_port))
            with httpx.Client(timeout=15) as client:
                for item in collection['item']:
                    req=item['request'];url=expand(req['url'],values)
                    headers={}
                    if req['auth']['type']=='bearer':headers['Authorization']='Bearer '+expand(req['auth']['bearer'][0]['value'],values)
                    payload=json.loads(expand(req['body']['raw'],values)) if 'body' in req else None
                    script='\n'.join(item['event'][0]['script']['exec'])
                    expected=int(re.search(r"HTTP exacto (\d+)",script)[1])
                    operations=[]
                    def sql(conn,cursor,statement,*args):
                        if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','MERGE')):operations.append('DML')
                    def commit(conn):operations.append('COMMIT')
                    from app.db.session import get_engine
                    engines=set([h.engine,get_engine()])
                    for engine in engines:
                        sa.event.listen(engine,'before_cursor_execute',sql);sa.event.listen(engine,'commit',commit)
                    try:r=client.request(req['method'],url,headers=headers,json=payload)
                    finally:
                        for engine in engines:
                            sa.event.remove(engine,'before_cursor_execute',sql);sa.event.remove(engine,'commit',commit)
                    step={'nombre':item['name'],'metodo':req['method'],'ruta_plantilla':req['url'],
                          'esperado':expected,'observado':r.status_code}
                    steps.append(step)
                    assert r.status_code==expected, 'Estado diferente del contrato guardado'
                    if req['method']=='GET' or '/validar-ingreso' in url or '/auth/' in url:
                        assert 'DML' not in operations, 'La lectura realizó DML'
                        step['sin_DML']=True;step['commits_observados']=operations.count('COMMIT')
                        # Feedback histórico usa with s.begin(): confirma la lectura.
                        # No presentar ese contrato existente como un GET sin commit.
                        if not url.endswith('/feedback'):assert operations==[], 'Commit inesperado'
                    j=r.json()
                    if 'login ' in item['name']:values['token_'+item['name'].rsplit(' ',1)[1]]=j['access_token']
                    if 'documento sintético' in item['name']:values.update({k:j[k] for k in ('id_version_documento','referencia','huella')})
                    if 'aceptación explícita' in item['name']:values['id_consentimiento']=j['id_consentimiento']
                    if 'inicio transaccional' in item['name']:values.update(id_intento=j['id_intento'],id_participacion=j['id_participacion'])
                    if 'escenario actual ' in item['name']:
                        assert set(j)=={'id_escenario','contexto','pregunta','recorrido_finalizado','respondidas'}
                        values.update(id_decision=j['pregunta']['id'],id_opcion=j['pregunta']['opciones'][0]['id'])
                    if '/attempts/' in url:
                        def keys(x):return [] if not isinstance(x,(dict,list)) else ([k for k in x]+sum([keys(v) for v in x.values()],[]) if isinstance(x,dict) else sum([keys(v) for v in x],[]))
                        assert not set(keys(j)) & {'clave_hash','es_correcta','esCorrecta','justificacion','nota_final','rubrica','puntaje'}
                    if 'progreso inicial' in item['name']:assert j['respondidas']==0
                    if 'progreso completo' in item['name']:assert j['respondidas']==2 and j['pendientes']==[]
                    if 'ruta terminal' in item['name']:assert j['recorrido_finalizado'] and j['pregunta'] is None
                    if 'cierre titular' in item['name']:assert j['estado']=='FINALIZADO'
                    print(item['name']+': HTTP '+str(r.status_code),flush=True)
            with h.sesiones() as session:
                attempt=session.get(IntentoModel,values['id_intento'])
                assert attempt.estado=='FINALIZADO'
                assert session.scalar(sa.select(sa.func.count()).select_from(PasoSimulacionModel).where(PasoSimulacionModel.id_intento==attempt.id_intento))==2
                assert session.scalar(sa.select(sa.func.count()).select_from(ResultadoIntentoModel))==0
            result.update(aprobado=True,postgresql='17 desechable propio',persistencia_sesion_independiente=True,
                          respuestas=2,resultados_oficiales=0,politicas='LAB explícitas; no institucionales',
                          overrides='Solo reloj fijo en main; ninguna sustitución de JWT/roles/repositorios')
    except Exception as e:
        result.update(error_tipo=type(e).__name__,nota='Se conserva el resultado fallido sin cuerpos ni secretos.')
    finally:
        result.update(pasos_aprobados=sum(s['esperado']==s['observado'] for s in steps),
            sha256_coleccion=hashlib.sha256((OUT/'Proyecto_Nuclear_recorrido_LAB.postman_collection.json').read_bytes()).hexdigest(),
            head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=lab.ROOT,text=True).strip(),
            fecha_fin_utc=datetime.now(timezone.utc).isoformat())
        file=OUT/('resultado_http_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
        file.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(file.name, 'APROBADO' if result['aprobado'] else 'NO APROBADO')
    return 0 if result['aprobado'] else 1


if __name__=='__main__':raise SystemExit(main())
