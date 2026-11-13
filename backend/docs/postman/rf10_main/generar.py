"""Contrato RF-10 MAIN sobre intento previamente preparado SOLO LAB."""
import json,sys,re
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'cobertura_27rf'))
from construir import req

def main():
 items=[]
 def add(n,m,u,c,actor='estudiante',body=None,extra=''):items.append(req(n,m,u,c,actor,body,extra))
 add('Login titular real','POST','/api/v1/identity/auth/estudiantes',200,None,{'correo':'{{correo_estudiante}}','codigo_convocatoria':'{{codigo_estudiante}}'},"pm.environment.set('token_estudiante',pm.response.json().access_token);")
 add('Rechazar anónimo','GET','/api/v1/attempts/{{id_intento}}/current-scenario',401,None)
 add('Login otro estudiante','POST','/api/v1/identity/auth/estudiantes',200,None,{'correo':'{{correo_ajeno}}','codigo_convocatoria':'{{codigo_ajeno}}'},"pm.environment.set('token_ajeno',pm.response.json().access_token);")
 add('Rechazar acceso ajeno','GET','/api/v1/attempts/{{id_intento}}/current-scenario',403,'ajeno')
 current='/api/v1/attempts/{{id_intento}}/current-scenario';progress='/api/v1/attempts/{{id_intento}}/progress'
 add('Escenario actual privado','GET',current,200,extra="const j=pm.response.json();pm.test('Solo escenario actual',()=>{pm.expect(j).to.have.all.keys('id_escenario','contexto','pregunta','recorrido_finalizado','respondidas');pm.expect(j.pregunta).to.have.all.keys('id','enunciado','opciones');j.pregunta.opciones.forEach(o=>pm.expect(o).to.have.all.keys('id','texto'));});pm.environment.set('rf10_q',j.pregunta.id);pm.environment.set('rf10_o',j.pregunta.opciones[0].id);pm.environment.set('rf10_alt',j.pregunta.opciones[1].id);")
 add('Recargar misma pregunta sin escribir','GET',current,200,extra="pm.test('Misma pregunta tras recarga',()=>pm.expect(pm.response.json().pregunta.id).to.eql(pm.environment.get('rf10_q')));")
 add('Rechazar pregunta futura','POST','/api/v1/attempts/{{id_intento}}/decisions/{{segunda_decision_id}}',403,body={'id_opcion':'{{segunda_opcion_id}}'})
 decision='/api/v1/attempts/{{id_intento}}/decisions/{{rf10_q}}'
 add('Primera selección','POST',decision,201,body={'id_opcion':'{{rf10_o}}'},extra="pm.test('Intento activo sin nota',()=>{const j=pm.response.json();pm.expect(j.estado).to.eql('EN_CURSO');pm.expect(j).not.to.have.property('nota_final');});")
 immutable="pm.test('Inmutable',()=>pm.expect(pm.response.json().detail.codigo).to.eql('RESPUESTA_INMUTABLE'));"
 add('Reenvío idéntico no es upsert','POST',decision,409,body={'id_opcion':'{{rf10_o}}'},extra=immutable)
 add('Rechazar cambio de alternativa','POST',decision,409,body={'id_opcion':'{{rf10_alt}}'},extra=immutable)
 add('PUT no registrado','PUT',decision,405,body={'id_opcion':'{{rf10_alt}}'})
 add('PATCH no registrado','PATCH',decision,405,body={'id_opcion':'{{rf10_alt}}'})
 add('Reconciliar selección desde progreso','GET',progress,200,extra="const j=pm.response.json();pm.test('Original persistida',()=>{pm.expect(j.respondidas).to.eql(1);pm.expect(j.selecciones).to.deep.eql([{id_decision:pm.environment.get('rf10_q'),id_opcion:pm.environment.get('rf10_o')}]);});")
 add('Siguiente escenario real','GET',current,200,extra="const j=pm.response.json();pm.test('Avance',()=>{pm.expect(j.respondidas).to.eql(1);pm.expect(j.recorrido_finalizado).to.eql(false);pm.expect(j.pregunta.id).not.to.eql(pm.environment.get('rf10_q'));});pm.environment.set('rf10_siguiente_q',j.pregunta.id);pm.environment.set('rf10_siguiente_o',j.pregunta.opciones[0].id);")
 add('Respuesta siguiente autorizada','POST','/api/v1/attempts/{{id_intento}}/decisions/{{rf10_siguiente_q}}',201,body={'id_opcion':'{{rf10_siguiente_o}}'})
 add('FIN sin contenido futuro','GET',current,200,extra="pm.test('FIN con nulos',()=>pm.expect(pm.response.json()).to.deep.eql({id_escenario:null,contexto:null,pregunta:null,recorrido_finalizado:true,respondidas:2}));")
 add('FIN no cierra automáticamente','GET',progress,200,extra="pm.test('Activo hasta cierre explícito',()=>{pm.expect(pm.response.json().intento.estado).to.eql('EN_CURSO');pm.expect(pm.response.json().respondidas).to.eql(2);});")
 add('Cierre explícito','POST','/api/v1/attempts/{{id_intento}}/finish',200,extra="pm.test('Finalizado',()=>pm.expect(pm.response.json().estado).to.eql('FINALIZADO'));pm.environment.set('rf10_cierre',JSON.stringify(pm.response.json()));")
 add('Repetir cierre conserva datos','POST','/api/v1/attempts/{{id_intento}}/finish',200,extra="pm.test('Idempotencia cierre',()=>pm.expect(pm.response.json()).to.deep.eql(JSON.parse(pm.environment.get('rf10_cierre'))));")
 add('Contenido activo cerrado','GET',current,409,extra="pm.test('No editable',()=>pm.expect(pm.response.json().detail.codigo).to.eql('INTENTO_NO_EDITABLE'));")
 add('Progreso histórico privado','GET',progress,200,extra="pm.test('Historial sin nota',()=>{const j=pm.response.json();pm.expect(j.respondidas).to.eql(2);pm.expect(j.intento.estado).to.eql('FINALIZADO');pm.expect(j).not.to.have.any.keys('nota_final','rubrica','criterios','justificacion');});")
 for i,x in enumerate(items,1):
  x['name']=f'RF10-MAIN-{i:02} | '+x['name'];x['request']['description']='Operación REAL de app.main. Intento/consentimiento preparados previamente en LAB; no demuestra inicio productivo ni aprobación integral RF-10.'
  x['event'].insert(0,dict(listen='prerequest',script=dict(type='text/javascript',exec=[f"if(pm.environment.get('rf10_preparado')!=='SOLO_LAB'||Number(pm.environment.get('rf10_paso')||0)!=={i-1}){{if(pm.execution&&pm.execution.skipRequest)pm.execution.skipRequest();throw new Error('Prepare RF-10 y siga el orden.');}}"])))
  code=re.search(r'HTTP exacto (\d+)',json.dumps(x['event'])).group(1)
  x['event'][-1]['script']['exec'].append(f"if(pm.response.code==={code})pm.environment.set('rf10_paso',{i});")
 collection=dict(info=dict(name='RF-10 — contrato Angular MAIN',schema='https://schema.getpostman.com/json/collection/v2.1.0/collection.json',description='Solo app.main; precondición de intento existente SOLO LAB. Respuestas inmutables. RF integral BLOQUEADO.'),item=[dict(name='RF-10 — MAIN',item=items)])
 (OUT/'RF10_MAIN.postman_collection.json').write_text(json.dumps(collection,ensure_ascii=False,indent=2),encoding='utf-8')
 keys=sorted(set(re.findall(r'\{\{([^{}]+)\}\}',json.dumps(collection)))|{'rf10_paso','rf10_preparado'})
 env=dict(name='RF10 PLANTILLA SIN SECRETOS — usar preparador',values=[dict(key=k,value='',enabled=True,type='secret' if any(s in k for s in ('token','codigo','clave')) else 'default') for k in keys],_postman_variable_scope='environment')
 (OUT/'RF10_MAIN.postman_environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8');print('RF10 MAIN:',len(items),'solicitudes')
if __name__=='__main__':main()
