"""Hechos de preparación académica; nunca notas ni permiso de publicación."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class IntentoParaRevision:
    id_intento: int
    numero: int
    estado: str
    id_resultado_tecnico: int | None


@dataclass(frozen=True)
class ConvocatoriaParaRevision:
    id_convocatoria: UUID
    id_estudiante: int
    estado: str
    id_participacion: int | None
    intentos: tuple[IntentoParaRevision, ...]
    pendientes: tuple[str, ...]


@dataclass(frozen=True)
class PreparacionEvaluacionSesion:
    id_sesion: UUID
    version_caso_id: UUID
    rubrica_id: UUID
    version_regla: str
    estado_sesion: str
    convocatorias: tuple[ConvocatoriaParaRevision, ...]
    pendientes: tuple[str, ...]

    @property
    def publicable(self) -> bool:
        # No existe todavía una composición oficial de consolidación/publicación.
        return False
