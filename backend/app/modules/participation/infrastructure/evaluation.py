"""Composición interna 8C: evidencia SQL real y previsualización sin resultados.

No configura HTTP, notas oficiales, políticas académicas o un repositorio falso.
Una instancia de ServicioEvaluacion por operación, igual que la composición 8B.
"""
from dataclasses import dataclass
from uuid import UUID

from app.modules.cases.application.evaluation_snapshot import RubricaHistorica, consultar_rubrica_historica
from app.modules.cases.application.answer_feedback import ExplicacionSeleccion, consultar_explicaciones_seleccionadas
from app.modules.participation.application.errors import AccesoDenegado
from app.modules.participation.application.evaluation_service import ServicioEvaluacion
from app.modules.participation.application.evaluation_mapping import MapeoRubricaEvaluacion, validar_mapeo_historico
from app.modules.participation.application.evaluation_ports import PoliticaEvaluacionPort, AusenciasPort
from app.modules.participation.domain.entities import Intento, EstadoIntento
from app.modules.participation.domain.evaluation import EvaluacionInconsistente, PoliticaEvaluacionPendiente, RubricaEvaluacion, ModalidadEvaluacion
from app.modules.participation.infrastructure.composition import (
    _Alcance, IdentityIntentoSQLAlchemy, SchedulingIntentoSQLAlchemy, CasesIntentoSQLAlchemy,
)
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.participation.infrastructure.unit_of_work import UnidadTrabajoSQLAlchemy
from app.modules.participation.application.dto import selecciones_de
from app.modules.participation.application.academic_policy import PoliticaAcademicaConfirmada, MapeoEscala100
from app.modules.cases.domain.exceptions import CasoNoEncontradoError


@dataclass(frozen=True)
class EvidenciasHistoricas:
    intento: Intento
    rubrica: RubricaHistorica


@dataclass(frozen=True)
class RetroalimentacionInterna:
    """Preparación técnica; NO un resultado académico confirmado/publicado."""
    id_intento: int
    id_participacion: int
    version_id: UUID
    rubrica_id: UUID
    version_regla: str
    respuestas: tuple[ExplicacionSeleccion, ...]


def _unidad(crear_sesion, fechas):
    return UnidadTrabajoSQLAlchemy(lambda s: RepositorioParticipacionSQLAlchemy(s, fechas=fechas), crear_sesion=crear_sesion)


def _evidencias(alcance, intento):
    if intento.estado == EstadoIntento.EN_CURSO:
        raise EvaluacionInconsistente("La evaluación exige el cierre persistido del intento.")
    fila = alcance.datos()
    cases = CasesIntentoSQLAlchemy(alcance, None)
    for seleccion in selecciones_de(intento):
        cases.validar_opcion(id_caso=fila.id_caso, id_decision=seleccion.id_decision, id_opcion=seleccion.id_opcion)
    try:
        rubrica = consultar_rubrica_historica(alcance.sesion(), version_id=fila.version_caso_id)
    except CasoNoEncontradoError:
        raise EvaluacionInconsistente("La referencia histórica de evaluación no es coherente.") from None
    if rubrica.id_caso_academico != fila.id_caso or not rubrica.version_regla.strip():
        raise EvaluacionInconsistente("La referencia histórica de evaluación está incompleta.")
    return EvidenciasHistoricas(intento, rubrica)


def _evidencias_autorizadas(trabajo, alcance, usuario, id_intento):
    intento = trabajo.repositorio.obtener_intento(id_intento)
    IdentityIntentoSQLAlchemy(alcance).autorizar_acceso(
        id_estudiante=int(usuario.id_usuario), id_participacion=intento.id_participacion)
    return _evidencias(alcance, intento)


def consultar_evidencias_8c(*, usuario, id_intento, fechas, crear_sesion) -> EvidenciasHistoricas:
    """Lectura interna autorizada de intento cerrado y fuente cruda de rúbrica.

    No clasifica, no califica, no vence intentos ni publica puntajes.
    """
    trabajo = _unidad(crear_sesion, fechas)
    alcance = _Alcance(lambda: trabajo.sesion, usuario, id_intento, fechas)
    with trabajo:
        return _evidencias_autorizadas(trabajo, alcance, usuario, id_intento)


