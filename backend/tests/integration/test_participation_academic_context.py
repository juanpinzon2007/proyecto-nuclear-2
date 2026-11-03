"""BD2-06: login/JWT SQL reales; ventana temporal positiva SOLO de laboratorio.

SQLite aislado y PostgreSQL recién creado por motor_identidades; sin URLs del
proyecto. No se abren endpoints nuevos ni se simula persistencia de intentos.
"""
from dataclasses import asdict, replace
from datetime import timedelta
import itertools
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError

from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Vinculos
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.participation.application.errors import AccesoDenegado, ReglaPendiente
from app.modules.participation.infrastructure.academic_context import ConsultaVinculacionSQLAlchemy
from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from tests.identity.academic_identity_support import motor_identidades, cuentas_identidades  # noqa: F401
from tests.identity.test_student_login_scheduling import login_sql  # noqa: F401
from tests.integration.test_participation_8a import integracion, principal, AHORA, version_fixture  # noqa: F401
from tests.unit.scheduling.ingress_support import politica_fixture

CLAVES_SINTETICAS = itertools.count(10001)
DOCENTES_SINTETICOS = itertools.count(400000001)


@pytest.fixture
def vinculado(integracion):
    c = integracion
    with c.sesiones.begin() as s:
        caso = s.get(CasoModel, c.caso_id)
        if s.bind.dialect.name == "sqlite":
            # SQLite no implementa la secuencia PG. Identidad de fixture explícita
            # en la MISMA fila de caso; no se deriva de ningún usuario ni UUID.
            caso.id_caso = next(CLAVES_SINTETICAS)
        # Rango de fixture separado del contador compartido de cuentas Identity.
        docente = UsuarioORM(id_usuario=next(DOCENTES_SINTETICOS), id_rol=1, nombre="Docente sintético", correo=f"{uuid4()}@fixture.test", clave_hash="no-utilizable")
        s.add(docente); s.flush()
        grupo = GrupoAcademicoORM(id_profesor=docente.id_usuario, nombre="Grupo de laboratorio", periodo="2026-2")
        s.add(grupo); s.flush()
        matricula = GrupoEstudianteORM(id_grupo=grupo.id_grupo, id_estudiante=c.propio, fecha_ingreso=AHORA.replace(tzinfo=None))
        s.add(matricula); s.flush()
        asignacion = AsignacionCasoModel(id_grupo=grupo.id_grupo, id_caso=caso.id_caso,
            sesion_programada_id=c.sesion, version_caso_id=c.version,
            apertura=(AHORA-timedelta(minutes=5)).replace(tzinfo=None),
            cierre=(AHORA+timedelta(hours=1)).replace(tzinfo=None), fecha_limite_ingreso=AHORA.replace(tzinfo=None), tiempo_maximo_min=20)
        s.add(asignacion); s.flush()
        datos = dict(id_asignacion=asignacion.id_asignacion, id_grupo=grupo.id_grupo,
                     id_matricula=matricula.id_grupo_estudiante, id_caso_academico=caso.id_caso)
    return SimpleNamespace(**vars(c), **datos)


def consultar(c, *, politica=None, id_asignacion=None, convocatoria=None, codigo=None, consulta_version=None, sesion=None, usuario=None):
    def llamada(s):
        return ConsultaVinculacionSQLAlchemy(s,
            politica=politica_fixture(10) if politica is None else politica,
            reloj=SimpleNamespace(ahora=lambda: AHORA), consulta_version=consulta_version,
        ).consultar(usuario=principal(c, s) if usuario is None else usuario,
            convocatoria_id=c.convocatoria if convocatoria is None else convocatoria,
            codigo_acceso=c.codigo if codigo is None else codigo,
            id_asignacion=c.id_asignacion if id_asignacion is None else id_asignacion)
    if sesion is not None:
        return llamada(sesion)
    with c.sesiones() as s:
        return llamada(s)


