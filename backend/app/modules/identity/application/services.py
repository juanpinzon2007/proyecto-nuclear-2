import csv
from collections.abc import Callable
from datetime import UTC, datetime
from io import StringIO

from app.modules.identity.application.ports import (
    FabricaUnidadTrabajo, LecturaReportes, LecturaSeguimiento,
)
from app.modules.identity.application.authorization import ServicioAutorizacion
from app.modules.identity.domain.entities import (
    AutorizacionRepeticion, AutorizacionesDocente, ContextoAcceso,
    DatosAltaDocente, DetalleParticipacion, FeedbackDocente, ResumenCaso, Rol, normalizar_correo, validar_id,
)
from app.modules.identity.domain.errors import AccesoDenegado, ConflictoIdentidad, IntegracionPendiente, NoAutenticado, RecursoNoDisponible, ReglaIdentidadInvalida


class ServicioReportes:
    def __init__(self, lecturas: LecturaReportes) -> None:
        self.lecturas = lecturas

    def descargar(self, contexto: ContextoAcceso, id_sesion: str) -> str:
        """Exporta resultados oficiales; la consulta LEFT JOIN sigue pendiente de ER."""
        validar_id(id_sesion)
        filas = tuple(self.lecturas.obtener_filas(contexto.id_usuario, id_sesion))
        estudiantes, participaciones = set(), set()
        for fila in filas:
            # No consolidar múltiples intentos ni elegir una fila arbitraria.
            if (fila.id_estudiante in estudiantes or
                    (fila.id_participacion is not None and fila.id_participacion in participaciones)):
                raise IntegracionPendiente()
            if fila.nota is not None and not 0 <= fila.nota <= 100:
                raise IntegracionPendiente()
            estudiantes.add(fila.id_estudiante)
            if fila.id_participacion is not None:
                participaciones.add(fila.id_participacion)
        salida = StringIO(newline="")
        escritor = csv.writer(salida)
        escritor.writerow(("id_estudiante", "id_participacion", "estado", "nota"))
        for fila in filas:
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
                 feedback: ServicioFeedbackDocente, *, reportes_oficiales=None) -> None:
        self.reportes_oficiales = reportes_oficiales
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

    def descargar_reporte(self, contexto: ContextoAcceso, id_sesion: str, *, formato=None, filtros=None):
        if formato is not None:
            if self.reportes_oficiales is None:
                raise IntegracionPendiente()
            return self.reportes_oficiales().descargar(id_sesion, formato, filtros)
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
            permiso = trabajo.autorizaciones.guardar(autorizacion)
            if isinstance(permiso,AutorizacionRepeticion):
                if (permiso.id_sesion,permiso.id_estudiante,permiso.id_docente_autorizador)!=(id_sesion,id_estudiante,contexto.id_usuario) or type(permiso.id_permiso_extra) is not int or permiso.id_permiso_extra<=0:
                    raise IntegracionPendiente()
                autorizacion=permiso
            elif permiso is not None:
                from dataclasses import replace
                if type(permiso) is not int or permiso <= 0:raise IntegracionPendiente()
                autorizacion = replace(autorizacion,id_permiso_extra=permiso)
            trabajo.commit()
        return autorizacion


class ServicioAdministracionUsuarios:
    def __init__(self, uow: FabricaUnidadTrabajo, hashear_clave: Callable[[str], str] | None = None) -> None:
        self.uow = uow
        self.hashear_clave = hashear_clave

    @staticmethod
    def _exigir_administrador(trabajo, contexto: ContextoAcceso) -> None:
        leer = getattr(trabajo.usuarios, 'obtener_para_escritura', None)
        if not callable(leer):
            raise IntegracionPendiente()
        actual = leer(contexto.id_usuario)
        if actual is None:
            raise NoAutenticado()
        if not isinstance(actual, ContextoAcceso) or actual.id_usuario != contexto.id_usuario:
            raise IntegracionPendiente()
        # Reutilizar exactamente la regla del Proxy, con identidad SQL vigente.
        ServicioAutorizacion.exigir_rol(actual, Rol.ADMINISTRADOR)

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
            self._exigir_administrador(trabajo, contexto)
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
            self._exigir_administrador(trabajo, contexto)
            docente = trabajo.usuarios.obtener(id_docente)
            if docente is None or Rol.DOCENTE not in docente.roles:
                raise RecursoNoDisponible()
            if trabajo.usuarios.permisos_existentes(autorizaciones.permisos) is not True:
                raise ReglaIdentidadInvalida()
            docente = trabajo.usuarios.asignar_autorizaciones(id_docente, autorizaciones)
            trabajo.commit()
        return docente

    def configurar_permisos_docentes(self, contexto: ContextoAcceso, permisos: frozenset[str]):
        with self.uow() as trabajo:
            self._exigir_administrador(trabajo, contexto)
            if trabajo.usuarios.permisos_existentes(permisos) is not True:
                raise ReglaIdentidadInvalida()
            perfil = trabajo.usuarios.configurar_permisos_docentes(permisos)
            trabajo.commit()
        return perfil
