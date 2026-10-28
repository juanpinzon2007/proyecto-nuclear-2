"""Aplicación aislada y dependencias falsas, exclusivas de las pruebas HTTP."""

from contextlib import contextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.participation.api.dependencies import (
    EstudianteAutenticado, obtener_estudiante_actual, obtener_facade,
)
from app.modules.participation.api.router import router
from app.modules.participation.application.evaluation_service import ServicioEvaluacion
from app.modules.participation.application.facade import ParticipacionFacade
from app.modules.participation.tests.evaluation_fakes import (
    AlmacenEvaluacionFalso, AusenciasFalsas, CasesEvaluacionFalso, PoliticaEvaluacionFalsa,
)
from app.modules.participation.tests.fakes import IdentityFalso, RelojFalso, SchedulingFalso

INICIO_URL = "/api/v1/participations/20/attempts"
DECISION_URL = "/api/v1/attempts/10/decisions/50"
PROGRESO_URL = "/api/v1/attempts/10/progress"
FIN_URL = "/api/v1/attempts/10/finish"
RESULTADO_URL = "/api/v1/participations/20/attempts/10/result"
AUSENCIA_URL = "/api/v1/participations/20/absence-result"


@dataclass
class EntornoHTTP:
    app: FastAPI
    client: TestClient
    almacen: AlmacenEvaluacionFalso
    reloj: RelojFalso
    facade: ParticipacionFacade
    cases: CasesEvaluacionFalso
    identity: IdentityFalso
    politica: PoliticaEvaluacionFalsa
    scheduling: SchedulingFalso
    ausencias: AusenciasFalsas

    def iniciar(self):
        respuesta = self.client.post(INICIO_URL, json={"id_consentimiento": 30})
        assert respuesta.status_code == 201, respuesta.text
        return respuesta

    def responder(self):
        respuesta = self.client.post(DECISION_URL, json={"id_opcion": 60})
        assert respuesta.status_code == 201, respuesta.text
        return respuesta

    def cerrar(self, *, completo=True):
        self.iniciar()
        self.responder()
        if completo:
            respuesta = self.client.post("/api/v1/attempts/10/decisions/51", json={"id_opcion": 63})
            assert respuesta.status_code == 201
        respuesta = self.client.post(FIN_URL)
        assert respuesta.status_code == 200
        return respuesta


@contextmanager
def crear_entorno_http():
    almacen, reloj = AlmacenEvaluacionFalso(), RelojFalso()
    identity, scheduling = IdentityFalso(), SchedulingFalso()
    cases, politica, ausencias = CasesEvaluacionFalso(), PoliticaEvaluacionFalsa(), AusenciasFalsas()
    evaluacion = ServicioEvaluacion(
        almacen.unidad_evaluacion, identity, scheduling, cases, politica, ausencias,
    )
    facade = ParticipacionFacade(
        fabrica=almacen.unidad, identity=identity, scheduling=scheduling,
        cases=cases, reloj=reloj, evaluacion=evaluacion,
    )
    app = FastAPI(debug=False)
    app.include_router(router)
    app.dependency_overrides[obtener_estudiante_actual] = lambda: EstudianteAutenticado(id_estudiante=7)
    app.dependency_overrides[obtener_facade] = lambda: facade
    try:
        # El modo por defecto propaga excepciones inesperadas: no ocultar fallos.
        with TestClient(app) as client:
            yield EntornoHTTP(app, client, almacen, reloj, facade, cases, identity, politica, scheduling, ausencias)
    finally:
        app.dependency_overrides.clear()
