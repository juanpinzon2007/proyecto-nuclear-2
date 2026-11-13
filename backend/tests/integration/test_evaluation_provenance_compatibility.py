"""Cruce PG17 de fuentes congeladas con algoritmos equivalentes y hashes distintos.

Los dos documentos proceden de Git HEAD y de sus anotaciones locales verificadas.
Se representa la fuente que captura cada runtime mediante su proveedor de metadata.
Las fuentes recibidas de PostgreSQL nunca se ejecutan.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import timezone
from decimal import Decimal
import json
from pathlib import Path
from threading import Barrier

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from alembic import command

from app.modules.participation.application import result_provenance
from app.modules.participation.application.result_provenance import canonico, huella
from app.modules.participation.domain.evaluation import EvaluacionInconsistente
from app.modules.participation.infrastructure import persisted_evaluation, question_evaluation
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.composition import _Alcance
from app.modules.participation.infrastructure.evaluation import _unidad
from app.modules.participation.infrastructure.question_result_repository import DetallesPreguntasSQLAlchemy
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.participation.infrastructure.result_repository import RepositorioResultadosTecnicosSQLAlchemy
from app.modules.identity.infrastructure.models import RolORM
from tests.identity.academic_identity_support import motor_postgresql_desechable, config_alembic
from tests.integration.test_evaluation_result_storage import (
    c as contexto_legado, pg_resultados, evaluar, consultar,
)
from tests.integration.test_question_result_storage import crear_registro, cerrar, guardar, leer, contar


def motor(nombre):
    path = Path(__file__).parents[1] / 'fixtures' / f'evaluation_motor_{nombre}_20261110.json'
    return json.loads(path.read_text(encoding='utf-8'))


@contextmanager
def runtime(monkeypatch, nombre):
    """Identidad de fuente del runtime, sin sustituir Strategy ni el calculador."""
    snapshot = motor(nombre)
    with monkeypatch.context() as patch:
        for modulo in (result_provenance, persisted_evaluation, question_evaluation):
            patch.setattr(modulo, 'fuentes_motor', lambda: deepcopy(snapshot))
        yield


@pytest.fixture
def pg_cruce_preguntas():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as connection:
            command.upgrade(config_alembic(connection), 'head')
            connection.execute(sa.insert(RolORM), [dict(id_rol=1, nombre='DOCENTE'), dict(id_rol=2, nombre='ESTUDIANTE')])
        yield engine


def test_snapshots_fijos_solo_difieren_en_anotaciones():
    class QuitarCadenas(ast.NodeTransformer):
        def visit_Expr(self, nodo):
            if isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, str):
                return None
            return self.generic_visit(nodo)

    versiones = {nombre: motor(nombre) for nombre in ('head', 'annotated')}
    assert huella(canonico(versiones['head'])) == '88f16a1abdebbbe3367c40a13ce3255f10a7bdd6872d3df20ce487777c872960'
    assert huella(canonico(versiones['annotated'])) == '38bbef396cb982fa6d32ab3f0620c9765a7fc32ab8ec4866d1668b842a706d08'
    assert versiones['head'].keys() == versiones['annotated'].keys()
    for modulo, fuente in versiones['head'].items():
        antes = QuitarCadenas().visit(ast.parse(fuente))
        despues = QuitarCadenas().visit(ast.parse(versiones['annotated'][modulo]))
        assert ast.dump(antes, include_attributes=False) == ast.dump(despues, include_attributes=False)


@pytest.mark.parametrize('historico,candidato', [('head', 'annotated'), ('annotated', 'head')])
def test_resultado_legacy_leido_desde_otro_runtime_preserva_documento(contexto_legado, monkeypatch, historico, candidato):
    contexto = contexto_legado
    with runtime(monkeypatch, historico):
        original = evaluar(contexto)
    with runtime(monkeypatch, candidato):
        recuperado = consultar(contexto)
    assert recuperado == original
    assert recuperado.datos.nota_final == Decimal('5.00')
    assert json.loads(recuperado.procedencia)['fuente_rubrica']['version_id'] == str(contexto.version.id)
    assert recuperado.sha256 == huella(recuperado.procedencia)


@pytest.mark.parametrize('historico,candidato', [('head', 'annotated'), ('annotated', 'head')])
def test_resultado_preguntas_cruzado_preserva_tercios_historia_y_replay(crear_registro, pg_cruce_preguntas, monkeypatch, historico, candidato):
    contexto = crear_registro(criterios=2, motor=pg_cruce_preguntas)
    cerrar(contexto, vencido=True, respondidas=1)
    with runtime(monkeypatch, historico):
        original = guardar(contexto)
    with runtime(monkeypatch, candidato):
        recuperado = leer(contexto)
        repetido = guardar(contexto)
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrentes = list(pool.map(lambda _: guardar(contexto), range(2)))
    assert recuperado == original == repetido
    assert all(resultado == original for resultado in concurrentes)
    assert original.datos.nota_final == Decimal('33.33')
    assert original.datos.modalidad.value == 'PARCIAL'
    assert original.datos.pendientes_con_cero == 2
    documento = json.loads(original.procedencia)
    assert documento['rubrica']['version_id'] == str(contexto.version.id)
    assert documento['motor'] == motor(historico)
    assert all((c['numerador'], c['denominador']) == (50, 3) for c in documento['exacto']['criterios'])
    assert original.sha256 == huella(original.procedencia)
    assert contar(contexto) == 1


@pytest.mark.parametrize('alteracion', ['fuente', 'nota'])
def test_documento_ajeno_o_calculo_alterado_rechazado_sin_reescribir(crear_registro, pg_cruce_preguntas, alteracion):
    contexto = crear_registro(motor=pg_cruce_preguntas)
    cerrar(contexto)
    original = guardar(contexto)
    fechas = FechasPersistencia(timezone.utc)
    with _unidad(contexto.sesiones, fechas) as trabajo:
        sesion = trabajo.sesion
        alcance = _Alcance(lambda: sesion, contexto.usuario, contexto.ik, fechas)
        repositorio = RepositorioResultadosTecnicosSQLAlchemy(sesion, alcance=alcance, fechas=fechas)
        fila = dict(sesion.execute(sa.select(R.__table__).where(R.id_intento == contexto.ik)).mappings().one())
        documento = json.loads(fila['procedencia'])
        if alteracion == 'fuente':
            documento['motor']['app.modules.participation.domain.estrategias_evaluacion'] += '\nraise RuntimeError("FUENTE_NO_EJECUTABLE")\n'
        else:
            documento['nota_final'] = '99.99'
        fila['procedencia'] = canonico(documento)
        fila['procedencia_sha256'] = huella(fila['procedencia'])
        with pytest.raises(EvaluacionInconsistente):
            DetallesPreguntasSQLAlchemy(repositorio).leer(fila)
    assert leer(contexto) == original and contar(contexto) == 1


def test_primeras_escrituras_concurrentes_eligen_una_definicion_inmutable(crear_registro, pg_cruce_preguntas, monkeypatch):
    contextos = [crear_registro(motor=pg_cruce_preguntas) for _ in range(2)]
    for contexto in contextos:
        cerrar(contexto, vencido=True, respondidas=1)
    runtime_actual = ContextVar('runtime_actual', default='head')
    inicio = Barrier(2)
    for modulo in (result_provenance, persisted_evaluation, question_evaluation):
        monkeypatch.setattr(modulo, 'fuentes_motor', lambda: motor(runtime_actual.get()))

    def escribir(item):
        nombre, contexto = item
        token = runtime_actual.set(nombre)
        try:
            inicio.wait(timeout=10)
            return guardar(contexto)
        finally:
            runtime_actual.reset(token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(escribir, zip(('head', 'annotated'), contextos)))
    politicas = {json.loads(r.procedencia)['politica_documento'] for r in resultados}
    assert len(politicas) == 1
    with contextos[0].sesiones() as session:
        assert session.scalar(sa.select(sa.func.count()).select_from(R)) == 2
        assert session.scalar(sa.select(sa.func.count(sa.distinct(R.politica_hash)))) == 1
    for contexto, resultado in zip(contextos, resultados):
        assert leer(contexto) == resultado == guardar(contexto)
        assert resultado.datos.nota_final == Decimal('33.33')


def test_rollback_no_fija_definicion_y_reintento_reutiliza_la_confirmada(crear_registro, pg_cruce_preguntas, monkeypatch):
    primero, segundo = [crear_registro(motor=pg_cruce_preguntas) for _ in range(2)]
    for contexto in (primero, segundo):
        cerrar(contexto, vencido=True, respondidas=1)

    def fallar(connection, cursor, statement, *args):
        if statement.startswith('INSERT INTO resultado_calculo_preguntas'):
            connection.exec_driver_sql('SELECT 1/0')

    sa.event.listen(primero.engine, 'before_cursor_execute', fallar)
    try:
        with runtime(monkeypatch, 'annotated'), pytest.raises(DBAPIError):
            guardar(primero)
    finally:
        sa.event.remove(primero.engine, 'before_cursor_execute', fallar)
    assert contar(primero) == 0
    segundo_resultado = guardar(segundo)
    with runtime(monkeypatch, 'annotated'):
        primero_resultado = guardar(primero)
    assert json.loads(primero_resultado.procedencia)['politica_documento'] == json.loads(segundo_resultado.procedencia)['politica_documento']
    assert primero_resultado.datos.nota_final == segundo_resultado.datos.nota_final == Decimal('33.33')
    assert leer(primero) == primero_resultado and leer(segundo) == segundo_resultado
