"""Proyección pura compartida; no decide ni persiste transiciones de estado."""
from app.modules.participation.application.dto import ProgresoIntento, ResumenIntento, selecciones_de
from app.modules.participation.application.errors import ReglaPendiente


def proyectar_progreso(intento, ruta) -> ProgresoIntento:
    selecciones = selecciones_de(intento)
    if ruta.disponible and any(s.id_decision not in ruta.decisiones for s in selecciones):
        raise ReglaPendiente("El recorrido excluye selecciones conservadas; debe resolverse su tratamiento.")
    respondidas = {s.id_decision for s in selecciones}
    return ProgresoIntento(
        intento=ResumenIntento.desde(intento),
        decisiones_aplicables=ruta.decisiones if ruta.disponible else None,
        selecciones=selecciones,
        pendientes=tuple(d for d in ruta.decisiones if d not in respondidas) if ruta.disponible else None,
        total_aplicable=len(ruta.decisiones) if ruta.total_conocido else None)
