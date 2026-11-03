"""Errores del adaptador con dobles explícitos, sin afirmar persistencia real."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica
from app.modules.identity.application.ports import ConsultaCuentaPorCorreo
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import IntegracionPendiente
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling


@pytest.mark.parametrize("inesperado", [False, True])
def test_errores_consulta_convocatorias_no_conceden_acceso(inesperado):
    usuarios = Mock(spec=ConsultaCuentaPorCorreo)
    usuarios.obtener_por_correo.return_value = ContextoAcceso("7", "alumno@universidad.test", frozenset({Rol.ESTUDIANTE}))
    resolver = Mock(spec=ResolverIdentidadAcademica)
    resolver.resolver.return_value = uuid4()
    with Session() as soporte:
        sesion = Mock(spec=Session)
        sesion.no_autoflush = soporte.no_autoflush
        sesion.execute.side_effect = RuntimeError("error inesperado") if inesperado else SQLAlchemyError("detalle SQL privado")
        validador = ValidadorConvocatoriaScheduling(sesion, usuarios, resolver)
        with pytest.raises(RuntimeError if inesperado else IntegracionPendiente) as fallo:
            validador.validar("alumno@universidad.test", "codigo-de-prueba")
        if not inesperado:
            assert "privado" not in str(fallo.value)


def test_fallo_repositorio_real_de_correo_no_se_convierte_en_usuario_valido():
    with Session() as soporte:
        sesion = Mock(spec=Session)
        sesion.no_autoflush = soporte.no_autoflush
        sesion.execute.side_effect = SQLAlchemyError("detalle SQL privado")
        resolver = Mock(spec=ResolverIdentidadAcademica)
        validador = ValidadorConvocatoriaScheduling(sesion, RepositorioUsuariosSQLAlchemy(sesion), resolver)
        with pytest.raises(IntegracionPendiente):
            validador.validar("alumno@universidad.test", "codigo-de-prueba")
        resolver.resolver.assert_not_called()
