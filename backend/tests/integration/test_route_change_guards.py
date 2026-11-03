"""Guardas reales 8B; las rutas positivas son contratos simulados, NO grafo Cases.

SQL, Facade, titularidad y rollback usan PostgreSQL desechable. No se deduce
ningún arco del orden editorial ni se instala una política productiva.
"""
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.domain.errors import IntentoNoEditable
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel
from tests.integration.test_steps_uuid import (
    c, pg, guardar, filas, fachada, progreso, RutaFixture,  # noqa: F401
)


class RamaFixture(RutaFixture):
    """Grafo SIMULADO: la segunda alternativa excluye la segunda pregunta."""
    def __init__(self, c):
        super().__init__(c)
        self.desvio = c.version.escenarios[0].preguntas[0].opciones[1].id

    def obtener(self, *, version_id, selecciones):
        assert version_id == self.version
        desvio = any(s.id_decision == self.ids[0] and s.id_opcion == self.desvio for s in selecciones)
        return RecorridoAplicable(self.ids[:1] if desvio else self.ids, True)


def test_cambio_de_rama_no_oculta_respuesta_persistida(c):
    ruta = RamaFixture(c)
    guardar(c, recorrido=ruta)
    guardar(c, q=1, recorrido=ruta)
    antes = filas(c)
    c.ahora += timedelta(seconds=1)
    # validar_cambio de esta fixture es permisivo: la guarda del adaptador debe
    # comprobar por sí misma el conjunto posterior, sin borrar la segunda fila.
    with pytest.raises(IntentoNoEditable):
        guardar(c, modificar=True, o=1, recorrido=ruta)
    assert filas(c) == antes
    assert progreso(c, recorrido=ruta).respondidas == 2


def test_cambio_sin_respuestas_excluidas_permite_contrato_explicito(c):
    ruta = RamaFixture(c)
    # La rama se elige en la PRIMERA respuesta; ya no mediante modificación.
    guardar(c, o=1, recorrido=ruta)
    c.ahora += timedelta(seconds=1)
    with pytest.raises(IntentoNoEditable):guardar(c, modificar=True, o=0, recorrido=ruta)
    p = progreso(c, recorrido=ruta)
    assert p.decisiones_aplicables == (ruta.ids[0],)
    assert p.pendientes == () and p.total_aplicable == 1
    assert p.selecciones[0].id_opcion == ruta.desvio
    # No contar las dos preguntas de la edición como total de esta rama simulada.
    with pytest.raises(AccesoDenegado, match="fuera"):
        guardar(c, q=1, recorrido=ruta)
    assert len(filas(c)) == 1


@pytest.mark.parametrize("error", ["no_disponible", "ajena", "excluye", "infraestructura"])
def test_fallo_al_resolver_ruta_posterior_revierte_registro(c, error):
    class Ruta(RutaFixture):
        def obtener(self, *, version_id, selecciones):
            if not selecciones:
                return super().obtener(version_id=version_id, selecciones=selecciones)
            if error == "infraestructura":
                raise ConnectionError("Fuente de recorrido indisponible")
            if error == "no_disponible":
                return RecorridoAplicable((), False, disponible=False)
            return RecorridoAplicable((uuid4(),) if error == "ajena" else (self.ids[1],), True)

    with pytest.raises(ConnectionError if error == "infraestructura" else ReglaPendiente):
        guardar(c, recorrido=Ruta(c))
    assert filas(c) == []
    # La transacción abortada no deja bloqueos ni impide una operación posterior.
    guardar(c)
    assert len(filas(c)) == 1


def test_ruta_posterior_recibe_reemplazo_unico_y_edicion_exacta(c):
    llamadas = []

    class Ruta(RutaFixture):
        def obtener(self, *, version_id, selecciones):
            llamadas.append((version_id, selecciones))
            return super().obtener(version_id=version_id, selecciones=selecciones)

    ruta = Ruta(c)
    guardar(c, recorrido=ruta)
    guardar(c, q=1, recorrido=ruta)
    c.ahora += timedelta(seconds=1)
    antes_llamadas = tuple(llamadas)
    with pytest.raises(IntentoNoEditable):guardar(c, modificar=True, o=1, recorrido=ruta)
    assert tuple(llamadas) == antes_llamadas
    version, propuestas = llamadas[-1]
    assert version == c.version.id
    assert tuple(s.id_decision for s in propuestas) == ruta.ids
    assert propuestas[0].id_opcion == c.version.escenarios[0].preguntas[0].opciones[0].id
    assert len(filas(c)) == 2


@pytest.mark.parametrize("modificar", [False, True])
def test_sesion_finalizada_no_puede_ser_reabierta_por_politica_permisiva(c, modificar):
    if modificar:
        guardar(c)
    antes = filas(c)
    with c.engine.begin() as s:
        s.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id == c.sesion)
                  .values(estado="FINALIZADO"))
    politica = SimpleNamespace(autorizar=lambda _: pytest.fail("No delegar una prohibición RF-25"))
    with pytest.raises(IntentoNoEditable if modificar else AccesoDenegado):
        guardar(c, modificar=modificar, autorizacion=politica)
    assert filas(c) == antes
    # El cierre personal autorizado no depende de permitir nuevas respuestas.
    cierre = fachada(c).finalizar(id_estudiante=c.alumno, id_intento=c.ik)
    assert cierre.estado.value == "FINALIZADO"
    assert fachada(c).finalizar(id_estudiante=c.alumno, id_intento=c.ik) == cierre


@pytest.mark.parametrize("cierre", ["finalizar", "vencer"])
def test_intento_cerrado_no_consulta_politicas_ni_modifica_historia(c, cierre):
    guardar(c)
    antes = filas(c)
    f = fachada(c)
    if cierre == "vencer":
        c.ahora += timedelta(days=1)
        f.procesar_vencimiento(id_estudiante=c.alumno, id_intento=c.ik)
    else:
        f.finalizar(id_estudiante=c.alumno, id_intento=c.ik)
    politica = SimpleNamespace(autorizar=lambda _: pytest.fail("Intento cerrado"))
    with pytest.raises(IntentoNoEditable):
        guardar(c, modificar=True, o=1, autorizacion=politica)
    assert filas(c) == antes
