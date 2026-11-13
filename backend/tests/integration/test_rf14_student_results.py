"""RF14: lectura main con login/JWT/PG17 reales; preparación académica SOLO LAB."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import secrets

import pytest
import sqlalchemy as sa

from app.db.session import get_engine
from app.modules.cases.infrastructure.models import VersionCasoModel
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.identity.infrastructure.models import UsuarioORM as U
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.participation.infrastructure.models import IntentoModel as I, ParticipacionModel as P, PasoSimulacionModel as Paso
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C
from app.modules.scheduling.domain.access_codes import hash_codigo
from tests.integration.test_question_result_storage import crear_registro, pg_resultados, cerrar, guardar  # noqa: F401
from tests.integration.test_main_evaluation_readiness import docente_http, revision, lectura  # noqa: F401
from tests.integration.test_evaluation_readiness import otro_convocado, cerrar_sesion_fixture


@pytest.fixture
def c(crear_registro, request):
    ctx = crear_registro(criterios=2)
    modo = getattr(request, 'param', 'completo')
    if modo != 'activo':
        cerrar(ctx, vencido=modo == 'vencido', respondidas=1 if modo in ('vencido', 'voluntario') else 3,
               rama=1 if modo == 'incorrecto' else 0, cero=modo == 'incorrecto')
    return ctx


def ruta(h): return f"/scheduling/convocatorias/{h.c.datos['convocatoria_id']}/resultado"


def habilitar(h):
    # Estado académico preparado en LAB; la visibilidad sí se configura por HTTP.
    with h.c.sesiones.begin() as s:
        s.get(S, h.c.sesion).estado = 'EN_CURSO'
    r = h.client.put(f'/scheduling/sesiones/{h.c.sesion}/evaluacion/visibilidad',
                    headers=h.auth['docente'], json={'mostrar_provisional': True})
    assert r.status_code == 200, r.text


def huella_resultado(h):
    with h.c.sesiones() as s:
        return s.execute(sa.select(R.id_resultado, R.nota_final, R.fecha_calculo, R.procedencia_sha256)
                         .where(R.id_intento == h.c.ik)).one_or_none()


@pytest.mark.parametrize('c,nota,correcta', [('completo', '100.00', True), ('incorrecto', '0.00', False)], indirect=['c'])
def test_feedback_historico_exacto_y_recargas_concurrentes_sin_escritura(docente_http, nota, correcta):
    h = docente_http
    guardar(h.c)
    habilitar(h)
    cerrar_sesion_fixture(h.c)
    with h.c.sesiones.begin() as s:
        old = s.get(VersionCasoModel, h.c.version.id)
        s.add(VersionCasoModel(id=uuid4(), caso_id=old.caso_id, numero=old.numero+1,
            nombre='Edición posterior LAB', desarrollo_situacional='Otro borrador', contexto_historia='LAB',
            tiempo_estimado_min=20, estado=EstadoCaso.BORRADOR))
    with h.c.sesiones() as s:
        seleccionadas = s.execute(sa.select(Paso.id_decision, Paso.id_opcion).where(Paso.id_intento == h.c.ik)
                                 .order_by(Paso.numero_paso)).all()
    antes = huella_resultado(h)
    with lectura(h) as config:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: h.client.get(ruta(h), headers=h.auth['estudiante']), range(3)))
    assert config and all(r.status_code == 200 for r in responses)
    data = responses[0].json()
    assert all(r.json() == data for r in responses)
    assert data['nota'] == nota and data['oficial'] is False
    assert data['detalle']['version_caso_id'] == str(h.c.version.id)
    assert [b['id_intento'] for b in data['explicaciones']] == [h.c.ik]
    actual = data['explicaciones'][0]['respuestas']
    assert [(x['pregunta_id'], x['opcion_id']) for x in actual] == [(str(q), str(o)) for q, o in seleccionadas]
    qs = {q.id: q for e in h.c.version.escenarios for q in e.preguntas}
    for item, (qid, oid) in zip(actual, seleccionadas):
        question = qs[qid]; option = next(o for o in question.opciones if o.id == oid)
        assert item == dict(pregunta_id=str(qid), opcion_id=str(oid), enunciado=question.enunciado,
                            texto_seleccionado=option.texto, es_correcta=correcta, justificacion=option.justificacion)
    assert huella_resultado(h) == antes
    assert not any(k in responses[0].text for k in ('clave_hash', 'codigo_hash', 'politica_documento', 'motor_documento'))


@pytest.mark.parametrize('c', ['vencido', 'voluntario'], indirect=True)
def test_parcial_muestra_solo_feedback_registrado_sin_preguntas_ficticias(docente_http):
    h = docente_http
    guardar(h.c); habilitar(h); cerrar_sesion_fixture(h.c)
    with lectura(h): r = h.client.get(ruta(h), headers=h.auth['estudiante'])
    assert r.status_code == 200, r.text
    assert r.json()['nota'] == '33.33' and r.json()['situacion'] == 'PARCIAL'
    assert len(r.json()['explicaciones'][0]['respuestas']) == 1
    with h.c.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(Paso).where(Paso.id_intento == h.c.ik)) == 1


def login_otro(h, cid):
    code = secrets.token_urlsafe(32)
    with h.c.sesiones.begin() as s:
        conv = s.get(C, cid); conv.codigo_hash = hash_codigo(code)
        uid = s.scalar(sa.select(IA.id_usuario).where(IA.sistema == 'SCHEDULING', IA.id_academico == conv.estudiante_id))
        correo = s.get(U, uid).correo
    r = h.client.post('/api/v1/identity/auth/estudiantes', json={'correo': correo, 'codigo_convocatoria': code})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}


@pytest.mark.parametrize('actor,http', [('anonimo',401), ('invalido',401), ('docente',403), ('admin',403),
    ('otro_estudiante',403), ('inactivo',401)])
def test_consulta_estudiantil_privada_sin_filtrar_nota(docente_http, actor, http):
    h = docente_http
    auth = h.auth['estudiante']
    if actor == 'otro_estudiante': auth = login_otro(h, otro_convocado(h.c))
    elif actor in ('docente', 'admin'): auth = h.auth[actor]
    elif actor == 'anonimo': auth = {}
    elif actor == 'invalido': auth = {'Authorization': 'Bearer invalido-LAB'}
    elif actor == 'inactivo':
        with h.c.sesiones.begin() as s: s.get(U, h.c.alumno).activo = False
    # No se necesita una nota para rechazar por identidad/rol; evita usar el
    # preparador como sustituto de autorización o de una política académica.
    with lectura(h): r = h.client.get(ruta(h), headers=auth)
    assert r.status_code == http, r.text
    assert not any(k in r.json() for k in ('nota', 'detalle', 'explicaciones', 'resultados'))


def test_guard_impide_ambiguedad_de_identidad_historica_sin_debilitar_lectura(docente_http):
    h = docente_http
    with pytest.raises(sa.exc.IntegrityError) as error:
        with h.c.sesiones.begin() as s:
            s.add(IA(sistema='SCHEDULING', id_academico=uuid4(), id_usuario=h.c.alumno))
    assert error.value.orig.sqlstate == '23514'
    guardar(h.c); habilitar(h)
    with lectura(h): r = h.client.get(ruta(h), headers=h.auth['estudiante'])
    assert r.status_code == 200 and r.json()['detalle']['id_participacion'] == h.c.pk


def test_cerrado_sin_calculo_pendiente_404_sin_generar_resultado(docente_http):
    h = docente_http
    habilitar(h)
    with lectura(h): r = h.client.get(ruta(h), headers=h.auth['estudiante'])
    assert r.status_code == 404 and huella_resultado(h) is None
    assert 'nota' not in r.json()


def test_ausencia_no_consultable_hasta_publicacion_explicita_sin_intentos_ficticios(docente_http):
    h = docente_http
    cid = otro_convocado(h.c); auth = login_otro(h, cid)
    guardar(h.c); cerrar_sesion_fixture(h.c)
    with h.c.sesiones() as s:
        antes = [s.scalar(sa.select(sa.func.count()).select_from(m)) for m in (P, I)]
    base = f'/scheduling/sesiones/{h.c.sesion}/evaluacion'
    assert h.client.post(base+f'/convocatorias/{cid}/ausencia', headers=h.auth['docente'],
                         json={'motivo':'Confirmación individual explícita LAB'}).status_code == 200
    path = f'/scheduling/convocatorias/{cid}/resultado'
    assert h.client.get(path, headers=auth).status_code == 404
    revision = h.client.get(base+'/consolidacion', headers=h.auth['docente'])
    assert revision.status_code == 200 and revision.json()['publicable']
    pub = h.client.post(base+'/publicaciones', headers=h.auth['docente'],
                        json={'revision_sha256':revision.json()['revision_sha256']})
    assert pub.status_code == 200, pub.text
    with lectura(h): r = h.client.get(path, headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()['oficial'] is True and r.json()['situacion'] == 'AUSENTE' and r.json()['nota'] == '0.00'
    assert r.json()['explicaciones'] == [] and r.json()['detalle']['id_participacion'] is None
    assert r.json()['detalle']['intentos'] == []
    with h.c.sesiones() as s:
        assert [s.scalar(sa.select(sa.func.count()).select_from(m)) for m in (P, I)] == antes
