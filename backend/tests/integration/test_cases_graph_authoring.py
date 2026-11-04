"""Autoría HTTP/JWT/SQL real; solo PostgreSQL nuevo y desechable.

Los únicos datos sembrados son cuentas, roles, permiso y asociaciones explícitas
de laboratorio. Contenido, UUID de escenas/opciones, grafo y publicación se
obtienen exclusivamente por la API, sin overrides de autenticación/autorización.
"""
from copy import deepcopy
from itertools import count
from types import SimpleNamespace
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from alembic import command
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.modules.cases.api.router import router
from app.modules.cases.infrastructure.models import VersionCasoModel
from app.modules.identity.api import dependencies as identity, academic_dependencies
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM, PermisoORM, RolPermisoORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.participation.application.dto import SeleccionDecision
from app.modules.participation.infrastructure.cases_route import RecorridoCasesSQLAlchemy
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic
from tests.integration.cases.conftest import payload_valido  # noqa: F401

URL = "/api/v1/cases"
IDS = count(2000, 3)


@pytest.fixture(scope="module")
def pg_autoria():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as c:
            command.upgrade(config_alembic(c), "head")
        sesiones = sessionmaker(engine, expire_on_commit=False)
        with sesiones.begin() as s:
            s.add_all([RolORM(id_rol=1, nombre="DOCENTE"), RolORM(id_rol=2, nombre="ESTUDIANTE")])
            s.add(PermisoORM(id_permiso=1, codigo="CREAR_CASOS", descripcion="Laboratorio de autoría"))
        yield sesiones


@pytest.fixture
def autor(pg_autoria, payload_valido):
    sesiones = pg_autoria
    propio = next(IDS)
    with sesiones.begin() as s:
        if s.get(RolPermisoORM, (1, 1)) is None:
            s.add(RolPermisoORM(id_rol=1, id_permiso=1))
        for i in (propio, propio+1, propio+2):
            s.add(UsuarioORM(id_usuario=i, id_rol=2 if i==propio+2 else 1,
                nombre="Cuenta sintética", correo=f"autor{i}@universidad.test", clave_hash="sin-login-por-clave"))
            s.flush()
            s.add(IdentidadAcademicaORM(id_usuario=i, sistema="CASES", id_academico=uuid4()))
    tokens = TokensJWT("clave-exclusiva-autoria-http-laboratorio-"*2, "cases-lab", "cases-lab")
    app = FastAPI()
    app.include_router(router)

    def db():
        with sesiones() as s:
            yield s

    def usuarios():
        with sesiones() as s:
            yield lambda: RepositorioUsuariosSQLAlchemy(s)

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[identity.obtener_fabrica_tokens] = lambda: lambda: tokens
    app.dependency_overrides[identity.obtener_fabrica_usuarios] = usuarios
    app.dependency_overrides[academic_dependencies.obtener_fabrica_sesiones_academicas] = lambda: sesiones
    payload = deepcopy(payload_valido)
    for n in (2, 3):
        e = deepcopy(payload["scenarios"][0]); e["orden"] = n
        e["contextoSituacional"] = f"Rama sintética {n}"
        payload["scenarios"].append(e)
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, sesiones=sesiones, propio=propio, payload=payload,
            headers={"Authorization":"Bearer "+tokens.emitir(str(propio))},
            ajeno={"Authorization":"Bearer "+tokens.emitir(str(propio+1))},
            estudiante={"Authorization":"Bearer "+tokens.emitir(str(propio+2))})


def crear(a, payload=None):
    r = a.client.post(URL, headers=a.headers, json=payload or a.payload)
    assert r.status_code == 201, r.text
    vid = r.json()["version_id"]
    detalle = a.client.get(f"{URL}/{vid}", headers=a.headers)
    assert detalle.status_code == 200
    escenas = sorted(detalle.json()["escenarios"], key=lambda e:e["orden"])
    opciones = [sorted(e["preguntas"][0]["opciones"], key=lambda o:o["orden"]) for e in escenas]
    body = {"escenario_inicial_id":escenas[0]["id"],"transiciones":[
        {"opcion_id":o["id"],"tipo":"ESCENA","destino_id":escenas[i+1]["id"]}
        for i,o in enumerate(opciones[0])]+[
        {"opcion_id":o["id"],"tipo":"FIN"} for os in opciones[1:] for o in os]}
    return vid, body, escenas


def configurar(a, vid, body):
    return a.client.put(f"{URL}/{vid}/graph", headers=a.headers, json=body)


def test_http_crear_configurar_publicar_y_consumir_misma_version(autor):
    a=autor;vid,body,escenas=crear(a)
    assert configurar(a,vid,body).status_code==200
    grafo=a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()
    assert a.client.post(f"{URL}/{vid}/publish",headers=a.headers).status_code==200
    # Otra Session, adaptador REAL de Participation; sin proveedor de ruta falso.
    with a.sesiones() as s:
        adapter=RecorridoCasesSQLAlchemy(lambda:s)
        ruta=adapter.obtener(version_id=UUID(vid),selecciones=())
        q0=UUID(escenas[0]["preguntas"][0]["id"])
        assert ruta.disponible and ruta.decisiones==(q0,) and not ruta.total_conocido
        elegida=body["transiciones"][1]
        q2=UUID(escenas[2]["preguntas"][0]["id"])
        selecciones=(SeleccionDecision(q0,UUID(elegida["opcion_id"])),)
        siguiente=adapter.obtener(version_id=UUID(vid),selecciones=selecciones)
        assert siguiente.decisiones==(q0,q2) and not siguiente.total_conocido
        fin=selecciones+(SeleccionDecision(q2,UUID(escenas[2]["preguntas"][0]["opciones"][0]["id"])),)
        assert adapter.obtener(version_id=UUID(vid),selecciones=fin).total_conocido
    assert configurar(a,vid,body).status_code==400
    assert a.client.put(f"{URL}/{vid}",headers=a.headers,json=a.payload).status_code==400
    assert a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()==grafo
    # Crear otro caso por HTTP no modifica ni sustituye el grafo publicado.
    crear(a)
    assert a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()==grafo


