"""Contrato CLI del runner; dobles solo de orquestación, sin acreditar SQL."""
from unittest.mock import AsyncMock

import pytest

from app.modules.scheduling.infrastructure import worker_runner as runner


def test_opcion_invalida_no_ejecuta_revision(monkeypatch):
    revision = AsyncMock()
    monkeypatch.setattr(runner, 'ejecutar_revision', revision)
    with pytest.raises(SystemExit) as error:
        runner.main(['--opcion-inexistente'])
    assert error.value.code == 2
    revision.assert_not_awaited()


def test_interrupcion_de_usuario_se_informa_sin_traceback(monkeypatch, caplog):
    def interrumpir():
        raise KeyboardInterrupt

    monkeypatch.setattr(runner, 'ejecutar_revision', interrumpir)
    with caplog.at_level('INFO'):
        assert runner.main(['--once']) == 0
    assert 'detenido' in caplog.text
    assert all(r.exc_info is None for r in caplog.records)
