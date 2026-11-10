"""Ejecuta una carpeta RF con PG17 NUEVO; o prepara su Environment privado para Desktop."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta,datetime,timezone
import argparse,json,os,secrets,subprocess,sys,shutil
from pathlib import Path
from uuid import UUID,uuid4
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];ENTREGA=OUT.parent/'entrega_20261109'
sys.path.insert(0,str(ENTREGA));import desktop

def setval(env,key,value):
 v=next((v for v in env['values'] if v['key']==key),None)
 if v is None:v=dict(key=key,value='',type='default',enabled=True);env['values'].append(v)
 v['value']=str(value)
 if any(s in key for s in ('token','clave','codigo')):v['type']='secret'

def contrato(rf):return next(x for x in json.loads((OUT/'CONTRATOS_CASOS.json').read_text(encoding='utf-8')) if x['rf']==rf)

@contextmanager
def preparar(rf):
 c=contrato(rf)
 if rf=='RF-24':
  # Convocar ANTES de cerrar la sesión: misma secuencia de las pruebas existentes.
  # Se adapta solo la preparación LAB, nunca el contrato de convocatoria.
  def preparar_ausencia(secretos,stack):
   from tests.integration.test_evaluation_readiness import otro_convocado,cerrar_sesion_fixture
   h,r=desktop.reportes.preparar_tecnico(secretos,stack,incluir_abierto=False)
   h.c.rf_ausente=otro_convocado(h.c);cerrar_sesion_fixture(h.c)
   r['convocatoria_id']=str(h.c.datos['convocatoria_id'])
   return h,r
  desktop.reportes.preparar=preparar_ausencia
 with desktop.preparar(c['modo']) as p:
  env=json.loads(p.environment.read_text(encoding='utf-8'));env['name']='NUCLEAR 27RF — '+rf+' — '+uuid4().hex[:8]
  for v in json.loads((OUT/'Proyecto_Nuclear_27RF.postman_environment.json').read_text(encoding='utf-8'))['values']:
   if not any(x['key']==v['key'] for x in env['values']):env['values'].append(v)
  setval(env,'rf_activo',rf);setval(env,'rf_paso',0);setval(env,'rf_nuevo_correo',uuid4().hex+'@universidad.test');setval(env,'rf_clave_nueva',secrets.token_urlsafe(32))
  from tests.integration.cases.conftest import payload_valido
  payload=payload_valido.__wrapped__();payload['rubric']['versionRegla']='PREGUNTAS_100_V1'
  for o in payload['scenarios'][0]['questions'][0]['options']:o['valoraciones']={'Análisis':100 if o['esCorrecta'] else 0}
  payload['case']['nombre']='Caso RF07 sintético '+uuid4().hex[:8];editado=deepcopy(payload)
  editado['scenarios']=[deepcopy(payload['scenarios'][0]) for _ in (1,2)]
  for n in (1,2):
   e=editado['scenarios'][n-1];e['orden']=n;e['contextoSituacional']='Contexto persistente '+str(n)
   q=e['questions'][0];q['enunciado']='Pregunta editable '+str(n)
   q['options'].append(dict(orden=3,texto='Tercera alternativa',esCorrecta=False,justificacion='Justificación sintética tercera',valoraciones={'Análisis':0}))
  setval(env,'rf_payload',json.dumps(payload,ensure_ascii=False));setval(env,'rf_payload_editado',json.dumps(editado,ensure_ascii=False))
  if c['modo']=='reportes':
   h=p.contexto.c;setval(env,'id_participacion',h.pk)
   from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
   with h.sesiones() as s:setval(env,'estudiante_id',s.get(C,h.datos['convocatoria_id']).estudiante_id)
   if rf=='RF-24':
    setval(env,'rf_ausente',h.rf_ausente)
    base=f'/scheduling/sesiones/{h.sesion}/evaluacion/consolidacion'
    rev=p.contexto.client.get(base,headers=p.contexto.auth['docente']);assert rev.status_code==200 and not rev.json()['publicable']
    setval(env,'rf_revision_incompleta',rev.json()['revision_sha256'])
  else:
   h=p.contexto
   setval(env,'rf_inicio',(h.ahora-timedelta(minutes=3)).isoformat());setval(env,'rf_fin',(h.ahora+timedelta(minutes=40)).isoformat());setval(env,'rf_estudiante_integer',h.titular.id)
   if rf in ('RF-04','RF-18','RF-20','RF-21'):
    # Solo preparación administrativa: cuentas/matrículas veraces. No grants implícitos.
    from app.modules.identity.infrastructure.models import UsuarioORM as U
    from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
    from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
    from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S
    with h.sesiones.begin() as s:
     a=s.get(A,h.aid)
     origen=s.get(S,h.sesion)
     nueva=S(espacio_academico_id=origen.espacio_academico_id,version_caso_id=origen.version_caso_id,
       docente_id=origen.docente_id,fecha_inicio=origen.fecha_inicio,fecha_fin=origen.fecha_fin,
       tiempo_maximo_minutos=origen.tiempo_maximo_minutos,estado='SIN_INICIAR',
       mensaje_personalizado='Convocatoria sintética 27RF')
     s.add(nueva);s.flush()
     s.add(A(id_grupo=a.id_grupo,id_caso=a.id_caso,sesion_programada_id=nueva.id,
       version_caso_id=a.version_caso_id,apertura=a.apertura,cierre=a.cierre,
       fecha_limite_ingreso=a.fecha_limite_ingreso,tiempo_maximo_min=a.tiempo_maximo_min))
     setval(env,'rf_sesion_convocatoria',nueva.id)
     for key in ('rf_nuevo_alumno_uuid','rf_otro_nuevo_alumno_uuid'):
      u=U(id_rol=2,nombre='Matriculado sintético 27RF',correo=uuid4().hex+'@universidad.test',clave_hash='sin-login-LAB');s.add(u);s.flush();ident=uuid4()
      if key=='rf_nuevo_alumno_uuid':setval(env,'rf_nuevo_alumno_correo',u.correo)
      s.add_all([IA(id_usuario=u.id_usuario,sistema='SCHEDULING',id_academico=ident),M(id_grupo=a.id_grupo,id_estudiante=u.id_usuario,fecha_ingreso=a.apertura)]);setval(env,key,ident)
  p.environment.write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
  master=p.carpeta/'Proyecto_Nuclear_27RF.postman_collection.json'
  with master.open('xb') as f:f.write((OUT/'Proyecto_Nuclear_27RF.postman_collection.json').read_bytes())
  if p.coleccion.parent.resolve()!=p.carpeta.resolve():raise RuntimeError('Colección temporal fuera de su carpeta propia.')
  p.coleccion.unlink()  # Solo copia efímera creada por desktop.preparar, no el original del repositorio.
  p.coleccion=master
  try:yield p,c,editado
  finally:
   if master.parent.resolve()!=p.carpeta.resolve():raise RuntimeError('Ruta fuera del temporal propio.')
   master.unlink(missing_ok=True)

def comprobar_sql(p,rf,ids,esperado):
 import sqlalchemy as sa
 from app.modules.cases.infrastructure.models import VersionCasoModel as V
 from app.modules.participation.infrastructure.models import ParticipacionModel as P,IntentoModel as I
 from app.modules.scheduling.infrastructure.models import NotificacionModel as N
 h=p.contexto.c if p.modo=='reportes' else p.contexto
 r=p.verificar_sql()
 with h.sesiones() as s:
  r['postgres_version']=s.execute(sa.text('SHOW server_version')).scalar();assert r['postgres_version'].startswith('17.')
  if ids.get('rf_version'):
   v=s.get(V,UUID(ids['rf_version']));assert v is not None
   assert v.nombre==esperado['case']['nombre'] and len(v.escenarios)==2
   for e in v.escenarios:
    src=esperado['scenarios'][e.orden-1];assert e.contexto_situacional==src['contextoSituacional'] and len(e.preguntas)==1
    q=e.preguntas[0];assert q.enunciado==src['questions'][0]['enunciado'] and len(q.opciones)==3
    for o in q.opciones:
     op=next(x for x in src['questions'][0]['options'] if x['orden']==o.orden);assert (o.texto,o.es_correcta,o.justificacion)==(op['texto'],op['esCorrecta'],op['justificacion'])
   r['autoria_confirmada_otra_session']=dict(version=str(v.id),escenarios=2,preguntas=2,opciones=6,estado=v.estado.value,justificaciones_exactas=True,rubrica_historica=str(v.rubrica.id))
  if rf=='RF-24':
   from app.modules.participation.infrastructure.academic_results_models import AusenciaAcademicaModel as Aus
   aus=s.scalars(sa.select(Aus)).all();assert len(aus)==1
   r['ausencias_confirmadas']=len(aus);assert s.scalar(sa.select(sa.func.count()).select_from(P))==1 and s.scalar(sa.select(sa.func.count()).select_from(I))==1
   r['sin_intentos_ficticios']=True
  if rf=='RF-27':
   avisos=s.scalars(sa.select(N).where(N.publicacion_evaluacion_id.is_not(None))).all();assert len(avisos)==1
   r['avisos_publicacion']=len(avisos)
  if ids.get('rf_sesion') and rf=='RF-19':
   from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S,EventoAuditoriaModel as E
   sid=UUID(ids['rf_sesion']);assert s.get(S,sid).estado=='FINALIZADO'
   assert s.scalar(sa.select(sa.func.count()).select_from(E).where(E.sesion_id==sid))==2
   r['transiciones_docentes_sin_duplicar']=2
 return r

def ejecutar(rf,dest,newman):
 dest.mkdir(parents=True,exist_ok=False);datos=dict(rf=rf,fecha_utc=datetime.now(timezone.utc).isoformat(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),codigo_local=True,solicitudes=[],worker=[],ejecutor='Newman 6.2.3, runtime independiente por Send',fallos=0,limpieza=False)
 c=contrato(rf)
 try:
  with preparar(rf) as (p,c,esperado):
   datos['modo']=p.modo;datos['antes']=p.verificar_sql();ruta_temp=p.environment
   proc=subprocess.Popen([shutil.which('node'),str(OUT/'ejecutar_send.cjs'),str(p.coleccion),str(p.environment),rf,str(dest)],cwd=ROOT,env={**os.environ,'NUCLEAR_NEWMAN_MODULE':str(newman)},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1)
   try:
    for line in proc.stdout:
     ev=json.loads(line)
     if ev['tipo']=='worker':
      w=p.worker();datos['worker'].append(w);proc.stdin.write(json.dumps(dict(ok=w['codigo']==0))+'\n');proc.stdin.flush()
     elif ev['tipo']=='solicitud':datos['solicitudes'].append(ev);print(rf,len(datos['solicitudes']),ev.get('http'),len(ev['errores']),flush=True)
     elif ev['tipo']=='fin':datos['fin']=ev;datos['fallos']=ev['fallos']
     elif ev['tipo']=='fatal':raise RuntimeError('Error de ejecutor; véase registro nominal sin secretos.')
    codigo=proc.wait(timeout=30)
   finally:
    if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
   if codigo==0 and datos.get('fin') and len(datos['solicitudes'])==len(c['casos']):
    datos['despues']=comprobar_sql(p,rf,datos['fin']['ids'],esperado)
    archivos=[x for x in datos['solicitudes'] if 'archivo'in x]
    if archivos:
     from openpyxl import load_workbook
     from pypdf import PdfReader
     assert len(archivos)==2 and archivos[0]['publicacion']['X-Publicacion-Id']==archivos[1]['publicacion']['X-Publicacion-Id']
     assert load_workbook(dest/'reporte.xlsx')['Resultados']['H2'].value==33.33
     assert '33.33'in ''.join(pg.extract_text() for pg in PdfReader(dest/'reporte.pdf').pages)
     datos['binarios_verificados']=True
    if rf=='RF-19':assert len(datos['worker'])==2 and 'Sesiones cerradas: 1'in datos['worker'][0]['salida'] and 'Sesiones cerradas: 0'in datos['worker'][1]['salida']
   else:datos['fallos']=max(1,datos['fallos'])
  datos['limpieza']=not ruta_temp.exists()
 except Exception as e:
  datos['fallos']=max(1,datos['fallos']);datos['error_tipo']=type(e).__name__;datos['limpieza']=not locals().get('ruta_temp',Path('__no_existe__')).exists()
 datos['bloqueo']=c['bloqueo'];datos['estado']='FALLIDO' if datos['fallos'] else 'BLOQUEADO' if c['bloqueo'] else 'APROBADO'
 (dest/'resultado.json').write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding='utf-8')
 suite=ET.Element('testsuite',name=rf,tests=str(sum(len(x['pruebas']) for x in datos['solicitudes'])+bool(datos.get('error_tipo'))),failures=str(sum(not a['aprobada'] for x in datos['solicitudes'] for a in x['pruebas'])),errors=str(int(bool(datos.get('error_tipo')))))
 props=ET.SubElement(suite,'properties');ET.SubElement(props,'property',name='estado_integral_RF',value=datos['estado'])
 for s in datos['solicitudes']:
  for a in s['pruebas']:
   test=ET.SubElement(suite,'testcase',classname=s['caso'],name=a['nombre'])
   if not a['aprobada']:ET.SubElement(test,'failure',message=a.get('error') or 'Aserción fallida')
 if datos.get('error_tipo'):ET.SubElement(ET.SubElement(suite,'testcase',classname=rf,name='Preparación/SQL/limpieza'),'error',message=datos['error_tipo'])
 ET.ElementTree(suite).write(dest/'junit.xml',encoding='utf-8',xml_declaration=True)
 print(rf,datos['estado'], 'aserciones',datos.get('fin',{}).get('aserciones',0),flush=True)
 return datos

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rf',required=True,choices=[f'RF-{i:02}' for i in range(1,28)]+['todos']);parser.add_argument('--evidencias',type=Path);parser.add_argument('--newman',type=Path);parser.add_argument('--preparar',action='store_true');a=parser.parse_args()
 if a.preparar:
  if a.rf=='todos':parser.error('Desktop: prepare una carpeta RF cada vez.')
  with preparar(a.rf) as (p,c,_):
   print('IMPORTAR:',p.coleccion);print('IMPORTAR:',p.environment);print('SELECCIONAR Environment:',json.loads(p.environment.read_text(encoding='utf-8'))['name']);print('CARPETA:',a.rf);print('PRIMER SEND:',c['casos'][0]['nombre']);print('LAB sintético; nunca compartir/exportar valores secretos.')
   for accion in iter(lambda:input('i=abrir carpeta; w=Worker RF-19; q=cerrar: ').strip().lower(),'q'):
    if accion=='i' and os.name=='nt':os.startfile(str(p.carpeta))
    if accion=='w' and a.rf=='RF-19':print(json.dumps(p.worker(),ensure_ascii=False))
 else:
  if not a.evidencias or not a.newman:parser.error('Se requiere --evidencias carpeta NUEVA y --newman módulo privado.')
  if a.rf=='todos':
   a.evidencias.mkdir(parents=True,exist_ok=False)
   seleccion={};fallos=0
   for i in range(1,28):
    rf=f'RF-{i:02}';log=a.evidencias/(rf+'.log')
    with log.open('w',encoding='utf-8') as f:r=subprocess.run([sys.executable,'-B',__file__,'--rf',rf,'--evidencias',str(a.evidencias/rf),'--newman',str(a.newman)],cwd=ROOT,stdout=f,stderr=f)
    fallos+=bool(r.returncode);seleccion[rf]=(a.evidencias/rf/'resultado.json').resolve().relative_to(ROOT).as_posix()
    print(rf,'terminado; código',r.returncode,flush=True)
   (a.evidencias/'SELECCION_RESULTADOS.json').write_text(json.dumps(seleccion,indent=2),encoding='utf-8')
   (a.evidencias/'coleccion_ejecutada.json').write_bytes((OUT/'Proyecto_Nuclear_27RF.postman_collection.json').read_bytes())
   print('Fin HTTP: los RF bloqueados conservan su clasificación; no equivale a 27 aprobados.')
   raise SystemExit(1 if fallos else 0)
  else:raise SystemExit(1 if ejecutar(a.rf,a.evidencias,a.newman)['fallos'] else 0)
