"""Eslabón base del Chain of Responsibility (Sección 4.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.cases.domain.entities.caso import VersionCaso
from app.modules.cases.domain.validators.resultado import ResultadoValidacion


class ValidadorCaso(ABC):
    """Cada eslabón valida lo suyo, acumula errores y delega al siguiente."""

    def __init__(self) -> None:
        self._siguiente: ValidadorCaso | None = None

    def enlazar(self, siguiente: ValidadorCaso) -> ValidadorCaso:
        """Enlaza el siguiente eslabón y lo retorna para encadenar llamadas."""
        self._siguiente = siguiente
        return siguiente

    def comprobar(
        self, version: VersionCaso, resultado: ResultadoValidacion | None = None
    ) -> ResultadoValidacion:
        resultado = resultado if resultado is not None else ResultadoValidacion()
        self._validar(version, resultado)
        if self._siguiente is not None:
            return self._siguiente.comprobar(version, resultado)
        return resultado

    @abstractmethod
    def _validar(self, version: VersionCaso, resultado: ResultadoValidacion) -> None:
        """Agrega errores a ``resultado``; no debe lanzar excepciones."""

