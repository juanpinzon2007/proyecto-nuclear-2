"""Regresión 8A: HTTP ASGI y SQL SQLite/PostgreSQL de laboratorio.

Reutiliza login/JWT/resolver SQL existentes. Solo la ventana y el reloj positivos
son sintéticos. No demuestra persistencia de intentos ni una política RF-22 real.
"""

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
import jwt
import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.modules.cases.application.published_version import consultar_version_publicada
from app.modules.cases.domain.enums import EstadoCaso
from app.modules.cases.domain.exceptions import CasoNoEncontradoError
from app.modules.cases.infrastructure.models import RubricaModel, VersionCasoModel
from app.modules.identity.api import academic_dependencies
from app.modules.identity.application.academic_identity import SistemaAcademico, VinculoAcademico
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy as Vinculos
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy
from app.modules.participation.api.dependencies import EstudianteAutenticado, obtener_estudiante_actual
from app.modules.participation.api.router import router
from app.modules.participation.application.errors import AccesoDenegado, RecursoNoDisponible, ReglaPendiente
from app.modules.participation.infrastructure.integration import ConsultaIngresoSQLAlchemy
from app.modules.scheduling.domain.ingress_policy import PoliticaIngresoNoConfigurada
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, NotificacionModel, SesionProgramadaModel
from tests.identity.academic_identity_support import motor_identidades, cuentas_identidades  # noqa: F401
from tests.identity.test_student_login_scheduling import login_sql, login, SECRETO  # noqa: F401
from tests.unit.scheduling.ingress_support import politica_fixture, restaurar_utc_solo_fixture_sqlite


AHORA = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
SONDA = "/sonda-identidad-participation-8a"
INICIO = "/api/v1/participations/20/attempts"


@pytest.fixture
def integracion(login_sql):
    c = login_sql
    c.app.include_router(router)  # Solo aplicación de prueba, nunca main.py.

    @c.app.get(SONDA)
    def sonda(estudiante: Annotated[EstudianteAutenticado, Depends(obtener_estudiante_actual)]):
        return estudiante.model_dump(mode="json")

    with c.sesiones.begin() as s:
        sesion = s.get(SesionProgramadaModel, c.sesion)
        sesion.estado = "EN_CURSO"
        sesion.fecha_inicio = AHORA - timedelta(minutes=5)
        sesion.fecha_fin = AHORA + timedelta(hours=1)
        version = s.get(VersionCasoModel, sesion.version_caso_id)
        version_id, caso_id = version.id, version.caso_id
        # Referencia sintética cargada antes de publicar por login_sql.
        rubrica = s.scalar(select(RubricaModel).where(RubricaModel.version_caso_id==version_id))
        rubrica_id = rubrica.id
    event.listen(c.sesiones, "loaded_as_persistent", restaurar_utc_solo_fixture_sqlite)
    try:
        respuesta = login(c)
        assert respuesta.status_code == 200, respuesta.text
        yield SimpleNamespace(**vars(c), token=respuesta.json()["access_token"],
                              version=version_id, caso_id=caso_id, rubrica=rubrica_id)
    finally:
        event.remove(c.sesiones, "loaded_as_persistent", restaurar_utc_solo_fixture_sqlite)


def cabeceras(c, token=None):
    return {"Authorization": "Bearer " + (c.token if token is None else token)}


def version_fixture(s, c, *, rubrica=True, estado=EstadoCaso.PUBLICADO, regla="regla-lab-otra"):
    """Contenido sintético: cargar en BORRADOR, luego fijar el estado del escenario.

    Sin rúbrica representa un dato académico incompleto para probar el lector,
    no una publicación legítima mediante la Chain ni un bypass de triggers.
    """
    v=VersionCasoModel(caso_id=c.caso_id,numero=2,nombre="Versión de prueba",
                       desarrollo_situacional="d",contexto_historia="c",tiempo_estimado_min=30,
                       estado=EstadoCaso.BORRADOR)
    s.add(v);s.flush()
    r=None
    if rubrica:
        r=RubricaModel(version_caso_id=v.id,nombre="Referencia de prueba",version_regla=regla)
        s.add(r);s.flush()
    if estado!=EstadoCaso.BORRADOR:
        v.estado=EstadoCaso.PUBLICADO;s.flush()
        if estado==EstadoCaso.ARCHIVADO:v.estado=estado;s.flush()
    return v,r


