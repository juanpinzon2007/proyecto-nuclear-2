"""Errores propios de Identity, sin dependencias HTTP ni de persistencia."""


class ErrorIdentidad(Exception):
    pass


class NoAutenticado(ErrorIdentidad):
    pass


class AccesoDenegado(ErrorIdentidad):
    pass


class IntegracionPendiente(ErrorIdentidad):
    pass


class ReglaIdentidadInvalida(ErrorIdentidad):
    pass


class RecursoNoDisponible(ErrorIdentidad):
    pass


class ConflictoIdentidad(ErrorIdentidad):
    pass
