"""RF03: el servicio no confía únicamente en el contexto anterior del Proxy."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from app.modules.identity.application.ports import RepositorioUsuarios
from app.modules.identity.application.services import ServicioAdministracionUsuarios
from app.modules.identity.domain.entities import AutorizacionesDocente, ContextoAcceso, Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente, NoAutenticado


@pytest.mark.parametrize('operacion', ['crear_docente', 'asignar_autorizaciones'])
@pytest.mark.parametrize('situacion,error', [('inactiva', NoAutenticado), ('sin_rol', AccesoDenegado),
    ('inexistente', NoAutenticado), ('adapter_invalido', IntegracionPendiente)])
def test_servicio_revalida_antes_de_cualquier_mutacion(operacion, situacion, error):
    anterior = ContextoAcceso('1', 'admin@universidad.test', frozenset({Rol.ADMINISTRADOR}))
    actual = {'inactiva': replace(anterior, activo=False),
        'sin_rol': replace(anterior, roles=frozenset({Rol.DOCENTE})),
        'inexistente': None, 'adapter_invalido': True}[situacion]
    repo = Mock(spec=RepositorioUsuarios); repo.obtener_para_escritura.return_value = actual
    uow = MagicMock(); uow.__enter__.return_value = uow; uow.usuarios = repo
    service = ServicioAdministracionUsuarios(lambda: uow)
    data = AutorizacionesDocente(frozenset({Rol.DOCENTE}), frozenset())
    with pytest.raises(error):
        if operacion == 'crear_docente':
            service.crear_docente(anterior, 'docente@universidad.test', data)
        else:
            service.asignar_autorizaciones(anterior, '2', data)
    repo.obtener_para_escritura.assert_called_once_with('1')
    repo.permisos_existentes.assert_not_called()
    repo.crear_docente.assert_not_called(); repo.asignar_autorizaciones.assert_not_called()
    uow.commit.assert_not_called()


def test_adapter_sin_puerto_transaccional_falla_cerrado():
    actor = ContextoAcceso('1', 'admin@universidad.test', frozenset({Rol.ADMINISTRADOR}))
    uow = MagicMock(); uow.__enter__.return_value = uow; uow.usuarios = SimpleNamespace()
    with pytest.raises(IntegracionPendiente):
        ServicioAdministracionUsuarios(lambda: uow).crear_docente(actor, 'docente@universidad.test',
            AutorizacionesDocente(frozenset({Rol.DOCENTE}), frozenset()))
    uow.commit.assert_not_called()
