"""MAIN/PG17 con archivo de decisión LAB, sin overrides de políticas de inicio.

La aprobación de consentimiento y reloj siguen inyectados SOLO LAB hasta la
composición del proveedor firmado. Settings se aporta explícitamente al módulo
para permitir integrar este cambio antes del commit propietario de configuración.
"""
from types import SimpleNamespace

import pytest
import sqlalchemy as sa

from app.main import app
from app.modules.participation.api import start_dependencies
from app.modules.participation.application.errors import ReglaPendiente
from app.modules.participation.infrastructure.models import IntentoModel as I, ParticipacionModel as P
from app.modules.scheduling.infrastructure.models import EventoAuditoriaModel as E
from tests.integration.test_main_start_composition import (
    componer_laboratorio, aceptar_main, iniciar_main,
    test_inicio_concurrente_y_rollback_real as comprobar_concurrencia,
    test_repeticion_permiso_real_consumido_una_vez as comprobar_permiso,
)
from tests.integration.test_lab_student_journey import recorrido_lab, pg_autoria, payload_valido, cantidades
from tests.unit.participation.test_start_policy_file import archivo_politica, decision_lab


@pytest.fixture
def main_archivo(recorrido_lab, tmp_path, monkeypatch):
    h=recorrido_lab
    componer_laboratorio(h)
    for proveedor in (start_dependencies.obtener_politica_inicio,start_dependencies.obtener_politica_vinculacion):
        app.dependency_overrides.pop(proveedor)
    archivo,huella=archivo_politica(tmp_path,decision_lab(h.documento.referencia))
    configuracion=SimpleNamespace(participation_start_policy_file=archivo,
        participation_start_policy_sha256=huella,academic_runtime_scope="LABORATORIO")
    monkeypatch.setattr(start_dependencies,"get_settings",lambda:configuracion)
    h.configuracion_inicio=configuracion
    return h


def test_inicio_archivo_real_guarda_estado_y_vinculos(main_archivo):
    h=main_archivo;a,_=aceptar_main(h);cid=a.json()["id_consentimiento"]
    r=iniciar_main(h,cid);assert r.status_code==201,r.text
    with h.sesiones() as s:
        i=s.get(I,r.json()["id_intento"]);p=s.get(P,i.id_participacion)
        assert p.estado=="pendiente" and i.estado=="EN_CURSO"
        assert p.id_consentimiento==i.id_consentimiento==cid
    assert iniciar_main(h,cid).status_code==409
    with h.sesiones() as s:
        eventos=s.scalars(sa.select(E).where(E.sesion_id==h.sesion,E.tipo=="INICIO_INTENTO_POLITICA")).all()
        assert len(eventos)==1
        import json
        evidencia=json.loads(eventos[0].descripcion)
        assert evidencia["id_intento"]==i.id_intento and evidencia["id_participacion"]==p.id_participacion
        assert evidencia["politica_sha256"]==h.configuracion_inicio.participation_start_policy_sha256
        assert evidencia["politica_version"]=="1" and evidencia["politica_ambito"]=="LABORATORIO"


@pytest.mark.parametrize("defecto",["hash","scope","archivo"])
def test_configuracion_invalida_cierra_main_sin_escrituras(main_archivo,defecto):
    h=main_archivo;a,_=aceptar_main(h)
    if defecto=="hash":h.configuracion_inicio.participation_start_policy_sha256="0"*64
    elif defecto=="scope":h.configuracion_inicio.academic_runtime_scope="PRODUCCION"
    else:h.configuracion_inicio.participation_start_policy_file=None
    assert iniciar_main(h,a.json()["id_consentimiento"]).status_code==503
    assert cantidades(h)==([],[])


def test_concurrencia_y_rollback_main_archivo(main_archivo):
    comprobar_concurrencia(main_archivo)
    with main_archivo.sesiones() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(E).where(
            E.sesion_id==main_archivo.sesion,E.tipo=="INICIO_INTENTO_POLITICA"))==1


def test_permiso_nativo_main_archivo(main_archivo):
    comprobar_permiso(main_archivo)


@pytest.mark.parametrize("simular_defecto_anterior",[True,False])
def test_revalidacion_aprobacion_antes_de_intento_revierte_participacion(main_archivo,monkeypatch,simular_defecto_anterior):
    h=main_archivo;a,_=aceptar_main(h);cid=a.json()["id_consentimiento"]
    from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
    original=FuenteConsentimientoSQLAlchemy.vigente
    if simular_defecto_anterior:
        from app.modules.participation.infrastructure.start import IdentityInicioSQLAlchemy
        constructor=IdentityInicioSQLAlchemy.__init__
        def sin_fabrica(self,alcance,**kw):
            kw.pop("crear_fuente_consentimiento",None)
            constructor(self,alcance,**kw)
        monkeypatch.setattr(IdentityInicioSQLAlchemy,"__init__",sin_fabrica)
    llamadas=[]
    def vigente(self,**kw):
        llamadas.append(self.politica_aprobacion)
        # Primera consulta del coordinador permite P, segunda es Identity antes
        # de I. Toda reconstrucción de fuente debe conservar aprobación vigente.
        if len(llamadas)==2 and self.politica_aprobacion is not None:
            from app.modules.identity.domain.errors import IntegracionPendiente
            raise IntegracionPendiente()
        return original(self,**kw)
    monkeypatch.setattr(FuenteConsentimientoSQLAlchemy,"vigente",vigente)
    r=iniciar_main(h,cid)
    assert len(llamadas)==2 and llamadas[0] is not None
    if simular_defecto_anterior:
        assert r.status_code==201 and llamadas[1] is None
        assert tuple(map(len,cantidades(h)))==(1,1)
    else:
        assert r.status_code==503 and llamadas[1] is not None
        assert cantidades(h)==([],[])


def test_error_auditoria_revierte_participacion_intento_y_evento(main_archivo):
    h=main_archivo;a,_=aceptar_main(h);cid=a.json()["id_consentimiento"]
    def fallo(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith("insert into evento_auditoria"):
            conn.exec_driver_sql("SELECT 1/0")
    from app.db.session import get_engine
    engines={h.engine,get_engine()}
    for engine in engines:sa.event.listen(engine,"after_cursor_execute",fallo)
    try:assert iniciar_main(h,cid).status_code==500
    finally:
        for engine in engines:sa.event.remove(engine,"after_cursor_execute",fallo)
    assert cantidades(h)==([],[])
    with h.sesiones() as s:
        assert not s.scalars(sa.select(E).where(E.sesion_id==h.sesion,E.tipo=="INICIO_INTENTO_POLITICA")).all()
