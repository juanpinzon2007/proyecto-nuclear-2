from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, Request, HTTPException

from app.modules.identity.api.dependencies import (
    obtener_fabrica_autenticacion, obtener_proxy_administracion,
    obtener_proxy_excepciones, obtener_proxy_seguimiento, obtener_usuario_actual,
    obtener_consulta_feedback_estudiantil,
    obtener_fabrica_autenticacion_personal,
    obtener_fabrica_sesiones_login,
    obtener_fabrica_tokens,
    obtener_notificador_negocio,
    obtener_remitente_codigo_primer_ingreso,
    obtener_remitente_codigo_recuperacion,
)
from app.modules.identity.api.errors import RutaIdentity
from app.modules.identity.api.schemas import (
    AutorizacionesDocenteSchema, CrearDocente, IdPublico, RespuestaAccesoEstudiante,
    RespuestaMensajeOperacion, RespuestaToken,
    SolicitudConfirmarRecuperacion, SolicitudFeedback, SolicitudLogin, SolicitudLoginPersonal,
    SolicitudRecuperarContrasena, SolicitudRepeticion, SolicitudVerificarPrimerIngreso, UsuarioPublico,
    PaginaDocentesRespuesta, SolicitudPermisosDocentes, PerfilPermisosDocentesRespuesta,
)
from app.modules.identity.application.authentication import ServicioAutenticacion
from app.modules.identity.application.proxy_administracion import ProxyAdministracionUsuarios
from app.modules.identity.application.proxy_excepciones import ProxyExcepciones
from app.modules.identity.application.proxy_seguimiento import ProxySeguimiento
from app.modules.identity.domain.entities import (
    AutorizacionRepeticion, ContextoAcceso, DetalleParticipacion, FeedbackDocente, ResumenCaso, ResumenParticipacion,
    Rol, normalizar_correo,
)
from app.modules.identity.domain.errors import IntegracionPendiente, NoAutenticado, ReglaIdentidadInvalida
from app.modules.identity.infrastructure.business_notifications import notificar_registro_usuario
from app.modules.identity.infrastructure.credentials import CredencialesPersonalSQLAlchemy
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.onboarding import (
    estado_primer_ingreso,
    generar_y_enviar_codigo_primer_ingreso,
    verificar_codigo_primer_ingreso,
)
from app.modules.identity.infrastructure.password_recovery import (
    confirmar_recuperacion_contrasena,
    enviar_codigo_recuperacion_smtp,
    generar_y_enviar_codigo_recuperacion,
)
from app.modules.scheduling.infrastructure.mail_delivery import configuracion_correo
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.security import TokensJWT
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


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


@router.post("/auth/estudiantes/acceso", response_model=RespuestaAccesoEstudiante)
def autenticar_estudiante_por_clave(
    solicitud: SolicitudLoginPersonal,
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
    remitente_codigo: Annotated[Callable[..., None], Depends(obtener_remitente_codigo_primer_ingreso)],
) -> RespuestaAccesoEstudiante:
    """Autentica al estudiante con contraseña y solicita código por correo únicamente en su primer ingreso."""
    emisor = tokens()
    try:
        correo = normalizar_correo(solicitud.correo)
    except ReglaIdentidadInvalida:
        raise NoAutenticado() from None

    try:
        with sesiones() as db:
            actual = CredencialesPersonalSQLAlchemy(db).validar(correo, solicitud.clave.get_secret_value())
            if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
                raise NoAutenticado()
            uid = id_entero(actual.id_usuario)
            if estado_primer_ingreso(db, id_usuario=uid):
                return RespuestaAccesoEstudiante(
                    requiere_verificacion=False,
                    access_token=emisor.emitir(actual.id_usuario),
                )
            fila = db.get(UsuarioORM, uid)
            nombre = fila.nombre if fila is not None else actual.correo
            try:
                ttl = generar_y_enviar_codigo_primer_ingreso(
                    db,
                    id_usuario=uid,
                    correo=actual.correo,
                    nombre=nombre,
                    remitente_correo=remitente_codigo,
                )
                db.commit()
            except IntegracionPendiente:
                db.rollback()
                raise
            except SQLAlchemyError:
                db.rollback()
                raise IntegracionPendiente() from None
            return RespuestaAccesoEstudiante(
                requiere_verificacion=True,
                correo=actual.correo,
                mensaje="Primer inicio de sesión detectado. Revisa tu correo e ingresa el código de verificación.",
                expira_en_segundos=ttl,
            )
    except (ValueError, SQLAlchemyError):
        raise IntegracionPendiente() from None


