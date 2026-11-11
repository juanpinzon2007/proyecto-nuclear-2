"""Recuperación docente explícita desde cierres persistidos, PostgreSQL 17."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone

import pytest
import sqlalchemy as sa

from app.modules.identity.domain.errors import AccesoDenegado, ReglaIdentidadInvalida
from app.modules.participation.domain.clock import RelojSistema
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.participation.infrastructure.teacher_evaluation import EvaluadorTecnicoDocente
from app.modules.participation.infrastructure.teacher_result import ConsultaResultadoDocenteSQLAlchemy
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel as R
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
from tests.integration.test_main_technical_results import (
    c, crear_registro, pg_resultados, docente_http, revision, ruta,
)  # noqa: F401
from tests.integration.test_question_result_storage import contar, cerrar
from tests.integration.test_evaluation_result_storage import evaluar


def recuperador(h):
    consulta = ConsultaResultadoDocenteSQLAlchemy(usuario=h.c.actor, crear_sesion=h.c.sesiones,
        fechas=FechasPersistencia(timezone.utc))
    return EvaluadorTecnicoDocente(consulta=consulta, reloj=RelojSistema())


@pytest.mark.parametrize('c', ['completo', 'parcial'], indirect=True)
def test_cierre_persistido_se_recupera_y_se_consulta_por_http_sin_publicar(docente_http):
    h = docente_http
    assert h.client.get(ruta(h), headers=h.auth['docente']).status_code == 404
    servicio = recuperador(h)
    resultado = servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    item = resultado.intentos[0]
    assert item.estado == 'DISPONIBLE' and item.id_resultado is not None and item.motivo is None
    respuesta = h.client.get(ruta(h), headers=h.auth['docente'])
    assert respuesta.status_code == 200
    assert respuesta.json()['nota_final'] == ('100.00' if respuesta.json()['modalidad'] == 'COMPLETA' else '33.33')
    assert respuesta.json()['oficial'] is False and respuesta.json()['id_resultado'] == item.id_resultado
    assert servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,)) == resultado
    assert contar(h.c) == 1


def test_fallo_sql_conserva_cierre_y_reintento_recupera(docente_http):
    h = docente_http
    servicio = recuperador(h)
    with h.c.sesiones() as sesion:
        previo = sesion.execute(sa.select(I.estado, I.fin).where(I.id_intento == h.c.ik)).one()
    def fallar(conn, cursor, statement, *args):
        if statement.startswith('INSERT INTO resultado_calculo_preguntas'):
            conn.exec_driver_sql('SELECT 1/0')
    sa.event.listen(h.c.engine, 'after_cursor_execute', fallar)
    try:
        resultado = servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    finally:
        sa.event.remove(h.c.engine, 'after_cursor_execute', fallar)
    assert resultado.intentos[0].estado == 'PENDIENTE'
    assert resultado.intentos[0].motivo == 'CONFIGURACION_O_PERSISTENCIA'
    assert contar(h.c) == 0
    with h.c.sesiones() as sesion:
        assert sesion.execute(sa.select(I.estado, I.fin).where(I.id_intento == h.c.ik)).one() == previo
    assert servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,)).intentos[0].estado == 'DISPONIBLE'


def test_lectura_fallida_despues_commit_recupera_resultado_confirmado(docente_http):
    h = docente_http
    insertado = [False]
    confirmado = [False]
    fallo = [False]
    def sql(conn, cursor, statement, *args):
        if statement.startswith('INSERT INTO resultado_intento '):
            insertado[0] = True
        if confirmado[0] and statement.startswith('SELECT resultado_intento.') and not fallo[0]:
            fallo[0] = True
            conn.exec_driver_sql('SELECT 1/0')
    def commit(conn):
        if insertado[0]:
            confirmado[0] = True
    sa.event.listen(h.c.engine, 'before_cursor_execute', sql)
    sa.event.listen(h.c.engine, 'commit', commit)
    try:
        resultado = recuperador(h).recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    finally:
        sa.event.remove(h.c.engine, 'before_cursor_execute', sql)
        sa.event.remove(h.c.engine, 'commit', commit)
    assert fallo[0] and resultado.intentos[0].estado == 'PENDIENTE' and contar(h.c) == 1
    with h.c.sesiones() as sesion:
        existente = sesion.scalar(sa.select(R.id_resultado).where(R.id_intento == h.c.ik))
    recuperado = recuperador(h).recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    assert recuperado.intentos[0].id_resultado == existente and contar(h.c) == 1


def test_seleccion_con_intento_ajeno_falla_antes_de_escribir(docente_http, crear_registro):
    h = docente_http
    otro = crear_registro()
    cerrar(otro)
    with pytest.raises(AccesoDenegado):
        recuperador(h).recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik, otro.ik))
    assert contar(h.c) == 0


def test_recuperaciones_concurrentes_conservan_una_cabecera(docente_http):
    h = docente_http
    servicio = recuperador(h)
    def recuperar(_):
        return servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(recuperar, range(2)))
    assert resultados[0] == resultados[1]
    assert resultados[0].intentos[0].estado == 'DISPONIBLE' and contar(h.c) == 1


@pytest.mark.parametrize('c', ['activo'], indirect=True)
def test_cierre_ausente_y_convocatoria_retirada_requieren_revision(docente_http):
    h = docente_http
    servicio = recuperador(h)
    resultado = servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    assert resultado.intentos[0].motivo == 'CIERRE_NO_PERSISTIDO' and contar(h.c) == 0
    with h.c.sesiones.begin() as sesion:
        sesion.get(C, h.c.datos['convocatoria_id']).estado = 'RETIRADA'
    resultado = servicio.recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    assert resultado.intentos[0].motivo == 'CONVOCATORIA_RETIRADA' and contar(h.c) == 0


@pytest.mark.parametrize('c', ['legacy'], indirect=True)
def test_motor_historico_se_recupera_sin_reinterpretar(docente_http):
    h = docente_http
    anterior = evaluar(h.c)
    resultado = recuperador(h).recuperar_cierres(id_sesion=h.c.sesion, ids_intentos=(h.c.ik,))
    assert resultado.intentos[0].id_resultado == anterior.id_resultado and contar(h.c) == 1


@pytest.mark.parametrize('ids', [(), (True,), (0,), (-1,), (1, 1)])
def test_solicitud_explicita_invalida_no_crea_resultados(docente_http, ids):
    with pytest.raises(ReglaIdentidadInvalida):
        recuperador(docente_http).recuperar_cierres(id_sesion=docente_http.c.sesion, ids_intentos=ids)
    assert contar(docente_http.c) == 0
