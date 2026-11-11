"""Recorrido main con CoreSettings real y atestación sintética exclusiva de LAB.

Grupos, matrículas y evidencia documental son preparación administrativa LAB.
Caso, publicación, programación, convocatorias, aceptación e inicio usan main.
No se sustituyen proveedores ni autenticación mediante dependency_overrides.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa

from app.core.config import get_settings
from app.db.session import get_engine
from app.modules.identity.infrastructure.models import UsuarioORM as U
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM as IA
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.scheduling.infrastructure.models import EventoAuditoriaModel as E, NotificacionModel as N
from tests.integration.test_academic_assignment_programming import (
    asignable, personal, lab, inicializar,
)  # noqa: F401
from tests.integration.cases.conftest import payload_valido as payload_original
from tests.integration.test_consent_version_persistence import publicar, elegir
from tests.unit.identity.test_consent_approval_attestation import escribir_paquete
from tests.unit.participation.test_start_policy_file import archivo_politica, decision_lab


@pytest.fixture
def payload_valido():
    datos = payload_original.__wrapped__()
    datos['rubric']['versionRegla'] = 'PREGUNTAS_100_V1'
    for opcion in datos['scenarios'][0]['questions'][0]['options']:
        opcion['valoraciones'] = {'Análisis': 100 if opcion['esCorrecta'] else 0}
    return datos


@pytest.fixture
def configurado(asignable, tmp_path, monkeypatch):
    from app.main import app
    a = asignable
    assert app.dependency_overrides == {}
    ahora = datetime.now(timezone.utc)
    extra_uuid = uuid4()
    with a.h.sesiones.begin() as sesion:
        extra = U(id_rol=2, nombre='Estudiante adicional LAB', correo=f'{uuid4().hex}@universidad.test',
                  clave_hash='sin-login-personal-LAB', activo=True)
        sesion.add(extra)
        sesion.flush()
        sesion.add_all([IA(id_usuario=extra.id_usuario, sistema='SCHEDULING', id_academico=extra_uuid),
            M(id_grupo=a.grupo, id_estudiante=extra.id_usuario, fecha_ingreso=datetime(2026, 1, 1), activo=True)])
    solicitud = a.datos | dict(fecha_inicio=(ahora-timedelta(minutes=1)).isoformat(),
        fecha_fin=(ahora+timedelta(minutes=40)).isoformat(),
        fecha_limite_ingreso=(ahora+timedelta(minutes=20)).isoformat(),
        estudiantes_ids=[str(a.estudiante), str(extra_uuid)])
    respuesta = a.h.cliente.post('/scheduling/sesiones', headers=a.auth, json=solicitud)
    assert respuesta.status_code == 201, respuesta.text
    programada = respuesta.json()
    convocatoria = next(c for c in programada['convocatorias'] if c['estudiante_id'] == str(a.estudiante))
    ausente = next(c for c in programada['convocatorias'] if c['estudiante_id'] == str(extra_uuid))
    contexto = SimpleNamespace(datos={'id_asignacion': programada['id_asignacion']}, ahora=ahora,
                              docente=a.h.docente[0])
    with a.h.sesiones.begin() as sesion:
        documento_id = publicar(contexto, sesion)
        elegir(contexto, sesion, documento_id)
        documento = FuenteConsentimientoSQLAlchemy(sesion).vigente(
            id_asignacion=programada['id_asignacion'], ahora=ahora)
    atestacion = escribir_paquete(tmp_path, [documento], programada['id_asignacion'], ahora)
    politica, huella = archivo_politica(tmp_path, decision_lab(documento.referencia))
    for nombre, valor in vars(atestacion).items():
        monkeypatch.setenv(nombre.upper(), str(valor))
    monkeypatch.setenv('PARTICIPATION_START_POLICY_FILE', str(politica))
    monkeypatch.setenv('PARTICIPATION_START_POLICY_SHA256', huella)
    get_settings.cache_clear()
    settings = get_settings()
    assert type(settings).__name__ == 'Settings' and settings.academic_runtime_scope == 'LABORATORIO'
    login = a.h.cliente.post('/api/v1/identity/auth/estudiantes', json={
        'correo': a.h.estudiante[1], 'codigo_convocatoria': convocatoria['codigo_acceso']})
    assert login.status_code == 200, login.text
    estudiante = {'Authorization': 'Bearer '+login.json()['access_token']}
    base = f'/api/v1/identity/convocatorias/{convocatoria["convocatoria_id"]}/asignaciones/{programada["id_asignacion"]}/consentimiento'
    yield SimpleNamespace(a=a, cliente=a.h.cliente, sesiones=a.h.sesiones, docente=a.auth,
        estudiante=estudiante, codigo=convocatoria['codigo_acceso'], cid=convocatoria['convocatoria_id'],
        sid=programada['id'], aid=programada['id_asignacion'], ausente=ausente['convocatoria_id'],
        consentimiento=base, politica_sha=huella)
    assert app.dependency_overrides == {}


def aceptar(h):
    documento = h.cliente.get(h.consentimiento, headers=h.estudiante)
    assert documento.status_code == 200, documento.text
    datos = {k: documento.json()[k] for k in ('id_version_documento', 'referencia', 'huella')}
    respuesta = h.cliente.post(h.consentimiento+'/aceptacion', headers=h.estudiante, json=datos | {'acepta': True})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()['id_consentimiento']


def admitir(h):
    espera = h.cliente.post(f'/scheduling/convocatorias/{h.cid}/espera', headers=h.estudiante,
                           json={'codigo_acceso': h.codigo})
    assert espera.status_code == 201, espera.text
    habilitar = h.cliente.post(f'/scheduling/sesiones/{h.sid}/estado', headers=h.docente, json={'accion': 'iniciar'})
    assert habilitar.status_code == 200, habilitar.text
    assert h.cliente.get(f'/scheduling/convocatorias/{h.cid}/admision', headers=h.estudiante).json()['admitida'] is True


def iniciar(h, consentimiento, permiso=None):
    return h.cliente.post(f'/api/v1/convocatorias/{h.cid}/intentos', headers=h.estudiante,
        json=dict(id_asignacion=h.aid, codigo_acceso=h.codigo,
                  id_consentimiento=consentimiento, id_permiso_extra=permiso))


def contar(h, modelo):
    with h.sesiones() as sesion:
        return sesion.scalar(sa.select(sa.func.count()).select_from(modelo))


def test_main_configurado_recorrido_inmutable_evaluacion_repeticion_y_ausencia(configurado):
    h = configurado
    consentimiento = aceptar(h)
    assert contar(h, P) == contar(h, I) == 0
    admitir(h)
    primero = iniciar(h, consentimiento)
    assert primero.status_code == 201, primero.text
    intento = primero.json()['id_intento']
    assert datetime.fromisoformat(primero.json()['vence_en']) - datetime.fromisoformat(primero.json()['inicio']) == timedelta(minutes=30)
    base = f'/api/v1/attempts/{intento}'
    actual = h.cliente.get(base+'/current-scenario', headers=h.estudiante)
    assert actual.status_code == 200
    assert not any(campo in actual.text for campo in ('es_correcta', 'justificacion', 'nota_final'))
    pregunta = actual.json()['pregunta']
    decision = base+'/decisions/'+pregunta['id']
    assert h.cliente.post(decision, headers=h.estudiante, json={'id_opcion': pregunta['opciones'][0]['id']}).status_code == 201
    assert h.cliente.post(decision, headers=h.estudiante, json={'id_opcion': pregunta['opciones'][1]['id']}).status_code == 409
    assert h.cliente.get(base+'/progress', headers=h.estudiante).json()['respondidas'] == 1
    assert h.cliente.get(base+'/current-scenario', headers=h.estudiante).json()['recorrido_finalizado'] is True
    fin = h.cliente.post(base+'/finish', headers=h.estudiante)
    assert fin.status_code == 200 and fin.json()['estado'] == 'FINALIZADO'
    assert contar(h, R) == 0
    evaluacion = f'/scheduling/sesiones/{h.sid}/evaluacion/intentos/{intento}/resultado-tecnico'
    resultado = h.cliente.post(evaluacion, headers=h.docente)
    assert resultado.status_code == 200, resultado.text
    assert resultado.json()['nota_final'] == '100.00' and resultado.json()['oficial'] is False
    assert h.cliente.get(evaluacion, headers=h.docente).json() == resultado.json()
    permiso = h.cliente.post('/api/v1/identity/excepciones/repeticiones', headers=h.docente,
        json={'id_sesion': h.sid, 'id_estudiante': str(h.a.h.estudiante[0])})
    assert permiso.status_code == 201, permiso.text
    permiso_id = int(permiso.json()['id_permiso_extra'])
    segundo = iniciar(h, consentimiento, permiso_id)
    assert segundo.status_code == 201, segundo.text
    assert segundo.json()['numero_intento'] == 2
    segundo_id = segundo.json()['id_intento']
    assert h.cliente.post(f'/api/v1/attempts/{segundo_id}/finish', headers=h.estudiante).status_code == 200
    assert iniciar(h, consentimiento, permiso_id).status_code in (403, 409)
    cierre = h.cliente.post(f'/scheduling/sesiones/{h.sid}/estado', headers=h.docente, json={'accion': 'finalizar'})
    assert cierre.status_code == 200
    ausencia = h.cliente.post(f'/scheduling/sesiones/{h.sid}/evaluacion/convocatorias/{h.ausente}/ausencia',
        headers=h.docente, json={'motivo': 'Confirmación expresa sintética LAB'})
    assert ausencia.status_code == 200 and ausencia.json()['nota'] == '0.00', ausencia.text
    assert contar(h, P) == 1 and contar(h, I) == 2
    with h.sesiones() as sesion:
        assert sesion.scalars(sa.select(P.estado)).one() == 'pendiente'
        assert sesion.scalar(sa.select(sa.func.count()).select_from(N).where(N.publicacion_evaluacion_id.is_not(None))) == 0


def test_inicio_real_concurrente_conserva_un_evento_y_un_intento(configurado):
    h = configurado
    consentimiento = aceptar(h)
    admitir(h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        respuestas = list(pool.map(lambda _: iniciar(h, consentimiento), range(2)))
    assert sorted(r.status_code for r in respuestas) == [201, 409], [r.text for r in respuestas]
    assert contar(h, P) == contar(h, I) == 1
    with h.sesiones() as sesion:
        eventos = sesion.scalars(sa.select(E).where(E.tipo == 'INICIO_INTENTO_POLITICA')).all()
        assert len(eventos) == 1 and h.codigo not in eventos[0].descripcion
        assert h.politica_sha in eventos[0].descripcion


def test_vencimiento_configurado_separa_lectura_cierre_y_calculo(configurado, monkeypatch):
    from app.modules.participation.domain.clock import RelojSistema
    from app.modules.participation.infrastructure.models import PasoSimulacionModel
    h = configurado
    consentimiento = aceptar(h)
    admitir(h)
    respuesta = iniciar(h, consentimiento)
    assert respuesta.status_code == 201
    intento = respuesta.json()['id_intento']
    base = f'/api/v1/attempts/{intento}'
    vencimiento = datetime.fromisoformat(respuesta.json()['vence_en'])
    # Avance explícito del reloj solo en esta prueba de frontera temporal.
    monkeypatch.setattr(RelojSistema, 'ahora', lambda self: vencimiento)
    progreso = h.cliente.get(base+'/progress', headers=h.estudiante)
    assert progreso.status_code == 200 and progreso.json()['intento']['estado'] == 'VENCIDO'
    with h.sesiones() as sesion:
        assert sesion.get(I, intento).estado == 'EN_CURSO'
    fin = h.cliente.post(base+'/finish', headers=h.estudiante)
    assert fin.status_code == 200 and fin.json()['estado'] == 'VENCIDO'
    assert contar(h, R) == contar(h, PasoSimulacionModel) == 0
    url = f'/scheduling/sesiones/{h.sid}/evaluacion/intentos/{intento}/resultado-tecnico'
    resultado = h.cliente.post(url, headers=h.docente)
    assert resultado.status_code == 200, resultado.text
    assert resultado.json()['nota_final'] == '0.00' and resultado.json()['oficial'] is False
    assert h.cliente.post(url, headers=h.docente).json() == resultado.json()
    assert contar(h, R) == 1 and contar(h, PasoSimulacionModel) == 0


def test_error_auditoria_revierte_inicio_con_proveedores_reales(configurado):
    h = configurado
    consentimiento = aceptar(h)
    admitir(h)
    motor = get_engine()
    def fallar(conn, cursor, statement, *args):
        if statement.startswith('INSERT INTO evento_auditoria'):
            conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(motor, 'after_cursor_execute', fallar)
    try:
        # El límite ASGI devuelve 500 para fallos SQL inesperados. La UoW
        # debe revertirlos y nunca presentarlos como una política ausente.
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as cliente:
            respuesta = cliente.post(f'/api/v1/convocatorias/{h.cid}/intentos', headers=h.estudiante,
                json=dict(id_asignacion=h.aid, codigo_acceso=h.codigo,
                          id_consentimiento=consentimiento))
    finally:
        sa.event.remove(motor, 'after_cursor_execute', fallar)
    assert respuesta.status_code == 500 and 'SQL' not in respuesta.text
    assert contar(h, P) == contar(h, I) == 0
    assert iniciar(h, consentimiento).status_code == 201


@pytest.mark.parametrize('problema', ['sin_aceptacion', 'scope_produccion', 'fuera_periodo'])
def test_bloqueos_reales_previos_al_insert(configurado, monkeypatch, problema):
    h = configurado
    consentimiento = 2147483647 if problema == 'sin_aceptacion' else aceptar(h)
    admitir(h)
    if problema == 'scope_produccion':
        monkeypatch.setenv('ACADEMIC_RUNTIME_SCOPE', 'PRODUCCION')
        get_settings.cache_clear()
    elif problema == 'fuera_periodo':
        from app.modules.participation.domain.clock import RelojSistema
        instante = datetime.now(timezone.utc)+timedelta(hours=1)
        monkeypatch.setattr(RelojSistema, 'ahora', lambda self: instante)
    respuesta = iniciar(h, consentimiento)
    assert respuesta.status_code == (503 if problema == 'scope_produccion' else 403), respuesta.text
    assert contar(h, P) == contar(h, I) == 0
