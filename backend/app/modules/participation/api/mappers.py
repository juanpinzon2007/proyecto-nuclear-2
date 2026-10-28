from app.modules.participation.api.schemas import (
    CriterioResultadoRespuesta, IntentoRespuesta, ProgresoRespuesta,
    ReferenciaAcademicaRespuesta, ResultadoDefinitivoRespuesta,
)
from app.modules.participation.application.dto import ProgresoIntento, ResumenIntento
from app.modules.participation.domain.evaluation import DatosEvaluacion


def mapear_intento(datos: ResumenIntento) -> IntentoRespuesta:
    return IntentoRespuesta.model_validate(datos)


def mapear_progreso(datos: ProgresoIntento) -> ProgresoRespuesta:
    # Lista blanca del esquema; no se serializa el agregado entero ni su rúbrica.
    return ProgresoRespuesta.model_validate(datos)


def mapear_resultado(datos: DatosEvaluacion) -> ResultadoDefinitivoRespuesta:
    # Application ya verificó autorización, cierre y confirmación de persistencia.
    # El esquema exige nota/política; no convierte un candidato vacío en resultado.
    return ResultadoDefinitivoRespuesta(
        id_participacion=datos.id_participacion, id_intento=datos.id_intento,
        modalidad=datos.modalidad,
        referencia=ReferenciaAcademicaRespuesta.model_validate(datos.referencia),
        nota_final=format(datos.nota_final, "f"),
        politica_calculo=datos.politica_calculo,
        criterios=[CriterioResultadoRespuesta(
            id_criterio=c.id_criterio, id_nivel=c.id_nivel,
            puntaje_obtenido=format(c.puntaje_obtenido, "f"),
        ) for c in datos.criterios],
    )
