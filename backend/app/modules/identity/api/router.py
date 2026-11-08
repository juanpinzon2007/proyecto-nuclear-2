from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.modules.identity.api.dependencies import (
    obtener_fabrica_autenticacion, obtener_proxy_administracion,
    obtener_proxy_excepciones, obtener_proxy_seguimiento, obtener_usuario_actual,
    obtener_consulta_feedback_estudiantil,
    obtener_fabrica_autenticacion_personal,
)
from app.modules.identity.api.errors import RutaIdentity
from app.modules.identity.api.schemas import (
    AutorizacionesDocenteSchema, CrearDocente, IdPublico, RespuestaToken,
    SolicitudFeedback, SolicitudLogin, SolicitudLoginPersonal, SolicitudRepeticion, UsuarioPublico,
    PaginaDocentesRespuesta,
)
from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.proxy_excepciones import ProxyExcepciones
from app.modules.identity.application.proxy_seguimiento import ProxySeguimiento
from app.modules.identity.domain.entities import (
    AutorizacionRepeticion, ContextoAcceso, DetalleParticipacion, FeedbackDocente, ResumenCaso, ResumenParticipacion,
)


router = APIRouter(
    prefix="/api/v1/identity", tags=["identity"], route_class=RutaIdentity,
    responses={401: {"description": "Credenciales ausentes o inválidas"},
               403: {"description": "Operación denegada por el Proxy"},
               503: {"description": "Integración o configuración pendiente"}},
)
UsuarioActual = Annotated[ContextoAcceso, Depends(obtener_usuario_actual)]
Seguimiento = Annotated[ProxySeguimiento, Depends(obtener_proxy_seguimiento)]
Excepciones = Annotated[ProxyExcepciones, Depends(obtener_proxy_excepciones)]
Administracion = Annotated[ProxyAdministracionUsuarios, Depends(obtener_proxy_administracion)]


@router.post("/auth/estudiantes", response_model=RespuestaToken)
def autenticar_estudiante(
    solicitud: SolicitudLogin,
    servicio: Annotated[Callable[[], ServicioAutenticacion], Depends(obtener_fabrica_autenticacion)],
) -> RespuestaToken:
    token = servicio().autenticar_estudiante(solicitud.correo, solicitud.codigo_convocatoria.get_secret_value())
    return RespuestaToken(access_token=token)


@router.post("/auth/personal", response_model=RespuestaToken)
def autenticar_personal(
    solicitud: SolicitudLoginPersonal,
    servicio: Annotated[Callable[[], ServicioAutenticacion], Depends(obtener_fabrica_autenticacion_personal)],
) -> RespuestaToken:
    token = servicio().autenticar_personal(solicitud.correo, solicitud.clave.get_secret_value())
    return RespuestaToken(access_token=token)


@router.get("/me", response_model=UsuarioPublico)
def consultar_identidad(usuario: UsuarioActual) -> UsuarioPublico:
    return UsuarioPublico.desde_contexto(usuario)


@router.post("/docentes", response_model=UsuarioPublico, status_code=201)
def crear_docente(solicitud: CrearDocente, usuario: UsuarioActual, proxy: Administracion) -> UsuarioPublico:
    if solicitud.nombre is not None:
        return UsuarioPublico.desde_contexto(proxy.crear_docente(
            usuario, solicitud.correo, solicitud.a_dominio(), nombre=solicitud.nombre,
            clave=solicitud.clave.get_secret_value() if solicitud.clave else None,
        ))
    return UsuarioPublico.desde_contexto(proxy.crear_docente(usuario, solicitud.correo, solicitud.a_dominio()))


@router.get("/docentes", response_model=PaginaDocentesRespuesta)
def consultar_docentes(usuario: UsuarioActual, proxy: Administracion,
    limite: Annotated[int, Query(ge=1, le=100)] = 25,
    desplazamiento: Annotated[int, Query(ge=0)] = 0):
    """Cuentas docentes; no incluye permisos ni asociaciones académicas."""
    return proxy.consultar_docentes(usuario, limite=limite, desplazamiento=desplazamiento)


@router.put("/docentes/{id_docente}/autorizaciones", response_model=UsuarioPublico)
def asignar_autorizaciones(id_docente: IdPublico, solicitud: AutorizacionesDocenteSchema,
                          usuario: UsuarioActual, proxy: Administracion) -> UsuarioPublico:
    return UsuarioPublico.desde_contexto(proxy.asignar_autorizaciones(usuario, id_docente, solicitud.a_dominio()))


@router.get("/seguimiento/casos", response_model=list[ResumenCaso], response_model_exclude_none=True)
def listar_casos_realizados(usuario: UsuarioActual, proxy: Seguimiento):
    return proxy.listar_casos_realizados(usuario)


@router.get("/seguimiento/participaciones/{id_participacion}", response_model=DetalleParticipacion)
def consultar_participacion(id_participacion: IdPublico, usuario: UsuarioActual, proxy: Seguimiento):
    return proxy.consultar_participacion(usuario, id_participacion)


@router.get("/seguimiento/casos/{id_caso}/participaciones", response_model=list[ResumenParticipacion])
def listar_participaciones(id_caso: IdPublico, usuario: UsuarioActual, proxy: Seguimiento):
    return proxy.listar_participaciones(usuario, id_caso)


@router.get("/seguimiento/sesiones/{id_sesion}/reporte", response_class=Response,
            responses={200: {"content": {"text/csv": {}}, "description": "Reporte CSV académico"}})
def descargar_reporte(id_sesion: IdPublico, usuario: UsuarioActual, proxy: Seguimiento) -> Response:
    return Response(proxy.descargar_reporte(usuario, id_sesion), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="reporte-participacion.csv"'})


@router.post("/seguimiento/participaciones/{id_participacion}/feedback", response_model=FeedbackDocente, status_code=201)
def registrar_feedback(id_participacion: IdPublico, solicitud: SolicitudFeedback,
                       usuario: UsuarioActual, proxy: Seguimiento):
    return proxy.registrar_feedback(usuario, id_participacion, solicitud.texto)


@router.get("/seguimiento/participaciones/{id_participacion}/feedback", response_model=FeedbackDocente)
def consultar_feedback_estudiantil(
    id_participacion: IdPublico,
    consulta: Annotated[Callable[..., FeedbackDocente], Depends(obtener_consulta_feedback_estudiantil)],
):
    """Valoración general propia; no devuelve respuestas, correcciones ni notas."""
    return consulta(id_participacion=id_participacion)


@router.post("/excepciones/repeticiones", response_model=AutorizacionRepeticion, response_model_exclude_none=True, status_code=201)
def autorizar_repeticion(solicitud: SolicitudRepeticion, usuario: UsuarioActual, proxy: Excepciones):
    return proxy.autorizar_repeticion(usuario, solicitud.id_sesion, solicitud.id_estudiante)
