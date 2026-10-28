"""Enumeraciones del dominio de casos y rúbricas."""

from enum import StrEnum


class EstadoCaso(StrEnum):
    """Ciclo de vida de una versión de caso (``version_caso.estado``)."""

    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    ARCHIVADO = "ARCHIVADO"
