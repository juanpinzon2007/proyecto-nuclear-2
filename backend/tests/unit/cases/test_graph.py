"""Navegación de la versión en memoria, sin repositorios ni HTTP."""

from dataclasses import asdict, replace
from uuid import UUID

import pytest

from app.modules.cases.application.graph import (
    EscenaGrafo, GrafoNoDisponible, GrafoVersion, PreguntaGrafo,
    ReglaRecorridoPendiente, SeleccionFueraDeRecorrido, Transicion,
)


def uid(numero):
    return UUID(int=numero)


@pytest.fixture
def grafo():
    return GrafoVersion(uid(1), (
        EscenaGrafo(uid(10), True, "Inicio", (PreguntaGrafo(uid(20), "Decidir", (
            Transicion(uid(30), "ESCENA", uid(11), "Continuar"),
            Transicion(uid(31), "FIN", None, "Terminar"),
        )),)),
        EscenaGrafo(uid(11), False, "Cierre", (PreguntaGrafo(uid(21), "Cerrar", (
            Transicion(uid(32), "FIN", None, "Terminar"),
        )),)),
    ))


@pytest.mark.parametrize("selecciones,escenas,decisiones,actual,finalizado", [
    ((), (10,), (20,), 10, False),
    (((20, 30),), (10, 11), (20, 21), 11, False),
    (((20, 31),), (10,), (20,), None, True),
    (((20, 30), (21, 32)), (10, 11), (20, 21), None, True),
])
def test_recorrido_sigue_la_rama_elegida(grafo, selecciones, escenas, decisiones, actual, finalizado):
    resultado = grafo.recorrer(tuple((uid(p), uid(o)) for p, o in selecciones))
    assert resultado.escenas == tuple(map(uid, escenas))
    assert resultado.decisiones == tuple(map(uid, decisiones))
    assert resultado.escena_actual == (uid(actual) if actual is not None else None)
    assert resultado.finalizado is finalizado


@pytest.mark.parametrize("selecciones", [
    ((20, 30), (20, 31)),  # Pregunta duplicada.
    ((20, 32),),  # Opción de otra pregunta.
    ((21, 32),),  # Respuesta adelantada.
    ((20, 31), (21, 32)),  # Respuesta fuera de la rama terminada.
])
def test_selecciones_ajenas_o_duplicadas_se_rechazan(grafo, selecciones):
    with pytest.raises(SeleccionFueraDeRecorrido):
        grafo.recorrer(tuple((uid(p), uid(o)) for p, o in selecciones))


@pytest.mark.parametrize("iniciales", [(False, False), (True, True)])
def test_exige_una_unica_escena_inicial(grafo, iniciales):
    escenas = tuple(replace(e, inicial=i) for e, i in zip(grafo.escenas, iniciales))
    with pytest.raises(GrafoNoDisponible):
        replace(grafo, escenas=escenas).validar_ejecutable()


@pytest.mark.parametrize("tipo,destino,error", [
    ("ESCENA", uid(999), GrafoNoDisponible),
    ("ESCENA", None, GrafoNoDisponible),
    ("FIN", uid(11), GrafoNoDisponible),
    (None, None, GrafoNoDisponible),
    ("ESCENA", uid(10), ReglaRecorridoPendiente),
])
def test_rama_invalida_bloquea_incluso_si_se_elige_otra(grafo, tipo, destino, error):
    escena = grafo.escenas[0]
    pregunta = escena.preguntas[0]
    opcion = replace(pregunta.opciones[0], tipo=tipo, destino_id=destino)
    pregunta = replace(pregunta, opciones=(opcion, pregunta.opciones[1]))
    grafo = replace(grafo, escenas=(replace(escena, preguntas=(pregunta,)), grafo.escenas[1]))
    with pytest.raises(error):
        grafo.recorrer(((uid(20), uid(31)),))


@pytest.mark.parametrize("cantidad", [0, 2])
def test_escena_sin_regla_de_avance_explicita_se_bloquea(grafo, cantidad):
    escena = grafo.escenas[0]
    segunda = PreguntaGrafo(uid(22), "Otra decisión", (
        Transicion(uid(33), "FIN", None, "Terminar la segunda pregunta"),
    ))
    preguntas = (escena.preguntas[0], segunda)[:cantidad]
    assert len(preguntas) == cantidad
    if cantidad == 2:
        assert preguntas[0] is not preguntas[1]
        assert preguntas[0].id != preguntas[1].id
        assert {o.opcion_id for o in preguntas[0].opciones}.isdisjoint(
            o.opcion_id for o in preguntas[1].opciones
        )
    configurado = replace(grafo, escenas=(replace(escena, preguntas=preguntas), grafo.escenas[1]))
    antes = asdict(configurado)
    with pytest.raises(ReglaRecorridoPendiente, match="varias preguntas o sin preguntas"):
        configurado.validar_ejecutable()
    assert asdict(configurado) == antes
