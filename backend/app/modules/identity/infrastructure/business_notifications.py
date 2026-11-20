"""Notificaciones transaccionales de negocio por correo electrónico (sin romper contratos existentes)."""

from collections.abc import Callable
from decimal import Decimal
import logging
import os
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.cases.domain.entities.caso import Rubrica
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.onboarding import enviar_correo_directo
from app.modules.scheduling.infrastructure.mail_delivery import configuracion_correo

logger = logging.getLogger(__name__)
_SUFIJOS_PRUEBA_RESERVADOS = (".test", ".invalid", ".example", ".localhost")
_ENVIO_DIRECTO_REAL = enviar_correo_directo


def _es_correo_reservado_prueba(correo: str) -> bool:
    return correo.strip().casefold().endswith(_SUFIJOS_PRUEBA_RESERVADOS)


def obtener_contacto_por_identidad(
    db: Session,
    *,
    sistema: str,
    id_academico: UUID,
) -> tuple[str, str] | None:
    """Resuelve `(correo, nombre)` del titular asociado a una identidad académica."""
    try:
        with db.begin_nested():
            fila = db.execute(
                select(UsuarioORM.correo, UsuarioORM.nombre)
                .join(IdentidadAcademicaORM, IdentidadAcademicaORM.id_usuario == UsuarioORM.id_usuario)
                .where(
                    IdentidadAcademicaORM.sistema == sistema,
                    IdentidadAcademicaORM.id_academico == id_academico,
                )
                .limit(1)
            ).first()
            return (fila.correo, fila.nombre) if fila is not None else None
    except SQLAlchemyError:
        return None


def rubrica_cambio(antes: Rubrica | None, despues: Rubrica | None) -> bool:
    """Indica si se asignó una rúbrica nueva o cambió su definición."""
    if despues is None:
        return False
    if antes is None:
        return True

    def _firma(r: Rubrica):
        return (
            r.nombre.strip(),
            r.version_regla.strip(),
            tuple(
                sorted(
                    (c.nombre.strip(), Decimal(c.peso), len(c.niveles))
                    for c in r.criterios
                )
            ),
        )

    return _firma(antes) != _firma(despues)


def despachar_correo_seguro(
    *,
    correo: str,
    asunto: str,
    generar_cuerpo: Callable[[str], str],
    background_tasks: BackgroundTasks | None = None,
    notificador: Callable[..., None] | None = None,
) -> None:
    """Programa o ejecuta el envío de correo sin interrumpir transacciones ya confirmadas."""
    if notificador is not None:
        if background_tasks is not None:
            background_tasks.add_task(notificador, correo=correo, asunto=asunto, generar_cuerpo=generar_cuerpo)
        else:
            notificador(correo=correo, asunto=asunto, generar_cuerpo=generar_cuerpo)
        return

    if _es_correo_reservado_prueba(correo):
        return
    if "PYTEST_CURRENT_TEST" in os.environ and enviar_correo_directo is _ENVIO_DIRECTO_REAL:
        return
    if configuracion_correo() is None:
        return

    def _enviar() -> None:
        try:
            enviar_correo_directo(destinatario=correo, asunto=asunto, generar_cuerpo=generar_cuerpo)
        except Exception as error:
            logger.warning("Aviso de negocio no enviado a %s (%s)", correo, type(error).__name__)

    if background_tasks is not None:
        background_tasks.add_task(_enviar)
    else:
        _enviar()


def notificar_registro_usuario(
    *,
    correo: str,
    nombre: str,
    rol: str,
    background_tasks: BackgroundTasks | None = None,
    notificador: Callable[..., None] | None = None,
) -> None:
    rol_norm = rol.strip().upper()
    if rol_norm == "ESTUDIANTE":
        asunto = "Cuenta estudiantil registrada - SPS"
        detalle = (
            f"Tu cuenta estudiantil ({correo}) fue registrada en el Simulador de Psicología Social (SPS).\n"
            "Ingresa con tu correo y contraseña inicial; únicamente en tu primer inicio de sesión recibirás un código de verificación por este correo."
        )
    else:
        asunto = f"Cuenta {rol_norm.lower()} registrada - SPS"
        detalle = (
            f"Tu cuenta con rol {rol_norm} ({correo}) fue registrada correctamente en el Simulador de Psicología Social (SPS)."
        )

    despachar_correo_seguro(
        correo=correo,
        asunto=asunto,
        generar_cuerpo=lambda url: f"Hola {nombre},\n\n{detalle}\n\nPlataforma: {url}",
        background_tasks=background_tasks,
        notificador=notificador,
    )


