"""Configuración opt-in de puntuación, sobre el grafo y valoraciones existentes.

No reinterpreta reglas históricas. Una pregunta debe tener una correspondencia
inequívoca con sus criterios. Si una alternativa tiene varias valoraciones,
solo puede representar un puntaje único cuando todas coinciden; nunca se
promedian criterios ni se transforman niveles en porcentajes.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.cases.application.graph import GrafoVersion, GrafoNoDisponible

REGLA_PREGUNTAS = "PREGUNTAS_100_V1"


class ConfiguracionCalificacionInvalida(GrafoNoDisponible):
    pass


@dataclass(frozen=True)
class PuntajeAlternativa:
    pregunta_id: UUID
    opcion_id: UUID
    criterio_id: UUID
    puntaje: Decimal


@dataclass(frozen=True)
class ConfiguracionPreguntas:
    grafo: GrafoVersion
    criterios: tuple[UUID, ...]
    puntajes: tuple[PuntajeAlternativa, ...]

    def validar(self) -> int:
        inicial = self.grafo.validar_ejecutable()
        escenas = self.grafo.escenas
        if len({e.id for e in escenas}) != len(escenas):
            raise ConfiguracionCalificacionInvalida("Escenas duplicadas.")
        preguntas = [q for e in escenas for q in e.preguntas]
        opciones = [o.opcion_id for q in preguntas for o in q.opciones]
        if len({q.id for q in preguntas}) != len(preguntas) or len(set(opciones)) != len(opciones):
            raise ConfiguracionCalificacionInvalida("Preguntas u opciones duplicadas.")
        if not self.criterios or len(set(self.criterios)) != len(self.criterios):
            raise ConfiguracionCalificacionInvalida("Rúbrica ausente o criterios duplicados.")
        valores = {}
        pares = set()
        for p in self.puntajes:
            if (p.opcion_id, p.criterio_id) in pares or p.criterio_id not in self.criterios:
                raise ConfiguracionCalificacionInvalida("Correspondencia de rúbrica ambigua o ajena.")
            if not isinstance(p.puntaje, Decimal) or not p.puntaje.is_finite() or not Decimal(0) <= p.puntaje <= Decimal(100):
                raise ConfiguracionCalificacionInvalida("Cada puntaje exige Decimal explícito entre 0 y 100.")
            pares.add((p.opcion_id, p.criterio_id))
            valores.setdefault(p.opcion_id, []).append(p)
        if any(len({p.puntaje for p in vs}) != 1 for vs in valores.values()):
            raise ConfiguracionCalificacionInvalida("La alternativa contiene puntajes distintos por criterio; falta un puntaje único.")
        if set(valores) != set(opciones):
            raise ConfiguracionCalificacionInvalida("Faltan puntajes o existen alternativas ajenas.")
        criterio_pregunta = {}
        for q in preguntas:
            ids = {frozenset(p.criterio_id for p in valores[o.opcion_id]) for o in q.opciones}
            if len(ids) != 1 or not ids or any(p.pregunta_id != q.id for o in q.opciones for p in valores[o.opcion_id]):
                raise ConfiguracionCalificacionInvalida("La pregunta no tiene un criterio inequívoco.")
            criterio_pregunta[q.id] = next(iter(ids))
        nodos = {e.id: e for e in escenas}
        memo = {}

        def perfil(id_escena):
            if id_escena in memo:
                return memo[id_escena]
            q = nodos[id_escena].preguntas[0]
            propios = tuple(int(c in criterio_pregunta[q.id]) for c in self.criterios)
            ramas = set()
            for o in q.opciones:
                resto = perfil(o.destino_id) if o.tipo == "ESCENA" else (0,) * len(propios)
                ramas.add(tuple(a + b for a, b in zip(propios, resto)))
            if len(ramas) != 1:
                raise ConfiguracionCalificacionInvalida("Rutas completas con distinta cantidad de preguntas o criterios.")
            memo[id_escena] = ramas.pop()
            return memo[id_escena]

        cantidades = perfil(inicial)
        if len(set(cantidades)) != 1 or not all(cantidades):
            raise ConfiguracionCalificacionInvalida("Cada criterio exige igual cantidad de preguntas por ruta.")
        # El perfil anterior prueba igualdad por criterio. La longitud del
        # recorrido se calcula por separado: una pregunta no cuenta N veces
        # por tener N criterios.
        longitudes = {}
        def longitud(id_escena):
            if id_escena not in longitudes:
                q = nodos[id_escena].preguntas[0]
                destinos = {1 + (longitud(o.destino_id) if o.tipo == 'ESCENA' else 0) for o in q.opciones}
                if len(destinos) != 1:
                    raise ConfiguracionCalificacionInvalida("Rutas completas con distinta cantidad de preguntas.")
                longitudes[id_escena] = destinos.pop()
            return longitudes[id_escena]
        return longitud(inicial)

    def seleccionar(self, selecciones: tuple[tuple[UUID, UUID], ...]):
        """No elige una continuación para pendientes: solo devuelve la ruta real.

        El denominador de toda continuación es idéntico tras validar los perfiles.
        Las preguntas pendientes se representan por cantidad, nunca por respuestas.
        """
        total = self.validar()
        ruta = self.grafo.recorrer(selecciones)
        if tuple(q for q, _ in selecciones) != ruta.decisiones[:len(selecciones)]:
            raise ConfiguracionCalificacionInvalida("El orden de las respuestas no corresponde al recorrido.")
        puntos = {p.opcion_id: p.puntaje for p in self.puntajes}
        return ruta, total, tuple(puntos[o] for _, o in selecciones)
