"""Rutas REST del módulo de programación académica."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_db, get_session_factory
from app.modules.scheduling.api.schemas import (
    ProgramarSesionRequest,
    CambiarEstadoRequest,
    SesionResponse,
    CrearConvocatoriaRequest,
    ConvocatoriaResponse,
    ConvocatoriaDetalleResponse,
    EspacioAcademicoResponse,
    CrearEspacioAcademicoRequest,
    ValidarIngresoRequest,
    NotificacionResponse,
    NotificarCalificacionRequest,
)
from app.modules.scheduling.application.crear_convocatoria import (
    ErrorConvocatoria,
    crear_convocatoria,
)
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
from app.modules.scheduling.application.notificar_calificacion import (
    notificar_calificacion,
)
from app.modules.scheduling.domain.state import (
    TransicionInvalidaError,
)
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel,
    SesionProgramadaModel,
    ConvocatoriaModel,
    NotificacionModel,
)
from app.modules.scheduling.application.crear_notificacion import (
    crear_notificacion,
)


router = APIRouter(
    prefix="/scheduling",
    tags=["Scheduling"],
)


def obtener_docente_autenticado() -> UUID:
    """
    Pendiente: conectar con el módulo de identidad.

    Por seguridad, se bloquean las operaciones hasta que
    exista una dependencia JWT real y validada.
    """
    raise HTTPException(
        status_code=503,
        detail="Autenticación docente pendiente de integración.",
    )


Docente = Annotated[
    UUID,
    Depends(obtener_docente_autenticado),
]

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
def listar_espacios(db: BaseDatos):
    """Lista todos los espacios académicos disponibles."""
    consulta = select(EspacioAcademicoModel).order_by(EspacioAcademicoModel.nombre)
    return db.scalars(consulta).all()


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
    db: BaseDatos,
    docente_id: UUID | None = None,
    espacio_id: UUID | None = None,
):
    """Lista las sesiones programadas con filtros opcionales."""
    consulta = select(SesionProgramadaModel)
    if docente_id is not None:
        consulta = consulta.where(SesionProgramadaModel.docente_id == docente_id)
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
    db: BaseDatos,
):
    """Obtiene el detalle de una sesión académica."""
    sesion = db.get(SesionProgramadaModel, sesion_id)
    if sesion is None:
        raise HTTPException(
            status_code=404,
            detail="Sesión no encontrada.",
        )
    return sesion


@router.post(
    "/sesiones",
    response_model=SesionResponse,
    status_code=201,
)
def crear_sesion(
    datos: ProgramarSesionRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """Programa una sesión académica (RF-18)."""
    try:
        sesion = programar_sesion(
            db,
            docente_id=docente_id,
            **datos.model_dump(),
        )

        db.commit()
        db.refresh(sesion)
        return sesion

    except ErrorProgramacion as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception:
        db.rollback()
        raise


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
):
    """Convoca a un estudiante a una sesión académica (RF-20)."""
    try:
        sesion = db.get(
            SesionProgramadaModel,
            sesion_id,
            with_for_update=True,
        )

        if sesion is None:
            raise HTTPException(
                status_code=404,
                detail="Sesión no encontrada.",
            )

        if sesion.docente_id != docente_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para convocar estudiantes.",
            )

        # Crear convocatoria y generar código seguro.
        resultado = crear_convocatoria(
            db,
            sesion_id=sesion_id,
            estudiante_id=datos.estudiante_id,
        )

        # Registrar notificación interna para el estudiante.
        crear_notificacion(
            db,
            destinatario_id=datos.estudiante_id,
            convocatoria_id=resultado.convocatoria_id,
            tipo="CONVOCATORIA",
            canal="INTERNA",
            mensaje=(
                "Has sido convocado a una sesión académica. "
                "Consulta los detalles de tu convocatoria "
                "y solicita tu código mediante el canal "
                "institucional autorizado."
            ),
        )

        # Confirmar ambas operaciones juntas.
        db.commit()

        return ConvocatoriaResponse(
            convocatoria_id=resultado.convocatoria_id,
            codigo_acceso=resultado.codigo_acceso,
        )

    except ErrorConvocatoria as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

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
    db: BaseDatos,
):
    """Valida el ingreso de un estudiante mediante código, convocatoria y horario (RF-22)."""
    try:
        return validar_ingreso(
            db,
            convocatoria_id=datos.convocatoria_id,
            estudiante_id=datos.estudiante_id,
            codigo_acceso=datos.codigo_acceso,
            tolerancia_minutos=datos.tolerancia_minutos,
        )
    except ErrorIngreso as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


# =========================================================================
# Notificaciones (RF-21, RF-27)
# =========================================================================

@router.get(
    "/notificaciones",
    response_model=list[NotificacionResponse],
)
def listar_notificaciones(
    destinatario_id: UUID,
    db: BaseDatos,
):
    """Consulta las notificaciones de un usuario/estudiante (RF-21)."""
    consulta = (
        select(NotificacionModel)
        .where(NotificacionModel.destinatario_id == destinatario_id)
        .order_by(NotificacionModel.creada_en.desc())
    )
    return db.scalars(consulta).all()


@router.post(
    "/calificaciones/notificar",
    response_model=NotificacionResponse,
    status_code=201,
)
def notificar_calificacion_participacion(
    datos: NotificarCalificacionRequest,
    docente_id: Docente,
    db: BaseDatos,
):
    """Notifica al estudiante la disponibilidad de su calificación académica (RF-27)."""
    try:
        notificacion = notificar_calificacion(
            db,
            estudiante_id=datos.estudiante_id,
            participacion_id=datos.participacion_id,
        )
        db.commit()
        db.refresh(notificacion)
        return notificacion
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except Exception:
        db.rollback()
        raise
