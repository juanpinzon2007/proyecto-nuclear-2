"""Demo MAIN con puertos LAB explícitos o control cerrado. Solo PG17 propio."""
import argparse,json,os,sys,subprocess,shutil
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];sys.path.insert(0,str(OUT.parent/'entrega_20261109'))
import desktop

class RelojLaboratorio:
 def __init__(self):self.desplazamiento=timedelta(0)
 def ahora(self):return datetime.now(timezone.utc)+self.desplazamiento

@contextmanager
def preparar(rf):
 with desktop.preparar('principal') as p:
  from app.main import app
  from app.modules.participation.api.dependencies import obtener_reloj_escenario,obtener_fechas_escenario
  from app.modules.identity.api.consent_dependencies import obtener_reloj_consentimiento
  from tests.integration.test_main_start_composition import componer_laboratorio
  prev=dict(app.dependency_overrides);h=p.contexto;reloj=RelojLaboratorio()
  if rf!='CONTROL':
   componer_laboratorio(h)
   app.dependency_overrides[obtener_reloj_escenario]=lambda:reloj
   app.dependency_overrides[obtener_reloj_consentimiento]=lambda:reloj
  env=json.loads(p.environment.read_text(encoding='utf-8'));env['name']='FASE1 '+rf+' — '+('SIN APROBACION' if rf=='CONTROL' else 'SOLO POLITICAS LAB')+' — '+uuid4().hex[:8]
  vals={v['key']:v for v in env['values']}
  for v in json.loads((OUT/'Proyecto_Nuclear_fase1.postman_environment.json').read_text(encoding='utf-8'))['values']:vals.setdefault(v['key'],v)
  for k,v in dict(fase1_rf=rf,id_estudiante_usuario=h.titular.id).items():vals[k]['value']=str(v)
  if rf=='CONTROL':
   # Evidencia sintética válida SOLO como precondición LAB del control negativo.
   from tests.integration.test_lab_student_journey import aceptar
   a=aceptar(h)
   for k,v in dict(id_version_documento=h.docid,referencia=h.documento.referencia,huella=h.documento.huella,id_consentimiento=a['id_consentimiento']).items():vals[k]['value']=str(v)
  env['values']=list(vals.values());p.environment.write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
  col=p.carpeta/'Proyecto_Nuclear_fase1.postman_collection.json'
  with col.open('xb') as f:f.write((OUT/'Proyecto_Nuclear_fase1.postman_collection.json').read_bytes())
  anterior=p.coleccion;assert anterior.parent==p.carpeta;anterior.unlink();p.coleccion=col
  def vencer():
   import sqlalchemy as sa
   from app.modules.participation.infrastructure.models import IntentoModel as I
   with h.sesiones() as s:
    i=s.scalar(sa.select(I).where(I.estado=='EN_CURSO'));assert i is not None
    limite=obtener_fechas_escenario().desde_db(i.inicio)+timedelta(microseconds=int(i.duracion_concedida_segundos*Decimal(1000000)))
   reloj.desplazamiento=limite-datetime.now(timezone.utc)+timedelta(seconds=1)
  try:yield p,vencer
  finally:
   app.dependency_overrides.clear();app.dependency_overrides.update(prev);col.unlink(missing_ok=True)

