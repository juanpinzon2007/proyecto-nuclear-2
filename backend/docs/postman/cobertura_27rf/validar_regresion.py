"""Regresión existente, .env desactivado, SQLite aislado y PG17 exclusivamente propio."""
import argparse,hashlib,json,os,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def safe(t):
 t=re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[JWT omitido]',t)
 return re.sub(r'(postgres(?:ql)?(?:\+\w+)?://[^:\s/@]+:)[^@\s]+@',r'\1[omitido]@',t)
def ejecutar(modo,dest):
 dest.mkdir(parents=True,exist_ok=False)
 env={k:v for k,v in os.environ.items() if not k.startswith(('POSTGRES_','IDENTITY_','PARTICIPATION_','PG')) and k not in ('DATABASE_URL','TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL','PYTHONPATH')}
 env.update(PYTHONPATH=str(ROOT/'backend'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',SPS_TEST_IDENTITY_MAPPING_DOCKER='1',SPS_TEST_POSTGRESQL='0')
 focal=['backend/tests/integration/test_cases_graph_authoring.py','backend/tests/unit/cases']
 contratos=json.loads((OUT/'CONTRATOS_CASOS.json').read_text(encoding='utf-8'))
 relacionada=['backend/tests/unit']+sorted({'backend/'+t.split('::')[0] for c in contratos for t in c['tests']})+['backend/tests/integration/test_admin_teacher_directory.py','backend/tests/integration/test_main_staff_login.py','backend/tests/integration/test_session_state_consistency.py','backend/tests/integration/test_session_notification_atomicity.py']
 targets=list(dict.fromkeys(focal if modo=='focal' else relacionada));targets=[p for p in targets if (ROOT/p).exists()]
 def huellas():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('backend/app','backend/tests') for p in (ROOT/folder).rglob('*.py')}
 antes=huellas();launcher="import sys;from app.core.config import Settings,get_settings;Settings.model_config['env_file']=None;get_settings.cache_clear();import pytest;raise SystemExit(pytest.main(sys.argv[1:]))"
 cmd=[sys.executable,'-B','-c',launcher,'-c','backend/pyproject.toml',*targets,'-q','-rs','--tb=short','-p','no:cacheprovider','-o','junit_family=legacy','--junitxml='+str(dest/'junit.xml')]
 meta=dict(fecha_inicio=datetime.now(timezone.utc).isoformat(),comando=cmd,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),env_file=False,postgres='Contenedores nuevos de fixtures opt-in; nunca URL heredada',targets=targets,fuentes_antes=antes)
 (dest/'ejecucion.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
 p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace');tail=[]
 with (dest/'consola.log').open('w',encoding='utf-8') as f:
  for l in p.stdout:l=safe(l);f.write(l);f.flush();tail=(tail+[l])[-30:]
 code=p.wait();r=dict(codigo=code,fuentes_estables=antes==huellas(),fecha_fin=datetime.now(timezone.utc).isoformat())
 xml=dest/'junit.xml'
 if xml.exists():
  tree=ET.parse(xml)
  for el in tree.iter():
   if el.text:el.text=safe(el.text)
   if el.tail:el.tail=safe(el.tail)
   for k,v in list(el.attrib.items()):el.set(k,safe(v))
  tree.write(xml,encoding='utf-8',xml_declaration=True);cs=tree.findall('.//testcase');r.update(total=len(cs),fallidas=sum(x.find('failure')is not None for x in cs),errores=sum(x.find('error')is not None for x in cs),omitidas=sum(x.find('skipped')is not None for x in cs));r['aprobadas']=r['total']-r['fallidas']-r['errores']-r['omitidas']
 (dest/'resultado.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(''.join(tail));print(json.dumps(r));return code
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--modo',choices=['focal','relacionada'],required=True);p.add_argument('--evidencias',type=Path,required=True);a=p.parse_args();raise SystemExit(ejecutar(a.modo,a.evidencias))
