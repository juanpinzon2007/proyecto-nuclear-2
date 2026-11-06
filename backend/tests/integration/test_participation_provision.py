"""Convocatoria → participación → intento y recorrido HTTP real en app aislada.

Todas las políticas positivas son explícitamente LAB. Ningún mock sustituye
titularidad, matrícula, relaciones, grafo, repositorio, JWT o transacción.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta, timezone
from threading import Barrier
from types import SimpleNamespace

from fastapi import APIRouter, Depends, FastAPI, Response
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest
import sqlalchemy as sa

from app.modules.identity.api import dependencies as identity, academic_dependencies
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.participation.api.dependencies import obtener_facade, crear_dependencia_facade_8b
from app.modules.participation.api.errors import RutaParticipacion
from app.modules.participation.api.mappers import mapear_intento
from app.modules.participation.api.router import router
from app.modules.participation.api.schemas import EsquemaHTTP, Identificador, IntentoRespuesta
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente, ErrorAplicacionParticipacion
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import ParticipacionModel as P, IntentoModel as I
from app.modules.participation.infrastructure.provision import ServicioVinculacionSQLAlchemy
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel as S, ConvocatoriaModel as C
from tests.integration.test_attempt_start import convocada, pg_grafo, IngresoLaboratorio, InicioLaboratorio  # noqa: F401
from tests.integration.test_participation_persistence import contexto
from tests.integration.test_attempt_state import principal
from tests.integration.consent_support import FuenteConsentimientoLaboratorio


class VinculacionLaboratorio:
    def autorizar(self, c):
        if (c.estado_asignacion != "programada" or not c.apertura <= c.ahora < c.cierre
                or c.ahora > c.limite_ingreso):
            raise AccesoDenegado("Sin autorización de provisión LAB.")
        return "pendiente"  # Elección expresa LAB, no default del servicio.


def servicio(c, **kw):
    return ServicioVinculacionSQLAlchemy(**(dict(usuario=c.usuario,
        reloj=SimpleNamespace(ahora=lambda:c.ahora),fechas=FechasPersistencia(timezone.utc),
        crear_sesion=c.sesiones,politica_ingreso=IngresoLaboratorio(),
        politica_vinculacion=VinculacionLaboratorio(),politica_inicio=InicioLaboratorio(),
        fuente_consentimiento=FuenteConsentimientoLaboratorio())|kw))


def argumentos(c, **kw):
    return dict(convocatoria_id=c.datos["convocatoria_id"],id_asignacion=c.datos["id_asignacion"],codigo_acceso=c.codigo)|kw


def vincular(c, **kw):
    return servicio(c,**kw).obtener_o_crear(**argumentos(c))


def iniciar(c, **kw):
    return servicio(c,**kw).iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=c.consentimiento)


def filas(c):
    # Session distinta: lo observado ya tuvo que confirmarse o revertirse.
    with c.sesiones() as s:
        p=[dict(x) for x in s.execute(sa.select(P.__table__).where(P.convocatoria_id==c.datos["convocatoria_id"])).mappings()]
        i=[dict(x) for x in s.execute(sa.select(I.__table__).join(P,P.id_participacion==I.id_participacion)
            .where(P.convocatoria_id==c.datos["convocatoria_id"])).mappings()]
        return p,i


def test_crear_vinculo_referencias_y_recuperar_sin_duplicar(convocada):
    c=convocada
    a=vincular(c);b=vincular(c)
    assert a.creada and not b.creada and a.participacion==b.participacion
    p,i=filas(c)
    assert len(p)==1 and not i
    assert (p[0]["id_asignacion"],p[0]["id_grupo_estudiante"],p[0]["convocatoria_id"])==(
        c.datos["id_asignacion"],c.datos["id_grupo_estudiante"],c.datos["convocatoria_id"])


def test_recuperacion_conserva_estado_existente(convocada):
    c=convocada;a=vincular(c)
    with c.sesiones.begin() as s:s.get(P,a.participacion.id_participacion).estado="estado-fixture"
    b=vincular(c)
    assert not b.creada and b.participacion.estado=="estado-fixture"


def test_convocatoria_ajena_no_crea(convocada):
    c=convocada;otro=contexto(c.engine)
    with pytest.raises(AccesoDenegado):vincular(c,usuario=principal(otro))
    assert filas(c)==([],[])


@pytest.mark.parametrize("invalido",["cuenta","rol","matricula","convocatoria","contexto","sesion_no_iniciada","sesion_finalizada"])
def test_validaciones_reales(convocada,invalido):
    c=convocada
    with c.sesiones.begin() as s:
        if invalido=="cuenta":s.get(UsuarioORM,c.alumno).activo=False
        elif invalido=="rol":s.get(UsuarioORM,c.alumno).id_rol=1
        elif invalido=="matricula":s.get(GrupoEstudianteORM,c.datos["id_grupo_estudiante"]).activo=False
        elif invalido=="convocatoria":s.get(C,c.datos["convocatoria_id"]).estado="RETIRADA"
        elif invalido=="sesion_no_iniciada":s.get(S,c.sesion).estado="SIN_INICIAR"
        elif invalido=="sesion_finalizada":s.get(S,c.sesion).estado="FINALIZADO"
    kw={"usuario":replace(c.usuario,id_convocatoria=None)} if invalido=="contexto" else {}
    with pytest.raises(AccesoDenegado):vincular(c,**kw)
    assert filas(c)==([],[])


@pytest.mark.parametrize("dato",["codigo","asignacion","convocatoria"])
def test_no_acepta_referencias_del_cliente_sin_verificar(convocada,dato):
    c=convocada;otro=contexto(c.engine)
    kw={"codigo_acceso":"incorrecto"} if dato=="codigo" else (
        {"id_asignacion":otro.datos["id_asignacion"]} if dato=="asignacion" else {"convocatoria_id":otro.datos["convocatoria_id"]})
    with pytest.raises(AccesoDenegado):servicio(c).obtener_o_crear(**argumentos(c,**kw))
    assert filas(c)==([],[])


@pytest.mark.parametrize("politica",["politica_ingreso","politica_vinculacion","politica_inicio"])
def test_inicio_sin_politicas_no_deja_participacion(convocada,politica):
    c=convocada
    with pytest.raises(ReglaPendiente):iniciar(c,**{politica:None})
    assert filas(c)==([],[])


@pytest.mark.parametrize("estado",[None,True,"","x"*21])
def test_estado_no_aprobado_no_se_inventa(convocada,estado):
    c=convocada
    with pytest.raises(ReglaPendiente):vincular(c,politica_vinculacion=SimpleNamespace(autorizar=lambda _:estado))
    assert filas(c)==([],[])


def test_dos_provisiones_concurrentes_un_vinculo(convocada):
    c=convocada;barrera=Barrier(2)
    def enviar(_):
        barrera.wait(timeout=5)
        return vincular(c)
    with ThreadPoolExecutor(max_workers=2) as pool:resultados=list(pool.map(enviar,range(2)))
    assert sorted(x.creada for x in resultados)==[False,True]
    assert len({x.participacion.id_participacion for x in resultados})==1
    assert len(filas(c)[0])==1


def test_dos_inicios_concurrentes_un_vinculo_y_un_intento(convocada):
    c=convocada;barrera=Barrier(2)
    def enviar(_):
        barrera.wait(timeout=5)
        try:iniciar(c);return "creado"
        except ErrorAplicacionParticipacion:return "rechazado"
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(enviar,range(2)))==["creado","rechazado"]
    p,i=filas(c)
    assert len(p)==len(i)==1 and i[0]["id_participacion"]==p[0]["id_participacion"]


@pytest.mark.parametrize("punto",["participacion","intento","commit"])
def test_rollback_atomico_de_ambas_entidades(convocada,monkeypatch,punto):
    c=convocada
    clase,nombre=(UnidadTrabajoSQLAlchemy,"commit") if punto=="commit" else (
        RepositorioParticipacionSQLAlchemy,"agregar_participacion" if punto=="participacion" else "agregar_intento")
    original=getattr(clase,nombre)
    def fallo(self,*args,**kw):
        if punto!="commit":original(self,*args,**kw)
        raise RuntimeError("Fallo intermedio LAB")
    with monkeypatch.context() as m:
        m.setattr(clase,nombre,fallo)
        with pytest.raises(RuntimeError):iniciar(c)
    assert filas(c)==([],[])
    iniciar(c)
    assert all(len(x)==1 for x in filas(c))


def test_inicio_fallido_con_p_existente_no_elimina_historial(convocada):
    c=convocada;p=vincular(c)
    with pytest.raises(ReglaPendiente):iniciar(c,politica_inicio=None)
    guardadas,intentos=filas(c)
    assert len(guardadas)==1 and guardadas[0]["id_participacion"]==p.participacion.id_participacion and not intentos


def test_consentimiento_ajeno_revierte_participacion_nueva(convocada):
    c=convocada;otro=contexto(c.engine)
    with pytest.raises(AccesoDenegado):
        servicio(c).iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=otro.consentimiento)
    assert filas(c)==([],[])


@pytest.mark.parametrize("politica",["politica_ingreso","politica_vinculacion"])
def test_proveedor_no_disponible_no_concede_acceso(convocada,politica):
    c=convocada
    class Fallo:
        def obtener_ventana(self,**_):raise RuntimeError("Política LAB no disponible")
        def autorizar(self,_):raise RuntimeError("Política LAB no disponible")
    with pytest.raises(RuntimeError):vincular(c,**{politica:Fallo()})
    assert filas(c)==([],[])


class SolicitudVinculacion(EsquemaHTTP):
    id_asignacion: Identificador
    codigo_acceso: SecretStr


class SolicitudInicio(SolicitudVinculacion):
    id_consentimiento: Identificador
    id_permiso_extra: Identificador | None=None


@pytest.fixture
def http(convocada,monkeypatch):
    from uuid import UUID
    c=convocada
    monkeypatch.setattr(identity,"get_session_factory",lambda:c.sesiones)
    monkeypatch.setattr(academic_dependencies,"get_session_factory",lambda:c.sesiones)
    tokens=TokensJWT("clave-exclusiva-vinculacion-lab-"*3,"vinculacion-lab","cliente-lab")
    app=FastAPI(debug=False)
    lab=APIRouter(prefix="/lab/v1",route_class=RutaParticipacion)
    opciones={}
    @lab.post("/convocatorias/{convocatoria_id}/participacion")
    def provision(convocatoria_id:UUID,solicitud:SolicitudVinculacion,response:Response,
                  usuario=Depends(identity.obtener_estudiante_actual)):
        r=servicio(c,usuario=usuario,**opciones).obtener_o_crear(convocatoria_id=convocatoria_id,
            id_asignacion=solicitud.id_asignacion,codigo_acceso=solicitud.codigo_acceso.get_secret_value())
        response.status_code=201 if r.creada else 200
        return {"id_participacion":r.participacion.id_participacion,"creada":r.creada,"estado":r.participacion.estado}
    @lab.post("/convocatorias/{convocatoria_id}/intentos",response_model=IntentoRespuesta,status_code=201)
    def inicio(convocatoria_id:UUID,solicitud:SolicitudInicio,usuario=Depends(identity.obtener_estudiante_actual)):
        r=servicio(c,usuario=usuario,**opciones).iniciar_desde_convocatoria(convocatoria_id=convocatoria_id,
            id_asignacion=solicitud.id_asignacion,codigo_acceso=solicitud.codigo_acceso.get_secret_value(),
            id_consentimiento=solicitud.id_consentimiento,id_permiso_extra=solicitud.id_permiso_extra)
        return mapear_intento(r)
    app.include_router(lab);app.include_router(router)
    app.dependency_overrides[identity.obtener_fabrica_tokens]=lambda:lambda:tokens
    app.dependency_overrides[obtener_facade]=crear_dependencia_facade_8b(crear_sesion=c.sesiones,
        reloj=SimpleNamespace(ahora=lambda:c.ahora),fechas=FechasPersistencia(timezone.utc))
    with TestClient(app) as client:
        yield SimpleNamespace(c=c,client=client,tokens=tokens,opciones=opciones,
            base=f"/lab/v1/convocatorias/{c.datos['convocatoria_id']}",
            headers={"Authorization":"Bearer "+tokens.emitir(str(c.alumno),str(c.datos["convocatoria_id"]))},
            body=dict(id_asignacion=c.datos["id_asignacion"],codigo_acceso=c.codigo))


def test_http_recorrido_completo_sin_p_ni_i_precreados(http):
    h=http;c=h.c
    assert filas(c)==([],[])
    r=h.client.post(h.base+"/intentos",json=h.body|dict(id_consentimiento=c.consentimiento),headers=h.headers)
    assert r.status_code==201,r.text
    datos=r.json();ik=datos["id_intento"]
    p,i=filas(c)
    assert len(p)==len(i)==1 and datos["id_participacion"]==p[0]["id_participacion"]
    duplicado=h.client.post(h.base+"/intentos",json=h.body|dict(id_consentimiento=c.consentimiento),headers=h.headers)
    assert duplicado.status_code==409 and all(len(x)==1 for x in filas(c))
    for escena in (0,1):
        q=c.version.escenarios[escena].preguntas[0]
        ruta=f"/api/v1/attempts/{ik}/decisions/{q.id}"
        assert h.client.post(ruta,json={"id_opcion":str(q.opciones[0].id)},headers=h.headers).status_code==201
        cambio=h.client.put(ruta,json={"id_opcion":str(q.opciones[1].id)},headers=h.headers)
        assert cambio.status_code==409 and cambio.json()["detail"]["codigo"]=="RESPUESTA_INMUTABLE"
    progreso=h.client.get(f"/api/v1/attempts/{ik}/progress",headers=h.headers)
    assert progreso.status_code==200 and progreso.json()["respondidas"]==2
    assert progreso.json()["pendientes"]==[]
    for secreto in ("es_correcta","nota_final","justificacion",c.codigo):assert secreto not in progreso.text
    fin=h.client.post(f"/api/v1/attempts/{ik}/finish",headers=h.headers)
    assert fin.status_code==200 and fin.json()["estado"]=="FINALIZADO"
    assert filas(c)[1][0]["estado"]=="FINALIZADO"


def test_http_obtener_existente_e_iniciar(http):
    h=http
    a=h.client.post(h.base+"/participacion",json=h.body,headers=h.headers)
    b=h.client.post(h.base+"/participacion",json=h.body,headers=h.headers)
    assert a.status_code==201 and b.status_code==200
    assert a.json()["id_participacion"]==b.json()["id_participacion"]
    r=h.client.post(h.base+"/intentos",json=h.body|dict(id_consentimiento=h.c.consentimiento),headers=h.headers)
    assert r.status_code==201 and r.json()["id_participacion"]==a.json()["id_participacion"]


@pytest.mark.parametrize("actor",["anonimo","jwt_invalido","ajeno"])
def test_http_no_suplanta_identidad(http,actor):
    h=http;headers={}
    if actor=="jwt_invalido":headers={"Authorization":"Bearer invalido"}
    elif actor=="ajeno":
        otro=contexto(h.c.engine)
        headers={"Authorization":"Bearer "+h.tokens.emitir(str(otro.alumno),str(otro.datos["convocatoria_id"]))}
    r=h.client.post(h.base+"/intentos",json=h.body|dict(id_consentimiento=h.c.consentimiento),headers=headers)
    assert r.status_code==(403 if actor=="ajeno" else 401) and filas(h.c)==([],[])


def test_http_politica_faltante_y_campos_suplantados(http):
    h=http
    h.opciones["politica_vinculacion"]=None
    r=h.client.post(h.base+"/intentos",json=h.body|dict(id_consentimiento=h.c.consentimiento),headers=h.headers)
    assert r.status_code==503 and filas(h.c)==([],[])
    r=h.client.post(h.base+"/participacion",json=h.body|dict(id_estudiante=123,estado="aprobada"),headers=h.headers)
    assert r.status_code==422 and filas(h.c)==([],[])
    assert h.c.codigo not in r.text
