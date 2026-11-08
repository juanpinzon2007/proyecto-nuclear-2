"""Artefactos Postman 2.1 desde app.main; nunca abre conexiones SQL.

No publica en un workspace. OpenAPI generado es el contrato de estructura;
NOTAS añade autorización/cierre que OpenAPI no documenta completamente.
"""
from pathlib import Path
import copy
import hashlib
import inspect
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'backend'))
sys.dont_write_bytecode = True
from app.core.config import Settings, get_settings
Settings.model_config['env_file'] = None
get_settings.cache_clear()
from app.main import app
from fastapi.routing import APIRoute

SCHEMA = 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
METHODS = {'get','post','put','patch','delete'}
TECH = {'/health','/openapi.json','/docs','/redoc','/docs/oauth2-redirect'}
BLOCKED = {'/scheduling/calificaciones/notificar'}
VARS = {'base_url':'http://127.0.0.1:8765','base_url_laboratorio':'http://127.0.0.1:8766',
 'laboratorio_confirmado':'false','permitir_escrituras_laboratorio':'false',
 'limite':'25','desplazamiento':'0','accion':'finalizar'}
SECRET = {'clave_admin','clave_docente','clave_docente_nuevo','codigo_estudiante','codigo_ajeno',
 'token_admin','token_docente','token_estudiante','token_ajeno','token_docente_ajeno'}
for name in SECRET: VARS[name] = ''
PATHVAR = {'attempt_id':'id_intento','decision_id':'id_decision','version_id':'version_id',
 'id_caso':'caso_uuid','id_participacion':'id_participacion','id_docente':'id_docente',
 'sesion_id':'sesion_id','id_sesion':'sesion_id','convocatoria_id':'convocatoria_id'}


