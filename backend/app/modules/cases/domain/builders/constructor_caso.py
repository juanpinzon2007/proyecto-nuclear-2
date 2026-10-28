"""Interfaz y construcción progresiva de una versión de caso (Sección 4.3)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from decimal import Decimal

from app.modules.cases.domain.entities.caso import (
    CriterioRubrica,
    Escenario,
    NivelRubrica,
    OpcionRespuesta,
    Pregunta,
    Rubrica,
    VersionCaso,
)
from app.modules.cases.domain.exceptions import ErrorConstruccionCaso


class IConstructorCaso(ABC):
    """Contrato del Builder; el router/servicio solo conoce esta interfaz."""

    @abstractmethod
    def iniciar_datos(
        self,
        docente_creador_id: uuid.UUID,
        nombre: str,
        desarrollo_situacional: str,
        contexto_historia: str,
        tiempo_estimado_min: int,
    ) -> IConstructorCaso: ...

    @abstractmethod
    def agregar_escenario(self, orden: int, contexto_situacional: str) -> IConstructorCaso: ...

    @abstractmethod
    def agregar_pregunta(self, orden: int, enunciado: str) -> IConstructorCaso: ...

    @abstractmethod
    def agregar_opcion_y_justificacion(
        self, orden: int, texto: str, es_correcta: bool, justificacion: str
    ) -> IConstructorCaso: ...

    @abstractmethod
    def asignar_valoracion(self, criterio_nombre: str, puntaje: Decimal) -> IConstructorCaso:
        """Valora la última opción agregada contra un criterio (por nombre)."""

    @abstractmethod
    def definir_rubrica(self, nombre: str, version_regla: str) -> IConstructorCaso: ...

    @abstractmethod
    def agregar_criterio(self, nombre: str, peso: Decimal) -> IConstructorCaso: ...

    @abstractmethod
    def agregar_nivel(self, nombre: str, puntaje: Decimal, descriptor: str) -> IConstructorCaso: ...

    @abstractmethod
    def construir(self) -> VersionCaso: ...


class ConstructorCaso(IConstructorCaso):
    """Ensambla la jerarquía en memoria; la persistencia (commit) la hace el repositorio.

    Mantiene un cursor sobre el escenario/pregunta/criterio actual y rechaza
    llamadas fuera de secuencia con ``ErrorConstruccionCaso``.
    """

    def __init__(self) -> None:
        self._reiniciar()

    def _reiniciar(self) -> None:
        self._version: VersionCaso | None = None
        self._escenario: Escenario | None = None
        self._pregunta: Pregunta | None = None
        self._criterio: CriterioRubrica | None = None
        self._opcion: OpcionRespuesta | None = None
        # (opción, nombre de criterio, puntaje) resueltos en construir()
        self._valoraciones: list[tuple[OpcionRespuesta, str, Decimal]] = []

    def iniciar_datos(
        self,
        docente_creador_id: uuid.UUID,
        nombre: str,
        desarrollo_situacional: str,
        contexto_historia: str,
        tiempo_estimado_min: int,
    ) -> ConstructorCaso:
        self._reiniciar()
        self._version = VersionCaso(
            nombre=nombre,
            desarrollo_situacional=desarrollo_situacional,
            contexto_historia=contexto_historia,
            tiempo_estimado_min=tiempo_estimado_min,
            docente_creador_id=docente_creador_id,
        )
        return self

    def agregar_escenario(self, orden: int, contexto_situacional: str) -> ConstructorCaso:
        version = self._requerir_version()
        if any(e.orden == orden for e in version.escenarios):
            raise ErrorConstruccionCaso(f"Ya existe un escenario con orden {orden}.")
        self._escenario = Escenario(orden=orden, contexto_situacional=contexto_situacional)
        version.escenarios.append(self._escenario)
        self._pregunta = None
        self._opcion = None
        return self

    def agregar_pregunta(self, orden: int, enunciado: str) -> ConstructorCaso:
        escenario = self._requerir(self._escenario, "agregar_escenario() antes de agregar_pregunta()")
        if any(p.orden == orden for p in escenario.preguntas):
            raise ErrorConstruccionCaso(f"Ya existe una pregunta con orden {orden} en el escenario.")
        self._pregunta = Pregunta(orden=orden, enunciado=enunciado)
        escenario.preguntas.append(self._pregunta)
        self._opcion = None
        return self

    def agregar_opcion_y_justificacion(
        self, orden: int, texto: str, es_correcta: bool, justificacion: str
    ) -> ConstructorCaso:
        pregunta = self._requerir(self._pregunta, "agregar_pregunta() antes de agregar opciones")
        if any(o.orden == orden for o in pregunta.opciones):
            raise ErrorConstruccionCaso(f"Ya existe una opción con orden {orden} en la pregunta.")
        self._opcion = OpcionRespuesta(
            orden=orden, texto=texto, es_correcta=es_correcta, justificacion=justificacion
        )
        pregunta.opciones.append(self._opcion)
        return self

    def asignar_valoracion(self, criterio_nombre: str, puntaje: Decimal) -> ConstructorCaso:
        opcion = self._requerir(
            self._opcion, "agregar_opcion_y_justificacion() antes de asignar_valoracion()"
        )
        self._valoraciones.append((opcion, criterio_nombre, puntaje))
        return self

    def definir_rubrica(self, nombre: str, version_regla: str) -> ConstructorCaso:
        version = self._requerir_version()
        version.rubrica = Rubrica(nombre=nombre, version_regla=version_regla)
        self._criterio = None
        return self

    def agregar_criterio(self, nombre: str, peso: Decimal) -> ConstructorCaso:
        rubrica = self._requerir_version().rubrica
        rubrica = self._requerir(rubrica, "definir_rubrica() antes de agregar_criterio()")
        self._criterio = CriterioRubrica(nombre=nombre, peso=peso)
        rubrica.criterios.append(self._criterio)
        return self

    def agregar_nivel(self, nombre: str, puntaje: Decimal, descriptor: str) -> ConstructorCaso:
        criterio = self._requerir(self._criterio, "agregar_criterio() antes de agregar_nivel()")
        criterio.niveles.append(NivelRubrica(nombre=nombre, puntaje=puntaje, descriptor=descriptor))
        return self

    def construir(self) -> VersionCaso:
        """Entrega la versión en BORRADOR (sin validar: eso ocurre al publicar) y reinicia."""
        version = self._requerir_version()
        self._resolver_valoraciones(version)
        self._reiniciar()
        return version

    def _resolver_valoraciones(self, version: VersionCaso) -> None:
        """Convierte nombres de criterio en ids; falla si el criterio no existe.

        Sin rúbrica no hay a qué resolver: se omite y ``ValidadorRubrica`` lo reporta.
        """
        if version.rubrica is None:
            return
        criterios = {c.nombre: c for c in version.rubrica.criterios}
        for opcion, nombre, puntaje in self._valoraciones:
            criterio = criterios.get(nombre)
            if criterio is None:
                raise ErrorConstruccionCaso(f"La valoración referencia un criterio inexistente: '{nombre}'.")
            opcion.valoraciones[criterio.id] = puntaje

    def _requerir_version(self) -> VersionCaso:
        return self._requerir(self._version, "iniciar_datos() primero")

    @staticmethod
    def _requerir[T](valor: T | None, paso: str) -> T:
        if valor is None:
            raise ErrorConstruccionCaso(f"Debe invocar {paso}.")
        return valor

