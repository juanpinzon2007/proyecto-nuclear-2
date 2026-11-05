"""Fase 9: enlace HTTP estudiantil real, condicionado SOLO en laboratorio.

Reutiliza preparación administrativa, políticas explícitas y grafo de 8B.
No acredita login docente, políticas productivas ni publicación de notas.
"""
import json

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, func

from app.modules.identity.api.dependencies import obtener_usuario_actual, obtener_fabrica_tokens
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.evaluation import consultar_evidencias_8c, crear_evaluacion_8c
from app.modules.participation.domain.evaluation import PoliticaEvaluacionPendiente
from datetime import timezone
from app.modules.participation.infrastructure.models import IntentoModel, PasoSimulacionModel
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from tests.integration.test_participation_http_composition import (
    integracion, autor, pg_autoria, payload_valido, iniciar, cantidades,  # noqa: F401
)


def test_recorrido_vertical_desde_login_hasta_cierre_sin_publicar_resultados(integracion, record_property):
    h = integracion
    pasos = []

    def observar(nombre, respuesta, esperado):
        assert respuesta.status_code == esperado, nombre
        pasos.append(dict(paso=nombre, http=respuesta.status_code))
        # Nunca registrar el cuerpo del login, Bearer o código individual.
        record_property("recorrido_http", json.dumps(pasos))
        return respuesta

    login = observar("login correo/codigo SQL real", h.client.post(
        '/api/v1/identity/auth/estudiantes', json={
            'correo': f'autor{h.estudiante}@universidad.test',
            'codigo_convocatoria': h.codigo}), 200)
    h.headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    observar("identidad vigente", h.client.get('/api/v1/identity/me', headers=h.headers), 200)
    observar("ingreso sin crear participacion", h.client.post('/scheduling/validar-ingreso',
        headers=h.headers, json={'convocatoria_id': str(h.convocatoria),
            'estudiante_id': str(h.uuid_estudiante), 'codigo_acceso': h.codigo}), 200)
    assert cantidades(h) == ([], [])
    observar("titularidad ajena rechazada antes de crear", h.client.post(h.base + '/intentos',
        headers=h.headers_ajeno, json=h.body | {'id_consentimiento': h.consentimiento}), 403)
    assert cantidades(h) == ([], [])
    inicio = observar("inicio combinado transaccional", iniciar(h), 201).json()
    ik = inicio['id_intento']
    base = f'/api/v1/attempts/{ik}'
    resultado = f"/api/v1/participations/{inicio['id_participacion']}/attempts/{ik}/result"
    observar("segundo inicio no duplica", iniciar(h), 409)
    assert tuple(map(len, cantidades(h))) == (1, 1)
    # Nueva Session: convocatoria, asignación y sesión conservan la misma edición.
    with h.sesiones() as s:
        assert s.get(ConvocatoriaModel, h.convocatoria).sesion_id == h.sesion
        assert s.get(SesionProgramadaModel, h.sesion).version_caso_id == h.version
        assert s.get(AsignacionCasoModel, h.asignacion).version_caso_id == h.version
        assert s.get(IntentoModel, ik).id_participacion == inicio['id_participacion']
    observar("progreso ajeno privado", h.client.get(base + '/progress', headers=h.headers_ajeno), 403)
    observar("resultado activo cerrado por composicion", h.client.get(resultado, headers=h.headers), 503)
    actual = observar("contenido privado de primera escena", h.client.get(base + '/current-scenario', headers=h.headers), 200).json()
    q = actual['pregunta']
    url = base + '/decisions/' + q['id']
    observar("primera seleccion", h.client.post(url, headers=h.headers,
        json={'id_opcion': q['opciones'][0]['id']}), 201)
    observar("sustitucion prohibida", h.client.put(url, headers=h.headers,
        json={'id_opcion': q['opciones'][1]['id']}), 409)
    siguiente = observar("contenido privado de siguiente escena", h.client.get(base + '/current-scenario', headers=h.headers), 200).json()
    q2 = siguiente['pregunta']
    observar("pregunta pendiente del grafo real", h.client.post(base + '/decisions/' + q2['id'],
        headers=h.headers, json={'id_opcion': q2['opciones'][0]['id']}), 201)
    progreso = observar("progreso privado completo", h.client.get(base + '/progress', headers=h.headers), 200)
    assert progreso.json()['respondidas'] == 2 and progreso.json()['pendientes'] == []
    assert not any(x in progreso.text for x in ('es_correcta', 'justificacion', 'nota_final', 'puntaje', h.codigo))
    terminal = observar("ruta terminada sin preguntas futuras", h.client.get(base + '/current-scenario', headers=h.headers), 200).json()
    assert terminal['recorrido_finalizado'] and terminal['pregunta'] is None
    observar("finalizacion ajena rechazada", h.client.post(base + '/finish', headers=h.headers_ajeno), 403)
    assert observar("finalizacion titular", h.client.post(base + '/finish', headers=h.headers), 200).json()['estado'] == 'FINALIZADO'
    observar("cierre repetido idempotente", h.client.post(base + '/finish', headers=h.headers), 200)
    observar("contenido cerrado tras finalizar", h.client.get(base + '/current-scenario', headers=h.headers), 409)
    observar("resultado cerrado aun sin politica/composicion", h.client.get(resultado, headers=h.headers), 503)
    with h.sesiones() as s:
        assert s.get(IntentoModel, ik).estado == 'FINALIZADO'
        respuestas = s.scalars(select(PasoSimulacionModel).where(PasoSimulacionModel.id_intento == ik)).all()
        assert len(respuestas) == 2
        assert str(next(p for p in respuestas if str(p.id_decision) == q['id']).id_opcion) == q['opciones'][0]['id']
        assert s.scalar(select(func.count()).select_from(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == ik)) == 0
    record_property('persistencia_independiente', 'version exacta; 2 respuestas; seleccion original; FINALIZADO; 0 resultados')
    # El MISMO intento HTTP llega a la frontera 8C, sin motor ni política ficticios.
    # Reconstruir contexto exclusivamente desde su JWT y repositorio vigentes.
    with h.sesiones() as s:
        usuario = obtener_usuario_actual(
            HTTPAuthorizationCredentials(scheme='Bearer', credentials=login.json()['access_token']),
            h.client.app.dependency_overrides[obtener_fabrica_tokens](),
            lambda: RepositorioUsuariosSQLAlchemy(s))
    argumentos = dict(usuario=usuario, id_intento=ik, fechas=FechasPersistencia(timezone.utc), crear_sesion=h.sesiones)
    evidencia = consultar_evidencias_8c(**argumentos)
    assert evidencia.rubrica.version_id == h.version
    assert evidencia.rubrica.rubrica_id is not None and evidencia.rubrica.version_regla
    assert len(evidencia.intento.pasos) == 2
    with pytest.raises(PoliticaEvaluacionPendiente, match='mapeo aprobado'):
        crear_evaluacion_8c(**argumentos).previsualizar_intento(id_estudiante=h.estudiante, id_intento=ik)
    with h.sesiones() as s:
        assert s.scalar(select(func.count()).select_from(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == ik)) == 0
    record_property('frontera_8c', 'mismo intento y rubrica historica leidos; calculo bloqueado por mapeo; 0 resultados')
