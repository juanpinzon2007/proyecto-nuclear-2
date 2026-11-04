"""RF-15/26 HTTP con JWT, ámbito y PostgreSQL reales; no notas oficiales."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func, delete

from app.modules.identity.api.dependencies import obtener_fabrica_sesiones_seguimiento
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM as F
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.participation.infrastructure.individual_feedback import RepositorioFeedbackIndividual
from tests.integration.test_participation_http_composition import (
    integracion, autor, pg_autoria, payload_valido, iniciar,
)  # noqa: F401

BASE='/api/v1/identity/seguimiento'


@pytest.fixture
def seguimiento(integracion):
    h=integracion
    h.client.app.dependency_overrides[obtener_fabrica_sesiones_seguimiento]=lambda:h.sesiones
    with h.sesiones.begin() as s:
        s.add(IdentidadAcademicaORM(id_usuario=h.a.propio+1,sistema='SCHEDULING',id_academico=uuid4()))
    r=iniciar(h);assert r.status_code==201,r.text
    h.ik=r.json()['id_intento'];h.pk=r.json()['id_participacion']
    h.detalle=f'{BASE}/participaciones/{h.pk}'
    q=h.escenas[0]['preguntas'][0]
    assert h.client.post(f"/api/v1/attempts/{h.ik}/decisions/{q['id']}",headers=h.headers,
        json={'id_opcion':q['opciones'][0]['id']}).status_code==201
    return h


def escribir(h,texto,headers=None):
    return h.client.post(h.detalle+'/feedback',headers=headers or h.a.headers,json={'texto':texto})


def test_docente_consulta_solo_su_ambito_con_intentos_y_referencias_exactas(seguimiento):
    h=seguimiento
    casos=h.client.get(BASE+'/casos',headers=h.a.headers)
    assert casos.status_code==200,casos.text
    assert len(casos.json())==1
    caso=casos.json()[0]
    assert caso['version_caso_id']==str(h.version)
    listado=h.client.get(f"{BASE}/casos/{caso['id_caso']}/participaciones",headers=h.a.headers)
    assert listado.status_code==200 and len(listado.json())==1
    fila=listado.json()[0]
    assert (fila['id_participacion'],fila['id_estudiante'],fila['id_convocatoria'])==(str(h.pk),str(h.estudiante),str(h.convocatoria))
    detalle=h.client.get(h.detalle,headers=h.a.headers)
    assert detalle.status_code==200,detalle.text
    d=detalle.json()
    assert d['intentos'][0]['id_intento']==str(h.ik) and d['intentos'][0]['respondidas']==1
    assert d['respuestas'][0]['id_intento']==str(h.ik)
    assert d['respuestas'][0]['retroalimentacion'] is None
    assert d['version_caso_id']==str(h.version) and d['id_sesion']==str(h.sesion)
    assert 'nota_final' not in d and h.codigo not in detalle.text


def test_feedback_se_crea_edita_y_recupera_sin_duplicar_desde_otra_sesion(seguimiento):
    h=seguimiento
    primera=escribir(h,'Valoración inicial');assert primera.status_code==201,primera.text
    with h.sesiones() as s:
        pk=s.scalar(select(F.id_retroalimentacion).where(F.id_participacion==h.pk))
    segunda=escribir(h,'Valoración corregida');assert segunda.status_code==201,segunda.text
    assert segunda.json()['id_docente']==str(h.a.propio)
    with h.sesiones() as s:
        filas=s.scalars(select(F).where(F.id_participacion==h.pk)).all()
        assert len(filas)==1 and filas[0].id_retroalimentacion==pk
        assert filas[0].texto=='Valoración corregida' and filas[0].id_profesor==h.a.propio
        assert filas[0].fecha_registro is not None
    assert h.client.get(h.detalle,headers=h.a.headers).json()['feedback_docente']=='Valoración corregida'


@pytest.mark.parametrize('actor',['anonimo','invalido','estudiante','docente_ajeno'])
def test_no_se_consultan_ni_modifican_participaciones_ajenas(seguimiento,actor):
    h=seguimiento
    headers={'anonimo':{},'invalido':{'Authorization':'Bearer invalido'},
             'estudiante':h.headers,'docente_ajeno':h.a.ajeno}[actor]
    estado=401 if actor in ('anonimo','invalido') else 403
    assert h.client.get(h.detalle,headers=headers).status_code==estado
    assert h.client.post(h.detalle+'/feedback',headers=headers,json={'texto':'No autorizado'}).status_code==estado
    with h.sesiones() as s:assert s.scalar(select(func.count()).select_from(F).where(F.id_participacion==h.pk))==0


def test_listados_no_filtran_participaciones_de_otro_docente(seguimiento):
    h=seguimiento
    propio=h.client.get(BASE+'/casos',headers=h.a.headers).json()[0]
    assert h.client.get(BASE+'/casos',headers=h.a.ajeno).json()==[]
    assert h.client.get(f"{BASE}/casos/{propio['id_caso']}/participaciones",headers=h.a.ajeno).status_code==403
    assert h.client.get(f'{BASE}/casos/{uuid4()}/participaciones',headers=h.a.headers).status_code==403


@pytest.mark.parametrize('identificador',['2147483647','no-es-entero'])
def test_identificadores_no_disponibles_o_invalidos_se_rechazan(seguimiento,identificador):
    h=seguimiento;url=f'{BASE}/participaciones/{identificador}'
    esperado=403 if identificador.isdecimal() else 422
    assert h.client.get(url,headers=h.a.headers).status_code==esperado
    assert h.client.post(url+'/feedback',headers=h.a.headers,json={'texto':'Valoración'}).status_code==esperado


@pytest.mark.parametrize('texto',['','   ','a'*10001,'texto\x00invalido'])
def test_feedback_invalido_no_sustituye_el_confirmado(seguimiento,texto):
    h=seguimiento;assert escribir(h,'Confirmado').status_code==201
    assert escribir(h,texto).status_code==422
    assert h.client.get(h.detalle,headers=h.a.headers).json()['feedback_docente']=='Confirmado'


def test_error_tras_upsert_revierte_y_preserva_valoracion_anterior(seguimiento,monkeypatch):
    h=seguimiento;assert escribir(h,'Original').status_code==201
    original=RepositorioFeedbackIndividual.agregar
    def fallar(self,feedback):
        original(self,feedback)
        raise RuntimeError('Fallo controlado antes de commit')
    with monkeypatch.context() as m:
        m.setattr(RepositorioFeedbackIndividual,'agregar',fallar)
        assert escribir(h,'No confirmado').status_code==500
    assert h.client.get(h.detalle,headers=h.a.headers).json()['feedback_docente']=='Original'
    with h.sesiones() as s:assert s.scalar(select(F.texto).where(F.id_participacion==h.pk))=='Original'


def test_dos_actualizaciones_http_concurrentes_una_valoracion_vigente(seguimiento):
    h=seguimiento;barrera=Barrier(2)
    def actualizar(texto):
        barrera.wait(timeout=10);r=escribir(h,texto);assert r.status_code==201,r.text
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(actualizar,['Versión A','Versión B']))
    with h.sesiones() as s:
        filas=s.scalars(select(F).where(F.id_participacion==h.pk)).all()
        assert len(filas)==1 and filas[0].texto in ('Versión A','Versión B')
        assert filas[0].id_profesor==h.a.propio


def test_detalle_cerrado_usa_explicacion_historica_y_no_abre_notas_reportes(seguimiento):
    h=seguimiento
    assert h.client.post(f'/api/v1/attempts/{h.ik}/finish',headers=h.headers).status_code==200
    assert h.client.post(f'/api/v1/cases/{h.version}/archive',headers=h.a.headers).status_code==200
    r=h.client.get(h.detalle,headers=h.a.headers);assert r.status_code==200,r.text
    assert r.json()['respuestas'][0]['retroalimentacion']=='Justificación teórica.'
    assert r.json()['intentos'][0]['estado']=='FINALIZADO'
    assert 'nota_final' not in r.text
    assert h.client.get(f'{BASE}/sesiones/{h.sesion}/reporte',headers=h.a.headers).status_code==503
    assert h.client.get(h.detalle,headers=h.headers).status_code==403


@pytest.mark.parametrize('cambio',['inactivo','rol','asociacion_ausente','asociacion_ambigua'])
def test_revalidacion_actual_del_docente_y_sus_asociaciones(seguimiento,cambio):
    h=seguimiento
    with h.sesiones.begin() as s:
        if cambio=='inactivo':s.get(UsuarioORM,h.a.propio).activo=False
        elif cambio=='rol':s.get(UsuarioORM,h.a.propio).id_rol=2
        elif cambio=='asociacion_ausente':s.execute(delete(IdentidadAcademicaORM).where(
            IdentidadAcademicaORM.id_usuario==h.a.propio,IdentidadAcademicaORM.sistema=='SCHEDULING'))
        else:s.add(IdentidadAcademicaORM(id_usuario=h.a.propio,sistema='SCHEDULING',id_academico=uuid4()))
    esperado={'inactivo':401,'rol':403,'asociacion_ausente':403,'asociacion_ambigua':503}[cambio]
    assert h.client.get(h.detalle,headers=h.a.headers).status_code==esperado
    assert escribir(h,'Rechazado').status_code==esperado
