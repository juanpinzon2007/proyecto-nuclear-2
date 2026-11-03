"""Session SQLAlchemy real sin conexión; NO demuestra persistencia ni concurrencia PG."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import event
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.modules.participation.application.errors import ConflictoActualizacion
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy


def test_misma_sesion_para_ambos_repositorios_y_un_solo_commit():
    sesion = Session()
    eventos = []
    event.listen(sesion, "after_commit", lambda _: eventos.append("commit"))
    factory = Mock(return_value=sesion)
    with UnidadTrabajoSQLAlchemy(
        lambda s: SimpleNamespace(sesion=s), crear_resultados=lambda s: SimpleNamespace(sesion=s),
        crear_sesion=factory,
    ) as trabajo:
        assert trabajo.repositorio.sesion is trabajo.resultados.sesion is sesion
        assert sesion.in_transaction()
        assert eventos == []
        trabajo.commit()
        with pytest.raises(RuntimeError):
            trabajo.commit()
    assert eventos == ["commit"]
    factory.assert_called_once()
    assert not sesion.in_transaction()


def test_sin_commit_o_con_excepcion_se_revierte():
    for fallar in (False, True):
        sesion = Session()
        eventos = []
        event.listen(sesion, "after_rollback", lambda _: eventos.append("rollback"))
        try:
            with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=lambda: sesion):
                if fallar:
                    raise ValueError("operación interrumpida")
        except ValueError:
            pass
        assert eventos == ["rollback"]
        assert not sesion.in_transaction()


def test_fabrica_compartida_se_resuelve_solo_al_entrar(monkeypatch):
    sesion = Session()
    factory = Mock(return_value=sesion)
    getter = Mock(return_value=factory)
    monkeypatch.setattr("app.modules.participation.infrastructure.unit_of_work.get_session_factory", getter)
    trabajo = UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(sesion=s))
    getter.assert_not_called()
    with trabajo:
        assert trabajo.repositorio.sesion is sesion
    getter.assert_called_once()
    factory.assert_called_once()


def test_sin_adapter_resultados_no_aparenta_integracion():
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=Session) as trabajo:
        with pytest.raises(MapeoPersistenciaPendiente):
            _ = trabajo.resultados


def test_error_construyendo_repositorio_cierra_sesion(monkeypatch):
    sesion = Session()
    cerrar = Mock(wraps=sesion.close)
    monkeypatch.setattr(sesion, "close", cerrar)
    def fallar(s):
        raise MapeoPersistenciaPendiente("tablas no acordadas")
    with pytest.raises(MapeoPersistenciaPendiente):
        with UnidadTrabajoSQLAlchemy(fallar, crear_sesion=lambda: sesion):
            pass
    cerrar.assert_called_once()
    assert not sesion.in_transaction()


@pytest.mark.parametrize("codigo", ["23505", "40001", "40P01"])
def test_sqlstate_concurrente_se_traduce_sin_reintento_automatico(monkeypatch, codigo):
    sesion = Session()
    original = RuntimeError("detalle SQL privado")
    original.sqlstate = codigo
    fallo = IntegrityError("sentencia", {}, original)
    confirmar = Mock(side_effect=fallo)
    monkeypatch.setattr(sesion, "commit", confirmar)
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=lambda: sesion) as trabajo:
        with pytest.raises(ConflictoActualizacion) as error:
            trabajo.commit()
        assert "privado" not in str(error.value)
        assert not sesion.in_transaction()
    confirmar.assert_called_once()


def test_error_fk_no_se_disfraza_de_conflicto_concurrente(monkeypatch):
    sesion = Session()
    original = RuntimeError("FK pendiente")
    original.sqlstate = "23503"
    fallo = IntegrityError("sentencia", {}, original)
    monkeypatch.setattr(sesion, "commit", Mock(side_effect=fallo))
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=lambda: sesion) as trabajo:
        with pytest.raises(DBAPIError):
            trabajo.commit()
        assert not sesion.in_transaction()


def test_error_de_commit_aisla_unidad_fallida_y_permite_una_nueva(monkeypatch):
    sesion = Session()
    monkeypatch.setattr(sesion, "commit", Mock(side_effect=RuntimeError("fallo simulado")))
    unidad = UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=lambda: sesion)
    with unidad:
        with pytest.raises(RuntimeError):
            unidad.commit()
        with pytest.raises(RuntimeError):
            _ = unidad.repositorio
    with pytest.raises(RuntimeError):
        unidad.__enter__()
    with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=Session) as nueva:
        nueva.commit()


def test_sesion_ajena_activa_no_se_confirma_o_revierte():
    sesion = Session()
    sesion.begin()
    try:
        with pytest.raises(RuntimeError):
            with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=lambda: sesion):
                pass
        assert sesion.in_transaction()
    finally:
        sesion.rollback()
        sesion.close()


def test_fuera_de_contexto_no_hay_repositorio_activo():
    unidad = UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=Session)
    with pytest.raises(RuntimeError):
        _ = unidad.repositorio
    with unidad:
        pass
    with pytest.raises(RuntimeError):
        _ = unidad.repositorio


@pytest.mark.parametrize("codigo", ["23505", "40001", "40P01"])
def test_conflicto_antes_de_commit_revierte_y_se_traduce(codigo):
    sesion = Session()
    original = RuntimeError("diagnóstico privado")
    original.sqlstate = codigo
    fallo = IntegrityError("sentencia", {}, original)
    with pytest.raises(ConflictoActualizacion) as error:
        with UnidadTrabajoSQLAlchemy(lambda s: SimpleNamespace(), crear_sesion=lambda: sesion):
            raise fallo
    assert not sesion.in_transaction()
    assert "privado" not in str(error.value)