def write(name, data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def reference(name):
    VARS.setdefault(name,'')
    return '{{'+name+'}}'


def resolve(s, spec):
    if '$ref' in s:
        v=spec
        for k in s['$ref'][2:].split('/'):v=v[k]
        return resolve(v,spec)
    if isinstance(s,dict):return {k:resolve(v,spec) if isinstance(v,(dict,list)) else v for k,v in s.items() if k not in ('$schema','discriminator')}
    if isinstance(s,list):return [resolve(v,spec) if isinstance(v,(dict,list)) else v for v in s]
    return s


def example(s, spec, name='dato'):
    s=resolve(s,spec)
    if 'default' in s and s['default'] is not None:return s['default']
    if 'enum' in s:return s['enum'][0]
    if 'anyOf' in s:return example(next(x for x in s['anyOf'] if x.get('type')!='null'),spec,name)
    if s.get('type')=='object' or 'properties' in s:
        return {k:example(v,spec,k) for k,v in s.get('properties',{}).items() if k in s.get('required',[])}
    if s.get('type')=='array':return [example(s['items'],spec,name)]
    if s.get('type')=='boolean':return True
    if s.get('type') in ('integer','number'):
        return reference(PATHVAR.get(name,name)) if name.startswith('id_') else max(1,s.get('minimum',1),s.get('exclusiveMinimum',0)+1)
    if s.get('format')=='date-time':return reference(name)
    if s.get('format')=='uuid':return reference(PATHVAR.get(name,name))
    if s.get('format')=='password' or 'codigo' in name or name=='clave':return reference(name)
    return 'Dato sintético LAB' if s.get('minLength',0)<20 else reference(name)


def policy(path,method):
    if path.endswith('/reporte'):return 'DOCENTE','RF-16: formato=xlsx o pdf desde publicación oficial inmutable; JWT/cuenta/rol y ámbito docente/sesión/caso/grupos. RR/READ ONLY. Sin formato conserva 503, sin publicación 404. No recalcula notas.'
    if path in TECH or '/auth/' in path:return 'PUBLICO','Ninguna para acceder; el login valida credenciales y cuenta persistente.'
    if path.startswith('/api/v1/cases'):return 'DOCENTE','Identidad CASES inequívoca, titularidad; CREAR_CASOS en escrituras. Publicación exige grafo ejecutable; publicados inmutables.'
    if path.endswith('/identity/me'):return 'AUTENTICADO','Cuenta activa y rol vigente desde PostgreSQL.'
    if path.startswith('/api/v1/identity/docentes'):return 'ADMINISTRADOR','Cuentas de Identity; no concede ámbito académico ni DOCENTE ADMINISTRADOR.'
    if path.startswith('/api/v1/attempts'):return 'ESTUDIANTE','JWT con convocatoria propia activa, matrícula, intento propio, versión histórica, zona explícita y condiciones temporales del caso de uso.'
    if path.endswith('/convocatorias/{convocatoria_id}/resultado'):
        return 'ESTUDIANTE','RF-14: solo titular con JWT real y convocatoria del token. Provisional exige configuración expresa y todos sus intentos cerrados. Sin correctas durante sesión activa. Oficial: última publicación explícita; no calcula ni escribe.'
    if '/evaluacion/' in path and not path.endswith(('/resultado-tecnico','/evaluacion/preparacion')):
        return 'DOCENTE','RF-24/RF-25/RF-27: ámbito persistente sesión/caso/grupos. Ausencia explícita sin intentos ficticios; retiradas excluidas; máximo en misma participación. Publicación manual completa, hash de revisión y aviso interno atómicos. GET RR/READ ONLY.'
    if path.endswith('/identity/excepciones/repeticiones'):
        return 'DOCENTE','RF-25: permiso nativo individual de un uso, misma participación histórica, sesión EN_CURSO e intentos anteriores cerrados. Idempotente si existe permiso pendiente; no inicia intentos ni concede consentimiento.'
    if path.endswith('/resultado-tecnico') and method=='post':
        return 'DOCENTE','RF-13/RF-24: comando explícito sobre intento cerrado. Identidad/rol y ámbito persistentes bajo locks; UoW independiente del cierre. Idempotente 200; activo u otro motor 409; fallo 503 recuperable. Sin cuerpo ni puntajes del cliente, sin notas oficiales.'
    if path.endswith('/resultado-tecnico'):
        return 'DOCENTE','RF-13/RF-24: resultado técnico previamente persistido, no oficial. JWT/cuenta/rol y ámbito sesión/caso/grupos/participación/intento. REPEATABLE READ/READ ONLY; GET no genera resultados; 404 si no existe.'
    if path.endswith('/evaluacion/preparacion'):
        return 'DOCENTE','RF-13/RF-24/RF-16: preparación, no notas. Cuenta activa, identidades CASES/SCHEDULING inequívocas, sesión/caso/grupos propios y matrículas ciertas; zona histórica explícita. READ ONLY; publicable=false.'
    if path.startswith('/scheduling'):
        if any(x in path for x in ('validar-ingreso','/espera','/admision','/notificaciones')):
            return 'ESTUDIANTE','Identidad SCHEDULING, convocatoria propia y matrícula; ingreso exige concesión de admisión y EN_CURSO, nunca crea P/I.'
        return 'DOCENTE','Identidad SCHEDULING. Sesión propia; programación requiere asignación explícita docente-espacio y caso publicado propio. /espacios es catálogo docente global según código actual.'
    if path.endswith('/feedback') and method=='get':return 'ESTUDIANTE','Participación propia y condiciones de visibilidad; no muestra notas ni correcciones.'
    return 'DOCENTE','Ámbito persistente de caso/sesión/participación; seguimiento de casos realizados. No hay notas oficiales.'


def token(role):return {'ADMINISTRADOR':'token_admin','DOCENTE':'token_docente','ESTUDIANTE':'token_estudiante','AUTENTICADO':'token_estudiante'}.get(role)


GUARD = r"""if (pm.variables.get('laboratorio_confirmado') !== 'true') throw new Error('Confirme laboratorio propio, no una base permanente.');
const destino=pm.variables.replaceIn(pm.request.url.toString());
if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+\//.test(destino)) throw new Error('Solo loopback con puerto explícito de laboratorio.');
if (['POST','PUT','PATCH','DELETE'].includes(pm.request.method) && pm.variables.get('permitir_escrituras_laboratorio') !== 'true') throw new Error('Escrituras LAB no confirmadas.');
const bruto=pm.request.url.toString()+' '+JSON.stringify(pm.request.headers.toJSON())+' '+(pm.request.body ? pm.request.body.raw || '' : '')+' '+JSON.stringify(pm.request.auth ? pm.request.auth.toJSON() : {});
for (const m of bruto.matchAll(/\{\{([^{}]+)\}\}/g)) { const v=pm.variables.get(m[1]); if (v === undefined || v === '') throw new Error('Complete la variable local: '+m[1]); }
"""


def tests(status, schema=None, private=False, extra=''):
    s=f"pm.test('HTTP exacto {status}',()=>pm.response.to.have.status({status}));\n"
    if schema is not None:
        s+="pm.test('Contrato JSON',()=>pm.response.to.have.jsonSchema("+json.dumps(schema,ensure_ascii=False)+"));\n"
    s+="""if (pm.request.method !== 'HEAD' && (pm.response.headers.get('Content-Type')||'').includes('json')) {
const j=pm.response.json();
function claves(v) { if (!v || typeof v!=='object') return []; return Object.keys(v).concat(...Object.values(v).map(claves)); }
pm.test('Sin credenciales privadas',()=>pm.expect(claves(j)).not.to.include.any.members(['clave_hash','password','secreto','jwt_secret','codigo_hash']));
"""
    if private:s+="pm.test('Sin notas ni correcciones',()=>pm.expect(claves(j)).not.to.include.any.members(['es_correcta','esCorrecta','justificacion','nota_final','rubrica','puntaje','criterios']));\n"
    s+='}\n'+extra
    return s.splitlines()


def request(name, method, path, role='PUBLICO', body=None, status=200, spec=None,
            schema=None, extra='', host='base_url', auth=None, private=False, description=''):
    url=reference(host)+re.sub(r'(?<!\{)\{([^{}]+)\}(?!\})',lambda m:reference(PATHVAR.get(m[1],m[1])),path)
    a={'type':'noauth'} if role=='PUBLICO' else {'type':'bearer','bearer':[{'key':'token','value':reference(auth or token(role)),'type':'string'}]}
    req={'method':method.upper(),'header':[{'key':'Accept','value':'application/json'}],
         'url':url,'auth':a,'description':description}
    if body is not None:
        raw=body if isinstance(body,str) else json.dumps(body,ensure_ascii=False,indent=2)
        # Variables numéricas se sustituyen antes de interpretar el JSON.
        raw=re.sub(r'"(\{\{(?:id_asignacion|id_consentimiento|id_version_documento)\}\})"',r'\1',raw)
        req['body']={'mode':'raw','raw':raw,'options':{'raw':{'language':'json'}}}
        req['header'].append({'key':'Content-Type','value':'application/json'})
    return {'name':name,'request':req,'event':[{'listen':'test','script':{'type':'text/javascript','exec':tests(status,schema,private,extra)}}], 'response':[]}


def collection(name, items):
    return {'info':{'name':name,'schema':SCHEMA,'description':'Solo laboratorio nuevo y desechable. Sin secretos exportados. Consulte README.md; ninguna aprobación de políticas oficiales.'},
            'event':[{'listen':'prerequest','script':{'type':'text/javascript','exec':GUARD.splitlines()}}], 'item':items}


def ciclo_academico(logins,login_ajeno):
    b='/scheduling/sesiones/{sesion_id}/evaluacion'
    items=copy.deepcopy(logins)+[copy.deepcopy(login_ajeno)]
    items.append(request('1 — revisar cohorte y capturar hash','get',b+'/consolidacion','DOCENTE',extra="const j=pm.response.json();pm.test('Todas resueltas',()=>pm.expect(j.publicable).to.eql(true));pm.variables.set('revision_publicacion_sha256',j.revision_sha256);"))
    items.append(request('2 — autorizar publicación completa','post',b+'/publicaciones','DOCENTE',{'revision_sha256':reference('revision_publicacion_sha256')},extra="const j=pm.response.json();pm.test('Oficial por autorización explícita',()=>pm.expect(j.oficial).to.eql(true));pm.variables.set('publicacion_id',j.id);pm.test('Sin duplicados',()=>pm.expect(new Set(j.resultados.map(x=>x.convocatoria_id)).size).to.eql(j.resultados.length));"))
    items.append(request('3 — reintento de misma publicación','post',b+'/publicaciones','DOCENTE',{'revision_sha256':reference('revision_publicacion_sha256')},extra="pm.test('Misma publicación',()=>pm.expect(pm.response.json().id).to.eql(pm.variables.get('publicacion_id')));"))
    items.append(request('4 — lectura oficial docente','get',b+'/publicaciones','DOCENTE',extra="pm.test('Publicación autorizada',()=>pm.expect(pm.response.json().oficial).to.eql(true));"))
    items.append(request('5 — consulta privada titular','get','/scheduling/convocatorias/{convocatoria_id}/resultado','ESTUDIANTE',extra="const j=pm.response.json();pm.test('Oficial y decimal',()=>{pm.expect(j.oficial).to.eql(true);pm.expect(j.nota).to.match(/^\\d+\\.\\d{2}$/);});"))
    items.append(request('6 — docente ajeno rechazado','get',b+'/publicaciones','DOCENTE',status=403,auth='token_docente_ajeno'))
    items.append(request('7 — sin autenticación','get',b+'/publicaciones',status=401))
    write('Proyecto_Nuclear_publicacion_academica.postman_collection.json',collection('Proyecto Nuclear — publicación académica explícita — app.main',items))


def main():
    spec=app.openapi();write('openapi_main.json',spec)
    deps={}
    def names(d):
        return sorted({getattr(x.call,'__name__',type(x.call).__name__) for x in d.dependencies} | {n for x in d.dependencies for n in names(x)})
    def routes(items):
        for r in items:
            if isinstance(r,APIRoute):yield r
            elif hasattr(r,'original_router'):yield from routes(r.original_router.routes)
    for r in routes(app.routes):
        for m in r.methods:
            matches=[p for p,ops in spec['paths'].items() if m.lower() in ops and (p==r.path or p.endswith(r.path))]
            assert len(matches)==1,('Revisar inclusión de router',r.path,m)
            deps[(matches[0],m.lower())]={'archivo':str(Path(inspect.getsourcefile(r.endpoint)).relative_to(ROOT)).replace('\\','/'),'funcion':r.endpoint.__name__,'dependencias':names(r.dependant)}
    assert len(deps)==50,'Cambió la superficie registrada; conciliar inventario antes de regenerar.'
    groups={n:[] for n in ('Identity','Cases','Scheduling','Participation','Seguimiento y notificaciones','Tecnico')}
    inventory=[];preparacion_items=[];resultados_items=[];evaluacion_items=[]
    for path,ops in spec['paths'].items():
        for method,op in ops.items():
            if method not in METHODS:continue
            role,notes=policy(path,method)
            blocked=path in BLOCKED
            status=503 if blocked else int(next(k for k in op['responses'] if k.startswith('2')))
            body_schema=op.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema')
            body=example(body_schema,spec) if body_schema else None
            if '/auth/personal' in path:body={'correo':reference('correo_docente'),'clave':reference('clave_docente')}
            if '/auth/estudiantes' in path:body={'correo':reference('correo_estudiante'),'codigo_convocatoria':reference('codigo_estudiante')}
            if path=='/api/v1/identity/docentes' and method=='post':body={'nombre':'Docente nuevo LAB','correo':reference('correo_docente_nuevo'),'clave':reference('clave_docente_nuevo'),'roles':['DOCENTE'],'permisos':['CREAR_CASOS']}
            if path.endswith('/autorizaciones'):body={'roles':['DOCENTE'],'permisos':['CREAR_CASOS']}
            if body_schema and '$ref' in body_schema and body_schema['$ref'].endswith('/CasoPayload'):
                from tests.integration.cases.conftest import payload_valido
                body=payload_valido.__wrapped__()
            if path.endswith('/graph') and method=='put':body=reference('grafo_body')
            if path.endswith('/publicaciones') and method=='post':body={'revision_sha256':reference('revision_publicacion_sha256')}
            if path.endswith('/rectificacion'):body={'id_confirmacion':reference('ausencia_id'),'motivo':'Rectificación docente explícita LAB'}
            params=op.get('parameters',[])
            query=[p for p in params if p['in']=='query']
            target=path+('?'+'&'.join(p['name']+'='+reference(p['name']) for p in query) if query else '')
            if path.endswith('/reporte'):target=path+'?formato=xlsx'
            schema=op['responses'].get(str(status),{}).get('content',{}).get('application/json',{}).get('schema')
            if schema:schema=resolve(schema,spec)
            group='Cases' if path.startswith('/api/v1/cases') else 'Participation' if '/attempts/' in path else 'Scheduling' if path.startswith('/scheduling') else 'Identity'
            if '/seguimiento/' in path or '/notificaciones' in path or 'calificaciones/notificar' in path:group='Seguimiento y notificaciones'
            if path in TECH:group='Tecnico'
            desc=notes+(' BLOQUEADO: 503 con identidad y referencias válidas; no se afirma éxito funcional.' if blocked else ' Disponible en app.main; requiere configuración y recursos válidos.')
            extra=''
            if path.endswith('/consolidacion'):
                extra="const j=pm.response.json();pm.test('Revisión explícita',()=>{pm.expect(j.publicable).to.be.a('boolean');pm.expect(j.revision_sha256).to.match(/^[0-9a-f]{64}$/);});pm.variables.set('revision_publicacion_sha256',j.revision_sha256);"
            if path.endswith('/evaluacion/preparacion'):
                extra="""const j=pm.response.json();
pm.test('Preparación no autoriza publicación',()=>pm.expect(j.publicable).to.eql(false));
pm.test('Versión histórica esperada',()=>pm.expect(j.version_caso_id).to.eql(pm.variables.get('version_id')));
pm.test('Sin rúbrica, respuestas o resultado técnico identificable',()=>{function k(x){if(!x||typeof x!=='object')return [];return Object.keys(x).concat(...Object.values(x).map(k));}pm.expect(k(j)).not.to.include.any.members(['rubrica_id','version_regla','nota_final','puntaje','respuestas','id_resultado_tecnico','procedencia','es_correcta','justificacion']);});
pm.test('Sin caché',()=>pm.expect(pm.response.headers.get('Cache-Control')).to.eql('no-store'));
"""
            if path.endswith('/resultado-tecnico'):
                extra="""const j=pm.response.json();
pm.test('Técnico, no oficial',()=>pm.expect(j.oficial).to.eql(false));
pm.test('Versión histórica',()=>pm.expect(j.version_caso_id).to.eql(pm.variables.get('version_id')));
pm.test('Nota decimal como cadena',()=>pm.expect(j.nota_final).to.be.a('string').and.match(/^\\d+\\.\\d{2}$/));
pm.test('Sin código ni credenciales',()=>{pm.expect(j).not.to.have.property('procedencia');pm.expect(j).not.to.have.property('politica_documento');});
pm.test('Sin caché',()=>pm.expect(pm.response.headers.get('Cache-Control')).to.eql('no-store'));
if(j.ambito==='TECNICO')pm.test('Fracciones exactas como cadenas',()=>j.criterios.forEach(c=>{pm.expect(c.numerador).to.be.a('string').and.match(/^\\d+$/);pm.expect(c.denominador).to.be.a('string').and.match(/^[1-9]\\d*$/);}));
"""
            positive=request(f'{method.upper()} {path}'+(' [CIERRE SEGURO]' if blocked else ' [POSITIVA/PRECONDICIONES]'),method,target,role,body,status,schema=schema,private='/attempts/' in path,description=desc,extra=extra)
            variants=[positive]
            if path.endswith('/reporte'):
                for formato,item in [('xlsx',positive),('pdf',request('GET reporte oficial PDF','get',path+'?formato=pdf','DOCENTE'))]:
                    item['event'][0]['script']['exec'] += [
                        "pm.test('Archivo adjunto no vacío',()=>{pm.expect(pm.response.size().body).to.be.above(100);pm.expect(pm.response.headers.get('Content-Disposition')).to.include('attachment;');});",
                        "pm.test('Fuente oficial identificada',()=>{pm.expect(pm.response.headers.get('X-Publicacion-Id')).to.match(/^[0-9a-f-]{36}$/);pm.expect(pm.response.headers.get('X-Publicacion-Version')).to.match(/^[1-9][0-9]*$/);pm.expect(pm.response.headers.get('X-Publicacion-SHA256')).to.match(/^[0-9a-f]{64}$/);});"]
                    mime='application/pdf' if formato=='pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    item['request']['header']=[{'key':'Accept','value':mime}]
                    item['event'][0]['script']['exec'].append("pm.test('MIME correcto',()=>pm.expect(pm.response.headers.get('Content-Type')).to.include('"+mime+"'));")
                    if formato=='pdf':variants.append(item)
                variants.append(request('GET reporte sin formato [CSV CERRADO]','get',path,'DOCENTE',status=503))
            if body_schema and resolve(body_schema,spec).get('required'):
                variants.append(request(f'{method.upper()} {path} [BODY INVALIDO]',method,target,role,{},422))
            if role!='PUBLICO':
                variants.append(request(f'{method.upper()} {path} [SIN JWT]',method,target,'PUBLICO',body,401))
                neg=request(f'{method.upper()} {path} [JWT INVALIDO]',method,target,role,body,401)
                neg['request']['auth']['bearer'][0]['value']='invalido-LAB';variants.append(neg)
                wrong='token_docente' if role in ('ADMINISTRADOR','ESTUDIANTE') else 'token_estudiante'
                if role!='AUTENTICADO':variants.append(request(f'{method.upper()} {path} [ROL NO AUTORIZADO]',method,target,role,body,403,auth=wrong))
            if path.endswith('/evaluacion/preparacion'):
                variants.append(request('GET preparación [PARÁMETRO NO ADMITIDO]','get',path+'?docente_id=otro','DOCENTE',status=422))
                preparacion_items=copy.deepcopy(variants)
            if path.endswith('/resultado-tecnico') and method=='get':
                variants.append(request('GET resultado técnico [DOCENTE AJENO]','get',path,'DOCENTE',status=403,auth='token_docente_ajeno'))
                variants.append(request('GET resultado técnico [AÚN NO DISPONIBLE]','get',path.replace('{id_intento}','{intento_sin_resultado_id}'),'DOCENTE',status=404,
                    extra="pm.test('No devuelve nota',()=>pm.expect(pm.response.json()).not.to.have.property('nota_final'));"))
                resultados_items=copy.deepcopy(variants)
            if path.endswith('/resultado-tecnico') and method=='post':
                variants.append(request('POST evaluación [DOCENTE AJENO]','post',path,'DOCENTE',status=403,auth='token_docente_ajeno'))
                variants.append(request('POST evaluación [INTENTO ACTIVO]','post',path.replace('{id_intento}','{intento_sin_resultado_id}'),'DOCENTE',status=409))
                variants.append(request('POST evaluación [BODY PROHIBIDO]','post',path,'DOCENTE',body={'nota_final':'100'},status=422))
                evaluacion_items=copy.deepcopy(variants)
            groups[group].append({'name':method.upper()+' '+path,'item':variants})
            inventory.append({'metodo':method.upper(),'ruta':path,'rol':role,'autenticacion':'Bearer JWT real' if role!='PUBLICO' else 'Sin Bearer',
                'estado':'REGISTRADO_BLOQUEADO' if blocked else 'REGISTRADO_CON_PRECONDICIONES','dependencias_academicas':notes,
                'parametros':params,'body':resolve(body_schema,spec) if body_schema else None,
                'respuestas_openapi':op['responses'],'respuesta_funcional_preparada':status,
                'errores_fuera_de_openapi':'401 autenticación; 403 ámbito/rol; 404 recurso según módulo; 409 conflictos según módulo; 400 reglas Cases; 422 validación; 503 integración/política. No todos aplican a todas las rutas.',
                **deps.get((path,method),{})})
    for p in ('/openapi.json','/docs','/redoc','/docs/oauth2-redirect'):
        for method in ('GET','HEAD'):
            groups['Tecnico'].append(request(method+' '+p,method,p))
            inventory.append({'metodo':method,'ruta':p,'rol':'PUBLICO','autenticacion':'Ninguna', 'estado':'DOCUMENTACION_AUTOMATICA','body':None,'respuesta_funcional_preparada':200})
    write('inventario_endpoints.json',inventory)
    write('Proyecto_Nuclear_main.postman_collection.json',collection('Proyecto Nuclear — app.main — catálogo (no ejecutar entero)',[{'name':k,'item':v} for k,v in groups.items() if v]))
    logins=[]
    for role,perfil in [('DOCENTE','docente'),('ESTUDIANTE','estudiante')]:
        path='/api/v1/identity/auth/'+('personal' if perfil=='docente' else 'estudiantes')
        body={'correo':reference('correo_'+perfil)}
        body.update({'clave':reference('clave_docente')} if perfil=='docente' else {'codigo_convocatoria':reference('codigo_estudiante')})
        logins.append(request('MAIN — login '+perfil,'post',path,body=body,
            extra="pm.variables.set('token_"+perfil+"',pm.response.json().access_token);"))
    write('Proyecto_Nuclear_preparacion_docente.postman_collection.json',collection(
        'Proyecto Nuclear — preparación docente privada — app.main',logins+preparacion_items))
    login_ajeno=request('MAIN — login docente ajeno','post','/api/v1/identity/auth/personal',
        body={'correo':reference('correo_docente_ajeno'),'clave':reference('clave_docente')},
        extra="pm.variables.set('token_docente_ajeno',pm.response.json().access_token);")
    write('Proyecto_Nuclear_resultados_tecnicos.postman_collection.json',collection('Proyecto Nuclear — resultados técnicos docentes, NO oficiales',logins+[login_ajeno]+resultados_items))
    ruta_resultado='/scheduling/sesiones/{sesion_id}/evaluacion/intentos/{id_intento}/resultado-tecnico'
    pendiente=request('MAIN — cerrado sin resultado [GET 404]','get',ruta_resultado,'DOCENTE',status=404)
    primero=copy.deepcopy(evaluacion_items[0]);primero['name']='MAIN — evaluar cerrado [POST 200]'
    primero['event'][0]['script']['exec'] += ["pm.test('Resultado conocido LAB, no oficial',()=>{const x=pm.response.json();pm.expect(x.ambito).to.eql('TECNICO');pm.expect(x.nota_final).to.eql('33.33');pm.expect(x.oficial).to.eql(false);});"]
    primero['event'][0]['script']['exec'] += ["const x=pm.response.json();pm.variables.set('resultado_id_primero',x.id_resultado);pm.variables.set('resultado_hash_primero',x.procedencia_sha256);pm.variables.set('resultado_fecha_primero',x.fecha_calculo);"]
    repetir=copy.deepcopy(evaluacion_items[0]);repetir['name']='MAIN — reintento idempotente [POST 200]'
    repetir['event'][0]['script']['exec'] += ["const x=pm.response.json();pm.test('Mismo resultado y fecha',()=>{pm.expect(String(x.id_resultado)).to.eql(String(pm.variables.get('resultado_id_primero')));pm.expect(x.procedencia_sha256).to.eql(pm.variables.get('resultado_hash_primero'));pm.expect(x.fecha_calculo).to.eql(pm.variables.get('resultado_fecha_primero'));});"]
    write('Proyecto_Nuclear_evaluacion_tecnica.postman_collection.json',collection(
        'Proyecto Nuclear — cierre confirmado y evaluación explícita, NO oficial',
        logins+[login_ajeno,pendiente,primero,repetir,copy.deepcopy(resultados_items[0])]+evaluacion_items[1:]))
    ciclo_academico(logins,login_ajeno)
    workflow(spec)
    write('Proyecto_Nuclear_laboratorio.postman_environment.json',{'name':'Proyecto Nuclear LAB — SIN SECRETOS','values':[{'key':k,'value':v,'type':'secret' if k in SECRET or any(x in k for x in ('clave','codigo','token')) else 'default','enabled':True} for k,v in sorted(VARS.items())], '_postman_variable_scope':'environment'})
    rows=['# Endpoints registrados en app.main','','Fuente: openapi_main.json y dependencias de los routers. No acredita despliegue ni ejecución HTTP.','','| Método | Ruta | Rol | Estado | Dependencias |','|---|---|---|---|---|']
    for i in inventory:rows.append('| '+ ' | '.join(str(i.get(k,'')) for k in ('metodo','ruta','rol','estado','dependencias_academicas'))+' |')
    rows+=['','Parámetros, cuerpos y esquemas de respuesta completos: inventario_endpoints.json y openapi_main.json.',
           'Preparación, resultado técnico, publicación manual autorizada y RF-16 Excel/PDF están registrados. Sin formato, el CSV anterior conserva 503. Inicio/provisión/consentimiento no están en main. PUT de decisiones no está montado: 405, no una operación disponible.',
           'OpenAPI no enumera todos los errores funcionales: revisar archivo/función/dependencias indicados y README.']
    (OUT/'INVENTARIO.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(json.dumps({'operaciones_openapi':sum(m in METHODS for v in spec['paths'].values() for m in v),'rutas_documentacion':4,'colecciones':6}))


def workflow(spec):
    items=[]
    def add(name,method,path,role='ESTUDIANTE',body=None,status=200,extra='',lab=False,auth=None):
        # El catálogo usa los esquemas exactos; este recorrido añade invariantes.
        canonical=re.sub(r'/attempts/\{id_intento\}', '/attempts/{attempt_id}',path)
        canonical=canonical.replace('{id_decision}','{decision_id}')
        response=spec.get('paths',{}).get(canonical,{}).get(method.lower(),{}).get('responses',{}).get(str(status),{})
        schema=response.get('content',{}).get('application/json',{}).get('schema')
        items.append(request(('LAB AISLADA — ' if lab else 'MAIN — ')+name,method,path,role,body,status,
            schema=resolve(schema,spec) if schema else None,extra=extra,auth=auth,private='/attempts/' in path,
            host='base_url_laboratorio' if lab else 'base_url'))
    for role in ('admin','docente'):
        add('login '+role,'POST','/api/v1/identity/auth/personal','PUBLICO',{'correo':reference('correo_'+role),'clave':reference('clave_'+role)},extra="pm.variables.set('token_"+role+"',pm.response.json().access_token);")
    add('listar docentes','GET','/api/v1/identity/docentes','ADMINISTRADOR')
    for who in ('estudiante','ajeno'):
        add('login '+who,'POST','/api/v1/identity/auth/estudiantes','PUBLICO',{'correo':reference('correo_'+who),'codigo_convocatoria':reference('codigo_'+who)},extra="pm.variables.set('token_"+who+"',pm.response.json().access_token);")
    add('identidad privada','GET','/api/v1/identity/me')
    add('admisión persistida en preparación LAB','GET','/scheduling/convocatorias/{convocatoria_id}/admision',extra="pm.test('Concesión vigente',()=>pm.expect(pm.response.json().admitida).to.eql(true));")
    add('validar ingreso sin crear P/I','POST','/scheduling/validar-ingreso',body={'convocatoria_id':reference('convocatoria_id'),'estudiante_id':reference('estudiante_id'),'codigo_acceso':reference('codigo_estudiante')})
    cb='/api/v1/identity/convocatorias/{convocatoria_id}/asignaciones/{id_asignacion}/consentimiento'
    add('documento sintético versionado','GET',cb,lab=True,extra="const j=pm.response.json(); ['id_version_documento','referencia','huella'].forEach(k=>pm.variables.set(k,j[k]));")
    add('aceptación explícita LAB','POST',cb+'/aceptacion',lab=True,body={'id_version_documento':reference('id_version_documento'),'referencia':reference('referencia'),'huella':reference('huella'),'acepta':True},extra="pm.variables.set('id_consentimiento',pm.response.json().id_consentimiento);")
    start={'id_asignacion':reference('id_asignacion'),'codigo_acceso':reference('codigo_estudiante'),'id_consentimiento':reference('id_consentimiento')}
    add('inicio transaccional LAB','POST','/api/v1/convocatorias/{convocatoria_id}/intentos',body=start,status=201,lab=True,extra="const j=pm.response.json();pm.variables.set('id_intento',j.id_intento);pm.variables.set('id_participacion',j.id_participacion);")
    add('inicio repetido sin duplicados','POST','/api/v1/convocatorias/{convocatoria_id}/intentos',body=start,status=409,lab=True)
    base='/api/v1/attempts/{attempt_id}'
    add('progreso ajeno rechazado','GET',base+'/progress',status=403,auth='token_ajeno')
    add('progreso inicial','GET',base+'/progress',extra="pm.test('Cero respuestas',()=>pm.expect(pm.response.json().respondidas).to.eql(0));")
    for n in (1,2):
        add(f'escenario actual {n}','GET',base+'/current-scenario',extra="const q=pm.response.json().pregunta; pm.test('Pregunta habilitada',()=>pm.expect(q).to.be.an('object')); if(q){pm.variables.set('id_decision',q.id);pm.variables.set('id_opcion',q.opciones[0].id);}")
        add(f'primera selección {n}','POST',base+'/decisions/{decision_id}',body={'id_opcion':reference('id_opcion')},status=201)
        if n==1:add('segunda selección rechazada','POST',base+'/decisions/{decision_id}',body={'id_opcion':reference('id_opcion')},status=409)
    add('ruta terminal','GET',base+'/current-scenario',extra="pm.test('Terminal sin pregunta futura',()=>{const j=pm.response.json();pm.expect(j.recorrido_finalizado).to.eql(true);pm.expect(j.pregunta).to.eql(null);});")
    add('progreso completo privado','GET',base+'/progress',extra="pm.test('Dos respondidas',()=>pm.expect(pm.response.json().respondidas).to.eql(2));")
    add('cierre ajeno rechazado','POST',base+'/finish',status=403,auth='token_ajeno')
    add('cierre titular','POST',base+'/finish',extra="pm.test('Finalizado',()=>pm.expect(pm.response.json().estado).to.eql('FINALIZADO'));")
    add('cierre idempotente','POST',base+'/finish')
    add('escenario cerrado','GET',base+'/current-scenario',status=409)
    fb='/api/v1/identity/seguimiento/participaciones/{id_participacion}/feedback'
    add('feedback individual docente','POST',fb,'DOCENTE',{'texto':'Valoración sintética LAB: recorrido completado.'},201)
    add('consulta privada feedback','GET',fb)
    add('feedback ajeno rechazado','GET',fb,status=403,auth='token_ajeno')
    add('avisos internos propios','GET','/scheduling/notificaciones?destinatario_id='+reference('estudiante_id'))
    add('reporte oficial cerrado','GET','/api/v1/identity/seguimiento/sesiones/{id_sesion}/reporte','DOCENTE',status=503)
    write('Proyecto_Nuclear_recorrido_LAB.postman_collection.json',collection('Proyecto Nuclear — recorrido integral LAB — NO productivo',items))
    rows=['# Orden del recorrido de laboratorio','','Ejecutar una sola iteración, sobre un laboratorio nuevo. No es un recorrido productivo completo: consentimiento e inicio usan servidor separado y políticas LAB explícitas.','','| Paso | Operación/superficie | Método | URL | HTTP exacto |','|---|---|---|---|---|']
    for n,item in enumerate(items,1):
        req=item['request'];status=re.search(r'HTTP exacto (\d+)','\n'.join(item['event'][0]['script']['exec']))[1]
        rows.append(f"| {n} | {item['name']} | {req['method']} | `{req['url']}` | {status} |")
    rows += ['', 'Los logins capturan tokens en pm.variables; la consulta de documento captura versión, referencia y huella; aceptación captura id_consentimiento; inicio captura id_participacion/id_intento; cada escenario captura únicamente la pregunta/opción actualmente habilitadas.',
             'No se crean opciones o respuestas ficticias, ni se calcula/publica una nota. El primer camino seleccionado corresponde al grafo SQL real del fixture.',
             'La preparación administrativa previa incluye espera y habilitación docente; el recorrido verifica su concesión persistida. No se atribuye a app.main la creación del intento realizada en la superficie LAB.']
    (OUT/'RECORRIDO.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')


if __name__=='__main__':main()
