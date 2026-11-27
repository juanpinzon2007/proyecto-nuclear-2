"""Activa un laboratorio efimero por carpeta de Postman en este equipo."""
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json, os, re, secrets, sys
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

repo = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(repo / 'backend/docs/postman/cobertura_27rf'))
from ejecutar_rf import preparar, comprobar_correo

lock = Lock()
active = {}
executor = ThreadPoolExecutor(max_workers=1)
lifecycle = ExitStack()
port = 18647
config = Path(os.environ['LOCALAPPDATA']) / 'NuclearStandLocal'
config.mkdir(exist_ok=True)
keyfile = config / 'acceso-local'
if not keyfile.exists():
    with keyfile.open('x') as file:
        file.write(secrets.token_urlsafe(32))
key = keyfile.read_text()
environment = dict(name='Nuclear - todas las carpetas (local)', _postman_variable_scope='environment',
                   values=[dict(key='clave_selector_local', value=key, type='secret', enabled=True)])
(config/'Nuclear-MULTI.postman_environment.json').write_text(json.dumps(environment), encoding='utf8')

def start(rf):
    try:
        lifecycle.close()
        p, _, _ = lifecycle.enter_context(preparar(rf))
        values = json.loads(p.environment.read_text(encoding='utf8'))['values']
        with lock:
            active.update(status='ready', values=values, lab=p, workers={})
    except Exception as exc:
        with lock:
            active.update(status='error', error=type(exc).__name__)

class Selector(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer '+key):
            self.send_error(403)
            return
        match = re.fullmatch(r'/(RF-(?:0[1-9]|1[0-9]|2[0-7]))/(abrir|worker2|worker3|correo2)', self.path)
        if not match:
            self.send_error(404)
            return
        rf, action = match.groups()
        with lock:
            if active.get('rf') != rf and active.get('status') != 'loading' and action == 'abrir':
                active.clear()
                active.update(rf=rf, status='loading')
                executor.submit(start,rf)
            state = active.get('status')
            if state == 'loading':
                code, data = 202, {'mensaje':'Preparando PostgreSQL. Vuelve a pulsar Send en unos segundos.'}
            elif state != 'ready' or active.get('rf') != rf:
                code, data = 409, {'mensaje':'Abre el primer paso de la carpeta.', 'error':active.get('error')}
            elif action == 'abrir':
                code, data = 200, {'values':active['values']}
            else:
                try:
                    if action not in active['workers']:
                        if action.startswith('worker') and rf=='RF-19':
                            assert active['lab'].worker()['codigo']==0
                        elif action=='correo2' and rf in ('RF-20','RF-21'):
                            comprobar_correo(active['lab'],2)
                        else:
                            raise ValueError()
                        active['workers'][action]=True
                    code,data=200,{'ok':True}
                except Exception as exc:
                    code,data=409,{'error':type(exc).__name__}
        raw=json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

if __name__=='__main__':
    with HTTPServer(('127.0.0.1',port),Selector) as server:
        try:
            server.serve_forever()
        finally:
            executor.submit(lifecycle.close).result()
            executor.shutdown()
