"""Evidencias PT-DCP-01: solo fixtures existentes y PostgreSQL desechable.

No es una aplicación productiva. Ejecutar con ejecutar.ps1, nunca con URLs externas.
"""
from decimal import Decimal
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa

from tests.integration.test_scheduling_participation import http, simulacion, pg_grafo, ruta  # noqa: F401
from tests.integration.test_participation_persistence import contexto
from tests.integration.test_evaluation_feedback import cerrar_fixture
from tests.integration.test_academic_policy import (
    academico, calculo, rubrica, docente, escribir, leer,
)
from app.modules.identity.domain.errors import AccesoDenegado
from app.modules.participation.infrastructure.models import PasoSimulacionModel as Paso
from app.modules.participation.infrastructure.result_models import ResultadoCriterioModel as Detalle


@pytest.fixture
def evidencia(request, pg_grafo):
    carpeta = Path(os.environ["SPS_EVIDENCIAS_DIR"])
    carpeta.mkdir(parents=True, exist_ok=True)
    with pg_grafo.connect() as s:
        laboratorio = dict(
            base=s.scalar(sa.text("SELECT current_database()")),
            version_postgresql=s.scalar(sa.text("SHOW server_version")),
            revision_alembic=s.scalar(sa.text("SELECT version_num FROM alembic_version")),
            host=pg_grafo.url.host, puerto=pg_grafo.url.port,
            aislamiento="Contenedor nuevo del fixture motor_postgresql_desechable; PGDATA tmpfs; sin volúmenes persistentes.",
        )
    (carpeta / "laboratorio.json").write_text(json.dumps(laboratorio, ensure_ascii=False, indent=2), encoding="utf-8")
    pasos = []
    def registrar(titulo, *, precondiciones, entrada, operacion, esperado, obtenido, cumple, fuente):
        registro = dict(paso=len(pasos)+1, titulo=titulo, ambito="LABORATORIO; NO PRODUCTIVO",
                        precondiciones=precondiciones, entrada=entrada, operacion=operacion,
                        esperado=esperado, obtenido=obtenido, cumple=bool(cumple), test_fuente=fuente)
        pasos.append(registro)
        documento = dict(escenario=request.node.name, pasos=pasos)
        (carpeta / (request.node.name+".json")).write_text(
            json.dumps(documento, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("\n"+"="*72+"\n"+json.dumps(registro, ensure_ascii=False, indent=2, default=str), flush=True)
        assert cumple, f"No se cumple el resultado esperado: {titulo}"
        if os.environ.get("SPS_EVIDENCIA_PAUSA") == "1":
            input("Capture este paso. Pulse ENTER para continuar (no cierre la terminal): ")
    return registrar


def http_paso(ev, h, titulo, metodo, path, esperado, *, body=None, codigo=None):
    r = h.client.request(metodo, path, headers=h.headers, **({"json": body} if body is not None else {}))
    contenido = r.json()
    ev(titulo, precondiciones="Intento sintético existente; JWT real de laboratorio; matrícula y convocatoria propias; sesión EN_CURSO; reloj controlado dentro del horario; grafo SQL publicado.",
       entrada=body, operacion=f"{metodo} {path} (Bearer omitido de la evidencia)",
       esperado=dict(http=esperado, codigo=codigo), obtenido=dict(http=r.status_code, body=contenido),
       cumple=r.status_code == esperado and (codigo is None or contenido.get("detail", {}).get("codigo") == codigo),
       fuente="backend/tests/integration/test_scheduling_participation.py::test_http_real_jwt_sql_respuesta_progreso_put_y_cierre")
    return contenido


def test_01_participation_http(http, evidencia):
    h, ev = http, evidencia
    c = h.c
    path, body = ruta(c)
    http_paso(ev,h,"Primera respuesta registrada", "POST",path,201,body=body)
    cambiado = {"id_opcion": str(c.version.escenarios[0].preguntas[0].opciones[1].id)}
    http_paso(ev,h,"Sustitución mediante PUT rechazada", "PUT",path,409,body=cambiado,codigo="RESPUESTA_INMUTABLE")
    with c.sesiones() as s:
        seleccion = s.execute(sa.select(Paso.id_opcion).where(Paso.id_intento == c.ik)).scalars().all()
    ev("La selección original permanece en PostgreSQL", precondiciones="POST confirmado y PUT rechazado",
       entrada=dict(id_intento=c.ik), operacion="SELECT id_opcion FROM paso_simulacion WHERE id_intento = :id",
       esperado=[body["id_opcion"]], obtenido=seleccion,
       cumple=[str(x) for x in seleccion] == [body["id_opcion"]],
       fuente="backend/tests/integration/test_immutable_answers.py::test_put_logico_rechazado_conserva_original")
    p = http_paso(ev,h,"Consulta privada de progreso", "GET",f"/api/v1/attempts/{c.ik}/progress",200)
    prohibidos = ("es_correcta", "puntaje", "justificacion", "nota_final")
    ev("Progreso sin corrección ni notas", precondiciones="Una respuesta registrada",
       entrada=dict(campos_no_permitidos=prohibidos), operacion="Inspección del JSON HTTP anterior",
       esperado="respondidas=1; sin campos de corrección", obtenido=p,
       cumple=p["respondidas"] == 1 and all(x not in json.dumps(p) for x in prohibidos),
       fuente="backend/tests/integration/test_scheduling_participation.py::test_http_real_jwt_sql_respuesta_progreso_put_y_cierre")
    otro = contexto(c.engine)
    token_ajeno = h.tokens.emitir(str(otro.alumno),str(otro.datos["convocatoria_id"]))
    ajeno = h.client.get(f"/api/v1/attempts/{c.ik}/progress",headers={"Authorization":"Bearer "+token_ajeno})
    ev("Progreso ajeno rechazado por HTTP", precondiciones="Segundo estudiante sintético, JWT válido y convocatoria propia, pero intento de otro titular",
       entrada=dict(id_usuario_solicitante=otro.alumno,id_intento_ajeno=c.ik),
       operacion=f"GET /api/v1/attempts/{c.ik}/progress con JWT del otro alumno (omitido)",
       esperado="HTTP 403 sin selecciones privadas", obtenido=dict(http=ajeno.status_code,body=ajeno.json()),
       cumple=ajeno.status_code == 403 and "selecciones" not in ajeno.text,
       fuente="backend/tests/integration/test_scheduling_participation.py::test_intento_ajeno_no_se_consulta_ni_responde; aquí se añade observación HTTP")
    path2, body2 = ruta(c,1)
    http_paso(ev,h,"Respuesta de la siguiente escena autorizada por el grafo", "POST",path2,201,body=body2)
    pathfin = f"/api/v1/attempts/{c.ik}/finish"
    cerrado = http_paso(ev,h,"Finalización voluntaria", "POST",pathfin,200)
    repetido = http_paso(ev,h,"Finalización repetida", "POST",pathfin,200)
    ev("Cierre idempotente", precondiciones="Intento ya finalizado", entrada=None,
       operacion="Comparar ambas respuestas de finalización", esperado="Respuestas idénticas; estado FINALIZADO",
       obtenido=repetido, cumple=cerrado == repetido and "FINALIZADO" in json.dumps(cerrado),
       fuente="backend/tests/integration/test_scheduling_participation.py::test_http_real_jwt_sql_respuesta_progreso_put_y_cierre")


def registro(pg):
    c = cerrar_fixture(contexto(pg), opcion=0)
    c.politica_id = "pt-dcp-laboratorio-"+uuid4().hex
    return c


def test_02_evaluation_interna(pg_grafo, evidencia):
    ev = evidencia
    r = rubrica([20,100],[Decimal(60),Decimal(40)])
    nota = calculo(r).nota_final
    ev("Cálculo reproducible: pesos efectivos iguales", precondiciones="Dos logros sintéticos ya expresados en escala 0–100; no se resuelve el mapeo académico pendiente.",
       entrada=dict(logros=[20,100], pesos_historicos=[60,40], pesos_efectivos=["1/2","1/2"]),
       operacion="CalculadorRubrica: PROMEDIO_IGUALITARIO_100; (20 + 100) / 2",
       esperado="60 exacto, sin redondeo ni reescritura de la rúbrica", obtenido=dict(nota=nota,pesos_historicos=[x.peso_porcentaje for x in r.criterios]),
       cumple=nota == Decimal(60) and [x.peso_porcentaje for x in r.criterios] == [Decimal(60),Decimal(40)],
       fuente="backend/tests/integration/test_academic_policy.py::test_igual_peso_no_reescribe_pesos_historicos")
    c = registro(pg_grafo)
    a = academico(c).evaluar(id_estudiante=c.alumno)
    ev("Evaluación técnica persistida de otra rúbrica: un criterio", precondiciones="Otro intento cerrado sintético; una pregunta; nivel real de fixture con puntaje 5; mapeo SOLO LAB 5×20=100; agregación de una pregunta SOLO LAB.",
       entrada=dict(id_intento=c.ik,opcion=c.q.opciones[0].id,rubrica_id=c.version.rubrica.id,version_id=c.version.id,logro=100),
       operacion="academico(c).evaluar(id_estudiante=c.alumno) reutiliza Strategy, calculador y repositorio SQL existentes",
       esperado="100.00; oficial=false; resultado técnico LABORATORIO; NO es la rúbrica de dos criterios del paso anterior",
       obtenido=dict(id_resultado=a.id_resultado,nota=a.datos.nota_final,oficial=a.oficial,sha256=a.sha256),
       cumple=a.datos.nota_final == Decimal(100) and not a.oficial,
       fuente="backend/tests/integration/test_academic_policy.py::test_100_se_persiste_y_recupera_sin_nota_oficial")
    b = academico(c).consultar(id_estudiante=c.alumno)
    with c.sesiones() as s:
        detalles = [dict(x) for x in s.execute(sa.select(Detalle.__table__).where(Detalle.id_resultado == a.id_resultado)).mappings()]
    procedencia = json.loads(b.procedencia)
    ev("Recuperación desde otra sesión SQL y rúbrica histórica", precondiciones="Resultado técnico confirmado en PostgreSQL",
       entrada=dict(id_intento=c.ik), operacion="Nueva instancia de servicio .consultar(); SELECT resultado_criterio",
       esperado="Resultado idéntico; un detalle; referencia a la misma versión y rúbrica; sin nota oficial",
       obtenido=dict(igual=a == b,detalle=detalles,fuente_rubrica=procedencia["fuente_rubrica"],oficial=b.oficial),
       cumple=a == b and len(detalles) == 1 and not b.oficial
           and procedencia["fuente_rubrica"]["version_id"] == str(c.version.id)
           and procedencia["fuente_rubrica"]["rubrica_id"] == str(c.version.rubrica.id),
       fuente="backend/tests/integration/test_evaluation_result_storage.py::test_evaluar_guardar_y_recuperar_otra_session")


def test_03_feedback_individual(pg_grafo, evidencia):
    ev = evidencia
    c = registro(pg_grafo)
    u = docente(c)
    escribir(c,u,"Valoración individual de laboratorio PT-DCP-01")
    f = leer(c)
    ev("Retroalimentación individual: registro y lectura del titular", precondiciones="Participación sintética cerrada; docente propietario con asociaciones verificadas; estudiante titular.",
       entrada=dict(id_participacion=c.pk,id_docente=u.id_usuario,id_estudiante=c.alumno,texto="Valoración individual de laboratorio PT-DCP-01"),
       operacion="ServicioFeedbackDocente.registrar(); consultar_feedback_individual() (servicios internos, NO HTTP)",
       esperado="Texto recuperado solo para el titular", obtenido=dict(texto=f.texto),
       cumple=f.texto == "Valoración individual de laboratorio PT-DCP-01",
       fuente="backend/tests/integration/test_academic_policy.py::test_feedback_individual_editable_y_privado")
    otra = registro(pg_grafo)
    error = None
    try:
        leer(c,usuario=otra.usuario)
    except AccesoDenegado as exc:
        error = type(exc).__name__
    ev("Acceso ajeno rechazado", precondiciones="Otro estudiante real de la fixture con otra convocatoria; no se suplanta al titular",
       entrada=dict(id_participacion_objetivo=c.pk,id_usuario_solicitante=otra.usuario.id_usuario),
       operacion="consultar_feedback_individual(usuario=otro, id_participacion=objetivo)",
       esperado="Excepción AccesoDenegado; no devolución del texto; no se atribuye un código HTTP",
       obtenido=dict(excepcion=error), cumple=error == "AccesoDenegado",
       fuente="backend/tests/integration/test_academic_policy.py::test_feedback_individual_editable_y_privado")
