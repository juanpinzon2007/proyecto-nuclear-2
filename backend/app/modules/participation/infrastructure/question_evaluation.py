"""Cálculo técnico interno autorizado. Sin escritura ni publicación oficial.

La persistencia actual exige un nivel discreto por criterio y no representa
promedios arbitrarios: no se inserta un detalle falso para superar esa barrera.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import inspect

from app.modules.cases.infrastructure.scoring import consultar_configuracion_preguntas
from app.modules.participation.application.result_provenance import canonico, fuentes_motor
from app.modules.participation.application.evaluation_service import seleccionar_estrategia
from app.modules.participation.domain.calculador_rubrica import CalculadorRubrica
from app.modules.participation.domain.entities import EstadoIntento
from app.modules.participation.domain.evaluation import ContextoEvaluacion, ModalidadEvaluacion, EvaluacionInconsistente, ReferenciaAcademica
from app.modules.participation.infrastructure.evaluation import _unidad, _evidencias_autorizadas
from app.modules.participation.infrastructure.composition import _Alcance
from app.modules.participation.application.question_details import detalle_exacto


@dataclass(frozen=True)
class CalificacionTecnicaPreguntas:
    id_intento: int
    modalidad: ModalidadEvaluacion
    preguntas_exigidas: int
    preguntas_respondidas: int
    pendientes_con_cero: int
    nota_final: Decimal
    procedencia: str
    sha256: str
    oficial: bool = False
    persistido: bool = False

    @property
    def id_participacion(self):
        import json
        return json.loads(self.procedencia)['intento']['id_participacion']


def calcular_intento_por_preguntas(*, usuario, id_intento, fechas, crear_sesion):
    trabajo = _unidad(crear_sesion, fechas)
    alcance = _Alcance(lambda: trabajo.sesion, usuario, id_intento, fechas)
    with trabajo:
        historico = _evidencias_autorizadas(trabajo, alcance, usuario, id_intento)
        config = consultar_configuracion_preguntas(trabajo.sesion, version_id=historico.rubrica.version_id)
        return preparar_calculo_historico(historico,config)


def preparar_calculo_historico(historico,config):
    """Mismo cálculo para preview, escritor y verificador; no autoriza actores."""
    intento, rubrica = historico.intento, historico.rubrica
    # El llamador adjunta la configuración leída en SU transacción.
    selecciones = tuple((p.id_decision, p.id_opcion) for p in intento.pasos)
    ruta, total, puntos = config.seleccionar(selecciones)
    if intento.estado == EstadoIntento.FINALIZADO and not ruta.finalizado:
        raise EvaluacionInconsistente("El cierre voluntario no completó el recorrido.")
    modalidad = ModalidadEvaluacion.PARCIAL if intento.estado == EstadoIntento.VENCIDO else ModalidadEvaluacion.COMPLETA
    # Las estrategias existentes verifican las evidencias reales del prefijo.
    # No elegir una rama futura para inventar preguntas pendientes.
    referencia = ReferenciaAcademica(rubrica.id_caso_academico, rubrica.rubrica_id, rubrica.referencia_versionada)
    seleccionar_estrategia(modalidad).preparar(ContextoEvaluacion(referencia, intento.id_participacion,
        modalidad, ruta.decisiones, intento))
    nota = CalculadorRubrica().calcular_preguntas(puntajes=puntos, total_exigidas=total)
    politica = canonico(dict(id='PREGUNTAS_100_V1',version='1',formula='suma_puntajes/total_ruta',
        redondeo='ROUND_HALF_UP',decimales=2,motor=fuentes_motor(),
        validador=inspect.getsource(type(config)),contabilidad=inspect.getsource(detalle_exacto)))
    documento = canonico(dict(formato='preguntas-100-v1',configuracion=config,intento=intento,
        rubrica=rubrica,denominador=total,puntajes=puntos,nota_final=nota,
        formula='suma_puntajes/total_ruta',redondeo='ROUND_HALF_UP',decimales=2,
        motor=fuentes_motor(),validador=inspect.getsource(type(config)),
        configuracion_documento=canonico(config),politica_documento=politica,
        exacto=detalle_exacto(config,selecciones)))
    return CalificacionTecnicaPreguntas(intento.id_intento, modalidad,total,len(puntos),total-len(puntos),nota,
        documento,hashlib.sha256(documento.encode('utf-8')).hexdigest())
