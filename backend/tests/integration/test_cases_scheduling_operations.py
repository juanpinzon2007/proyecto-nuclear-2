"""Cierre 8B: fuentes reales de Cases/Scheduling, sin inferir rutas o políticas.

Solo fixtures conceden permisos. No se habilita API ni inicio productivo.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.modules.cases.application.simulation_structure import consultar_estructura_version, validar_opcion_version
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.application.dto import RecorridoAplicable
from app.modules.participation.domain.errors import IntentoNoEditable
from app.modules.participation.infrastructure.codecs import FechasPersistencia
from app.modules.participation.infrastructure.composition import crear_facade_8b
from app.modules.participation.infrastructure.repository import RepositorioParticipacionSQLAlchemy
from app.modules.scheduling.application.attempt_operations import consultar_operacion_sesion, OperacionSesionDenegada, CondicionesOperacionNoDisponibles
from app.modules.scheduling.infrastructure.models import SesionProgramadaModel
from tests.integration.test_participation_persistence import datos, motor, laboratorio_pg, FECHA  # noqa: F401
from tests.integration.test_steps_uuid import c, pg, guardar, progreso, filas, fachada, RutaFixture, EdicionFixture  # noqa: F401


def consultar_operacion(c,s,**cambios):
    argumentos=dict(sesion_id=c.sesion,convocatoria_id=c.datos["convocatoria_id"],estudiante_id=c.uuid,
                    version_caso_id=c.version.id,operacion="RESPONDER")
    return consultar_operacion_sesion(s,**(argumentos|cambios))


def test_estructura_publicada_real_sin_correccion_ni_ruta_inferida(datos):
    c=datos
    with c.sesiones() as s:
        estructura=consultar_estructura_version(s,version_id=c.version.id)
    assert estructura.version_id==c.version.id and estructura.caso_id==c.version.caso_id
    assert estructura.estado==EstadoCaso.PUBLICADO
    assert estructura.rubrica_id==c.version.rubrica.id
    assert tuple(p.id for p in estructura.preguntas)==tuple(p.id for e in c.version.escenarios for p in e.preguntas)
    assert estructura.preguntas[0].opciones==tuple(o.id for o in c.version.escenarios[0].preguntas[0].opciones)
    contenido=str(asdict(estructura))
    for campo in ("es_correcta","justificacion","valoraciones","puntaje","decisiones_disponibles"):
        assert campo not in contenido


def test_estructura_preserva_edicion_anterior_y_rubrica(c):
    with c.sesiones() as s:
        anterior=consultar_estructura_version(s,version_id=c.anterior.id)
        actual=consultar_estructura_version(s,version_id=c.version.id)
    assert anterior.numero==1 and actual.numero==2 and anterior.caso_id==actual.caso_id
    assert anterior.rubrica_id!=actual.rubrica_id
    guardar(c)
    with c.sesiones() as s:
        assert consultar_estructura_version(s,version_id=c.anterior.id)==anterior
    assert progreso(c).selecciones[0].id_decision in {p.id for p in actual.preguntas}


@pytest.mark.parametrize("error",["pregunta","version","opcion"])
def test_fuente_cases_rechaza_relaciones_ajenas(c,error):
    pregunta=c.version.escenarios[0].preguntas[0]
    argumentos=dict(version_id=c.version.id,pregunta_id=pregunta.id,opcion_id=pregunta.opciones[0].id)
    if error=="pregunta":argumentos["opcion_id"]=c.version.escenarios[0].preguntas[1].opciones[0].id
    elif error=="version":argumentos["version_id"]=c.anterior.id
    else:argumentos["opcion_id"]=uuid4()
    with c.sesiones() as s,pytest.raises(CasoNoEncontradoError):
        validar_opcion_version(s,**argumentos)


def test_orden_y_cantidad_de_preguntas_no_autorizan_la_primera(c):
    with c.sesiones() as s:
        estructura=consultar_estructura_version(s,version_id=c.version.id)
    assert len(estructura.preguntas)==2
    p=progreso(c)
    assert p.decisiones_aplicables is None and p.pendientes is None and p.total_aplicable is None
    with pytest.raises(ReglaPendiente,match="punto"):
        guardar(c,recorrido=None)
    assert filas(c)==[]


def test_pregunta_fuera_del_recorrido_explicito_no_se_guarda(c):
    class SoloPrimera(RutaFixture):
        def obtener(self,**_):return RecorridoAplicable((self.ids[0],),True)
    with pytest.raises(AccesoDenegado,match="fuera"):
        guardar(c,q=1,recorrido=SoloPrimera(c))
    assert filas(c)==[]


def test_validator_del_punto_se_consulta_incluso_primera_y_modificacion_sola(c):
    class Punto(RutaFixture):
        def validar_cambio(self,*,version_id,selecciones,propuesta):
            assert version_id==self.version
            if not selecciones and propuesta.id_decision!=self.ids[0]:
                raise AccesoDenegado("Punto no autorizado por la fixture")
            if selecciones:
                raise ReglaPendiente("Modificación no aprobada en este punto")
    ruta=Punto(c)
    with pytest.raises(AccesoDenegado):guardar(c,q=1,recorrido=ruta)
    guardar(c,recorrido=ruta)
    anteriores=filas(c)
    with pytest.raises(IntentoNoEditable):guardar(c,modificar=True,o=1,recorrido=ruta)
    assert filas(c)==anteriores


@pytest.mark.parametrize("estado",["SIN_INICIAR","EN_CURSO","FINALIZADO"])
def test_estado_scheduling_es_hecho_no_permiso(c,estado):
    # Preparación de datos sintéticos de estado, no transición productiva.
    with c.engine.begin() as s:
        s.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(estado=estado))
    with c.sesiones.begin() as s:
        contexto=consultar_operacion(c,s)
        assert contexto.estado==estado and contexto.version_caso_id==c.version.id
        assert contexto.inicio.tzinfo is not None
    error = AccesoDenegado if estado == "FINALIZADO" else ReglaPendiente
    mensaje = "finalizada" if estado == "FINALIZADO" else "autorización"
    with pytest.raises(error,match=mensaje):
        guardar(c,autorizacion=None)
    assert filas(c)==[]


@pytest.mark.parametrize("campo",["sesion_id","convocatoria_id","estudiante_id","version_caso_id"])
def test_scheduling_verifica_correspondencia_real(c,campo):
    with c.sesiones.begin() as s,pytest.raises(OperacionSesionDenegada):
        consultar_operacion(c,s,**{campo:uuid4()})


def test_operacion_sin_transaccion_o_nombre_desconocido_cierra(c):
    with c.sesiones() as s,pytest.raises(CondicionesOperacionNoDisponibles):consultar_operacion(c,s)
    with c.sesiones.begin() as s,pytest.raises(CondicionesOperacionNoDisponibles):consultar_operacion(c,s,operacion="DESCONOCIDA")


def test_servicios_de_modulos_y_repo_comparten_transaccion_y_operacion(c,monkeypatch):
    import app.modules.participation.infrastructure.composition as modulo
    original=modulo.consultar_operacion_sesion
    guardar_original=RepositorioParticipacionSQLAlchemy.guardar_intento
    sesiones=[];acciones=[]
    def consultar(db,**argumentos):
        assert db.in_transaction()
        sesiones.append(db)
        acciones.append(argumentos["operacion"])
        return original(db,**argumentos)
    def persistir(self,*args,**kwargs):
        assert self.sesion is sesiones[-1]
        return guardar_original(self,*args,**kwargs)
    monkeypatch.setattr(modulo,"consultar_operacion_sesion",consultar)
    monkeypatch.setattr(RepositorioParticipacionSQLAlchemy,"guardar_intento",persistir)
    guardar(c)
    c.ahora+=timedelta(seconds=1)
    # Nueva política: la segunda escritura corresponde a OTRA pregunta.
    guardar(c,q=1)
    assert acciones==["RESPONDER","RESPONDER"] and sesiones[0] is not sesiones[1]
    assert len(filas(c))==2


def test_finalizacion_sesion_concurrente_no_reutiliza_permiso_previo(c):
    inicio=Barrier(2)
    def responder():
        inicio.wait(timeout=5)
        try:guardar(c);return "guardada"
        except AccesoDenegado:return "denegada"
    def cerrar():
        inicio.wait(timeout=5)
        with c.engine.begin() as s:
            s.execute(sa.update(SesionProgramadaModel).where(SesionProgramadaModel.id==c.sesion).values(estado="FINALIZADO"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        respuesta=pool.submit(responder);fin=pool.submit(cerrar)
        r=respuesta.result(timeout=10);fin.result(timeout=10)
    assert r in {"guardada","denegada"}
    assert len(filas(c))==(1 if r=="guardada" else 0)


def test_modificacion_y_vencimiento_concurrentes_conservan_respuesta(c):
    guardar(c);inicio=Barrier(2)
    def construir(ahora):
        return crear_facade_8b(usuario=c.usuario,id_intento=c.ik,reloj=SimpleNamespace(ahora=lambda:ahora),
            fechas=FechasPersistencia(timezone.utc),crear_sesion=c.sesiones,
            autorizacion_edicion=EdicionFixture(c),recorrido=RutaFixture(c))
    def modificar():
        f=construir(FECHA.replace(tzinfo=timezone.utc)+timedelta(minutes=2))
        inicio.wait(timeout=5)
        q=c.version.escenarios[0].preguntas[0]
        try:f.modificar_decision(id_estudiante=c.alumno,id_intento=c.ik,id_decision=q.id,id_opcion=q.opciones[1].id)
        except IntentoNoEditable:pass
    def vencer():
        f=construir(FECHA.replace(tzinfo=timezone.utc)+timedelta(hours=1))
        inicio.wait(timeout=5)
        return f.procesar_vencimiento(id_estudiante=c.alumno,id_intento=c.ik)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(modificar);b=pool.submit(vencer)
        a.result(timeout=10);resultado=b.result(timeout=10)
    assert resultado.estado.value=="VENCIDO" and resultado.fin==resultado.vence_en
    assert len(filas(c))==1 and progreso(c).respondidas==1
