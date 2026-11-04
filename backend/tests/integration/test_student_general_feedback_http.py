"""RF-26: comentario general privado, JWT real y PostgreSQL desechable.

Reutiliza el recorrido HTTP 8B y su autoría real. Solo las políticas de inicio
y los datos académicos sembrados son de laboratorio; no sustituye autorización.
RF-27 usa el aviso INTERNA real; no anuncia una calificación disponible.
"""
from datetime import timedelta
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError

from app.modules.identity.api import dependencies as identity
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM as F
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C, NotificacionModel as N
from tests.integration.test_teacher_followup_http import (
    seguimiento, integracion, autor, pg_autoria, payload_valido, iniciar, escribir,
)  # noqa: F401 - fixtures compartidas de integración real


def lectura(h, headers=None, identificador=None):
    return h.client.get(
        f'/api/v1/identity/seguimiento/participaciones/{identificador or h.pk}/feedback',
        headers=h.headers if headers is None else headers,
    )


def cerrar(h):
    r=h.client.post(f'/api/v1/attempts/{h.ik}/finish',headers=h.headers)
    assert r.status_code==200,r.text
    return r


def snapshot(h):
    with h.sesiones() as s:
        return tuple(s.execute(select(F.__table__).where(F.id_participacion==h.pk)).all())


def test_titular_lee_actualizacion_confirmada_sin_escrituras_ni_notas(seguimiento):
    h=seguimiento
    assert escribir(h,'Valoración individual inicial').status_code==201
    cerrar(h)
    primera=lectura(h);assert primera.status_code==200,primera.text
    assert primera.headers['Cache-Control']=='no-store'
    assert primera.json()['id_participacion']==str(h.pk)
    assert primera.json()['id_docente']==str(h.a.propio)
    assert primera.json()['texto']=='Valoración individual inicial'
    assert set(primera.json())=={'id_participacion','id_docente','texto','fecha'}
    assert escribir(h,'Valoración individual revisada').status_code==201
    antes=snapshot(h)
    with h.sesiones() as s:
        avisos=s.scalar(select(func.count()).select_from(N))
    for _ in range(2):
        r=lectura(h);assert r.status_code==200,r.text
        assert r.json()['texto']=='Valoración individual revisada'
    assert snapshot(h)==antes and len(antes)==1
    assert h.codigo not in r.text and 'nota_final' not in r.text
    # La lectura no genera avisos y el aviso general no es CALIFICACION.
    with h.sesiones() as s:
        assert s.scalar(select(func.count()).select_from(N))==avisos
        assert s.scalar(select(func.count()).select_from(N).where(
            N.convocatoria_id==h.convocatoria,N.tipo=='CALIFICACION'))==0


@pytest.mark.parametrize('actor',['anonimo','invalido','otro_estudiante','docente_ajeno','docente_titular'])
def test_consulta_rechaza_otros_actores_sin_filtrar_comentario(seguimiento,actor):
    h=seguimiento;assert escribir(h,'Comentario reservado').status_code==201;cerrar(h)
    headers={'anonimo':{},'invalido':{'Authorization':'Bearer invalido'},
        'otro_estudiante':h.headers_ajeno,'docente_ajeno':h.a.ajeno,'docente_titular':h.a.headers}[actor]
    r=lectura(h,headers)
    assert r.status_code==(401 if actor in ('anonimo','invalido') else 403),r.text
    assert 'Comentario reservado' not in r.text
    assert r.headers['Cache-Control']=='no-store'


def test_intento_activo_no_expone_comentario_correccion_o_nota(seguimiento):
    h=seguimiento;assert escribir(h,'Solo visible al cerrar').status_code==201
    antes=snapshot(h)
    r=lectura(h);assert r.status_code==403,r.text
    assert all(x not in r.text for x in ('Solo visible al cerrar','Justificación','nota_final','es_correcta'))
    assert snapshot(h)==antes
    with h.sesiones() as s:assert s.get(I,h.ik).estado=='EN_CURSO'


def avisos(h):
    with h.sesiones() as s:
        return tuple(s.execute(select(N.__table__).where(
            N.convocatoria_id==h.convocatoria,N.tipo=='RETROALIMENTACION').order_by(N.creada_en,N.id)).all())


def test_aviso_persistido_destinatario_real_y_bandeja_privada(seguimiento):
    h=seguimiento;assert escribir(h,'Contenido privado del docente').status_code==201
    filas=avisos(h);assert len(filas)==1
    n=filas[0]
    assert n.destinatario_id==h.uuid_estudiante and n.convocatoria_id==h.convocatoria
    assert n.canal=='INTERNA' and n.estado=='PENDIENTE'
    assert 'Contenido privado del docente' not in n.mensaje
    assert 'calificación' not in n.mensaje and h.codigo not in n.mensaje
    url=f'/scheduling/notificaciones?destinatario_id={h.uuid_estudiante}'
    r=h.client.get(url,headers=h.headers);assert r.status_code==200,r.text
    assert str(n.id) in {x['id'] for x in r.json()}
    assert h.client.get(url,headers=h.headers_ajeno).status_code==403
    assert h.client.get(url,headers=h.a.ajeno).status_code==403
    # Recibir el aviso no permite saltarse las condiciones de visibilidad.
    assert lectura(h).status_code==403


