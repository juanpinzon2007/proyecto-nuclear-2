"""Brechas literales CP-I-05/06/08/09; PostgreSQL desechable y contratos actuales.

No modifica producción ni fuerza referencias imposibles desactivando guards.
Las salidas JSON son observaciones auténticas y no contienen códigos ni tokens.
"""
from contextlib import contextmanager
from datetime import timezone
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel, EscenarioModel, OpcionRespuestaModel, PreguntaModel
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.cases.infrastructure.repositories.graph_repository import RepositorioGrafoSQLAlchemy
from app.modules.identity.api import dependencies as identity, academic_dependencies
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM
from app.modules.identity.infrastructure.security import TokensJWT
from app.modules.participation.api.dependencies import obtener_facade
from app.modules.participation.api.router import router
from app.modules.participation.infrastructure.models import ParticipacionModel, IntentoModel
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel as A
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel as C
from tests.integration.test_attempt_start import (
    c, convocada, pg_grafo, facade, iniciar, filas, preparar_convocada,
)  # noqa: F401
from tests.integration.test_cases_graph import version_grafo, configurar
from tests.integration.test_cases_history import publicar
from tests.integration.test_participation_persistence import participacion, contexto


def observar(ficha, **datos):
    # Solo datos explícitos y seguros. No imprimir headers, contexto completo,
    # motor, solicitudes con código o excepciones SQL con sus parámetros.
    print(json.dumps(dict(ficha=ficha,observacion=datos),ensure_ascii=False,default=str),flush=True)


