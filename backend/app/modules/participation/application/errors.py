class ErrorAplicacionParticipacion(Exception):
    """Una operación de Application no puede completarse."""


class AccesoDenegado(ErrorAplicacionParticipacion):
    """Identity o Scheduling no autoriza la operación."""


class ReglaPendiente(ErrorAplicacionParticipacion):
    """Una política requerida todavía no tiene una decisión aprobada."""


class RecursoNoDisponible(ErrorAplicacionParticipacion):
    """El repositorio no puede proporcionar el recurso solicitado."""


class EvaluacionNoConfirmada(RecursoNoDisponible):
    """El recurso cerrado está autorizado, pero aún no tiene resultado confirmado."""

    def __init__(self, *, id_participacion: int, id_intento: int | None) -> None:
        super().__init__("No existe una evaluación confirmada para consultar.")
        self.id_participacion = id_participacion
        self.id_intento = id_intento


class ConflictoActualizacion(ErrorAplicacionParticipacion):
    """Cambió el agregado desde que se leyó; no sobrescribirlo."""
