"""Matriz nominal desde resultados reales; nunca convierte 503 en cumplimiento."""
import argparse,csv,hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def leer(p):return json.loads(p.read_text(encoding='utf-8'))
def main(evidencias):
 contratos=leer(OUT/'CONTRATOS_CASOS.json');col=leer(OUT/'Proyecto_Nuclear_27RF.postman_collection.json');seleccion=leer(evidencias/'SELECCION_RESULTADOS.json')
 snapshot=evidencias/'ciclo_integral_1/coleccion_ejecutada.json'
 viejo=leer(snapshot if snapshot.exists() else evidencias/'coleccion_ejecutada.json')
 codigo_prev={}
 for l in (ROOT/'backend/docs/AUDITORIA_COBERTURA_BACKEND_20261105.md').read_text(encoding='utf-8').splitlines():
  m=re.match(r'\| (RF-\d\d) ',l)
  if m:
   partes=l.split('|')
   if len(partes)>5:codigo_prev[m[1]]=partes[2].strip()
 resumen=[];filas=[];total=ET.Element('testsuites');aserciones=0;solicitudes=0
 portada=['# Matriz de trazabilidad RF-01 a RF-27','','Fuente literal: `REQUISITOS_FUENTE.json`, PDF central pp. 4–5 con SHA-256. Se conservan las decisiones posteriores y sus discrepancias; no se declara aprobación institucional por una implementación o fixture.','','APROBADO identifica aceptación técnica del MVP confirmado por el equipo, mediante app.main y PostgreSQL17 de laboratorio. La aprobación académica o externa se registra por separado. La activación productiva del consentimiento requiere una fuente oficial aprobada. BLOQUEADO puede contener operaciones técnicas aprobadas: no representa cumplimiento integral. FALLIDO conserva un defecto observado; NO EJECUTADO no tiene veredicto.','','Cada carpeta se prepara en una base nueva. Las precondiciones repetidas por RF son solicitudes reales, pero no se contabilizan como funcionalidades distintas. Un HTTP negativo esperado es aceptación de seguridad; 503 no es un caso positivo de funcionalidad.','','| RF | Requisito | Aceptación técnica MVP | HTTP ejecutadas | pm.test | Evidencia / detalle | Aceptación académica o externa |','|---|---|---|---:|---:|---|---|']
 junit_py=[]
 for modo in ('focal','relacionada','general'):
  p=evidencias/('pytest_'+modo)/'junit.xml'
  if p.exists():junit_py+=ET.parse(p).findall('.//testcase')
 for c,folder in zip(contratos,col['item']):
  rf=c['rf'];archivo=ROOT/seleccion[rf]
  r=leer(archivo) if archivo.exists() else dict(rf=rf,solicitudes=[],fallos=0,limpieza=False)
  actuales={s['caso']:s for s in r['solicitudes']}
  assert [s['caso'] for s in r['solicitudes']]==[s['nombre'] for s in c['casos']][:len(r['solicitudes'])],rf+' contiene casos diferentes del contrato actual'
  # La evidencia ciclo1 solo se reutiliza cuando request y scripts son idénticos.
  if 'ciclo_integral_1' in archivo.parts:
   anterior=next(x for x in viejo['item'] if x['name'].startswith(rf+' '))
   def relevante(f):return [dict(request={k:v for k,v in x['request'].items() if k!='description'},event=x['event'],name=x['name']) for x in f['item']]
   assert relevante(anterior)==relevante(folder),rf+' necesita repetición por cambio funcional'
  estado=('NO EJECUTADO' if not archivo.exists() else 'FALLIDO' if r['fallos'] or not r['limpieza'] or len(r['solicitudes'])!=len(c['casos']) else 'BLOQUEADO' if c['bloqueo'] or any(s.get('http')==503 for s in r['solicitudes']) else 'APROBADO')
  n=sum(len(s['pruebas']) for s in r['solicitudes']);aserciones+=n;solicitudes+=len(r['solicitudes'])
  pxml=archivo.parent/'junit.xml'
  if pxml.exists():total.append(ET.parse(pxml).getroot())
  tests_ejecutados=[]
  for t in c['tests']:
   f,metodo=t.split('::');modulo=Path(f).stem
   encontrados=[x for x in junit_py if x.get('classname','').split('.')[-1]==modulo and x.get('name','').split('[')[0]==metodo and x.find('failure')is None and x.find('error')is None and x.find('skipped')is None]
   if encontrados:tests_ejecutados.append(dict(pytest=t,variantes=len({x.get('classname','')+'::'+x.get('name','') for x in encontrados})))
  evidencia=archivo.relative_to(ROOT).as_posix();externo=c.get('aceptacion_externa') or ('Proveedor SMTP institucional pendiente de configuración y validación externa.' if rf in ('RF-20','RF-21') else 'Contrato vigente conservado; aprobación nueva no atribuida.');fila=dict(rf=rf,nombre=c['nombre'],estado=estado,bloqueo=c['bloqueo'],aceptacion_externa=externo,http=len(r['solicitudes']),aserciones=n,evidencia=evidencia,tests_ejecutados=tests_ejecutados)
  resumen.append(fila);nombre=rf+'.md';portada.append(f"| {rf} | {c['nombre']} | **{estado}** | {len(r['solicitudes'])} | {n} | [{rf}]({nombre}) | {fila['aceptacion_externa']} |")
  d=[f"# {rf} — {c['nombre']}",'',c['fuente'],'',f"**Aceptación técnica MVP: {estado}.** "+(c['bloqueo'] or 'El recorrido de aceptación y sus negativas aprobaron; ver límites del entorno.'),'','## Implementación reutilizada','',codigo_prev.get(rf,'Ver rutas y contratos del módulo en OpenAPI.'),'','## Preparación y superficie','',f"`preparar-27rf.ps1 -RF {rf}`. Modo {c['modo']}; PostgreSQL17 nuevo, JWT reales. Cuentas, matrículas, grants y asignación son datos administrativos sintéticos. La colección maestra utiliza app.main. En modo principal, atestación sintética y decisión de inicio se cargan por configuración real del servidor en ámbito LABORATORIO. Los proveedores y relojes de main permanecen reales. En modo reportes, la preparación académica previa es sintética. No acredita aprobación institucional del consentimiento.",'','## Casos y resultados nominales','','| Caso / operación | HTTP esperado → observado | Resultado | Aserciones reales |','|---|---|---|---|']
  for esperado in c['casos']:
   s=actuales.get(esperado['nombre'],dict(caso=esperado['nombre'],http=None,pruebas=[],errores=[]));ase='; '.join(a['nombre'] for a in s['pruebas']);superficie='LAB' if 'base_url_laboratorio'in esperado['ruta'] else 'app.main'
   caso_estado='NO EJECUTADO' if s.get('http')is None else 'BLOQUEADO' if s['http']==503 else 'APROBADO' if s['http']==esperado['esperado'] and not s['errores'] and s['pruebas'] and all(a['aprobada'] for a in s['pruebas']) else 'FALLIDO'
   nombre_caso=s['caso'].replace('|','&#124;')
   d.append(f"| {nombre_caso} / `{esperado['metodo']} {esperado['ruta']}` ({superficie}) | {esperado['esperado']} → {s.get('http')} | {caso_estado} | {ase} |")
   filas.append(dict(rf=rf,descripcion=c['fuente'],estado_rf=estado,aceptacion_externa=fila['aceptacion_externa'],caso=esperado['caso'],nombre=s['caso'],metodo=esperado['metodo'],endpoint=esperado['ruta'],superficie=superficie,http_esperado=esperado['esperado'],http_real=s.get('http'),aserciones=ase,resultado=caso_estado,evidencia=evidencia,pytest='; '.join(x['pytest'] for x in tests_ejecutados),referencia_PT='PM-'+rf+' es caso HTTP nuevo; no se atribuye ficha CP inexistente. RF-01 tiene apoyo CP-ID-01/02; el resto requiere conciliación documental individual con PT-DCP-01 v2.4.'))
  d+=['','## Aceptación académica o externa','',fila['aceptacion_externa'],'','## Evidencias','','Resultado: `'+evidencia+'`; JUnit nominal junto al JSON. SQL posterior desde otra Session:','','```json',json.dumps(r.get('despues'),ensure_ascii=False,indent=2),'```','','Las aserciones pm.test se ejecutaron con Newman 6.2.3; no se afirma haber usado la interfaz gráfica de Desktop. Los binarios XLSX/PDF, si corresponden, están junto al resultado y fueron leídos y contrastados. No se fabricaron capturas.','','## Pruebas automatizadas complementarias ejecutadas','']
  d += ['- `'+x['pytest']+'` ('+str(x['variantes'])+' variantes no solapadas por identificador).' for x in tests_ejecutados] or ['No se atribuye una ejecución pytest adicional; consultar resultado HTTP/SQL.']
  d+=['','## Sustentación','','Importe la colección maestra y el Environment privado de este RF, seleccione su nombre y ejecute únicamente esta carpeta desde el primer caso. No use el Runner sobre las 27 carpetas con una sola base. Muestre URL, HTTP, Response sintética y Test Results; oculte tokens, códigos, credenciales y cuerpos de login. Capture los casos PM-'+rf+' con sus nombres; las capturas manuales siguen pendientes. En RF-07 priorice edición, consulta exacta, publicación y rechazos. En RF-19 ejecute w antes de cada consulta WORKER 2/3.','']
  (OUT/nombre).write_text('\n'.join(d),encoding='utf-8')
 cont=Counter(x['estado'] for x in resumen)
 resultado=dict(head_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),rama=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),conteos={k:cont[k] for k in ('APROBADO','FALLIDO','BLOQUEADO','NO EJECUTADO')},http=solicitudes,aserciones_pm_test=aserciones,aserciones_fallidas=sum(1 for x in total.findall('.//testcase') if x.find('failure')is not None),rf=resumen,nota='Nueva ejecución completa e independiente por RF. Se conservan los ciclos diagnósticos y se informan las suites pytest separadamente, sin sumar ejecuciones solapadas.')
 (OUT/'RESULTADOS_27RF.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
 portada+=['',f"**Total: {cont['APROBADO']} APROBADOS, {cont['BLOQUEADO']} BLOQUEADOS, {cont['FALLIDO']} FALLIDOS y {cont['NO EJECUTADO']} NO EJECUTADOS.** {solicitudes} solicitudes ejecutadas y {aserciones} aserciones pm.test; La aceptación académica o externa conserva sus condiciones explícitas en la última columna.",'','La matriz CSV contiene una fila por caso, método, endpoint, aserciones reales, veredicto, evidencia nominal y referencias pytest acreditadas. Las fichas PT-DCP-01 no se renumeraron: los identificadores PM son nuevos, con conciliación documental pendiente donde no hay ficha equivalente.','']
 (OUT/'MATRIZ_TRAZABILIDAD_27RF.md').write_text('\n'.join(portada),encoding='utf-8')
 with (OUT/'matriz_trazabilidad_27rf.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)
 brechas=['# Condiciones externas y alcance del MVP','','El resultado técnico deriva de ejecuciones completas y verificables. Ningún HTTP 503 acredita una funcionalidad positiva.','','## Decisiones confirmadas por el equipo','','Una pregunta por escena y ausencia de ciclos alcanzables. Respuestas inmutables. Participación inicial pendiente, con estado efectivo derivado del intento. Evaluación por orden docente después del cierre y recuperación de pendientes. Repetición individual del mismo caso y versión histórica mediante permiso de un uso.','','## Aprobación académica o externa','']
 brechas += [f"- **{c['rf']}** {c['aceptacion_externa']}" for c in contratos if c.get('aceptacion_externa')]
 brechas += ['','RF-20/RF-21 conservan aceptación SMTP local. El proveedor, remitente, URL y recepción institucional requieren validación de despliegue.','','## Diagnósticos conservados','','Los ciclos V3 previos preservan el fallo inicial del esperado de rollback SQL, las importaciones del preparador, la incompatibilidad entre un reloj LAB congelado y la aceptación en tiempo real, y una aserción JavaScript con tipos distintos. Se corrigieron la prueba o el preparador y sus aserciones, conservando los contratos HTTP. Los resultados finales se ejecutaron completos después de las correcciones. Las evidencias están fuera del repositorio en C:/SPS/nuclear_v3_20261111.','','No se automatiza la aprobación institucional, la publicación oficial al cerrar ni el cambio de políticas académicas. Los resultados técnicos y oficiales conservan sus contratos existentes separados.','']
 (OUT/'BRECHAS_RF.md').write_text('\n'.join(brechas),encoding='utf-8')
 ET.ElementTree(total).write(evidencias/'junit_postman_27rf.xml',encoding='utf-8',xml_declaration=True)
 print(json.dumps(dict(conteos=resultado['conteos'],http=solicitudes,pm_test=aserciones),ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidencias',type=Path,required=True);a=p.parse_args();main(a.evidencias.resolve())
