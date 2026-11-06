"""Inicio SQL real con políticas explícitas SOLO de laboratorio; sin rutas públicas."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta, timezone
from threading import Barrier
from types import SimpleNamespace

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa

from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.identity.api import dependencies as identity, academic_dependencies
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM, GrupoEstudianteORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.participation.api.dependencies import obtener_facade
from app.modules.participation.api.router import router
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente, ErrorAplicacionParticipacion, RecursoNoDisponible
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.domain.errors import RespuestaInmutable
from app.modules.participation.infrastructure.start import crear_facade_inicio_8b
from app.modules.scheduling.domain.ingress_policy import VentanaIngreso
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.application.crear_convocatoria import crear_convocatoria
from app.modules.scheduling.infrastructure.admission import registrar_espera
from app.modules.scheduling.application.cambiar_estado_y_publicar import cambiar_estado_y_publicar
from app.modules.scheduling.application.registrar_observadores import crear_gestor_eventos
from tests.integration.test_cases_graph import pg_grafo, version_grafo, configurar  # noqa: F401
from tests.integration.test_cases_history import publicar
from tests.integration.test_participation_persistence import contexto, participacion, FECHA
from tests.integration.test_attempt_state import principal


class IngresoLaboratorio:
    def obtener_ventana(self, *, id_sesion, inicio, fin):
        return VentanaIngreso(inicio,fin,True,False)  # No es RF-22 aprobado.


class InicioLaboratorio:
    def __init__(self, referencia="sintetico"):
        self.referencia = referencia  # Configuración explícita SOLO LAB.

    def autorizar(self, c):
        # Regla SINTÉTICA explícita, jamás default productivo. Usa el cupo real
        # almacenado, sin sumar permisos ni conceder repeticiones excepcionales.
        if c.version_consentimiento != self.referencia:
            raise ReglaPendiente("Versión de consentimiento sin regla LAB.")
        if (c.estado_asignacion != "programada" or not c.apertura <= c.ahora < c.cierre
                or c.ahora > c.limite_ingreso or c.numero_intento > c.intentos_base
                or c.id_permiso_extra is not None):
            raise AccesoDenegado("Inicio fuera de la política LAB.")


def preparar_convocada(engine, *, configurar_recorrido=configurar):
    """Datos reales; permite preparar un grafo incompleto ANTES de publicar.

    Es helper de pruebas, no una política ni una configuración productiva.
    """
    c = contexto(engine)
    v = version_grafo()
    v.caso_id,v.docente_creador_id,v.numero = c.version.caso_id,c.version.docente_creador_id,2
    with c.sesiones.begin() as s:
        mapeado = CasoRepository(s)._mapear(v)
        familia = s.get(CasoModel,v.caso_id)
        familia.versiones.append(mapeado.versiones.pop())
    configurar_recorrido(c.sesiones,v)
    c.version = publicar(c.sesiones,v)
    with c.sesiones.begin() as s:
        vieja = s.get(S,c.sesion)
        nueva = S(espacio_academico_id=vieja.espacio_academico_id,version_caso_id=v.id,
            docente_id=vieja.docente_id,fecha_inicio=vieja.fecha_inicio,fecha_fin=vieja.fecha_fin,
            tiempo_maximo_minutos=vieja.tiempo_maximo_minutos,estado="SIN_INICIAR")
        s.add(nueva);s.flush()
        a = s.get(A,c.datos["id_asignacion"])
        asignacion = A(id_grupo=a.id_grupo,id_caso=a.id_caso,sesion_programada_id=nueva.id,version_caso_id=v.id,
            apertura=a.apertura,cierre=a.cierre,fecha_limite_ingreso=a.cierre,tiempo_maximo_min=a.tiempo_maximo_min)
        s.add(asignacion);s.flush()
        conv = crear_convocatoria(s,sesion_id=nueva.id,estudiante_id=c.uuid)
        c.datos |= dict(id_asignacion=asignacion.id_asignacion,convocatoria_id=conv.convocatoria_id)
        c.sesion,c.codigo = nueva.id,conv.codigo_acceso
    c.usuario = principal(c)
    c.ahora = FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=1)
    # Contrato posterior: EN_CURSO sin concesión individual no autoriza inicio.
    # Preparación LAB mediante servicios reales, sin INSERT de admisiones falsas.
    with c.sesiones.begin() as s:
        registrar_espera(s,usuario=c.usuario,convocatoria_id=c.datos['convocatoria_id'],
            codigo=c.codigo,reloj=SimpleNamespace(ahora=lambda:c.ahora))
    with c.sesiones() as s:
        asyncio.run(cambiar_estado_y_publicar(s,sesion_id=c.sesion,accion='iniciar',
            gestor=crear_gestor_eventos(c.sesiones)))
    return c


@pytest.fixture
def convocada(pg_grafo):
    return preparar_convocada(pg_grafo)


@pytest.fixture
def c(convocada):
    c = convocada
    c.pk = participacion(c)
    return c


def facade(c, **kw):
    return crear_facade_inicio_8b(**(dict(usuario=c.usuario,id_participacion=c.pk,
        reloj=SimpleNamespace(ahora=lambda:c.ahora),fechas=FechasPersistencia(timezone.utc),
        crear_sesion=c.sesiones,codigo_acceso=c.codigo,
        politica_ingreso=IngresoLaboratorio(),politica_inicio=InicioLaboratorio())|kw))


def iniciar(c, **kw):
    return facade(c,**kw).iniciar_intento(id_estudiante=c.alumno,id_participacion=c.pk,id_consentimiento=c.consentimiento)


def filas(c):
    with c.sesiones() as s:
        return [dict(x) for x in s.execute(sa.select(I.__table__).where(I.id_participacion==c.pk)).mappings()]


def test_inicio_real_y_segunda_session_con_version_y_duracion(c):
    r = iniciar(c)
    f = filas(c)
    assert len(f)==1 and f[0]["id_intento"]==r.id_intento and f[0]["estado"]=="EN_CURSO"
    assert f[0]["duracion_concedida_segundos"]==1800 and f[0]["id_consentimiento"]==c.consentimiento
    assert r.vence_en-r.inicio==timedelta(minutes=30)
    # Después del inicio, la composición 8B existente puede leer el intento.
    from tests.integration.test_scheduling_participation import real
    c.ik = r.id_intento
    assert real(c).consultar_progreso(id_estudiante=c.alumno,id_intento=c.ik).respondidas==0
    q=c.version.escenarios[0].preguntas[0]
    real(c).registrar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[0].id)
    with pytest.raises(RespuestaInmutable):
        real(c).modificar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[1].id)


@pytest.mark.parametrize("estado",["SIN_INICIAR","FINALIZADO"])
def test_sesion_no_permitida(c,estado):
    with c.sesiones.begin() as s:s.get(S,c.sesion).estado=estado
    with pytest.raises(AccesoDenegado):iniciar(c)
    assert filas(c)==[]


@pytest.mark.parametrize("minutos",[-1,60,61])
def test_fuera_de_horario(c,minutos):
    c.ahora=FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=minutos)
    with pytest.raises(AccesoDenegado):iniciar(c)
    assert filas(c)==[]


@pytest.mark.parametrize("control",["cuenta","rol","matricula","convocatoria","contexto","consentimiento","futuro","codigo"])
def test_controles_reales_del_inicio(c,control):
    with c.sesiones.begin() as s:
        if control=="cuenta":s.get(UsuarioORM,c.alumno).activo=False
        elif control=="rol":s.get(UsuarioORM,c.alumno).id_rol=1
        elif control=="matricula":s.get(GrupoEstudianteORM,c.datos["id_grupo_estudiante"]).activo=False
        elif control=="convocatoria":s.get(C,c.datos["convocatoria_id"]).estado="RETIRADA"
        elif control=="consentimiento":s.get(ConsentimientoORM,c.consentimiento).fecha_revocacion=FECHA
        elif control=="futuro":s.get(ConsentimientoORM,c.consentimiento).fecha_aceptacion=FECHA+timedelta(hours=2)
    kw={}
    if control=="contexto":kw["usuario"]=replace(c.usuario,id_convocatoria=None)
    if control=="codigo":kw["codigo_acceso"]="incorrecto"
    with pytest.raises(AccesoDenegado):iniciar(c,**kw)
    assert filas(c)==[]


def test_titular_ajeno(c):
    otro = contexto(c.engine)
    with pytest.raises(AccesoDenegado):iniciar(c,usuario=principal(otro))
    assert filas(c)==[]


@pytest.mark.parametrize("ausente",["politica_ingreso","politica_inicio"])
def test_falta_politica_cierra(c,ausente):
    with pytest.raises(ReglaPendiente):iniciar(c,**{ausente:None})
    assert filas(c)==[]


def test_duplicado_y_repeticion_no_autorizada(c):
    r=iniciar(c)
    with pytest.raises(ErrorAplicacionParticipacion):iniciar(c)
    from tests.integration.test_scheduling_participation import real
    c.ik=r.id_intento
    real(c).finalizar(id_estudiante=c.alumno,id_intento=c.ik)
    with pytest.raises(AccesoDenegado):iniciar(c)
    assert len(filas(c))==1


def test_rollback_tras_insert(c,monkeypatch):
    original=RepositorioParticipacionSQLAlchemy.agregar_intento
    def fallo(self,intento):
        original(self,intento)
        raise RuntimeError("Fallo intermedio de laboratorio")
    with monkeypatch.context() as m:
        m.setattr(RepositorioParticipacionSQLAlchemy,"agregar_intento",fallo)
        with pytest.raises(RuntimeError):iniciar(c)
    assert filas(c)==[]
    iniciar(c)
    assert len(filas(c))==1


def test_concurrencia_dos_solicitudes_un_intento(c):
    barrera=Barrier(2)
    def enviar():
        barrera.wait(timeout=5)
        try:iniciar(c);return "creado"
        except ErrorAplicacionParticipacion:return "rechazado"
    with ThreadPoolExecutor(max_workers=2) as p:
        assert sorted(p.map(lambda _:enviar(),range(2)))==["creado","rechazado"]
    assert len(filas(c))==1


def test_revalidar_instante_real_no_autorizacion_obsoleta(c):
    fin=FECHA.replace(tzinfo=timezone.utc)+timedelta(hours=1)
    instantes=iter((fin-timedelta(seconds=1),fin))
    with pytest.raises(AccesoDenegado):
        iniciar(c,reloj=SimpleNamespace(ahora=lambda:next(instantes)))
    assert filas(c)==[]


def test_version_archivada_no_se_sustituye(c):
    with c.sesiones() as s:
        v=CasoRepository(s).obtener_version(c.version.id,c.version.docente_creador_id)
        v.archivar();CasoRepository(s).actualizar_estado(v)
    with pytest.raises(RecursoNoDisponible):iniciar(c)
    assert filas(c)==[]


def test_duracion_contradictoria_no_se_inventa(c):
    with c.sesiones.begin() as s:s.get(S,c.sesion).tiempo_maximo_minutos=40
    with pytest.raises(ReglaPendiente):iniciar(c)
    assert filas(c)==[]


@pytest.mark.parametrize("resultado",[True,False,"permitido"])
def test_contrato_politica_invalido_no_concede_acceso(c,resultado):
    with pytest.raises(ReglaPendiente):
        iniciar(c,politica_inicio=SimpleNamespace(autorizar=lambda _:resultado))
    assert filas(c)==[]


def test_fallo_politica_no_escribe(c):
    class Fallo:
        def autorizar(self,_):raise RuntimeError("Proveedor no disponible")
    with pytest.raises(RuntimeError):iniciar(c,politica_inicio=Fallo())
    assert filas(c)==[]


def test_consentimiento_ajeno_no_inicia(c):
    otro=contexto(c.engine)
    with pytest.raises(AccesoDenegado):
        facade(c).iniciar_intento(id_estudiante=c.alumno,id_participacion=c.pk,id_consentimiento=otro.consentimiento)
    assert filas(c)==[]


@pytest.mark.parametrize("defecto",["inexistente","ajeno","profesor_ajeno"])
def test_permiso_no_verificado_no_inicia(c,defecto):
    permiso=2147483647
    if defecto != "inexistente":
        otro=contexto(c.engine)
        otra_p=participacion(otro)
        with c.sesiones.begin() as s:
            p=PermisoIntentoExtraORM(id_participacion=otra_p if defecto=="ajeno" else c.pk,
                id_profesor=otro.docente,cantidad_autorizada=1,justificacion="Fixture negativa",
                fecha_autorizacion=FECHA)
            s.add(p);s.flush();permiso=p.id_permiso_extra
    with pytest.raises(AccesoDenegado):
        facade(c).iniciar_intento(id_estudiante=c.alumno,id_participacion=c.pk,
            id_consentimiento=c.consentimiento,id_permiso_extra=permiso)
    assert filas(c)==[]


@pytest.fixture
def http_inicio(c,monkeypatch):
    monkeypatch.setattr(identity,"get_session_factory",lambda:c.sesiones)
    monkeypatch.setattr(academic_dependencies,"get_session_factory",lambda:c.sesiones)
    tokens=TokensJWT("clave-exclusiva-inicio-laboratorio-"*3,"inicio-lab","cliente-lab")
    app=FastAPI(debug=False);app.include_router(router)
    app.dependency_overrides[identity.obtener_fabrica_tokens]=lambda:lambda:tokens
    def dependencia(usuario=Depends(identity.obtener_estudiante_actual)):
        return facade(c,usuario=usuario)
    app.dependency_overrides[obtener_facade]=dependencia
    with TestClient(app) as client:
        yield client,{"Authorization":"Bearer "+tokens.emitir(str(c.alumno),str(c.datos["convocatoria_id"]))}


def test_http_inicio_jwt_real_y_duplicado(c,http_inicio):
    client,headers=http_inicio
    url=f"/api/v1/participations/{c.pk}/attempts"
    body={"id_consentimiento":c.consentimiento}
    r=client.post(url,json=body,headers=headers)
    assert r.status_code==201 and r.json()["estado"]=="EN_CURSO"
    assert client.post(url,json=body,headers=headers).status_code==409


@pytest.mark.parametrize("token",[None,"Bearer invalido"])
def test_http_sin_autenticacion_no_escribe(c,http_inicio,token):
    client,_=http_inicio
    r=client.post(f"/api/v1/participations/{c.pk}/attempts",json={"id_consentimiento":c.consentimiento},
        headers={} if token is None else {"Authorization":token})
    assert r.status_code==401 and filas(c)==[]


def test_http_politica_faltante_503(c,http_inicio,monkeypatch):
    client,headers=http_inicio
    def pendiente(self,condiciones):raise ReglaPendiente("Sin política de consentimiento")
    monkeypatch.setattr(InicioLaboratorio,"autorizar",pendiente)
    r=client.post(f"/api/v1/participations/{c.pk}/attempts",json={"id_consentimiento":c.consentimiento},headers=headers)
    assert r.status_code==503 and r.json()["detail"]["codigo"]=="INTEGRACION_O_POLITICA_PENDIENTE"
    assert filas(c)==[]
