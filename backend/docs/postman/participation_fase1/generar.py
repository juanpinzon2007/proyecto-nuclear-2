"""Colecciones MAIN condicionadas. El 503 de control NO es cumplimiento del RF."""
from pathlib import Path
from copy import deepcopy
import json,sys
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT.parent/'cobertura_27rf'))
from construir import req,P

def main():
 carpetas=[]
 for rf in ('RF-12','RF-23','RF-25'):
  items=deepcopy(P[:16 if rf=='RF-23' else 25])
  for item in items:
   item['request']['url']=item['request']['url'].replace('{{base_url_laboratorio}}','{{base_url}}')
   item['name']=item['name'].replace('LAB','MAIN CON POLÍTICAS LAB')
  if rf=='RF-23':
   items += [req('RELOJ LAB — consultar vencimiento sin escribir','GET','/api/v1/attempts/{{id_intento}}/progress',200,'estudiante',extra="pm.test('Vencido y una selección conservada',()=>{const j=pm.response.json();pm.expect(j.intento.estado).to.eql('VENCIDO');pm.expect(j.respondidas).to.eql(1);});"),req('Persistir cierre vencido sin calificar','POST','/api/v1/attempts/{{id_intento}}/finish',200,'estudiante',extra="pm.test('Cierre VENCIDO',()=>pm.expect(pm.response.json().estado).to.eql('VENCIDO'));")]
  if rf=='RF-25':
   body={'id_sesion':'{{sesion_id}}','id_estudiante':'{{id_estudiante_usuario}}'}
   items += [req('Autorizar repetición individual por creador','POST','/api/v1/identity/excepciones/repeticiones',201,'docente',body,extra="pm.test('Permiso nativo',()=>pm.expect(pm.response.json().id_permiso_extra).to.be.above(0));pm.environment.set('id_permiso_extra',pm.response.json().id_permiso_extra);"),req('Repetir autorización sin duplicarla','POST','/api/v1/identity/excepciones/repeticiones',201,'docente',body,extra="pm.test('Mismo permiso',()=>pm.expect(pm.response.json().id_permiso_extra).to.eql(Number(pm.environment.get('id_permiso_extra'))));"),req('Rechazar autorización estudiantil','POST','/api/v1/identity/excepciones/repeticiones',403,'estudiante',body)]
   start={'id_asignacion':'{{id_asignacion}}','codigo_acceso':'{{codigo_estudiante}}','id_consentimiento':'{{id_consentimiento}}','id_permiso_extra':'{{id_permiso_extra}}'}
   raw=json.dumps(start).replace('"{{id_asignacion}}"','{{id_asignacion}}').replace('"{{id_consentimiento}}"','{{id_consentimiento}}').replace('"{{id_permiso_extra}}"','{{id_permiso_extra}}')
   items += [req('Iniciar extra con permiso real y UoW única','POST','/api/v1/convocatorias/{{convocatoria_id}}/intentos',201,'estudiante',raw,extra="pm.test('Segundo intento',()=>pm.expect(pm.response.json().numero_intento).to.eql(2));pm.environment.set('id_intento',pm.response.json().id_intento);"),req('Rechazar duplicación de extra activo','POST','/api/v1/convocatorias/{{convocatoria_id}}/intentos',409,'estudiante',raw),req('Cerrar extra sin nota automática','POST','/api/v1/attempts/{{id_intento}}/finish',200,'estudiante'),req('Permiso consumido no reutilizable','POST','/api/v1/convocatorias/{{convocatoria_id}}/intentos',403,'estudiante',raw)]
  carpetas.append(dict(name=rf+' — app.main con proveedores explícitos SOLO LAB',description='No aprueba institucionalmente el documento ni las políticas. Recorrido técnico sobre app.main; preparar exclusivamente esta carpeta con el parámetro -RF del script PowerShell. Cierre completo del RF BLOQUEADO por contratos pendientes.',item=items))
 # Demostrar que metadatos/documento/aceptación LAB no habilitan producción.
 control=[deepcopy(P[3])]
 u='/api/v1/identity/convocatorias/{{convocatoria_id}}/asignaciones/{{id_asignacion}}/consentimiento'
 control += [req('Documento bloqueado sin aprobación oficial','GET',u,503,'estudiante'),req('Aceptar bloqueado sin aprobación oficial','POST',u+'/aceptacion',503,'estudiante',{'id_version_documento':'{{id_version_documento}}','referencia':'{{referencia}}','huella':'{{huella}}','acepta':True}),req('Inicio bloqueado sin políticas productivas','POST','/api/v1/convocatorias/{{convocatoria_id}}/intentos',503,'estudiante','{"id_asignacion": {{id_asignacion}}, "codigo_acceso": "{{codigo_estudiante}}", "id_consentimiento": {{id_consentimiento}}}')]
 # id_version_documento debe ser INTEGER en la solicitud, no una cadena.
 control[2]['request']['body']['raw']=control[2]['request']['body']['raw'].replace('"{{id_version_documento}}"','{{id_version_documento}}')
 carpetas.append(dict(name='CONTROL — composición productiva cerrada',description='Solo controles negativos de seguridad; 503 nunca prueba cumplimiento funcional. La aceptación sintética se prepara explícitamente en LAB para no inventar un ID.',item=control))
 for folder in carpetas:
  rf=folder['name'].split(' ')[0]
  for k,item in enumerate(folder['item'],1):
   item['name']=f'F1-{rf}-{k:02} | '+item['name']
   item['event']=[x for x in item['event'] if x['listen']=='test']
   item['event'].insert(0,dict(listen='prerequest',script=dict(type='text/javascript',exec=[f"if(pm.environment.get('fase1_rf')!=='{rf}'){{if(pm.execution&&pm.execution.skipRequest)pm.execution.skipRequest();throw new Error('Prepare únicamente {rf}.');}}"])))
   item['request']['description']='Ruta REAL registrada en app.main. '+('CONTROL NEGATIVO: no aprobación oficial/políticas; NO cumplimiento del RF.' if rf=='CONTROL' else 'Proveedores de políticas y documento SINTÉTICOS, exclusivamente en PostgreSQL17 propio de laboratorio; NO habilitación productiva.')+' Ejecutar en orden; tokens e IDs se capturan del servidor. Nunca mostrar Authorization ni códigos/clave/login en capturas.'
 c=dict(info=dict(name='Proyecto Nuclear — fase 1 MAIN condicionado RF-12 RF-23 RF-25',schema='https://schema.getpostman.com/json/collection/v2.1.0/collection.json'),item=carpetas)
 (OUT/'Proyecto_Nuclear_fase1.postman_collection.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
 env=json.loads((OUT.parent/'cobertura_27rf/Proyecto_Nuclear_27RF.postman_environment.json').read_text(encoding='utf-8'));env['name']='FASE1 PLANTILLA SIN SECRETOS — usar preparador'
 keys={v['key'] for v in env['values']}
 import re
 for k in re.findall(r'\{\{([^{}]+)\}\}',json.dumps(c))+['fase1_rf']:
  if k not in keys:env['values'].append(dict(key=k,value='',type='secret' if any(t in k for t in ('clave','codigo','token')) else 'default',enabled=True));keys.add(k)
 for v in env['values']:v['value']=''
 (OUT/'Proyecto_Nuclear_fase1.postman_environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
 print([(f['name'],len(f['item'])) for f in carpetas])
if __name__=='__main__':main()
