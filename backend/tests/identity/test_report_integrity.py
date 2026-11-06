"""Contrato mecánico CSV, datos sintéticos: NO evaluación ni reporte oficial."""
import csv
from decimal import Decimal
from io import StringIO

import pytest

from app.modules.identity.application.services import ServicioReportes
from app.modules.identity.domain.entities import ContextoAcceso, Rol, FilaReporte, EstadoReporte
from app.modules.identity.domain.errors import IntegracionPendiente


class LecturasContrato:
    """Doble explícito solo para probar el serializador, nunca un adaptador SQL."""
    def __init__(self, filas):
        self.filas = filas
        self.llamadas = []

    def obtener_filas(self, docente, sesion):
        self.llamadas.append((docente,sesion))
        return self.filas


def exportar(filas):
    lector = LecturasContrato(filas)
    actor = ContextoAcceso('docente-lab','docente@universidad.test',frozenset({Rol.DOCENTE}))
    contenido = ServicioReportes(lector).descargar(actor,'sesion-lab')
    assert lector.llamadas == [('docente-lab','sesion-lab')]
    return contenido


def fila(estudiante='e1',participacion='p1',nota='50.00',estado=EstadoReporte.COMPLETA):
    return FilaReporte(estudiante,participacion,estado,None if nota is None else Decimal(nota))


def test_csv_sintetico_conserva_limites_vacios_columnas_y_escape(record_property):
    contenido = exportar((fila('=1+1','p1','100.00'),fila('e2','p2','0.00',EstadoReporte.PARCIAL),
        fila('e3',None,None,EstadoReporte.AUSENCIA),fila('e4',None,None,EstadoReporte.AUSENCIA)))
    lector = csv.DictReader(StringIO(contenido))
    assert lector.fieldnames == ['id_estudiante','id_participacion','estado','nota']
    filas = list(lector)
    assert filas[0]['id_estudiante'] == "'=1+1"
    assert [f['nota'] for f in filas] == ['100.00','0.00','','']
    assert [f['id_participacion'] for f in filas] == ['p1','p2','','']
    assert [f['estado'] for f in filas] == ['COMPLETA','PARCIAL','AUSENCIA','AUSENCIA']
    record_property('csv_sintetico_NO_OFICIAL',contenido)


@pytest.mark.parametrize('filas',[
    (fila(),fila()),
    (fila(),fila(participacion='p2',estado=EstadoReporte.PARCIAL)),
    (fila(),fila(estudiante='e2')),
])
def test_reporte_rechaza_duplicado_o_contradiccion_sin_elegir_una_fila(filas):
    with pytest.raises(IntegracionPendiente):
        exportar(filas)


@pytest.mark.parametrize('nota',['-0.01','100.01'])
def test_reporte_rechaza_nota_fuera_de_escala_confirmada(nota):
    with pytest.raises(IntegracionPendiente):
        exportar((fila(nota=nota),))
