"""Excepciones del dominio de casos y rúbricas."""

from app.modules.cases.domain.validators.resultado import ResultadoValidacion


class ErrorDominioCaso(Exception):
    """Base de las excepciones del dominio de casos."""


class ErrorConstruccionCaso(ErrorDominioCaso):
    """El Builder fue usado fuera de secuencia o con datos inconsistentes."""


class ErrorPersistenciaCaso(ErrorDominioCaso):
    """Falló la persistencia; la transacción fue revertida."""


class CasoNoEncontradoError(ErrorDominioCaso):
    """La versión no existe o no pertenece al docente solicitante."""


class CasoInvalidoError(ErrorDominioCaso):
    """La versión no supera la validación de publicación (RF-09)."""

    def __init__(self, resultado: ResultadoValidacion) -> None:
        self.resultado = resultado
        super().__init__(f"El caso no puede publicarse: {len(resultado.errores)} error(es).")

    @property
    def errores(self) -> list[str]:
        return list(self.resultado.errores)

