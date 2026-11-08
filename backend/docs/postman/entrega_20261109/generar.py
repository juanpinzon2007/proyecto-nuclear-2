"""Compone artefactos de entrega desde colecciones verificadas, sin SQL."""
from pathlib import Path
from copy import deepcopy
import json,re,sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent
sys.path.insert(0,str(BASE))
from generar_colecciones import request,collection


def guardar(nombre,datos): (OUT/nombre).write_text(json.dumps(datos,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def locales(item):
    x=deepcopy(item)
    for e in x.get('event',[]):
        e['script']['exec']=[s.replace('pm.variables.set(', 'pm.environment.set(').replace('33.33','100.00') for s in e['script']['exec']]
    return x


def main():
    anterior=json.loads((BASE/'Proyecto_Nuclear_recorrido_LAB.postman_collection.json').read_text(encoding='utf-8'))
    evaluacion=json.loads((BASE/'Proyecto_Nuclear_evaluacion_tecnica.postman_collection.json').read_text(encoding='utf-8'))
    items=[locales(x) for x in anterior['item'][:25]]+[locales(evaluacion['item'][2])]+[locales(x) for x in evaluacion['item'][3:7]]+[locales(x) for x in evaluacion['item'][9:11]]
    assert len(items)==32
    guardar('Proyecto_Nuclear_entrega_20261109.postman_collection.json',collection('ENTREGA 9 noviembre — recorrido técnico — MAIN y LAB explícitos',items))
    ruta='/scheduling/sesiones/{worker_sesion_id}'
    w=[locales(evaluacion['item'][0])]
    for nombre,estado in [('WORKER 1 — antes de ejecutar: EN_CURSO','EN_CURSO'),('WORKER 2 — después de w: FINALIZADO','FINALIZADO'),('WORKER 3 — después de segundo w: FINALIZADO','FINALIZADO')]:
        w.append(request(nombre,'GET',ruta,'DOCENTE',extra="pm.test('Estado esperado',()=>pm.expect(pm.response.json().estado).to.eql('"+estado+"'));pm.test('Edición histórica',()=>pm.expect(pm.response.json().version_caso_id).to.eql(pm.variables.get('version_id')));"))
    guardar('Proyecto_Nuclear_worker_20261109.postman_collection.json',collection('WORKER — ejecutar Send por pasos; w en consola entre consultas',w))
    env=json.loads((BASE/'Proyecto_Nuclear_laboratorio.postman_environment.json').read_text(encoding='utf-8'))
    env['name']='Entrega 9 noviembre — SOLO recursos temporales — SIN SECRETOS'
    keys={v['key'] for v in env['values']}
    for k in ('worker_sesion_id','resultado_id_primero','resultado_hash_primero','resultado_fecha_primero'):
        if k not in keys:env['values'].append(dict(key=k,value='',type='default',enabled=True))
    guardar('Proyecto_Nuclear_entrega_20261109.postman_environment.json',env)
    for file in OUT.glob('*.postman_collection.json'):
        c=json.loads(file.read_text(encoding='utf-8'))
        for item in c['item']:
            assert not item.get('response')
            for v in re.findall(r'\{\{([^{}]+)\}\}',json.dumps(item)):
                assert v in {x['key'] for x in env['values']},v
    assert all(not x['value'] for x in env['values'] if x['type']=='secret')


if __name__=='__main__':main()
