from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from app.modules.participation.domain.clock import Reloj
from app.modules.participation.domain.errors import (
    ErrorDominioParticipacion,
    IntentoNoEditable,
    RespuestaInmutable,
)

# Los INTEGER antiguos siguen siendo válidos en dobles/contratos históricos;
# el adaptador real exige UUID existentes, nunca convierte entre ambos.
IdentificadorCases = int | UUID


def es_referencia_cases(valor: object) -> bool:
    return (type(valor) is int and valor > 0) or (isinstance(valor, UUID) and valor.int != 0)


def _entero_positivo(valor: int, nombre: str) -> None:
    if type(valor) is not int or valor <= 0:
        raise ErrorDominioParticipacion(f"{nombre} debe ser un entero positivo.")


def _fecha_con_zona(valor: datetime) -> None:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ErrorDominioParticipacion("Las fechas deben incluir zona horaria.")


def _utc(valor: datetime) -> datetime:
    _fecha_con_zona(valor)
    return valor.astimezone(timezone.utc)


class EstadoIntento(StrEnum):
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    VENCIDO = "VENCIDO"


@dataclass(frozen=True)
class Participacion:
    id_participacion: int
    id_asignacion: int
    id_grupo_estudiante: int
    estado: str
    fecha_registro: datetime

    def __post_init__(self) -> None:
        for nombre in ("id_participacion", "id_asignacion", "id_grupo_estudiante"):
            _entero_positivo(getattr(self, nombre), nombre)
        if not self.estado.strip():
            raise ErrorDominioParticipacion("La participación debe tener un estado.")
        object.__setattr__(self, "fecha_registro", _utc(self.fecha_registro))


@dataclass(frozen=True)
class PasoSimulacion:
    """Selección registrada inmutable; no contiene corrección ni puntajes."""

    id_paso: int
    id_intento: int
    id_decision: IdentificadorCases
    id_opcion: IdentificadorCases
    numero_paso: int
    registrado_en: datetime
    tiempo_segundos: int
    reflexion_estudiante: str | None = None

    def __post_init__(self) -> None:
        for nombre in ("id_paso", "id_intento", "numero_paso"):
            _entero_positivo(getattr(self, nombre), nombre)
        for nombre in ("id_decision", "id_opcion"):
            if not es_referencia_cases(getattr(self, nombre)):
                raise ErrorDominioParticipacion(f"{nombre} debe ser una referencia válida de Cases.")
        object.__setattr__(self, "registrado_en", _utc(self.registrado_en))
        if type(self.tiempo_segundos) is not int or self.tiempo_segundos < 0:
            raise ErrorDominioParticipacion("tiempo_segundos debe ser un entero no negativo.")