def test_escrituras_identicas_concurrentes_y_reintento_no_duplican_aviso(seguimiento):
    h=seguimiento;barrera=Barrier(2)
    def guardar(_):
        barrera.wait(timeout=10)
        r=escribir(h,'Texto confirmado');assert r.status_code==201,r.text
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(guardar,range(2)))
    assert len(snapshot(h))==1 and len(avisos(h))==1
    assert escribir(h,'Texto confirmado').status_code==201
    assert len(avisos(h))==1
    assert escribir(h,'Cambio efectivo').status_code==201
    assert len(snapshot(h))==1 and len(avisos(h))==2


def test_fallo_del_aviso_revierte_ambas_escrituras_y_reintento_recupera(seguimiento,monkeypatch):
    from app.modules.participation.infrastructure import individual_feedback as modulo
    h=seguimiento;assert escribir(h,'Original').status_code==201
    antes,notificaciones=snapshot(h),avisos(h)
    original=modulo.crear_notificacion
    def fallar(*a,**kw):
        original(*a,**kw)
        raise RuntimeError('Fallo controlado después de flush, antes de commit')
    with monkeypatch.context() as m:
        m.setattr(modulo,'crear_notificacion',fallar)
        assert escribir(h,'Cambio no confirmado').status_code==500
    assert snapshot(h)==antes and avisos(h)==notificaciones
    assert escribir(h,'Cambio no confirmado').status_code==201
    assert len(avisos(h))==2
    cerrar(h)
    assert lectura(h).json()['texto']=='Cambio no confirmado'


def test_vencido_persistido_permite_comentario_sin_calificar(seguimiento):
    h=seguimiento;assert escribir(h,'Comentario de intento vencido').status_code==201
    instante=h.reloj.ahora()+timedelta(minutes=31)
    h.reloj.ahora=lambda:instante
    assert cerrar(h).json()['estado']=='VENCIDO'
    r=lectura(h);assert r.status_code==200,r.text
    assert r.json()['texto']=='Comentario de intento vencido' and 'nota_final' not in r.text


@pytest.mark.parametrize('contexto',[None,'otro'])
def test_contexto_de_convocatoria_no_se_elige_desde_la_url(seguimiento,contexto):
    h=seguimiento;assert escribir(h,'Privado').status_code==201;cerrar(h)
    tokens=h.client.app.dependency_overrides[identity.obtener_fabrica_tokens]()()
    jwt=tokens.emitir(str(h.estudiante),None if contexto is None else str(uuid4()))
    r=lectura(h,{'Authorization':'Bearer '+jwt})
    assert r.status_code==403 and 'Privado' not in r.text


@pytest.mark.parametrize('cambio',['retirada','inactivo','sin_rol_estudiante'])
def test_convocatoria_y_cuenta_se_revalidan_al_consultar(seguimiento,cambio):
    h=seguimiento;assert escribir(h,'Privado').status_code==201;cerrar(h)
    with h.sesiones.begin() as s:
        if cambio=='retirada':s.get(C,h.convocatoria).estado='RETIRADA'
        elif cambio=='inactivo':s.get(UsuarioORM,h.estudiante).activo=False
        else:s.get(UsuarioORM,h.estudiante).id_rol=1
    r=lectura(h)
    assert r.status_code==(401 if cambio=='inactivo' else 403),r.text
    assert 'Privado' not in r.text


@pytest.mark.parametrize('identificador',['2147483647','no-es-entero'])
def test_participacion_no_disponible_o_identificador_invalido(seguimiento,identificador):
    r=lectura(seguimiento,identificador=identificador)
    assert r.status_code==(403 if identificador.isdecimal() else 422),r.text


def test_sin_valoracion_no_la_crea_ni_la_inventa(seguimiento):
    h=seguimiento;cerrar(h)
    r=lectura(h);assert r.status_code==503,r.text  # Contrato interno preexistente.
    assert snapshot(h)==()


def test_fallo_sql_cierra_acceso_y_no_modifica_valoracion(seguimiento):
    h=seguimiento;assert escribir(h,'Confirmado').status_code==201;cerrar(h)
    antes=snapshot(h)
    def no_disponible():raise OperationalError('SELECT',{},Exception('fallo de laboratorio'))
    overrides=h.client.app.dependency_overrides
    anterior=overrides[identity.obtener_fabrica_sesiones_seguimiento]
    overrides[identity.obtener_fabrica_sesiones_seguimiento]=lambda:no_disponible
    try:
        r=lectura(h);assert r.status_code==503,r.text
        assert all(x not in r.text for x in ('Confirmado','SELECT','fallo de laboratorio'))
    finally:overrides[identity.obtener_fabrica_sesiones_seguimiento]=anterior
    assert snapshot(h)==antes
