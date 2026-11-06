"""Validación de ingreso de estudiantes a sesiones académicas."""

from app.modules.scheduling.domain.access_codes import coincide_codigo

from uuid import UUID

from sqlalchemy.orm import Session
from app.modules.scheduling.domain.ingress_policy import (
    PoliticaIngreso, PoliticaTemporalNoDisponible, RelojIngreso, VentanaIngreso, fecha_utc,
)

from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    SesionProgramadaModel,
)


class ErrorIngreso(ValueError):
    """El estudiante no cumple las condiciones de acceso."""
    pass


def validar_ingreso(
    db: Session,
    *,
    convocatoria_id: UUID,
    estudiante_id: UUID,
    codigo_acceso: str,
    politica: PoliticaIngreso,
    reloj: RelojIngreso,
    admision=None,
) -> SesionProgramadaModel:
    """Verifica código, convocatoria, estado y horario."""

    # Validar la convocatoria.
    convocatoria = db.get(
        ConvocatoriaModel,
        convocatoria_id,
    )

    if (
        convocatoria is None
        or convocatoria.estado != "ACTIVA"
        or convocatoria.estudiante_id != estudiante_id
    ):
        raise ErrorIngreso("Acceso no autorizado.")

    # Verificar el código generado durante la convocatoria.
    if not coincide_codigo(codigo_acceso, convocatoria.codigo_hash):
        raise ErrorIngreso("Acceso no autorizado.")

    # Comprobar la sesión académica.
    sesion = db.get(
        SesionProgramadaModel,
        convocatoria.sesion_id,
    )

    if sesion is None:
        raise ErrorIngreso("La sesión no existe.")

    # Solo la transición efectiva de habilitación abre esta condición. Alcanzar
    # la fecha programada, o una política inyectada, nunca sustituye EN_CURSO.
    if sesion.estado != "EN_CURSO":
        raise ErrorIngreso("La sesión no está en curso.")

    inicio, fin = fecha_utc(sesion.fecha_inicio), fecha_utc(sesion.fecha_fin)
    if fin <= inicio:
        raise PoliticaTemporalNoDisponible()
    if admision is not None:
        admision.autorizar(convocatoria_id=convocatoria.id,estudiante_id=estudiante_id,
            sesion_id=sesion.id,version_id=sesion.version_caso_id)
        # Límites exteriores de programación conservados, sin margen adicional.
        ventana = VentanaIngreso(inicio,fin,True,False)
    else:
        ventana = politica.obtener_ventana(id_sesion=sesion.id, inicio=inicio, fin=fin)
    if (not isinstance(ventana, VentanaIngreso) or ventana.apertura < inicio
            or ventana.cierre > fin):
        raise PoliticaTemporalNoDisponible()
    # Una sola lectura, después de consultar los datos y la política del servidor.
    if not ventana.contiene(reloj.ahora()):
        raise ErrorIngreso("El ingreso no está dentro de la ventana autorizada.")

    return sesion
