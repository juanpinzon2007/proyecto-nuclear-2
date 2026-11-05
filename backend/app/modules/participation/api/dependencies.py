from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.api.dependencies import obtener_estudiante_actual as estudiante_identity
from app.modules.identity.api.academic_dependencies import obtener_estudiante_scheduling
from app.modules.identity.domain.entities import ContextoAcceso
from app.modules.participation.application.facade import ParticipacionFacade


class EstudianteAutenticado(BaseModel):
    """Cuenta y UUID académico separados, construidos exclusivamente por el servidor.

    id_estudiante conserva la firma HTTP interna anterior y representa aquí la
    PK INTEGER de usuario, nunca el UUID Scheduling ni id_grupo_estudiante.
    Los campos opcionales preservan los dobles de etapas anteriores; la
    dependencia real siempre proporciona el UUID resuelto, sin generarlo.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    id_estudiante: Annotated[int, Field(strict=True, gt=0)]
    id_estudiante_scheduling: UUID | None = None
    id_convocatoria: str | None = None


def obtener_estudiante_actual(
    usuario: Annotated[ContextoAcceso, Depends(estudiante_identity)],
    academico: Annotated[UUID, Depends(obtener_estudiante_scheduling)],
) -> EstudianteAutenticado:
    # Identity persiste usuario como INTEGER y lo expone como cadena decimal.
    # Esto adapta esa misma cuenta; no convierte UUID ni resuelve una membresía.
    identificador = usuario.id_usuario
    if (not identificador.isascii() or not identificador.isdecimal()
            or not 0 < int(identificador) <= 2_147_483_647
            or str(int(identificador)) != identificador):
        raise HTTPException(503, detail={
            "codigo": "IDENTIDAD_NO_COMPATIBLE",
            "mensaje": "La cuenta autenticada no tiene una referencia compatible.",
        })
    return EstudianteAutenticado(
        id_estudiante=int(identificador), id_estudiante_scheduling=academico,
        id_convocatoria=usuario.id_convocatoria,
    )


def obtener_facade(
    estudiante: Annotated[EstudianteAutenticado, Depends(obtener_estudiante_actual)],
) -> ParticipacionFacade:
    # La identidad se exige incluso antes de componer los futuros adaptadores.
    raise HTTPException(status_code=503, detail={
        "codigo": "INTEGRACION_NO_CONFIGURADA",
        "mensaje": "Los adaptadores reales de Participación todavía no están configurados.",
    })


def obtener_consulta_escenario(
    usuario: Annotated[ContextoAcceso, Depends(estudiante_identity)],
):
    raise HTTPException(503, detail={"codigo": "INTEGRACION_NO_CONFIGURADA",
        "mensaje": "La consulta de escenario no está configurada."})


def crear_dependencia_escenario_8b(*, crear_sesion, fechas, reloj):
    """Solo composición explícita del servidor; no registra rutas en main."""
    from app.modules.participation.infrastructure.current_scenario import ConsultaEscenarioActualSQLAlchemy

    def dependencia(usuario: Annotated[ContextoAcceso, Depends(estudiante_identity)]):
        return ConsultaEscenarioActualSQLAlchemy(usuario=usuario, crear_sesion=crear_sesion,
            fechas=fechas, reloj=reloj)
    return dependencia


def crear_dependencia_facade_8b(*, crear_sesion, fechas, reloj):
    """Composición HTTP explícita por el servidor; NO se instala en main.py.

    Solo operaciones sobre un intento existente. Identity verifica JWT/rol y
    el agregado revalida titularidad dentro de la UoW. No acepta políticas,
    fechas, estudiante ni Session enviados desde el cliente. La zona histórica
    de timestamps se configura explícitamente mediante fechas, sin inferirla.
    """
    from app.modules.participation.infrastructure.composition import crear_facade_8b

    def dependencia(request: Request, usuario: Annotated[ContextoAcceso, Depends(estudiante_identity)]) -> ParticipacionFacade:
        identificador = request.path_params.get("attempt_id")
        if identificador is None:
            raise HTTPException(503, detail={"codigo": "INICIO_NO_HABILITADO",
                "mensaje": "La autorización de inicio todavía no está configurada."})
        try:
            id_intento = int(identificador)
        except (TypeError, ValueError):
            raise HTTPException(422, detail={"codigo": "SOLICITUD_INVALIDA", "mensaje": "Intento inválido."}) from None
        if not 0 < id_intento <= 2147483647:
            raise HTTPException(422, detail={"codigo": "SOLICITUD_INVALIDA", "mensaje": "Intento inválido."})
        return crear_facade_8b(usuario=usuario, id_intento=id_intento, reloj=reloj,
                              fechas=fechas, crear_sesion=crear_sesion)

    return dependencia


def crear_dependencia_vinculacion_8b(*, crear_sesion, fechas, reloj,
                                    politica_ingreso=None, politica_vinculacion=None,
                                    politica_inicio=None):
    """Composición opt-in del servidor, sin políticas académicas por defecto.

    Instancia por solicitud. No reutiliza autorizaciones/sesiones de una consulta
    previa; el servicio existente revalida y bloquea dentro de su propia UoW.
    Ninguna política de laboratorio se importa o selecciona desde esta capa.
    """
    from app.modules.participation.infrastructure.provision import ServicioVinculacionSQLAlchemy

    def dependencia(usuario: Annotated[ContextoAcceso, Depends(estudiante_identity)]):
        return ServicioVinculacionSQLAlchemy(usuario=usuario, crear_sesion=crear_sesion,
            fechas=fechas, reloj=reloj, politica_ingreso=politica_ingreso,
            politica_vinculacion=politica_vinculacion, politica_inicio=politica_inicio)

    return dependencia
