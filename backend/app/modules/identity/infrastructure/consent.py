"""Mecánica interna SQL. Sin fuente oficial compuesta ni rutas de aceptación.

La tabla conserva la referencia histórica externa en version_texto. No se
atribuyen huellas/evidencia explícita a registros legados por existir una fila.
"""
from datetime import datetime
from sqlalchemy import select, exists

from app.modules.identity.application.consent import DocumentoConsentimiento
from app.modules.identity.domain.entities import Rol
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM
from app.modules.identity.infrastructure.repositories import RepositorioUsuariosSQLAlchemy, id_entero
from app.modules.identity.infrastructure.academic_base_models import ConsentimientoORM as C


def _documento(fuente, id_asignacion, ahora):
    if (fuente is None or type(id_asignacion) is not int or id_asignacion<=0
            or not isinstance(ahora,datetime) or ahora.utcoffset() is None):
        raise IntegracionPendiente()
    documento = fuente.vigente(id_asignacion=id_asignacion,ahora=ahora)
    if not isinstance(documento,DocumentoConsentimiento) or not documento.vigente:
        raise IntegracionPendiente()
    return documento


def exigir_aceptacion(db, *, id_estudiante, id_asignacion, ahora, fechas, fuente,
                     id_consentimiento=None):
    documento = _documento(fuente,id_asignacion,ahora)
    consulta = select(C).where(C.id_estudiante==id_estudiante)
    if id_consentimiento is None:
        consulta = consulta.where(C.version_texto==documento.referencia,C.fecha_revocacion.is_(None))
    else:
        consulta = consulta.where(C.id_consentimiento==id_consentimiento)
    if documento.id_version_documento is not None:
        consulta=consulta.where(C.id_version_documento==documento.id_version_documento,
            C.aceptacion_explicita.is_(True),C.huella_aceptada==documento.huella)
    filas = db.scalars(consulta.with_for_update(read=True).execution_options(populate_existing=True)).all()
    if len(filas)>1:
        raise IntegracionPendiente()
    if (not filas or filas[0].version_texto!=documento.referencia
            or filas[0].fecha_revocacion is not None
            or fechas.desde_db(filas[0].fecha_aceptacion)>ahora):
        raise AccesoDenegado()
    return filas[0]


class ServicioConsentimientoSQLAlchemy:
    """Usa una Session prestada, actor revalidado y sin commit propio.

    No es una API productiva; el llamador controla la UoW y el rollback. No se
    inventa unicidad por estudiante/versión ni se reutilizan aceptaciones ambiguas.
    """
    def __init__(self, db, *, fuente=None, fechas, reloj):
        self.db,self.fuente,self.fechas,self.reloj=db,fuente,fechas,reloj

    def _titular(self, usuario):
        if usuario is None: raise AccesoDenegado()
        cuenta=id_entero(usuario.id_usuario)
        fila=self.db.get(UsuarioORM,cuenta,with_for_update=True,populate_existing=True)
        if fila is None: raise AccesoDenegado()
        self.db.get(RolORM,fila.id_rol,with_for_update={'read':True},populate_existing=True)
        actual=RepositorioUsuariosSQLAlchemy(self.db).obtener(str(cuenta))
        if actual is None or not actual.activo or Rol.ESTUDIANTE not in actual.roles:
            raise AccesoDenegado()
        return cuenta

    def aceptar(self, *, usuario, id_asignacion, referencia_presentada, huella_presentada, acepta):
        # El ámbito lo aporta la fuente confiable, no el id elegido por el cliente.
        with self.db.no_autoflush:
            cuenta=self._titular(usuario)
            ahora=self.reloj.ahora()
            documento=_documento(self.fuente,id_asignacion,ahora)
            if (acepta is not True or referencia_presentada!=documento.referencia
                    or huella_presentada!=documento.huella): raise AccesoDenegado()
            # Serialización por cuenta para las operaciones de este servicio.
            existentes=self.db.scalars(select(C).where(C.id_estudiante==cuenta,
                C.version_texto==documento.referencia,C.fecha_revocacion.is_(None))).all()
            if existentes:
                if (documento.id_version_documento is not None and len(existentes)==1
                    and existentes[0].id_version_documento==documento.id_version_documento
                    and existentes[0].aceptacion_explicita is True
                    and existentes[0].huella_aceptada==documento.huella
                    and self.fechas.desde_db(existentes[0].fecha_aceptacion)<=ahora):
                    return existentes[0].id_consentimiento
                # Una fila histórica no prueba consentimiento explícito de esta
                # solicitud. No crear duplicados ni afirmar idempotencia sin prueba.
                raise IntegracionPendiente()
            fila=C(id_estudiante=cuenta,version_texto=documento.referencia,
                   fecha_aceptacion=self.fechas.hacia_db(ahora,sin_offset=True))
            if documento.id_version_documento is not None:
                fila.id_version_documento=documento.id_version_documento
                fila.aceptacion_explicita=True;fila.huella_aceptada=documento.huella
            self.db.add(fila);self.db.flush()
            return fila.id_consentimiento

    def consultar(self, *, usuario, id_asignacion, id_consentimiento):
        with self.db.no_autoflush:
            cuenta=self._titular(usuario)
            fila=exigir_aceptacion(self.db,id_estudiante=cuenta,id_asignacion=id_asignacion,
                id_consentimiento=id_consentimiento,ahora=self.reloj.ahora(),
                fuente=self.fuente,fechas=self.fechas)
            return fila.id_consentimiento

    def comprobar_revocacion(self, *, usuario, id_consentimiento):
        """Guard interno, sin crear un flujo de revocación ni modificar fechas."""
        from app.modules.participation.infrastructure.models import IntentoModel
        with self.db.no_autoflush:
            cuenta=self._titular(usuario)
            fila=self.db.get(C,id_consentimiento,with_for_update=True,populate_existing=True)
            if fila is None or fila.id_estudiante!=cuenta: raise AccesoDenegado()
            if self.db.scalar(select(exists().where(IntentoModel.id_consentimiento==fila.id_consentimiento,
                                                   IntentoModel.estado=='EN_CURSO'))):
                raise AccesoDenegado()
