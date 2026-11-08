"""Puertos que necesita Identity; no son adaptadores integrados de otros módulos.

El DBML confirma el mapeo de acceso con un rol por usuario y permisos por rol.
Las firmas académicas y su adaptación transaccional aún requieren acuerdo.
"""

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.identity.domain.entities import (
    AccesoConvocatoria, AutorizacionRepeticion, AutorizacionesDocente,
    CondicionesRepeticion, ContextoAcceso, DatosAltaDocente, DetalleParticipacion, FeedbackDocente,
    FilaReporte, ResumenCaso, ResumenParticipacion,
)


class RepositorioUsuarios(Protocol):
    def obtener(self, id_usuario: str) -> ContextoAcceso | None: ...
    def permisos_existentes(self, permisos: frozenset[str]) -> bool: ...
    def crear_docente(self, correo: str, autorizaciones: AutorizacionesDocente,
                      *, datos: DatosAltaDocente | None = None) -> ContextoAcceso: ...
    def asignar_autorizaciones(self, id_docente: str, autorizaciones: AutorizacionesDocente) -> ContextoAcceso: ...


class ConsultaCuentaPorCorreo(Protocol):
    def obtener_por_correo(self, correo: str) -> ContextoAcceso | None:
        """Cuenta existente única tras normalización; ambigüedad falla cerrada."""
        ...


class ValidadorCredencialesPersonal(Protocol):
    def validar(self, correo: str, clave: str) -> ContextoAcceso | None:
        """Verifica hash privado y retorna cuenta/roles actuales, nunca el hash.

        Ausencia o contraseña inválida no distingue públicamente la cuenta.
        Errores de infraestructura fallan cerrados; no generan identidades.
        """
        ...


class ValidadorConvocatoria(Protocol):
    def validar(self, correo: str, codigo: str) -> AccesoConvocatoria | None:
        """Valida la pareja completa contra la convocatoria vigente y autorizada.

        Debe comprobar pertenencia/retiro y no identificar solo por correo ni
        generar códigos. Ninguna excepción o diagnóstico debe revelar el código.
        """
        ...


class ValidadorContextoConvocatoria(Protocol):
    def validar_contexto(self, *, id_usuario: str, contexto: str | None, solicitada: UUID) -> None:
        """Exige convocatoria del token, titularidad y vigencia actuales; no horario."""
        ...


class TokensAcceso(Protocol):
    def emitir(self, id_usuario: str, id_convocatoria: str | None = None) -> str: ...


class ConsultaAmbitoAcademico(Protocol):
    def puede_consultar_participacion(self, id_docente: str, id_participacion: str) -> bool: ...
    def puede_consultar_sesion(self, id_docente: str, id_sesion: str) -> bool: ...


class LecturaSeguimiento(Protocol):
    def listar_participaciones(self, id_docente: str, id_caso: str) -> tuple[ResumenParticipacion, ...]: ...
    def listar_casos_realizados(self, id_docente: str) -> tuple[ResumenCaso, ...]: ...
    def consultar_participacion(self, id_docente: str, id_participacion: str) -> DetalleParticipacion:
        """Solo datos visibles en el ámbito del docente y de casos realizados."""
        ...


class LecturaReportes(Protocol):
    def obtener_filas(self, id_docente: str, id_sesion: str) -> tuple[FilaReporte, ...]:
        """Incluye convocados sin resultado mediante LEFT JOIN público acordado.

        No calcula ni consolida notas. Estados, ausencia confirmada y nota deben
        proceder de Participation/Scheduling; no inferir ausencia de filas vacías.
        """
        ...


class ConsultaEscrituraAcademica(ConsultaAmbitoAcademico, Protocol):
    def condiciones_repeticion(self, id_docente: str, id_sesion: str, id_estudiante: str) -> CondicionesRepeticion:
        """Comprobar bajo la misma transacción/bloqueo que guarda la concesión."""
        ...


class RepositorioAutorizaciones(Protocol):
    def guardar(self, autorizacion: AutorizacionRepeticion) -> int | AutorizacionRepeticion | None:
        """Sin commit propio. Devuelve ID nativo o concesión persistida (fecha original en replay)."""
        ...


class RepositorioFeedback(Protocol):
    def agregar(self, feedback: FeedbackDocente) -> None: ...


class UnidadTrabajoIdentity(Protocol):
    usuarios: RepositorioUsuarios
    autorizaciones: RepositorioAutorizaciones
    feedback: RepositorioFeedback
    academia: ConsultaEscrituraAcademica

    def __enter__(self) -> Self: ...
    def __exit__(self, tipo: type[BaseException] | None, error: BaseException | None, traceback: TracebackType | None) -> None:
        """Rollback y cierre al salir sin commit o ante un fallo."""
        ...
    def commit(self) -> None: ...


FabricaUnidadTrabajo = Callable[[], UnidadTrabajoIdentity]


class IServicioSeguimiento(Protocol):
    def listar_participaciones(self, contexto: ContextoAcceso, id_caso: str) -> tuple[ResumenParticipacion, ...]: ...
    def listar_casos_realizados(self, contexto: ContextoAcceso) -> tuple[ResumenCaso, ...]: ...
    def consultar_participacion(self, contexto: ContextoAcceso, id_participacion: str) -> DetalleParticipacion: ...
    def descargar_reporte(self, contexto: ContextoAcceso, id_sesion: str, *, formato=None, filtros=None): ...
    def registrar_feedback(self, contexto: ContextoAcceso, id_participacion: str, texto: str) -> FeedbackDocente: ...


class IServicioExcepciones(Protocol):
    def autorizar_repeticion(self, contexto: ContextoAcceso, id_sesion: str, id_estudiante: str) -> AutorizacionRepeticion: ...


class IServicioAdministracion(Protocol):
    def crear_docente(self, contexto: ContextoAcceso, correo: str, autorizaciones: AutorizacionesDocente,
                      *, nombre: str | None = None, clave: str | None = None) -> ContextoAcceso: ...
    def asignar_autorizaciones(self, contexto: ContextoAcceso, id_docente: str, autorizaciones: AutorizacionesDocente) -> ContextoAcceso: ...
