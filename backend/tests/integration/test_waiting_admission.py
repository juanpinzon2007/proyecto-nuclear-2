"""Sala/admisión real en main y PG17 propio. Sin políticas sintéticas de ingreso."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event,Barrier
from uuid import UUID,uuid4
from types import SimpleNamespace

import pytest
from sqlalchemy import select,func,event,text
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from alembic import command

from app.db.session import get_engine
from app.modules.identity.infrastructure.models import UsuarioORM as U
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C,SesionProgramadaModel as S,EventoAuditoriaModel as E,NotificacionModel as N
from app.modules.scheduling.application.registrar_observadores import crear_gestor_eventos
from app.modules.scheduling.application.worker_cierre import cerrar_sesiones_vencidas
from tests.integration.test_main_early_ingress import ingreso_main,habilitar,pedir
from tests.integration.test_participation_http_composition import integracion,autor,pg_autoria,payload_valido,cantidades  # noqa: F401
from tests.integration.test_main_teacher_followup import observar_lectura
from tests.identity.academic_identity_support import motor_postgresql_desechable,config_alembic


def espera(h,**extra):
    return h.main.post(f'/scheduling/convocatorias/{h.convocatoria}/espera',headers=h.main_headers,
        json={'codigo_acceso':h.codigo,**extra})


def consulta(h):return h.main.get(f'/scheduling/convocatorias/{h.convocatoria}/admision',headers=h.main_headers)


def conteos(h):
    with h.sesiones() as s:
        c=s.get(C,h.convocatoria);ses=s.get(S,h.sesion)
        return (ses.estado,c.espera_registrada_en,c.espera_version_caso_id,c.admision_evento_id,
            s.scalar(select(func.count()).select_from(E).where(E.sesion_id==h.sesion)),
            s.scalar(select(func.count()).select_from(N).join(C,C.id==N.convocatoria_id)
                .where(C.sesion_id==h.sesion,N.tipo=='SESION_INICIADA')))


def test_espera_idempotente_admision_y_validacion_sin_escritura(ingreso_main,record_property):
    h=ingreso_main
    assert consulta(h).json()['solicitada'] is False
    a=espera(h);b=espera(h)
    assert (a.status_code,b.status_code)==(201,200) and a.json()==b.json()
    assert a.json()['solicitada'] and not a.json()['admitida']
    assert pedir(h).status_code==403 and cantidades(h)==([],[])
    habilitar(h);antes=conteos(h)
    with observar_lectura() as sql:
        c=consulta(h);v=pedir(h);otra=pedir(h)
    assert c.status_code==v.status_code==otra.status_code==200,(c.text,v.text)
    assert c.json()['admitida'] and v.json()['version_caso_id']==str(h.version)
    assert sql==[] and conteos(h)==antes and cantidades(h)==([],[])
    assert all(x not in v.text for x in (h.codigo,'nota_final','justificacion','es_correcta'))
    assert espera(h).status_code==200  # Recuperación de concesión previa, no nueva solicitud.
    # El mismo autorizador SQL se inyecta en la consulta existente de 8A;
    # contexto derivado del JWT real, sin abrir escrituras ni otra autorización.
    from fastapi.security import HTTPAuthorizationCredentials
    from app.modules.identity.api.dependencies import obtener_usuario_actual,obtener_fabrica_tokens
    from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
    from app.modules.participation.infrastructure.integration import ConsultaIngresoSQLAlchemy
    from app.modules.scheduling.infrastructure.admission import AdmisionSQLAlchemy
    from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada
    with h.sesiones() as sesion,observar_lectura() as sql:
        usuario=obtener_usuario_actual(HTTPAuthorizationCredentials(scheme='Bearer',
            credentials=h.main_headers['Authorization'].split(' ',1)[1]),
            obtener_fabrica_tokens(),lambda:RepositorioUsuariosSQLAlchemy(sesion))
        lectura=ConsultaIngresoSQLAlchemy(sesion,politica=PoliticaIngresoNoConfigurada(),
            reloj=SimpleNamespace(ahora=lambda:h.instante),admision=AdmisionSQLAlchemy(sesion,usuario))
        contexto=lectura.consultar(usuario=usuario,convocatoria_id=h.convocatoria,codigo_acceso=h.codigo)
        assert contexto.version_caso_id==h.version and contexto.sesion_id==h.sesion and sql==[]
    record_property('admision_confirmada',c.text)


@pytest.mark.parametrize('problema,esperado',[('anonimo',401),('ajeno',403),('retirada',403),
    ('matricula',403),('sin_matricula',403),('codigo',403),('version_cliente',422),('student_id',422),('finalizada',403)])
def test_espera_protegida(ingreso_main,problema,esperado):
    h=ingreso_main;headers=h.main_headers;body={'codigo_acceso':h.codigo}
    if problema=='anonimo':headers={}
    elif problema=='ajeno':headers=h.headers_ajeno
    elif problema=='codigo':body['codigo_acceso']='incorrecto'
    elif problema=='version_cliente':body['version_id']=str(uuid4())
    elif problema=='student_id':body['student_id']=str(uuid4())
    elif problema=='finalizada':
        habilitar(h)
        assert h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'finalizar'}).status_code==200
    else:
        with h.sesiones.begin() as s:
            if problema=='retirada':s.get(C,h.convocatoria).estado='RETIRADA'
            elif problema=='sin_matricula':s.delete(s.get(M,h.matricula))
            else:s.get(M,h.matricula).activo=False
    r=h.main.post(f'/scheduling/convocatorias/{h.convocatoria}/espera',headers=headers,json=body)
    assert r.status_code==esperado,r.text
    with h.sesiones() as s:assert s.get(C,h.convocatoria).espera_registrada_en is None
    assert h.codigo not in r.text and cantidades(h)==([],[])


def test_habilitar_sin_solicitud_no_admite_tardios(ingreso_main):
    h=ingreso_main;habilitar(h)
    assert espera(h).status_code==403 and pedir(h).status_code==403
    assert consulta(h).json()['admitida'] is False
    assert conteos(h)[1:4]==(None,None,None)


def test_docente_ajeno_no_habilita(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201
    clave='Clave docente ajeno SOLO LAB'
    with h.sesiones.begin() as s:
        u=U(id_rol=1,nombre='Docente ajeno LAB',correo=f'{uuid4().hex}@universidad.test',clave_hash=obtener_hasheador().hash(clave))
        s.add(u);s.flush();correo=u.correo
        s.add(IA(id_usuario=u.id_usuario,sistema='SCHEDULING',id_academico=uuid4()))
    login=h.main.post('/api/v1/identity/auth/personal',json={'correo':correo,'clave':clave});assert login.status_code==200
    r=h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers={'Authorization':'Bearer '+login.json()['access_token']},json={'accion':'iniciar'})
    assert r.status_code==403 and conteos(h)[0]=='SIN_INICIAR' and conteos(h)[3] is None


def test_repetir_habilitacion_no_duplica_auditoria_avisos_ni_admision(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201;habilitar(h);antes=conteos(h)
    r=h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'iniciar'})
    assert r.status_code==409 and conteos(h)==antes
    assert antes[4:]==(1,1)


def test_rollback_congelacion_no_habilita_parcialmente(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201;motor=h.sesiones.kw['bind']
    with motor.begin() as c:
        c.execute(text("CREATE FUNCTION public.fallo_adm_lab() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.admision_evento_id IS NOT NULL THEN RAISE EXCEPTION 'fallo privado LAB'; END IF; RETURN NEW; END $$"))
        c.execute(text('CREATE TRIGGER fallo_adm_lab BEFORE UPDATE ON convocatoria FOR EACH ROW EXECUTE FUNCTION public.fallo_adm_lab()'))
    try:
        r=h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'iniciar'})
        assert r.status_code==503 and 'privado' not in r.text
        estado=conteos(h);assert estado[0]=='SIN_INICIAR' and estado[3:] == (None,0,0)
    finally:
        with motor.begin() as c:
            c.execute(text('DROP TRIGGER fallo_adm_lab ON convocatoria'));c.execute(text('DROP FUNCTION public.fallo_adm_lab()'))
    habilitar(h);assert consulta(h).json()['admitida']


def test_rollback_espera_no_crea_fantasma(ingreso_main):
    h=ingreso_main;motor=h.sesiones.kw['bind']
    with motor.begin() as c:
        c.execute(text("CREATE FUNCTION public.fallo_espera_lab() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.espera_registrada_en IS NOT NULL THEN RAISE EXCEPTION 'fallo privado LAB'; END IF; RETURN NEW; END $$"))
        c.execute(text('CREATE TRIGGER fallo_espera_lab AFTER UPDATE ON convocatoria FOR EACH ROW EXECUTE FUNCTION public.fallo_espera_lab()'))
    try:assert espera(h).status_code==503
    finally:
        with motor.begin() as c:
            c.execute(text('DROP TRIGGER fallo_espera_lab ON convocatoria'));c.execute(text('DROP FUNCTION public.fallo_espera_lab()'))
    habilitar(h);assert consulta(h).json()['solicitada'] is False


def test_matricula_invalida_en_el_corte_no_se_admite_despues(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201
    with h.sesiones.begin() as s:s.get(M,h.matricula).activo=False
    habilitar(h)
    with h.sesiones.begin() as s:s.get(M,h.matricula).activo=True
    assert consulta(h).json()['admitida'] is False
    assert espera(h).status_code==pedir(h).status_code==403


@pytest.mark.parametrize('cambio',['retiro','final','worker'])
def test_concesion_historica_no_elude_condiciones_actuales(ingreso_main,cambio):
    h=ingreso_main;assert espera(h).status_code==201;habilitar(h);evento=conteos(h)[3]
    if cambio=='retiro':
        r=h.main.delete(f'/scheduling/sesiones/{h.sesion}/convocatorias/{h.convocatoria}',headers=h.docente_headers)
        assert r.status_code==200,r.text
    elif cambio=='final':
        assert h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'finalizar'}).status_code==200
    else:
        asyncio.run(cerrar_sesiones_vencidas(h.sesiones,crear_gestor_eventos(h.sesiones),ahora=h.inicio+timedelta(days=2)))
    assert pedir(h).status_code==403 and conteos(h)[3]==evento


def test_triggers_y_fk_protegen_espera_version_y_causa(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201;habilitar(h);antes=conteos(h)
    for operacion in ('espera','concesion','evento','version'):
        with pytest.raises(IntegrityError):
            with h.sesiones.begin() as s:
                if operacion=='espera':s.get(C,h.convocatoria).espera_registrada_en+=timedelta(seconds=1)
                elif operacion=='concesion':s.get(C,h.convocatoria).admision_evento_id=None
                elif operacion=='evento':s.get(E,antes[3]).origen='WORKER'
                else:s.get(S,h.sesion).version_caso_id=uuid4()
    assert conteos(h)==antes


def test_validacion_y_consulta_concurrentes_sin_dml(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201;habilitar(h);antes=conteos(h)
    with observar_lectura() as sql,ThreadPoolExecutor(max_workers=3) as pool:
        respuestas=list(pool.map(lambda _:pedir(h),range(3)))
    assert [r.status_code for r in respuestas]==[200]*3
    assert sql==[] and conteos(h)==antes and cantidades(h)==([],[])


def test_carrera_espera_confirma_antes_habilitacion(ingreso_main):
    h=ingreso_main;tomado=Event();liberar=Event();motor=get_engine()
    def pausa(conn,cursor,statement,params,context,many):
        if 'FROM sesion_programada' in statement and 'FOR UPDATE NOWAIT' in statement and not tomado.is_set():
            tomado.set();assert liberar.wait(10)
    event.listen(motor,'after_cursor_execute',pausa)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(espera,h);assert tomado.wait(10)
            b=pool.submit(h.main.post,f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'iniciar'})
            liberar.set();assert a.result(timeout=15).status_code==201
            assert b.result(timeout=15).status_code==200
    finally:liberar.set();event.remove(motor,'after_cursor_execute',pausa)
    assert consulta(h).json()['admitida'] is True


def test_carrera_habilitacion_gana_no_admite_nueva_solicitud(ingreso_main):
    h=ingreso_main;tomado=Event();liberar=Event();motor=get_engine()
    def pausa(conn,cursor,statement,params,context,many):
        if statement.startswith('UPDATE sesion_programada SET estado=') and not tomado.is_set():
            tomado.set();assert liberar.wait(10)
    event.listen(motor,'after_cursor_execute',pausa)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(h.main.post,f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'iniciar'})
            assert tomado.wait(10)
            # Otro portal HTTP: el endpoint docente async usa DB síncrona.
            # No bloquear ambas solicitudes en el mismo event loop de TestClient.
            otro=TestClient(h.main.app,raise_server_exceptions=False)
            r=otro.post(f'/scheduling/convocatorias/{h.convocatoria}/espera',
                headers=h.main_headers,json={'codigo_acceso':h.codigo})
            assert r.status_code==409,r.text
            liberar.set();assert a.result(timeout=15).status_code==200
    finally:liberar.set();event.remove(motor,'after_cursor_execute',pausa)
    assert espera(h).status_code==403 and not consulta(h).json()['admitida']


def test_migracion_upgrade_downgrade_vacia_pg17():
    with motor_postgresql_desechable() as motor:
        with motor.begin() as c:
            cfg=config_alembic(c);command.upgrade(cfg,'20261105_waiting_admission')
            assert c.scalar(text('SELECT version_num FROM alembic_version'))=='20261105_waiting_admission'
            command.downgrade(cfg,'20261104_teacher_spaces')
            command.upgrade(cfg,'20261105_waiting_admission')
            assert c.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='convocatoria' AND column_name IN ('espera_registrada_en','espera_version_caso_id','admision_evento_id')"))==3


def test_downgrade_no_elimina_solicitudes(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201
    with pytest.raises(RuntimeError,match='No eliminar evidencia'):
        with h.sesiones.kw['bind'].begin() as c:command.downgrade(config_alembic(c),'20261104_teacher_spaces')
    assert consulta(h).json()['solicitada']


def test_conjunto_varias_solicitudes_previas_con_jwt_real(ingreso_main):
    h=ingreso_main
    # Preparación administrativa explícita: cuenta, vínculo y matrícula del LAB.
    with h.sesiones.begin() as s:
        correo=f'{uuid4()}@universidad.test';academic=uuid4()
        u=U(id_rol=s.get(U,h.estudiante).id_rol,nombre='Estudiante laboratorio',correo=correo,clave_hash='sin-login-personal')
        s.add(u);s.flush()
        s.add_all([IA(id_usuario=u.id_usuario,sistema='SCHEDULING',id_academico=academic),
            M(id_grupo=s.get(M,h.matricula).id_grupo,id_estudiante=u.id_usuario,
                fecha_ingreso=h.inicio.replace(tzinfo=None)-timedelta(days=1))])
    c=h.main.post(f'/scheduling/sesiones/{h.sesion}/convocatorias',headers=h.docente_headers,
        json={'estudiante_id':str(academic)})
    assert c.status_code==201,c.text
    login=h.main.post('/api/v1/identity/auth/estudiantes',json={'correo':correo,'codigo_convocatoria':c.json()['codigo_acceso']})
    assert login.status_code==200
    otro=SimpleNamespace(**(vars(h)|dict(convocatoria=UUID(c.json()['convocatoria_id']),
        codigo=c.json()['codigo_acceso'],uuid_estudiante=academic,
        main_headers={'Authorization':'Bearer '+login.json()['access_token']})))
    assert espera(h).status_code==espera(otro).status_code==201
    habilitar(h)
    assert consulta(h).json()['admitida'] and consulta(otro).json()['admitida']
    assert pedir(h).status_code==pedir(otro).status_code==200
    assert conteos(h)[3]==conteos(otro)[3]  # Misma causa docente persistida.
    assert conteos(h)[4:]==(1,2) and cantidades(h)==cantidades(otro)==([],[])


def test_dos_solicitudes_de_espera_convergen_sin_duplicacion(ingreso_main):
    h=ingreso_main;barrera=Barrier(2)
    def solicitar(_):
        cliente=TestClient(h.main.app,raise_server_exceptions=False)
        barrera.wait(timeout=10)
        return cliente.post(f'/scheduling/convocatorias/{h.convocatoria}/espera',
            headers=h.main_headers,json={'codigo_acceso':h.codigo})
    with ThreadPoolExecutor(max_workers=2) as pool:respuestas=list(pool.map(solicitar,range(2)))
    estados=[r.status_code for r in respuestas]
    assert estados.count(201)==1 and all(x in (200,201,409) for x in estados),estados
    antes=conteos(h)
    assert espera(h).status_code==200 and conteos(h)==antes
    habilitar(h);assert consulta(h).json()['admitida'] and conteos(h)[4:]==(1,1)


def test_conflicto_convocatoria_no_confirma_habilitacion_parcial(ingreso_main):
    h=ingreso_main;assert espera(h).status_code==201
    with h.sesiones() as otra:
        otra.get(C,h.convocatoria,with_for_update=True)
        r=h.main.post(f'/scheduling/sesiones/{h.sesion}/estado',headers=h.docente_headers,json={'accion':'iniciar'})
        assert r.status_code==409,r.text
        assert conteos(h)[0]=='SIN_INICIAR' and conteos(h)[3:]==(None,0,0)
        otra.rollback()
    habilitar(h);assert consulta(h).json()['admitida']


@pytest.mark.parametrize('segundos,esperado',[(-1,403),(0,200),(3599,200),(3600,403)])
def test_admision_no_amplia_limites_exteriores_programados(ingreso_main,segundos,esperado):
    h=ingreso_main;assert espera(h).status_code==201;habilitar(h)
    h.instante=h.inicio+timedelta(seconds=segundos)
    with observar_lectura() as sql:r=pedir(h)
    assert r.status_code==esperado,r.text
    assert sql==[] and cantidades(h)==([],[])
