"""Rutas REST del módulo de programación académica."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from app.modules.participation.api.dependencies import obtener_fechas_escenario
from app.modules.participation.application.errors import ReglaPendiente
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente

from app.db.session import get_db, get_session_factory
from app.modules.scheduling.api.dependencies import exigir_contexto_convocatoria
from app.modules.scheduling.api.dependencies import obtener_admision
from app.modules.scheduling.api.dependencies import obtener_autorizacion_espacios_programacion
from app.modules.scheduling.application.programming_access import AutorizacionEspacioProgramacion
from app.modules.scheduling.infrastructure.programming_access import programar_sesion_autorizada
from app.modules.scheduling.infrastructure.academic_assignment import ProgramacionAcademicaPersistida
from app.modules.identity.api.academic_dependencies import obtener_docente_scheduling, obtener_estudiante_scheduling, DocenteActual
from app.modules.scheduling.api.schemas import (
    ProgramarSesionRequest,
    CambiarEstadoRequest,
    SesionResponse,
    SesionConAsignacionResponse,
    CrearConvocatoriaRequest,
    ConvocatoriaResponse,
    ConvocatoriaDetalleResponse,
    EspacioAcademicoResponse,
    CrearEspacioAcademicoRequest,
    ValidarIngresoRequest,
    NotificacionResponse,
    NotificarCalificacionRequest,
    ActualizarSesionRequest,
)
from app.modules.scheduling.application.crear_convocatoria import (
    ErrorConvocatoria,
)
from app.modules.scheduling.application.codigos_convocatoria import CorreoConvocatoriaNoDisponible
from app.modules.scheduling.infrastructure.convocation_management import convocar_con_aviso, retirar_con_aviso
from app.modules.scheduling.application.cambiar_estado_sesion import SesionNoEncontradaError
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.api.dependencies import obtener_estudiante_actual
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.scheduling.infrastructure.ingress_access import exigir_matricula_ingreso
from app.modules.scheduling.application.programar_sesion import (
    ErrorProgramacion,
    programar_sesion,
)
from app.modules.scheduling.application.cambiar_estado_y_publicar import (
    cambiar_estado_y_publicar,
)
from app.modules.scheduling.application.registrar_observadores import (
    crear_gestor_eventos,
)
from app.modules.scheduling.application.validar_ingreso import (
    ErrorIngreso,
    validar_ingreso,
)
from app.modules.scheduling.domain.state import (
    TransicionInvalidaError,
)
from app.modules.scheduling.domain.ingress_policy import (
    PoliticaIngreso, PoliticaIngresoNoConfigurada,
    PoliticaTemporalNoDisponible, RelojIngreso, RelojServidor,
)
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
    ConvocatoriaModel,
    NotificacionModel,
    DocenteEspacioAcademicoModel,
)
from app.modules.scheduling.application.crear_notificacion import (
    crear_notificacion,
)


router = APIRouter(
    prefix="/scheduling",
    tags=["Scheduling"],
)

DETALLE_CORREO_CONVOCATORIA = {
    'codigo': 'CORREO_CONVOCATORIA_NO_DISPONIBLE',
    'mensaje': 'El correo de SPS no está configurado. Habilítalo para emitir las convocatorias.',
}


def obtener_docente_autenticado(
    docente_id: Annotated[UUID, Depends(obtener_docente_scheduling)],
) -> UUID:
    """Sin resolver persistente real no se habilita ninguna operación docente."""
    return docente_id


Docente = Annotated[
    UUID,
    Depends(obtener_docente_autenticado),
]

Estudiante = Annotated[UUID, Depends(obtener_estudiante_scheduling)]


def exigir_politica_ingreso_configurada() -> PoliticaIngreso:
    """El ingreso desde el inicio programado sigue sin política suficiente."""
    return PoliticaIngresoNoConfigurada()


def obtener_reloj_ingreso() -> RelojIngreso:
    return RelojServidor()

BaseDatos = Annotated[
    Session,
    Depends(get_db),
]

FabricaSesion = Annotated[
    sessionmaker[Session],
    Depends(get_session_factory),
]


# =========================================================================
# Espacios Académicos (RF-04 / RF-18)
# =========================================================================

@router.get(
    "/espacios",
    response_model=list[EspacioAcademicoResponse],
)
def listar_espacios(docente_id: Docente, db: BaseDatos, usuario: DocenteActual):
    """Selecciona espacios concedidos explícitamente al docente autenticado.

    El INTEGER de Identity procede del JWT revalidado, nunca del UUID de
    Scheduling. Crear un espacio no concede permiso para programarlo.
    """
    consulta = (
        select(EspacioAcademicoModel)
        .join(DocenteEspacioAcademicoModel,
              DocenteEspacioAcademicoModel.espacio_academico_id == EspacioAcademicoModel.id)
        .where(DocenteEspacioAcademicoModel.id_docente == id_entero(usuario.id_usuario))
        .order_by(EspacioAcademicoModel.nombre, EspacioAcademicoModel.id)
    )
    try:
        with db.no_autoflush:
            return db.scalars(consulta).all()
    except SQLAlchemyError:
        raise HTTPException(503, detail="Consulta académica no disponible.") from None


@router.post(
    "/espacios",
    response_model=EspacioAcademicoResponse,
    status_code=201,
)
def crear_espacio(
    datos: CrearEspacioAcademicoRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """Registra un nuevo espacio académico (requiere autorización docente)."""
    espacio = EspacioAcademicoModel(nombre=datos.nombre.strip())
    db.add(espacio)
    db.commit()
    db.refresh(espacio)
    return espacio


# =========================================================================
# Sesiones Académicas (RF-18, RF-19)
# =========================================================================

@router.get(
    "/sesiones",
    response_model=list[SesionResponse],
)
def listar_sesiones(
    docente_autenticado: Docente,
    db: BaseDatos,
    docente_id: UUID | None = None,
    espacio_id: UUID | None = None,
):
    """Lista las sesiones programadas con filtros opcionales."""
    if docente_id is not None and docente_id != docente_autenticado:
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar sesiones de otro docente.")
    consulta = select(SesionProgramadaModel).where(
        SesionProgramadaModel.docente_id == docente_autenticado,
    )
    if espacio_id is not None:
        consulta = consulta.where(SesionProgramadaModel.espacio_academico_id == espacio_id)
    consulta = consulta.order_by(SesionProgramadaModel.fecha_inicio.desc())
    return db.scalars(consulta).all()


@router.get(
    "/sesiones/{sesion_id}",
    response_model=SesionResponse,
)
def obtener_sesion(
    sesion_id: UUID,
    docente_id: Docente,
    db: BaseDatos,
):
    """Obtiene el detalle de una sesión académica."""
    sesion = db.get(SesionProgramadaModel, sesion_id)
    if sesion is None:
        raise HTTPException(
            status_code=404,
            detail="Sesión no encontrada.",
        )
    if sesion.docente_id != docente_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar esta sesión.")
    return sesion


@router.post(
    "/sesiones",
    response_model=SesionConAsignacionResponse | SesionResponse,
    status_code=201,
)
def crear_sesion(
    datos: ProgramarSesionRequest,
    response: Response,
    docente_id: Docente,
    db: BaseDatos,
    usuario: DocenteActual,
    autorizacion: Annotated[AutorizacionEspacioProgramacion | None, Depends(obtener_autorizacion_espacios_programacion)],
):
    """Programa una sesión académica (RF-18)."""
    try:
        sesion = programar_sesion_autorizada(
            db,
            usuario=usuario,autorizacion_espacio=autorizacion,
            docente_id=docente_id,
            fechas_asignacion=obtener_fechas_escenario() if datos.grupo_id is not None else None,
            **datos.model_dump(),
        )

        # No abrir otra lectura después de confirmar: un fallo de refresh no
        # debe comunicar rollback cuando la sesión ya quedó persistida.
        if isinstance(sesion, ProgramacionAcademicaPersistida):
            base = SesionResponse.model_validate(sesion.sesion).model_dump()
            resultado = SesionConAsignacionResponse(**base, id_asignacion=sesion.id_asignacion,
                convocatorias=[dict(convocatoria_id=c.convocatoria_id, estudiante_id=c.estudiante_id)
                               for c in sesion.convocatorias])
            response.headers['Cache-Control'] = 'no-store'
        else:
            resultado=SesionResponse.model_validate(sesion)
        db.commit()
        return resultado

    except CorreoConvocatoriaNoDisponible:
        db.rollback()
        raise HTTPException(503, detail=DETALLE_CORREO_CONVOCATORIA, headers={'Cache-Control': 'no-store'}) from None
    except (AccesoDenegado, IntegracionPendiente, SQLAlchemyError, ReglaPendiente, MapeoPersistenciaPendiente) as error:
        db.rollback()
        estado=403 if isinstance(error,AccesoDenegado) else 503
        raise HTTPException(estado,detail='Autorización académica de programación no disponible.',
            headers={'Cache-Control':'no-store'}) from None

    except ErrorProgramacion as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


@router.patch(
    "/sesiones/{sesion_id}",
    response_model=SesionResponse,
)
def actualizar_sesion(
    sesion_id: UUID,
    datos: ActualizarSesionRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """Actualiza horarios/condiciones de la sesión y notifica cambios a estudiantes convocados (RF-18/RF-21)."""
    sesion = db.get(SesionProgramadaModel, sesion_id, with_for_update=True, populate_existing=True)
    if sesion is None:
        raise HTTPException(404, detail="Sesión no encontrada.")
    if sesion.docente_id != docente_id:
        raise HTTPException(403, detail="No tienes permiso para modificar esta sesión.")
    if sesion.estado == "FINALIZADO":
        raise HTTPException(409, detail="No se pueden modificar sesiones ya finalizadas.")

    from app.modules.cases.infrastructure.models.caso import VersionCasoModel
    from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
    from app.modules.scheduling.infrastructure.mail_delivery import encolar_correo

    version = db.get(VersionCasoModel, sesion.version_caso_id)

    nuevo_inicio = datos.fecha_inicio if datos.fecha_inicio is not None else sesion.fecha_inicio
    nuevo_fin = datos.fecha_fin if datos.fecha_fin is not None else sesion.fecha_fin
    if nuevo_inicio.utcoffset() is None or nuevo_fin.utcoffset() is None:
        raise HTTPException(422, detail="Las fechas deben incluir zona horaria.")
    if nuevo_fin <= nuevo_inicio:
        raise HTTPException(422, detail="La fecha final debe ser posterior a la inicial.")

    if datos.tiempo_maximo_minutos is not None:
        if version is not None and datos.tiempo_maximo_minutos > version.tiempo_estimado_min:
            raise HTTPException(422, detail="El tiempo máximo supera el estimado del caso.")
        sesion.tiempo_maximo_minutos = datos.tiempo_maximo_minutos

    sesion.fecha_inicio = nuevo_inicio
    sesion.fecha_fin = nuevo_fin
    if datos.lugar is not None:
        sesion.lugar = datos.lugar.strip() or None
    if datos.mensaje_personalizado is not None:
        sesion.mensaje_personalizado = datos.mensaje_personalizado.strip() or None

    # Sincronizar asignación si existe
    fechas = obtener_fechas_escenario()
    asigs = db.scalars(select(AsignacionCasoModel).where(AsignacionCasoModel.sesion_programada_id == sesion.id)).all()
    for a in asigs:
        a.apertura = fechas.hacia_db(nuevo_inicio, sin_offset=True)
        a.cierre = fechas.hacia_db(nuevo_fin, sin_offset=True)
        a.tiempo_maximo_min = sesion.tiempo_maximo_minutos

    # Notificar cambios relevantes a todos los estudiantes con convocatoria ACTIVA (RF-21)
    activas = db.scalars(
        select(ConvocatoriaModel).where(
            ConvocatoriaModel.sesion_id == sesion.id,
            ConvocatoriaModel.estado == "ACTIVA",
        )
    ).all()
    nombre_caso = version.nombre if version else "Caso clínico"
    for conv in activas:
        notif = crear_notificacion(
            db,
            destinatario_id=conv.estudiante_id,
            convocatoria_id=conv.id,
            tipo="CAMBIO_SESION",
            canal="INTERNA",
            mensaje=(
                f"Se actualizaron condiciones de la sesión '{nombre_caso}': "
                f"inicio {nuevo_inicio.isoformat()}, fin {nuevo_fin.isoformat()}"
                f"{f', lugar: {sesion.lugar}' if sesion.lugar else ''}."
            ),
        )
        encolar_correo(db, notificacion=notif, caso=nombre_caso, sesion=sesion)

    db.commit()
    db.refresh(sesion)
    return sesion


@router.post(
    "/sesiones/{sesion_id}/estado",
    response_model=SesionResponse,
)
async def actualizar_estado(
    sesion_id: UUID,
    datos: CambiarEstadoRequest,
    docente_id: Docente,
    db: BaseDatos,
    session_factory: FabricaSesion,
):
    """Inicia o finaliza una sesión de su docente (RF-19)."""
    sesion = db.get(
        SesionProgramadaModel,
        sesion_id,
        with_for_update=True,
        populate_existing=True,
    )

    if sesion is None:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Sesión no encontrada.",
        )

    if sesion.docente_id != docente_id:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para modificar esta sesión.",
        )

    gestor = crear_gestor_eventos(session_factory)

    try:
        return await cambiar_estado_y_publicar(
            db,
            sesion_id=sesion_id,
            accion=datos.accion,
            gestor=gestor,
            origen="DOCENTE",
        )

    except TransicionInvalidaError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error
    except IntegracionPendiente:
        db.rollback()
        raise HTTPException(503,detail='Admisión no disponible.',headers={'Cache-Control':'no-store'}) from None
    except SQLAlchemyError as error:
        db.rollback()
        estado=409 if getattr(error.orig,'sqlstate',None)=='55P03' else 503
        raise HTTPException(estado,detail='Conflicto de habilitación; reintente.' if estado==409
            else 'Persistencia de sesión no disponible.',headers={'Cache-Control':'no-store'}) from None


# =========================================================================
# Convocatorias (RF-20, RF-21)
# =========================================================================

@router.get(
    "/sesiones/{sesion_id}/convocatorias",
    response_model=list[ConvocatoriaDetalleResponse],
)
def listar_convocatorias(
    sesion_id: UUID,
    docente_id: Docente,
    db: BaseDatos,
):
    """Lista las convocatorias de una sesión perteneciente al docente (RF-20)."""
    sesion = db.get(SesionProgramadaModel, sesion_id)
    if sesion is None:
        raise HTTPException(
            status_code=404,
            detail="Sesión no encontrada.",
        )
    if sesion.docente_id != docente_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para ver convocatorias de esta sesión.",
        )

    consulta = (
        select(ConvocatoriaModel)
        .where(ConvocatoriaModel.sesion_id == sesion_id)
        .order_by(ConvocatoriaModel.id)
    )
    return db.scalars(consulta).all()


@router.post(
    "/sesiones/{sesion_id}/convocatorias",
    response_model=ConvocatoriaResponse,
    status_code=201,
)
def convocar_estudiante(
    sesion_id: UUID,
    datos: CrearConvocatoriaRequest,
    docente_id: Docente,
    db: BaseDatos,
    respuesta: Response,
    usuario: DocenteActual,
):
    """Convoca a un estudiante a una sesión académica (RF-20)."""
    try:
        convocatoria_id = convocar_con_aviso(db,usuario=usuario,sesion_id=sesion_id,
            estudiante_id=datos.estudiante_id,docente_id=docente_id)

        # Confirmar ambas operaciones juntas.
        db.commit()
        respuesta.headers['Cache-Control']='no-store'
        return ConvocatoriaResponse(convocatoria_id=convocatoria_id)

    except CorreoConvocatoriaNoDisponible:
        db.rollback()
        raise HTTPException(503, detail=DETALLE_CORREO_CONVOCATORIA, headers={'Cache-Control': 'no-store'}) from None
    except (AccesoDenegado, IntegracionPendiente, SesionNoEncontradaError, SQLAlchemyError) as error:
        db.rollback()
        estado=403 if isinstance(error,AccesoDenegado) else 404 if isinstance(error,SesionNoEncontradaError) else 503
        raise HTTPException(estado,detail='Ámbito de convocatoria no disponible.',headers={'Cache-Control':'no-store'}) from None
    except ErrorConvocatoria as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


@router.delete('/sesiones/{sesion_id}/convocatorias/{convocatoria_id}',response_model=ConvocatoriaDetalleResponse)
def retirar_estudiante(sesion_id: UUID, convocatoria_id: UUID, docente_id: Docente, db: BaseDatos, respuesta: Response, usuario: DocenteActual):
    """Retiro lógico idempotente; conserva código hash y referencias históricas."""
    try:
        convocatoria=retirar_con_aviso(db,usuario=usuario,sesion_id=sesion_id,convocatoria_id=convocatoria_id,docente_id=docente_id)
        # Materializar antes de cerrar la transacción; no SELECT posterior al commit.
        resultado=ConvocatoriaDetalleResponse.model_validate(convocatoria)
        db.commit()
        respuesta.headers['Cache-Control']='no-store'
        return resultado
    except (AccesoDenegado, IntegracionPendiente, SesionNoEncontradaError, SQLAlchemyError) as error:
        db.rollback()
        estado=403 if isinstance(error,AccesoDenegado) else 404 if isinstance(error,SesionNoEncontradaError) else 503
        raise HTTPException(estado,detail='Ámbito de convocatoria no disponible.',headers={'Cache-Control':'no-store'}) from None
    except ErrorConvocatoria as error:
        db.rollback()
        raise HTTPException(422,detail=str(error)) from None
    except Exception:
        db.rollback()
        raise


# =========================================================================
# Validación de Ingreso de Estudiantes (RF-22)
# =========================================================================

@router.post(
    "/validar-ingreso",
    response_model=SesionResponse,
)
def validar_ingreso_estudiante(
    datos: ValidarIngresoRequest,
    estudiante_id: Estudiante,
    politica: Annotated[PoliticaIngreso, Depends(exigir_politica_ingreso_configurada)],
    usuario: Annotated[ContextoAcceso, Depends(obtener_estudiante_actual)],
    contexto: Annotated[None, Depends(exigir_contexto_convocatoria)],
    reloj: Annotated[RelojIngreso, Depends(obtener_reloj_ingreso)],
    admision: Annotated[object, Depends(obtener_admision)],
    db: BaseDatos,
    respuesta: Response,
):
    """Requiere titular autenticado además de código, convocatoria y horario."""
    if datos.estudiante_id != estudiante_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para validar el ingreso de otro estudiante.",
                            headers={"Cache-Control": "no-store"})
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        with db.no_autoflush:
            sesion = validar_ingreso(
                db,
                convocatoria_id=datos.convocatoria_id,
                estudiante_id=estudiante_id,
                codigo_acceso=datos.codigo_acceso,
                politica=politica,
                reloj=reloj,
                admision=admision,
            )
            exigir_matricula_ingreso(db, id_usuario=usuario.id_usuario, sesion=sesion)
            return sesion
    except ErrorIngreso as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
            headers={"Cache-Control": "no-store"},
        ) from error
    except AccesoDenegado:
        raise HTTPException(403, detail="Ingreso no autorizado.", headers={"Cache-Control": "no-store"}) from None
    except (PoliticaTemporalNoDisponible, IntegracionPendiente, SQLAlchemyError):
        raise HTTPException(503, detail="Política temporal o infraestructura de ingreso no disponible.",
                            headers={"Cache-Control": "no-store"}) from None


# =========================================================================
# Notificaciones (RF-21, RF-27)
# =========================================================================

@router.get(
    "/notificaciones",
    response_model=list[NotificacionResponse],
)
def listar_notificaciones(
    destinatario_id: UUID,
    estudiante_id: Estudiante,
    db: BaseDatos,
    respuesta: Response,
):
    """Solo las notificaciones del estudiante resuelto por el servidor."""
    if destinatario_id != estudiante_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar notificaciones ajenas.")
    respuesta.headers["Cache-Control"] = "no-store"
    consulta = (
        select(NotificacionModel)
        .where(NotificacionModel.destinatario_id == estudiante_id)
        .order_by(NotificacionModel.creada_en.desc())
    )
    return db.scalars(consulta).all()


@router.post(
    "/calificaciones/notificar",
    status_code=200,
    responses={503: {"description": "Publicación oficial no disponible; operación sin escritura."}},
)
def notificar_calificacion_participacion(
    datos: NotificarCalificacionRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """RF-27: notifica calificación oficial únicamente tras verificar titularidad docente y publicación oficial."""
    from fastapi.responses import JSONResponse
    from app.modules.cases.infrastructure.models.caso import VersionCasoModel
    from app.modules.participation.infrastructure.academic_results_models import (
        PublicacionEvaluacionModel,
        ResultadoParticipacionModel,
    )
    from app.modules.scheduling.infrastructure.mail_delivery import encolar_correo

    with db.no_autoflush:
        fila = db.execute(
            select(ConvocatoriaModel, SesionProgramadaModel, PublicacionEvaluacionModel, ResultadoParticipacionModel)
            .join(SesionProgramadaModel, SesionProgramadaModel.id == ConvocatoriaModel.sesion_id)
            .join(PublicacionEvaluacionModel, PublicacionEvaluacionModel.sesion_id == SesionProgramadaModel.id)
            .join(
                ResultadoParticipacionModel,
                (ResultadoParticipacionModel.publicacion_id == PublicacionEvaluacionModel.id)
                & (ResultadoParticipacionModel.convocatoria_id == ConvocatoriaModel.id),
            )
            .where(
                SesionProgramadaModel.docente_id == docente_id,
                ConvocatoriaModel.estudiante_id == datos.estudiante_id,
                ConvocatoriaModel.id == datos.participacion_id,
            )
            .order_by(PublicacionEvaluacionModel.version.desc())
            .limit(1)
        ).first()

    if fila is None:
        raise HTTPException(
            status_code=503,
            detail="La publicación de calificaciones oficiales todavía no está disponible.",
            headers={"Cache-Control": "no-store"},
        )

    conv, sesion, pub, res_part = fila
    version = db.get(VersionCasoModel, sesion.version_caso_id)
    notif = crear_notificacion(
        db,
        destinatario_id=datos.estudiante_id,
        convocatoria_id=conv.id,
        tipo="CALIFICACION",
        canal="INTERNA",
        mensaje=(
            f"Recordatorio oficial de calificación ({res_part.situacion}): "
            f"nota {res_part.nota_definitiva}/100 disponible en la plataforma."
        ),
    )
    if version is not None:
        encolar_correo(db, notificacion=notif, caso=version.nombre, sesion=sesion)
    db.commit()
    return JSONResponse(
        status_code=200,
        content={"notificado": True, "notificacion_id": str(notif.id)},
        headers={"Cache-Control": "no-store"},
    )


from app.modules.scheduling.api.admission_router import router as admission_router
router.include_router(admission_router)

# Solo lectura docente acreditada; no monta Evaluation ni Participation general.
from app.modules.scheduling.api.evaluation_readiness import router as readiness_router
router.include_router(readiness_router)

from app.modules.scheduling.api.technical_results import router as resultados_tecnicos_router
router.include_router(resultados_tecnicos_router)

from app.modules.scheduling.api.academic_results import router as academic_results_router
router.include_router(academic_results_router)

from app.modules.scheduling.api.organization_router import router as organization_router
router.include_router(organization_router)
