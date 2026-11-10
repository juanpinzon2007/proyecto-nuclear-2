"""Contrato público existente: sin DB, reglas nuevas ni estrechar tipos legacy."""
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.main import app
from app.modules.participation.api.schemas import SeleccionSolicitud


def test_operaciones_main_documentan_los_errores_reales():
    paths = app.openapi()['paths']
    for path in ('/api/v1/attempts/{attempt_id}/decisions/{decision_id}',
                 '/api/v1/attempts/{attempt_id}/finish'):
        assert set(paths[path]) == {'post'}
        op = paths[path]['post']
        for status in ('401', '403', '404', '409', '422', '503'):
            assert op['responses'][status]['content']['application/json']['schema']['$ref'].endswith('/ErrorHTTP')
    decision = paths['/api/v1/attempts/{attempt_id}/decisions/{decision_id}']['post']
    parameters = {p['name']: p['schema'] for p in decision['parameters']}
    assert parameters['attempt_id']['type'] == 'integer'
    assert parameters['decision_id']['format'] == 'uuid'


def test_seleccion_conserva_uuid_y_el_contrato_interno_legacy():
    uid = 'ad4c4318-4ea9-47dd-844c-0497bacd9861'
    assert SeleccionSolicitud(id_opcion=uid).id_opcion == UUID(uid)
    assert SeleccionSolicitud(id_opcion=1).id_opcion == 1
    # Aceptar INTEGER en el DTO compartido no lo convierte en una opción válida
    # del grafo SQL UUID. No se rompe ese contrato histórico para tipar Angular.
    with pytest.raises(ValidationError):
        SeleccionSolicitud(id_opcion=True)


@pytest.mark.parametrize('campo', ['id_estudiante', 'rol'])
def test_el_cuerpo_no_admite_identidad_o_privilegios(campo):
    with pytest.raises(ValidationError):
        SeleccionSolicitud.model_validate({'id_opcion': 'ad4c4318-4ea9-47dd-844c-0497bacd9861', campo: 1})


def test_fin_de_ruta_es_distinto_del_estado_del_intento():
    schemas = app.openapi()['components']['schemas']
    properties = schemas['EscenarioActualRespuesta']['properties']
    for name in ('id_escenario', 'contexto', 'pregunta'):
        assert any(s.get('type') == 'null' for s in properties[name]['anyOf'])
    assert schemas['EstadoIntento']['enum'] == ['EN_CURSO', 'FINALIZADO', 'VENCIDO']
    assert set(schemas['OpcionActualRespuesta']['properties']) == {'id', 'texto'}
