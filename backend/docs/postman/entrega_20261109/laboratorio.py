"""Preparación de sustentación: solo datos/servidores efímeros, sin cambios productivos."""
from contextlib import ExitStack
from pathlib import Path
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from uuid import UUID,uuid4
import argparse,json,sys,secrets
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import laboratorio_http as lab


def preparar(secretos,stack):
    import pytest
    import sqlalchemy as sa
    from tests.integration.test_cases_graph_authoring import pg_autoria
    from tests.integration.cases.conftest import payload_valido
    from tests.integration.test_lab_student_journey import recorrido_lab
    from app.modules.identity.infrastructure.models import UsuarioORM as U
    from app.modules.identity.infrastructure.credentials import obtener_hasheador
    from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
    from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
    from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S,ConvocatoriaModel as C
    from app.modules.scheduling.domain.access_codes import hash_codigo
    from app.modules.cases.infrastructure.models import VersionCasoModel as V
    sesiones=stack.enter_context(lab.fixture(pg_autoria))
    patch=pytest.MonkeyPatch();stack.callback(patch.undo)
    payload=payload_valido.__wrapped__()
    payload['rubric']['versionRegla']='PREGUNTAS_100_V1'
    for e in payload['scenarios']:
        for q in e['questions']:
            for o in q['options']:o['valoraciones']={'Análisis':100 if o['esCorrecta'] else 0}
    # Solo datos docentes sintéticos: caso/grafo/publicación/programación/convocatoria
    # se ejecutan mediante las rutas reales ya usadas por la fixture integral.
    h=stack.enter_context(lab.fixture(recorrido_lab,sesiones,payload,patch,lambda *a:None))
    with sesiones.begin() as s:
        principal=s.get(S,h.sesion)
        profesor=s.get(U,s.get(G,s.get(A,h.aid).id_grupo).id_profesor)
        admin=s.scalar(sa.select(U).where(U.id_rol==3))
        admin.clave_hash=obtener_hasheador().hash(secretos['clave_admin'])
        profesor.clave_hash=obtener_hasheador().hash(secretos['clave_docente'])
        ajeno=U(id_rol=1,nombre='Docente ajeno entrega LAB',correo=f'ajeno-{uuid4().hex}@universidad.test',
            clave_hash=obtener_hasheador().hash(secretos['clave_docente']))
        s.add(ajeno);s.flush()
        for sistema in ('CASES','SCHEDULING'):s.add(IA(id_usuario=ajeno.id_usuario,sistema=sistema,id_academico=uuid4()))
        for estudiante,key in ((h.titular,'codigo_estudiante'),(h.ajeno,'codigo_ajeno')):
            s.get(C,UUID(estudiante.convocatoria)).codigo_hash=hash_codigo(secretos[key])
        fin=datetime.now(timezone.utc)-timedelta(hours=26)
        w=S(espacio_academico_id=principal.espacio_academico_id,version_caso_id=h.version,
            docente_id=principal.docente_id,fecha_inicio=fin-timedelta(hours=1),fecha_fin=fin,
            tiempo_maximo_minutos=30,estado='EN_CURSO')
        s.add(w);s.flush()
        wc=C(sesion_id=w.id,estudiante_id=h.titular.uuid,codigo_hash=hash_codigo(secrets.token_urlsafe(32)),estado='ACTIVA')
        s.add(wc);s.flush()
        h.worker_sesion=w.id;h.worker_convocatoria=wc.id
        recursos=dict(correo_admin=admin.correo,correo_docente=profesor.correo,correo_docente_ajeno=ajeno.correo,
            correo_estudiante=h.titular.correo,correo_ajeno=h.ajeno.correo,id_docente=str(profesor.id_usuario),
            estudiante_id=str(h.titular.uuid),convocatoria_id=h.titular.convocatoria,sesion_id=str(h.sesion),
            version_id=str(h.version),id_asignacion=str(h.aid),caso_uuid=str(s.get(V,h.version).caso_id),
            espacio_academico_id=str(principal.espacio_academico_id),worker_sesion_id=str(w.id))
    return h,recursos


