class ErrorDominioParticipacion(ValueError):
    """Una operación viola una regla local de Participación."""


class IntentoNoEditable(ErrorDominioParticipacion):
    """El intento terminó o alcanzó su límite individual."""
