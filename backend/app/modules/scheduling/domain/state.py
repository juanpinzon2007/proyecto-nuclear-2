
class TransicionInvalidaError(Exception):
    """Error cuando se intenta cambiar a un estado no permitido."""
    pass


class EstadoSesion:
    """Clase base para los estados de una sesión."""

    nombre = ""

    def iniciar(self):
        raise TransicionInvalidaError(
            f"No se puede iniciar desde {self.nombre}"
        )

    def finalizar(self):
        raise TransicionInvalidaError(
            f"No se puede finalizar desde {self.nombre}"
        )


class EstadoSinIniciar(EstadoSesion):
    nombre = "SIN_INICIAR"

    def iniciar(self):
        return EstadoEnCurso()


class EstadoEnCurso(EstadoSesion):
    nombre = "EN_CURSO"

    def finalizar(self):
        return EstadoFinalizado()


class EstadoFinalizado(EstadoSesion):
    nombre = "FINALIZADO"


ESTADOS = {
    "SIN_INICIAR": EstadoSinIniciar,
    "EN_CURSO": EstadoEnCurso,
    "FINALIZADO": EstadoFinalizado,
}


def transicionar(estado_actual: str, accion: str) -> str:
    clase_estado = ESTADOS.get(estado_actual)

    if clase_estado is None:
        raise TransicionInvalidaError(
            f"Estado desconocido: {estado_actual}"
        )

    estado = clase_estado()

    if accion == "iniciar":
        return estado.iniciar().nombre

    if accion == "finalizar":
        return estado.finalizar().nombre

    raise TransicionInvalidaError(
        f"Acción desconocida: {accion}"
    )
