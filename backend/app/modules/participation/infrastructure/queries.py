"""Adaptador SQLAlchemy de SOLO LECTURA, pendiente de tablas compartidas aprobadas.

No es aún el RepositorioParticipacion completo: no hay inserciones ni updates.
Recibe Table ya existentes; no define metadatos, tablas ni otra Base declarativa.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from types import MappingProxyType

from sqlalchemy import Integer, Table, select
from sqlalchemy.orm import Session

from app.modules.participation.application.errors import ConflictoActualizacion, RecursoNoDisponible
from app.modules.participation.domain.entities import EstadoIntento, Intento, Participacion, PasoSimulacion
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente

PARTICIPACION = ("id_participacion", "id_asignacion", "id_grupo_estudiante", "estado", "fecha_registro")
INTENTO = ("id_intento", "id_participacion", "id_consentimiento", "id_permiso_extra", "numero_intento", "estado", "inicio", "fin")
PASO = ("id_paso", "id_intento", "id_decision", "id_opcion", "numero_paso", "registrado_en", "tiempo_segundos", "reflexion_estudiante")


@dataclass(frozen=True)
class TablasLecturaParticipacion:
    participacion: Table
    intento: Table
    paso_simulacion: Table

    def __post_init__(self) -> None:
        for tabla, nombre, columnas in (
            (self.participacion, "participacion", PARTICIPACION),
            (self.intento, "intento", INTENTO),
            (self.paso_simulacion, "paso_simulacion", PASO),
        ):
            if not isinstance(tabla, Table) or tabla.name != nombre or not set(columnas).issubset(tabla.c.keys()):
                raise MapeoPersistenciaPendiente(f"Falta la tabla/columnas compartidas de {nombre}.")
            for columna in columnas:
                if columna.startswith("id_") and not isinstance(tabla.c[columna].type, Integer):
                    raise MapeoPersistenciaPendiente("El mapeo de identificadores no coincide con el ER entero.")


class LecturasParticipacionSQLAlchemy:
    def __init__(
        self, sesion: Session, tablas: TablasLecturaParticipacion, *,
        fechas: FechasPersistencia, estados: Mapping[str, EstadoIntento] | None = None,
        duracion_historica: Callable[[Session, int], timedelta] | None = None,
        bloquear: bool = False,
    ) -> None:
        if estados is not None and any(not isinstance(e, EstadoIntento) for e in estados.values()):
            raise MapeoPersistenciaPendiente("Falta un mapeo explícito de estados de intento.")
        self.sesion = sesion
        self.tablas = tablas
        self.fechas = fechas
        self.estados = MappingProxyType(dict(estados or {}))
        self.duracion_historica = duracion_historica
        self.bloquear = bloquear

    def _participacion(self, identificador: int):
        tabla = self.tablas.participacion
        sentencia = select(*(tabla.c[c] for c in PARTICIPACION)).where(tabla.c.id_participacion == identificador)
        return sentencia.with_for_update() if self.bloquear else sentencia

    def obtener_participacion(self, id_participacion: int) -> Participacion:
        fila = self.sesion.execute(self._participacion(id_participacion)).mappings().one_or_none()
        if fila is None:
            raise RecursoNoDisponible("Participación no disponible.")
        return Participacion(
            fila["id_participacion"], fila["id_asignacion"], fila["id_grupo_estudiante"],
            fila["estado"], self.fechas.desde_db(fila["fecha_registro"]),
        )

    def _reconstruir(self, fila: Mapping) -> Intento:
        if self.duracion_historica is None:
            raise MapeoPersistenciaPendiente("El ER no conserva la duración individual histórica del intento.")
        try:
            estado = self.estados[fila["estado"]]
        except KeyError as error:
            raise MapeoPersistenciaPendiente("Estado persistido sin correspondencia aprobada.") from error
        tabla = self.tablas.paso_simulacion
        sentencia = select(*(tabla.c[c] for c in PASO)).where(
            tabla.c.id_intento == fila["id_intento"]
        ).order_by(tabla.c.numero_paso, tabla.c.id_paso)
        pasos = tuple(PasoSimulacion(
            id_paso=p["id_paso"], id_intento=p["id_intento"], id_decision=p["id_decision"],
            id_opcion=p["id_opcion"], numero_paso=p["numero_paso"],
            registrado_en=self.fechas.desde_db(p["registrado_en"]),
            tiempo_segundos=p["tiempo_segundos"], reflexion_estudiante=p["reflexion_estudiante"],
        ) for p in self.sesion.execute(sentencia).mappings().all())
        return Intento(
            id_intento=fila["id_intento"], id_participacion=fila["id_participacion"],
            id_consentimiento=fila["id_consentimiento"], numero_intento=fila["numero_intento"],
            inicio=self.fechas.desde_db(fila["inicio"]),
            tiempo_maximo=self.duracion_historica(self.sesion, fila["id_intento"]),
            id_permiso_extra=fila["id_permiso_extra"], estado=estado,
            fin=self.fechas.desde_db(fila["fin"]) if fila["fin"] is not None else None,
            pasos=pasos,
        )

    def obtener_intento(self, id_intento: int) -> Intento:
        tabla = self.tablas.intento
        sentencia = select(*(tabla.c[c] for c in INTENTO)).where(tabla.c.id_intento == id_intento)
        fila = self.sesion.execute(sentencia).mappings().one_or_none()
        if fila is None:
            raise RecursoNoDisponible("Intento no disponible.")
        if self.bloquear:
            # Orden común con inicio: primero participación, después intento.
            # No bloquear primero intento y luego su padre, pues invertiría el orden.
            self.obtener_participacion(fila["id_participacion"])
            sentencia = sentencia.where(tabla.c.id_participacion == fila["id_participacion"]).with_for_update()
            fila = self.sesion.execute(sentencia).mappings().one_or_none()
            if fila is None:
                raise ConflictoActualizacion("El intento cambió mientras se obtenía el bloqueo.")
        return self._reconstruir(fila)

    def listar_intentos(self, id_participacion: int) -> tuple[Intento, ...]:
        if self.bloquear:
            self.obtener_participacion(id_participacion)
        tabla = self.tablas.intento
        sentencia = select(*(tabla.c[c] for c in INTENTO)).where(
            tabla.c.id_participacion == id_participacion
        ).order_by(tabla.c.id_intento)
        if self.bloquear:
            sentencia = sentencia.with_for_update()
        filas = self.sesion.execute(sentencia).mappings().all()
        return tuple(self._reconstruir(fila) for fila in filas)