def estado_worker(h):
    from sqlalchemy import select,func
    from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S,EventoAuditoriaModel as A,NotificacionModel as N
    from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
    with h.sesiones() as s:
        w=s.get(S,h.worker_sesion)
        return dict(estado=w.estado,version_caso_id=str(w.version_caso_id),
            auditorias=s.scalar(select(func.count()).select_from(A).where(A.sesion_id==h.worker_sesion,A.estado_nuevo=='FINALIZADO')),
            avisos_sesion=s.scalar(select(func.count()).select_from(N).where(N.convocatoria_id==h.worker_convocatoria,N.tipo=='SESION_FINALIZADA')),
            resultados_tecnicos_totales=s.scalar(select(func.count()).select_from(R)))


def worker_una_vez(h):
    from tests.integration.test_worker_process import una_revision
    antes=estado_worker(h)
    codigo,salida=una_revision(SimpleNamespace(sesiones=h.sesiones))
    despues=estado_worker(h)
    assert codigo==0 and despues['estado']=='FINALIZADO' and despues['auditorias']==despues['avisos_sesion']==1
    assert despues['resultados_tecnicos_totales']==antes['resultados_tecnicos_totales']
    return dict(comando='python -B -c LAUNCHER_AISLADO --once; run_module(app.modules.scheduling.infrastructure.worker_runner)',
        codigo=codigo,salida=salida,antes=antes,despues=despues)


def run(args):
    lab.settings_lab();secretos=lab.secretos_interactivos()
    with ExitStack() as stack:
        h,r=preparar(secretos,stack)
        from app.main import app
        r.update(base_url='http://127.0.0.1:'+str(lab.serve(app,args.puerto,stack)),
            base_url_laboratorio='http://127.0.0.1:'+str(lab.serve(h.lab.app,args.puerto_lab,stack)))
        print('LAB propio PG17; reloj fijo SOLO en operaciones de ingreso/intento; JWT real.')
        print('Fuente de consentimiento y políticas de inicio SINTÉTICAS; inicio solo en app aislada.')
        print('Preparación ya ejecutada por API: caso PREGUNTAS_100_V1, grafo, publicación, sesión y convocatoria.')
        print('Vínculos/grupo/matrícula/asignación/consentimiento son preparación administrativa LAB.')
        print('Preparación API ya ejecutada (ASGI, sin cuerpos ni credenciales):')
        for n,paso in enumerate(h.pasos,1):
            print(f"PREP-{n:02}: {paso['superficie']} | {paso['metodo']} {paso['ruta']} | HTTP {paso['observado']} | {paso['paso']}")
        print(json.dumps(r,ensure_ascii=False,indent=2))
        print('Clave DOCENTE también corresponde al DOCENTE AJENO sintético. No exportar secretos/JWT.')
        print('Runner principal: 32 solicitudes. Worker: Send por pasos, w entre consultas.')
        while True:
            accion=input('w = worker real --once; e = estado SQL; q = cerrar y limpiar solo recursos propios: ').strip().lower()
            if accion=='q':break
            if accion=='w':print(json.dumps(worker_una_vez(h),ensure_ascii=False,indent=2))
            elif accion=='e':print(json.dumps(estado_worker(h),ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--puerto',type=int,default=8765);p.add_argument('--puerto-lab',type=int,default=8766)
    args=p.parse_args()
    if args.puerto==args.puerto_lab or not all(1024<=x<=65535 for x in (args.puerto,args.puerto_lab)):p.error('Dos puertos locales distintos entre 1024 y 65535.')
    try:run(args)
    except (KeyboardInterrupt,EOFError):print('Fin del laboratorio; limpieza del contexto ejecutada.')
    except Exception:
        print('No se completó la demostración. Verifique Docker/puertos y evidencia; no se muestran datos privados.',file=sys.stderr)
        raise SystemExit(1)
