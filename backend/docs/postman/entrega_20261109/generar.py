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


def reportes_oficiales():
    # Reutiliza login/cohorte/publicación explícita existentes; ninguna nota inventada.
    previa=json.loads((BASE/'Proyecto_Nuclear_publicacion_academica.postman_collection.json').read_text(encoding='utf-8'))
    items=[locales(x) for x in previa['item']]
    # Este laboratorio produce el resultado técnico real 33.33, no el 100 del recorrido de entrega.
    for x in items:
        for e in x.get('event',[]):
            e['script']['exec']=[line.replace('100.00','33.33') for line in e['script']['exec']]
    lector=next(x for x in items if x['name'].startswith('4 —'))
    lector['event'][0]['script']['exec'] += [
        "const publicada=pm.response.json();pm.environment.set('publicacion_id',publicada.id);pm.environment.set('publicacion_version',publicada.version);pm.environment.set('publicacion_sha256',publicada.revision_sha256);"]
    ruta='/api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte'
    for formato,mime in [('xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),('pdf','application/pdf')]:
        extra=r"""pm.test('Binario no vacío',()=>pm.expect(pm.response.size().body).to.be.above(100));
        pm.test('MIME correcto',()=>pm.expect(pm.response.headers.get('Content-Type')).to.include('%s'));
        pm.test('Descarga adjunta',()=>pm.expect(pm.response.headers.get('Content-Disposition')).to.match(/attachment;.*\.%s"$/));
        pm.test('Publicación exacta',()=>{pm.expect(pm.response.headers.get('X-Publicacion-Id')).to.eql(pm.environment.get('publicacion_id'));pm.expect(pm.response.headers.get('X-Publicacion-Version')).to.eql(String(pm.environment.get('publicacion_version')));pm.expect(pm.response.headers.get('X-Publicacion-SHA256')).to.eql(pm.environment.get('publicacion_sha256'));});
        pm.test('Privado',()=>pm.expect(pm.response.headers.get('Cache-Control')).to.eql('no-store'));
        """ % (mime,formato)
        item=request('RF16 — descargar '+formato.upper(),'GET',ruta+'?formato='+formato,'DOCENTE',extra=extra,
            description='RF-16: archivo de publicación oficial previamente autorizada, sin cálculo ni escrituras. Send and Download para guardarlo y abrirlo. No publicar automáticamente.')
        item['request']['header']=[{'key':'Accept','value':mime}];items.append(item)
    for nombre,rol,status,auth in [('sin JWT','PUBLICO',401,None),('docente ajeno','DOCENTE',403,'token_docente_ajeno'),('estudiante','ESTUDIANTE',403,None)]:
        items.append(request('RF16 — rechazo '+nombre,'GET',ruta+'?formato=xlsx',rol,status=status,auth=auth,
            extra="pm.test('No descarga datos',()=>pm.expect(pm.response.headers.get('Content-Disposition')).to.eql(undefined));"))
    guardar('Proyecto_Nuclear_reportes_oficiales.postman_collection.json',collection('ENTREGA — RF-16 publicación y reportes oficiales — app.main',items))


def main():
    anterior=json.loads((BASE/'Proyecto_Nuclear_recorrido_LAB.postman_collection.json').read_text(encoding='utf-8'))
    evaluacion=json.loads((BASE/'Proyecto_Nuclear_evaluacion_tecnica.postman_collection.json').read_text(encoding='utf-8'))
    items=[locales(x) for x in anterior['item'][:25]]+[locales(evaluacion['item'][2])]+[locales(x) for x in evaluacion['item'][3:7]]+[locales(x) for x in evaluacion['item'][9:11]]
    assert len(items)==32
    entrega=collection('ENTREGA 9 noviembre — recorrido técnico — MAIN y LAB explícitos',items)
    entrega['info']['description']+=' RF-16 oficial: usar la colección adicional Proyecto_Nuclear_reportes_oficiales del mismo directorio con laboratorio_publicacion.py; no ejecutar ambos recorridos sobre el mismo estado.'
    guardar('Proyecto_Nuclear_entrega_20261109.postman_collection.json',entrega)
    reportes_oficiales()
    ruta='/scheduling/sesiones/{worker_sesion_id}'
    w=[locales(evaluacion['item'][0])]
    for nombre,estado in [('WORKER 1 — antes de ejecutar: EN_CURSO','EN_CURSO'),('WORKER 2 — después de w: FINALIZADO','FINALIZADO'),('WORKER 3 — después de segundo w: FINALIZADO','FINALIZADO')]:
        w.append(request(nombre,'GET',ruta,'DOCENTE',extra="pm.test('Estado esperado',()=>pm.expect(pm.response.json().estado).to.eql('"+estado+"'));pm.test('Edición histórica',()=>pm.expect(pm.response.json().version_caso_id).to.eql(pm.variables.get('version_id')));"))
    guardar('Proyecto_Nuclear_worker_20261109.postman_collection.json',collection('WORKER — ejecutar Send por pasos; w en consola entre consultas',w))
    env=json.loads((BASE/'Proyecto_Nuclear_laboratorio.postman_environment.json').read_text(encoding='utf-8'))
    env['name']='Entrega 9 noviembre — SOLO recursos temporales — SIN SECRETOS'
    keys={v['key'] for v in env['values']}
    for k in ('worker_sesion_id','resultado_id_primero','resultado_hash_primero','resultado_fecha_primero','publicacion_version','publicacion_sha256','laboratorio_modo','laboratorio_id','paso_principal','paso_reportes','paso_worker','primera_decision_id','primera_opcion_id','opcion_alternativa_id','cierre_original'):
        if k not in keys:env['values'].append(dict(key=k,value='',type='default',enabled=True))
    guardar('Proyecto_Nuclear_entrega_20261109.postman_environment.json',env)
    from contratos_desktop import enriquecer, generar_guia
    enriquecer(OUT)
    generar_guia(OUT)
    for file in OUT.glob('*.postman_collection.json'):
        c=json.loads(file.read_text(encoding='utf-8'))
        for item in c['item']:
            assert not item.get('response')
            for v in re.findall(r'\{\{([^{}]+)\}\}',json.dumps(item)):
                assert v in {x['key'] for x in env['values']},v
    assert all(not x['value'] for x in env['values'] if x['type']=='secret')


if __name__=='__main__':main()
