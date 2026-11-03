"""Identity + Scheduling + Cases + Participation reales, sin políticas simuladas.

PostgreSQL desechable; JWT existente con claves de laboratorio y reloj controlado.
Los intentos se provisionan como datos sintéticos: no son inicios productivos.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa

from app.modules.identity.api import dependencies as identity, academic_dependencies
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.participation.api.dependencies import obtener_facade, crear_dependencia_facade_8b
from app.modules.participation.api.router import router
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.domain.errors import IntentoNoEditable, RespuestaInmutable
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.composition import crear_facade_8b
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.scheduling.application.attempt_operations import (
    autorizar_respuesta_sesion, OperacionSesionDenegada, CondicionesOperacionNoDisponibles,
)
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C
from tests.integration.test_cases_graph import simulacion, pg_grafo  # noqa: F401
from tests.integration.test_participation_persistence import FECHA, contexto
from tests.integration.test_attempt_state import principal
from tests.integration.test_steps_uuid import filas


def real(c, *, usuario=None):
    return crear_facade_8b(usuario=c.usuario if usuario is None else usuario, id_intento=c.ik,
        reloj=SimpleNamespace(ahora=lambda: c.ahora), fechas=FechasPersistencia(timezone.utc),
        crear_sesion=c.sesiones)  # NO proveedor de autorización ni recorrido falso.


def responder(c, escena=0, opcion=0, **opciones):
    q = c.version.escenarios[escena].preguntas[0]
    return real(c, **opciones).registrar_decision(id_estudiante=c.alumno, id_intento=c.ik,
        id_decision=q.id, id_opcion=q.opciones[opcion].id)


@pytest.mark.parametrize("segundos,permitido", [(-1,False),(0,True),(3599,True),(3600,False),(3601,False)])
def test_fronteras_confirmadas_scheduling(segundos, permitido):
    inicio = FECHA.replace(tzinfo=timezone.utc)
    argumentos = dict(estado="EN_CURSO", inicio=inicio, fin=inicio+timedelta(hours=1),
                     ahora=inicio+timedelta(seconds=segundos), operacion="RESPONDER")
    if permitido:
        assert autorizar_respuesta_sesion(**argumentos) is None
    else:
        with pytest.raises(OperacionSesionDenegada):
            autorizar_respuesta_sesion(**argumentos)


@pytest.mark.parametrize("invalido", ["zona", "orden", "estado", "reloj"])
def test_datos_no_verificables_no_conceden_permiso(invalido):
    inicio = FECHA.replace(tzinfo=timezone.utc)
    args = dict(estado="EN_CURSO", inicio=inicio, fin=inicio+timedelta(hours=1), ahora=inicio, operacion="RESPONDER")
    if invalido == "zona": args["inicio"] = FECHA
    elif invalido == "orden": args["fin"] = inicio
    elif invalido == "estado": args["estado"] = "DESCONOCIDO"
    else: args["ahora"] = None
    with pytest.raises(CondicionesOperacionNoDisponibles):
        autorizar_respuesta_sesion(**args)


def test_responder_y_completar_rama_sin_proveedores_simulados(simulacion):
    c = simulacion
    responder(c)
    antes = filas(c)
    with pytest.raises(RespuestaInmutable): responder(c, opcion=1)
    with pytest.raises(AccesoDenegado): responder(c, escena=2)
    assert filas(c) == antes
    responder(c, escena=1)
    progreso = real(c).consultar_progreso(id_estudiante=c.alumno, id_intento=c.ik)
    assert progreso.respondidas == 2 and progreso.pendientes == () and progreso.total_aplicable == 2
    cerrado = real(c).finalizar(id_estudiante=c.alumno, id_intento=c.ik)
    assert cerrado.estado.value == "FINALIZADO"


@pytest.mark.parametrize("estado", ["SIN_INICIAR", "FINALIZADO"])
def test_estado_sesion_no_autoriza_respuestas(simulacion, estado):
    c = simulacion
    with c.engine.begin() as s: s.execute(sa.update(S).where(S.id == c.sesion).values(estado=estado))
    with pytest.raises(AccesoDenegado): responder(c)
    assert filas(c) == []


@pytest.mark.parametrize("momento", ["antes", "fin", "despues"])
def test_horario_sesion_releido_y_fin_exclusivo(simulacion, momento):
    c = simulacion
    with c.engine.begin() as s:
        s.execute(sa.update(S).where(S.id == c.sesion).values(
            fecha_inicio=(FECHA+timedelta(minutes=2)).replace(tzinfo=timezone.utc),
            fecha_fin=(FECHA+timedelta(minutes=5)).replace(tzinfo=timezone.utc)))
    c.ahora = (FECHA+timedelta(minutes={"antes":1,"fin":5,"despues":6}[momento])).replace(tzinfo=timezone.utc)
    with pytest.raises(AccesoDenegado): responder(c)
    assert filas(c) == []


def test_cierre_entre_autorizacion_y_registro_no_se_elude(simulacion):
    c = simulacion
    fin = (FECHA+timedelta(minutes=5)).replace(tzinfo=timezone.utc)
    with c.engine.begin() as s:
        s.execute(sa.update(S).where(S.id == c.sesion).values(fecha_fin=fin))
    instantes = iter((fin-timedelta(seconds=1), fin-timedelta(microseconds=1), fin))
    f = crear_facade_8b(usuario=c.usuario, id_intento=c.ik,
        reloj=SimpleNamespace(ahora=lambda:next(instantes)), fechas=FechasPersistencia(timezone.utc), crear_sesion=c.sesiones)
    q = c.version.escenarios[0].preguntas[0]
    with pytest.raises(AccesoDenegado):
        f.registrar_decision(id_estudiante=c.alumno, id_intento=c.ik, id_decision=q.id, id_opcion=q.opciones[0].id)
    assert filas(c) == []


def test_zona_equivalente_no_cambia_autorizacion(simulacion):
    c = simulacion
    c.ahora = c.ahora.astimezone(timezone(timedelta(hours=-5)))
    responder(c)
    assert len(filas(c)) == 1


@pytest.mark.parametrize("control", ["matricula", "convocatoria", "cuenta", "rol", "contexto"])
def test_autorizacion_relee_identity_y_scheduling(simulacion, control):
    c = simulacion
    with c.engine.begin() as s:
        if control == "matricula":
            s.execute(sa.update(GrupoEstudianteORM).where(GrupoEstudianteORM.id_grupo_estudiante == c.datos["id_grupo_estudiante"]).values(activo=False))
        elif control == "convocatoria": s.execute(sa.update(C).where(C.id == c.datos["convocatoria_id"]).values(estado="RETIRADA"))
        elif control == "cuenta": s.execute(sa.update(UsuarioORM).where(UsuarioORM.id_usuario == c.alumno).values(activo=False))
        elif control == "rol": s.execute(sa.update(UsuarioORM).where(UsuarioORM.id_usuario == c.alumno).values(id_rol=1))
        else: c.usuario = replace(c.usuario, id_convocatoria=str(uuid4()))
    with pytest.raises(AccesoDenegado): responder(c)
    assert filas(c) == []


def test_intento_ajeno_no_se_consulta_ni_responde(simulacion):
    c = simulacion
    otro = contexto(c.engine)
    with pytest.raises(AccesoDenegado): responder(c, usuario=principal(otro))
    with pytest.raises(AccesoDenegado):
        real(c, usuario=principal(otro)).consultar_progreso(id_estudiante=otro.alumno, id_intento=c.ik)
    assert filas(c) == []


def test_duracion_individual_historica_no_se_recalcula(simulacion):
    c = simulacion
    with c.engine.begin() as s: s.execute(sa.update(S).where(S.id == c.sesion).values(tiempo_maximo_minutos=1))
    c.ahora = (FECHA+timedelta(minutes=5)).replace(tzinfo=timezone.utc)
    responder(c)
    c.ahora = (FECHA+timedelta(minutes=30, microseconds=1)).replace(tzinfo=timezone.utc)
    with pytest.raises(IntentoNoEditable): responder(c, escena=1)
    assert len(filas(c)) == 1
    assert real(c).consultar_progreso(id_estudiante=c.alumno,id_intento=c.ik).intento.estado.value == "VENCIDO"


@pytest.mark.parametrize("limite", ["varias", "ciclo"])
def test_recorrido_no_soportado_no_infiere_permiso(pg_grafo, monkeypatch, limite):
    import tests.integration.test_cases_graph as datos
    from app.modules.cases.domain.entities.caso import Pregunta
    from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
    if limite == "varias":
        original = datos.version_grafo
        def version():
            v = original(); v.escenarios[0].preguntas.append(Pregunta(2, "Pregunta sin regla de avance")); return v
        monkeypatch.setattr(datos, "version_grafo", version)
        # Publicar exige opciones: copiar una pregunta completa con IDs nuevos.
        from app.modules.cases.domain.entities.caso import OpcionRespuesta
        anterior = version
        def completa():
            v = anterior(); q = v.escenarios[0].preguntas[-1]
            q.opciones = [OpcionRespuesta(o.orden,o.texto,o.es_correcta,o.justificacion,valoraciones=dict(o.valoraciones))
                          for o in v.escenarios[0].preguntas[0].opciones]
            return v
        monkeypatch.setattr(datos, "version_grafo", completa)
    else:
        original = datos.configurar
        def configurar(sesiones, v):
            ids, opciones = original(sesiones, v)
            with sesiones.begin() as s:
                RepositorioGrafoSQLAlchemy(s).configurar(version_id=v.id, docente_id=v.docente_creador_id,
                    inicial_id=ids[0], transiciones=((opciones[1][0].id,"ESCENA",ids[0]),))
            return ids, opciones
        monkeypatch.setattr(datos, "configurar", configurar)
    c = datos.simulacion.__wrapped__(pg_grafo)
    with pytest.raises(ReglaPendiente): responder(c)
    assert filas(c) == []


def test_rollback_de_escritura_no_confirma_respuesta(simulacion, monkeypatch):
    c = simulacion
    original = RepositorioParticipacionSQLAlchemy.guardar_intento
    def fallar(self, *a, **kw):
        original(self, *a, **kw)
        raise RuntimeError("Fallo después de insertar, antes del commit")
    with monkeypatch.context() as m:
        m.setattr(RepositorioParticipacionSQLAlchemy, "guardar_intento", fallar)
        with pytest.raises(RuntimeError): responder(c)
    assert filas(c) == []
    responder(c)
    assert len(filas(c)) == 1


def test_registros_concurrentes_con_autorizacion_real(simulacion):
    c, barrera = simulacion, Barrier(2)
    def enviar(opcion):
        barrera.wait(timeout=5)
        try: responder(c, opcion=opcion); return "guardada"
        except RespuestaInmutable: return "rechazada"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(enviar, (0,1))) == ["guardada","rechazada"]
    assert len(filas(c)) == 1


def test_inicio_sigue_cerrado_aunque_este_autorizado_responder(simulacion):
    c = simulacion
    with pytest.raises(ReglaPendiente):
        real(c).iniciar_intento(id_estudiante=c.alumno, id_participacion=c.pk, id_consentimiento=c.consentimiento)
    assert filas(c) == []
    responder(c)
    assert len(filas(c)) == 1  # Autorizar respuesta no implica autorizar inicio.


def test_autorizacion_no_se_reutiliza_fuera_de_su_transaccion(simulacion):
    from app.modules.participation.infrastructure.composition import (
        _Alcance, SchedulingIntentoSQLAlchemy, AutorizacionRespuestaScheduling,
    )
    c = simulacion
    with c.sesiones() as s:
        alcance = _Alcance(lambda:s, c.usuario, c.ik, FechasPersistencia(timezone.utc))
        adaptador = SchedulingIntentoSQLAlchemy(alcance, AutorizacionRespuestaScheduling(),
            SimpleNamespace(ahora=lambda:c.ahora))
        with s.begin():
            with pytest.raises(ReglaPendiente): adaptador.validar_instante_registro(instante=c.ahora)
            adaptador.validar_edicion(id_asignacion=c.datos["id_asignacion"],id_grupo_estudiante=c.datos["id_grupo_estudiante"])
            adaptador.validar_instante_registro(instante=c.ahora)
        with s.begin(), pytest.raises(ReglaPendiente):
            adaptador.validar_instante_registro(instante=c.ahora)
    assert filas(c) == []


@pytest.fixture
def http(simulacion, monkeypatch):
    c = simulacion
    monkeypatch.setattr(identity, "get_session_factory", lambda: c.sesiones)
    monkeypatch.setattr(academic_dependencies, "get_session_factory", lambda: c.sesiones)
    tokens = TokensJWT("clave-exclusiva-scheduling-participation-test-"*2,"8b-lab","8b-client")
    app = FastAPI(debug=False); app.include_router(router)
    app.dependency_overrides[identity.obtener_fabrica_tokens] = lambda: lambda: tokens
    app.dependency_overrides[obtener_facade] = crear_dependencia_facade_8b(crear_sesion=c.sesiones,
        fechas=FechasPersistencia(timezone.utc), reloj=SimpleNamespace(ahora=lambda:c.ahora))
    with TestClient(app) as client:
        yield SimpleNamespace(c=c, client=client, app=app, tokens=tokens,
            headers={"Authorization":"Bearer "+tokens.emitir(str(c.alumno),str(c.datos["convocatoria_id"]))})


def ruta(c, escena=0):
    q = c.version.escenarios[escena].preguntas[0]
    return f"/api/v1/attempts/{c.ik}/decisions/{q.id}", {"id_opcion":str(q.opciones[0].id)}


def test_http_real_jwt_sql_respuesta_progreso_put_y_cierre(http):
    h, c = http, http.c
    path, body = ruta(c)
    assert h.client.post(path,json=body,headers=h.headers).status_code == 201
    assert h.client.put(path,json=body,headers=h.headers).json()["detail"]["codigo"] == "RESPUESTA_INMUTABLE"
    assert h.client.post(path,json=body,headers=h.headers).status_code == 409
    path2, body2 = ruta(c,1)
    assert h.client.post(path2,json=body2,headers=h.headers).status_code == 201
    p = h.client.get(f"/api/v1/attempts/{c.ik}/progress",headers=h.headers)
    assert p.status_code == 200 and p.json()["respondidas"] == 2
    for prohibido in ("es_correcta","puntaje","justificacion","nota_final"):
        assert prohibido not in p.text
    fin = f"/api/v1/attempts/{c.ik}/finish"
    r = h.client.post(fin,headers=h.headers)
    assert r.status_code == 200 and h.client.post(fin,headers=h.headers).json() == r.json()


@pytest.mark.parametrize("token", ["ausente", "invalido", "convocatoria_ajena", "inactivo"])
def test_http_no_elude_identity(http, token):
    h, c = http, http.c
    headers = dict(h.headers)
    if token == "ausente": headers = {}
    elif token == "invalido": headers["Authorization"] = "Bearer no-valido"
    elif token == "convocatoria_ajena": headers["Authorization"] = "Bearer "+h.tokens.emitir(str(c.alumno),str(uuid4()))
    else:
        with c.engine.begin() as s: s.execute(sa.update(UsuarioORM).where(UsuarioORM.id_usuario==c.alumno).values(activo=False))
    path, body = ruta(c)
    respuesta = h.client.post(path,json=body,headers=headers)
    assert respuesta.status_code == (403 if token == "convocatoria_ajena" else 401)
    assert filas(c) == []


def test_http_inicio_y_resultados_no_se_abren(http):
    h, c = http, http.c
    r = h.client.post(f"/api/v1/participations/{c.pk}/attempts",
        json={"id_consentimiento":c.consentimiento},headers=h.headers)
    assert r.status_code == 503 and r.json()["detail"]["codigo"] == "INICIO_NO_HABILITADO"
    assert h.client.get(f"/api/v1/participations/{c.pk}/attempts/{c.ik}/result",headers=h.headers).status_code == 503
    assert filas(c) == []