def principal(c, s) -> ContextoAcceso:
    # Verificación del JWT realmente emitido por el login HTTP del laboratorio.
    identidad = c.tokens.verificar(c.token)
    cuenta = RepositorioUsuariosSQLAlchemy(s).obtener(identidad.id_usuario)
    return replace(cuenta, id_convocatoria=identidad.id_convocatoria)


def consulta(c, *, politica=None, convocatoria=None, codigo=None, usuario=None, consulta_version=None):
    with c.sesiones() as s:
        adaptador = ConsultaIngresoSQLAlchemy(
            s, politica=politica if politica is not None else PoliticaIngresoNoConfigurada(),
            reloj=SimpleNamespace(ahora=lambda: AHORA),
            consulta_version=consulta_version,
        )
        return adaptador.consultar(
            usuario=usuario if usuario is not None else principal(c, s),
            convocatoria_id=convocatoria if convocatoria is not None else c.convocatoria,
            codigo_acceso=codigo if codigo is not None else c.codigo,
        )


def test_identidad_real_separa_cuenta_y_uuid_sin_confiar_en_cabeceras(integracion):
    c = integracion
    respuesta = c.cliente.get(SONDA + "?student_id=999", headers=cabeceras(c) | {
        "X-Student-ID": "999", "X-Docente-Id": str(uuid4()),
    })
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id_estudiante": c.propio, "id_estudiante_scheduling": str(c.uuid),
        "id_convocatoria": str(c.convocatoria),
    }


@pytest.mark.parametrize("problema", ["ausente", "invalido", "vencido", "manipulado", "inexistente"])
def test_jwt_rechazado_sin_exponer_datos(integracion, problema):
    c = integracion
    if problema == "ausente":
        headers = {}
    elif problema == "invalido":
        headers = cabeceras(c, "token-inventado")
    elif problema == "inexistente":
        headers = cabeceras(c, c.tokens.emitir("2147483647", str(c.convocatoria)))
    else:
        claims = jwt.decode(c.token, SECRETO, algorithms=["HS256"],
                            issuer="login-sql-test", audience="login-sql-client")
        clave = SECRETO
        if problema == "vencido":
            ahora = int(datetime.now(timezone.utc).timestamp())
            claims.update(iat=ahora - 900, nbf=ahora - 900, exp=ahora - 1)
        else:
            clave = "otra-clave-exclusiva-de-laboratorio-" * 2
        headers = cabeceras(c, jwt.encode(claims, clave, algorithm="HS256"))
    respuesta = c.cliente.get(SONDA, headers=headers)
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert "id_estudiante" not in respuesta.json()


@pytest.mark.parametrize("problema,estado", [("inactivo", 401), ("docente", 403), ("ambiguo", 503)])
def test_estado_vigente_y_asociacion_se_leen_del_servidor(integracion, problema, estado):
    c = integracion
    with c.sesiones.begin() as s:
        if problema == "inactivo":
            s.get(UsuarioORM, c.propio).activo = False
        elif problema == "docente":
            s.get(UsuarioORM, c.propio).id_rol = 1
        else:
            Vinculos(s).agregar_verificado(VinculoAcademico(str(c.propio), SistemaAcademico.SCHEDULING, uuid4()))
    assert c.cliente.get(SONDA, headers=cabeceras(c)).status_code == estado


