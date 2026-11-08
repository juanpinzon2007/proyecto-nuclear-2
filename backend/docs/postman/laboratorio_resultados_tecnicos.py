"""Demostración docente efímera; solo fixtures SQL sintéticas de las pruebas reales."""
from contextlib import ExitStack
import argparse
import getpass
import json
import sys
import warnings
import laboratorio_http as lab


def preparar(secretos, stack, *, evaluar=True):
    import pytest
    import sqlalchemy as sa
    from tests.integration.test_question_result_storage import pg_resultados, crear_registro, cerrar, guardar
    from tests.integration.test_main_evaluation_readiness import docente_http, revision
    from tests.integration.test_participation_persistence import intento, FECHA
    from app.modules.identity.infrastructure.models import UsuarioORM as U
    from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
    from app.modules.identity.infrastructure.credentials import obtener_hasheador
    from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
    from app.modules.scheduling.domain.access_codes import hash_codigo
    engine=stack.enter_context(lab.fixture(pg_resultados))
    patch=pytest.MonkeyPatch();stack.callback(patch.undo)
    c=crear_registro.__wrapped__(engine,patch)(criterios=2)
    cerrar(c,vencido=True,respondidas=1)
    revision.__wrapped__(c)
    h=stack.enter_context(lab.fixture(docente_http,c,patch))
    if evaluar:guardar(c)
    with c.sesiones.begin() as s:
        docente=s.get(U,c.docente)
        ajeno=s.scalar(sa.select(U).where(U.nombre=='Docente ajeno LAB'))
        docente.clave_hash=obtener_hasheador().hash(secretos['clave_docente'])
        ajeno.clave_hash=obtener_hasheador().hash(secretos['clave_docente'])
        s.get(C,c.datos['convocatoria_id']).codigo_hash=hash_codigo(secretos['codigo_estudiante'])
        # Permiso explícito sintético para preparar un intento SIN resultado.
        # No acredita una política productiva de repetición ni un inicio HTTP.
        permiso=PermisoIntentoExtraORM(id_participacion=c.pk,id_profesor=c.docente,cantidad_autorizada=1,
            justificacion='Preparación explícita LAB, no autorización productiva',fecha_autorizacion=FECHA)
        s.add(permiso);s.flush();pid=permiso.id_permiso_extra
        recursos=dict(correo_docente=docente.correo,correo_docente_ajeno=ajeno.correo,
            correo_estudiante=s.get(U,c.alumno).correo,sesion_id=str(c.sesion),version_id=str(c.version.id),id_intento=c.ik)
    recursos['intento_sin_resultado_id']=intento(c,c.pk,numero_intento=2,id_permiso_extra=pid)
    return h,recursos


def run(puerto, sin_evaluar=False):
    lab.settings_lab()
    if not sys.stdin.isatty() or not sys.stderr.isatty():raise RuntimeError('Use consola interactiva.')
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        secretos={k:getpass.getpass(label) for k,label in [('clave_docente','Clave sintética docente/ajeno LAB: '),
            ('codigo_estudiante','Código sintético estudiante LAB: ')]}
    if any(not v or len(v)>256 for v in secretos.values()):raise RuntimeError('Secretos LAB inválidos.')
    with ExitStack() as stack:
        _,recursos=preparar(secretos,stack,evaluar=not sin_evaluar)
        from app.main import app
        recursos['base_url']='http://127.0.0.1:'+str(lab.serve(app,puerto,stack))
        print('LAB PostgreSQL17 NUEVO. Datos sintéticos; no acredita autoría/inicio productivos.')
        print('Intento VENCIDO preparado sin resultado; use POST explícito, sin cuerpo.' if sin_evaluar else 'Resultado persistido PARCIAL: 33.33; fracciones 50/3 + 50/3; oficial=false.')
        print(json.dumps(recursos,ensure_ascii=False,indent=2))
        print('Complete SOLO valores locales de Postman. No exporte secretos ni respuestas de login.')
        input('Enter termina el servidor y elimina únicamente el contenedor propio. ')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--puerto',type=int,default=8765)
    p.add_argument('--sin-evaluar',action='store_true',help='Prepara cierre confirmado sin calcular; POST lo evaluará.')
    args=p.parse_args()
    try:run(args.puerto,args.sin_evaluar)
    except KeyboardInterrupt:pass
    except Exception:
        print("No se completó el laboratorio. Revise Docker, postgres:17 y puerto local; no se muestran detalles privados.",file=sys.stderr)
        raise SystemExit(1)
