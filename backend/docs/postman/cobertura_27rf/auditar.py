"""Inventario reproducible sin conectarse a una BD; fuentes y cobertura existente."""
import ast,hashlib,json,re,sys,zipfile
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent

def main():
 p=ROOT/'_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf'
 paginas=[re.sub(r'(?m)^\s*[45]\s*$','',PdfReader(p).pages[i].extract_text()).replace('ID Épica Requisito Descripción verificable','') for i in (3,4)]
 t=' '.join(' '.join(paginas).split()); requisitos={}
 for n in range(1,28):
  clave=f'RF-{n:02}';inicio=t.index(clave+' ');fin=t.index(f'RF-{n+1:02} ',inicio+6) if n<27 else t.index('2.2 Requisitos',inicio)
  requisitos[clave]=t[inicio:fin].strip()
 colecciones=[]
 for p in ROOT.rglob('*.postman_collection.json'):
  if '.git' in p.parts:continue
  try:
   c=json.loads(p.read_text(encoding='utf-8-sig'))
   def solicitudes(items):
    return sum(solicitudes(x['item']) if 'item'in x else 1 for x in items)
   colecciones.append(dict(ruta=p.relative_to(ROOT).as_posix(),nombre=c['info']['name'],solicitudes=solicitudes(c['item']),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  except (ValueError,KeyError):pass
 tests=[]
 for p in sorted(list((ROOT/'backend/tests').rglob('test_*.py'))+list((ROOT/'backend/app/modules/participation/tests').rglob('test_*.py'))):
  a=ast.parse(p.read_text(encoding='utf-8-sig'))
  for f in ast.walk(a):
   if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name.startswith('test_'):tests.append(p.relative_to(ROOT/'backend').as_posix()+'::'+f.name)
 fuente=dict(ruta='_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf',sha256=hashlib.sha256((ROOT/'_referencias_locales/ProyectoNuclear-IngenieriaSoftwareII (1).pdf').read_bytes()).hexdigest(),paginas=[4,5],requisitos=requisitos)
 (OUT/'REQUISITOS_FUENTE.json').write_text(json.dumps(fuente,ensure_ascii=False,indent=2),encoding='utf-8')
 (OUT/'INVENTARIO_PREVIO.json').write_text(json.dumps(dict(colecciones=colecciones,tests=tests,nota='Inventario estático; no acredita ejecución. No se atribuyen CP-I sin correspondencia individual.'),ensure_ascii=False,indent=2),encoding='utf-8')
 sys.path.insert(0,str(ROOT/'backend/docs/postman'));import laboratorio_http;laboratorio_http.settings_lab()
 from app.main import app
 (OUT/'openapi_main.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding='utf-8')
 print('RF:',len(requisitos),'colecciones:',len(colecciones),'métodos pytest:',len(tests),'rutas OpenAPI:',len(app.openapi()['paths']))
if __name__=='__main__':main()
