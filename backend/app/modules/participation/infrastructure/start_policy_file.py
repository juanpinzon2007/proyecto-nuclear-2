"""Políticas puras de inicio y provisión desde una decisión fijada por el servidor."""
from hashlib import sha256
import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.scheduling.domain.ingress_policy import fecha_utc, PoliticaTemporalNoDisponible


class DecisionInicio(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    ambito: Literal["PRODUCCION", "LABORATORIO"]
    referencia_decision: str = Field(min_length=1, max_length=500)
    aprobacion: Literal["APROBADA", "LABORATORIO_PENDIENTE"]
    estado_inicial_participacion: Literal["pendiente"]
    estados_asignacion: list[Literal["programada"]] = Field(min_length=1, max_length=1)
    intentos_base: Literal[1]
    usos_permiso_extra: Literal[1]
    referencias_consentimiento: list[str] = Field(min_length=1)
    incluye_limite_ingreso: bool


class EvidenciaPoliticaInicio(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    politica_id: str = Field(min_length=1, max_length=100)
    politica_version: str = Field(min_length=1, max_length=100)
    politica_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    politica_ambito: Literal["PRODUCCION", "LABORATORIO"]
    referencia_decision: str = Field(min_length=1, max_length=500)


class PoliticasInicioArchivo:
    def __init__(self, decision: DecisionInicio, huella: str):
        self.decision = decision
        self.huella = huella

    def _validar_ventana(self, condiciones):
        try:
            ahora, apertura, cierre, limite = map(fecha_utc, (
                condiciones.ahora, condiciones.apertura, condiciones.cierre,
                condiciones.limite_ingreso))
        except PoliticaTemporalNoDisponible:
            raise ReglaPendiente("Las fechas de inicio requieren zona verificable.") from None
        if not apertura <= limite <= cierre or apertura >= cierre:
            raise ReglaPendiente("La ventana asignada es incoherente.")
        limite_admitido = ahora < limite or self.decision.incluye_limite_ingreso and ahora == limite
        if (condiciones.estado_asignacion not in self.decision.estados_asignacion
                or not apertura <= ahora < cierre or not limite_admitido):
            raise AccesoDenegado("Inicio fuera de la ventana o estado autorizados.")

    def _trazar(self, operacion):
        logging.getLogger(__name__).info("politica_participacion_autorizada", extra={
            "politica_id": self.decision.id, "politica_version": self.decision.version,
            "politica_sha256": self.huella, "politica_ambito": self.decision.ambito,
            "referencia_decision": self.decision.referencia_decision, "operacion": operacion})

    def autorizar_inicio(self, condiciones):
        self._validar_ventana(condiciones)
        if condiciones.version_consentimiento not in self.decision.referencias_consentimiento:
            raise ReglaPendiente("La decisión no incluye la referencia de consentimiento.")
        try:
            aceptado = fecha_utc(condiciones.aceptado_en)
            ahora = fecha_utc(condiciones.ahora)
        except PoliticaTemporalNoDisponible:
            raise ReglaPendiente("La aceptación requiere fecha verificable.") from None
        if aceptado > ahora:
            raise AccesoDenegado("La aceptación es posterior al inicio.")
        if type(condiciones.intentos_base) is not int or condiciones.intentos_base != self.decision.intentos_base:
            raise ReglaPendiente("El cupo base persistido difiere de la decisión.")
        if type(condiciones.numero_intento) is not int or condiciones.numero_intento < 1:
            raise AccesoDenegado("Número de intento inválido.")
        if condiciones.id_permiso_extra is None:
            if (condiciones.numero_intento != 1 or condiciones.cantidad_extra is not None
                    or condiciones.usos_permiso != 0):
                raise AccesoDenegado("El cupo base está agotado.")
        elif (condiciones.id_participacion is None or condiciones.numero_intento <= 1
                or type(condiciones.cantidad_extra) is not int
                or condiciones.cantidad_extra != self.decision.usos_permiso_extra
                or type(condiciones.usos_permiso) is not int or condiciones.usos_permiso != 0):
            raise AccesoDenegado("El permiso adicional no dispone de un uso autorizado.")
        self._trazar("INICIAR")

    def autorizar_vinculacion(self, condiciones):
        self._validar_ventana(condiciones)
        self._trazar("VINCULAR")
        return self.decision.estado_inicial_participacion


class PoliticaInicioArchivo:
    def __init__(self, politicas):
        self.politicas = politicas

    def autorizar(self, condiciones):
        return self.politicas.autorizar_inicio(condiciones)

    def evidencia(self):
        d = self.politicas.decision
        return EvidenciaPoliticaInicio(politica_id=d.id, politica_version=d.version,
            politica_sha256=self.politicas.huella, politica_ambito=d.ambito,
            referencia_decision=d.referencia_decision)


class PoliticaVinculacionArchivo:
    def __init__(self, politicas):
        self.politicas = politicas

    def autorizar(self, condiciones):
        return self.politicas.autorizar_vinculacion(condiciones)


def cargar_politicas_inicio(*, archivo, huella, ambito):
    """Lee y fija una instantánea. Ningún valor del comando HTTP configura reglas."""
    if (ambito not in ("PRODUCCION", "LABORATORIO") or not archivo
            or not isinstance(huella, str) or len(huella) != 64
            or any(c not in "0123456789abcdef" for c in huella)):
        raise ReglaPendiente("Falta configuración verificada de la decisión de inicio.")
    try:
        original = Path(archivo).read_bytes()
        if sha256(original).hexdigest() != huella:
            raise ValueError()
        datos = json.loads(original.decode("utf-8"))
        canonico = json.dumps(datos, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if original != canonico:
            raise ValueError()
        decision = DecisionInicio.model_validate(datos)
        textos = [decision.id, decision.version, decision.referencia_decision,
                  decision.estado_inicial_participacion, *decision.referencias_consentimiento]
        if (decision.ambito != ambito or any(not t.strip() or t != t.strip() for t in textos)
                or len(set(decision.referencias_consentimiento)) != len(decision.referencias_consentimiento)
                or any(len(t) > 30 for t in decision.referencias_consentimiento)
                or ambito == "PRODUCCION" and decision.aprobacion != "APROBADA"
                or type(datos["intentos_base"]) is not int or type(datos["usos_permiso_extra"]) is not int):
            raise ValueError()
    except (OSError, ValueError, TypeError, ValidationError):
        raise ReglaPendiente("La decisión de inicio no es verificable para este ámbito.") from None
    return PoliticasInicioArchivo(decision, huella)