def test_cuenta_sin_asociacion_no_recibe_uuid_nuevo(integracion):
    c = integracion
    identificador = c.ajeno + 1_000_000
    with c.sesiones.begin() as s:
        s.add(UsuarioORM(id_usuario=identificador, id_rol=2, nombre="Solo laboratorio",
                         correo=f"sin-vinculo-{identificador}@universidad.test", clave_hash="fixture"))
    token = c.tokens.emitir(str(identificador), str(c.convocatoria))
    assert c.cliente.get(SONDA, headers=cabeceras(c, token)).status_code == 403


@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("post", INICIO, {"id_consentimiento": 30}),
    ("post", "/api/v1/participations/999/attempts", {"id_consentimiento": 30}),
    ("get", "/api/v1/attempts/999/progress", None),
    ("post", "/api/v1/attempts/999/finish", None),
    ("post", "/api/v1/attempts/999/decisions/1", {"id_opcion": 1}),
    ("get", "/api/v1/participations/20/attempts/999/result", None),
])
def test_identidad_valida_no_abre_fachada_ni_recursos_sin_mapeo(integracion, metodo, ruta, cuerpo):
    c = integracion
    datos = {} if cuerpo is None else {"json": cuerpo}
    respuesta = c.cliente.request(metodo, ruta, headers=cabeceras(c), **datos)
    assert respuesta.status_code == 503
    assert respuesta.json()["detail"]["codigo"] == "INTEGRACION_NO_CONFIGURADA"
    assert respuesta.headers["cache-control"] == "no-store"
    # No existe escritor ni permiso implícito por ID de URL, propio o ajeno.
    assert "nota_final" not in respuesta.text


def test_fallo_de_infraestructura_identity_no_concede_acceso(integracion):
    c = integracion
    def fallar():
        raise SQLAlchemyError("detalle privado de conexión")
    c.app.dependency_overrides[academic_dependencies.obtener_fabrica_sesiones_academicas] = lambda: fallar
    respuesta = c.cliente.get(SONDA, headers=cabeceras(c))
    assert respuesta.status_code == 503 and "detalle privado" not in respuesta.text


def test_sin_rf22_no_se_obtiene_contexto_de_ingreso(integracion):
    with pytest.raises(ReglaPendiente):
        consulta(integracion)


def test_contexto_sql_con_ventana_sintetica_conserva_version_asignada(integracion):
    c = integracion
    with c.sesiones.begin() as s:
        posterior,otra_rubrica=version_fixture(s,c,regla="regla-lab-8a-v2")
        rubrica_posterior_id = otra_rubrica.id
    contexto = consulta(c, politica=politica_fixture(15))
    assert contexto.estudiante_scheduling_id == c.uuid
    assert contexto.convocatoria_id == c.convocatoria and contexto.sesion_id == c.sesion
    assert contexto.caso_id == c.caso_id and contexto.version_caso_id == c.version
    assert contexto.numero_version == 1 and contexto.tiempo_maximo == timedelta(minutes=20)
    assert contexto.rubrica_id == c.rubrica and contexto.rubrica_id != rubrica_posterior_id
    assert contexto.version_regla == "regla-lab-8a-v1"
    assert not {"es_correcta", "justificacion", "puntaje", "nota_final", "id_nivel"}.intersection(asdict(contexto))


def test_rubrica_de_otra_version_no_completa_la_asignada(integracion):
    c = integracion
    with c.sesiones.begin() as s:
        sin_rubrica,_=version_fixture(s,c,rubrica=False)
        s.get(SesionProgramadaModel, c.sesion).version_caso_id = sin_rubrica.id
    # La rúbrica de v1 sigue existiendo, pero la sesión tiene asignada v2.
    with pytest.raises(RecursoNoDisponible):
        consulta(c, politica=politica_fixture(15))


def test_rf22_bloquea_antes_de_consultar_version_y_rubrica(integracion, monkeypatch):
    def no_debe_consultarse(*args, **kwargs):
        pytest.fail("Sin política temporal no debe consultarse contenido académico")
    monkeypatch.setattr("app.modules.participation.infrastructure.integration.consultar_version_publicada",
                        no_debe_consultarse)
    with pytest.raises(ReglaPendiente):
        consulta(integracion)