@dataclass(frozen=True)
class Intento:
    id_intento: int
    id_participacion: int
    id_consentimiento: int
    numero_intento: int
    inicio: datetime
    tiempo_maximo: timedelta
    id_permiso_extra: int | None = None
    estado: EstadoIntento = EstadoIntento.EN_CURSO
    fin: datetime | None = None
    pasos: tuple[PasoSimulacion, ...] = ()

    def __post_init__(self) -> None:
        for nombre in ("id_intento", "id_participacion", "id_consentimiento", "numero_intento"):
            _entero_positivo(getattr(self, nombre), nombre)
        if self.id_permiso_extra is not None:
            _entero_positivo(self.id_permiso_extra, "id_permiso_extra")
        object.__setattr__(self, "inicio", _utc(self.inicio))
        if not isinstance(self.tiempo_maximo, timedelta) or self.tiempo_maximo <= timedelta(0):
            raise ErrorDominioParticipacion("El tiempo máximo debe ser positivo.")
        if not isinstance(self.estado, EstadoIntento):
            raise ErrorDominioParticipacion("Estado de intento desconocido.")
        if self.estado == EstadoIntento.EN_CURSO:
            if self.fin is not None:
                raise ErrorDominioParticipacion("Un intento en curso no tiene fecha de fin.")
        else:
            if self.fin is None:
                raise ErrorDominioParticipacion("Un intento cerrado debe conservar su fin.")
            object.__setattr__(self, "fin", _utc(self.fin))
            if not self.inicio <= self.fin <= self.vence_en:
                raise ErrorDominioParticipacion("La fecha de fin está fuera del intento.")
            if self.estado == EstadoIntento.VENCIDO and self.fin != self.vence_en:
                raise ErrorDominioParticipacion("El vencimiento cierra en el límite individual.")
            if self.estado == EstadoIntento.FINALIZADO and self.fin == self.vence_en:
                raise ErrorDominioParticipacion("En el límite corresponde un vencimiento.")
        if not isinstance(self.pasos, tuple):
            raise ErrorDominioParticipacion("Los pasos deben ser una tupla inmutable.")
        for campo in ("id_paso", "id_decision", "numero_paso"):
            valores = [getattr(paso, campo) for paso in self.pasos]
            if len(valores) != len(set(valores)):
                raise ErrorDominioParticipacion(f"No se permiten pasos duplicados por {campo}.")
        for paso in self.pasos:
            if paso.id_intento != self.id_intento:
                raise ErrorDominioParticipacion("El paso pertenece a otro intento.")
            if not self.inicio <= paso.registrado_en < self.vence_en:
                raise ErrorDominioParticipacion("El paso fue registrado fuera del tiempo permitido.")
            if self.fin is not None and paso.registrado_en > self.fin:
                raise ErrorDominioParticipacion("El paso es posterior al cierre.")
            transcurrido = int((paso.registrado_en - self.inicio).total_seconds())
            if paso.tiempo_segundos != transcurrido:
                raise ErrorDominioParticipacion("El tiempo del paso no coincide con el del servidor.")

    @classmethod
    def iniciar(
        cls,
        *,
        id_intento: int,
        id_participacion: int,
        id_consentimiento: int,
        numero_intento: int,
        tiempo_maximo: timedelta,
        reloj: Reloj,
        id_permiso_extra: int | None = None,
    ) -> "Intento":
        ahora = reloj.ahora()
        _fecha_con_zona(ahora)
        return cls(
            id_intento=id_intento,
            id_participacion=id_participacion,
            id_consentimiento=id_consentimiento,
            numero_intento=numero_intento,
            inicio=ahora.astimezone(timezone.utc),
            tiempo_maximo=tiempo_maximo,
            id_permiso_extra=id_permiso_extra,
        )

    @property
    def vence_en(self) -> datetime:
        # UTC evita que cambios de horario local alteren la duración transcurrida.
        return self.inicio.astimezone(timezone.utc) + self.tiempo_maximo

    def _ahora(self, reloj: Reloj) -> datetime:
        ahora = reloj.ahora()
        _fecha_con_zona(ahora)
        ahora = ahora.astimezone(timezone.utc)
        ultima_fecha = max((paso.registrado_en for paso in self.pasos), default=self.inicio)
        if ahora < max(self.inicio, ultima_fecha):
            raise ErrorDominioParticipacion("El reloj no puede retroceder sobre registros existentes.")
        return ahora

    def _exigir_editable(self, reloj: Reloj) -> datetime:
        if self.estado != EstadoIntento.EN_CURSO:
            raise IntentoNoEditable("El intento ya está cerrado.")
        ahora = self._ahora(reloj)
        if ahora >= self.vence_en:
            raise IntentoNoEditable("El tiempo individual se agotó.")
        return ahora

    def registrar_decision(
        self,
        *,
        id_paso: int,
        id_decision: IdentificadorCases,
        id_opcion: IdentificadorCases,
        reloj: Reloj,
        reflexion_estudiante: str | None = None,
    ) -> "Intento":
        ahora = self._exigir_editable(reloj)
        if any(paso.id_decision == id_decision for paso in self.pasos):
            raise RespuestaInmutable("La respuesta ya está registrada y es inmutable.")
        paso = PasoSimulacion(
            id_paso=id_paso,
            id_intento=self.id_intento,
            id_decision=id_decision,
            id_opcion=id_opcion,
            numero_paso=max((p.numero_paso for p in self.pasos), default=0) + 1,
            registrado_en=ahora,
            tiempo_segundos=int((ahora - self.inicio).total_seconds()),
            reflexion_estudiante=reflexion_estudiante,
        )
        return replace(self, pasos=(*self.pasos, paso))

    def modificar_decision(
        self,
        *,
        id_decision: IdentificadorCases,
        id_opcion: IdentificadorCases,
        reloj: Reloj,
        reflexion_estudiante: str | None = None,
    ) -> "Intento":
        self._exigir_editable(reloj)
        # Firma conservada para rechazar clientes antiguos, nunca para crear por PUT.
        raise RespuestaInmutable("No se permite modificar una respuesta, ni sustituir su reflexión.")

    def actualizar_vencimiento(self, reloj: Reloj) -> "Intento":
        if self.estado != EstadoIntento.EN_CURSO:
            return self
        if self._ahora(reloj) >= self.vence_en:
            return replace(self, estado=EstadoIntento.VENCIDO, fin=self.vence_en)
        return self

    def finalizar(self, reloj: Reloj) -> "Intento":
        if self.estado != EstadoIntento.EN_CURSO:
            return self
        ahora = self._ahora(reloj)
        if ahora >= self.vence_en:
            return replace(self, estado=EstadoIntento.VENCIDO, fin=self.vence_en)
        return replace(self, estado=EstadoIntento.FINALIZADO, fin=ahora)
