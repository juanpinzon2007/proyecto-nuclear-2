"""Contrato de lectura del contexto real, separado de los puertos INTEGER del ER."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.participation.application.dto import ResumenIntento
from app.modules.participation.application.dto import RecorridoAplicable, SeleccionDecision


@dataclass(frozen=True)
class ContextoIngresoParticipacion:
    """Fotografía informativa: NO es un permiso persistente para crear intentos."""

    estudiante_scheduling_id: UUID
    convocatoria_id: UUID
    sesion_id: UUID
    caso_id: UUID
    version_caso_id: UUID
    numero_version: int
    tiempo_maximo: timedelta
    rubrica_id: UUID
    version_regla: str


class ConsultaIngresoParticipacion(Protocol):
    def consultar(
        self, *, usuario: ContextoAcceso, convocatoria_id: UUID, codigo_acceso: str,
    ) -> ContextoIngresoParticipacion:
        """usuario viene de Identity/JWT del servidor, nunca del cuerpo HTTP.

        Consulta titularidad, ingreso y referencia asignada. No crea participación,
        no consume cupos ni convierte estos UUID a los INTEGER del agregado.
        """
        ...


@dataclass(frozen=True)
class ContextoVinculadoParticipacion:
    """Referencias acreditadas de lectura; no autorización de inicio ni entidad ORM."""

    ingreso: ContextoIngresoParticipacion
    id_usuario: int
    id_grupo_estudiante: int
    id_grupo: int
    id_asignacion: int
    id_caso_academico: int


class ConsultaVinculacionParticipacion(Protocol):
    def consultar(
        self, *, usuario: ContextoAcceso, convocatoria_id: UUID,
        codigo_acceso: str, id_asignacion: int,
    ) -> ContextoVinculadoParticipacion:
        """Asignación explícita: verifica pertenencia sin elegir grupo ni escribir.

        Reutiliza el contrato de ingreso; no reemplaza la autorización atómica
        de los futuros puertos de inicio ni constituye un permiso reutilizable.
        """
        ...


class ConsultaEstadoPersistidoIntento(Protocol):
    def consultar(self, *, usuario: ContextoAcceso, id_intento: int) -> ResumenIntento:
        """Cabecera autorizada, sin inferir pasos, recorrido o permiso de continuar.

        Devuelve el estado almacenado, no procesa vencimientos ni autoriza ingreso.
        """
        ...


class RecorridoVersionCases(Protocol):
    """Ruta del servidor para una edición exacta; no contar preguntas globales.

    validar_cambio debe autorizar el punto actual (incluso la primera respuesta)
    y conservar las otras selecciones. El orden editorial no autoriza un punto.
    obtener es una consulta sin efectos: se invoca antes y con las selecciones
    propuestas después del cambio, dentro de la misma operación. Una ruta
    disponible debe incluir todas las respuestas conservadas; no autoriza borrar
    historia. total_conocido no significa que el estudiante haya completado la ruta.
    """
    def obtener(self, *, version_id: UUID, selecciones: tuple[SeleccionDecision, ...]) -> RecorridoAplicable: ...
    def validar_cambio(self, *, version_id: UUID, selecciones: tuple[SeleccionDecision, ...], propuesta: SeleccionDecision) -> None: ...


@dataclass(frozen=True)
class CondicionesEdicionIntento:
    id_asignacion: int
    id_grupo_estudiante: int
    sesion_id: UUID
    estado_sesion: str
    inicio_sesion: datetime
    fin_sesion: datetime
    ahora: datetime
    operacion: str = "RESPONDER"


class AutorizacionEdicionIntento(Protocol):
    def autorizar(self, condiciones: CondicionesEdicionIntento) -> None:
        """Política del servidor sobre datos bloqueados de la misma transacción.

        No reutilizar el permiso informativo 8A ni la ventana RF-22 de ingreso.
        No abrir otra Session para reconstruir o confirmar estas condiciones.
        """
        ...
