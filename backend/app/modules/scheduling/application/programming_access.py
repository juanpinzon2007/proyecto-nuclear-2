"""Permiso de espacio separado de identidad, autoría y validaciones de horario."""
from typing import Protocol
from uuid import UUID


class AutorizacionEspacioProgramacion(Protocol):
    def autorizar(self, *, id_usuario: str, id_espacio: UUID) -> None:
        """Exige asignación explícita vigente del docente al espacio.

        La implementación debe usar la Session del escritor y proteger las
        fuentes de autorización hasta su commit. No concede permisos por crear
        un espacio, por su nombre ni por una sesión anterior. Deniega o comunica
        indisponibilidad mediante los errores existentes de Identity.
        """
        ...
