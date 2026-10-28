class ErrorAplicacionParticipacion(Exception):
    """Una operación de Application no puede completarse."""


class AccesoDenegado(ErrorAplicacionParticipacion):
    """Identity o Scheduling no autoriza la operación."""


class ReglaPendiente(ErrorAplicacionParticipacion):
    """Una política requerida todavía no tiene una decisión aprobada."""


class RecursoNoDisponible(ErrorAplicacionParticipacion):
    """El repositorio no puede proporcionar el recurso solicitado."""


class ConflictoActualizacion(ErrorAplicacionParticipacion):
    """Cambió el agregado desde que se leyó; no sobrescribirlo."""
