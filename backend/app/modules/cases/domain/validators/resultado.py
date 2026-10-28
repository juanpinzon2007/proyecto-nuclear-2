"""Resultado acumulativo de la cadena de validación."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ResultadoValidacion:
    """Acumula los errores de todos los eslabones sin detener el flujo."""

    errores: list[str] = field(default_factory=list)

    @property
    def es_valido(self) -> bool:
        return not self.errores

    def agregar_error(self, mensaje: str) -> None:
        self.errores.append(mensaje)

