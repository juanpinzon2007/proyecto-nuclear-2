from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from decimal import Context, Decimal, localcontext

from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente


@dataclass(frozen=True)
class FechasPersistencia:
    """La zona de timestamps sin offset debe acordarse, no inferirse del equipo."""

    zona_sin_offset: tzinfo | None

    def desde_db(self, valor: datetime) -> datetime:
        if not isinstance(valor, datetime):
            raise MapeoPersistenciaPendiente("La columna temporal no contiene datetime.")
        if valor.tzinfo is not None and valor.utcoffset() is not None:
            return valor.astimezone(timezone.utc)
        if self.zona_sin_offset is None:
            raise MapeoPersistenciaPendiente("Falta acordar la zona de los timestamps sin offset.")
        candidatos = set()
        for fold in (0, 1):
            posible = valor.replace(tzinfo=self.zona_sin_offset, fold=fold)
            utc = posible.astimezone(timezone.utc)
            if utc.astimezone(self.zona_sin_offset).replace(tzinfo=None) == valor:
                candidatos.add(utc)
        if len(candidatos) != 1:
            raise MapeoPersistenciaPendiente("El timestamp local es ambiguo o inexistente.")
        return candidatos.pop()

    def hacia_db(self, valor: datetime, *, sin_offset: bool) -> datetime:
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise MapeoPersistenciaPendiente("El dominio debe proporcionar una fecha con zona.")
        utc = valor.astimezone(timezone.utc)
        if not sin_offset:
            return utc
        if self.zona_sin_offset is None:
            raise MapeoPersistenciaPendiente("No eliminar un offset sin política temporal explícita.")
        local = utc.astimezone(self.zona_sin_offset).replace(tzinfo=None)
        if self.desde_db(local) != utc:
            raise MapeoPersistenciaPendiente("El timestamp no puede reconstruirse sin pérdida.")
        return local


def decimal_exacto(valor: Decimal, *, precision: int, escala: int) -> Decimal:
    """Valida compatibilidad NUMERIC(p,s), sin decidir redondeos académicos."""
    if not isinstance(valor, Decimal) or not valor.is_finite() or valor < 0:
        raise MapeoPersistenciaPendiente("Se requiere Decimal finito no negativo.")
    if type(precision) is not int or type(escala) is not int or not 0 <= escala <= precision or precision <= 0:
        raise ValueError("Precisión/escala NUMERIC inválidas.")
    digitos = len(valor.as_tuple().digits) + abs(valor.as_tuple().exponent)
    with localcontext(Context(prec=max(28, digitos + precision + escala + 5))):
        cuantizado = valor.quantize(Decimal(1).scaleb(-escala))
        if cuantizado != valor:
            raise MapeoPersistenciaPendiente("La columna perdería decimales; no redondear automáticamente.")
        if valor >= Decimal(1).scaleb(precision - escala):
            raise MapeoPersistenciaPendiente("El valor excede el rango de la columna NUMERIC.")
        return cuantizado
