"""Ámbito HTTP de consentimiento: solo composición explícita, sin ingreso/start.

No sustituye la aceptación ni su fuente. Posee la transacción de esta operación
y revalida las relaciones antes de delegar en el servicio de consentimiento.
"""
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.modules.identity.application.academic_identity import ResolverIdentidadAcademica
from app.modules.identity.infrastructure.academic_identity_repository import RepositorioIdentidadAcademicaSQLAlchemy
from app.modules.identity.infrastructure.scheduling_access import ValidadorConvocatoriaScheduling
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, ConflictoIdentidad, IntegracionPendiente
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.academic_base_models import GrupoEstudianteORM as M, ConsentimientoORM as C
from app.modules.identity.infrastructure.consent import ServicioConsentimientoSQLAlchemy, exigir_aceptacion
from app.modules.identity.infrastructure.consent_repository import FuenteConsentimientoSQLAlchemy
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.scheduling.infrastructure.models import ConvocatoriaModel, SesionProgramadaModel
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.domain.ingress_policy import fecha_utc, PoliticaTemporalNoDisponible
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente


class ConsentimientoEstudiantilSQLAlchemy:
    def __init__(self, *, usuario, crear_sesion, fechas, reloj, politica_aprobacion=None):
        self.usuario, self.crear_sesion, self.fechas, self.reloj = usuario, crear_sesion, fechas, reloj
        self.politica_aprobacion = politica_aprobacion

    def _ambito(self, db, convocatoria_id, id_asignacion, escribir):
        if self.usuario is None or type(id_asignacion) is not int or id_asignacion <= 0:
            raise AccesoDenegado()
        cuenta = id_entero(self.usuario.id_usuario)
        # Mismo orden de locks que provisión: cuenta/rol/mapping/matrícula/C/S/A.
        u = db.get(UsuarioORM, cuenta, with_for_update=True if escribir else {'read': True}, populate_existing=True)
        if u is None:
            raise AccesoDenegado()
        db.get(RolORM, u.id_rol, with_for_update={'read': True}, populate_existing=True)
        actual = RepositorioUsuariosSQLAlchemy(db).obtener(str(cuenta))
        if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
            raise AccesoDenegado()
        db.scalars(select(IdentidadAcademicaORM).where(IdentidadAcademicaORM.id_usuario == cuenta)
                   .with_for_update(read=True)).all()
        matriculas = db.scalars(select(M).join(AsignacionCasoModel, AsignacionCasoModel.id_grupo == M.id_grupo)
            .where(AsignacionCasoModel.id_asignacion == id_asignacion, M.id_estudiante == cuenta)
            .with_for_update(read=True, of=M).execution_options(populate_existing=True)).all()
        if len(matriculas) != 1 or not matriculas[0].activo:
            raise AccesoDenegado()
        c = db.get(ConvocatoriaModel, convocatoria_id, with_for_update={'read': True}, populate_existing=True)
        if c is None:
            raise AccesoDenegado()
        s = db.get(SesionProgramadaModel, c.sesion_id, with_for_update={'read': True}, populate_existing=True)
        a = db.get(AsignacionCasoModel, id_asignacion,
            with_for_update={'read': True}, populate_existing=True)
        if s is None or a is None or a.sesion_programada_id != s.id or a.version_caso_id != s.version_caso_id:
            raise AccesoDenegado()
        ValidadorConvocatoriaScheduling(db, RepositorioUsuariosSQLAlchemy(db),
            ResolverIdentidadAcademica(RepositorioIdentidadAcademicaSQLAlchemy(db))).validar_contexto(id_usuario=str(cuenta),
            contexto=self.usuario.id_convocatoria, solicitada=convocatoria_id)
        # Comprobar correspondencia real INTEGER/UUID, nunca convertir identidades.
        caso = db.scalar(select(CasoModel).where(CasoModel.id_caso == a.id_caso))
        v = db.get(VersionCasoModel, s.version_caso_id)
        if caso is None or v is None or v.caso_id != caso.id:
            raise AccesoDenegado()
        return cuenta

    def ejecutar(self, *, convocatoria_id, id_asignacion, operacion, solicitud=None):
        escribir = operacion == 'aceptar'
        try:
            with self.crear_sesion() as db, db.no_autoflush:
                cuenta = self._ambito(db, convocatoria_id, id_asignacion, escribir)
                ahora = fecha_utc(self.reloj.ahora())
                fuente = FuenteConsentimientoSQLAlchemy(db, politica_aprobacion=self.politica_aprobacion)
                documento = fuente.vigente(id_asignacion=id_asignacion, ahora=ahora)
                if operacion == 'documento':
                    return dict(id_version_documento=documento.id_version_documento,
                        referencia=documento.referencia, documento_id=documento.documento_id,
                        version=documento.version, texto=documento.texto, huella=documento.huella)
                servicio = ServicioConsentimientoSQLAlchemy(db, fuente=fuente, fechas=self.fechas, reloj=self.reloj)
                if escribir:
                    if (solicitud.id_version_documento != documento.id_version_documento
                        or solicitud.referencia != documento.referencia or solicitud.huella != documento.huella):
                        raise ConflictoIdentidad()
                    pk = servicio.aceptar(usuario=self.usuario, id_asignacion=id_asignacion,
                        referencia_presentada=solicitud.referencia, huella_presentada=solicitud.huella, acepta=solicitud.acepta)
                    fila = db.get(C, pk)
                else:
                    try:
                        fila = exigir_aceptacion(db, id_estudiante=cuenta, id_asignacion=id_asignacion,
                            ahora=ahora, fechas=self.fechas, fuente=fuente)
                    except AccesoDenegado:
                        fila = None
                respuesta = dict(aceptado=fila is not None, id_version_documento=documento.id_version_documento,
                    referencia=documento.referencia, huella=documento.huella,
                    id_consentimiento=fila.id_consentimiento if fila else None,
                    fecha_aceptacion=self.fechas.desde_db(fila.fecha_aceptacion) if fila else None)
                if escribir:
                    db.commit()
                return respuesta
        except (SQLAlchemyError, PoliticaTemporalNoDisponible, MapeoPersistenciaPendiente):
            raise IntegracionPendiente() from None
