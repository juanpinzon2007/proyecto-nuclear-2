from datetime import datetime, timezone
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime:
        """Devuelve una fecha con zona horaria, obtenida por el servidor."""
        ...


class RelojSistema:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)
