class ErrorDominioParticipacion(ValueError):
    """Una operación viola una regla local de Participación."""


class IntentoNoEditable(ErrorDominioParticipacion):
    """El intento terminó o alcanzó su límite individual."""


class RespuestaInmutable(IntentoNoEditable):
    """Política confirmada: una respuesta registrada no se cambia ni elimina."""
