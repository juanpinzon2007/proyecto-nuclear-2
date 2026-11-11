"""Decisión explícita del servidor, documentos y estados exclusivamente LAB."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.application.start_policy import CondicionesInicioIntento
from app.modules.participation.infrastructure.start_policy_file import cargar_politicas_inicio


def decision_lab(referencia="LAB-consent-1"):
    return dict(id="inicio-MVP-LAB", version="1", ambito="LABORATORIO",
        referencia_decision="Decisión MVP estado P pendiente, prueba LAB",
        aprobacion="LABORATORIO_PENDIENTE", estado_inicial_participacion="pendiente",
        estados_asignacion=["programada"], intentos_base=1, usos_permiso_extra=1,
        referencias_consentimiento=[referencia], incluye_limite_ingreso=False)


def archivo_politica(tmp_path, datos=None):
    original=json.dumps(datos or decision_lab(),sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()
    archivo=tmp_path/"inicio-lab.json";archivo.write_bytes(original)
    return archivo,sha256(original).hexdigest()


def condiciones():
    ahora=datetime.now(timezone.utc)
    return CondicionesInicioIntento(None,1,uuid4(),uuid4(),uuid4(),"MVP","programada",
        ahora-timedelta(minutes=1),ahora+timedelta(minutes=30),ahora+timedelta(minutes=10),
        ahora,"LAB-consent-1",ahora-timedelta(seconds=1),1,1,None,None,0)


def cargar(tmp_path, datos=None, **cambios):
    archivo,huella=archivo_politica(tmp_path,datos)
    return cargar_politicas_inicio(**(dict(archivo=archivo,huella=huella,ambito="LABORATORIO")|cambios))


def test_inicio_y_estado_explicitos(tmp_path):
    p=cargar(tmp_path);c=condiciones()
    assert p.autorizar_inicio(c) is None
    assert p.autorizar_vinculacion(SimpleNamespace(**c.__dict__))=="pendiente"


@pytest.mark.parametrize("cambios",[
    {"numero_intento":2}, {"estado_asignacion":"cancelada"},
    {"numero_intento":1,"id_permiso_extra":4,"cantidad_extra":1},
    {"id_participacion":4,"numero_intento":2,"id_permiso_extra":4,"cantidad_extra":1,"usos_permiso":1},
    {"id_participacion":4,"numero_intento":2,"id_permiso_extra":4,"cantidad_extra":2},
])
def test_cupos_y_estado_rechazados(tmp_path,cambios):
    with pytest.raises(AccesoDenegado):cargar(tmp_path).autorizar_inicio(replace(condiciones(),**cambios))


def test_permiso_persistido_de_un_uso(tmp_path):
    assert cargar(tmp_path).autorizar_inicio(replace(condiciones(),id_participacion=1,
        numero_intento=2,id_permiso_extra=3,cantidad_extra=1)) is None


@pytest.mark.parametrize("inclusiva",[True,False])
def test_frontera_deadline_explicita(tmp_path,inclusiva):
    p=cargar(tmp_path,decision_lab()|{"incluye_limite_ingreso":inclusiva})
    c=condiciones();c=replace(c,ahora=c.limite_ingreso)
    if inclusiva:assert p.autorizar_inicio(c) is None
    else:
        with pytest.raises(AccesoDenegado):p.autorizar_inicio(c)
    with pytest.raises(AccesoDenegado):p.autorizar_inicio(replace(c,ahora=c.cierre))


@pytest.mark.parametrize("cambios",[{"ambito":None},{"ambito":"PRODUCCION"},{"archivo":None},{"huella":"0"*64}])
def test_fuente_ausente_alterada_o_scope_incompatible(tmp_path,cambios):
    with pytest.raises(ReglaPendiente):cargar(tmp_path,**cambios)


@pytest.mark.parametrize("cambios",[
    {"estado_inicial_participacion":"activa"},{"intentos_base":2},{"intentos_base":True},
    {"usos_permiso_extra":True},{"estados_asignacion":["cancelada"]},
    {"incluye_limite_ingreso":None},{"referencias_consentimiento":[]},
    {"referencias_consentimiento":["LAB","LAB"]},
])
def test_decisiones_fuera_del_contrato_cerradas(tmp_path,cambios):
    with pytest.raises(ReglaPendiente):cargar(tmp_path,decision_lab()|cambios)


def test_no_inferir_frontera_ni_estado(tmp_path):
    for campo in ("incluye_limite_ingreso","estado_inicial_participacion"):
        datos=decision_lab();datos.pop(campo)
        with pytest.raises(ReglaPendiente):cargar(tmp_path,datos)


def test_json_canonico_y_hash_sobre_original(tmp_path):
    archivo=tmp_path/"no-canonico.json";archivo.write_text(json.dumps(decision_lab(),indent=2))
    with pytest.raises(ReglaPendiente):
        cargar_politicas_inicio(archivo=archivo,huella=sha256(archivo.read_bytes()).hexdigest(),ambito="LABORATORIO")


def test_consentimiento_y_cupo_persistidos_se_revalidan(tmp_path):
    for cambios in ({"version_consentimiento":"otra"},{"intentos_base":2}):
        with pytest.raises(ReglaPendiente):cargar(tmp_path).autorizar_inicio(replace(condiciones(),**cambios))
