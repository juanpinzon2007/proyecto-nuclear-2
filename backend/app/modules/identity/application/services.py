import csv
from collections.abc import Callable
from datetime import UTC, datetime
from io import StringIO

from app.modules.identity.application.ports import (
    FabricaUnidadTrabajo, LecturaReportes, LecturaSeguimiento,
)
from app.modules.identity.domain.entities import (
    AutorizacionRepeticion, AutorizacionesDocente, ContextoAcceso,
    DatosAltaDocente, DetalleParticipacion, FeedbackDocente, ResumenCaso, Rol, normalizar_correo, validar_id,
)
from app.modules.identity.domain.errors import AccesoDenegado, ConflictoIdentidad, IntegracionPendiente, RecursoNoDisponible, ReglaIdentidadInvalida


class ServicioReportes:
    def __init__(self, lecturas: LecturaReportes) -> None:
        self.lecturas = lecturas

    def descargar(self, contexto: ContextoAcceso, id_sesion: str) -> str:
        """Exporta resultados oficiales; la consulta LEFT JOIN sigue pendiente de ER."""
        validar_id(id_sesion)
        salida = StringIO(newline="")
        escritor = csv.writer(salida)
        escritor.writerow(("id_estudiante", "id_participacion", "estado", "nota"))
        for fila in self.lecturas.obtener_filas(contexto.id_usuario, id_sesion):
            escritor.writerow((
                self._celda(fila.id_estudiante), self._celda(fila.id_participacion or ""),
                fila.estado.value, "" if fila.nota is None else format(fila.nota, "f"),
            ))
        return salida.getvalue()

    @staticmethod
    def _celda(valor: str) -> str:
        # Evitar fórmulas al abrir un identificador externo como hoja de cálculo.
        if valor.lstrip().startswith(("=", "+", "-", "@")) or valor.startswith(("\t", "\r", "\n")):
            return "'" + valor
        return valor


class ServicioFeedbackDocente:
    def __init__(self, uow: FabricaUnidadTrabajo) -> None:
        self.uow = uow

    def registrar(self, contexto: ContextoAcceso, id_participacion: str, texto: str) -> FeedbackDocente:
        validar_id(id_participacion)
        feedback = FeedbackDocente(id_participacion, contexto.id_usuario, texto.strip(), datetime.now(UTC))
        with self.uow() as trabajo:
            # Revalidar el ámbito dentro de la transacción de escritura.
            if trabajo.academia.puede_consultar_participacion(contexto.id_usuario, id_participacion) is not True:
                raise AccesoDenegado()
            trabajo.feedback.agregar(feedback)
            trabajo.commit()
        return feedback


class ServicioSeguimiento:
    def __init__(self, lecturas: LecturaSeguimiento, reportes: ServicioReportes | None,
                 feedback: ServicioFeedbackDocente) -> None:
        self.lecturas = lecturas
        self.reportes = reportes
        self.feedback = feedback

    def listar_casos_realizados(self, contexto: ContextoAcceso) -> tuple[ResumenCaso, ...]:
        return self.lecturas.listar_casos_realizados(contexto.id_usuario)

    def listar_participaciones(self, contexto: ContextoAcceso, id_caso: str):
        validar_id(id_caso)
        return self.lecturas.listar_participaciones(contexto.id_usuario, id_caso)

    def consultar_participacion(self, contexto: ContextoAcceso, id_participacion: str) -> DetalleParticipacion:
        validar_id(id_participacion)
        return self.lecturas.consultar_participacion(contexto.id_usuario, id_participacion)

    def descargar_reporte(self, contexto: ContextoAcceso, id_sesion: str) -> str:
        if self.reportes is None:
            raise IntegracionPendiente()
        return self.reportes.descargar(contexto, id_sesion)

    def registrar_feedback(self, contexto: ContextoAcceso, id_participacion: str, texto: str) -> FeedbackDocente:
        return self.feedback.registrar(contexto, id_participacion, texto)


class ServicioExcepciones:
    def __init__(self, uow: FabricaUnidadTrabajo) -> None:
        self.uow = uow

    def autorizar_repeticion(self, contexto: ContextoAcceso, id_sesion: str,
                            id_estudiante: str) -> AutorizacionRepeticion:
        validar_id(id_sesion)
        validar_id(id_estudiante)
        with self.uow() as trabajo:
            condiciones = trabajo.academia.condiciones_repeticion(contexto.id_usuario, id_sesion, id_estudiante)
            if condiciones.es_docente_creador is not True:
                raise AccesoDenegado()
            if condiciones.sesion_finalizada or not condiciones.existe_participacion:
                raise ConflictoIdentidad()
            autorizacion = AutorizacionRepeticion(
                id_sesion, id_estudiante, contexto.id_usuario, datetime.now(UTC),
            )
            trabajo.autorizaciones.guardar(autorizacion)
            trabajo.commit()
        return autorizacion


class ServicioAdministracionUsuarios:
    def __init__(self, uow: FabricaUnidadTrabajo, hashear_clave: Callable[[str], str] | None = None) -> None:
        self.uow = uow
        self.hashear_clave = hashear_clave

    def crear_docente(self, contexto: ContextoAcceso, correo: str,
                      autorizaciones: AutorizacionesDocente, *, nombre: str | None = None,
                      clave: str | None = None) -> ContextoAcceso:
        correo = normalizar_correo(correo)
        datos = None
        if nombre is not None or clave is not None:
            if nombre is None or clave is None or not nombre.strip() or len(nombre) > 120 or not clave:
                raise ReglaIdentidadInvalida()
            if self.hashear_clave is None:
                raise IntegracionPendiente()
            datos = DatosAltaDocente(nombre.strip(), self.hashear_clave(clave))
        with self.uow() as trabajo:
            if trabajo.usuarios.permisos_existentes(autorizaciones.permisos) is not True:
                raise ReglaIdentidadInvalida()
            if datos is None:
                docente = trabajo.usuarios.crear_docente(correo, autorizaciones)
            else:
                docente = trabajo.usuarios.crear_docente(correo, autorizaciones, datos=datos)
            trabajo.commit()
        return docente

    def asignar_autorizaciones(self, contexto: ContextoAcceso, id_docente: str,
                              autorizaciones: AutorizacionesDocente) -> ContextoAcceso:
        validar_id(id_docente)
        with self.uow() as trabajo:
            docente = trabajo.usuarios.obtener(id_docente)
            if docente is None or Rol.DOCENTE not in docente.roles:
                raise RecursoNoDisponible()
            if trabajo.usuarios.permisos_existentes(autorizaciones.permisos) is not True:
                raise ReglaIdentidadInvalida()
            docente = trabajo.usuarios.asignar_autorizaciones(id_docente, autorizaciones)
            trabajo.commit()
        return docente
