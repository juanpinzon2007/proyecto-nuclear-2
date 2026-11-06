"""Consentimiento/inicio SQL PG17; definición SINTÉTICA, no documento oficial."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta, timezone
from threading import Barrier
from types import SimpleNamespace

import pytest
from sqlalchemy import select, event, func

from app.modules.identity.application.consent import DocumentoConsentimiento
from app.modules.identity.infrastructure.consent import ServicioConsentimientoSQLAlchemy
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C
from app.modules.identity.domain.errors import AccesoDenegado as IdentityDenegado, IntegracionPendiente
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from tests.integration.consent_support import FuenteConsentimientoLaboratorio
from tests.integration.test_participation_persistence import contexto
from tests.integration.test_participation_provision import (
    convocada,pg_grafo,servicio,argumentos,iniciar,filas,http,  # noqa: F401
)


@contextmanager
def observar_p(c):
    instrucciones=[]
    def sql(conn,cursor,statement,params,context,many):
        if statement.lstrip().lower().startswith('insert into participacion'):
            instrucciones.append('INSERT P')
    event.listen(c.engine,'before_cursor_execute',sql)
    try: yield instrucciones
    finally: event.remove(c.engine,'before_cursor_execute',sql)


def interno(c,s,fuente):
    return ServicioConsentimientoSQLAlchemy(s,fuente=fuente,fechas=FechasPersistencia(timezone.utc),
        reloj=SimpleNamespace(ahora=lambda:c.ahora))


@pytest.mark.parametrize('modo',['provision','inicio'])
@pytest.mark.parametrize('problema',['ausente','antigua','revocada','futura','fuente_ausente'])
def test_consentimiento_rechazado_antes_de_cualquier_insert_p(convocada,modo,problema):
    c=convocada; fuente=FuenteConsentimientoLaboratorio()
    with c.sesiones.begin() as s:
        fila=s.get(C,c.consentimiento)
        if problema=='ausente':s.delete(fila)
        elif problema=='antigua':fila.version_texto='otra-version-LAB'
        elif problema=='revocada':fila.fecha_revocacion=fila.fecha_aceptacion
        elif problema=='futura':fila.fecha_aceptacion=(c.ahora+timedelta(days=1)).replace(tzinfo=None)
    if problema=='fuente_ausente':fuente=None
    with observar_p(c) as sql, pytest.raises((AccesoDenegado,ReglaPendiente)):
        sv=servicio(c,fuente_consentimiento=fuente)
        if modo=='inicio':sv.iniciar_desde_convocatoria(**argumentos(c),id_consentimiento=c.consentimiento)
        else:sv.obtener_o_crear(**argumentos(c))
    assert sql==[] and filas(c)==([],[])


def test_politica_inicio_rechazada_antes_de_insert_p(convocada):
    c=convocada
    class Denegar:
        def autorizar(self,condiciones):
            assert condiciones.id_participacion is None
            raise AccesoDenegado('Rechazo explícito LAB')
    with observar_p(c) as sql, pytest.raises(AccesoDenegado):iniciar(c,politica_inicio=Denegar())
    assert sql==[] and filas(c)==([],[])


def test_aceptacion_explicita_persistida_y_recuperada_en_otra_session(convocada):
    c=convocada;fuente=FuenteConsentimientoLaboratorio()
    fuente.publicar(DocumentoConsentimiento('LAB-nueva-1','documento-LAB','2','Texto nuevo SOLO LAB.',True))
    d=fuente.actual
    with c.sesiones.begin() as s:
        pk=interno(c,s,fuente).aceptar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],
            referencia_presentada=d.referencia,huella_presentada=d.huella,acepta=True)
    with c.sesiones() as s:
        assert interno(c,s,fuente).consultar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],id_consentimiento=pk)==pk
        fila=s.get(C,pk)
        assert fila.id_estudiante==c.alumno and fila.version_texto==d.referencia
        assert fila.fecha_aceptacion==c.ahora.replace(tzinfo=None)
    assert filas(c)==([],[])


@pytest.mark.parametrize('cambio',[{'acepta':False},{'acepta':1},{'referencia_presentada':'ajena'}, {'huella_presentada':'incorrecta'}])
def test_aceptacion_no_es_implicita_ni_version_elegida_por_cliente(convocada,cambio):
    c=convocada;f=FuenteConsentimientoLaboratorio();d=f.actual
    with c.sesiones.begin() as s,pytest.raises(IdentityDenegado):
        interno(c,s,f).aceptar(**(dict(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],
            referencia_presentada=d.referencia,huella_presentada=d.huella,acepta=True)|cambio))
    assert filas(c)==([],[])


def test_version_nueva_exige_nueva_aceptacion_sin_reescribir_la_anterior(convocada):
    c=convocada;f=FuenteConsentimientoLaboratorio()
    f.publicar(DocumentoConsentimiento('LAB-version-2','documento-LAB','2','Segunda definición LAB.',True))
    with c.sesiones() as s,pytest.raises(IdentityDenegado):
        interno(c,s,f).consultar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],id_consentimiento=c.consentimiento)
    with c.sesiones() as s:assert s.get(C,c.consentimiento).version_texto=='sintetico'


def test_consulta_ajena_no_acredita_aceptacion(convocada):
    c=convocada;otro=contexto(c.engine)
    with c.sesiones() as s,pytest.raises(IdentityDenegado):
        interno(c,s,FuenteConsentimientoLaboratorio()).consultar(usuario=c.usuario,
            id_asignacion=c.datos['id_asignacion'],id_consentimiento=otro.consentimiento)


def test_guard_no_permite_revocar_con_intento_en_curso(convocada):
    c=convocada;iniciar(c)
    with c.sesiones() as s,pytest.raises(IdentityDenegado):
        interno(c,s,FuenteConsentimientoLaboratorio()).comprobar_revocacion(usuario=c.usuario,id_consentimiento=c.consentimiento)
    with c.sesiones() as s:assert s.get(C,c.consentimiento).fecha_revocacion is None


def test_rollback_aceptacion_no_deja_fila(convocada):
    c=convocada;f=FuenteConsentimientoLaboratorio()
    f.publicar(DocumentoConsentimiento('LAB-rollback','doc-LAB','1','Texto LAB rollback.',True));d=f.actual
    with pytest.raises(RuntimeError):
        with c.sesiones.begin() as s:
            interno(c,s,f).aceptar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],
                referencia_presentada=d.referencia,huella_presentada=d.huella,acepta=True)
            raise RuntimeError('Fallo LAB después de flush')
    with c.sesiones() as s:assert s.scalar(select(func.count()).select_from(C).where(C.version_texto==d.referencia))==0


def test_dos_aceptaciones_concurrentes_no_duplican_registro(convocada):
    c=convocada;f=FuenteConsentimientoLaboratorio()
    f.publicar(DocumentoConsentimiento('LAB-concurrente','doc-LAB','1','Texto LAB concurrente.',True));d=f.actual
    barrera=Barrier(2)
    def aceptar(_):
        barrera.wait(timeout=10)
        try:
            with c.sesiones.begin() as s:
                interno(c,s,f).aceptar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],
                    referencia_presentada=d.referencia,huella_presentada=d.huella,acepta=True)
            return 'creada'
        except IntegracionPendiente:return 'sin-duplicar'
    with ThreadPoolExecutor(max_workers=2) as pool:resultados=list(pool.map(aceptar,range(2)))
    assert sorted(resultados)==['creada','sin-duplicar']
    with c.sesiones() as s:assert s.scalar(select(func.count()).select_from(C).where(C.version_texto==d.referencia))==1


def test_http_consentimiento_ajeno_no_inserta_p_ni_i(http):
    h=http;c=h.c;otro=contexto(c.engine)
    with observar_p(c) as sql:
        r=h.client.post(h.base+'/intentos',headers=h.headers,
            json=h.body|{'id_consentimiento':otro.consentimiento})
    assert r.status_code==403 and sql==[] and filas(c)==([],[])


def test_documento_sin_fuente_no_se_inventa(convocada):
    c=convocada
    with c.sesiones() as s,pytest.raises(IntegracionPendiente):
        interno(c,s,None).aceptar(usuario=c.usuario,id_asignacion=c.datos['id_asignacion'],
            referencia_presentada='sin-documento',huella_presentada='sin-huella',acepta=True)


def test_fuente_lab_no_reutiliza_referencia_para_contenido_diferente():
    f=FuenteConsentimientoLaboratorio()
    with pytest.raises(IntegracionPendiente):f.publicar(replace(f.actual,texto='Otro contenido'))
