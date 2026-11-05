"""Adaptador real de RecorridoVersionCases; comparte la Session de la UoW."""
from app.modules.cases.application.graph import GrafoNoDisponible, SeleccionFueraDeRecorrido
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.domain.errors import RespuestaInmutable
from app.modules.participation.application.current_scenario import EscenarioActual, PreguntaActual, OpcionActual


class RecorridoCasesSQLAlchemy:
    def __init__(self, crear_sesion):
        self.crear_sesion = crear_sesion

    def obtener(self, *, version_id, selecciones):
        try:
            grafo = RepositorioGrafoSQLAlchemy(self.crear_sesion()).leer(version_id)
            ruta = grafo.recorrer(tuple((s.id_decision, s.id_opcion) for s in selecciones))
        except SeleccionFueraDeRecorrido:
            raise ReglaPendiente("El recorrido excluye respuestas conservadas o contiene una selección inválida.") from None
        except GrafoNoDisponible:
            return RecorridoAplicable((), False, disponible=False)
        # Solo una ruta terminada por FIN acredita su conjunto completo; no se
        # suman todas las preguntas de las alternativas que no se recorrieron.
        return RecorridoAplicable(ruta.decisiones, ruta.finalizado)

    def obtener_actual(self, *, version_id, selecciones):
        """Mismo grafo y algoritmo; proyecta SOLO el nodo actualmente habilitado."""
        try:
            grafo = RepositorioGrafoSQLAlchemy(self.crear_sesion()).leer(version_id)
            ruta = grafo.recorrer(tuple((s.id_decision, s.id_opcion) for s in selecciones))
        except GrafoNoDisponible:
            raise ReglaPendiente("Cases no acredita un recorrido ejecutable.") from None
        if ruta.finalizado:
            return EscenarioActual(None, None, None, True, len(selecciones))
        escena = next(e for e in grafo.escenas if e.id == ruta.escena_actual)
        pregunta = escena.preguntas[0]  # recorrer ya exige una pregunta por escena.
        return EscenarioActual(escena.id, escena.contexto,
            PreguntaActual(pregunta.id, pregunta.enunciado,
                tuple(OpcionActual(o.opcion_id, o.texto) for o in pregunta.opciones)),
            False, len(selecciones))

    def validar_cambio(self, *, version_id, selecciones, propuesta):
        if any(s.id_decision == propuesta.id_decision for s in selecciones):
            raise RespuestaInmutable("La respuesta registrada es inmutable; no puede modificar el recorrido.")
        try:
            grafo = RepositorioGrafoSQLAlchemy(self.crear_sesion()).leer(version_id)
            ruta = grafo.recorrer(tuple((s.id_decision, s.id_opcion) for s in selecciones))
            if ruta.finalizado or propuesta.id_decision != ruta.decisiones[-1]:
                raise AccesoDenegado("La pregunta no pertenece a la escena actual.")
            grafo.recorrer(tuple((s.id_decision, s.id_opcion) for s in (*selecciones, propuesta)))
        except GrafoNoDisponible:
            raise ReglaPendiente("Cases no acredita el punto del recorrido y la conservación de las respuestas.") from None
