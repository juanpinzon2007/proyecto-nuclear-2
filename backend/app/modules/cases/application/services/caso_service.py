"""Servicio de aplicación: orquesta Builder, Chain of Responsibility y Repository."""

import uuid
from collections.abc import Callable

from app.modules.cases.api.schemas.caso_schemas import CasoPayload
from app.modules.cases.domain.builders.constructor_caso import IConstructorCaso
from app.modules.cases.domain.entities.caso import ResumenVersion, VersionCaso
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.domain.repositories import ICasoRepository
from app.modules.cases.domain.validators.base import ValidadorCaso


class CasoService:
    """Casos de uso RF-09: crear borrador y publicar."""

    def __init__(
        self,
        repositorio: ICasoRepository,
        fabrica_constructor: Callable[[], IConstructorCaso],
        cadena_validacion: ValidadorCaso,
    ) -> None:
        self._repositorio = repositorio
        self._fabrica_constructor = fabrica_constructor
        self._cadena = cadena_validacion

    def crear_borrador(self, docente_creador_id: uuid.UUID, payload: CasoPayload) -> VersionCaso:
        """RF-09: guarda en BORRADOR aunque esté incompleto (no ejecuta el CoR)."""
        version = self._construir(docente_creador_id, payload)
        self._repositorio.guardar(version)
        return version

    def listar(self, docente_creador_id: uuid.UUID) -> list[ResumenVersion]:
        """Resumen de los casos del docente."""
        return self._repositorio.listar_por_docente(docente_creador_id)

    def obtener(self, docente_creador_id: uuid.UUID, version_id: uuid.UUID) -> VersionCaso:
        """Detalle completo de una versión del docente."""
        return self._obtener_o_fallar(docente_creador_id, version_id)

    def actualizar(
        self, docente_creador_id: uuid.UUID, version_id: uuid.UUID, payload: CasoPayload
    ) -> VersionCaso:
        """Reemplaza la estructura de un BORRADOR con la del nuevo payload.

        Raises:
            CasoNoEncontradoError: la versión no existe o es de otro docente.
            CasoInvalidoError: la versión no está en BORRADOR.
            ErrorConstruccionCaso: payload inconsistente (la BD no se modifica).
        """
        existente = self._obtener_o_fallar(docente_creador_id, version_id)
        existente.asegurar_editable()
        nueva = self._construir(docente_creador_id, payload)
        nueva.id = existente.id
        nueva.caso_id = existente.caso_id
        nueva.numero = existente.numero
        self._repositorio.reemplazar(nueva)
        return nueva

    def archivar(self, docente_creador_id: uuid.UUID, version_id: uuid.UUID) -> VersionCaso:
        """PUBLICADO → ARCHIVADO.

        Raises:
            CasoNoEncontradoError: la versión no existe o es de otro docente.
            CasoInvalidoError: la versión no está PUBLICADA.
        """
        version = self._obtener_o_fallar(docente_creador_id, version_id)
        version.archivar()
        self._repositorio.actualizar_estado(version)
        return version

    def publicar(self, docente_creador_id: uuid.UUID, version_id: uuid.UUID) -> VersionCaso:
        """Valida un borrador existente con el CoR y lo pasa a PUBLICADO.

        Raises:
            CasoNoEncontradoError: la versión no existe o es de otro docente.
            CasoInvalidoError: no es BORRADOR o no supera la validación (no hay commit).
        """
        version = self._obtener_o_fallar(docente_creador_id, version_id)
        version.publicar(self._cadena)
        self._repositorio.actualizar_estado(version)
        return version

    def _obtener_o_fallar(self, docente_creador_id: uuid.UUID, version_id: uuid.UUID) -> VersionCaso:
        version = self._repositorio.obtener_version(version_id, docente_creador_id)
        if version is None:
            raise CasoNoEncontradoError(f"Versión {version_id} no encontrada.")
        return version

    def _construir(self, docente_creador_id: uuid.UUID, payload: CasoPayload) -> VersionCaso:
        b = self._fabrica_constructor()
        b.iniciar_datos(
            docente_creador_id=docente_creador_id,
            nombre=payload.case.nombre,
            desarrollo_situacional=payload.case.desarrollo_situacional,
            contexto_historia=payload.case.contexto_historia,
            tiempo_estimado_min=payload.case.tiempo_estimado_min,
        )
        for escenario in payload.scenarios:
            b.agregar_escenario(escenario.orden, escenario.contexto_situacional)
            for pregunta in escenario.questions:
                b.agregar_pregunta(pregunta.orden, pregunta.enunciado)
                for opcion in pregunta.options:
                    b.agregar_opcion_y_justificacion(
                        opcion.orden, opcion.texto, opcion.es_correcta, opcion.justificacion
                    )
                    for criterio, puntaje in opcion.valoraciones.items():
                        b.asignar_valoracion(criterio, puntaje)
        if payload.rubric is not None:
            b.definir_rubrica(payload.rubric.nombre, payload.rubric.version_regla)
            for criterio in payload.rubric.criterios:
                b.agregar_criterio(criterio.nombre, criterio.peso)
                for nivel in criterio.niveles:
                    b.agregar_nivel(nivel.nombre, nivel.puntaje, nivel.descriptor)
        return b.construir()

