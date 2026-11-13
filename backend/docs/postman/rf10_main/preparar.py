"""RF-10 MAIN: PG17 nuevo, intento previo por mecanismo LAB existente."""
import argparse,json,subprocess,sys,shutil,os,hashlib
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(OUT.parent/'entrega_20261109'))
import desktop

@contextmanager
def preparar():
 with desktop.preparar('principal') as p:
  h=p.contexto;env=json.loads(p.environment.read_text(encoding='utf-8'));vals={v['key']:v for v in env['values']}
  from tests.integration.test_lab_student_journey import aceptar,iniciar
  # El hash de código se renueva en el preparador existente: usar ese secreto LAB
  # auténtico, no el código anterior conservado en el namespace de la fixture.
  h.titular.codigo=vals['codigo_estudiante']['value']
  acceptance=aceptar(h);attempt=iniciar(h,acceptance['id_consentimiento']).json()
  vals['id_intento']['value']=str(attempt['id_intento'])
  for v in json.loads((OUT/'RF10_MAIN.postman_environment.json').read_text(encoding='utf-8'))['values']:vals.setdefault(v['key'],v)
  vals['segunda_decision_id']['value']=h.escenas[1]['preguntas'][0]['id']
  vals['segunda_opcion_id']['value']=h.escenas[1]['preguntas'][0]['opciones'][0]['id']
  vals['rf10_paso']['value']='0';vals['rf10_preparado']['value']='SOLO_LAB';vals['base_url_laboratorio']['value']=''
  env['values']=list(vals.values());env['name']='RF10 MAIN — INTENTO PREVIO LAB — '+p.carpeta.name
  p.environment.write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
  col=p.carpeta/'RF10_MAIN.postman_collection.json'
  with col.open('xb') as f:f.write((OUT/'RF10_MAIN.postman_collection.json').read_bytes())
  try:yield p,col
  finally:col.unlink(missing_ok=True)

def ejecutar(dest,newman):
 dest.mkdir(parents=True,exist_ok=False)
 result=dict(fecha_inicio=datetime.now(timezone.utc).isoformat(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),rf='RF-10',estado_integral='BLOQUEADO',preparacion='PG17, relaciones y aceptación/inicio SOLO LAB; luego únicamente requests de app.main',gui=False,solicitudes=[])
 def fuentes():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for d in ('backend/app','backend/tests') for p in (ROOT/d).rglob('*.py')}
 result['fuentes_antes']=fuentes();(dest/'inicio.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 try:
  with preparar() as (p,col):
   result['antes']=p.verificar_sql();envfile=p.environment
   result['coleccion_sha256']=hashlib.sha256(col.read_bytes()).hexdigest()
   result['preparador_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
   proc=subprocess.run([shutil.which('node'),str(OUT.parent/'cobertura_27rf/ejecutar_send.cjs'),str(col),str(envfile),'RF-10',str(dest)],env={**os.environ,'NUCLEAR_NEWMAN_MODULE':str(newman)},capture_output=True,text=True,encoding='utf-8',timeout=240)
   (dest/'consola_newman.log').write_text(proc.stdout,encoding='utf-8')
   assert proc.returncode==0,'Fallo Node; revisar log sanitario'
   for line in proc.stdout.splitlines():
    event=json.loads(line)
    if event['tipo']=='solicitud':result['solicitudes'].append(event)
    elif event['tipo']=='fin':result['fin']=event
   assert len(result['solicitudes'])==21 and result['fin']['fallos']==0
   result['despues']=p.verificar_sql()
   assert result['despues']['intentos']==result['despues']['participaciones']==1
   assert result['despues']['respuestas']==2 and result['despues']['resultados']==result['despues']['publicaciones']==0
   import sqlalchemy as sa
   from app.modules.participation.infrastructure.models import IntentoModel as I
   with p.contexto.sesiones() as s:
    i=s.get(I,int(next(v['value'] for v in json.loads(envfile.read_text(encoding='utf-8'))['values'] if v['key']=='id_intento')))
    assert i.estado=='FINALIZADO';result['estado_SQL_independiente']=i.estado
  result['limpieza']=not envfile.exists();result['aprobado_tecnico']=True
 except Exception as err:
  result['aprobado_tecnico']=False;result['error_tipo']=type(err).__name__;raise
 finally:
  result['fuentes_estables']=result['fuentes_antes']==fuentes();result['fecha_fin']=datetime.now(timezone.utc).isoformat()
  (dest/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  suite=ET.Element('testsuite',name='RF10 MAIN',tests=str(sum(len(s['pruebas']) for s in result['solicitudes'])),errors=str(int(not result.get('aprobado_tecnico',False))))
  for s in result['solicitudes']:
   for a in s['pruebas']:
    c=ET.SubElement(suite,'testcase',classname=s['caso'],name=a['nombre'])
    if not a['aprobada']:ET.SubElement(c,'failure',message=a.get('error','fallo'))
  if not result.get('aprobado_tecnico',False):ET.SubElement(ET.SubElement(suite,'testcase',classname='LAB',name='preparación/SQL/limpieza'),'error',message=result.get('error_tipo','Fallo'))
  ET.ElementTree(suite).write(dest/'junit.xml',encoding='utf-8',xml_declaration=True)
 print(json.dumps(dict(http=len(result['solicitudes']),aserciones=result['fin']['aserciones'],limpieza=result['limpieza'],estado_integral='BLOQUEADO')))

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--ejecutar',action='store_true');a.add_argument('--newman',type=Path);a.add_argument('--evidencias',type=Path);args=a.parse_args()
 if args.ejecutar:
  if not args.newman or not args.evidencias:a.error('Faltan --newman módulo local y --evidencias carpeta NUEVA')
  ejecutar(args.evidencias,args.newman)
 else:
  with preparar() as (p,col):
   print('IMPORTAR:',col);print('IMPORTAR:',p.environment);print('SELECCIONAR:',json.loads(p.environment.read_text(encoding='utf-8'))['name']);print('CARPETA: RF-10 — MAIN; intento existente preparado SOLO LAB; no inicio productivo.')
   while input('q=cerrar y limpiar recursos propios: ').strip().lower()!='q':pass
