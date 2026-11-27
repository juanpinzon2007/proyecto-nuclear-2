from pathlib import Path
import json
out=Path(__file__).resolve().parent
source=out.parent/'Proyecto_Nuclear_27RF.postman_collection.json'
c=json.loads(source.read_text(encoding='utf8'))
c['info']['name']='Nuclear - probar cualquier requisito'
for folder in c['item']:
    rf=folder['name'][:5]
    for n,i in enumerate(folder['item'],1):
        script=next(e['script'] for e in i['event'] if e['listen']=='prerequest')
        action='abrir' if n==1 else 'worker2' if 'WORKER 2 ' in i['name'] else 'worker3' if 'WORKER 3 ' in i['name'] else 'correo2' if 'CORREO 2 ' in i['name'] else ''
        if not action: continue
        old=script['exec']
        script['exec']=[
            "const key = pm.environment.get('clave_selector_local');",
            "function detener(msg) { pm.execution.skipRequest(); throw new Error(msg); }",
            "if (!key) detener('Selecciona el entorno Nuclear - todas las carpetas (local).');",
            "function preparar(pendientes) {",
            f"  pm.sendRequest({{url:'http://127.0.0.1:18647/{rf}/{action}',method:'POST',header:{{Authorization:'Bearer '+key}}}}, (err,res) => {{",
            "    if(err) detener('Abre Encender-Postman-local.cmd y vuelve a pulsar Send.');",
            "    if(res.code===202 && pendientes>0) { setTimeout(()=>preparar(pendientes-1),1000); return; }",
            "    if(res.code!==200) detener(res.json().mensaje || 'El laboratorio sigue preparandose. Repite este paso.');",
            "    if(res.json().values) for(const v of res.json().values) pm.environment.set(v.key,v.value);",
            *old, "  });", "}", "preparar(90);"]
(out/'Nuclear-MULTI.postman_collection.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8')
