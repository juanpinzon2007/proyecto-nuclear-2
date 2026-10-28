import csv
from dataclasses import replace
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock

import pytest

from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.application.ports import LecturaReportes, ValidadorConvocatoria
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.proxy_excepciones import ProxyExcepciones
from app.modules.identity.application.proxy_seguimiento import ProxySeguimiento
from app.modules.identity.application.services import (
    ServicioAdministracionUsuarios, ServicioExcepciones, ServicioFeedbackDocente, ServicioReportes,
)
from app.modules.identity.domain.entities import (
    AccesoConvocatoria, AutorizacionesDocente, CondicionesRepeticion,
    EstadoReporte, FilaReporte, Rol,
)
from app.modules.identity.domain.errors import (
    AccesoDenegado, ConflictoIdentidad, IntegracionPendiente, NoAutenticado, ReglaIdentidadInvalida,
)


def servicio_login(escenario, tokens, dominios=("universidad.test",)):
    convocatorias = Mock(spec=ValidadorConvocatoria)
    convocatorias.validar.return_value = AccesoConvocatoria("estudiante-1", "convocatoria-1")
    servicio = ServicioAutenticacion(escenario.usuarios, convocatorias, tokens, dominios)
    return servicio, convocatorias


def test_login_valida_la_pareja_correo_codigo_antes_de_emitir(escenario, tokens):
    servicio, convocatorias = servicio_login(escenario, tokens)
    token = servicio.autenticar_estudiante("Alumno@Universidad.Test", "codigo-convocatoria")
    convocatorias.validar.assert_called_once_with("alumno@universidad.test", "codigo-convocatoria")
    assert tokens.verificar(token).id_convocatoria == "convocatoria-1"


@pytest.mark.parametrize("correo,codigo", [
    ("alumno@otra.test", "codigo"), ("alumno@universidad.test.evil.test", "codigo"),
    ("alumno@sub.universidad.test", "codigo"), ("malformado", "codigo"),
    ("alumno@universidad.test", "   "), ("alumno\n@universidad.test", "codigo"),
])
def test_login_rechaza_dominio_o_datos_invalidos_sin_consultar(escenario, tokens, correo, codigo):
    servicio, convocatorias = servicio_login(escenario, tokens)
    with pytest.raises(NoAutenticado):
        servicio.autenticar_estudiante(correo, codigo)
    convocatorias.validar.assert_not_called()


def test_login_sin_dominios_confirmados_no_admite_acceso(escenario, tokens):
    servicio, convocatorias = servicio_login(escenario, tokens, ())
    with pytest.raises(IntegracionPendiente):
        servicio.autenticar_estudiante("alumno@universidad.test", "codigo")
    convocatorias.validar.assert_not_called()


def test_login_rechaza_codigo_no_validado(escenario, tokens):
    servicio, convocatorias = servicio_login(escenario, tokens)
    convocatorias.validar.return_value = None
    with pytest.raises(NoAutenticado):
        servicio.autenticar_estudiante("alumno@universidad.test", "incorrecto")


@pytest.mark.parametrize("tipo", ["inactivo", "correo_ajeno", "docente", "inexistente"])
def test_login_no_autentica_una_identidad_ajena_a_la_convocatoria(escenario, tokens, tipo):
    usuario = escenario.estudiante
    nuevo = {"inactivo": replace(usuario, activo=False),
             "correo_ajeno": replace(usuario, correo="otro@universidad.test"),
             "docente": replace(usuario, roles=frozenset({Rol.DOCENTE})), "inexistente": None}[tipo]
    escenario.identidades[usuario.id_usuario] = nuevo
    servicio, _ = servicio_login(escenario, tokens)
    with pytest.raises(NoAutenticado):
        servicio.autenticar_estudiante("alumno@universidad.test", "codigo")


def test_permiso_especifico_no_se_deduce_del_rol_docente(escenario):
    with pytest.raises(AccesoDenegado):
        escenario.autorizacion.exigir_permiso(escenario.docente, "CREAR_CASOS")
    habilitado = replace(escenario.docente, permisos=frozenset({"CREAR_CASOS"}))
    escenario.autorizacion.exigir_permiso(habilitado, "CREAR_CASOS")


@pytest.mark.parametrize("operacion", ["lista", "detalle", "reporte", "feedback", "excepcion", "administracion"])
def test_estudiante_no_alcanza_servicios_protegidos(escenario, operacion):
    fabrica = Mock(side_effect=AssertionError("No debe construirse el servicio real."))
    seguimiento = ProxySeguimiento(fabrica, escenario.autorizacion)
    llamadas = {
        "lista": lambda: seguimiento.listar_casos_realizados(escenario.estudiante),
        "detalle": lambda: seguimiento.consultar_participacion(escenario.estudiante, "p1"),
        "reporte": lambda: seguimiento.descargar_reporte(escenario.estudiante, "s1"),
        "feedback": lambda: seguimiento.registrar_feedback(escenario.estudiante, "p1", "Comentario"),
        "excepcion": lambda: ProxyExcepciones(fabrica, escenario.autorizacion).autorizar_repeticion(escenario.estudiante, "s1", "e1"),
        "administracion": lambda: ProxyAdministracionUsuarios(fabrica, escenario.autorizacion).crear_docente(
            escenario.estudiante, "docente@universidad.test", AutorizacionesDocente(frozenset({Rol.DOCENTE}), frozenset())),
    }
    with pytest.raises(AccesoDenegado):
        llamadas[operacion]()
    fabrica.assert_not_called()
    escenario.academia.puede_consultar_participacion.assert_not_called()