@pytest.mark.parametrize("etapa", ["politica", "referencia_cases"])
def test_fallo_de_dependencia_en_etapa_final_no_devuelve_contexto(integracion, monkeypatch, etapa):
    def fallar(*args, **kwargs):
        raise SQLAlchemyError("detalle SQL privado de la dependencia")
    politica = politica_fixture(15)
    if etapa == "politica":
        politica.obtener_ventana = fallar
    else:
        monkeypatch.setattr("app.modules.participation.infrastructure.integration.consultar_version_publicada", fallar)
    with pytest.raises(ReglaPendiente) as error:
        consulta(integracion, politica=politica)
    assert "detalle SQL privado" not in str(error.value)


@pytest.mark.parametrize("problema", ["ajena", "inexistente", "retirada", "codigo", "sin_contexto"])
def test_contexto_rechaza_convocatoria_o_codigo_no_autorizado(integracion, problema):
    c = integracion
    opciones = {}
    if problema == "ajena":
        # Contexto ajeno simulado internamente: la BD también exige titularidad.
        with c.sesiones() as s:
            opciones["usuario"] = replace(principal(c, s), id_convocatoria=str(c.convocatoria_ajena))
        opciones.update(convocatoria=c.convocatoria_ajena, codigo=c.codigo_ajeno)
    elif problema == "inexistente":
        identificador = uuid4()
        with c.sesiones() as s:
            opciones["usuario"] = replace(principal(c, s), id_convocatoria=str(identificador))
        opciones["convocatoria"] = identificador
    elif problema == "retirada":
        with c.sesiones.begin() as s:
            s.get(ConvocatoriaModel, c.convocatoria).estado = "RETIRADA"
    elif problema == "codigo":
        opciones["codigo"] = "no-es-el-codigo"
    else:
        with c.sesiones() as s:
            opciones["usuario"] = replace(principal(c, s), id_convocatoria=None)
    with pytest.raises(AccesoDenegado):
        consulta(c, politica=politica_fixture(15), **opciones)


@pytest.mark.parametrize("estado", ["SIN_INICIAR", "FINALIZADO"])
def test_scheduling_conserva_control_de_estado(integracion, estado):
    c = integracion
    with c.sesiones.begin() as s:
        s.get(SesionProgramadaModel, c.sesion).estado = estado
    with pytest.raises(AccesoDenegado):
        consulta(c, politica=politica_fixture(15))


@pytest.mark.parametrize("estado", [EstadoCaso.BORRADOR, EstadoCaso.ARCHIVADO])
def test_version_asignada_no_publicada_no_se_sustituye(integracion, estado):
    c = integracion
    with c.sesiones.begin() as s:
        otra,_=version_fixture(s,c,estado=estado)
        s.get(SesionProgramadaModel,c.sesion).version_caso_id=otra.id
    with pytest.raises(RecursoNoDisponible):
        consulta(c, politica=politica_fixture(15))


def test_version_inexistente_rechazada_por_consulta_publica(integracion):
    with integracion.sesiones() as s:
        with pytest.raises(CasoNoEncontradoError):
            consultar_version_publicada(s, version_id=uuid4())