@pytest.mark.parametrize("actor",["anonimo","token_invalido","estudiante","sin_permiso","sin_asociacion"])
def test_autoria_no_concede_acceso_sin_identidad_rol_permiso_y_vinculo(autor,actor):
    a=autor;vid,body,_=crear(a)
    headers=a.headers
    if actor=="anonimo": headers={"X-Docente-Id":str(uuid4())}
    elif actor=="token_invalido": headers={"Authorization":"Bearer invalido"}
    elif actor=="estudiante":headers=a.estudiante
    elif actor=="sin_permiso":
        with a.sesiones.begin() as s:s.execute(delete(RolPermisoORM).where(RolPermisoORM.id_rol==1))
    else:
        with a.sesiones.begin() as s:s.execute(delete(IdentidadAcademicaORM).where(IdentidadAcademicaORM.id_usuario==a.propio))
    for metodo,url,kw in [("post",URL,{"json":a.payload}),
                          ("put",f"{URL}/{vid}/graph",{"json":body}),
                          ("post",f"{URL}/{vid}/publish",{})]:
        r=getattr(a.client,metodo)(url,headers=headers,**kw)
        assert r.status_code==(401 if actor in ("anonimo","token_invalido") else 403)
    with a.sesiones() as s:assert s.get(VersionCasoModel,UUID(vid)).estado.value=="BORRADOR"


def test_docente_ajeno_no_consulta_configura_o_publica(autor):
    a=autor;vid,body,_=crear(a)
    for method,suffix,kw in [("get","/graph",{}),("put","/graph",{"json":body}),("post","/publish",{})]:
        r=getattr(a.client,method)(f"{URL}/{vid}{suffix}",headers=a.ajeno,**kw)
        assert r.status_code==404


@pytest.mark.parametrize("referencia",["inicial","opcion","destino"])
@pytest.mark.parametrize("origen",["inexistente","otra_version"])
def test_referencias_inexistentes_o_cruzadas_no_dejan_escrituras(autor,referencia,origen):
    a=autor;vid,body,_=crear(a)
    assert configurar(a,vid,body).status_code==200
    previo=a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()
    _,otro,escenas=crear(a)
    dato=str(uuid4()) if origen=="inexistente" else {
        "inicial":escenas[0]["id"],"opcion":otro["transiciones"][0]["opcion_id"],"destino":escenas[1]["id"]}[referencia]
    malo=deepcopy(body)
    if referencia=="inicial":malo["escenario_inicial_id"]=dato
    else:malo["transiciones"][0]["opcion_id" if referencia=="opcion" else "destino_id"]=dato
    assert configurar(a,vid,malo).status_code==422
    assert a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()==previo


@pytest.mark.parametrize("problema",["ciclo","transicion_omitida","opcion_duplicada","fin_con_destino","escena_sin_destino"])
def test_configuracion_no_ejecutable_o_incoherente_revierte(autor,problema):
    a=autor;vid,body,_=crear(a)
    assert configurar(a,vid,body).status_code==200
    previo=a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()
    malo=deepcopy(body)
    if problema=="ciclo":malo["transiciones"][0]["destino_id"]=body["escenario_inicial_id"]
    elif problema=="transicion_omitida":malo["transiciones"].pop(0)
    elif problema=="opcion_duplicada":malo["transiciones"].append(malo["transiciones"][0])
    elif problema=="fin_con_destino":malo["transiciones"][0]["tipo"]="FIN"
    else:malo["transiciones"][0].pop("destino_id")
    assert configurar(a,vid,malo).status_code==422
    assert a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()==previo


def test_multipregunta_y_publicacion_sin_grafo_se_rechazan(autor):
    a=autor;payload=deepcopy(a.payload)
    q=deepcopy(payload["scenarios"][0]["questions"][0]);q["orden"]=2
    payload["scenarios"][0]["questions"].append(q)
    vid,body,_=crear(a,payload)
    assert configurar(a,vid,body).status_code==422
    assert a.client.post(f"{URL}/{vid}/publish",headers=a.headers).status_code==422
    with a.sesiones() as s:assert s.get(VersionCasoModel,UUID(vid)).estado.value=="BORRADOR"


def test_dos_configuraciones_concurrentes_se_conservan_completas(autor):
    a=autor;vid,body,_=crear(a)
    otro=deepcopy(body)
    otro["transiciones"][0]["destino_id"],otro["transiciones"][1]["destino_id"]=body["transiciones"][1]["destino_id"],body["transiciones"][0]["destino_id"]
    barrera=Barrier(2)
    def guardar(b):
        barrera.wait(timeout=10)
        r=configurar(a,vid,b);assert r.status_code==200,r.text
        return r.json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados=list(pool.map(guardar,[body,otro]))
    final=a.client.get(f"{URL}/{vid}/graph",headers=a.headers).json()
    assert final in resultados
    assert a.client.post(f"{URL}/{vid}/publish",headers=a.headers).status_code==200
