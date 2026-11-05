"""RN-16: permiso de laboratorio verificado contra el creador real de Cases.

PostgreSQL desechable; no aprueba políticas de repetición ni crea rutas públicas.
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.academic_models import PermisoIntentoExtraORM
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.infrastructure.start import IdentityInicioSQLAlchemy
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from tests.integration.test_attempt_start import c, convocada  # noqa: F401
from tests.integration.test_cases_graph import pg_grafo  # noqa: F401


@pytest.mark.parametrize("vinculacion", ["creador", "ajeno", "ausente", "ambigua"])
def test_permiso_exige_identidad_cases_inequivoca_del_creador(c, vinculacion):
    with c.sesiones.begin() as s:
        permiso = PermisoIntentoExtraORM(id_participacion=c.pk, id_profesor=c.docente,
            cantidad_autorizada=1, justificacion="Fixture RN-16", fecha_autorizacion=c.ahora.replace(tzinfo=None))
        s.add(permiso)
        s.flush()
        permiso_id = permiso.id_permiso_extra
        # Asociación explícita SOLO de la fixture; nunca se infiere de INTEGER.
        repositorio = RepositorioIdentidadAcademicaSQLAlchemy(s)
        if vinculacion != "ausente":
            repositorio.agregar_verificado(VinculoAcademico(str(c.docente), SistemaAcademico.CASES,
                uuid4() if vinculacion == "ajeno" else c.version.docente_creador_id))
        if vinculacion == "ambigua":
            repositorio.agregar_verificado(VinculoAcademico(str(c.docente), SistemaAcademico.CASES, uuid4()))
    with c.sesiones.begin() as s:
        asignacion = s.get(AsignacionCasoModel, c.datos["id_asignacion"])
        fila = SimpleNamespace(id_participacion=c.pk,
            id_grupo_estudiante=c.datos["id_grupo_estudiante"],
            id_asignacion=asignacion.id_asignacion, id_caso=asignacion.id_caso)
        identidad = IdentityInicioSQLAlchemy(SimpleNamespace(sesion=lambda: s, datos=lambda: fila))
        argumentos = dict(id_estudiante=c.alumno, id_participacion=c.pk,
            id_grupo_estudiante=c.datos["id_grupo_estudiante"],
            id_consentimiento=c.consentimiento, id_permiso_extra=permiso_id)
        if vinculacion == "creador":
            identidad.autorizar_inicio(**argumentos)
            assert identidad.permiso.id_permiso_extra == permiso_id
        else:
            with pytest.raises((AccesoDenegado, ReglaPendiente)):
                identidad.autorizar_inicio(**argumentos)