def test_seguimiento_denegado_no_delega_a_repositorio(escenario):
    fabrica = Mock()
    escenario.academia.puede_consultar_participacion.return_value = False
    with pytest.raises(AccesoDenegado):
        ProxySeguimiento(fabrica, escenario.autorizacion).consultar_participacion(escenario.docente, "p-ajena")
    fabrica.assert_not_called()


@pytest.mark.parametrize("creador,previa,finalizada,error", [
    (False, True, False, AccesoDenegado), (True, False, False, ConflictoIdentidad),
    (True, True, True, ConflictoIdentidad),
])
def test_excepcion_exige_creador_participacion_y_sesion_no_finalizada(escenario, creador, previa, finalizada, error):
    escenario.academia.condiciones_repeticion.return_value = CondicionesRepeticion(creador, previa, finalizada)
    servicio = ServicioExcepciones(lambda: escenario.trabajo)
    with pytest.raises(error):
        ProxyExcepciones(lambda: servicio, escenario.autorizacion).autorizar_repeticion(escenario.docente, "s1", "e1")
    escenario.trabajo.autorizaciones.guardar.assert_not_called()
    escenario.trabajo.commit.assert_not_called()


def test_excepcion_guarda_concesion_sin_crear_intentos(escenario):
    servicio = ServicioExcepciones(lambda: escenario.trabajo)
    concesion = ProxyExcepciones(lambda: servicio, escenario.autorizacion).autorizar_repeticion(escenario.docente, "s1", "e1")
    assert concesion.id_docente_autorizador == escenario.docente.id_usuario
    assert concesion.fecha_autorizacion.utcoffset().total_seconds() == 0
    escenario.trabajo.autorizaciones.guardar.assert_called_once_with(concesion)
    escenario.trabajo.commit.assert_called_once()


def test_feedback_revalida_ambito_dentro_de_transaccion(escenario):
    escenario.academia.puede_consultar_participacion.return_value = False
    with pytest.raises(AccesoDenegado):
        ServicioFeedbackDocente(lambda: escenario.trabajo).registrar(escenario.docente, "p1", "Comentario")
    escenario.trabajo.feedback.agregar.assert_not_called()
    escenario.trabajo.commit.assert_not_called()


def test_feedback_registra_autor_y_fecha_del_servidor(escenario):
    resultado = ServicioFeedbackDocente(lambda: escenario.trabajo).registrar(escenario.docente, "p1", " Buen análisis ")
    assert resultado.texto == "Buen análisis"
    assert resultado.id_docente == escenario.docente.id_usuario
    escenario.trabajo.feedback.agregar.assert_called_once_with(resultado)
    escenario.trabajo.commit.assert_called_once()


@pytest.mark.parametrize("texto", [" ", "\x00", "a" * 10001])
def test_feedback_invalido_no_abre_transaccion(escenario, texto):
    fabrica = Mock()
    with pytest.raises(ReglaIdentidadInvalida):
        ServicioFeedbackDocente(fabrica).registrar(escenario.docente, "p1", texto)
    fabrica.assert_not_called()


def test_reporte_conserva_parciales_ausentes_y_precision_sin_inventar_ceros(escenario):
    lecturas = Mock(spec=LecturaReportes)
    lecturas.obtener_filas.return_value = (
        FilaReporte("e1", "p1", EstadoReporte.COMPLETA, Decimal("4.25")),
        FilaReporte("e2", "p2", EstadoReporte.PARCIAL, Decimal("2.10")),
        FilaReporte("e3", None, EstadoReporte.AUSENCIA, None),
    )
    contenido = ServicioReportes(lecturas).descargar(escenario.docente, "s1")
    filas = list(csv.DictReader(StringIO(contenido)))
    assert [f["estado"] for f in filas] == ["COMPLETA", "PARCIAL", "AUSENCIA"]
    assert [f["nota"] for f in filas] == ["4.25", "2.10", ""]
    assert filas[2]["id_participacion"] == ""
    lecturas.obtener_filas.assert_called_once_with(escenario.docente.id_usuario, "s1")


def test_reporte_neutraliza_formulas_en_identificadores(escenario):
    lecturas = Mock(spec=LecturaReportes)
    lecturas.obtener_filas.return_value = (FilaReporte("=1+1", None, EstadoReporte.AUSENCIA, None),)
    filas = list(csv.DictReader(StringIO(ServicioReportes(lecturas).descargar(escenario.docente, "s1"))))
    assert filas[0]["id_estudiante"] == "'=1+1"


def test_administracion_solo_acepta_permisos_del_catalogo(escenario):
    escenario.usuarios.permisos_existentes.return_value = False
    servicio = ServicioAdministracionUsuarios(lambda: escenario.trabajo)
    with pytest.raises(ReglaIdentidadInvalida):
        ProxyAdministracionUsuarios(lambda: servicio, escenario.autorizacion).crear_docente(
            escenario.administrador, "nuevo@universidad.test", AutorizacionesDocente(frozenset({Rol.DOCENTE}), frozenset({"INVENTADO"})))
    escenario.usuarios.crear_docente.assert_not_called()
    escenario.trabajo.commit.assert_not_called()
