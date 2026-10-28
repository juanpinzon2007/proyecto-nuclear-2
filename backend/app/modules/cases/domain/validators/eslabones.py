"""Eslabones concretos de la validación de publicación (RF-09)."""

from decimal import Decimal

from app.modules.cases.domain.entities.caso import VersionCaso
from app.modules.cases.domain.validators.base import ValidadorCaso
from app.modules.cases.domain.validators.resultado import ResultadoValidacion

MIN_OPCIONES = 2
PESO_TOTAL_RUBRICA = Decimal(100)


class ValidadorEstructura(ValidadorCaso):
    """Existen escenarios y el tiempo estimado es válido."""

    def _validar(self, version: VersionCaso, resultado: ResultadoValidacion) -> None:
        if not version.nombre.strip():
            resultado.agregar_error("El caso debe tener nombre.")
        if version.tiempo_estimado_min <= 0:
            resultado.agregar_error("El tiempo estimado debe ser mayor que 0 minutos.")
        if not version.escenarios:
            resultado.agregar_error("El caso debe tener al menos un escenario.")


class ValidadorPreguntas(ValidadorCaso):
    """Todo escenario tiene al menos una pregunta."""

    def _validar(self, version: VersionCaso, resultado: ResultadoValidacion) -> None:
        for escenario in version.escenarios:
            if not escenario.preguntas:
                resultado.agregar_error(f"El escenario {escenario.orden} no tiene preguntas.")


class ValidadorRespuestas(ValidadorCaso):
    """Mínimo 2 opciones, con correctas e incorrectas, todas justificadas."""

    def _validar(self, version: VersionCaso, resultado: ResultadoValidacion) -> None:
        for escenario in version.escenarios:
            for pregunta in escenario.preguntas:
                ref = f"escenario {escenario.orden}, pregunta {pregunta.orden}"
                if len(pregunta.opciones) < MIN_OPCIONES:
                    resultado.agregar_error(
                        f"({ref}) requiere al menos {MIN_OPCIONES} opciones."
                    )
                if not pregunta.correctas:
                    resultado.agregar_error(f"({ref}) no tiene opción correcta.")
                if not pregunta.incorrectas:
                    resultado.agregar_error(f"({ref}) no tiene opción incorrecta.")
                for opcion in pregunta.opciones:
                    if not opcion.tiene_justificacion:
                        resultado.agregar_error(
                            f"({ref}) la opción {opcion.orden} carece de justificación."
                        )


class ValidadorRubrica(ValidadorCaso):
    """La rúbrica existe, sus pesos suman 100 y cada criterio tiene niveles."""

    def _validar(self, version: VersionCaso, resultado: ResultadoValidacion) -> None:
        rubrica = version.rubrica
        if rubrica is None:
            resultado.agregar_error("El caso no tiene rúbrica asociada.")
            return
        if not rubrica.criterios:
            resultado.agregar_error("La rúbrica no tiene criterios.")
            return
        if rubrica.peso_total != PESO_TOTAL_RUBRICA:
            resultado.agregar_error(
                f"Los pesos de la rúbrica suman {rubrica.peso_total}, deben sumar 100."
            )
        for criterio in rubrica.criterios:
            if not criterio.niveles:
                resultado.agregar_error(f"El criterio '{criterio.nombre}' no tiene niveles.")


class ValidadorMapeoOpciones(ValidadorCaso):
    """Cada opción tiene una valoración para cada criterio de la rúbrica.

    Si no hay rúbrica o criterios, no reporta nada: ya lo hace ``ValidadorRubrica``.
    """

    def _validar(self, version: VersionCaso, resultado: ResultadoValidacion) -> None:
        if version.rubrica is None or not version.rubrica.criterios:
            return
        criterios = {c.id: c.nombre for c in version.rubrica.criterios}
        for escenario in version.escenarios:
            for pregunta in escenario.preguntas:
                for opcion in pregunta.opciones:
                    ref = (
                        f"escenario {escenario.orden}, pregunta {pregunta.orden}, "
                        f"opción {opcion.orden}"
                    )
                    for criterio_id, nombre in criterios.items():
                        if criterio_id not in opcion.valoraciones:
                            resultado.agregar_error(
                                f"({ref}) no tiene valoración para el criterio '{nombre}'."
                            )
                    if any(cid not in criterios for cid in opcion.valoraciones):
                        resultado.agregar_error(
                            f"({ref}) valora un criterio que no pertenece a la rúbrica."
                        )


def construir_cadena_publicacion() -> ValidadorCaso:
    """Ensambla Estructura → Preguntas → Respuestas → Rúbrica → Mapeo de opciones."""
    cabeza = ValidadorEstructura()
    cabeza.enlazar(ValidadorPreguntas()).enlazar(ValidadorRespuestas()).enlazar(
        ValidadorRubrica()
    ).enlazar(ValidadorMapeoOpciones())
    return cabeza