def preparar_retroalimentacion_8c(*, usuario, id_intento, fechas, crear_sesion) -> RetroalimentacionInterna:
    """Prepara feedback existente bajo titularidad/cierre; no publica ni persiste.

    Usa la UoW completa, no una autorización de lectura anterior. No se conecta
    a las rutas de resultados ni toma una previsualización como nota oficial.
    """
    trabajo = _unidad(crear_sesion, fechas)
    alcance = _Alcance(lambda: trabajo.sesion, usuario, id_intento, fechas)
    with trabajo:
        evidencia = _evidencias_autorizadas(trabajo, alcance, usuario, id_intento)
        try:
            respuestas = consultar_explicaciones_seleccionadas(trabajo.sesion,
                version_id=evidencia.rubrica.version_id,
                selecciones=tuple((p.id_decision, p.id_opcion) for p in evidencia.intento.pasos))
        except CasoNoEncontradoError:
            raise EvaluacionInconsistente("El feedback no corresponde a las respuestas históricas.") from None
        return RetroalimentacionInterna(id_intento, evidencia.intento.id_participacion,
            evidencia.rubrica.version_id, evidencia.rubrica.rubrica_id,
            evidencia.rubrica.version_regla, respuestas)


class CasesEvaluacionSQLAlchemy(CasesIntentoSQLAlchemy):
    def __init__(self, alcance, recorrido, mapeo: MapeoRubricaEvaluacion | None):
        super().__init__(alcance, recorrido)
        self.mapeo = mapeo

    def obtener_marco_evaluacion(self, *, id_caso, id_participacion, id_intento, selecciones):
        fila = self.a.datos()
        if (id_caso, id_participacion, id_intento) != (fila.id_caso, fila.id_participacion, self.a.id_intento):
            raise AccesoDenegado("Referencia de evaluación no disponible.")
        intento = RepositorioParticipacionSQLAlchemy(self.a.sesion(), fechas=self.a.fechas).obtener_intento(id_intento)
        if selecciones != selecciones_de(intento):
            raise EvaluacionInconsistente("Las selecciones no coinciden con el intento persistido.")
        fuente = _evidencias(self.a, intento).rubrica
        if self.mapeo is None:
            raise PoliticaEvaluacionPendiente("Falta máximo y traducción aprobada de puntajes a logros porcentuales.")
        rubrica = self.mapeo.preparar(fuente)
        validar_mapeo_historico(fuente, rubrica)
        return rubrica, self.obtener_recorrido(id_caso=id_caso, selecciones=selecciones)


class _PoliticaBaseDocumentada:
    """RN-14: tiempo agotado exige parcial; la fórmula sigue sin configurar.

    Fuente centralizada Ingeniería Software II, página 7. No clasifica el cierre
    voluntario ni confirma ausencia por falta de respuestas.
    """
    def clasificar(self, *, intento, decisiones_aplicables):
        if intento.estado == EstadoIntento.VENCIDO:
            return ModalidadEvaluacion.PARCIAL
        raise PoliticaEvaluacionPendiente("Falta clasificación académica aprobada.")

    def preparar_calculo(self, **_):
        raise PoliticaEvaluacionPendiente("Falta fórmula, agregación y redondeo aprobados.")

    def confirmar_ausencia(self, **_):
        raise PoliticaEvaluacionPendiente("Faltan condiciones académicas de ausencia.")


def crear_evaluacion_8c(*, usuario, id_intento, fechas, crear_sesion,
                       recorrido=None, mapeo: MapeoRubricaEvaluacion | None = None,
                       politica: PoliticaEvaluacionPort | None = None,
                       ausencias: AusenciasPort | None = None) -> ServicioEvaluacion:
    trabajo = _unidad(crear_sesion, fechas)
    alcance = _Alcance(lambda: trabajo.sesion, usuario, id_intento, fechas)
    bloqueada = _PoliticaBaseDocumentada()
    # Scheduling solo se usa para la referencia de asignación, no para editar ni
    # reautorizar ingreso. Nunca se llama reloj en este recorrido de evaluación.
    return ServicioEvaluacion(lambda: trabajo, IdentityIntentoSQLAlchemy(alcance),
        SchedulingIntentoSQLAlchemy(alcance, None, None),
        CasesEvaluacionSQLAlchemy(alcance, recorrido, MapeoEscala100(mapeo) if politica is None else mapeo),
        politica if politica is not None else PoliticaAcademicaConfirmada(),
        ausencias if ausencias is not None else bloqueada)
