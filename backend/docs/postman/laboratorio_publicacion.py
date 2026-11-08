"""Sustentación efímera: publica por HTTP un resultado real, con preparación LAB explícita."""
from contextlib import ExitStack
import argparse,getpass,json,sys,warnings
import laboratorio_http as lab
from laboratorio_resultados_tecnicos import preparar as preparar_tecnico


def preparar(secretos,stack):
    from tests.integration.test_evaluation_readiness import cerrar_sesion_fixture
    h,recursos=preparar_tecnico(secretos,stack,incluir_abierto=False)
    # Preparación administrativa sintética. NO acredita creación/inicio/cierre
    # docente por HTTP ni aprobación institucional de consentimiento.
    cerrar_sesion_fixture(h.c)
    recursos['convocatoria_id']=str(h.c.datos['convocatoria_id'])
    return h,recursos


def run(puerto):
    lab.settings_lab()
    if not sys.stdin.isatty() or not sys.stderr.isatty():raise RuntimeError('Use consola interactiva.')
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        secretos={k:getpass.getpass(label) for k,label in [('clave_docente','Clave sintética docente/ajeno LAB: '),('codigo_estudiante','Código sintético estudiante LAB: ')]}
    if any(not v or len(v)>256 for v in secretos.values()):raise RuntimeError('Secretos LAB inválidos.')
    with ExitStack() as stack:
        _,recursos=preparar(secretos,stack)
        from app.main import app
        recursos['base_url']='http://127.0.0.1:'+str(lab.serve(app,puerto,stack))
        print('PG17 NUEVO: sesión finalizada, intento vencido y resultado técnico 33.33, NO publicado.')
        print('Preparación administrativa LAB; publicación y consulta se ejecutan por app.main/JWT real.')
        print(json.dumps(recursos,ensure_ascii=False,indent=2))
        print('Postman: Proyecto_Nuclear_publicacion_academica; secretos solo en valores locales, nunca exportar.')
        input('Enter cierra el servidor y elimina únicamente el contenedor propio. ')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--puerto',type=int,default=8765)
    try:run(p.parse_args().puerto)
    except KeyboardInterrupt:pass
    except Exception:
        print('No se completó el laboratorio; revise Docker/postgres:17/puerto. No se muestran datos privados.',file=sys.stderr)
        raise SystemExit(1)
