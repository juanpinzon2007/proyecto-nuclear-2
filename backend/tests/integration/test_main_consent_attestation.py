"""Main con JWT, titularidad y consentimiento SQL reales en PostgreSQL17 desechable."""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.modules.identity.api import consent_dependencies as deps, dependencies as identity
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
from app.modules.identity.infrastructure.models import UsuarioORM
from tests.integration.test_consent_http import app_para
from tests.integration.test_consent_version_persistence import publicar, elegir
from tests.integration.test_participation_provision import convocada, pg_grafo  # noqa: F401
from tests.unit.identity.test_consent_approval_attestation import escribir_paquete


@pytest.fixture
def principal(convocada, tmp_path, monkeypatch):
    from app.main import app
    c=convocada
    with c.sesiones.begin() as db:
        c.documento=publicar(c,db);elegir(c,db,c.documento)
        d=FuenteConsentimientoSQLAlchemy(db).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
        correo=db.get(UsuarioORM,c.alumno).correo
    c.config=escribir_paquete(tmp_path,[d],c.datos['id_asignacion'],c.ahora)
    c.config.participation_timestamp_zone='UTC'
    monkeypatch.setattr(deps,'get_settings',lambda:c.config)
    lab,c.tokens=app_para(c)
    anterior=dict(app.dependency_overrides)
    app.dependency_overrides.update(lab.dependency_overrides)
    app.dependency_overrides[identity.obtener_fabrica_sesiones_seguimiento]=lambda:c.sesiones
    app.dependency_overrides[deps.obtener_reloj_consentimiento]=lambda:SimpleNamespace(ahora=lambda:c.ahora)
    try:
        with TestClient(app,raise_server_exceptions=False) as client:
            login=client.post('/api/v1/identity/auth/estudiantes',json={'correo':correo,'codigo_convocatoria':c.codigo})
            assert login.status_code==200
            c.headers={'Authorization':'Bearer '+login.json()['access_token']}
            c.client=client
            c.url=(f'/api/v1/identity/convocatorias/{c.datos["convocatoria_id"]}'
                f'/asignaciones/{c.datos["id_asignacion"]}/consentimiento')
            c.tmp_path=tmp_path
            yield c
    finally:
        app.dependency_overrides.clear();app.dependency_overrides.update(anterior)


def datos(c):
    d=c.client.get(c.url,headers=c.headers)
    assert d.status_code==200
    return {k:d.json()[k] for k in ('id_version_documento','referencia','huella')} | {'acepta':True}


def test_main_consulta_acepta_renueva_y_preserva_historia(principal):
    c=principal;anterior=datos(c)
    assert c.client.get(c.url+'/aceptacion',headers=c.headers).json()['aceptado'] is False
    r=c.client.post(c.url+'/aceptacion',headers=c.headers,json=anterior)
    assert r.status_code==200 and r.json()['aceptado'] is True
    assert c.client.post(c.url+'/aceptacion',headers=c.headers,json=anterior).json()==r.json()
    with c.sesiones.begin() as db:
        nuevo=publicar(c,db,'2');elegir(c,db,nuevo)
        d=FuenteConsentimientoSQLAlchemy(db).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
    config=escribir_paquete(c.tmp_path,[d],c.datos['id_asignacion'],c.ahora)
    config.participation_timestamp_zone='UTC';c.config=config
    assert c.client.get(c.url+'/aceptacion',headers=c.headers).json()['aceptado'] is False
    assert c.client.post(c.url+'/aceptacion',headers=c.headers,json=anterior).status_code==409
    assert c.client.post(c.url+'/aceptacion',headers=c.headers,json=datos(c)).status_code==200
    with c.sesiones() as db:
        assert db.get(C,r.json()['id_consentimiento']).id_version_documento==c.documento
        assert len(db.scalars(select(C).where(C.id_estudiante==c.alumno,C.id_version_documento.is_not(None))).all())==2


@pytest.mark.parametrize('problema',['sin_config','scope','expirado','evidencia','asignacion'])
def test_main_cierra_y_jwt_precede_config(principal,problema):
    c=principal
    with c.sesiones() as db:
        d=FuenteConsentimientoSQLAlchemy(db).vigente(id_asignacion=c.datos['id_asignacion'],ahora=c.ahora)
    if problema=='sin_config':c.config.identity_consent_approval_manifest=None
    elif problema=='scope':c.config.academic_runtime_scope='PRODUCCION'
    else:
        if problema=='evidencia':d=replace(d,sha256_aprobacion='0'*64)
        config=escribir_paquete(c.tmp_path,[d],c.datos['id_asignacion']+1 if problema=='asignacion' else c.datos['id_asignacion'],
            c.ahora-timedelta(days=1) if problema=='expirado' else c.ahora)
        config.participation_timestamp_zone='UTC';c.config=config
    assert c.client.get(c.url).status_code==401
    assert c.client.get(c.url,headers={'Authorization':'Bearer invalido'}).status_code==401
    r=c.client.get(c.url,headers=c.headers)
    assert r.status_code==503 and r.headers['Cache-Control']=='no-store'
    with c.sesiones() as db:
        assert db.scalars(select(C).where(C.id_estudiante==c.alumno,C.id_version_documento.is_not(None))).all()==[]


def test_main_titularidad_se_revalida_con_proveedor_real(principal):
    c=principal
    headers={'Authorization':'Bearer '+c.tokens.emitir(str(c.docente))}
    assert c.client.get(c.url,headers=headers).status_code==403
    from tests.integration.test_participation_persistence import contexto
    otro=contexto(c.engine)
    headers={'Authorization':'Bearer '+c.tokens.emitir(str(otro.alumno),str(c.datos['convocatoria_id']))}
    assert c.client.get(c.url,headers=headers).status_code==403