@pytest.mark.parametrize("relacion", ["sesion", "version", "rubrica"])
def test_integridad_real_impide_contextos_invalidos_y_se_revierte(integracion, relacion):
    c = integracion
    with c.sesiones() as s:
        if relacion == "sesion":
            s.get(ConvocatoriaModel, c.convocatoria).sesion_id = uuid4()
        elif relacion == "version":
            s.get(SesionProgramadaModel, c.sesion).version_caso_id = uuid4()
        else:
            s.get(RubricaModel, c.rubrica).version_caso_id = uuid4()
        with pytest.raises(IntegrityError) as error:
            s.flush()
        if s.get_bind().dialect.name=="postgresql":
            # Rúbrica histórica: el trigger actúa antes de la FK; otras referencias
            # inexistentes siguen rechazadas por sus FK originales.
            assert error.value.orig.sqlstate==("23514" if relacion=="rubrica" else "23503")
        s.rollback()
    # El rollback conserva la asociación original en el laboratorio.
    contexto = consulta(c, politica=politica_fixture(15))
    assert contexto.sesion_id == c.sesion and contexto.version_caso_id == c.version
    assert contexto.rubrica_id == c.rubrica


def test_rubrica_unica_por_version_se_conserva_tras_rollback(integracion):
    c = integracion
    with c.sesiones() as s:
        borrador,_=version_fixture(s,c,estado=EstadoCaso.BORRADOR)
        s.add(RubricaModel(version_caso_id=borrador.id, nombre="Duplicado solo de laboratorio",
                          version_regla="regla-duplicada"))
        with pytest.raises(IntegrityError) as error:
            s.flush()
        if s.get_bind().dialect.name=="postgresql":
            assert error.value.orig.sqlstate=="23505"
        s.rollback()
    contexto = consulta(c, politica=politica_fixture(15))
    assert contexto.rubrica_id == c.rubrica and contexto.version_regla == "regla-lab-8a-v1"


def test_lectura_no_confirma_ni_vuelca_cambios_pendientes(integracion):
    c = integracion
    identificador = uuid4()
    with c.sesiones() as s:
        usuario = principal(c, s)
        pendiente = NotificacionModel(id=identificador, destinatario_id=c.uuid,
                                      tipo="SONDA_8A", canal="INTERNA", mensaje="Solo fixture")
        s.add(pendiente)
        adaptador = ConsultaIngresoSQLAlchemy(s, politica=politica_fixture(15),
                                             reloj=SimpleNamespace(ahora=lambda: AHORA))
        adaptador.consultar(usuario=usuario, convocatoria_id=c.convocatoria, codigo_acceso=c.codigo)
        assert pendiente in s.new
        s.rollback()
    with c.sesiones() as s:
        assert s.scalar(select(NotificacionModel.id).where(NotificacionModel.id == identificador)) is None


def test_fallo_sql_en_consulta_se_propaga_cerrado_sin_datos_privados(integracion, monkeypatch):
    c = integracion
    with c.sesiones() as s:
        usuario = principal(c, s)
        def fallar(*args, **kwargs):
            raise SQLAlchemyError("contraseña y detalles SQL privados")
        monkeypatch.setattr(s, "get", fallar)
        adaptador = ConsultaIngresoSQLAlchemy(s, politica=politica_fixture(15),
                                             reloj=SimpleNamespace(ahora=lambda: AHORA))
        with pytest.raises(ReglaPendiente) as error:
            adaptador.consultar(usuario=usuario, convocatoria_id=c.convocatoria, codigo_acceso=c.codigo)
        assert "privados" not in str(error.value)
        s.rollback()


def test_consulta_inyectada_delega_version_exacta_sin_escribir(integracion, monkeypatch):
    c = integracion
    with c.sesiones.begin() as s:
        version_fixture(s,c,regla="regla-lab-posterior")
    esperado = consulta(c, politica=politica_fixture(15))
    llamadas = []
    with c.sesiones() as s:
        usuario = principal(c, s)
        pendiente = NotificacionModel(destinatario_id=c.uuid, tipo="SONDA_INYECCION",
                                      canal="INTERNA", mensaje="Solo fixture")
        s.add(pendiente)

        def no_escribir(*args, **kwargs):
            pytest.fail("La consulta inyectada no debe hacer flush ni commit")

        monkeypatch.setattr(s, "flush", no_escribir)
        monkeypatch.setattr(s, "commit", no_escribir)

        def delegar(db, *, version_id):
            llamadas.append((db, version_id))
            return consultar_version_publicada(db, version_id=version_id)

        adaptador = ConsultaIngresoSQLAlchemy(
            s, politica=politica_fixture(15), reloj=SimpleNamespace(ahora=lambda: AHORA),
            consulta_version=delegar,
        )
        actual = adaptador.consultar(usuario=usuario, convocatoria_id=c.convocatoria, codigo_acceso=c.codigo)
        assert llamadas == [(s, c.version)]
        assert actual == esperado
        assert actual.rubrica_id == c.rubrica and actual.version_regla == "regla-lab-8a-v1"
        assert pendiente in s.new and s.in_transaction()
        s.rollback()