def ejecutar(rf,dest,newman):
 dest.mkdir(parents=True,exist_ok=False);r=dict(rf=rf,estado_RF='BLOQUEADO',motivo='Sin documento oficial/proceso de aprobación ni políticas productivas definitivas.',solicitudes=[],errores=0,gui_ejecutada=False)
 with preparar(rf) as (p,vencer):
  r['antes']=p.verificar_sql();propio=p.environment
  n=subprocess.Popen([shutil.which('node'),str(OUT/'send.cjs'),str(p.coleccion),str(p.environment),rf,str(dest)],env={**os.environ,'NUCLEAR_NEWMAN_MODULE':str(newman)},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
  try:
   for line in n.stdout:
    ev=json.loads(line)
    if ev['tipo']=='reloj':vencer();n.stdin.write('{"ok":true}\n');n.stdin.flush();r['vencimiento_reloj_controlado_LAB']=True
    elif ev['tipo']=='solicitud':r['solicitudes'].append(ev);print(rf,len(r['solicitudes']),ev.get('http'),len(ev['errores']),flush=True)
    elif ev['tipo']=='fin':r['fin']=ev;r['errores']=ev['fallos']
    elif ev['tipo']=='fatal':r['errores']+=1
   assert n.wait(timeout=30)==0 and r['errores']==0
  finally:
   if n.poll() is None:n.terminate();n.wait(timeout=10)
  r['despues']=p.verificar_sql()
  import sqlalchemy as sa
  from app.modules.participation.infrastructure.models import IntentoModel as I
  if rf=='CONTROL':assert r['antes']==r['despues'] and r['despues']['participaciones']==r['despues']['intentos']==0
  else:
   assert r['despues']['participaciones']==1 and r['despues']['resultados']==r['despues']['publicaciones']==0
   assert r['despues']['intentos']==(2 if rf=='RF-25' else 1)
   with p.contexto.sesiones() as s:
    intentos=s.scalars(sa.select(I).order_by(I.id_intento)).all()
    assert all(i.duracion_concedida_segundos==1800 for i in intentos)
    assert intentos[-1].estado==('VENCIDO' if rf=='RF-23' else 'FINALIZADO')
    r['sql_independiente']=[dict(id=i.id_intento,numero=i.numero_intento,estado=i.estado,duracion=str(i.duracion_concedida_segundos),consentimiento=i.id_consentimiento,permiso=i.id_permiso_extra) for i in intentos]
 r['limpieza']=not propio.exists();r['aprobadas_http']=True
 (dest/'resultado.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 suite=ET.Element('testsuite',name=rf,tests=str(sum(len(x['pruebas']) for x in r['solicitudes'])),failures='0');props=ET.SubElement(suite,'properties');ET.SubElement(props,'property',name='estado_integral_RF',value='BLOQUEADO')
 for x in r['solicitudes']:
  for a in x['pruebas']:
   el=ET.SubElement(suite,'testcase',classname=x['caso'],name=a['nombre'])
   if not a['aprobada']:ET.SubElement(el,'failure',message=a.get('error','Aserción fallida'))
 ET.ElementTree(suite).write(dest/'junit.xml',encoding='utf-8',xml_declaration=True)
 print(json.dumps(dict(rf=rf,solicitudes=len(r['solicitudes']),aserciones=r['fin']['aserciones'],estado_integral='BLOQUEADO')))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--rf',choices=['CONTROL','RF-12','RF-23','RF-25'],default='CONTROL');parser.add_argument('--ejecutar',action='store_true');parser.add_argument('--evidencias',type=Path);parser.add_argument('--newman',type=Path);a=parser.parse_args()
 if a.ejecutar:
  if not a.evidencias or not a.newman:parser.error('Faltan --evidencias carpeta NUEVA y --newman módulo local.')
  ejecutar(a.rf,a.evidencias,a.newman)
 else:
  with preparar(a.rf) as (p,vencer):
   print('IMPORTAR:',p.coleccion);print('IMPORTAR:',p.environment);print('SELECCIONAR:',json.loads(p.environment.read_text(encoding='utf-8'))['name']);print('CARPETA:',a.rf)
   print('No acredita consentimiento institucional ni habilitación productiva. t=avanzar reloj SOLO RF-23 antes de RELOJ LAB; q=limpiar.')
   for accion in iter(lambda:input('i=carpeta; t=vencer LAB; q=cerrar: ').strip().lower(),'q'):
    if accion=='i' and os.name=='nt':os.startfile(str(p.carpeta))
    elif accion=='t' and a.rf=='RF-23':vencer();print('Reloj LAB situado después del límite; no se alteraron timestamps SQL.')
