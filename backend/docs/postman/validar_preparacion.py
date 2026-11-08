"""Validación local sin SQL: no sustituye Postman/Newman ni aceptación PG17."""
from pathlib import Path
import ast
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime,timezone
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'));sys.dont_write_bytecode=True


def requests(items):
    for x in items:
        if 'item' in x:yield from requests(x['item'])
        else:yield x


def main(salida=None):
    env=json.loads((OUT/'Proyecto_Nuclear_laboratorio.postman_environment.json').read_text(encoding='utf-8'))
    variables={x['key']:x['value'] for x in env['values']}
    assert all(not x['value'] for x in env['values'] if x['type']=='secret')
    spec=json.loads((OUT/'openapi_main.json').read_text(encoding='utf-8'))
    expected={(m.upper(),p) for p,v in spec['paths'].items() for m in v if m in ('get','post','put','delete','patch')}
    inventory=json.loads((OUT/'inventario_endpoints.json').read_text(encoding='utf-8'))
    assert {(i['metodo'],i['ruta']) for i in inventory if i['estado']!='DOCUMENTACION_AUTOMATICA'}==expected
    node=shutil.which('node');checks=[];scripts=[]
    for file in OUT.glob('*.postman_collection.json'):
        c=json.loads(file.read_text(encoding='utf-8'))
        assert c['info']['schema'].endswith('/v2.1.0/collection.json')
        scripts += ['\n'.join(e['script']['exec']) for e in c.get('event',[])]
        items=list(requests(c['item']))
        assert items and all(x['request']['method'] and x['request']['url'] for x in items)
        for x in items:
            assert x['response']==[]  # No respuestas guardadas ni JWT capturados.
            raw=json.dumps(x,ensure_ascii=False)
            assert not re.search(r'\{\{\{|\}\}\}',x['request']['url'])
            assert all(v in variables for v in re.findall(r'\{\{([^{}]+)\}\}',raw))
            scripts+=['\n'.join(e['script']['exec']) for e in x.get('event',[])]
            assert any('pm.test' in s for s in scripts[-len(x['event']):])
        checks.append({'archivo':file.name,'solicitudes':len(items)})
    if node:
        result=subprocess.run([node,'-e',"const vm=require('vm'); let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>{const a=JSON.parse(s);a.forEach(x=>new vm.Script(x));console.log(a.length);});"],
            input=json.dumps(scripts),text=True,capture_output=True)
        assert result.returncode==0,result.stderr
    for file in OUT.glob('*.py'):ast.parse(file.read_text(encoding='utf-8'))
    from app.core.config import Settings,get_settings
    Settings.model_config['env_file']=None;get_settings.cache_clear()
    from app.main import app
    from fastapi.testclient import TestClient
    from sqlalchemy.engine import Engine
    assert app.dependency_overrides=={} and app.openapi()==spec
    http=[]
    with patch.object(Engine,'connect',side_effect=AssertionError('SQL prohibido en validación sin laboratorio')):
        with TestClient(app,raise_server_exceptions=True) as client:
            for path,status in [('/health',200),('/openapi.json',200),
                ('/api/v1/identity/docentes',401),('/api/v1/identity/me',401),
                ('/api/v1/attempts/1/current-scenario',401),('/api/v1/attempts/1/progress',401),
                ('/scheduling/sesiones/00000000-0000-0000-0000-000000000001/evaluacion/preparacion',401),
                ('/scheduling/sesiones/00000000-0000-0000-0000-000000000001/evaluacion/intentos/1/resultado-tecnico',401)]:
                r=client.get(path);assert r.status_code==status,(path,r.status_code)
                if path=='/health':assert r.json()=={'status':'ok'}
                http.append({'metodo':'GET','ruta':path,'esperado':status,'observado':r.status_code,'medio':'ASGI/TestClient sin SQL'})
    result={'fecha_utc':datetime.now(timezone.utc).isoformat(),
        'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'operaciones_main':len(expected),'rutas_documentacion_get_head':4,'colecciones':checks,
        'scripts_sintaxis_js':len(scripts) if node else 'PENDIENTE: Node no disponible',
        'validacion_schema_oficial_postman':'NO EJECUTADA: validador/CLI no disponible; validación estructural propia',
        'pruebas_http_sin_sql':http,'postman_cli':shutil.which('postman'),'newman':shutil.which('newman'),
        'aceptacion_pg17_postman':'PENDIENTE: CLI/Newman ausentes; HTTP TCP Python se informa por separado en resultado_http_*.json',
        'sin_ejecucion_suite_general':True,'sin_secretos_en_archivos_importables':True}
    destino=salida or OUT/('VALIDACION_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    with destino.open('x',encoding='utf-8') as f:
        f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,help='JSON nuevo; nunca sobrescribe evidencia anterior.')
    main(parser.parse_args().salida)