@contextmanager
def cliente_inicio(c,monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(identity,"get_session_factory",lambda:c.sesiones)
        m.setattr(academic_dependencies,"get_session_factory",lambda:c.sesiones)
        tokens=TokensJWT("clave-exclusiva-brechas-pt-dcp-lab-"*3,"brechas-lab","cliente-lab")
        app=FastAPI(debug=False);app.include_router(router)
        app.dependency_overrides[identity.obtener_fabrica_tokens]=lambda:lambda:tokens
        def dependencia(usuario=Depends(identity.obtener_estudiante_actual)):
            return facade(c,usuario=usuario)
        app.dependency_overrides[obtener_facade]=dependencia
        with TestClient(app) as client:
            yield client,tokens


@pytest.mark.parametrize("contexto_invalido",["inexistente","otra_del_mismo_estudiante"])
def test_cp_i_05_inicio_rechaza_contexto_de_convocatoria_incorrecto(c,monkeypatch,contexto_invalido):
    actual=c.datos["convocatoria_id"]
    with c.sesiones() as s:
        if contexto_invalido=="inexistente":
            incorrecta=uuid4()
            assert s.get(C,incorrecta) is None
        else:
            # La fixture ya tiene otra convocatoria REAL del MISMO estudiante,
            # en otra sesión. No se fabrica una asociación INTEGER/UUID.
            incorrecta=s.scalar(sa.select(C.id).where(C.estudiante_id==c.uuid,C.id!=actual))
            assert incorrecta is not None
        existe=s.get(C,incorrecta) is not None
    with cliente_inicio(c,monkeypatch) as (client,tokens):
        respuesta=client.post(f"/api/v1/participations/{c.pk}/attempts",
            json={"id_consentimiento":c.consentimiento},
            headers={"Authorization":"Bearer "+tokens.emitir(str(c.alumno),str(incorrecta))})
    observar("CP-I-05",variante=contexto_invalido,contexto_existe=existe,
        contexto_coincide_con_participacion=incorrecta==actual,http=respuesta.status_code,
        respuesta=respuesta.json(),intentos=len(filas(c)))
    assert respuesta.status_code==403
    assert respuesta.json()["detail"]["codigo"]=="ACCESO_DENEGADO"
    assert filas(c)==[]
    with c.sesiones() as s:assert s.get(ParticipacionModel,c.pk).convocatoria_id==actual


def test_cp_i_06_inicio_sin_consentimiento_registrado_no_lo_crea(c,monkeypatch):
    # Preparación negativa SOLO sobre el consentimiento sintético recién creado,
    # todavía no usado por ningún intento. No se borra historial ni bases ajenas.
    with c.sesiones.begin() as s:
        assert s.scalar(sa.select(sa.func.count()).select_from(IntentoModel)
            .where(IntentoModel.id_consentimiento==c.consentimiento))==0
        s.execute(sa.delete(ConsentimientoORM).where(ConsentimientoORM.id_consentimiento==c.consentimiento))
    def cantidad():
        with c.sesiones() as s:
            return s.scalar(sa.select(sa.func.count()).select_from(ConsentimientoORM)
                .where(ConsentimientoORM.id_estudiante==c.alumno))
    assert cantidad()==0
    with cliente_inicio(c,monkeypatch) as (client,tokens):
        headers={"Authorization":"Bearer "+tokens.emitir(str(c.alumno),str(c.datos["convocatoria_id"]))}
        url=f"/api/v1/participations/{c.pk}/attempts"
        sin_campo=client.post(url,json={},headers=headers)
        referencia_inexistente=client.post(url,json={"id_consentimiento":c.consentimiento},headers=headers)
    observar("CP-I-06",consentimientos_registrados=cantidad(),
        campo_omitido_http=sin_campo.status_code,referencia_no_registrada_http=referencia_inexistente.status_code,
        respuesta_sin_campo=sin_campo.json(),respuesta_no_registrada=referencia_inexistente.json(),intentos=len(filas(c)))
    assert sin_campo.status_code==422
    assert referencia_inexistente.status_code==403
    assert cantidad()==0 and filas(c)==[]


def test_cp_i_08_inicio_conserva_version_asignada_aunque_exista_otra_posterior(c):
    posterior=version_grafo()
    posterior.caso_id,posterior.docente_creador_id,posterior.numero=c.version.caso_id,c.version.docente_creador_id,3
    with c.sesiones.begin() as s:
        familia=s.get(CasoModel,c.version.caso_id)
        mapeada=CasoRepository(s)._mapear(posterior)
        familia.versiones.append(mapeada.versiones.pop())
    # Publicación editorial legítima, sin configurar el recorrido de la nueva
    # edición. Elegirla indebidamente haría fallar el inicio del caso asignado.
    posterior=publicar(c.sesiones,posterior)
    inicio=iniciar(c)
    with c.sesiones() as s:
        version_persistida=s.scalar(sa.select(A.version_caso_id).join(ParticipacionModel,
            ParticipacionModel.id_asignacion==A.id_asignacion).where(ParticipacionModel.id_participacion==inicio.id_participacion))
        assert s.get(VersionCasoModel,posterior.id).estado=="PUBLICADO"
    observar("CP-I-08",version_asignada=c.version.id,version_posterior=posterior.id,
        version_persistida=version_persistida,intento=inicio.id_intento,estado=inicio.estado.value,
        numero_asignado=c.version.numero,numero_posterior=posterior.numero)
    assert inicio.estado.value=="EN_CURSO" and version_persistida==c.version.id
    assert version_persistida!=posterior.id and c.version.numero<posterior.numero


def test_cp_i_08_postgresql_rechaza_asignacion_de_familias_cruzadas(c):
    otra=contexto(c.engine)
    with c.sesiones() as s:
        original=dict(s.execute(sa.select(A.__table__).where(A.id_asignacion==c.datos["id_asignacion"])).mappings().one())
        alternativa=dict(s.execute(sa.select(A.__table__).where(A.id_asignacion==otra.datos["id_asignacion"])).mappings().one())
        antes=s.scalar(sa.select(sa.func.count()).select_from(A))
    cruzada={k:v for k,v in original.items() if k!="id_asignacion"}
    cruzada.update(id_caso=alternativa["id_caso"],id_grupo=alternativa["id_grupo"])
    assert cruzada["id_caso"]!=original["id_caso"]
    with pytest.raises(IntegrityError) as error:
        with c.engine.begin() as s:s.execute(A.__table__.insert().values(**cruzada))
    codigo=error.value.orig.sqlstate
    mensaje=error.value.orig.diag.message_primary
    with c.sesiones() as s:
        despues=s.scalar(sa.select(sa.func.count()).select_from(A))
        asignacion=s.get(A,c.datos["id_asignacion"])
        intacta=(asignacion.id_caso,asignacion.version_caso_id)==(original["id_caso"],original["version_caso_id"])
    observar("CP-I-08",operacion="INSERT asignacion_caso con caso de otra familia",
        sqlstate=codigo,guard=mensaje,asignaciones_antes=antes,asignaciones_despues=despues,
        asignacion_original_intacta=intacta,intentos=len(filas(c)))
    assert codigo=="23514" and "otra familia" in mensaje
    assert antes==despues and intacta and filas(c)==[]


@pytest.mark.parametrize("defecto",["sin_escena_inicial","transicion_sin_configurar"])
def test_cp_i_09_inicio_rechaza_grafo_no_ejecutable(pg_grafo,monkeypatch,defecto):
    def configurar_incompleto(sesiones,v):
        if defecto=="transicion_sin_configurar":
            configurar(sesiones,v)
            with sesiones.begin() as s:
                RepositorioGrafoSQLAlchemy(s).configurar(version_id=v.id,docente_id=v.docente_creador_id,
                    inicial_id=v.escenarios[0].id,transiciones=((v.escenarios[0].preguntas[0].opciones[0].id,None,None),))
        # Sin entrada: no se configura nada. No se falsifican transiciones.
    datos=preparar_convocada(pg_grafo,configurar_recorrido=configurar_incompleto)
    datos.pk=participacion(datos)
    with cliente_inicio(datos,monkeypatch) as (client,tokens):
        respuesta=client.post(f"/api/v1/participations/{datos.pk}/attempts",
            json={"id_consentimiento":datos.consentimiento},
            headers={"Authorization":"Bearer "+tokens.emitir(str(datos.alumno),str(datos.datos["convocatoria_id"]))})
    with datos.sesiones() as s:
        iniciales=s.scalar(sa.select(sa.func.count()).select_from(EscenarioModel)
            .where(EscenarioModel.version_caso_id==datos.version.id,EscenarioModel.es_inicial.is_(True)))
        faltantes=s.scalar(sa.select(sa.func.count()).select_from(OpcionRespuestaModel)
            .join(PreguntaModel,PreguntaModel.id==OpcionRespuestaModel.pregunta_id)
            .join(EscenarioModel,EscenarioModel.id==PreguntaModel.escenario_id)
            .where(EscenarioModel.version_caso_id==datos.version.id,OpcionRespuestaModel.tipo_transicion.is_(None)))
    observar("CP-I-09",defecto=defecto,escenas_iniciales=iniciales,transiciones_sin_configurar=faltantes,
        http=respuesta.status_code,respuesta=respuesta.json(),intentos=len(filas(datos)))
    assert respuesta.status_code==503
    assert respuesta.json()["detail"]["codigo"]=="INTEGRACION_O_POLITICA_PENDIENTE"
    assert filas(datos)==[]
