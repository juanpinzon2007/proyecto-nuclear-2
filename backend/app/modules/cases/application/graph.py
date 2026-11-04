"""Grafo versionado; no interpreta el orden editorial como navegación.

La evaluación del recorrido soporta solo puntos inequívocos (una pregunta por
escena). Multipregunta y ciclos se conservan como datos, bloqueados por política
pendiente, sin prohibiciones estructurales permanentes.
"""
from dataclasses import dataclass
from uuid import UUID
from typing import Protocol

from app.modules.cases.domain.entities.caso import VersionCaso


class GrafoNoDisponible(ValueError):
    pass


class ReglaRecorridoPendiente(GrafoNoDisponible):
    pass


class SeleccionFueraDeRecorrido(GrafoNoDisponible):
    pass


@dataclass(frozen=True)
class Transicion:
    opcion_id: UUID
    tipo: str | None
    destino_id: UUID | None
    texto: str


@dataclass(frozen=True)
class PreguntaGrafo:
    id: UUID
    enunciado: str
    opciones: tuple[Transicion, ...]


@dataclass(frozen=True)
class EscenaGrafo:
    id: UUID
    inicial: bool
    contexto: str
    preguntas: tuple[PreguntaGrafo, ...]


@dataclass(frozen=True)
class RecorridoGrafo:
    escenas: tuple[UUID, ...]
    decisiones: tuple[UUID, ...]
    escena_actual: UUID | None
    finalizado: bool


@dataclass(frozen=True)
class GrafoVersion:
    version_id: UUID
    escenas: tuple[EscenaGrafo, ...]

    def validar_ejecutable(self):
        iniciales = [e for e in self.escenas if e.inicial]
        if len(iniciales) != 1:
            raise GrafoNoDisponible("El recorrido exige exactamente una escena inicial.")
        nodos = {e.id: e for e in self.escenas}
        # Todas las ramas alcanzables deben estar definidas; no se elige una
        # alternativa para ocultar una transición incompleta.
        visitados, activos = set(), set()

        def visitar(id_escena):
            if id_escena in activos:
                raise ReglaRecorridoPendiente("Ciclos/revisitas requieren definición académica.")
            if id_escena in visitados:
                return
            escena = nodos.get(id_escena)
            if escena is None:
                raise GrafoNoDisponible("Destino inexistente o de otra versión.")
            if len(escena.preguntas) != 1:
                raise ReglaRecorridoPendiente("El avance con varias preguntas o sin preguntas no está definido.")
            pregunta = escena.preguntas[0]
            if not pregunta.opciones:
                raise GrafoNoDisponible("Pregunta sin alternativas.")
            activos.add(id_escena)
            for opcion in pregunta.opciones:
                if opcion.tipo == "ESCENA" and opcion.destino_id is not None:
                    visitar(opcion.destino_id)
                elif opcion.tipo != "FIN" or opcion.destino_id is not None:
                    raise GrafoNoDisponible("Transición necesaria sin configurar o incoherente.")
            activos.remove(id_escena)
            visitados.add(id_escena)

        visitar(iniciales[0].id)
        return iniciales[0].id

    def recorrer(self, selecciones: tuple[tuple[UUID, UUID], ...]) -> RecorridoGrafo:
        actual = self.validar_ejecutable()
        respuestas = dict(selecciones)
        if len(respuestas) != len(selecciones):
            raise SeleccionFueraDeRecorrido("Pregunta seleccionada más de una vez.")
        nodos = {e.id: e for e in self.escenas}
        escenas, preguntas = [], []
        while actual is not None:
            escena = nodos[actual]
            pregunta = escena.preguntas[0]
            escenas.append(actual)
            preguntas.append(pregunta.id)
            if pregunta.id not in respuestas:
                break
            opcion = next((o for o in pregunta.opciones if o.opcion_id == respuestas[pregunta.id]), None)
            if opcion is None:
                raise SeleccionFueraDeRecorrido("La opción no pertenece a la pregunta de la escena actual.")
            actual = opcion.destino_id if opcion.tipo == "ESCENA" else None
        if not set(respuestas).issubset(preguntas):
            raise SeleccionFueraDeRecorrido("Hay respuestas fuera de la ruta seleccionada.")
        return RecorridoGrafo(tuple(escenas), tuple(preguntas), actual, actual is None)


class AutoriaRecorridoPort(Protocol):
    """Autoría transaccional; el adaptador reutiliza el repositorio de grafo."""

    def obtener_recorrido(self, version: VersionCaso) -> GrafoVersion: ...

    def configurar_recorrido(self, version: VersionCaso, *, inicial_id: UUID,
                            transiciones: tuple[tuple[UUID, str, UUID | None], ...]) -> GrafoVersion: ...

    def publicar_ejecutable(self, version: VersionCaso) -> None: ...
