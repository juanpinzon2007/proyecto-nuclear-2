"""BD2-04: solo PostgreSQL nuevo, migraciones existentes + SQL experimental."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[2]
sys.path.insert(0,str(BACKEND))
sys.path.insert(0,str(HERE.parent/'laboratorio_er28'))

from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from tests.identity import academic_identity_support as support
from tests.integration.test_cases_history import nuevo, leer, publicar
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.infrastructure.models import VersionCasoModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.cases.application.published_version import consultar_version_publicada
from app.modules.scheduling.application.programar_sesion import programar_sesion, ErrorProgramacion
from app.modules.scheduling.infrastructure.models import EspacioAcademicoModel
from run_experiment import INVENTORY


TABLES = ['caso','version_caso','escenario','pregunta','opcion_respuesta','rubrica',
          'criterio_rubrica','nivel_rubrica','valoracion_opcion']


def main(*, revision_guard=None):
    runid=uuid4().hex
    files=[HERE/n for n in ('run_lab.py','protecciones.sql','revertir_protecciones.sql')]
    files += sorted((BACKEND/'alembic/versions').glob('*.py'))
    files += [BACKEND/'tests/identity/academic_identity_support.py',BACKEND/'tests/integration/test_cases_history.py',
              BACKEND/'app/modules/cases/infrastructure/repositories/caso_repository.py',
              BACKEND/'app/modules/scheduling/application/programar_sesion.py']
    ev={'run_id':runid,'tests':[], 'artifacts':{p.relative_to(BACKEND).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    install=(HERE/'protecciones.sql').read_text(encoding='utf-8')
    uninstall=(HERE/'revertir_protecciones.sql').read_text(encoding='utf-8')
    original_docker=support.docker
    owned=[]
    failure=None
    baseline='20261101_er28_base_academica'

    def instalar(c):
        if revision_guard:
            command.upgrade(support.config_alembic(c),revision_guard)
        else:
            c.exec_driver_sql(install,execution_options={'no_parameters':True})

    def revertir(c):
        if revision_guard:
            command.downgrade(support.config_alembic(c),baseline)
        else:
            c.exec_driver_sql(uninstall,execution_options={'no_parameters':True})

    def docker_tracked(*args,**kwargs):
        result=original_docker(*args,**kwargs)
        if args[0]=='create':owned.append(result)
        return result

    def check(name,ok,details=None):
        ev['tests'].append({'id':name,'passed':bool(ok),'details':details})
        if not ok:raise AssertionError(name)

    support.docker=docker_tracked
    try:
        with support.motor_postgresql_desechable() as engine:
            cid=owned[-1]
            raw=json.loads(original_docker('inspect',cid))[0]
            ev['laboratory']={'container_id':cid,'name':raw['Name'],
                'image':raw['Config']['Image'],'labels':raw['Config']['Labels'],
                'tmpfs':raw['HostConfig']['Tmpfs'],
                'mounts':[{'type':m['Type'],'destination':m['Destination']} for m in raw['Mounts']],
                'ports':raw['NetworkSettings']['Ports']}
            mount_text=original_docker('exec',cid,'cat','/proc/self/mountinfo')
            mounts=[line for line in mount_text.splitlines() if len(line.split())>4 and line.split()[4]=='/var/lib/postgresql/data']
            check('tmpfs_real_sin_volumen',len(mounts)==1 and mounts[0].split(' - ')[1].split()[0]=='tmpfs'
                  and set(raw['HostConfig']['Tmpfs'])=={'/var/lib/postgresql/data'})
            ev['laboratory']['tmpfs_real_verificado']=True
            with engine.begin() as c:
                ev['laboratory']['database']=c.scalar(text('SELECT current_database()'))
                ev['laboratory']['postgresql']=c.scalar(text('SHOW server_version'))
                command.upgrade(support.config_alembic(c),baseline)
                support.columnas_publicacion_para_fixture_historica(c)  # ORM actual en laboratorio histórico, sin instalar publicación.
            factory=sessionmaker(engine,expire_on_commit=False)

            def seed():
                v=nuevo()
                with factory() as s: CasoRepository(s).guardar(v)
                return v

            def catalog():
                with engine.connect() as c:return c.scalar(text(INVENTORY))

            def probe(name,sql,params=None,expected='23514',role=None):
                actual='00000'; message=''
                with engine.connect() as c:
                    tx=c.begin()
                    try:
                        if role:c.exec_driver_sql('SET LOCAL ROLE '+role)
                        c.execute(text(sql),params or {})
                    except DBAPIError as e:
                        actual=e.orig.sqlstate;message=str(e.orig).splitlines()[0]
                    finally:tx.rollback()
                check(name,actual==expected,{'expected':expected,'actual':actual,'sql':sql,'message':message})

            a,b=seed(),seed()
            a=publicar(factory,a)
            original=catalog()
            ev['catalog_before']=original
            # Vulnerabilidades originales reproducidas y revertidas; no se confunden
            # con pruebas positivas de seguridad después de instalar los triggers.
            probe('ANTES_SQL_modifica_PUBLICADO', 'UPDATE version_caso SET nombre=\'Sin protección\' WHERE id=:id',{'id':a.id},'00000')
            option=a.escenarios[0].preguntas[0].opciones[0]
            foreign=b.rubrica.criterios[0]
            probe('ANTES_FK_acepta_criterio_ajeno',
                  'UPDATE valoracion_opcion SET criterio_id=:c WHERE opcion_id=:o',{'c':foreign.id,'o':option.id},'00000')
            # Preflight falla sin dejar funciones/triggers ni reparar datos legados.
            with engine.connect() as c:
                tx=c.begin()
                c.execute(text('UPDATE valoracion_opcion SET criterio_id=:c WHERE opcion_id=:o'),{'c':foreign.id,'o':option.id})
                sp=c.begin_nested();state='00000'
                preflight_error=''
                try:instalar(c)
                except DBAPIError as e:state=e.orig.sqlstate;preflight_error=str(e.orig)
                finally:sp.rollback()
                check('preflight_rechaza_legado_incoherente',state=='23514',{'state':state,'error':preflight_error})
                check('instalacion_fallida_atomica',c.scalar(text("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'bd204_%'"))==0)
                tx.rollback()
            with engine.begin() as c:instalar(c)
            if revision_guard:
                with engine.connect() as c:
                    check('head_migrado_real',c.scalar(text('SELECT version_num FROM alembic_version'))==revision_guard)
            protected=catalog();ev['catalog_protected']=protected
            check('ninguna_tabla_columna_constraint_o_indice_nuevo',all(original[k]==protected[k] for k in ('all_user_tables','columns','constraints','indexes')))
            check('18_triggers',protected['user_triggers']==original['user_triggers']+18)
            # Matriz: INSERT/UPDATE/DELETE de todos los hijos de ambas clases históricas.
            def ids(v):
                e=v.escenarios[0];p=e.preguntas[0];o=p.opciones[0];r=v.rubrica;c=r.criterios[0];n=c.niveles[0]
                return {'caso':v.caso_id,'version_caso':v.id,'escenario':e.id,'pregunta':p.id,
                        'opcion_respuesta':o.id,'rubrica':r.id,'criterio_rubrica':c.id,'nivel_rubrica':n.id,
                        'valoracion_opcion':(o.id,c.id)}

            for estado in ('PUBLICADO','ARCHIVADO'):
                v=seed();v=publicar(factory,v)
                if estado=='ARCHIVADO':
                    v.archivar()
                    with factory() as s:CasoRepository(s).actualizar_estado(v)
                keys=ids(v)
                for t,key in keys.items():
                    where='opcion_id=:o AND criterio_id=:c' if t=='valoracion_opcion' else 'id=:id'
                    params={'o':key[0],'c':key[1]} if t=='valoracion_opcion' else {'id':key}
                    field={'caso':'docente_creador_id','version_caso':'nombre','escenario':'contexto_situacional',
                           'pregunta':'enunciado','opcion_respuesta':'texto','rubrica':'version_regla',
                           'criterio_rubrica':'nombre','nivel_rubrica':'descriptor','valoracion_opcion':'puntaje'}[t]
                    val=':nuevo' if t=='caso' else ('1.25' if t=='valoracion_opcion' else "'Alterado'")
                    probe(estado+':UPDATE:'+t,f'UPDATE {t} SET {field}={val} WHERE {where}',params|({'nuevo':uuid4()} if t=='caso' else {}))
                    probe(estado+':DELETE:'+t,f'DELETE FROM {t} WHERE {where}',params)
                    if t not in ('caso','version_caso'):
                        # Nuevo hijo válido por FK/UQ, pero su versión está congelada.
                        new_id=uuid4()
                        columns={'escenario':"id,version_caso_id,orden,contexto_situacional",
                                 'pregunta':"id,escenario_id,orden,enunciado",'opcion_respuesta':"id,pregunta_id,orden,texto,es_correcta,justificacion",
                                 'rubrica':"id,version_caso_id,nombre,version_regla",'criterio_rubrica':"id,rubrica_id,nombre,peso",
                                 'nivel_rubrica':"id,criterio_id,nombre,puntaje,descriptor",'valoracion_opcion':"opcion_id,criterio_id,puntaje"}[t]
                        if t=='valoracion_opcion':
                            # La otra opción no recibe un segundo valor idéntico por PK: usar
                            # un criterio de otra edición mostraría congelación antes de pertenencia.
                            insert='INSERT INTO valoracion_opcion VALUES (:o,:c,1)'
                            values={'o':v.escenarios[0].preguntas[0].opciones[1].id,'c':foreign.id}
                        else:
                            parent={'escenario':v.id,'pregunta':keys['escenario'],'opcion_respuesta':keys['pregunta'],
                                    'rubrica':v.id,'criterio_rubrica':keys['rubrica'],'nivel_rubrica':keys['criterio_rubrica']}[t]
                            tail={'escenario':"999,'Ensayo'",'pregunta':"999,'Ensayo'",'opcion_respuesta':"999,'Ensayo',false,'Justificación'",
                                  'rubrica':"'Otra','lab'",'criterio_rubrica':"'Otro',1",'nivel_rubrica':"'Otro',1,'Descriptor'"}[t]
                            insert=f'INSERT INTO {t} ({columns}) VALUES (:id,:parent,{tail})'
                            values={'id':new_id,'parent':parent}
                        probe(estado+':INSERT:'+t,insert,values)
                probe(estado+':no_revertir_estado','UPDATE version_caso SET estado=\'BORRADOR\' WHERE id=:id',{'id':v.id})
                check(estado+':rollback_grafo_igual',leer(factory,v)==v)

            # Restricciones de pertenencia e identidad mientras son borradores.
            c,d=seed(),seed();ci,di=ids(c),ids(d)
            probe('crear_DIRECTAMENTE_PUBLICADO_rechazado',
                  "INSERT INTO version_caso (id,caso_id,numero,nombre,desarrollo_situacional,contexto_historia,tiempo_estimado_min,estado) VALUES (:id,:p,99,'Ensayo','d','c',20,'PUBLICADO')",{'id':uuid4(),'p':c.caso_id})
            probe('valoracion_INSERT_entre_versiones','INSERT INTO valoracion_opcion VALUES (:o,:c,1)',{'o':ci['opcion_respuesta'],'c':di['criterio_rubrica']})
            probe('valoracion_UPDATE_entre_versiones','UPDATE valoracion_opcion SET criterio_id=:c WHERE opcion_id=:o',{'o':ci['opcion_respuesta'],'c':di['criterio_rubrica']})
            for t,parent in [('escenario','version_caso_id'),('pregunta','escenario_id'),('opcion_respuesta','pregunta_id'),('rubrica','version_caso_id'),('criterio_rubrica','rubrica_id'),('nivel_rubrica','criterio_id')]:
                parent_table={'version_caso_id':'version_caso','escenario_id':'escenario','pregunta_id':'pregunta','rubrica_id':'rubrica','criterio_id':'criterio_rubrica'}[parent]
                probe('no_reparentar:'+t,f'UPDATE {t} SET {parent}=:parent WHERE id=:id',{'id':ci[t],'parent':di[parent_table]})
            probe('version_no_cambia_familia','UPDATE version_caso SET caso_id=:p WHERE id=:id',{'p':d.caso_id,'id':c.id})
            probe('version_no_cambia_numero','UPDATE version_caso SET numero=999 WHERE id=:id',{'id':c.id})
            probe('no_publicar_editando','UPDATE version_caso SET estado=\'PUBLICADO\',nombre=\'Alterado\' WHERE id=:id',{'id':c.id})
            probe('no_archivar_borrador','UPDATE version_caso SET estado=\'ARCHIVADO\' WHERE id=:id',{'id':c.id})
            probe('FK_sigue_rechazando_huerfano',"INSERT INTO pregunta VALUES (:id,:p,1,'Sin padre')",{'id':uuid4(),'p':uuid4()},'23503')
            for t in TABLES:probe('TRUNCATE_bloqueado:'+t,f'TRUNCATE {t} CASCADE')
            # Escritor actual real: borrar/recrear hijos del borrador, publicar y archivar.
            edited=nuevo();edited.id=c.id;edited.caso_id=c.caso_id;edited.docente_creador_id=c.docente_creador_id;edited.numero=c.numero
            with factory() as s:CasoRepository(s).reemplazar(edited)
            check('repositorio_reemplaza_borrador',leer(factory,c)==edited)
            edited=publicar(factory,edited)
            with factory() as s:
                ref=consultar_version_publicada(s,version_id=edited.id)
                check('referencia_exacta_sin_filtrar_contenido',ref.version_id==edited.id and ref.rubrica_id==edited.rubrica.id and ref.version_regla==edited.rubrica.version_regla)
            with factory.begin() as s:
                espacio=EspacioAcademicoModel(nombre='Laboratorio BD204');s.add(espacio);s.flush();eid=espacio.id
                inicio=datetime(2030,1,1,tzinfo=timezone.utc)
                scheduled=programar_sesion(s,espacio_academico_id=eid,version_caso_id=edited.id,docente_id=edited.docente_creador_id,
                    fecha_inicio=inicio,fecha_fin=inicio+timedelta(hours=1),tiempo_maximo_minutos=20)
                check('Scheduling_conserva_UUID_exacto',scheduled.version_caso_id==edited.id)
                scheduled_id=scheduled.id
            # Edición 2 de la MISMA familia: fixture ORM, sin endpoint nuevo.
            later=nuevo();later.caso_id=edited.caso_id;later.docente_creador_id=edited.docente_creador_id;later.numero=2
            with factory.begin() as s:
                mapper=CasoRepository(s)
                model=VersionCasoModel(id=later.id,caso_id=later.caso_id,numero=later.numero,nombre=later.nombre,
                    desarrollo_situacional=later.desarrollo_situacional,contexto_historia=later.contexto_historia,
                    tiempo_estimado_min=later.tiempo_estimado_min,estado=EstadoCaso.BORRADOR)
                model.escenarios=[mapper._mapear_escenario(e) for e in later.escenarios]
                model.rubrica=mapper._mapear_rubrica(later.rubrica)
                s.add(model)
            later=publicar(factory,later)
            with factory() as s:
                check('edicion_posterior_no_sustituye_referencia',consultar_version_publicada(s,version_id=edited.id)==ref)
                check('dos_ediciones_familia_mismos_ids',s.scalar(text('SELECT count(*) FROM version_caso WHERE caso_id=:id'),{'id':edited.caso_id})==2)
            edited.archivar()
            with factory() as s:CasoRepository(s).actualizar_estado(edited)
            check('archivar_no_edita_grafo',leer(factory,edited)==edited)
            with engine.connect() as conn:
                check('archivo_no_reasigna_sesion',conn.scalar(text('SELECT version_caso_id FROM sesion_programada WHERE id=:id'),{'id':scheduled_id})==edited.id)
            # Cascadas legítimas de borrador; no se borran filas del equipo.
            draft_delete=seed()
            with engine.begin() as c:c.execute(text('DELETE FROM caso WHERE id=:id'),{'id':draft_delete.caso_id})
            check('cascada_borrador_sin_huerfanos',leer(factory,draft_delete) is None)
            # Concurrencia: la publicación mantiene el bloqueo y el editor SQL espera.
            def race(isolation):
                v=seed();ready=threading.Event();pids=[];errors=[]
                def edit_sql():
                    try:
                        with engine.connect().execution_options(isolation_level=isolation) as conn:
                            tx=conn.begin()
                            try:
                                pids.append(conn.scalar(text('SELECT pg_backend_pid()')));ready.set()
                                conn.execute(text("UPDATE opcion_respuesta SET texto='Carrera' WHERE id=:id"),{'id':v.escenarios[0].preguntas[0].opciones[0].id})
                                tx.commit()
                            finally:
                                if tx.is_active:tx.rollback()
                    except DBAPIError as e:errors.append(e.orig.sqlstate)
                    except BaseException as e:errors.append(type(e).__name__)
                with engine.connect() as owner:
                    tx=owner.begin();owner.execute(text("UPDATE version_caso SET estado='PUBLICADO' WHERE id=:id"),{'id':v.id})
                    thread=threading.Thread(target=edit_sql);thread.start()
                    try:
                        if not ready.wait(2):raise AssertionError('Hilo sin conexión')
                        deadline=time.monotonic()+1;blocked=False
                        while time.monotonic()<deadline:
                            if owner.scalar(text('SELECT cardinality(pg_blocking_pids(:p))'),{'p':pids[0]}):blocked=True;break
                            time.sleep(.01)
                        check('bloqueo_real:'+isolation,blocked)
                        tx.commit()
                    finally:
                        if tx.is_active:tx.rollback()
                        thread.join(5)
                    check('editor_no_pasa_publicacion:'+isolation,not thread.is_alive() and errors==(['23514'] if isolation=='READ COMMITTED' else ['40001']),errors)
                check('contenido_concurrente_intacto:'+isolation,leer(factory,v).escenarios[0].preguntas[0].opciones[0].texto==v.escenarios[0].preguntas[0].opciones[0].texto)
            race('READ COMMITTED');race('REPEATABLE READ')
            # Orden inverso: una edición ya iniciada se confirma ANTES de publicar.
            v=seed();ready=threading.Event();pids=[];errors=[]
            def publish_sql():
                try:
                    with engine.begin() as conn:
                        pids.append(conn.scalar(text('SELECT pg_backend_pid()')));ready.set()
                        conn.execute(text("UPDATE version_caso SET estado='PUBLICADO' WHERE id=:id"),{'id':v.id})
                except BaseException as e:errors.append(type(e).__name__)
            with engine.connect() as editor:
                tx=editor.begin()
                editor.execute(text("UPDATE opcion_respuesta SET texto='Editado antes de publicar' WHERE id=:id"),{'id':v.escenarios[0].preguntas[0].opciones[0].id})
                thread=threading.Thread(target=publish_sql);thread.start()
                try:
                    if not ready.wait(2):raise AssertionError('Publicador sin conexión')
                    limit=time.monotonic()+1;blocked=False
                    while time.monotonic()<limit:
                        if editor.scalar(text('SELECT cardinality(pg_blocking_pids(:p))'),{'p':pids[0]}):blocked=True;break
                        time.sleep(.01)
                    check('publicacion_espera_editor_iniciado',blocked)
                    tx.commit()
                finally:
                    if tx.is_active:tx.rollback()
                    thread.join(5)
                check('publicacion_posterior_confirma_sin_error',not thread.is_alive() and not errors,errors)
            final=leer(factory,v)
            check('edicion_confirma_antes_de_congelarse',final.estado==EstadoCaso.PUBLICADO and final.escenarios[0].preguntas[0].opciones[0].texto=='Editado antes de publicar')
            probe('tras_concurrencia_ya_no_edita',"UPDATE opcion_respuesta SET texto='Edición tardía' WHERE id=:id",{'id':v.escenarios[0].preguntas[0].opciones[0].id})
            # Un rol de escritura no propietario no puede desactivar la barrera.
            with engine.begin() as c:
                c.exec_driver_sql('CREATE ROLE bd204_writer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE')
                c.exec_driver_sql('GRANT USAGE ON SCHEMA public TO bd204_writer')
                c.exec_driver_sql('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO bd204_writer')
            probe('rol_app_no_desactiva_triggers','ALTER TABLE opcion_respuesta DISABLE TRIGGER USER',expected='42501',role='bd204_writer')
            probe('rol_app_no_cambia_replication_role',"SET LOCAL session_replication_role='replica'",expected='42501',role='bd204_writer')
            probe('rol_app_tambien_rechaza_historico',"UPDATE version_caso SET nombre='Rol app' WHERE id=:id",{'id':a.id},role='bd204_writer')
            check('sin_tablas_o_columnas_nuevas_final',all(original[k]==catalog()[k] for k in ('all_user_tables','columns','constraints','indexes')))
            def row_counts():
                with engine.connect() as c:
                    return {t:c.scalar(text('SELECT count(*) FROM public."'+t+'"')) for t in original['tables']}
            before_down=row_counts();ev['rows_before_down']=before_down
            with engine.begin() as c:revertir(c)
            check('reversion_no_cambia_catalogo_original',catalog()==original)
            check('reversion_preserva_filas',row_counts()==before_down)
            probe('reversion_solo_retira_barrera',"UPDATE version_caso SET nombre='Sin barrera otra vez' WHERE id=:id",{'id':a.id},'00000')
            if revision_guard:
                with engine.connect() as c:
                    check('head_revertido_real',c.scalar(text('SELECT version_num FROM alembic_version'))==baseline)
                with engine.begin() as c:instalar(c)
                check('reupgrade_mismo_catalogo',catalog()==protected)
                check('reupgrade_preserva_filas',row_counts()==before_down)
            ev['status']='passed'
    except BaseException as e:
        failure=e;ev['status']='failed';ev['error']=str(e)
    finally:
        support.docker=original_docker
        ev['cleanup']=[]
        for cid in owned:
            p=subprocess.run(['docker','inspect','--format','{{.Id}}',cid],capture_output=True,text=True,timeout=10)
            removed=p.returncode!=0 and 'No such' in p.stderr
            ev['cleanup'].append({'id':cid,'removed_verified':removed})
            if not removed:ev['status']='failed';failure=failure or RuntimeError('Limpieza no comprobada')
        dest=HERE/('evidencia_'+runid+'.json')
        dest.write_text(json.dumps(ev,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        print(json.dumps({'status':ev['status'],'tests':len(ev['tests']),'passed':sum(t['passed'] for t in ev['tests']),
                          'evidence':dest.name,'cleanup':ev['cleanup']}),flush=True)
    if failure:raise SystemExit(ev.get('error','Limpieza fallida'))
    return ev


if __name__=='__main__':
    for key in ('TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL'):
        os.environ.pop(key,None)
    os.environ['SPS_TEST_IDENTITY_MAPPING_DOCKER']='1'
    os.environ['SPS_TEST_POSTGRESQL']='0'
    main()