def test_contexto_acredita_referencias_reales_y_no_filtra_evaluacion(vinculado):
    c = vinculado
    resultado = consultar(c)
    assert (resultado.id_usuario, resultado.id_grupo_estudiante, resultado.id_grupo,
            resultado.id_asignacion, resultado.id_caso_academico) == (c.propio, c.id_matricula, c.id_grupo, c.id_asignacion, c.id_caso_academico)
    assert resultado.ingreso.estudiante_scheduling_id == c.uuid
    assert resultado.ingreso.convocatoria_id == c.convocatoria
    assert resultado.ingreso.sesion_id == c.sesion
    assert resultado.ingreso.version_caso_id == c.version
    assert resultado.ingreso.rubrica_id == c.rubrica
    serializado = str(asdict(resultado)).lower()
    for privado in (c.codigo.lower(), c.correo.lower(), "clave_hash", "puntaje", "es_correcta", "justificacion"):
        assert privado not in serializado


@pytest.mark.parametrize("problema", ["sin_matricula", "inactiva", "grupo_ajeno"])
def test_matricula_inexistente_inactiva_o_ajena_cierra(vinculado, problema):
    c = vinculado
    with c.sesiones.begin() as s:
        fila = s.get(GrupoEstudianteORM, c.id_matricula)
        if problema == "sin_matricula":
            s.delete(fila)
        elif problema == "inactiva":
            fila.activo = False
        else:
            fila.id_estudiante = c.ajeno
    with pytest.raises(AccesoDenegado, match="Vinculación académica no disponible"):
        consultar(c)


@pytest.mark.parametrize("problema", ["ajena", "retirada", "inexistente", "codigo_grupal"])
def test_convocatoria_y_codigo_no_conceden_pertenencia(vinculado, problema):
    c = vinculado
    if problema == "retirada":
        with c.sesiones.begin() as s:
            s.get(ConvocatoriaModel, c.convocatoria).estado = "RETIRADA"
    parametros = {
        "ajena": dict(convocatoria=c.convocatoria_ajena, codigo=c.codigo_ajeno),
        "inexistente": dict(convocatoria=uuid4()), "codigo_grupal": dict(codigo="codigo-grupal-no-autorizado"),
    }.get(problema, {})
    with pytest.raises(AccesoDenegado):
        consultar(c, **parametros)


@pytest.mark.parametrize("identificador", [2147483647, 0, -1, True, "1", 2147483648])
def test_asignacion_inexistente_o_id_no_valido_no_enumera(vinculado, identificador):
    with pytest.raises(AccesoDenegado, match="Vinculación académica no disponible"):
        consultar(vinculado, id_asignacion=identificador)


@pytest.mark.parametrize("otra_version", [False, True])
def test_asignacion_de_otra_sesion_rechazada(vinculado, otra_version):
    c = vinculado
    with c.sesiones.begin() as s:
        original = s.get(SesionProgramadaModel, c.sesion)
        version = version_fixture(s, c)[0].id if otra_version else c.version
        otra = SesionProgramadaModel(espacio_academico_id=original.espacio_academico_id,
            version_caso_id=version, docente_id=original.docente_id, fecha_inicio=original.fecha_inicio,
            fecha_fin=original.fecha_fin, tiempo_maximo_minutos=20, estado="EN_CURSO")
        s.add(otra); s.flush()
        asignacion = AsignacionCasoModel(id_grupo=c.id_grupo, id_caso=c.id_caso_academico,
            sesion_programada_id=otra.id, version_caso_id=version, apertura=AHORA.replace(tzinfo=None),
            cierre=(AHORA+timedelta(hours=1)).replace(tzinfo=None), fecha_limite_ingreso=AHORA.replace(tzinfo=None), tiempo_maximo_min=20)
        s.add(asignacion); s.flush()
        identificador = asignacion.id_asignacion
    with pytest.raises(AccesoDenegado):
        consultar(c, id_asignacion=identificador)


@pytest.mark.parametrize("campo", ["version_id", "rubrica_id", "caso_id", "version_regla", "numero"])
def test_referencia_cases_incompatible_no_se_acepta(vinculado, campo):
    from app.modules.cases.application.published_version import consultar_version_publicada
    with vinculado.sesiones.begin() as s:
        otra, _ = version_fixture(s, vinculado)
        ajena = consultar_version_publicada(s, version_id=otra.id)
    def equivocada(s, *, version_id):
        real = consultar_version_publicada(s, version_id=version_id)
        valor = "otra-regla" if campo == "version_regla" else (99 if campo == "numero" else getattr(ajena, campo))
        if campo == "caso_id":
            valor = uuid4()  # Las dos ediciones anteriores pertenecen a la misma familia.
        return replace(real, **{campo: valor})
    with pytest.raises(AccesoDenegado):
        consultar(vinculado, consulta_version=equivocada)


