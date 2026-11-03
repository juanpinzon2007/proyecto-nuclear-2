"""Adaptador real de RecorridoVersionCases; comparte la Session de la UoW."""
from app.modules.cases.application.graph import GrafoNoDisponible, SeleccionFueraDeRecorrido
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.domain.errors import RespuestaInmutable


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
