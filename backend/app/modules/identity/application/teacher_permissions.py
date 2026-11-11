"""Perfil global de permisos docentes confirmado por el responsable funcional."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PerfilPermisosDocentes:
    id_rol: int
    rol: str
    permisos: tuple[str, ...]
    permisos_disponibles: tuple[str, ...]
    docentes_afectados: int
    alcance: str = "GLOBAL_ROL"