def test_asignacion_de_grupo_sin_matricula_no_se_elige_implicitamente(vinculado):
    c = vinculado
    with c.sesiones.begin() as s:
        propio = s.get(GrupoAcademicoORM, c.id_grupo)
        grupo = GrupoAcademicoORM(id_profesor=propio.id_profesor, nombre="Otro grupo", periodo="2026-2")
        s.add(grupo); s.flush()
        asignacion = AsignacionCasoModel(id_grupo=grupo.id_grupo, id_caso=c.id_caso_academico,
            sesion_programada_id=c.sesion, version_caso_id=c.version, apertura=AHORA.replace(tzinfo=None),
            cierre=(AHORA+timedelta(hours=1)).replace(tzinfo=None), fecha_limite_ingreso=AHORA.replace(tzinfo=None), tiempo_maximo_min=20)
        s.add(asignacion); s.flush()
        identificador = asignacion.id_asignacion
    with pytest.raises(AccesoDenegado):
        consultar(c, id_asignacion=identificador)


def test_identidad_ambigua_cierra_sin_elegir(vinculado):
    c = vinculado
    with c.sesiones.begin() as s:
        Vinculos(s).agregar_verificado(VinculoAcademico(str(c.propio), SistemaAcademico.SCHEDULING, uuid4()))
    with pytest.raises(ReglaPendiente):
        consultar(c)


def test_rf22_sin_politica_bloquea_antes_de_cases_y_matricula(vinculado):
    consulta = Mock(side_effect=AssertionError("Cases no debe consultarse"))
    with pytest.raises(ReglaPendiente):
        consultar(vinculado, politica=PoliticaIngresoNoConfigurada(), consulta_version=consulta)
    consulta.assert_not_called()


def test_fallo_sql_de_vinculacion_cierra_sin_detalles_privados(vinculado):
    c = vinculado
    def fallar(conn, cursor, statement, params, context, many):
        if "FROM asignacion_caso" in statement:
            raise SQLAlchemyError("secreto de conexión privado")
    event.listen(c.engine, "before_cursor_execute", fallar)
    try:
        with pytest.raises(ReglaPendiente) as error:
            consultar(c)
        assert "secreto" not in str(error.value) and "privado" not in str(error.value)
    finally:
        event.remove(c.engine, "before_cursor_execute", fallar)


def test_consulta_no_escribe_no_flush_no_commit_ni_pierde_cambios_pendientes(vinculado):
    c = vinculado
    sentencias = []
    def registrar(conn, cursor, statement, params, context, many):
        sentencias.append(statement.lstrip().split()[0].upper())
    with c.sesiones() as s:
        actual = principal(c, s)
        pendiente = UsuarioORM(id_rol=2, nombre="Sin flush", correo=f"{uuid4()}@fixture.test", clave_hash="no-utilizable")
        s.add(pendiente)
        event.listen(c.engine, "before_cursor_execute", registrar)
        try:
            consultar(c, sesion=s, usuario=actual)
            assert pendiente in s.new and pendiente.id_usuario is None
            assert not set(sentencias) & {"INSERT", "UPDATE", "DELETE", "COMMIT"}
            assert s.in_transaction()
        finally:
            event.remove(c.engine, "before_cursor_execute", registrar)
        s.rollback()


def test_publicacion_posterior_no_sustituye_referencia(vinculado):
    c = vinculado
    with c.sesiones.begin() as s:
        nueva, rubrica = version_fixture(s, c)
        posterior, rubrica_posterior = nueva.id, rubrica.id
    resultado = consultar(c)
    assert resultado.ingreso.version_caso_id == c.version != posterior
    assert resultado.ingreso.rubrica_id == c.rubrica != rubrica_posterior