@pytest.mark.parametrize("error,traducido", [
    (CasoNoEncontradoError, RecursoNoDisponible), (SQLAlchemyError, ReglaPendiente),
])
def test_error_consulta_inyectada_no_usa_fallback_ni_expone_detalles(integracion, error, traducido):
    llamadas = []

    def fallar(db, *, version_id):
        llamadas.append(version_id)
        raise error("detalle privado de la consulta inyectada")

    with pytest.raises(traducido) as resultado:
        consulta(integracion, politica=politica_fixture(15), consulta_version=fallar)
    assert llamadas == [integracion.version]
    assert "detalle privado" not in str(resultado.value)


@pytest.mark.parametrize("problema,esperado", [
    ("rf22", ReglaPendiente), ("ajena", AccesoDenegado), ("codigo", AccesoDenegado),
    ("sin_contexto", AccesoDenegado), ("inactivo", AccesoDenegado),
    ("sin_rol", AccesoDenegado), ("ambiguo", ReglaPendiente), ("sesion_finalizada", AccesoDenegado),
])
def test_consulta_inyectada_no_se_invoca_antes_de_autorizacion(integracion, problema, esperado):
    c = integracion
    opciones = {"politica": politica_fixture(15)}
    if problema == "rf22":
        opciones["politica"] = PoliticaIngresoNoConfigurada()
    elif problema == "codigo":
        opciones["codigo"] = "codigo-no-autorizado"
    elif problema in {"ajena", "sin_contexto"}:
        with c.sesiones() as s:
            opciones["usuario"] = replace(principal(c, s), id_convocatoria=(
                str(c.convocatoria_ajena) if problema == "ajena" else None))
        if problema == "ajena":
            opciones.update(convocatoria=c.convocatoria_ajena, codigo=c.codigo_ajeno)
    else:
        with c.sesiones.begin() as s:
            if problema == "inactivo":
                s.get(UsuarioORM, c.propio).activo = False
            elif problema == "sin_rol":
                s.get(UsuarioORM, c.propio).id_rol = 1
            elif problema == "ambiguo":
                Vinculos(s).agregar_verificado(VinculoAcademico(str(c.propio), SistemaAcademico.SCHEDULING, uuid4()))
            else:
                s.get(SesionProgramadaModel, c.sesion).estado = "FINALIZADO"

    def no_consultar(*args, **kwargs):
        pytest.fail("La inyección no puede adelantar la consulta de Cases")

    with pytest.raises(esperado):
        consulta(c, consulta_version=no_consultar, **opciones)


@pytest.mark.parametrize("problema", ["borrador", "archivada", "sin_rubrica"])
def test_consulta_inyectada_real_conserva_rechazos_de_cases(integracion, problema):
    c = integracion
    with c.sesiones.begin() as s:
        otra,_=version_fixture(s,c,rubrica=problema!="sin_rubrica",estado=(
            EstadoCaso.BORRADOR if problema=="borrador" else
            EstadoCaso.ARCHIVADO if problema=="archivada" else EstadoCaso.PUBLICADO))
        s.get(SesionProgramadaModel,c.sesion).version_caso_id=otra.id
    with pytest.raises(RecursoNoDisponible):
        consulta(c, politica=politica_fixture(15), consulta_version=consultar_version_publicada)