@router.post("/auth/estudiantes/verificar-primer-ingreso", response_model=RespuestaToken)
def verificar_primer_ingreso_estudiante(
    solicitud: SolicitudVerificarPrimerIngreso,
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
    tokens: Annotated[Callable[[], TokensJWT], Depends(obtener_fabrica_tokens)],
) -> RespuestaToken:
    """Valida el código de verificación enviado al correo en el primer ingreso del estudiante."""
    emisor = tokens()
    try:
        correo = normalizar_correo(solicitud.correo)
    except ReglaIdentidadInvalida:
        raise NoAutenticado() from None
    codigo = solicitud.codigo.get_secret_value().strip()
    if not codigo:
        raise NoAutenticado()

    try:
        with sesiones() as db:
            actual = RepositorioUsuariosSQLAlchemy(db).obtener_por_correo(correo)
            if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
                raise NoAutenticado()
            uid = id_entero(actual.id_usuario)
            valido = verificar_codigo_primer_ingreso(db, id_usuario=uid, codigo=codigo)
            db.commit()
            if not valido:
                raise HTTPException(
                    401,
                    detail={
                        "codigo": "CODIGO_VERIFICACION_INVALIDO",
                        "mensaje": "El código de verificación es incorrecto o ha expirado.",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return RespuestaToken(access_token=emisor.emitir(actual.id_usuario))
    except (ValueError, SQLAlchemyError):
        raise IntegracionPendiente() from None


@router.post("/auth/recuperar-contrasena/solicitar", response_model=RespuestaMensajeOperacion)
def solicitar_recuperacion_clave(
    solicitud: SolicitudRecuperarContrasena,
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
    remitente_codigo: Annotated[Callable[..., None], Depends(obtener_remitente_codigo_recuperacion)],
) -> RespuestaMensajeOperacion:
    """Envía un código temporal al correo para recuperar la contraseña."""
    if remitente_codigo is enviar_codigo_recuperacion_smtp and configuracion_correo() is None:
        raise IntegracionPendiente()

    try:
        correo = normalizar_correo(solicitud.correo)
    except ReglaIdentidadInvalida:
        raise HTTPException(422, detail="Correo institucional inválido.") from None

    mensaje_ok = (
        "Si el correo está registrado y activo, enviamos un código de 6 dígitos "
        "para restablecer tu contraseña."
    )
    try:
        with sesiones() as db:
            actual = RepositorioUsuariosSQLAlchemy(db).obtener_por_correo(correo)
            if actual is not None and actual.activo:
                uid = id_entero(actual.id_usuario)
                fila = db.get(UsuarioORM, uid)
                nombre = fila.nombre if fila is not None else actual.correo
                try:
                    generar_y_enviar_codigo_recuperacion(
                        db,
                        id_usuario=uid,
                        correo=actual.correo,
                        nombre=nombre,
                        remitente_correo=remitente_codigo,
                    )
                    db.commit()
                except IntegracionPendiente:
                    db.rollback()
                    raise
                except SQLAlchemyError:
                    db.rollback()
                    raise IntegracionPendiente() from None
        return RespuestaMensajeOperacion(ok=True, mensaje=mensaje_ok)
    except (ValueError, SQLAlchemyError):
        raise IntegracionPendiente() from None


@router.post("/auth/recuperar-contrasena/confirmar", response_model=RespuestaMensajeOperacion)
def confirmar_recuperacion_clave(
    solicitud: SolicitudConfirmarRecuperacion,
    sesiones: Annotated[Callable[[], Session], Depends(obtener_fabrica_sesiones_login)],
) -> RespuestaMensajeOperacion:
    """Valida el código de recuperación y actualiza la contraseña del usuario."""
    try:
        correo = normalizar_correo(solicitud.correo)
    except ReglaIdentidadInvalida:
        raise NoAutenticado() from None

    codigo = solicitud.codigo.get_secret_value().strip()
    nueva_clave = solicitud.nueva_clave.get_secret_value()
    if not codigo or len(nueva_clave) < 6:
        raise HTTPException(422, detail="Ingresa el código y una nueva contraseña de al menos 6 caracteres.")

    try:
        with sesiones() as db:
            actual = RepositorioUsuariosSQLAlchemy(db).obtener_por_correo(correo)
            if actual is None or not actual.activo:
                raise HTTPException(
                    401,
                    detail={
                        "codigo": "CODIGO_RECUPERACION_INVALIDO",
                        "mensaje": "El código de recuperación es incorrecto o ha expirado.",
                    },
                )
            uid = id_entero(actual.id_usuario)
            ok = confirmar_recuperacion_contrasena(db, id_usuario=uid, codigo=codigo, nueva_clave=nueva_clave)
            db.commit()
            if not ok:
                raise HTTPException(
                    401,
                    detail={
                        "codigo": "CODIGO_RECUPERACION_INVALIDO",
                        "mensaje": "El código de recuperación es incorrecto o ha expirado.",
                    },
                )
            return RespuestaMensajeOperacion(
                ok=True,
                mensaje="Contraseña restablecida correctamente. Ya puedes iniciar sesión.",
            )
    except (ValueError, SQLAlchemyError):
        raise IntegracionPendiente() from None


@router.get("/me", response_model=UsuarioPublico)
def consultar_identidad(usuario: UsuarioActual) -> UsuarioPublico:
    return UsuarioPublico.desde_contexto(usuario)


@router.post("/docentes", response_model=UsuarioPublico, status_code=201)
def crear_docente(
    solicitud: CrearDocente,
    usuario: UsuarioActual,
    proxy: Administracion,
    background_tasks: BackgroundTasks,
    notificador: Annotated[Callable[..., None] | None, Depends(obtener_notificador_negocio)],
) -> UsuarioPublico:
    if solicitud.nombre is not None:
        creado = proxy.crear_docente(
            usuario, solicitud.correo, solicitud.a_dominio(), nombre=solicitud.nombre,
            clave=solicitud.clave.get_secret_value() if solicitud.clave else None,
        )
    else:
        creado = proxy.crear_docente(usuario, solicitud.correo, solicitud.a_dominio())
    notificar_registro_usuario(
        correo=creado.correo,
        nombre=solicitud.nombre or creado.correo,
        rol="DOCENTE",
        background_tasks=background_tasks,
        notificador=notificador,
    )
    return UsuarioPublico.desde_contexto(creado)


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


@router.get('/roles/docente/permisos', response_model=PerfilPermisosDocentesRespuesta)
def consultar_permisos_docentes(request: Request, usuario: UsuarioActual, proxy: Administracion):
    """Catálogo privado y perfil global vigente del rol docente."""
    if request.query_params:
        raise HTTPException(422, 'La consulta global no admite parámetros.')
    return proxy.consultar_permisos_docentes(usuario)


@router.put('/roles/docente/permisos', response_model=PerfilPermisosDocentesRespuesta)
def configurar_permisos_docentes(
    solicitud: SolicitudPermisosDocentes, request: Request, usuario: UsuarioActual, proxy: Administracion,
):
    """El cambio afecta a todas las cuentas del rol DOCENTE."""
    if request.query_params:
        raise HTTPException(422, 'La configuración global no admite parámetros.')
    return proxy.configurar_permisos_docentes(usuario, solicitud.permisos)


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
    responses={200: {"content": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {"schema": {"type": "string", "format": "binary"}},
        "application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        "description": "Publicación oficial histórica: seleccionar formato=xlsx o formato=pdf"},
        404: {"description": "Publicación oficial o versión inexistente"}})
def descargar_reporte(id_sesion: IdPublico, usuario: UsuarioActual, proxy: Seguimiento,
    request: Request, formato: Literal['xlsx','pdf'] | None = None,
    version_publicacion: Annotated[int | None, Query(gt=0)] = None,
    id_grupo: Annotated[int | None, Query(gt=0)] = None,
    id_estudiante: Annotated[list[int] | None, Query()] = None,
    estado: Literal['COMPLETA','PARCIAL','AUSENTE'] | None = None,
    agrupar_por: Literal['grupo','estudiante'] = 'grupo') -> Response:
    from app.modules.identity.application.official_reports import FiltrosReporte
    permitidos={'formato','version_publicacion','id_grupo','id_estudiante','estado','agrupar_por'}
    if set(request.query_params)-permitidos or any(i<=0 for i in id_estudiante or []):
        raise HTTPException(422, 'Parámetros de reporte inválidos')
    if formato is None:
        if request.query_params:raise HTTPException(422, 'Se requiere formato=xlsx o formato=pdf')
        # Contrato anterior conservado; no habilita CSV sin fuente oficial.
        return Response(proxy.descargar_reporte(usuario,id_sesion),media_type='text/csv',
            headers={'Content-Disposition':'attachment; filename="reporte-participacion.csv"'})
    filtros=FiltrosReporte(version_publicacion,id_grupo,tuple(sorted(set(id_estudiante or []))),estado,agrupar_por)
    archivo=proxy.descargar_reporte(usuario,id_sesion,formato=formato,filtros=filtros)
    return Response(archivo.contenido,media_type=archivo.media_type,headers={
        'Content-Disposition':f'attachment; filename="{archivo.nombre}"',
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
        'X-Publicacion-Id':str(archivo.publicacion_id),'X-Publicacion-Version':str(archivo.version),
        'X-Publicacion-SHA256':archivo.sha256})


@router.get(
    "/seguimiento/sesiones/{id_sesion}/reporte-provisional",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {"schema": {"type": "string", "format": "binary"}},
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
            },
            "description": "Reporte provisional en tiempo real de sesiones activas o no publicadas aún.",
        },
        404: {"description": "Sesión inexistente"},
    },
)
def descargar_reporte_provisional(
    id_sesion: IdPublico,
    usuario: UsuarioActual,
    formato: Literal["xlsx", "pdf"] = "pdf",
) -> Response:
    from app.db.session import get_session_factory
    from app.modules.identity.infrastructure.provisional_reports import generar_reporte_provisional

    with get_session_factory()() as db:
        contenido, media_type, nombre = generar_reporte_provisional(db, usuario, id_sesion, formato)
    return Response(
        contenido,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


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


from app.modules.identity.api.users_management_router import router as _users_management_router  # noqa: E402

router.include_router(_users_management_router)
