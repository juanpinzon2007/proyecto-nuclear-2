"""Dobles exclusivos de pruebas; sus permisos y rutas no son políticas oficiales."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.modules.participation.application.dto import RecorridoAplicable, SeleccionDecision
from app.modules.participation.application.errors import (
    AccesoDenegado, ConflictoActualizacion, RecursoNoDisponible, ReglaPendiente,
)
from app.modules.participation.application.ports import CondicionesIntento
from app.modules.participation.domain.entities import EstadoIntento, Intento, Participacion

INICIO = datetime(2026, 10, 27, 15, tzinfo=timezone.utc)


@dataclass
class RelojFalso:
    instante: datetime = INICIO

    def ahora(self) -> datetime:
        return self.instante


@dataclass
class AlmacenFalso:
    participaciones: dict[int, Participacion] = field(default_factory=lambda: {
        20: Participacion(20, 100, 200, "REGISTRADA", INICIO),
        21: Participacion(21, 100, 201, "REGISTRADA", INICIO),
    })
    intentos: dict[int, Intento] = field(default_factory=dict)
    siguiente_intento: int = 10
    siguiente_paso: int = 40
    commits: int = 0
    escrituras: int = 0
    version: int = 0
    fallo_commit: bool = False
    fallo_guardado: bool = False
    conflicto: bool = False

    def unidad(self) -> "UnidadTrabajoFalsa":
        return UnidadTrabajoFalsa(self)


class RepositorioFalso:
    def __init__(self, almacen: AlmacenFalso) -> None:
        self.almacen = almacen
        self.intentos = dict(almacen.intentos)
        self.escrituras = 0

    def obtener_participacion(self, id_participacion: int) -> Participacion:
        try:
            return self.almacen.participaciones[id_participacion]
        except KeyError as error:
            raise RecursoNoDisponible("Participación no disponible.") from error

    def obtener_intento(self, id_intento: int) -> Intento:
        try:
            return self.intentos[id_intento]
        except KeyError as error:
            raise RecursoNoDisponible("Intento no disponible.") from error

    def listar_intentos(self, id_participacion: int) -> tuple[Intento, ...]:
        return tuple(i for i in self.intentos.values() if i.id_participacion == id_participacion)

    def nuevo_id_intento(self) -> int:
        actual = self.almacen.siguiente_intento
        self.almacen.siguiente_intento += 1
        return actual

    def nuevo_id_paso(self) -> int:
        actual = self.almacen.siguiente_paso
        self.almacen.siguiente_paso += 1
        return actual

    def agregar_intento(self, intento: Intento) -> None:
        previos = self.listar_intentos(intento.id_participacion)
        if intento.id_intento in self.intentos or any(
            i.numero_intento == intento.numero_intento or i.estado == EstadoIntento.EN_CURSO
            for i in previos
        ):
            raise ConflictoActualizacion("Intento duplicado.")
        self.intentos[intento.id_intento] = intento
        self.escrituras += 1

    def guardar_intento(self, intento: Intento, *, esperado: Intento) -> None:
        if self.almacen.fallo_guardado:
            raise RuntimeError("Fallo de almacenamiento simulado.")
        if self.almacen.conflicto or self.intentos.get(intento.id_intento) != esperado:
            raise ConflictoActualizacion("El intento cambió.")
        self.intentos[intento.id_intento] = intento
        self.escrituras += 1


class UnidadTrabajoFalsa:
    def __init__(self, almacen: AlmacenFalso) -> None:
        self.almacen = almacen
        self.version = almacen.version
        self.repositorio = RepositorioFalso(almacen)

    def __enter__(self) -> "UnidadTrabajoFalsa":
        return self

    def __exit__(self, tipo, error, traceback) -> None:
        # Las copias locales sin commit simplemente se descartan.
        pass

    def commit(self) -> None:
        if self.almacen.fallo_commit:
            raise RuntimeError("Fallo de commit simulado.")
        if self.version != self.almacen.version:
            raise ConflictoActualizacion("Otra transacción confirmó cambios.")
        self.almacen.intentos = dict(self.repositorio.intentos)
        self.almacen.commits += 1
        self.almacen.escrituras += self.repositorio.escrituras
        self.almacen.version += 1


@dataclass
class IdentityFalso:
    fallar_en: set[str] = field(default_factory=set)
    llamadas: list[str] = field(default_factory=list)
    permitir_inicio: bool = True

    def autorizar_acceso(self, *, id_estudiante: int, id_participacion: int) -> None:
        self.llamadas.append("acceso")
        if "acceso" in self.fallar_en:
            raise RuntimeError("Identity no disponible.")
        if {20: 7, 21: 8}.get(id_participacion) != id_estudiante:
            raise AccesoDenegado("El estudiante no es titular.")

    def autorizar_inicio(self, **datos) -> None:
        self.llamadas.append("inicio")
        if "inicio" in self.fallar_en:
            raise RuntimeError("Identity no disponible.")
        if (
            not self.permitir_inicio or datos["id_consentimiento"] != 30
            or datos["id_permiso_extra"] not in (None, 90)
        ):
            raise AccesoDenegado("Consentimiento o permiso no autorizado.")


@dataclass
class SchedulingFalso:
    fallar_en: set[str] = field(default_factory=set)
    permitir_inicio: bool = True
    permitir_edicion: bool = True
    duracion: timedelta = timedelta(minutes=10)
    llamadas: list[str] = field(default_factory=list)

    def _comprobar_fallo(self, nombre: str) -> None:
        self.llamadas.append(nombre)
        if nombre in self.fallar_en:
            raise RuntimeError("Scheduling no disponible.")

    def obtener_condiciones(self, **datos) -> CondicionesIntento:
        self._comprobar_fallo("condiciones")
        if not self.permitir_inicio:
            raise AccesoDenegado("No se permite ingreso.")
        return CondicionesIntento(id_caso=300, tiempo_maximo=self.duracion)

    def autorizar_nuevo_intento(self, **datos) -> None:
        self._comprobar_fallo("nuevo")
        # Política de ejemplo exclusiva del fake, no implementada en Application.
        if datos["numero_intento"] > 1 and datos["id_permiso_extra"] != 90:
            raise AccesoDenegado("Falta autorización de repetición.")

    def validar_edicion(self, **datos) -> None:
        self._comprobar_fallo("edicion")
        if not self.permitir_edicion:
            raise AccesoDenegado("Asignación cerrada.")

    def obtener_id_caso(self, **datos) -> int:
        self._comprobar_fallo("caso")
        return 300


@dataclass
class CasesFalso:
    fallar_en: set[str] = field(default_factory=set)
    ruta: RecorridoAplicable = RecorridoAplicable((50, 51), True)
    ramificado: bool = False
    regla_pendiente: bool = False
    despues_de_validar: Callable[[], None] | None = None
    llamadas: list[str] = field(default_factory=list)

    def _comprobar_fallo(self, nombre: str) -> None:
        self.llamadas.append(nombre)
        if nombre in self.fallar_en:
            raise RuntimeError("Cases no disponible.")

    def validar_opcion(self, *, id_caso: int, id_decision: int, id_opcion: int) -> None:
        self._comprobar_fallo("opcion")
        opciones = {50: (60, 61), 51: (62, 63), 52: (64, 65), 99: (98,)}
        if id_caso != 300 or id_opcion not in opciones.get(id_decision, ()):
            raise AccesoDenegado("Opción ajena a la decisión o caso.")
        if self.despues_de_validar:
            self.despues_de_validar()

    def obtener_recorrido(self, *, id_caso: int, selecciones) -> RecorridoAplicable:
        self._comprobar_fallo("recorrido")
        if self.ramificado:
            opcion = next((s.id_opcion for s in selecciones if s.id_decision == 50), None)
            if opcion is None:
                return RecorridoAplicable((50,), False)
            return RecorridoAplicable((50, 51 if opcion == 60 else 52), True)
        return self.ruta

    def validar_cambio_conservando_pasos(
        self, *, id_caso: int, selecciones, propuesta: SeleccionDecision,
    ) -> None:
        self._comprobar_fallo("cambio")
        if self.regla_pendiente:
            raise ReglaPendiente("La modificación exige una política de recorrido aprobada.")
        actual = self.obtener_recorrido(id_caso=id_caso, selecciones=selecciones)
        if propuesta.id_decision not in actual.decisiones:
            raise AccesoDenegado("Decisión fuera del recorrido aplicable.")
        candidatas = tuple(s for s in selecciones if s.id_decision != propuesta.id_decision) + (propuesta,)
        nueva = self.obtener_recorrido(id_caso=id_caso, selecciones=candidatas)
        if any(s.id_decision not in nueva.decisiones for s in candidatas):
            raise ReglaPendiente("No se ha aprobado cómo invalidar las selecciones posteriores.")
