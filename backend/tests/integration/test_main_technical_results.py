"""main/JWT/PG17 reales. Fixtures administrativas sintéticas, sin overrides de auth."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from app.db.session import get_engine
from app.core.config import get_settings
from app.modules.identity.infrastructure.models import UsuarioORM as U, RolORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM as G
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from tests.integration.test_question_result_storage import crear_registro, pg_resultados, cerrar, guardar, contar  # noqa: F401
from tests.integration.test_main_evaluation_readiness import docente_http, revision, lectura  # noqa: F401
from tests.integration.test_evaluation_result_storage import evaluar, c as legacy_c


@pytest.fixture
def c(crear_registro, pg_resultados, request):
    modo=getattr(request,'param','parcial')
    if modo=='legacy':return legacy_c.__wrapped__(pg_resultados)
    ctx=crear_registro(criterios=2)
    if modo!='activo':cerrar(ctx,vencido=modo!='completo',respondidas=3 if modo=='completo' else 1)
    return ctx


def ruta(h, intento=None):
    return f'/scheduling/sesiones/{h.c.sesion}/evaluacion/intentos/{intento or h.c.ik}/resultado-tecnico'


@pytest.mark.parametrize('c',['completo','parcial'],indirect=True)
def test_main_resultado_existente_historico_decimal_y_solo_lectura(docente_http):
    h=docente_http;persistido=guardar(h.c)
    with lectura(h) as config:
        r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==200,r.text
    j=r.json();assert config and r.headers['cache-control']=='no-store'
    assert j['oficial'] is False and j['ambito']=='TECNICO'
    assert j['version_caso_id']==str(h.c.version.id) and j['rubrica_id']==str(h.c.version.rubrica.id)
    assert j['id_resultado']==persistido.id_resultado and j['id_intento']==h.c.ik
    assert j['nota_final']==str(persistido.datos.nota_final) and isinstance(j['nota_final'],str)
    if j['modalidad']=='PARCIAL':
        assert j['nota_final']=='33.33' and j['pendientes_con_cero']==2
        assert [(x['numerador'],x['denominador']) for x in j['criterios']]==[('50','3'),('50','3')]
    else:assert j['nota_final']=='100.00' and j['pendientes_con_cero']==0
    assert not any(x in r.text for x in ('politica_documento','procedencia"','clave','correo','codigo_hash','es_correcta','explicacion','@','def calcular'))
    assert len(j['preguntas'])==j['preguntas_respondidas']
    assert contar(h.c)==1


def test_ausente_404_no_calcula_ni_crea_resultado(docente_http):
    h=docente_http
    with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==404 and contar(h.c)==0
    assert 'nota_final' not in r.text


@pytest.mark.parametrize('c',['legacy'],indirect=True)
def test_compatibilidad_motor_anterior_no_se_convierte_en_oficial(docente_http):
    h=docente_http;anterior=evaluar(h.c)
    with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==200,r.text
    j=r.json();assert j['ambito']=='LABORATORIO' and j['oficial'] is False
    assert j['id_resultado']==anterior.id_resultado and j['preguntas']==[]
    assert j['criterios'] and all('nivel_id' in c and 'numerador' not in c for c in j['criterios'])


@pytest.mark.parametrize('problema,estado',[('anonimo',401),('invalido',401),('ajeno',403),('estudiante',403),
    ('admin',403),('inactivo',401),('sin_vinculo',403),('ambiguo',503),('rol_revocado',403)])
def test_jwt_y_autorizacion_persistentes_sin_filtraciones(docente_http,problema,estado):
    h=docente_http;guardar(h.c)
    auth=h.auth.get(problema,h.auth['docente'])
    if problema=='anonimo':auth={}
    elif problema=='invalido':auth={'Authorization':'Bearer invalido-LAB'}
    elif problema in ('inactivo','sin_vinculo','ambiguo','rol_revocado'):
        with h.c.sesiones.begin() as s:
            if problema=='inactivo':s.get(U,h.c.docente).activo=False
            elif problema=='sin_vinculo':s.execute(sa.delete(IA).where(IA.id_usuario==h.c.docente))
            elif problema=='ambiguo':s.add(IA(id_usuario=h.c.docente,sistema='SCHEDULING',id_academico=uuid4()))
            else:s.get(U,h.c.docente).id_rol=3
    with lectura(h):r=h.client.get(ruta(h),headers=auth|{'X-Docente-Id':str(h.c.docente)})
    assert r.status_code==estado and 'nota_final' not in r.text


@pytest.mark.parametrize('problema',['grupo_ajeno','creador_ajeno','intento_ajeno'])
def test_ambito_sesion_caso_grupo_e_intento(docente_http,problema,crear_registro):
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as s:
        if problema=='grupo_ajeno':s.get(G,s.get(A,h.c.datos['id_asignacion']).id_grupo).id_profesor=h.c.alumno
        elif problema=='creador_ajeno':s.scalar(sa.select(IA).where(IA.id_usuario==h.c.docente,IA.sistema=='CASES')).id_academico=uuid4()
    objetivo=None
    if problema=='intento_ajeno':
        otro=crear_registro();cerrar(otro);guardar(otro);objetivo=otro.ik
    with lectura(h):r=h.client.get(ruta(h,objetivo),headers=h.auth['docente'])
    assert r.status_code==(503 if problema=='grupo_ajeno' else 403) and 'nota_final' not in r.text


def test_retirada_conserva_antecedente_sin_publicacion(docente_http):
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as s:s.get(C,h.c.datos['convocatoria_id']).estado='RETIRADA'
    with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==200 and r.json()['oficial'] is False


def test_lecturas_concurrentes_idempotentes(docente_http):
    h=docente_http;guardar(h.c)
    with lectura(h) as config,ThreadPoolExecutor(max_workers=2) as pool:
        rs=list(pool.map(lambda _:h.client.get(ruta(h),headers=h.auth['docente']),range(2)))
    assert len(config)==2 and all(r.status_code==200 for r in rs)
    assert rs[0].json()==rs[1].json() and contar(h.c)==1


@pytest.mark.parametrize('zona',[None,'Zona/NoExiste'])
def test_zona_historica_obligatoria(docente_http,monkeypatch,zona):
    h=docente_http
    if zona is None:monkeypatch.delenv('PARTICIPATION_TIMESTAMP_ZONE')
    else:monkeypatch.setenv('PARTICIPATION_TIMESTAMP_ZONE',zona)
    get_settings.cache_clear()
    with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==503


def test_error_sql_lectura_no_expone_fuentes_y_recupera(docente_http):
    h=docente_http;guardar(h.c);e=get_engine()
    def fallar(conn,cursor,sql,*args):
        if sql.startswith('SELECT resultado_intento.'):
            raise OperationalError('SQL_INTERNO_LAB',{},RuntimeError('MARCADOR_PRIVADO'))
    sa.event.listen(e,'before_cursor_execute',fallar)
    try:
        with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    finally:sa.event.remove(e,'before_cursor_execute',fallar)
    assert r.status_code==503 and 'MARCADOR_PRIVADO' not in r.text
    assert h.client.get(ruta(h),headers=h.auth['docente']).status_code==200


def test_parametros_invalidos_y_sesion_inexistente(docente_http):
    h=docente_http
    with lectura(h):
        for url,status in [(ruta(h)+'?docente_id=otro',422),(ruta(h).replace(str(h.c.ik)+'/resultado','0/resultado'),422),
            (ruta(h).replace(str(h.c.sesion),str(uuid4())),403)]:
            assert h.client.get(url,headers=h.auth['docente']).status_code==status


@pytest.mark.parametrize('c',['activo'],indirect=True)
def test_get_no_cierra_ni_calcula_intento_activo(docente_http):
    h=docente_http
    with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==404 and contar(h.c)==0
    with h.c.sesiones() as s:assert s.get(I,h.c.ik).estado=='EN_CURSO'


def test_version_posterior_no_sustituye_referencia_historica(docente_http):
    from app.modules.cases.infrastructure.models import VersionCasoModel as V
    from app.modules.cases.domain.enums import EstadoCaso
    h=docente_http;guardar(h.c)
    with h.c.sesiones.begin() as s:
        anterior=s.get(V,h.c.version.id)
        posterior=V(id=uuid4(),caso_id=anterior.caso_id,numero=anterior.numero+1,nombre='Edición posterior LAB',
            desarrollo_situacional='Borrador posterior',contexto_historia='LAB',tiempo_estimado_min=20,estado=EstadoCaso.BORRADOR)
        s.add(posterior)
    with lectura(h):r=h.client.get(ruta(h),headers=h.auth['docente'])
    assert r.status_code==200 and r.json()['version_caso_id']==str(h.c.version.id)
    assert r.json()['nota_final']=='33.33'