def notificar_matricula_grupo(
    *,
    correo: str,
    nombre: str,
    grupo_nombre: str,
    grupo_periodo: str,
    docente_nombre: str | None = None,
    background_tasks: BackgroundTasks | None = None,
    notificador: Callable[..., None] | None = None,
) -> None:
    autor = f" por {docente_nombre}" if docente_nombre else ""
    despachar_correo_seguro(
        correo=correo,
        asunto=f"Registro en grupo académico '{grupo_nombre}' - SPS",
        generar_cuerpo=lambda url: (
            f"Hola {nombre},\n\n"
            f"Fuiste registrado/matriculado en el grupo académico \"{grupo_nombre}\" (periodo {grupo_periodo}){autor}.\n"
            "Cuando el docente programe sesiones y convoque casos para tu grupo recibirás la notificación con los detalles de ingreso.\n\n"
            f"Plataforma: {url}"
        ),
        background_tasks=background_tasks,
        notificador=notificador,
    )


def notificar_creacion_caso(
    *,
    correo: str,
    docente_nombre: str,
    caso_nombre: str,
    total_escenarios: int,
    rubrica_nombre: str | None = None,
    total_criterios: int = 0,
    background_tasks: BackgroundTasks | None = None,
    notificador: Callable[..., None] | None = None,
) -> None:
    if rubrica_nombre:
        bloque_rubrica = (
            f"También quedó asignada la rúbrica \"{rubrica_nombre}\" ({total_criterios} criterio(s)).\n"
            "Cuando configures su flujo de escenarios podrás publicarlo."
        )
    else:
        bloque_rubrica = (
            "El caso se guardó en estado BORRADOR sin rúbrica asignada aún.\n"
            "Recuerda asignarle una rúbrica y configurar su grafo antes de publicarlo."
        )
    despachar_correo_seguro(
        correo=correo,
        asunto=f"Caso creado en SPS: {caso_nombre}",
        generar_cuerpo=lambda url: (
            f"Hola {docente_nombre},\n\n"
            f"Se creó correctamente el caso \"{caso_nombre}\" con {total_escenarios} escenario(s) en estado BORRADOR.\n"
            f"{bloque_rubrica}\n\n"
            f"Plataforma: {url}"
        ),
        background_tasks=background_tasks,
        notificador=notificador,
    )


def notificar_asignacion_rubrica_caso(
    *,
    correo: str,
    docente_nombre: str,
    caso_nombre: str,
    numero_version: int,
    rubrica_nombre: str,
    version_regla: str,
    total_criterios: int,
    background_tasks: BackgroundTasks | None = None,
    notificador: Callable[..., None] | None = None,
) -> None:
    despachar_correo_seguro(
        correo=correo,
        asunto=f"Rúbrica asignada al caso '{caso_nombre}' - SPS",
        generar_cuerpo=lambda url: (
            f"Hola {docente_nombre},\n\n"
            f"Se asignó/actualizó correctamente la rúbrica \"{rubrica_nombre}\" "
            f"(regla {version_regla}, {total_criterios} criterio(s)) al caso \"{caso_nombre}\" (v{numero_version}).\n"
            "El borrador está listo para revisar su grafo y publicarlo cuando lo consideres.\n\n"
            f"Plataforma: {url}"
        ),
        background_tasks=background_tasks,
        notificador=notificador,
    )


def notificar_publicacion_caso(
    *,
    correo: str,
    docente_nombre: str,
    caso_nombre: str,
    numero_version: int,
    rubrica_nombre: str | None = None,
    background_tasks: BackgroundTasks | None = None,
    notificador: Callable[..., None] | None = None,
) -> None:
    info_rubrica = f" junto con la rúbrica \"{rubrica_nombre}\"" if rubrica_nombre else ""
    despachar_correo_seguro(
        correo=correo,
        asunto=f"Caso publicado en SPS: {caso_nombre} (v{numero_version})",
        generar_cuerpo=lambda url: (
            f"Hola {docente_nombre},\n\n"
            f"Tu caso \"{caso_nombre}\" (v{numero_version}){info_rubrica} ha sido PUBLICADO correctamente.\n"
            "Ya se encuentra disponible para programar sesiones académicas y convocar estudiantes.\n\n"
            f"Plataforma: {url}"
        ),
        background_tasks=background_tasks,
        notificador=notificador,
    )
